import pytest

from lib.messages import MessageMeta
from lib.events import EventMeta
from lib.commands import CommandMeta


@pytest.fixture()
def clear_meta():
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
    yield None
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
