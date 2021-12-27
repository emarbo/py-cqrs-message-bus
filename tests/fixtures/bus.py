import pytest

from cq.bus import MessageBus
from cq.messages import Message
from tests.utils.tracked_handler import TrackedHandler
from tests.utils.tracked_handler import tracked_handler


@pytest.fixture()
def bus():
    yield MessageBus()


@pytest.fixture()
def handler() -> TrackedHandler[Message, None]:
    """
    A generic handler for Commands and Events
    """

    @tracked_handler
    def handler(message: Message) -> None:
        return None

    return handler
