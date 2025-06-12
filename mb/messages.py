import typing as t

from mb.exceptions import DuplicatedNameError
from mb.exceptions import InvalidNameError


class MessageMeta(type):
    """
    The Message metaclass.

    Message.NAME defaults to the qualified name
    Message.NAME type and collision check
    """

    _messages: dict[str, "MessageMeta"] = {}

    def __new__(meta, name: str, bases: tuple[type], dic: dict[str, t.Any], **kw):
        meta._set_default_name(name, dic)
        meta._check_name_type(name, dic)
        meta._check_unique_name(name, dic)

        message_cls = super().__new__(meta, name, bases, dic, **kw)

        meta._messages[message_cls.NAME] = message_cls  # type: ignore[attr-defined]

        return message_cls

    @classmethod
    def _set_default_name(cls, name: str, dic: dict[str, t.Any]):
        try:
            dic["NAME"]
        except KeyError:
            dic["NAME"] = f"{dic['__module__']}.{name}"

    @classmethod
    def _check_name_type(cls, name: str, dic: dict[str, t.Any]):
        message_name = dic["NAME"]
        if not isinstance(message_name, str):
            raise InvalidNameError(
                f"'{name}.NAME' must be str. Found: '{type(message_name)}'"
            )

    @classmethod
    def _check_unique_name(cls, name: str, dic: dict[str, t.Any]):
        message_name = dic["NAME"]
        try:
            message_cls = cls._messages[message_name]
        except KeyError:
            return
        raise DuplicatedNameError(
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
