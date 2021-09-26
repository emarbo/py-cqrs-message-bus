class CQError(Exception):
    """
    Root exception
    """


class ConfigError(CQError):
    """
    General configuration error
    """


# --------------------------------------
# Errors on Message declarations
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
# Errors on handlers
# --------------------------------------


class DuplicatedCommandHandler(ConfigError):
    """
    A Command can have only one handler
    """


class MissingCommandHandler(ConfigError, RuntimeError):
    """
    No handler found for a Command
    """


# --------------------------------------
# Errors on handlers
# --------------------------------------


class InvalidMessageType(CQError, TypeError):
    """
    The Bus only handles Message types
    """
