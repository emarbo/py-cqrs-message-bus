class CQError(Exception):
    """
    Root exception
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


# --------------------------------------
# Databases
# --------------------------------------


class InvalidTransactionState(CQError):
    """
    Likely an internal error
    """
