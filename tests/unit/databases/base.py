import pytest
import typing as t

from lib.bus import MessageBus
from lib.databases import TransactionManager
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent


M = t.TypeVar("M", bound=TransactionManager)


class _TestTransactions(t.Generic[M]):
    """
    Common open/close transactions
    """

    @pytest.fixture
    def manager(self, bus: MessageBus) -> M:
        raise NotImplementedError()

    def test_manager_links_bus(self, bus: MessageBus, manager: M):
        assert manager.bus is bus
        assert bus.transaction_manager is manager

    def test_begin_and_commit(self, manager: M):
        manager.begin()
        assert manager.in_transaction
        manager.commit()
        assert not manager.in_transaction

    def test_begin_and_rollback(self, manager: M):
        manager.begin()
        assert manager.in_transaction
        manager.rollback()
        assert not manager.in_transaction

    def test_begin_and_close(self, manager: M):
        manager.begin()
        assert manager.in_transaction
        manager.close()
        assert not manager.in_transaction

    def test_multiple_begins_are_harmless(self, manager: M):
        manager.begin()
        manager.begin()
        manager.begin()
        assert manager.in_transaction
        manager.commit()
        assert not manager.in_transaction


class _TestEventHandling(t.Generic[M]):
    """
    Common open/close transactions
    """

    def test_events_are_handled_after_commit(
        self,
        bus: MessageBus,
        manager: M,
        user_created_handler: EventHandler,
    ):
        manager.begin()
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        assert not user_created_handler.calls
        manager.commit()
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event

    def test_events_are_discarded_on_rollback(
        self,
        bus: MessageBus,
        manager: M,
        user_created_handler: EventHandler,
    ):
        manager.begin()
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        assert not user_created_handler.calls
        manager.rollback()
        assert not user_created_handler.calls

    def test_events_are_discarded_on_close(
        self,
        bus: MessageBus,
        manager: M,
        user_created_handler: EventHandler,
    ):
        manager.begin()
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        assert not user_created_handler.calls
        manager.close()
        assert not user_created_handler.calls
