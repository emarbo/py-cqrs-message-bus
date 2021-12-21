import pytest
from dataclasses import dataclass

from lib.messages import MessageMeta
from lib.events import Event
from lib.events import EventMeta
from lib.exceptions import CQError


def test_events_are_registered():
    """
    Test events are registered in the EventType metaclass
    """

    class MyEvent(Event):
        NAME = "MyEvent"

    assert MyEvent is EventMeta._events["MyEvent"]
    assert MyEvent is MessageMeta._messages["MyEvent"]


def test_event_name_autogeneration():
    """
    Test a NAME is automatically generated when not defined
    """

    class MyEvent(Event):
        pass

    assert hasattr(MyEvent, "NAME")
    assert type(MyEvent.NAME) is str
    assert MyEvent.NAME.endswith(".MyEvent")


def test_name_collision_raises_exception():
    """
    Two events with the same name raises an Exception
    """

    class MyEvent(Event):
        NAME = "MyEvent"

    with pytest.raises(CQError):

        class OtherEvent(Event):
            NAME = "MyEvent"


def test_events_can_be_dataclasses():
    """
    Test events can be dataclasses
    """

    @dataclass
    class UserCreatedEvent(Event):
        NAME = "user-created"
        id: str

    event = UserCreatedEvent(id="1234")

    assert event.NAME == UserCreatedEvent.NAME
    assert event.id == "1234"
