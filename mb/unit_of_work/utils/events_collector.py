import abc
import typing as t

if t.TYPE_CHECKING:
    from mb.events import Event


class EventsCollector(t.Collection["Event"], abc.ABC):
    """
    Collects events to be handled later
    """

    def __bool__(self):
        return bool(len(self))

    @abc.abstractmethod
    def push(self, event: "Event"):
        raise NotImplementedError()

    @abc.abstractmethod
    def pop(self) -> "Event":
        raise NotImplementedError()

    @abc.abstractmethod
    def extend(self, events: "EventsCollector") -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def clear(self):
        """
        Clear **non persistent** events
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def __iter__(self) -> t.Iterator["Event"]:
        raise NotImplementedError()

    @abc.abstractmethod
    def __contains__(self, event) -> bool:
        raise NotImplementedError()


class EventsFifo(EventsCollector):
    """
    FIFO
    """

    queue: list["Event"]

    def __init__(self):
        self.queue = []

    def push(self, event: "Event"):
        self.queue.append(event)

    def pop(self) -> "Event":
        return self.queue.pop()

    def extend(self, events: "EventsCollector"):
        self.queue.extend(events)

    def clear(self):
        self.queue = [e for e in self.queue if e.is_persistent()]

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)

    def __contains__(self, event):
        return event in self.queue


class DedupeEventsFifo(EventsCollector):
    """
    Deduplicated FIFO
    """

    queue: list["Event"]
    seen: set["Event"]

    def __init__(self):
        self.queue = []
        self.seen = set()

    def push(self, event: "Event"):
        if event not in self:
            self.seen.add(event)
            self.queue.append(event)

    def pop(self) -> "Event":
        event = self.queue.pop()
        self.seen.remove(event)
        return event

    def extend(self, events: "EventsCollector"):
        for event in events:
            self.push(event)

    def clear(self):
        self.queue = [e for e in self.queue if e.is_persistent()]
        self.seen = set(self.queue)

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)

    def __contains__(self, event):
        return event in self.seen
