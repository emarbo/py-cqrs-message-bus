import pytest

from cq.bus.bus import MessageBus
from cq.bus.messages import Message
from cq.unit_of_work.nested import NestedUnitOfWork
from cq.utils.tracked_handler import TrackedHandler
from cq.utils.tracked_handler import tracked_handler


@pytest.fixture()
def bus():
    return MessageBus()


@pytest.fixture()
def uow(bus):
    return NestedUnitOfWork(bus)


@pytest.fixture()
def handler() -> TrackedHandler[Message, None]:
    """
    A generic handler for Commands and Events
    """

    @tracked_handler
    def handler(message: Message) -> None:
        return None

    return handler
