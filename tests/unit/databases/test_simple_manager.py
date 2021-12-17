from lib.bus import MessageBus
from lib.databases import BasicTransactionManager
from lib.events import Event


# TODO: Use a class-based test case that checks common stuff like connect/close,
# begin/commit/rollback. Then subclass it and reuse for testing both TransactionManager
# subclasses. It may even help with the Django stuff.


def build(bus: MessageBus):
    return BasicTransactionManager(bus)


def test_commit(clear_meta, bus: MessageBus):
    """
    Test commit
    """
    manager = build(bus)
    called = False

    class NewUser(Event):
        pass

    def hander(_: NewUser):
        nonlocal called
        called = True

    # Begin
    manager.begin()
    assert manager.in_transaction
    # Emit an event that should not be called until commit
    bus.emit_event(NewUser())
    assert not called
    # Commit
    manager.commit()
    assert called
    assert not manager.in_transaction


def test_rollback(clear_meta, bus: MessageBus):
    """
    Test commit
    """
    manager = build(bus)
    called = False

    class NewUser(Event):
        pass

    def hander(_: NewUser):
        nonlocal called
        called = True

    # Begin
    manager.begin()
    assert manager.in_transaction
    # Emit an event that should not be called until commit
    bus.emit_event(NewUser())
    assert not called
    # Commit
    manager.rollback()
    assert not called
    assert not manager.in_transaction


def test_many_begin(clear_meta, bus: MessageBus):
    """
    Test multiple begin are allowed
    """
    manager = build(bus)

    # Begin
    manager.begin()
    manager.begin()
    manager.begin()
    assert manager.in_transaction
    manager.commit()
    assert not manager.in_transaction


def test_close(clear_meta, bus: MessageBus):
    """
    Test close doesn't trigger a commit and closes transaction
    """
    manager = build(bus)
    called = False

    class NewUser(Event):
        pass

    def hander(_: NewUser):
        nonlocal called
        called = True

    # Begin
    manager.begin()
    assert manager.in_transaction
    # Emit an event that should not be called until commit
    bus.emit_event(NewUser())
    assert not called
    # Commit
    manager.close()
    assert not called
    assert not manager.in_transaction


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
