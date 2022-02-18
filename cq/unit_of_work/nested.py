import typing as t

from cq.exceptions import UowContextRequired
from cq.unit_of_work.base import UnitOfWork
from cq.unit_of_work.utils.events_collector import DedupeEventsFifo

if t.TYPE_CHECKING:
    from cq.bus.events import Event
    from cq.bus.bus import MessageBus
    from cq.unit_of_work.utils.events_collector import EventsCollector


class NestedUnitOfWork(UnitOfWork):
    """
    Handles events on outermost UOW commit.
    """

    stack: list["Transaction"]
    events_collector_cls: type["EventsCollector"]

    def __init__(
        self,
        bus: "MessageBus",
        events_collector_cls: type["EventsCollector"] = DedupeEventsFifo,
    ):
        super().__init__(bus)
        self.stack = []
        self.events_collector_cls = events_collector_cls

    def _emit_event(self, event: Event) -> None:
        self._validate_context()
        self.stack[-1].queue_event(event)

    def __enter__(self):
        self._begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            self._commit()
        else:
            self._rollback()

    def _begin(self):
        parent = self.stack[-1] if self.stack else None
        transaction = Transaction(self.bus, self.events_collector_cls(), parent)
        self.stack.append(transaction)

    def _commit(self):
        self._end().commit()

    def _rollback(self):
        self._end()

    def _end(self) -> "Transaction":
        self._validate_context()
        return self.stack.pop()

    def _validate_context(self):
        if not self.stack:
            raise UowContextRequired("No transaction in progress")


class Transaction:
    """
    The transaction holds the events emmitted during its lifespan and
    eventually calls the handlers on commit. If the transaction is
    rolled back, their events are also discarded.

    Nested transactions do the same but differ on commit. When committing
    a nested transaction, it just passes its events to the parent transaction
    instead of calling the handlers.
    """

    bus: "MessageBus"
    events: "EventsCollector"
    parent: t.Optional["Transaction"]

    def __init__(
        self,
        bus: "MessageBus",
        events: "EventsCollector",
        parent: "Transaction" = None,
    ):
        self.bus = bus
        self.events = events
        self.parent = parent

    def queue_event(self, event: Event):
        self.events.push(event)

    def queue_event_many(self, events: "EventsCollector"):
        self.events.extend(events)

    def commit(self):
        if self.parent:
            self.parent.queue_event_many(self.events)
        else:
            for event in self.events:
                self.bus._handle_event(event)
