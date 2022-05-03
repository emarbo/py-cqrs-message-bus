import typing as t

from mb.exceptions import CQProgrammingError
from mb.exceptions import UowContextRequired
from mb.unit_of_work.base import UnitOfWork
from mb.unit_of_work.utils.events_collector import DedupeEventsFifo

if t.TYPE_CHECKING:
    from mb.bus import MessageBus
    from mb.events import Event
    from mb.unit_of_work.utils.events_collector import EventsCollector


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

    # Transaction methods

    def __enter__(self):
        self._begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            self._commit()
        else:
            self._rollback()

    def _begin(self):
        transaction = Transaction(
            self,
            self.events_collector_cls(),
            self.stack[-1] if self.stack else None,
        )
        self.stack.append(transaction)

    def _commit(self):
        self._end().commit()

    def _rollback(self):
        self._end().rollback()

    def _end(self) -> "Transaction":
        self._ensure_context()
        return self.stack.pop()

    def _ensure_context(self):
        if not self.stack:
            raise UowContextRequired("No transaction in progress")

    # Events methods

    def _emit_event(self, event: "Event"):
        """
        Collect on the current transaction
        """
        self._ensure_context()
        self.stack[-1].collect_event(event)

    def _handle_events(self, events: t.Iterable["Event"]):
        """
        Called on commit the outermost transaction
        """
        if self.stack:
            raise CQProgrammingError("This call should happen outside the context")
        for event in events:
            self._handle_event(event)


class Transaction:
    """
    The transaction holds the events emmitted during its lifespan and
    eventually calls the handlers on commit. If the transaction is
    rolled back, their events are also discarded.

    Nested transactions do the same but differ on commit. When committing
    a nested transaction, it just passes its events to the parent transaction
    instead of calling the handlers.
    """

    uow: "NestedUnitOfWork"
    events: "EventsCollector"
    parent: t.Optional["Transaction"]

    def __init__(
        self,
        uow: "NestedUnitOfWork",
        events: "EventsCollector",
        parent: "Transaction" = None,
    ):
        self.uow = uow
        self.events = events
        self.parent = parent

    def commit(self):
        if self.parent:
            self.parent.collect_event_many(self.events)
        else:
            self.uow._handle_events(self.events)

    def rollback(self):
        self.events.clear()

    def collect_event(self, event: "Event"):
        self.events.push(event)

    def collect_event_many(self, events: "EventsCollector"):
        self.events.extend(events)
