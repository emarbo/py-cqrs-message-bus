import typing as t
import importlib

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.transaction import Atomic
from django.db.transaction import get_connection

from cq.bus import MessageBus
from cq.databases import SqlTransactionManager
from cq.exceptions import ConfigError


#
# XXX: There's no feasable implementation that supports multiple databases.
#
# The `bus.emit_event` must be database/framework agnostic. If we were mixing
# multiple databases (e.g., 'default', 'extra'), how could we know which
# SqlTransactionManager.context should be used? The deepest one? Or should be
# the 'default' one?
#
# As there isn't a right response here... I think that is better to make
# the MessageBus completely agnostic of the database replacing the concept of
# the transaction_manager by something else more abstract.
#
# Something like an EventsContext or a BusTransaction makes more sense to me.
# It's quite similar to what we have but lets the user handle this less
# magically.
#


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

    def __init__(self, settings: dict, *a, **kw):
        super().__init__(settings, *a, **kw)

        if not getattr(Atomic, "cq_patched", False):
            raise CqbusDjangoConfigError(
                "Atomic is not patched. "
                "Call patch_django_atomic before using this mixin. "
                "Preferrably at the __init__.py of your root app package."
            )

        self.cq_bus = None
        self.cq_transaction_manager = None
        self.cq_exiting_atomic = False
        self.cq_run_after_commit_hook_on_atomic_exit = False

        bus_opt = settings.get("MESSAGE_BUS")
        if bus_opt:
            bus = load_bus(bus_opt)
            self.bind_cqbus(bus)

    def bind_cqbus(self, bus: "MessageBus"):
        # The manager is reused by all connections
        if transaction_manager := bus.running_context:
            if not isinstance(transaction_manager, SqlTransactionManager):
                raise CqbusDjangoConfigError(
                    "The bus transaction_manager is not a SqlTransactionManager"
                )
        else:
            transaction_manager = SqlTransactionManager(bus)
            bus.running_context = transaction_manager

        self.cq_bus = bus
        self.cq_transaction_manager = transaction_manager
        # Track the current state
        self.cq_transaction_manager.set_autocommit(self.autocommit)
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


def load_bus(bus: t.Any) -> MessageBus:
    """
    Load the DATABASES->OPTIONS->MESSAGE_BUS
    """
    if isinstance(bus, MessageBus):
        return bus

    if isinstance(bus, str):
        bus = import_bus(bus)
    if not isinstance(bus, MessageBus):
        raise CqbusDjangoConfigError(
            "The DATABASES->MESSAGE_BUS is not a MessageBus. "
            f"Found type: {type(bus)}"
        )
    return bus


def import_bus(path: str):
    """
    Import the bus:
        >>> import_bus("app.busmodule:mybus")
        ...
    """
    if path.count(":") != 1:
        raise CqbusDjangoConfigError(
            "Invalid DATABASES->MESSAGE_BUS string format. "
            "Expected: <module_path>:<module_var> (e.g.: 'app.busmodule:mybus'). "
            f"Found: '{path}'."
        )
    module_name, variable_name = path.split(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        # The module_name exists but another ImportError araised during the import
        if e.name != module_name:
            raise
        raise CqbusDjangoConfigError(
            f"Cannot import DATABASES->MESSAGE_BUS module: '{module_name}'."
        ) from e
    try:
        return getattr(module, variable_name)
    except AttributeError:
        raise CqbusDjangoConfigError(
            f"Cannot find DATABASES->MESSAGE_BUS variable '{variable_name}' "
            f"in module '{module_name}'."
        )
