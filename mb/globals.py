import typing as t
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from mb.commands import Command
    from mb.events import Event
    from mb.unit_of_work import UnitOfWork


_uow_ctxvar: ContextVar["UnitOfWork"] = ContextVar("mb.uow")


@t.overload
def get_current_uow() -> "UnitOfWork":
    ...


@t.overload
def get_current_uow(raise_if_missing: t.Literal[True]) -> "UnitOfWork":
    ...


@t.overload
def get_current_uow(raise_if_missing: t.Literal[False]) -> t.Optional["UnitOfWork"]:
    ...


def get_current_uow(raise_if_missing: bool = True):
    uow = _uow_ctxvar.get(None)

    if not uow and raise_if_missing:
        raise LookupError("Missing UoW transaction")
    return uow


def emit_event(event: "Event"):
    uow = get_current_uow()
    uow.emit_event(event)


def handle_command(command: "Command"):
    uow = get_current_uow()
    return uow.handle_command(command)
