import inspect
import typing as t

from mb.exceptions import CQProgrammingError, DuplicatedCommandHandler
from mb.exceptions import InjectError
from mb.messages import Message
from mb.unit_of_work import UnitOfWork

Args = tuple[t.Any, ...]
Kwargs = dict[str, t.Any]

P = t.ParamSpec("P")
R = t.TypeVar("R")


class PreparedHandler(t.Generic[P, R]):
    handler: t.Callable[P, R]
    arguments: inspect.BoundArguments

    def __init__(self, handler: t.Callable[P, R], message: Message, uow: UnitOfWork):
        self.handler = handler  # type: ignore
        self.arguments = self._prepare_arguments(handler, message, uow)

    def __call__(self) -> R:
        return self.handler(*self.args, **self.kwargs)

    @property
    def args(self) -> Args:
        return self.arguments.args

    @property
    def kwargs(self) -> Kwargs:
        return self.arguments.kwargs

    def _prepare_arguments(
        self,
        handler: t.Callable,
        message: Message,
        uow: UnitOfWork,
    ) -> inspect.BoundArguments:
        """
        Returns the arguments to inject into the handler
        """
        signature = inspect.signature(handler)

        not_defined = object()

        args: list[t.Any] = []
        kwargs: Kwargs = {}
        for name, param in signature.parameters.items():
            value = not_defined
            # try matching by annotation (MUST BE A REAL TYPE, NOT STR)
            if annotation := param.annotation:
                if isinstance(annotation, type):
                    if issubclass(annotation, Message):
                        value = message
                    elif issubclass(annotation, UnitOfWork):
                        value = uow
            # try matching by name
            if value is not_defined:
                if name in ("message", "command", "cmd", "event"):
                    value = message
                elif name in ("uow", "unit_of_work"):
                    value = uow
            # try default
            if value is not_defined:
                if param.default is not inspect.Parameter.empty:
                    value = param.default
            # can't do anything
            if value is not_defined:
                raise InjectError(name, handler)
            # collect
            if param.POSITIONAL_ONLY:
                args.append(value)
            else:
                kwargs[name] = value

        try:
            return signature.bind(*args, **kwargs)
        except TypeError:
            raise CQProgrammingError("Unexpected injection error")
