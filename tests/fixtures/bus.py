import pytest

from mb.bus import MessageBus
from mb.messages import Message
from mb.unit_of_work import UnitOfWork
from mb.utils.tracked_handler import TrackedHandler
from mb.utils.tracked_handler import tracked_handler


@pytest.fixture()
def bus():
    return MessageBus()


@pytest.fixture()
def uow(bus):
    return UnitOfWork(bus)


@pytest.fixture()
def handler() -> TrackedHandler:
    """
    A generic handler for Commands and Events
    """

    @tracked_handler
    def handler(message: Message) -> None:
        return None

    return handler
