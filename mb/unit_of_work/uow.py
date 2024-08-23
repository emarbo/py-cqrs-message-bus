import typing as t
from contextvars import Token

from mb.commands import Command
from mb.events import Event
from mb.exceptions import InvalidMessageError
from mb.exceptions import ProgrammingError
from mb.exceptions import UowContextBrokenError
from mb.exceptions import UowContextRequiredError
from mb.globals import _uow_context
from mb.unit_of_work.utils.events_collector import EventsFifo

if t.TYPE_CHECKING:
    from mb.bus import MessageBus
    from mb.unit_of_work.utils.events_collector import EventsCollector


# TODO: Provide an autocommit mode to be paired with most of the
# database transaction managements. This is specially helpful when playing
# on a python terminal. Besides of that, the autocommit mode is the default
# mode for most of the database connections.


class UnitOfWork:
    """
    Keeps track of the events emitted during a transaction, and handles them on commit.

    Usage::

        >>> bus = MessageBus()
        >>> bus.subscribe_command(...)
        >>> bus.subscribe_event(...)
        >>> uow = UnitOfWork(bus)

        >>> # Initiates a transaction
        ... with uow:
        ...     # Eents are collected at root transaction
        ...     bus.handle_command(...)
        ...     try:
        ...         # Initiates a nested transaction
        ...         with uow:
        ...             # Events are collected at nested transaction
        ...             bus.handle_command(...)
        ...     except Exception:
        ...         # If an exception is raised, the events of the nested transaction
        ...         # are discarded
        ...         pass
        ...     else:
        ...         # Otherwise, the events are added to the root transaction
        ...         pass
        ... # On closing the context, all the collected events are handled

    """

    bus: "MessageBus"

    stack: list["Transaction"]
    _context_tokens: list[Token]

    events_collector_cls: type["EventsCollector"]

    def __init__(
        self,
        bus: "MessageBus",
        events_collector_cls: type["EventsCollector"] = EventsFifo,
    ):
        self.bus = bus

        self.stack = []
        self._context_tokens = []

        self.events_collector_cls = events_collector_cls

    # Transaction management

    def __enter__(self):
        self._context_tokens.append(_uow_context.set(self))

        self._begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        uow = _uow_context.get(None)
        _uow_context.reset(self._context_tokens.pop())
        if uow is not self:
            raise UowContextBrokenError(
                "UoW context missmatch. Did you call __enter__ or __exit__ manually?"
            )

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
        self._ensure_transaction()
        return self.stack.pop()

    def _ensure_transaction(self):
        if not self.stack:
            raise UowContextRequiredError("No transaction in progress")

    # Command events

    def handle_command(self, command: Command) -> t.Any:
        """
        Triggers the command handler. Handler exceptions are propagated

        :raises InvalidMessage: if this isn't an Event
        :raises MissingCommandHandler: if there's no handler configured for the command
        """
        if not isinstance(command, Command):
            raise InvalidMessageError(f"This is not a command: '{command}'")
        return self._handle_command(command)

    def _handle_command(self, command: Command) -> t.Any:
        return self.bus._handle_command(command, self)

    # Event methods

    def emit_event(self, event: Event):
        """
        Collects the event to be handled on commit.

        Handler exceptions are captured and error-logged (e.g., not propagated)

        :raises InvalidMessage: if this isn't an Event
        """
        if not isinstance(event, Event):
            raise InvalidMessageError(f"This is not an event: '{event}'")
        self._emit_event(event)

    def _emit_event(self, event: Event):
        """
        Collect on the current transaction
        """
        self._ensure_transaction()
        self.stack[-1].collect_event(event)

    def _handle_events(self, events: t.Iterable[Event]):
        """
        Called on commit the outermost transaction
        """
        if self.stack:
            raise ProgrammingError("This call should happen outside a transaction")
        for event in events:
            self._handle_event(event)

    def _handle_event(self, event: Event):
        self.bus._handle_event(event, self)


class Transaction:
    """
    The transaction holds the events emmitted during its lifespan and
    eventually calls the handlers on commit. If the transaction is
    rolled back, their events are also discarded.

    Nested transactions do the same but differ on commit. When committing
    a nested transaction, it just passes its events to the parent transaction
    instead of calling the handlers.
    """

    uow: "UnitOfWork"
    events: "EventsCollector"
    parent: t.Optional["Transaction"]

    def __init__(
        self,
        uow: "UnitOfWork",
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
