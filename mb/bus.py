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
from mb.injection import PreparedHandler

logger = logging.getLogger(__name__)


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

    event_handlers: dict[type[Event], list[t.Callable]]
    command_handlers: dict[type[Command], t.Callable]

    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.command_handlers = {}

    def subscribe_event(self, cls: type[Event], handler: t.Callable) -> None:
        """
        Subscribe to an event type. An event may have multiple handlers

        :raises InvalidMessageType:
        """
        if not self.__is_event_type(cls):
            raise InvalidMessageType(f"This is not an event class: '{cls}'")

        if handler in self.event_handlers:
            logger.info(
                "Ignoring duplicated subscribe of handler '{handler}' to '{cls}'"
            )
        else:
            self.event_handlers[cls].append(handler)

    def subscribe_command(self, cls: type[Command], handler: t.Callable) -> None:
        """
        Set the command handler for this command. Only one handler allowed.

        :raises InvalidMessageType:
        :raises ConfigError: if there is already a handler
        """
        if not self.__is_command_type(cls):
            raise InvalidMessageType(f"This is not a command class: '{cls}'")

        current = self.command_handlers.get(cls, None)
        if current is None:
            self.command_handlers[cls] = handler
        elif current == handler:
            logger.info(
                "Ignoring duplicated subscribe of handler '{handler}' to '{cls}'"
            )
        else:
            raise DuplicatedCommandHandler(
                f"Duplicated handler for command '{cls}'. "
                f"The handler '{handler}' overrides the current '{current}'"
            )

    def __is_command_type(self, thing):
        return isinstance(thing, type) and issubclass(thing, Command)

    def __is_event_type(self, thing):
        return isinstance(thing, type) and issubclass(thing, Event)

    def _handle_command(self, command: Command, uow: UnitOfWork) -> t.Any:
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
            raise MissingCommandHandler(command)

        logger.debug(f"Handling command '{command}': calling '{handler}'")
        prepared = PreparedHandler(handler, command, uow)
        return prepared()

    def _handle_event(self, event: Event, uow: UnitOfWork) -> None:
        """
        Triggers the event handlers. Handler exceptions are captured and error-logged.
        """
        # Collect handlers
        seen: set[t.Callable] = set()
        handlers: list[t.Callable] = []
        for event_cls in inspect.getmro(type(event)):
            for handler in self.event_handlers[event_cls]:
                if handler not in seen:
                    handlers.append(handler)
                    seen.add(handler)

        # Call handlers
        logger.debug(f"Handling event '{event}': {len(handlers)} handlers")
        for handler in handlers:
            logger.debug(f"Handling event '{event}': calling '{handler}'")
            prepared = PreparedHandler(handler, event, uow)
            try:
                prepared()
            except Exception:
                logger.exception(f"Exception handling event '{event}'")

    def clone(self) -> "MessageBus":
        """
        Returns a copy of itself with the same (detached) configuration
        """
        bus = type(self)()

        for command_cls, handler in self.command_handlers.items():
            bus.subscribe_command(command_cls, handler)

        for event_cls, handlers in self.event_handlers.items():
            for event_handler in handlers:
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
