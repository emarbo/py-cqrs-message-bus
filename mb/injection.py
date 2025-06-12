import inspect
import typing as t

from mb.exceptions import InjectionError
from mb.exceptions import ProgrammingError
from mb.messages import Message

if t.TYPE_CHECKING:
    from mb.unit_of_work import UnitOfWork

Args = tuple[t.Any, ...]
Kwargs = dict[str, t.Any]

P = t.ParamSpec("P")
R = t.TypeVar("R")


# TODO: The injection should be done beforehand at handler registration. This way
# (1) we detect configuration errors at startup and (2) there's no need to analyze
# signature on each call.


class PreparedHandler(t.Generic[P, R]):
    """
    Injects the message and uow to the handler.
    """

    handler: t.Callable[P, R]
    arguments: inspect.BoundArguments

    def __init__(self, handler: t.Callable[P, R], message: Message, uow: "UnitOfWork"):
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
        uow: "UnitOfWork",
    ) -> inspect.BoundArguments:
        """
        Returns the arguments to inject into the handler
        """
        from mb.unit_of_work import UnitOfWork

        signature = inspect.signature(handler)

        not_defined = object()

        args: list[t.Any] = []
        kwargs: Kwargs = {}

        for n, (name, param) in enumerate(signature.parameters.items()):
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

            # try default value
            if value is not_defined:
                if param.default is not inspect.Parameter.empty:
                    value = param.default

            # rule for untyped positional arguments (message, uow)
            # that do not use common names above
            if value is not_defined:
                if param.POSITIONAL_ONLY or param.POSITIONAL_OR_KEYWORD:
                    if n == 0:
                        value = message
                    elif n == 1:
                        value = uow

            # can't do anything
            if value is not_defined:
                raise InjectionError(name, handler)

            # collect
            if param.POSITIONAL_ONLY:
                args.append(value)
            else:
                kwargs[name] = value

        try:
            return signature.bind(*args, **kwargs)
        except TypeError:
            raise ProgrammingError("Unexpected injection error")
