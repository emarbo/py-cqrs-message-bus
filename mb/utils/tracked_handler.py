import functools
from itertools import chain
import typing as t

from mb.messages import Message

P = t.ParamSpec("P")
R = t.TypeVar("R")
M = t.TypeVar("M", bound=Message | None)


class TrackedHandler(t.Protocol[P, R, M]):
    calls: list[M]
    __call__: t.Callable[P, R]


def tracked_handler(func: t.Callable[P, R]) -> TrackedHandler[P, R, M]:
    """
    Tracks the calls to a handler in the :attr:`calls`.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> R:
        for argument in chain(args, kwargs.values()):
            if isinstance(argument, Message):
                wrapper.calls.append(argument)  # type:ignore
                break
        else:
            wrapper.calls.append(None)  # type:ignore
        return func(*args, **kwargs)

    wrapper.calls = []  # type:ignore
    return wrapper  # type:ignore
