import pytest

from cq.bus.commands import CommandMeta
from cq.bus.events import EventMeta
from cq.bus.messages import MessageMeta


@pytest.fixture(autouse=True)
def clear_meta():
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
    yield None
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
