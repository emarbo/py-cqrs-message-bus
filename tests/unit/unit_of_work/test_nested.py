import pytest

from mb.bus import MessageBus
from mb.unit_of_work import NestedUnitOfWork
from tests.unit.unit_of_work.base import _TestTransactionalUnitOfWork


@pytest.fixture
def uow(bus: MessageBus):
    return NestedUnitOfWork(bus)


class TestNestedUnitOfWork(
    _TestTransactionalUnitOfWork[NestedUnitOfWork],
):
    pass
