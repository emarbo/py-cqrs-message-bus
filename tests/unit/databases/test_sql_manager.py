import pytest

from lib.bus import MessageBus
from lib.databases import BasicTransactionManager
from lib.events import Event
from tests.fixtures.scenarios.create_user import CommandHandler
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent


@pytest.fixture(scope="module")
def manager(bus: MessageBus):
    return BasicTransactionManager(bus)


def test_manager_fixture_links_bus(
    bus: MessageBus,
    manager: BasicTransactionManager,
):
    assert manager.bus is bus


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


def test_checkpoints_events_are_hadled_on_transaction_commit(
    clear_meta,
    bus: MessageBus,
    manager: TransactionManager,
):
    """
    Test events emitted during a transaction are triggered on commit
    """
    calls = []  # type: list[Event]

    class MyEvent(Event):
        pass

    def event_hander(event: MyEvent):
        calls.append(event)

    # Given a bus configured to handle MyEvent
    bus.subscribe_event(MyEvent, event_hander)

    # When events are emitted in nested transactions
    # Then events are handled only after the parent transaction ends
    manager.begin()  # parent
    event_1 = MyEvent()
    bus.emit_event(event_1)
    manager.begin()  # nested
    event_2 = MyEvent()
    bus.emit_event(event_2)
    assert not calls, "Events must be handled on transaction ends"
    manager.commit()  # commit nested
    assert not calls, "Events must be handled on transaction ends"
    manager.commit()  # commit parent
    assert calls == [event_1, event_2], "Events must be handled on transaction ends"


def test_nested_transactions_dicards_events_on_rollback(
    clear_meta,
    bus: MessageBus,
    manager: TransactionManager,
):
    calls = []  # type: list[Event]

    class MyEvent(Event):
        pass

    def event_hander(event: MyEvent):
        calls.append(event)

    # Given a bus configured to handle MyEvent
    bus.subscribe_event(MyEvent, event_hander)

    # When events are emitted in nested transactions
    # Then events are handled only after the parent transaction ends
    manager.begin()  # parent
    event_1 = MyEvent()
    bus.emit_event(event_1)
    manager.begin()  # nested
    event_2 = MyEvent()
    bus.emit_event(event_2)
    manager.rollback()  # rollback nested
    manager.commit()  # commit parent
    assert calls == [event_1], "Events must be handled on transaction ends"
