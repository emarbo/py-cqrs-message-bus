import typing as t
import functools

from lib.messages import Message
from lib.commands import Command
from lib.events import Event


M = t.TypeVar("M", bound=Message)
C = t.TypeVar("C", bound=Command)
E = t.TypeVar("E", bound=Event)
R = t.TypeVar("R")


class TrackedHandler(t.Protocol[M, R]):
    calls: list[M]
    __call__: t.Callable[["TrackedHandler", M], R]


def tracked_handler(func: t.Callable[[M], R]) -> TrackedHandler[M, R]:
    """
    Tracks the calls to a handler in the :attr:`calls`.
    """

    @functools.wraps(func)
    def wrapper(m: M) -> R:
        wrapper.calls.append(m)  # type:ignore
        return func(m)

    wrapper.calls = []  # type:ignore
    return wrapper  # type:ignore
