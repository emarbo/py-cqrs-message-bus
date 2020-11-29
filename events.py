import typing as t
from pprint import pprint  # noqa
from collections import OrderedDict
from collections import defaultdict


class EventType(type):

    __events = {}

    def __init__(cls, cls_name, bases, attrs):
        cls.check_valid_name(cls_name, attrs)
        cls.check_unique_name(cls_name, attrs)

        cls.__events[attrs["NAME"]] = cls

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
            event_cls = cls.__events[name_attr]
        except KeyError:
            return
        raise RuntimeError(
            "These events have the same value for NAME: "
            f"'{cls_name}' and '{event_cls.__name__}'"
        )


class Event(metaclass=EventType):
    """
    The Event base class.

    Events with the same hash() are deduplicated by the Bus when using publish_on_commit
    or publish_on_command
    """

    NAME: t.ClassVar[str] = "Event"

    def __hash__(self):
        return hash((self.__class__, self.name))


class UserCreatedEvent(Event):

    NAME = "users.UserCreatedEvent"


EventHandler = t.Callable[[Event], t.Any]


class Bus:
    """
    An event bus. Or something like that
    """

    __queue: OrderedDict
    __subscribers: defaultdict

    def __init__(self):
        self.__queue = OrderedDict()
        self.__subscribers = defaultdict(list)

    def subscribe(self, event_cls: EventType, handler: EventHandler):
        """
        Subscribe to an event type
        """
        self.__subscribers[event_cls.NAME].append(handler)

    def publish(self, event: Event):
        """
        Executes subscribers immediately
        """
        for handler in self.__subscribers[event.NAME]:
            handler(event)

    def publish_on_commit(self, event: Event):
        pass

    def publish_on_command(self, event: Event):
        pass
