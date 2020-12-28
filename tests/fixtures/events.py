import pytest

from lib.messages import MessageType
from lib.events import EventType
from lib.commands import CommandType


@pytest.fixture()
def clear_meta():
    MessageType._clear()
    CommandType._clear()
    EventType._clear()
    yield None
    MessageType._clear()
    CommandType._clear()
    EventType._clear()
