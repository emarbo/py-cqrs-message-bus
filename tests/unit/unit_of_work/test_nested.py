import pytest

from cq.bus.bus import MessageBus
from cq.unit_of_work import NestedUnitOfWork
from tests.unit.unit_of_work.base import _TestUnitOfWork
from tests.unit.unit_of_work.base import _TestTransactionalUnitOfWork


class TestNestedUnitOfWork(
    _TestUnitOfWork[NestedUnitOfWork],
    _TestTransactionalUnitOfWork[NestedUnitOfWork],
):
    @pytest.fixture
    def uow(self, bus: MessageBus):
        return NestedUnitOfWork(bus)
