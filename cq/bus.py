import logging
import typing as t
from collections import defaultdict

from cq.commands import Command
from cq.databases import TransactionManager
from cq.events import Event
from cq.exceptions import DuplicatedCommandHandler
from cq.exceptions import InvalidMessage
from cq.exceptions import InvalidMessageType
from cq.exceptions import MissingCommandHandler

logger = logging.getLogger()

# --------------------------------------
# Typings
# --------------------------------------


C = t.TypeVar("C", bound=Command)
E = t.TypeVar("E", bound=Event)


class CommandHandlers(t.Protocol):  # pragma: no cover
    def __setitem__(self, key: type[C], item: t.Callable[[C], t.Any]):
        ...

    def __getitem__(self, item: type[C]) -> t.Callable[[C], t.Any]:
        ...


class EventHandlers(t.Protocol):  # pragma: no cover
    def __getitem__(self, item: type[E]) -> list[t.Callable[[E], t.Any]]:
        ...


# --------------------------------------
# Bus
# --------------------------------------

#
# TODO: Allow mixing in-process and remote (e.g. Kafka) handlers for
# both commands and events.
#
# An in-process command handler should be able to call a remote
# command handler and events emitted by the in-process commands
# should also be emitted on Kafka (if it's configured to do so).
#
# The event handler is actually who knows if it should be run
# synchronously or asynchronously. For instance, there might be
# many reactions to the UserCreatedEvent, some of them might need
# to run synchronously (e.g., created some auxiliary tables) and
# others (e.g., sending an email) can run remotely later.
#
# For every process there must be a single MessageBus that handles
# the transaction/events stuff but it could have multiple
# "handler providers" plugged that rely on different technologies
# to handler commands and events. In other words, the current
# MessageBus implemetation could be split in two classes:
# the MessageBus itself and an InProcessBusProvider. The MessageBus
# could have a list of providers that may handle a command, the
# first one able to do so handles it. For the events, there's even
# simpler as an event supports infinite handlers. Bear in mind that
# the same? configuration could be used by an HTTP worker and by a
# Kafka consumer... don't queue the same event infinitely.
#

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
