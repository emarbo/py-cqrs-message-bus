import inspect
import logging
import typing as t
from collections import defaultdict

from mb.commands import Command
from mb.events import Event
from mb.exceptions import DuplicatedCommandHandler
from mb.exceptions import InvalidMessage
from mb.exceptions import InvalidMessageType
from mb.exceptions import MissingCommandHandler
from mb.unit_of_work import UnitOfWork

logger = logging.getLogger()

# --------------------------------------
# Typings
# --------------------------------------

#
# TODO: Force callbacks' first argument type (command or event) but allow
# arbitrary keyword arguments to implement Dependency Injection features.
# Not all handlers need the current UnitOfWork and others might need
# other global services to work (e.g. EmailsService) that could be
# injected.
#
# Currently, Python 3.9 does not offer the abilities do to so. Will be
# the new Python 3.10 features enough? Concatenate, Param, ...
#

UOW = t.TypeVar("UOW", bound=UnitOfWork)
C = t.TypeVar("C", bound=Command)
E = t.TypeVar("E", bound=Event)


class CommandHandlers(t.Protocol):  # pragma: no cover
    def __setitem__(self, key: type[C], item: t.Callable[[C, UOW], t.Any]):
        ...

    def __getitem__(self, item: type[C]) -> t.Callable[[C, UOW], t.Any]:
        ...


class EventHandlers(t.Protocol):  # pragma: no cover
    def __getitem__(self, item: type[E]) -> list[t.Callable[[E, UOW], t.Any]]:
        ...


# --------------------------------------
# Bus
# --------------------------------------

#
# NOTE: subscrbing to Event means subscrbing to all events. In the same way,
# subscribing to ParentEvent means subscribing to any ChildEvent(ParentEvent).
# I dunno if this makes sense for everyone, I'm just exploring options and
# trying in a real project to get a real experience.
# Btw, I'll better check/revise how this works in Kafka or Rabbit and get some
# clever ideas from the real pros.
#


class MessageBus:
    """
    An in-memory message bus.
    """

    event_handlers: EventHandlers
    command_handlers: CommandHandlers

    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.command_handlers = {}

    def subscribe_event(
        self,
        cls: type[E],
        handler: t.Callable[[E, UOW], t.Any],
    ) -> None:
        """
        Subscribe to an event type. An event may have multiple handlers

        :raises InvalidMessageType:
        """
        if not issubclass(cls, Event):
            raise InvalidMessageType(f"This is not an event class: '{cls}'")
        self.event_handlers[cls].append(handler)

    def subscribe_command(
        self,
        cls: type[C],
        handler: t.Callable[[C, UOW], t.Any],
    ) -> None:
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

    def _handle_command(self, command: C, uow: UnitOfWork) -> t.Any:
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
        return handler(command, uow)

    def _handle_event(self, event: E, uow: UnitOfWork) -> None:
        """
        Triggers the event handlers. Handler exceptions are captured and error-logged.
        """
        handlers: list[t.Callable[[Event, UnitOfWork], None]] = []
        for event_cls in inspect.getmro(type(event)):
            handlers.extend(self.event_handlers[event_cls])
        logger.debug(f"Handling event '{event}': {len(handlers)} handlers")

        for handler in handlers:
            logger.debug(f"Handling event '{event}': calling '{handler}'")
            try:
                handler(event, uow)
            except Exception:
                logger.exception(f"Exception handling event '{event}'")

    def clone(self) -> "MessageBus":
        """
        Returns a copy of itself with the same (detached) configuration
        """
        bus = type(self)()

        for command_cls, handler in self.command_handlers.items():  # type:ignore
            bus.subscribe_command(command_cls, handler)

        for event_cls, handler in self.event_handlers.items():  # type:ignore
            for event_handler in handler:
                bus.subscribe_event(event_cls, event_handler)
        return bus

    def _clear_handlers(self):
        """
        Clear handlers. Mainly for testing purposes.
        """
        self._clear_command_handlers()
        self._clear_event_handlers()

    def _clear_command_handlers(self):
        """
        Clear handlers. Mainly for testing purposes.
        """
        self.command_handlers = {}

    def _clear_event_handlers(self):
        """
        Clear handlers. Mainly for testing purposes.
        """
        self.event_handlers = defaultdict(list)
