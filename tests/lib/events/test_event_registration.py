import pytest
from dataclasses import dataclass

from lib.events import Event
from lib.events import EventType


def test_event_registers(clear_meta):
    """
    Events are registered in the EventType metaclass
    """

    class MyEvent(Event):
        NAME = "MyEvent"

    assert MyEvent == EventType._events["MyEvent"]


def test_name_collision_raises_exception(clear_meta):
    """
    Events names collision raises an exception
    """

    class MyEvent(Event):
        NAME = "MyEvent"

    with pytest.raises(RuntimeError):

        class OtherEvent(Event):
            NAME = "MyEvent"


def test_event_dataclasses(clear_meta):
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
