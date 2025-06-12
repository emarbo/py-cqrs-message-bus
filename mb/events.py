import typing as t

from mb.messages import Message
from mb.messages import MessageMeta


class EventMeta(MessageMeta):
    """
    The Event metaclass
    """

    _events: dict[str, "EventMeta"] = {}

    def __new__(cls, name, bases, dic):
        # super checks NAME correctness and may assign a default
        event_cls = super().__new__(cls, name, bases, dic)

        cls._events[event_cls.NAME] = event_cls

        return event_cls

    @classmethod
    def _clear(cls):
        """
        Resets internal state. For testing.
        """
        cls._events = {}


class Event(Message, metaclass=EventMeta):
    """
    The Event base class. To inherit and set the NAME.
    """

    def is_persistent(self) -> bool:
        """
        Whether the event is persisted or discarded after a transaction roll back.

        Events that reflect metrics or failures may return True, so they are handled
        even when an error is raised while handling a command.
        """
        return False


def is_event_type(thing) -> t.TypeGuard[type[Event]]:
    return isinstance(thing, type) and issubclass(thing, Event)
