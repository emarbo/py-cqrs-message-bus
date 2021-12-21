import pytest

from lib.bus import MessageBus
from lib.databases import BasicTransactionManager
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent


@pytest.fixture()
def manager(bus: MessageBus):
    return BasicTransactionManager(bus)


def test_manager_links_bus(
    bus: MessageBus,
    manager: BasicTransactionManager,
):
    assert manager.bus is bus
    assert bus.transaction_manager is manager


def test_begin_commit(
    manager: BasicTransactionManager,
):
    manager.begin()
    assert manager.in_transaction
    manager.commit()
    assert not manager.in_transaction


def test_multiple_begins_are_allowed(
    manager: BasicTransactionManager,
):
    manager.begin()
    manager.begin()
    manager.begin()
    assert manager.in_transaction
    manager.commit()
    assert not manager.in_transaction


def test_events_are_handled_after_commit(
    bus: MessageBus,
    manager: BasicTransactionManager,
    user_created_handler: EventHandler,
):
    manager.begin()
    assert manager.in_transaction
    event = UserCreatedEvent("pepe")
    bus.emit_event(event)
    assert not user_created_handler.calls
    manager.commit()
    assert not manager.in_transaction
    assert user_created_handler.calls
    assert user_created_handler.calls[0] == event


def test_events_are_discarded_on_rollback(
    bus: MessageBus,
    manager: BasicTransactionManager,
    user_created_handler: EventHandler,
):
    manager.begin()
    assert manager.in_transaction
    event = UserCreatedEvent("pepe")
    bus.emit_event(event)
    assert not user_created_handler.calls
    manager.rollback()
    assert not manager.in_transaction
    assert not user_created_handler.calls


def test_events_are_discarded_on_close(
    bus: MessageBus,
    manager: BasicTransactionManager,
    user_created_handler: EventHandler,
):
    manager.begin()
    assert manager.in_transaction
    event = UserCreatedEvent("pepe")
    bus.emit_event(event)
    assert not user_created_handler.calls
    manager.close()
    assert not manager.in_transaction
    assert not user_created_handler.calls


def test_events_are_handled_immediately_outside_a_transaction(
    bus: MessageBus,
    manager: BasicTransactionManager,
    user_created_handler: EventHandler,
):
    assert manager.bus is bus
    event = UserCreatedEvent("pepe")
    bus.emit_event(event)
    assert user_created_handler.calls
    assert user_created_handler.calls[0] == event
