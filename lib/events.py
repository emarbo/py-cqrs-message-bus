import typing as t
from pprint import pprint  # noqa


class EventType(type):
    """
    The Event metaclass
    """

    _events: t.Dict[str, "EventType"] = {}

    def __init__(cls, cls_name, bases, attrs):
        cls.check_valid_name(cls_name, attrs)
        cls.check_unique_name(cls_name, attrs)

        cls._events[attrs["NAME"]] = cls

    @classmethod
    def check_valid_name(cls, cls_name, attrs):
        try:
            name_attr = attrs["NAME"]
        except KeyError:
            raise RuntimeError(f"{cls_name} doesn't have a NAME attribute")

        if not isinstance(name_attr, str):
            raise RuntimeError(f"{cls_name} NAME attr is not string: {type(name_attr)}")

    @classmethod
    def check_unique_name(cls, cls_name, attrs):
        name_attr = attrs["NAME"]
        try:
            event_cls = cls._events[name_attr]
        except KeyError:
            return
        raise RuntimeError(
            "These events have the same value for NAME: "
            f"'{cls_name}' and '{event_cls.__name__}'"
        )

    @classmethod
    def _clear(cls):
        """
        Resets internal state. For testing.
        """
        cls._events = {}


class Event(metaclass=EventType):
    """
    The Event base class. Inherit and change the NAME.
    """

    NAME: t.ClassVar[str] = "Event"

    def __hash__(self):
        return hash((self.__class__, self.name))
