import logging
import re
import typing as t
from collections import defaultdict

from mb.commands import Command
from mb.commands import is_command_type
from mb.events import Event
from mb.events import is_event_type
from mb.exceptions import ConfigError
from mb.exceptions import DuplicatedHandlerError
from mb.exceptions import InvalidMessageError
from mb.exceptions import MissingHandlerError
from mb.messages import Message

logger = logging.getLogger(__name__)


#
# NOTE: subscrbing to Event means subscrbing to all events. In the same way,
# subscribing to ParentEvent means subscribing to any ChildEvent(ParentEvent).
# I dunno if this makes sense for everyone, I'm just exploring options and
# trying in a real project to get a real experience.
# Btw, I'll better check/revise how this works in Kafka or Rabbit and get some
# clever ideas from the real pros.
#

#
# TODO: Provide priority when subscribing.
# By default, handlers are ordered by
#
#  1. Preciseness: when emitting MyEvent, handlers subscribed to MyEvent go before
#     events subscribed to Event
#
#  2. Subscription order: subscribers of MyEvent are called by subscription order
#
# The approach is ordering by priority, then Preciseness, then Subscription order.
#


#
# TODO: Allow event handlers to propagate exceptions. This is very helpful for tests
# that work with a preconfigured bus. Otherwise the test does not stop at the error!
#


# TODO: Provide an auto transaction in the handler decorator and registration
# TODO: Provide a DjangoMessageBus that extends the previous feature with autocommit.


@t.runtime_checkable
class EventMatcher(t.Protocol):
    def __call__(self, event: Event) -> bool:
        ...


class PatternEventMatcher(EventMatcher):
    """
    Pattern matcher that supports wildcard (*) and globstar (**) operators.

    Event names are composed by words separated by dots. At least one word is required.
    Every word is composed by alphanumeric characters, underscores or hippens.

        <word>[.<word>]*

    The widlcard and globstar must be placed either at the beginning/end of
    the pattern or between dots. Any other position will raise an error.

    The wildcard matches exactly one <word>, meanwhile the globstar one or more of
    these <words>.

    Examples:

        Pattern     : *
        Matches     : package, package_sent, package-sent

        Pattern     : *.*
        Matches     : package.sent

        Pattern     : **
        Matches     : everything

        Pattern     : packages.**
        Matches     : packages.letter.sent, packages.letter.lost
        Not matches : packages

        Pattern     : packages.**.sent
        Matches     : packages.letter.sent, packages.box.large.sent
        Not matches : packages.sent

        Pattern     : something.fixed
        Matches     : something.fixed
    """

    pattern: str
    _pattern_re: re.Pattern

    def __init__(self, pattern: str):
        self.validate_pattern(pattern)
        self.pattern = pattern
        self._pattern_re = self.to_regex(pattern)

    def __str__(self):
        return f"Pattern<{self.pattern}>"

    def __call__(self, message: Message) -> bool:
        return bool(self._pattern_re.match(message.NAME))

    @classmethod
    def is_pattern(cls, pattern: str):
        return "*" in pattern

    @classmethod
    def validate_pattern(cls, pattern: str):
        valid_chars = re.compile(r"^[a-zA-Z0-9_.*-]+$")
        if not valid_chars.match(pattern):
            raise ConfigError(
                "Invalid pattern. Patterns must contain alphanumeric characters, "
                f"underscores, hippens, dots or asteriks. Found: '{pattern}'"
            )

        invalid_star = re.compile(r".*([a-zA-Z0-9_-]\*|\*[a-zA-Z0-9_-]).*")
        if invalid_star.match(pattern):
            raise ConfigError(
                "Invalid pattern. Wildcard and globstar must be placed between dots, "
                f"the begining or the ending of the pattern. Found: '{pattern}'"
            )

        if "***" in pattern:
            raise ConfigError(
                "Invalid pattern. Found three consecutive asteriks: '{pattern}'"
            )

        if ".." in pattern:
            raise ConfigError(
                f"Invalid pattern. Found two consecutive points: '{pattern}'"
            )

    @classmethod
    def to_regex(cls, pattern: str) -> re.Pattern:
        pattern = (
            pattern.replace(r".", r"__dot__")
            .replace(r"**", r"__globstar__")  # order matters
            .replace(r"*", r"__wildcard__")
            .replace(r"__dot__", r"\.")
            .replace(r"__globstar__", r".+")
            .replace(r"__wildcard__", r"[^.]+")
        )
        return re.compile(f"^{pattern}$")


class TypeEventMatcher(EventMatcher):
    """
    Match events of a given type and their subclasses optionally
    """

    def __init__(self, event_type: type[Message], subclasses=True):
        self.event_type = event_type
        self.match_subclasses = subclasses

    def __call__(self, message: Message) -> bool:
        if self.match_subclasses:
            return isinstance(message, self.event_type)
        return type(message) is self.event_type


class MessageBus:
    """
    An in-memory message bus.
    """

    command_handlers: dict[str, t.Callable]

    ehandlers_by_name: dict[str, list[tuple[t.Callable, int]]]
    ehandlers_by_func: dict[EventMatcher, list[tuple[t.Callable, int]]]

    def __init__(self):
        self.command_handlers = {}

        self.ehandlers_by_name = defaultdict(list)
        self.ehandlers_by_func = defaultdict(list)

    def subscribe_command(
        self,
        match: type[Command] | str,
        handler: t.Callable,
    ) -> None:
        """
        Subscribe to a command.

        :raises ConfigError:
        :raises DuplicatedHandlerError:
        """
        if is_command_type(match):
            name = match.NAME
        elif isinstance(match, str):
            name = match
        else:
            raise ConfigError("Invalid command matcher", match)

        current = self.command_handlers.get(name, None)
        if current is None:
            self.command_handlers[name] = handler
        elif current == handler:
            logger.info("Ignoring duplicated subscription of '{handler}' to '{name}'")
        else:
            raise DuplicatedHandlerError(
                f"Duplicated handler for command '{name}'. "
                f"The handler '{handler}' overrides the current '{current}'"
            )

    def subscribe_event(
        self,
        match: EventMatcher | type[Event] | str,
        handler: t.Callable,
        priority: int = 0,
    ) -> None:
        """
        Subscribe to an event.

        :param match:
            An event type, event name, name pattern or callable.

            The event type is the same as passing MyEvent.NAME as argument. The name
            pattern uses :class:`PatternEventMatcher` that supports wildcard (*)
            and globstar (**) operators.

            For other matching strategies, pass your custom matching callable.

        :param handler:
            The handler to be called for this match.

            The bus will inject the message and/or unit of work to the proper arguments
            by inspecting the handler signature. The matching depends on argument
            annotations and names, and fallbacks to the parameters order otherwise.

            A handler may receive no parameters, and that's fine. If it wants to receive
            just the UoW, it must use annotations or name it as "uow" or "unit_of_work".

        :param priority:
            When multiple handlers match the same event, they're run in this priority
            order. If priorities match, the execution order is not predictable.

        :raises ConfigError:
        """
        if is_event_type(match):
            self.ehandlers_by_name[match.NAME].append((handler, priority))

        elif isinstance(match, str):
            if PatternEventMatcher.is_pattern(match):
                match = PatternEventMatcher(match)
                self.ehandlers_by_func[match].append((handler, priority))
            else:
                self.ehandlers_by_name[match].append((handler, priority))

        elif isinstance(match, EventMatcher):
            self.ehandlers_by_func[match].append((handler, priority))

        else:
            raise ConfigError("Invalid event matcher", match)

    def command_handler(
        self,
        match: type[Command] | str,
    ):
        """
        The :method:`subscribe_command` as decorator.
        """

        def decorator(handler: t.Callable):
            self.subscribe_command(match, handler)
            return handler

        return decorator

    def event_handler(
        self,
        match: EventMatcher | type[Event] | str,
    ):
        """
        The :method:`subscribe_event` as decorator.
        """

        def decorator(handler: t.Callable):
            self.subscribe_event(match, handler)
            return handler

        return decorator

    def get_command_handler(self, command: Command) -> t.Callable:
        """
        Get the configured command handler

        :raises InvalidMessageError: if this isn't a Command
        :raises MissingHandlerError: if there's no handler configured for the command
        """
        if not isinstance(command, Command):
            raise InvalidMessageError("This is not a command", command)

        try:
            return self.command_handlers[command.NAME]
        except KeyError:
            raise MissingHandlerError(command)

    def get_event_handlers(self, event: Event) -> list[t.Callable]:
        """
        Get the configured event handlers ordered by priority.

        :raises InvalidMessageError: if this isn't an Event
        """
        handlers: list[tuple[t.Callable, int]] = []

        if not isinstance(event, Event):
            raise InvalidMessageError("This is not an event", event)

        # Collect by name
        if event.NAME in self.ehandlers_by_name:
            handlers.extend(self.ehandlers_by_name[event.NAME])

        # Collect by func
        for match, _handlers in self.ehandlers_by_func.items():
            if match(event):
                handlers.extend(_handlers)

        # Order by priority
        handlers = sorted(handlers, key=lambda pair: pair[1])

        # Remove dups
        unique_handlers = []
        for handler, _ in handlers:
            if handler not in unique_handlers:
                unique_handlers.append(handler)

        return unique_handlers

    def clone(self) -> "MessageBus":
        """
        Returns a copy of itself with the same (detached) configuration
        """
        bus = type(self)()

        for name, handler in self.command_handlers.items():
            bus.subscribe_command(name, handler)

        for name, handlers in self.ehandlers_by_name.items():
            for handler, priority in handlers:
                bus.subscribe_event(name, handler, priority=priority)

        for func, handlers in self.ehandlers_by_func.items():
            for handler, priority in handlers:
                bus.subscribe_event(func, handler, priority=priority)

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
        self.ehandlers_by_name = defaultdict(list)
        self.ehandlers_by_func = defaultdict(list)
