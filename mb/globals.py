import typing as t
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from mb.unit_of_work import UnitOfWork

_uow_context: ContextVar["UnitOfWork"] = ContextVar("mb.uow")


def get_current_uow() -> t.Optional["UnitOfWork"]:
    return _uow_context.get(None)
