import logging
import typing as t
import threading

from cq.events import Event
from cq.exceptions import InvalidTransactionState

if t.TYPE_CHECKING:
    from cq.bus import MessageBus


logger = logging.getLogger()


class TransactionManager:

    bus: "MessageBus"

    def __init__(self, bus: "MessageBus"):
        self.bus = bus

    @property
    def in_transaction(self) -> bool:
        raise NotImplementedError()

    def queue_event(self, event: Event):
        raise NotImplementedError()

    def begin(self):
        raise NotImplementedError()

    def commit(self):
        raise NotImplementedError()

    def rollback(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()


class BasicTransactionContext:
    """
    A transaction context for the current connection.
    """

    transaction: t.Optional["Transaction"]

    def __init__(self):
        self.transaction = None

    def __str__(self):
        return f"transaction={self.transaction}"


class BasicTransactionManager(TransactionManager):
    """
    Handles a single transaction. Transactions are thread-local.
    """

    bus: "MessageBus"
    _context_proxy: threading.local

    def __init__(self, bus: "MessageBus"):
        self.bus = bus
        self.bus.transaction_manager = self
        self._context_proxy = threading.local()

    @property
    def context(self) -> "BasicTransactionContext":
        """
        Thread-local context
        """
        try:
            return self._context_proxy.context
        except AttributeError:
            self._context_proxy.context = BasicTransactionContext()
            return self._context_proxy.context

    @property
    def in_transaction(self) -> bool:
        return bool(self.context.transaction)

    def queue_event(self, event: Event) -> None:
        if not self.context.transaction:
            raise InvalidTransactionState("No transaction in progress")
        self.context.transaction.queue_event(event)

    def begin(self):
        if self.context.transaction:
            logger.warning("There is already a transaction in progress")
        else:
            self.context.transaction = Transaction(self.bus)

    def commit(self):
        if not self.context.transaction:
            raise InvalidTransactionState("No transaction in progress")
        transaction = self.context.transaction
        self.context.transaction = None
        transaction.commit()

    def rollback(self):
        if not self.context.transaction:
            raise InvalidTransactionState("No transaction in progress")
        self.context.transaction = None

    def close(self):
        self.context.transaction = None


class SqlTransactionContext:
    """
    A SQL transaction context for the current connection.
    """

    stack: list["Transaction"]
    connected: bool
    autocommit: bool

    def __init__(self):
        self.stack = []
        self.connected = False
        self.autocommit = False  # PEP 249 default

    def __str__(self):
        return (
            f"connected={self.connected:<1}, "
            f"autocommit={self.autocommit:<1}, "
            f"stack={len(self.stack)}"
        )


class SqlTransactionManager(TransactionManager):
    """
    A SQL transaction manager. Transactions are thread-local.
    """

    bus: "MessageBus"
    _context_proxy: threading.local

    def __init__(self, bus: "MessageBus"):
        self.bus = bus
        self.bus.transaction_manager = self
        # This might support contextvars (asyncio) in the future
        self._context_proxy = threading.local()

    @property
    def context(self) -> "SqlTransactionContext":
        """
        Thread-local context
        """
        try:
            return self._context_proxy.context
        except AttributeError:
            self._context_proxy.context = SqlTransactionContext()
            return self._context_proxy.context

    @property
    def in_transaction(self) -> bool:
        return bool(self.context.stack)

    def queue_event(self, event: Event) -> None:
        self._validate_in_transaction()
        self.context.stack[-1].queue_event(event)

    def connect(self):
        if self.context.connected:
            return
        self.context.connected = True
        self.context.stack = []
        # Same reasons as the comments in :method:`set_autocommit`.
        if not self.context.autocommit:
            self.begin()

    def close(self):
        self.context.connected = False
        self.context.stack = []

    def set_autocommit(self, autocommit):
        transition = (self.context.autocommit, autocommit)
        self.context.autocommit = autocommit
        # If autocommit is disabled and no transaction was active,
        # the database will automatically open a transaction (BEGIN)
        # after receiving the first statement. To emulate this behavior
        # we implicitly open a transaction if the conditions are met.
        #
        # SQLite doesn't open a transaction implicitly but we dont
        # care if begin() is called twice.
        if self.context.connected and not self.in_transaction and transition == (1, 0):
            self.begin()

    def begin(self):
        self._validate_connected()
        if self.in_transaction:
            # Most databases issue a warning but allow calling BEGIN twice
            logger.warning("There is already a transaction in progress")
        else:
            self.context.stack.append(Transaction(self.bus))

    def commit(self):
        self._validate_in_transaction()
        stack = self._end()
        for transaction in reversed(stack):
            transaction.commit()

    def rollback(self):
        self._validate_in_transaction()
        self._end()

    def _end(self) -> list["Transaction"]:
        stack = self.context.stack
        self.context.stack = []
        # Same reasons as the comments in :method:`set_autocommit`.
        if not self.context.autocommit:
            self.begin()
        return stack

    def begin_savepoint(self, uid: str = None):
        self._validate_in_transaction()
        self.context.stack.append(Transaction(self.bus, self.context.stack[-1], uid))

    def commit_savepoint(self, uid: str = None):
        """
        Commit all SAVEPOINT up to :param:`uid`
        """
        self._validate_in_transaction()
        savepoint = self._get_savepoint(uid)
        if not savepoint:
            logger.warning(f"Commit savepoint not found: '{uid}'")
            return
        # Commit up to the savepoint
        while True:
            transaction = self.context.stack.pop()
            transaction.commit()
            if transaction == savepoint:
                return

    def rollback_savepoint(self, uid: str = None):
        """
        Rollback all SAVEPOINT up to :param:`uid`
        """
        self._validate_in_transaction()
        savepoint = self._get_savepoint(uid)
        if not savepoint:
            logger.warning(f"Rollback savepoint not found: '{uid}'")
            return
        # Rollback up to the savepoint but keep it in the stack
        while True:
            transaction = self.context.stack[-1]
            transaction.rollback()
            if transaction == savepoint:
                return
            self.context.stack.pop()

    def _get_savepoint(self, uid: str = None) -> t.Optional["Transaction"]:
        # SQL SAVEPOINTS should be unique so we can safely iterate in this order
        for transaction in self.context.stack:
            if transaction.uid == uid:
                return transaction

    def _validate_connected(self):
        if not self.context.connected:
            raise InvalidTransactionState("Not connected")

    def _validate_in_transaction(self):
        self._validate_connected()
        if not self.in_transaction:
            raise InvalidTransactionState("No transaction in progress")


class Transaction:
    """
    A database transaction.

    The transaction holds the events emmitted during its lifespan and
    eventually calls the handlers on commit. If the transaction is
    rolled back, their events are also discarded.

    Nested transactions do the same but differ on commit. When committing
    a nested transaction, it just passes its events to the parent transaction
    instead of calling the handlers.

    Transactions must be pushed and popped by a manager that works as a
    bridge between the Bus and the database connection in use.
    """

    # CQ management
    bus: "MessageBus"
    events: list[Event]

    # Transaction management
    parent: t.Optional["Transaction"]
    uid: t.Optional[str]

    def __init__(
        self,
        bus: "MessageBus",
        parent: "Transaction" = None,
        uid: str = None,
    ):
        """
        :param uid: Optional identifier
        """
        self.bus = bus
        self.events = []

        self.parent = parent
        self.uid = uid

    def queue_event(self, event: Event):
        self.events.append(event)

    def queue_event_many(self, events: list[Event]):
        self.events.extend(events)

    def commit(self):
        if self.parent:
            self.parent.queue_event_many(self.events)
        else:
            for event in self.events:
                self.bus._handle_event(event)

    def rollback(self):
        self.events = []
