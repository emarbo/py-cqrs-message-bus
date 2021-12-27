import pytest

from cq.commands import CommandMeta
from cq.events import EventMeta
from cq.messages import MessageMeta


@pytest.fixture(autouse=True)
def clear_meta():
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
    yield None
    MessageMeta._clear()
    CommandMeta._clear()
    EventMeta._clear()
