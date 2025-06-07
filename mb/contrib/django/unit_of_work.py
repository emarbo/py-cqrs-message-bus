import typing as t
from contextlib import contextmanager

from django.db.transaction import atomic

from mb.unit_of_work import UnitOfWork

Using = t.Union[list[str], str, None]


class DjangoUnitOfWork(UnitOfWork):
    """
    Provides a handy `atomic` to bind the message bus and database transactions.

    No support provided for multiple connections or databases yet.

    ---------------------------------
    UoW transactions VS Django atomic
    ---------------------------------

    Note that the events are handled when the outermost UoW transaction is closed,
    regardless of the database transaction state. Therefore, it's highly recommended
    that your outermost Bus TX wraps the outermost Database TX, otherwise your events
    will be handled before the performing the Database Commit.

    BAD:

        >>> uow = DjangoUnitOfWork(bus)
        >>> with atomic():
        ...     with uow:
        ...         user.create()
        ...         uow.emit_event(UserCreated(user.id))  # queued
        ...     # UoW/Bus handles the events here (e.g., sending an email)
        ...     pass
        ... # Django commits but the database raises an error!!
        ... # You have sent an email to a user that was never created (⩾﹏⩽)
        ... pass

    GOOD:

        >>> uow = DjangoUnitOfWork(bus)
        >>> with uow:
        ...     with atomic():
        ...         user.save()
        ...         uow.emit_event(UserCreated(user.id))  # queued
        ... # Django commits the database and if there aren't errors
        ... # the UoW/Bus handles the events just before
        ... pass

    GOOD (shorter):

        >>> uow = DjangoUnitOfWork(bus)
        >>> with uow.atomic():
        ...     user.save()
        ...     uow.emit_event(UserCreated(user.id))  # queued

    -------------------------------------------------
    Savepoint rollbacks and other undesired scenarios
    -------------------------------------------------

    The following scenario is not supported yet:

        >>> uow = DjangoUnitOfWork(bus)
        >>> with uow.atomic():
        >>>     connection = get_connection()
        >>>     savepoint_id = connection.savepoint_ids[-1]
        >>>     # UoW collects events of the following function
        >>>     do_stuff_A()
        >>>     # Rollback changes to savepoint (the savepoint is still there)
        >>>     connection.savepoint_rollback(savepoint_id)
        >>>     # UoW collects events of the following function
        >>>     do_stuff_B()

    Despite the do_stuff_A changes were discarded, their events were emitted and
    handled by the bus. Although this scenario may be easy to cover, we are limiting
    flexibility on purpose to keep the code and uses simple:

        - Wrap all your atomic with a UoW context

    What happens with `atomic` blocks of third party applications? Well, since
    Django does not provide a rollback hook (e.g., signal) the only way to provide
    a solution is patching the Atomic class. We had a working implementation of
    this but we aren't sure this is the reasonable way to address the issue.

        - So, third party (rolled back) `atomic` blocks may cause issues.

    Other scenarios that may cause issues are:

        - Commiting or rolling back to a previous savepoint (not the last)
        - Using autocommit OFF
        - Closing and reopening the connection amidst an UoW transaction

    If you never thought about this issues before, then you don't need to worry
    about them. Code using autocommit OFF or rolling back to a concrete
    savepoint ID is likely an sysadmin script performing schema changes or
    doing something really, really, really special.

    We, as developers, usually think about a transaction as a context block.
    """

    @contextmanager
    def atomic(self, using=None):
        with self:
            with atomic(using=using):
                yield
