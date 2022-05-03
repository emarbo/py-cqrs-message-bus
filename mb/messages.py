import typing as t

from mb.exceptions import DuplicatedMessageName
from mb.exceptions import InvalidMessageName


class MessageMeta(type):
    """
    The Message metaclass.

    Message.NAME defaults to __module__.__name__
    Message.NAME type and collision check
    """

    _messages: dict[str, "MessageMeta"] = {}

    def __new__(cls, name, bases, dic, **kw):
        cls._set_default_name(name, dic)
        cls._check_name_type(name, dic)
        cls._check_unique_name(name, dic)

        # Create & register
        message_cls = super().__new__(cls, name, bases, dic, **kw)
        cls._messages[message_cls.NAME] = message_cls
        return message_cls

    @classmethod
    def _set_default_name(cls, name, dic):
        try:
            dic["NAME"]
        except KeyError:
            dic["NAME"] = f"{dic['__module__']}.{name}"

    @classmethod
    def _check_name_type(cls, name, dic):
        message_name = dic["NAME"]
        if not isinstance(message_name, str):
            raise InvalidMessageName(
                f"'{name}.NAME' must be of 'str' type. Found: '{type(message_name)}'"
            )

    @classmethod
    def _check_unique_name(cls, name, dic):
        message_name = dic["NAME"]
        try:
            message_cls = cls._messages[message_name]
        except KeyError:
            return
        raise DuplicatedMessageName(
            "These messages have the same NAME: "
            f"'{name}' and '{message_cls.__name__}'"
        )

    @classmethod
    def _clear(cls):
        """
        Resets internal state. For testing.
        """
        cls._messages = {}


class Message(metaclass=MessageMeta):
    """
    The Message base class
    """

    NAME: t.ClassVar[str]
