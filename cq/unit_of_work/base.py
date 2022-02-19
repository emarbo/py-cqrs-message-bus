import abc
import typing as t

from cq.exceptions import InvalidMessage
from cq.bus.events import Event

if t.TYPE_CHECKING:
    from cq.bus.bus import MessageBus


class UnitOfWork(abc.ABC):
    bus: "MessageBus"

    def __init__(self, bus: "MessageBus"):
        self.bus = bus

    def __call__(self):
        """
        Allow extending features for the with statement

        >>> uow = UnitOfWork(bus)
        >>> with uow:  # uow.__enter__: no customization allowed
        ...     pass
        >>> with uow(transaction=True):  # open for extension in subclasses
        ...     pass
        """
        return self

    @abc.abstractmethod
    def __enter__(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError()

    def emit_event(self, event: Event):
        """
        :raises InvalidMessage: if this isn't an Event
        """
        if not isinstance(event, Event):
            raise InvalidMessage(f"This is not an event: '{event}'")
        self._emit_event(event)

    @abc.abstractmethod
    def _emit_event(self, event: Event):
        raise NotImplementedError()
