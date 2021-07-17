import typing as t
from lib.messages import MessageType
from lib.messages import Message


# Command handlers may return a result
CommandHandler = t.Callable[["Command"], t.Any]


class CommandType(MessageType):
    """
    The Command metaclass
    """

    _commands: dict[str, "CommandType"] = {}

    def __new__(cls, name, bases, dic):
        command_cls = super().__new__(cls, name, bases, dic)
        cls._commands[command_cls.NAME] = command_cls
        return command_cls

    @classmethod
    def _clear(cls):
        """
        Resets internal state. For testing.
        """
        cls._events = {}


class Command(Message, metaclass=CommandType):
    """
    The Command base class. To inherit and set the NAME.
    """
    pass
