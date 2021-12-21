import typing as t
import logging
from collections import defaultdict

from lib.events import Event
from lib.commands import Command
from lib.exceptions import DuplicatedCommandHandler
from lib.exceptions import InvalidMessageType
from lib.exceptions import InvalidMessage
from lib.exceptions import MissingCommandHandler
from lib.databases import TransactionManager

logger = logging.getLogger()

# --------------------------------------
# Typings
# --------------------------------------


C = t.TypeVar("C", bound=Command)
E = t.TypeVar("E", bound=Event)


class CommandHandlers(t.Protocol):
    def __setitem__(self, key: type[C], item: t.Callable[[C], t.Any]):
        ...

    def __getitem__(self, item: type[C]) -> t.Callable[[C], t.Any]:
        ...


class EventHandlers(t.Protocol):
    def __getitem__(self, item: type[E]) -> list[t.Callable[[E], t.Any]]:
        ...


# --------------------------------------
# Bus
# --------------------------------------


class MessageBus:
    """
    An in-memory message bus.
    """

    event_handlers: EventHandlers
    command_handlers: CommandHandlers

    transaction_manager: t.Optional["TransactionManager"]

    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.command_handlers = {}
        self.transaction_manager = None

    def subscribe_event(self, cls: type[E], handler: t.Callable[[E], t.Any]) -> None:
        """
        Subscribe to an event type. An event may have multiple handlers

        :raises InvalidMessageType:
        """
        if not issubclass(cls, Event):
            raise InvalidMessageType(f"This is not an event class: '{cls}'")
        self.event_handlers[cls].append(handler)

    def subscribe_command(self, cls: type[C], handler: t.Callable[[C], t.Any]) -> None:
        """
        Set the command handler for this command. Only one handler allowed.

        :raises InvalidMessageType:
        :raises ConfigError: if there is already a handler
        """
        if not issubclass(cls, Command):
            raise InvalidMessageType(f"This is not a command class: '{cls}'")
        try:
            current_handler = self.command_handlers[cls]
        except KeyError:
            self.command_handlers[cls] = handler
        else:
            raise DuplicatedCommandHandler(
                f"Duplicated handler for command '{cls}'. "
                f"The handler '{handler}' overrides the current '{current_handler}'"
            )

    def handle_command(self, command: C) -> t.Any:
        """
        Triggers the command handler. Handler exceptions are propagated

        :raises InvalidMessage: if this isn't a Command
        :raises MissingCommandHandler: if there's no handler configured for the command
        """
        if not isinstance(command, Command):
            raise InvalidMessage(f"This is not an command: '{command}'")

        try:
            handler = self.command_handlers[type(command)]
        except KeyError:
            raise MissingCommandHandler(f"Missing handler for command: '{command}'")

        logger.debug(f"Handling command '{command}': calling '{handler}'")
        return handler(command)

    def emit_event(self, event: E) -> None:
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

    def _handle_event(self, event: E) -> None:
        """
        Triggers the event handlers. Handler exceptions are captured and error-logged.
        """
        handlers = self.event_handlers[type(event)][:]
        logger.debug(f"Handling event '{event}': {len(handlers)} handlers")

        for handler in handlers:
            logger.debug(f"Handling event '{event}': calling '{handler}'")
            try:
                handler(event)
            except Exception:
                logger.exception("Exception handling event '{event}'")
