import typing as t
import logging
from collections import defaultdict

from lib.events import EventType
from lib.events import Event
from lib.events import EventHandler
from lib.commands import CommandType
from lib.commands import Command
from lib.commands import CommandHandler
from lib.exceptions import DuplicatedCommandHandler
from lib.exceptions import InvalidMessageType
from lib.exceptions import MissingCommandHandler


logger = logging.getLogger()

Handler = t.Union[CommandHandler, EventHandler]


class MessageBus:
    """
    An in-memory message bus.
    """

    event_handlers: t.DefaultDict[str, list[EventHandler]]
    command_handlers: dict[str, CommandHandler]

    transaction_stack: list["Transaction"]

    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.command_handlers = {}
        self.transaction_stack = []

    def subscribe_event(self, event: EventType, handler: EventHandler):
        """
        Subscribe to an event type. An event may have multiple handlers
        """
        if not isinstance(event, EventType):
            raise InvalidMessageType(f"This is not an event class: '{event}'")
        self.event_handlers[event.NAME].append(handler)

    def subscribe_command(self, command: CommandType, handler: CommandHandler):
        """
        Set the command handler for this command. Only one handler allowed.

        :raises: ConfigError if there is already a handler
        """
        if not isinstance(command, CommandType):
            raise InvalidMessageType(f"This is not an command class: '{command}'")
        try:
            current_handler = self.command_handlers[command.NAME]
        except KeyError:
            self.command_handlers[command.NAME] = handler
        else:
            raise DuplicatedCommandHandler(
                f"Duplicated handler for command '{command}'. "
                f"The handler '{handler}' overrides the current '{current_handler}'"
            )

    def handle_command(self, command: Command) -> t.Any:
        """
        :raises InvalidMessageType: if the message type is wrong
        :raises MissingCommandHandler: if the command has no handler configured
        """
        if not isinstance(command, Command):
            raise InvalidMessageType(f"This is not an command instance: '{command}'")
        try:
            handler = self.command_handlers[command.NAME]
        except KeyError:
            raise MissingCommandHandler(f"Missing handler for command: '{command}'")
        # Command exceptions are unhandled by the bus
        return handler(command)

    def emit_event(self, event: Event) -> None:
        """
        Emit an event. If there's no running transaction, it's handled immediately
        """
        if not isinstance(event, Event):
            raise InvalidMessageType(f"This is not an event instance: '{event}'")
        if self.transaction_stack:
            self.transaction_stack[-1].emit_event(event)
        else:
            self._handle_event(event)

    def _handle_event(self, event: Event) -> None:
        """
        Called by the Transaction. Triggers the event handlers for this event.
        """
        for handler in self.event_handlers[event.NAME]:
            logger.debug(f"handling event '{event}' with handler '{handler}'")
            # Event exceptions are handled by the bus (at least, by now)
            try:
                handler(event)
            except Exception:
                logger.exception("Exception handling event '{event}'")


class Transaction:
    """
    Represents a database transaction.
    Events aren't handled until the top-level transaction is committed.
    """

    # CQ management
    bus: MessageBus
    events: list[Event]

    # Transaction management
    parent: t.Optional["Transaction"]

    def __init__(self, bus: MessageBus, parent: "Transaction" = None):
        self.bus = bus
        self.events = []

        self.parent = parent

    def emit_event(self, event: Event):
        self.events.append(event)

    def emit_event_many(self, events: list[Event]):
        self.events.extend(events)

    def commit(self):
        if self.parent:
            self.parent.emit_event_many(self.events)
        else:
            for event in self.events:
                self.bus._handle_event(event)

    def rollback(self):
        pass


class TransactionManager:
    """
    Bridge between the CQS library and the underlaying framework/database
    """

    bus: MessageBus

    def __init__(self, bus: MessageBus):
        self.bus = bus

    def begin(self):
        try:
            parent = self.bus.transaction_stack[-1]
        except IndexError:
            parent = None
        self.bus.transaction_stack.append(Transaction(self.bus, parent))

    def commit(self):
        transaction = self.bus.transaction_stack.pop()
        transaction.commit()

    def rollback(self):
        transaction = self.bus.transaction_stack.pop()
        transaction.rollback()
