import pytest

from lib.bus import MessageBus
from lib.databases import SqlTransactionManager
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent

from tests.unit.databases.base import _TestTransactions
from tests.unit.databases.base import _TestEventHandling


class TestSqlTransactions(_TestTransactions[SqlTransactionManager]):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        manager = SqlTransactionManager(bus)
        manager.set_autocommit(True)  # In False mode, it never closes transaction
        manager.connect()
        return manager


class TestSqlEventHandlingAutocommitOn(_TestEventHandling[SqlTransactionManager]):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        manager = SqlTransactionManager(bus)
        manager.set_autocommit(True)
        manager.connect()
        return manager

    def test_events_are_handled_immediately_outside_a_transaction(
        self,
        bus: MessageBus,
        user_created_handler: EventHandler,
    ):
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event


class TestSqlEventHandlingAutocommitOff(_TestEventHandling[SqlTransactionManager]):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        manager = SqlTransactionManager(bus)
        manager.set_autocommit(False)
        manager.connect()
        return manager

    def test_transaction_is_always_open(self, manager: SqlTransactionManager):
        assert manager.in_transaction
        manager.commit()
        assert manager.in_transaction

    def test_events_are_handled_only_on_commit(
        self,
        bus: MessageBus,
        manager: SqlTransactionManager,
        user_created_handler: EventHandler,
    ):
        # First loop
        event_1 = UserCreatedEvent("pepe_1")
        bus.emit_event(event_1)
        assert not user_created_handler.calls
        manager.commit()
        assert user_created_handler.calls == [event_1]
        assert manager.in_transaction

        # First loop
        event_2 = UserCreatedEvent("pepe_2")
        bus.emit_event(event_2)
        assert user_created_handler.calls == [event_1]
        manager.commit()
        assert user_created_handler.calls == [event_1, event_2]
        assert manager.in_transaction


class _TestSqlSavepoints:
    def test_committed_savepoint_events_are_hadled_on_commit(
        self,
        bus: MessageBus,
        manager: SqlTransactionManager,
        user_created_handler: EventHandler,
    ):
        manager.begin()
        manager.begin_savepoint("s1")
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        manager.commit_savepoint("s1")
        assert not user_created_handler.calls
        manager.commit()
        assert user_created_handler.calls
        assert user_created_handler.calls == [event]

    def test_rolled_back_savepoint_events_are_discarded_on_commit(
        self,
        bus: MessageBus,
        manager: SqlTransactionManager,
        user_created_handler: EventHandler,
    ):
        manager.begin()
        manager.begin_savepoint("s1")
        event = UserCreatedEvent("pepe")
        bus.emit_event(event)
        manager.rollback_savepoint("s1")
        manager.commit()
        assert not user_created_handler.calls

    def test_savepoints_are_reusable(
        self,
        bus: MessageBus,
        manager: SqlTransactionManager,
        user_created_handler: EventHandler,
    ):
        manager.begin()
        manager.begin_savepoint("s1")

        event_1 = UserCreatedEvent("pepe_1")
        bus.emit_event(event_1)
        manager.rollback_savepoint("s1")
        assert not user_created_handler.calls

        event_2 = UserCreatedEvent("pepe_2")
        bus.emit_event(event_2)
        manager.commit_savepoint("s1")
        assert not user_created_handler.calls

        manager.commit()
        assert user_created_handler.calls == [event_2]

    def test_commit_transaction_commits_opened_savepoints(
        self,
        bus: MessageBus,
        manager: SqlTransactionManager,
        user_created_handler: EventHandler,
    ):
        manager.begin()

        manager.begin_savepoint("s1")
        event_1 = UserCreatedEvent("pepe_1")
        bus.emit_event(event_1)
        assert not user_created_handler.calls

        manager.begin_savepoint("s2")
        event_2 = UserCreatedEvent("pepe_2")
        bus.emit_event(event_2)
        assert not user_created_handler.calls

        manager.commit()
        assert user_created_handler.calls == [event_1, event_2]


class TestSqlSavepointsAutocommitOff(_TestSqlSavepoints):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        manager = SqlTransactionManager(bus)
        manager.set_autocommit(False)
        manager.connect()
        return manager


class TestSqlSavepointsAutocommitOn(_TestSqlSavepoints):
    @pytest.fixture
    def manager(self, bus: MessageBus):
        manager = SqlTransactionManager(bus)
        manager.set_autocommit(True)
        manager.connect()
        return manager
