import pytest

from lib.events.event import EventType


@pytest.fixture()
def clear_events():
    EventType._clear()
    yield None
    EventType._clear()
