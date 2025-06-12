import typing as t

if t.TYPE_CHECKING:
    from mb.commands import Command


# --------------------------------------
# Base exceptions
# --------------------------------------


class ProgrammingError(BaseException):
    """
    Uncatchable error. Code violates some invariant
    """


class MbError(Exception):
    """
    Library root exception
    """


class ConfigError(MbError):
    """
    General configuration error
    """


# --------------------------------------
# Message definitions
# --------------------------------------


class InvalidNameError(ConfigError, TypeError):
    """
    The Message.NAME must be an string
    """


class DuplicatedNameError(ConfigError, TypeError):
    """
    Two messages have the same NAME
    """


# --------------------------------------
# Handler configuration
# --------------------------------------


class DuplicatedHandlerError(ConfigError):
    """
    A Command can have only one handler
    """


class MissingHandlerError(ConfigError, LookupError):
    """
    No handler found for a Command
    """

    def __init__(self, command: "Command"):
        self.message = f"Missing handler for command: '{command}'"
        self.command = command
        super().__init__(self.message, self.command)


class MessageTypeError(ConfigError, TypeError):
    """
    The Bus only handles Messages
    """


# --------------------------------------
# Handling messages
# --------------------------------------


class InvalidMessageError(MbError, TypeError):
    """
    The Bus only handles Messages
    """


class InjectionError(MbError, RuntimeError):
    """
    The argument couldn't be injected
    """

    def __init__(self, argument: str, handler: t.Callable):
        message = (
            "Cannot inject the {argument} argument in handler '{handler}'. "
            "No candidates found by name or annotation."
        )
        super().__init__(message, argument, handler)
        self.message = message
        self.argument = argument
        self.handler = handler


# --------------------------------------
# Unit of Work
# --------------------------------------


class UowTransactionError(MbError):
    """
    Code is using the UnitOfWork outside a transaction or
    the begin/commit/rollback calls are unpaired.

        >>> uow = UnitOfWork(bus)
        >>> with uow:
        ...     uow.emit_event(event)  # Good
        ... uow.emit_event(event)  # Bad
    """


class UowContextError(MbError):
    """
    UoW contexts are like parenthesis, they might be nested but
    pairs must match. This error is raised when pairs doesn't match.
    """
