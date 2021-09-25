class CQError(Exception):
    pass


class ConfigError(CQError):
    pass


class DuplicatedCommandHandler(ConfigError):
    pass


class MissingCommandHandler(ConfigError, RuntimeError):
    pass


class InvalidMessageType(CQError, TypeError):
    pass
