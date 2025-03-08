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

    def is_persistent(self):
        """
        Persistent events are handled even when the UoW transaction is rolled back.

        Most events reflect database changes and does not make sense to emit them
        if the change is not persisted in the database. This events shouldn't be
        persistent. For example, a `UserCreated` event.

        However, some events might signal important information that must be recorded
        or handled somehow. This events should be persistent to outlive their UoW
        transaction.

        For instance, let's suppose an application handles authorization erros by
        raising an exception that is later converted into a HTTP response by some
        framework middleware. At the same time, the application wants to track these
        errors using events. Without this ability, it will be very annoying or even
        impossible to do it.

        The example applies to any scenario where an exception is used to break the
        normal flow, but the event must be emitted.
        """
        return False


def is_event_type(thing) -> t.TypeGuard[type[Event]]:
    return isinstance(thing, type) and issubclass(thing, Event)
