import pytest

from mb.commands import CommandMeta
from mb.events import EventMeta
from mb.messages import MessageMeta


@pytest.fixture(autouse=True)
def clear_meta():
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
    yield None
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
