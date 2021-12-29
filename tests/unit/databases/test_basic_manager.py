import pytest

from cq.bus import MessageBus
from cq.databases import BasicTransactionManager
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent
from tests.unit.databases.base import _TestEventHandling
from tests.unit.databases.base import _TestTransactions


class TestBasicTransactions(_TestTransactions[BasicTransactionManager]):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        return BasicTransactionManager(bus)


class TestEventHandling(_TestEventHandling[BasicTransactionManager]):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        return BasicTransactionManager(bus)

    def test_events_are_handled_immediately_outside_a_transaction(
        self,
        bus: MessageBus,
        user_created_handler: EventHandler,
    ):
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event
