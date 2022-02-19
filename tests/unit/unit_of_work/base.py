import typing as t

import pytest

from cq.bus.bus import MessageBus
from cq.unit_of_work import UnitOfWork
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent

UOW = t.TypeVar("UOW", bound=UnitOfWork)


class FakeException(Exception):
    pass


class _TestUnitOfWork(t.Generic[UOW]):
    """
    Test common UnitOfWork interface
    """

    @pytest.fixture
    def uow(self, bus: MessageBus) -> UOW:
        raise NotImplementedError()

    def test_context(self, uow: UOW):
        with uow:
            pass

    def test_nested_context(self, uow: UOW):
        with uow:
            with uow:
                pass

    def test_context_rollback(self, uow: UOW):
        with pytest.raises(FakeException):
            with uow:
                raise FakeException()

    def test_events_are_handled(
        self,
        uow: UOW,
        user_created_handler: EventHandler,
    ):
        with uow:
            event = UserCreatedEvent("mike")
            uow.emit_event(event)
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event


class _TestTransactionalUnitOfWork(t.Generic[UOW]):
    """
    Test UnitOfWork that implements nested transactions management
    """

    def test_events_are_handled_on_commit(
        self,
        uow: UOW,
        user_created_handler: EventHandler,
    ):
        with uow:
            event = UserCreatedEvent("pepe")
            uow.emit_event(event)
            assert not user_created_handler.calls
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event

    def test_events_are_discarded_on_rollback(
        self,
        uow: UOW,
        user_created_handler: EventHandler,
    ):
        try:
            with uow:
                event = UserCreatedEvent("pepe")
                uow.emit_event(event)
                assert not user_created_handler.calls
                raise FakeException()
        except FakeException:
            pass
        assert not user_created_handler.calls

    def test_nested_events_are_handled_on_outermost_commit(
        self,
        uow: UOW,
        user_created_handler: EventHandler,
    ):
        with uow:
            with uow:
                event_1 = UserCreatedEvent("pepe-1")
                uow.emit_event(event_1)
            assert not user_created_handler.calls
            event_2 = UserCreatedEvent("pepe-2")
            uow.emit_event(event_2)
            assert not user_created_handler.calls
        assert user_created_handler.calls
        assert user_created_handler.calls == [event_1, event_2]

    def test_nested_rolled_back_events_are_discarded(
        self,
        uow: UOW,
        user_created_handler: EventHandler,
    ):
        with uow:
            try:
                with uow:
                    event_1 = UserCreatedEvent("pepe-1")
                    uow.emit_event(event_1)
                    raise FakeException()
            except FakeException:
                pass
            assert not user_created_handler.calls
            event_2 = UserCreatedEvent("pepe-2")
            uow.emit_event(event_2)
            assert not user_created_handler.calls
        assert user_created_handler.calls
        assert user_created_handler.calls == [event_2]
