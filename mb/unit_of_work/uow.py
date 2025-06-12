import logging
import typing as t
from contextlib import contextmanager
from contextvars import Token

from mb.commands import Command
from mb.events import Event
from mb.exceptions import InvalidMessageError
from mb.exceptions import ProgrammingError
from mb.exceptions import UowContextError
from mb.exceptions import UowTransactionError
from mb.globals import _uow_ctxvar
from mb.injection import PreparedHandler
from mb.unit_of_work.utils.events_collector import EventsFifo

if t.TYPE_CHECKING:
    from mb.bus import MessageBus
    from mb.unit_of_work.utils.events_collector import EventsCollector

logger = logging.getLogger(__name__)


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
    autocommit: bool
    _ctxvar_tokens: list[Token]

    events_collector_cls: type["EventsCollector"]

    def __init__(
        self,
        bus: "MessageBus",
        autocommit=True,
        events_collector_cls: type["EventsCollector"] = EventsFifo,
    ):
        self.bus = bus

        self.stack = []
        self.autocommit = autocommit
        self._ctxvar_tokens = []

        self.events_collector_cls = events_collector_cls

    @contextmanager
    def register_globally(self):
        """
        Makes this UoW globally available using the :func:`get_current_uow`
        """
        self._begin_global()
        try:
            yield
        finally:
            self._end_global()

    def _begin_global(self):
        self._ctxvar_tokens.append(_uow_ctxvar.set(self))

    def _end_global(self):
        uow = _uow_ctxvar.get(None)
        _uow_ctxvar.reset(self._ctxvar_tokens.pop())
        if uow is not self:
            raise UowContextError(
                "The global UoW does not match the uow being closed. "
                "This may happen when you open and close a transaction in a "
                "different thread or async context. Transactions must be handled "
                "by a single thread or async context."
            )

    def __enter__(self):
        """
        Enter global scope and begin transaction
        """
        self._begin_global()
        self._begin_transaction()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        End global scope and commit/rollback transaction
        """
        self._end_global()
        if not exc_type:
            self._commit()
        else:
            self._rollback()

    def _begin_transaction(self):
        transaction = Transaction(
            self,
            self.events_collector_cls(),
            self.stack[-1] if self.stack else None,
        )
        self.stack.append(transaction)

    def _end_transaction(self) -> "Transaction":
        if not self.stack:
            raise UowTransactionError(
                "No transaction in progress. "
                "Did you call __enter__ or __exit__ manually?"
            )
        return self.stack.pop()

    def _commit(self):
        transaction = self._end_transaction()
        transaction.commit()

        if not self.stack:
            self._handle_events(transaction.events)

    def _rollback(self):
        transaction = self._end_transaction()
        transaction.rollback()

        # Even if the outermost transaction was rolled back, they
        # may contain persistent events to be handled.
        if not self.stack:
            self._handle_events(transaction.events)

    # Command methods

    def handle_command(self, command: Command) -> t.Any:
        """
        Triggers the command handler. Handler exceptions are propagated

        :raises InvalidMessage: if this isn't a Command
        :raises MissingCommandHandler: if there's no handler configured for the command
        """
        handler = self.bus.get_command_handler(command)

        logger.debug(f"Handling command '{command.NAME}': calling '{handler}'")
        prepared = PreparedHandler(handler, command, self)
        return prepared()

    # Event methods

    def emit_event(self, event: Event):
        """
        Collects the event to be handled on commit.

        Handler exceptions are captured and error-logged (e.g., not propagated)

        :raises InvalidMessage: if this isn't an Event
        """
        if not isinstance(event, Event):
            raise InvalidMessageError(f"This is not an event: '{event}'")

        if self.stack:
            # Inside a transaction block
            self.stack[-1].collect_event(event)

        else:
            # Outside a transaction block
            if self.autocommit:
                self._handle_events([event])
            else:
                raise UowTransactionError(
                    "No transaction in progress and autocommit is OFF"
                )

    def _handle_events(self, events: t.Iterable[Event]):
        """
        Called on commit the outermost transaction
        """
        if self.stack:
            raise ProgrammingError("This call should happen outside a transaction")

        for event in events:
            handlers = self.bus.get_event_handlers(event)
            for handler in handlers:
                logger.debug(f"Handling event '{event.NAME}': {len(handlers)} handlers")
                prepared = PreparedHandler(handler, event, self)
                try:
                    prepared()
                except Exception:
                    logger.exception(f"Exception handling event '{event.NAME}'")


class Transaction:
    """
    The transaction holds the events emmitted during its lifespan.

    The transactions are always managed by the unit of work that creates and removes
    them from the current stack as required. When events are emitted, the unit of work
    stores them in the transaction in progress.

    When a nested transaction is committed or rolled back, it passes the collected
    events to their parent. Even rolled back transactions may pass events if they're
    marked as persistent.

    Once the outermost transaction is committed or rolled back, the unit of work will
    handle the events that reamin in the transaction.
    """

    uow: "UnitOfWork"
    events: "EventsCollector"
    parent: t.Optional["Transaction"]

    def __init__(
        self,
        uow: "UnitOfWork",
        events: "EventsCollector",
        parent: t.Optional["Transaction"] = None,
    ):
        self.uow = uow
        self.events = events
        self.parent = parent

    def commit(self):
        if self.parent:
            self.parent.collect_event_many(self.events)

    def rollback(self):
        self.events.clear()

    def collect_event(self, event: "Event"):
        self.events.push(event)

    def collect_event_many(self, events: "EventsCollector"):
        self.events.extend(events)
