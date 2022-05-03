import typing as t

from mb.commands import Command
from mb.events import Event
from mb.exceptions import InvalidMessage

if t.TYPE_CHECKING:
    from mb.bus import MessageBus


class UnitOfWork:
    """
    Simplest implementation. Handles events as they're emitted.
    """

    bus: "MessageBus"

    def __init__(self, bus: "MessageBus"):
        self.bus = bus

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def handle_command(self, command: Command) -> t.Any:
        """
        Triggers the command handler. Handler exceptions are propagated

        :raises InvalidMessage: if this isn't an Event
        :raises MissingCommandHandler: if there's no handler configured for the command
        """
        if not isinstance(command, Command):
            raise InvalidMessage(f"This is not a command: '{command}'")
        return self._handle_command(command)

    def _handle_command(self, command: Command) -> t.Any:
        return self.bus._handle_command(command, self)

    def emit_event(self, event: Event):
        """
        Triggers the event handlers. Handler exceptions are captured and error-logged.

        :raises InvalidMessage: if this isn't an Event
        """
        if not isinstance(event, Event):
            raise InvalidMessage(f"This is not an event: '{event}'")
        self._emit_event(event)

    def _emit_event(self, event: Event):
        self._handle_event(event)

    def _handle_event(self, event: Event):
        self.bus._handle_event(event, self)
