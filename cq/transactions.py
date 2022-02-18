from contextlib import ContextDecorator
import logging
import typing as t
import threading

from cq.events import Event
from cq.exceptions import InvalidTransactionState

if t.TYPE_CHECKING:
    from cq.bus import MessageBus


logger = logging.getLogger()


class TransactionContextManager(ContextDecorator):
    """
    >>> bus = MessageBus()
    >>> with TransactionContextManager(bus):
    ...     # Emitted events are deduplicated
    ...     bus.handle_command(...)
    ... # Events are emitted on context exit
    ... pass
    """

    bus: "MessageBus"

    def __init__(self, bus: "MessageBus"):
        self.bus = bus

    def __enter__(self):
        self.bus.running_context.begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.bus.running_context.rollback()
        else:
            self.bus.running_context.commit()


class RunningContext:

    bus: "MessageBus"
    transaction_stack: list["Transaction"]

    def __init__(self, bus: "MessageBus"):
        self.bus = bus
        self.transaction_stack = []

    def reset(self):
        self.transaction_stack = []

    def emit_event(self, event: Event) -> None:
        if self.transaction_stack:
            self.transaction_stack[-1].queue_event(event)
        else:
            self.bus._handle_event(event)

    def begin(self):
        if self.transaction_stack:
            self.transaction_stack.append(
                Transaction(self.bus, self.transaction_stack[-1])
            )
        else:
            self.transaction_stack.append(Transaction(self.bus))

    def commit(self):
        self._validate_in_transaction()
        transaction = self.transaction_stack.pop()
        transaction.commit()

    def rollback(self):
        self._validate_in_transaction()
        self.transaction_stack.pop()

    def _validate_in_transaction(self):
        if not self.transaction_stack:
            raise InvalidTransactionState("No transaction in progress")


class Transaction:
    """
    A bus transaction.

    The transaction holds the events emmitted during its lifespan and
    eventually calls the handlers on commit. If the transaction is
    rolled back, their events are also discarded.

    Nested transactions do the same but differ on commit. When committing
    a nested transaction, it just passes its events to the parent transaction
    instead of calling the handlers.
    """

    bus: "MessageBus"
    events: "UniqueQueue[Event]"
    parent: t.Optional["Transaction"]

    def __init__(self, bus: "MessageBus", parent: "Transaction" = None):
        self.bus = bus
        self.events = UniqueQueue()
        self.parent = parent

    def queue_event(self, event: Event):
        self.events.push(event)

    def queue_event_many(self, events: t.Iterable[Event]):
        self.events.push_many(events)

    def commit(self):
        if self.parent:
            self.parent.queue_event_many(self.events)
        else:
            for event in self.events:
                self.bus._handle_event(event)


E = t.TypeVar("E")


class UniqueQueue(t.Generic[E]):
    """
    A queue with unique items
    """

    queue: list[E]
    seen: set[E]

    def __init__(self):
        self.queue = []
        self.seen = set()

    def __bool__(self) -> bool:
        return bool(self.queue)

    def __iter__(self) -> t.Iterator[E]:
        return iter(self.queue)

    def push(self, e: E):
        if e not in self.seen:
            self.seen.add(e)
            self.queue.append(e)

    def pop(self) -> E:
        e = self.queue.pop()
        self.seen.remove(e)
        return e

    def push_many(self, elements: t.Iterable[E]):
        for e in elements:
            self.push(e)
