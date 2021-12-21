import pytest

from lib.bus import MessageBus
from lib.messages import Message
from tests.utils.tracked_handler import tracked_handler


@pytest.fixture()
def bus():
    yield MessageBus()


@pytest.fixture()
def handler():
    """
    A generic handler for Commands and Events
    """

    @tracked_handler
    def handler(message: Message):
        return None

    return handler
