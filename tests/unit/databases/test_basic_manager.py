import pytest

from lib.bus import MessageBus
from lib.databases import BasicTransactionManager

from tests.unit.databases.base import _TestTransactions
from tests.unit.databases.base import _TestEventHandling
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent


class TestBasicTransactions(_TestTransactions[BasicTransactionManager]):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        return BasicTransactionManager(bus)


class TestEventHandliing(_TestEventHandling[BasicTransactionManager]):
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
