import typing as t
import logging
from collections import defaultdict
from enum import IntEnum

from lib.messages import MessageType
from lib.events import EventType
from lib.events import Event
from lib.events import EventHandler
from lib.commands import CommandType
from lib.commands import Command
from lib.commands import CommandHandler


logger = logging.getLogger()


class MessageBus:
    """
    An in-memory message bus.
    """

    event_handlers: t.DefaultDict[str, list[EventHandler]]
    command_handlers: dict[str, CommandHandler]
    stack: list["TransactionStack"]

    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.command_handlers = {}
        self.stack = []

    def subscribe_event(self, event: EventType, handler: EventHandler):
        """
        Subscribe to an event type
        """
        self.event_handlers[event.NAME].append(handler)

    def subscribe_command(self, command: CommandType, handler: CommandHandler):
        """
        Set the command handler for command

        :raises: RuntimeError if there is already a handler
        """
        try:
            current_handler = self.command_handlers[command.NAME]
        except KeyError:
            self.command_handlers[command.NAME].append(handler)
        else:
            raise RuntimeError(
                f"Duplicated handler for command {command}. "
                f"The handler {handler} overrides the current {current_handler}"
            )

    def handle(self, message: MessageType) -> t.Any:
        if not self.stack:
            self.stack.append(TransactionStack(self, message))
            return self.stack[-1].execute()
        else:
            return self.stack[-1].handle(message)


class Status(IntEnum):
    INIT = 1
    EXECUTING_HANDLER = 2
    FLUSHING_EVENTS = 3
    DONE = 4


class TransactionStack:

    bus: "MessageBus"
    message: MessageType
    events: list[EventType]

    level: int
    status: Status

    def __init__(self, bus: "MessageBus", message: MessageType, level=0):
        self.assert_message_type(message)

        self.bus = bus
        self.message = message
        self.events = []

        self.level = level
        self.status = Status.INIT

    def handle(self, message: MessageType):
        """
        Handle a message requested by the application code
        """
        self.assert_message_type(message)

        if isinstance(message, Command):
            self.handle_command(message)
        elif isinstance(message, Event):
            self.handle_event(message)

    def handle_command(self, command: Command):
        """
        Handle a command requested by the application code
        """
        # Push a new transaction on the stack that will handle the command
        self.push_and_execute(command)

    def handle_event(self, event: Event):
        """
        Handle an event requested by the application code (just queue)
        """
        # Queue the event to be handled after the command ends successfully
        assert self.status == Status.EXECUTING_HANDLER, "Programming error"
        self.events.append(event)

    def execute(self):
        """
        Execute :attr:`message` handler
        """
        if isinstance(self.message, Command):
            self.execute_command()
        elif isinstance(message, Event):
            self.execute_event()

    def execute_command(self):
        """
        Execute :attr:`message` command handler
        """
        logger.debug("handling command %s", self.message)
        self.assert_im_the_head()

        self.set_status(Status.EXECUTING_HANDLER)
        try:
            handler = self.bus.command_handlers[self.message.NAME]
            handler(self.message)
        except Exception:
            logger.exception("Exception handling command %s", self.message)
            self.assert_im_the_head()
            self.bus.stack.pop()
            raise

        self.set_status(Status.FLUSHING_EVENTS)
        if len(self.bus.stack) > 1:
            # This might be called 'merge_up'
            for event in self.events:
                self.bus.stack[-2].handle(event)
        else:
            for event in self.events:
                self.push_and_execute(event)
        self.set_status(Status.DONE)

    def execute_event(self):
        """
        Execute the event handler
        """
        logger.debug("handling event %s", self.message)
        self.assert_im_the_head()

        # TODO: Here is an asymmetry between handling a command and an event.
        # The events have multiple handlers so that we shall stack on TransactionStack
        # for each pair of event and handler. Also, there must no be errors if no
        # handlers are set.

        self.set_status(Status.EXECUTING_HANDLER)
        for handler in self.bus.event_handlers[self.message.NAME]:
            logger.debug("handling event %s with handler %s", self.message, handler)
            try:
                handler(self.message)
            except Exception:
                logger.exception("Exception handling event %s", self.messag)
                self.assert_im_the_head()
                self.bus.stack.pop()
                raise

        self.set_status(Status.FLUSHING_EVENTS)
        if len(self.bus.stack) > 1:
            # This might be called 'merge_up'
            for event in self.events:
                self.bus.stack[-2].handle(event)
        else:
            for event in self.events:
                self.push_and_execute(event)
        self.set_status(Status.DONE)

    def push_and_execute(self, message: MessageType):
        """
        Push a new transaction and execute the message
        """
        self.assert_im_the_head()
        self.bus.stack.append(TransactionStack(self.bus, message, level=self.level + 1))
        self.bus.stack[-1].execute()

    def assert_im_the_head(self):
        assert self.bus.stack[-1] is self, "Programming error"

    def assert_message_type(self, message: MessageType):
        valid = isinstance(message, (Event, Command))
        assert valid, f"Invalid message type: '{type(message)}'"

    def set_status(self, status: Status):
        assert self.status < status, "Programming error"
        self.status = status
