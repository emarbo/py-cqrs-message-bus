from lib.bus import MessageBus
from lib.bus import TransactionManager
from lib.events import Event


def test_simple_transaction_stack(
    clear_meta,
    bus: MessageBus,
    transaction_manager: TransactionManager,
):
    """
    Test simple transaction management
    """
    # Commits
    transaction_manager.begin()
    assert len(bus.transaction_stack) == 1
    transaction_manager.commit()
    assert len(bus.transaction_stack) == 0

    # Rollbacks
    transaction_manager.begin()
    assert len(bus.transaction_stack) == 1
    transaction_manager.rollback()
    assert len(bus.transaction_stack) == 0


def test_events_are_triggered_on_commit(
    clear_meta,
    bus: MessageBus,
    transaction_manager: TransactionManager,
):
    """
    Test events emitted during a transaction are triggered on commit
    """
    called = [False]

    class MyEvent(Event):
        pass

    def event_hander(_: MyEvent):
        called[0] = True

    # Given a bus configured to handle MyEvent
    bus.subscribe_event(MyEvent, event_hander)

    # When an event is emitted during a transaction
    transaction_manager.begin()
    event = MyEvent()
    bus.emit_event(event)
    # Then the event is queued and the handler is not called
    assert bus.transaction_stack[-1].events == [event]
    assert not called[0], "Event must be queued until transaction ends"

    # When the transaction is committed
    transaction_manager.commit()
    # Then the handler is called
    assert called[0], "Event must be handled after the transaction commit"


def test_events_are_discarded_on_rollback(
    clear_meta,
    bus: MessageBus,
    transaction_manager: TransactionManager,
):
    """
    Test events emitted during a transaction are discarded on rollback
    """
    called = [False]

    class MyEvent(Event):
        pass

    def event_hander(_: MyEvent):
        called[0] = True

    # Given a bus configured to handle MyEvent
    bus.subscribe_event(MyEvent, event_hander)

    # When an event is emitted during a rollback transaction
    transaction_manager.begin()
    bus.emit_event(MyEvent())
    transaction_manager.rollback()
    # Then the event is discarded
    assert not called[0], "Events must be discarded on rollback"


def test_events_are_handled_immediately_outside_transaction(
    clear_meta,
    bus: MessageBus,
):
    called = [False]

    class MyEvent(Event):
        pass

    def event_hander(_: MyEvent):
        called[0] = True

    # Given a bus configured to handle MyEvent
    bus.subscribe_event(MyEvent, event_hander)
    # When an event is emitted outside a transaction
    bus.emit_event(MyEvent())
    # Then the event is handled immediately
    assert called[0], "Events must be handled immediately outside transactions"


def test_nested_transactions_trigger_events_on_parent_commit(
    clear_meta,
    bus: MessageBus,
    transaction_manager: TransactionManager,
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
    transaction_manager.begin()  # parent
    event_1 = MyEvent()
    bus.emit_event(event_1)
    transaction_manager.begin()  # nested
    event_2 = MyEvent()
    bus.emit_event(event_2)
    assert not calls, "Events must be handled on transaction ends"
    transaction_manager.commit()  # commit nested
    assert not calls, "Events must be handled on transaction ends"
    transaction_manager.commit()  # commit parent
    assert calls == [event_1, event_2], "Events must be handled on transaction ends"


def test_nested_transactions_dicards_events_on_rollback(
    clear_meta,
    bus: MessageBus,
    transaction_manager: TransactionManager,
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
    transaction_manager.begin()  # parent
    event_1 = MyEvent()
    bus.emit_event(event_1)
    transaction_manager.begin()  # nested
    event_2 = MyEvent()
    bus.emit_event(event_2)
    transaction_manager.rollback()  # rollback nested
    transaction_manager.commit()  # commit parent
    assert calls == [event_1], "Events must be handled on transaction ends"
