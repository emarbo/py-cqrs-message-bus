import pytest

from lib.events import EventType


@pytest.fixture()
def clear_events():
    EventType._clear()
    yield None
    EventType._clear()
