import pytest

from lib.bus import MessageBus
from lib.messages import Message
from lib.events import Event
from lib.commands import Command
from lib.exceptions import CQError

# TODO: The whole shit of creating a class and a handler should be easy
# to encapsulate in a class-based test case and reused everywhere. It's
# a really repeated scenario.


def test_bus_handles_commands(
    clear_meta,
    bus: MessageBus,
):
    """
    Test simple command configuration
    """
    called = [False]

    class MyCommand(Command):
        pass

    def command_handler(_: MyCommand):
        called[0] = True

    # Given a bus configured to handle MyCommand
    bus.subscribe_command(MyCommand, command_handler)
    # When handling a command
    bus.handle_command(MyCommand())
    # Then the handler must be called
    assert called[0]


def test_bus_handles_events(
    clear_meta,
    bus: MessageBus,
):
    """
    Test simple event configuration
    """
    called = [False]

    class MyEvent(Event):
        pass

    def event_hander(_: MyEvent):
        called[0] = True

    # Given a bus configured to handle MyEvent
    bus.subscribe_event(MyEvent, event_hander)
    # When emitting an event
    bus.emit_event(MyEvent())
    # Then the handler must be called
    assert called[0]


def test_missing_command_handler_raises_error(
    clear_meta,
    bus: MessageBus,
):
    """
    Test commands must have handlers
    """

    class MyCommand(Command):
        pass

    # Given a bus not able to handle MyCommand
    pass
    # When handling MyCommand it shall raise an error
    with pytest.raises(CQError):
        bus.handle_command(MyCommand())


def test_missing_event_handler_is_fine(
    clear_meta,
    bus: MessageBus,
):
    """
    Test events don't require handlers
    """

    class MyEvent(Event):
        pass

    # Given a bus not able to handle MyEvent
    pass
    # When emitting the event, no errors are raised
    bus.emit_event(MyEvent())


def test_bus_handles_commands_emitting_events(
    clear_meta,
    bus: MessageBus,
):
    """
    Test simple commands and events scenario
    """
    calls = []  # type: list[Message]

    class MyCommand(Command):
        pass

    class MyEvent(Event):
        pass

    command = MyCommand()
    event = MyEvent()

    def command_handler(command: MyCommand):
        calls.append(command)
        bus.emit_event(event)

    def event_hander(event: MyEvent):
        calls.append(event)

    # Given a command hanlder that emits events
    bus.subscribe_command(MyCommand, command_handler)
    bus.subscribe_event(MyEvent, event_hander)

    # When handling the command
    bus.handle_command(command)
    # Then both hanlders must be called
    assert calls == [command, event]
