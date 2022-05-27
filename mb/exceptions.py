import typing as t

if t.TYPE_CHECKING:
    from mb.commands import Command

# TODO: Sufix all errors with Error (and remove some prefixes?)
# TODO: Move some message str to the __init__ of these exceptions

# --------------------------------------
# Base exceptions
# --------------------------------------


class CQBaseError(BaseException):
    """
    Uncatchable error
    """


class CQProgrammingError(CQBaseError, RuntimeError):
    """
    Uncatchable error. Code violates some invariant
    """


class CQError(Exception):
    """
    Library root exception
    """


class ConfigError(CQError):
    """
    General configuration error
    """


# --------------------------------------
# Message definitions
# --------------------------------------


class InvalidMessageName(ConfigError, TypeError):
    """
    The Message.NAME must be an string
    """


class DuplicatedMessageName(ConfigError, TypeError):
    """
    Two messages have the same NAME
    """


# --------------------------------------
# Handler configuration
# --------------------------------------


class DuplicatedCommandHandler(ConfigError):
    """
    A Command can have only one handler
    """


class MissingCommandHandler(ConfigError, RuntimeError):
    """
    No handler found for a Command
    """

    def __init__(self, command: "Command"):
        self.message = f"Missing handler for command: '{command}'"
        self.command = command
        super().__init__(self.message, self.command)


class InvalidMessageType(ConfigError, TypeError):
    """
    The Bus only handles Messages
    """


# --------------------------------------
# Handling messages
# --------------------------------------


class InvalidMessage(CQError, TypeError):
    """
    The Bus only handles Messages
    """


class InjectError(CQError, RuntimeError):
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
# Databases
# --------------------------------------


class InvalidTransactionState(CQError):
    """
    Likely an internal error
    """


# --------------------------------------
# Unit of Work
# --------------------------------------


class UowContextRequired(CQError):
    """
    Code is using the UnitOfWork outside the context or
    the begin/commit/rollback calls are unpaired.

        >>> uow = UnitOfWork(bus)
        >>> with uow:
        ...     uow.emit_event(event)  # Good
        ... uow.emit_event(event)  # Bad
    """
