import typing as t
import logging
from collections import defaultdict

from lib.events import Event
from lib.events import EventHandler
from lib.commands import Command
from lib.commands import CommandHandler
from lib.exceptions import DuplicatedCommandHandler
from lib.exceptions import InvalidMessageType
from lib.exceptions import InvalidMessage
from lib.exceptions import MissingCommandHandler
from lib.databases import TransactionManager


logger = logging.getLogger()

Handler = t.Union[CommandHandler, EventHandler]
CommandType = t.Type[Command]
EventType = t.Type[Event]


class MessageBus:
    """
    An in-memory message bus.
    """

    event_handlers: t.DefaultDict[str, list[EventHandler]]
    command_handlers: dict[str, CommandHandler]

    transaction_manager: t.Optional["TransactionManager"]

    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.command_handlers = {}
        self.transaction_manager = None

    def subscribe_event(self, event: EventType, handler: EventHandler):
        """
        Subscribe to an event type. An event may have multiple handlers

        :raises InvalidMessageType:
        """
        if not issubclass(event, Event):
            raise InvalidMessageType(f"This is not an event class: '{event}'")
        self.event_handlers[event.NAME].append(handler)

    def subscribe_command(self, command: CommandType, handler: CommandHandler):
        """
        Set the command handler for this command. Only one handler allowed.

        :raises InvalidMessageType:
        :raises ConfigError: if there is already a handler
        """
        if not issubclass(command, Command):
            raise InvalidMessageType(f"This is not a command class: '{command}'")
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
        Triggers the command handler. Handler exceptions are propagated

        :raises InvalidMessage: if this isn't a Command
        :raises MissingCommandHandler: if there's no handler configured for the command
        """
        if not isinstance(command, Command):
            raise InvalidMessage(f"This is not an command: '{command}'")

        try:
            handler = self.command_handlers[command.NAME]
        except KeyError:
            raise MissingCommandHandler(f"Missing handler for command: '{command}'")

        logger.debug(f"Handling command '{command}': calling '{handler}'")
        return handler(command)

    def emit_event(self, event: Event) -> None:
        """
        Emit an event. If there's no running transaction, it's handled immediately.

        :raises InvalidMessage: if this isn't an Event
        """
        if not isinstance(event, Event):
            raise InvalidMessage(f"This is not an event: '{event}'")

        if self.transaction_manager and self.transaction_manager.in_transaction:
            self.transaction_manager.queue_event(event)
        else:
            self._handle_event(event)

    def _handle_event(self, event: Event) -> None:
        """
        Triggers the event handlers. Handler exceptions are captured and error-logged.
        """
        handlers = self.event_handlers[event.NAME][:]
        logger.debug(f"Handling event '{event}': {len(handlers)} handlers")

        for handler in handlers:
            logger.debug(f"Handling event '{event}': calling '{handler}'")
            try:
                handler(event)
            except Exception:
                logger.exception("Exception handling event '{event}'")
