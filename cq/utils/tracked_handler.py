import functools
import typing as t

from cq.bus.commands import Command
from cq.bus.events import Event
from cq.bus.messages import Message
from cq.unit_of_work.base import UnitOfWork

UOW = t.TypeVar("UOW", bound=UnitOfWork)
M = t.TypeVar("M", bound=Message)
C = t.TypeVar("C", bound=Command)
E = t.TypeVar("E", bound=Event)
R = t.TypeVar("R")


class TrackedHandler(t.Protocol[M, R]):
    calls: list[M]
    __call__: t.Callable[["TrackedHandler", M, UOW], R]


def tracked_handler(func: t.Callable[[M, UOW], R]) -> TrackedHandler[M, R]:
    """
    Tracks the calls to a handler in the :attr:`calls`.
    """

    @functools.wraps(func)
    def wrapper(m: M, uow: UOW) -> R:
        wrapper.calls.append(m)  # type:ignore
        return func(m, uow)

    wrapper.calls = []  # type:ignore
    return wrapper  # type:ignore
