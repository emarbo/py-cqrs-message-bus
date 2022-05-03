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
    def extend(self, events: "EventsCollector") -> "Event":
        raise NotImplementedError()

    @abc.abstractmethod
    def clear(self):
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

    def extend(self, events: "EventsCollector") -> "Event":
        self.queue.extend(events)

    def clear(self):
        self.queue = []

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)

    def __contains__(self, event: "Event"):  # type: ignore
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

    def extend(self, events: "EventsCollector") -> "Event":
        for event in events:
            self.push(event)

    def clear(self):
        self.queue = []
        self.seen = set()

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)

    def __contains__(self, event: "Event"):  # type: ignore
        return event in self.seen
