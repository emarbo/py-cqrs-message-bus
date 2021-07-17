import typing as t
from collections import OrderedDict
from collections import defaultdict

from lib.messages import MessageType
from lib.events import EventType
from lib.events import Event
from lib.events import EventHandler
from lib.commands import CommandType
from lib.commands import Command
from lib.commands import CommandHandler



class MessageBus:
    """
    An in-memory message bus.
    """

    _queue: OrderedDict
    _subscribers: defaultdict

    def __init__(self):
        self._queue = OrderedDict()
        self._subscribers = defaultdict(list)

    def subscribe(self, event_cls: EventType, handler: EventHandler):
        """
        Subscribe to an event type
        """
        self._subscribers[event_cls.NAME].append(handler)

    def publish(self, event: Event):
        """
        Executes subscribers immediately
        """
        for handler in self._subscribers[event.NAME]:
            handler(event)

    def publish_on_command(self, event: Event):
        """
        Executes subscribers when current command finishes successfully
        """
        raise NotImplementedError()
