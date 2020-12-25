import pytest
from dataclasses import dataclass

from lib.events.event import Event
from lib.events.event import EventType


def test_event_registers(clear_events):
    """
    Events are registered in the EventType metaclass
    """

    class MyEvent(Event):
        NAME = "MyEvent"

    assert MyEvent == EventType._events["MyEvent"]


def test_name_collision_raises_exception(clear_events):
    """
    Events names collision raises an exception
    """

    class MyEvent(Event):
        NAME = "MyEvent"

    with pytest.raises(RuntimeError):

        class OtherEvent(Event):
            NAME = "MyEvent"


def test_event_dataclasses(clear_events):
    """
    Events can be dataclasses
    """

    @dataclass
    class UserCreatedEvent(Event):
        NAME = "user-created"
        id: str

    event = UserCreatedEvent(id="1234")

    assert event.NAME == UserCreatedEvent.NAME
    assert event.id == "1234"
