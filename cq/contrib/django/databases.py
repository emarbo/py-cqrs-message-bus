import typing as t

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.transaction import Atomic
from django.db.transaction import get_connection

from cq.bus import MessageBus
from cq.databases import SqlTransactionManager
from cq.exceptions import ConfigError


class CqbusDjangoConfigError(ConfigError):
    pass


class CqbusDjangoBindingError(ConfigError):
    pass


class CqbusDjangoTransactionBridge(BaseDatabaseWrapper):
    """
    Link Django database transactions to the SqlTransactionManager
    """

    cq_bus: t.Optional[MessageBus]
    cq_transaction_manager: t.Optional[SqlTransactionManager]
    cq_exiting_atomic: bool
    cq_run_after_commit_hook_on_atomic_exit: bool

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

        if not getattr(Atomic, "cq_patched", False):
            raise CqbusDjangoConfigError(
                "Atomic is not patched. "
                "Call patch_django_atomic before using this mixin"
            )

        self.cq_bus = None
        self.cq_transaction_manager = None
        self.cq_exiting_atomic = False
        self.cq_run_after_commit_hook_on_atomic_exit = False

    def bind_cqbus(self, bus: "MessageBus"):
        # The transaction manager now tread-local as
        self.cq_bus = bus
        self.cq_transaction_manager = SqlTransactionManager(bus)
        self.cq_transaction_manager.set_autocommit(self.autocommit)
        # Track the current state
        if self.connection:
            self.cq_transaction_manager.connect()
            for sid in self.savepoint_ids:
                if sid is not None:  # Discard faked savepoints
                    self.cq_transaction_manager.begin_savepoint(sid)

    def set_autocommit(self, autocommit: bool, **kw):
        super().set_autocommit(autocommit, **kw)
        if self.cq_transaction_manager:
            self.cq_transaction_manager.set_autocommit(autocommit)

    def connect(self):
        super().connect()
        if self.cq_transaction_manager:
            self.cq_transaction_manager.connect()

    def commit(self):
        if not self.cq_transaction_manager:
            super().commit()
            return

        # Preventively, disable this. See comments bellow
        self.cq_run_after_commit_hook_on_atomic_exit = False
        super().commit()
        # We could call :method:`after_commit_hook` here if it wasn't for
        # the Atomic management of the internal variables. When Atomic calls
        # this :method:`commit` it hasn't restored the internal state yet so
        # it isn't ready to open new transactions so we shouldn't trigger
        # the after commit hook (because trying to start a new transaction
        # would be a mess).
        if not self.cq_exiting_atomic:
            # This `commit()` is called outside an Atomic because Django doesn't
            # allow calling `commit()` inside it (raises error). There's no
            # problem in calling the hooks just now
            self.after_commit_hook()
        else:
            # This is the regular Django case: we are inside an Atomic block
            # (precisely, in the Atomic.__exit__) and we need to wait until the
            # end of __exit__ to ensure the internal `self` state is consistent
            # and ready to start new transactions.
            #
            # When used in regular AUTOCOMMIT on, the Atomic.__enter__ had turned
            # it off and it's still off at this point. It will be turned on again
            # at the end of the Atomic.__exit__
            #
            # When used in the not recommended AUTOCOMMIT off, we still need to
            # wait the end of Atomic.__exit__ because the :attr:`in_atomic_block`
            # still needs to be restored.
            self.cq_run_after_commit_hook_on_atomic_exit = True

    def after_commit_hook(self):
        """
        This hook is called after every successful commit.
        """
        self.cq_run_after_commit_hook_on_atomic_exit = False
        self.cq_transaction_manager.commit()

    def rollback(self):
        super().rollback()
        if self.cq_transaction_manager:
            self.cq_transaction_manager.rollback()

    def close(self):
        super().close()
        if self.cq_transaction_manager:
            self.cq_transaction_manager.close()

    def savepoint(self) -> str:
        sid = super().savepoint()
        if self.cq_transaction_manager and self._savepoint_allowed():
            self.cq_transaction_manager.begin_savepoint(sid)
        return sid

    def savepoint_commit(self, sid):
        super().savepoint_commit(sid)
        if self.cq_transaction_manager and self._savepoint_allowed():
            self.cq_transaction_manager.commit_savepoint(sid)

    def savepoint_rollback(self, sid):
        super().savepoint_rollback(sid)
        if self.cq_transaction_manager and self._savepoint_allowed():
            self.cq_transaction_manager.rollback_savepoint(sid)


def patch_django_atomic():
    """
    Enables real "after commit" hooks when working with the
    CqbusDjangoTransactionBridge mixin.
    """
    # The Atomic is a private API but I didn't find any other solution
    patched = getattr(Atomic, "cq_patched", False)
    if patched:
        return

    Atomic.cq_patched = True
    Atomic.__original_exit__ = Atomic.__exit__

    def __patched_exit__(self, exc_type, exc_value, traceback):
        connection: BaseDatabaseWrapper = get_connection(self.using)

        # Not of our business
        if not isinstance(connection, CqbusDjangoTransactionBridge):
            self.__original_exit__(self)
            return

        # See the comments in `CqbusDjangoTransactionBridge.commit`
        connection: CqbusDjangoTransactionBridge
        # Flag the state
        connection.cq_exiting_atomic = True
        self.__original_exit__(exc_type, exc_value, traceback)
        connection.cq_exiting_atomic = False
        # Launch hook if needed
        if connection.cq_run_after_commit_hook_on_atomic_exit:
            connection.after_commit_hook()

    Atomic.__exit__ = __patched_exit__


def unpatch_django_atomic():
    """
    For testing purposes? Have in mind that patches aren't thread-local
    """
    patched = getattr(Atomic, "cq_patched", False)
    if not patched:
        return

    Atomic.__exit__ = Atomic.__original_exit__
