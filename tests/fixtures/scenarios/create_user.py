import pytest
import typing as t
from dataclasses import dataclass

from lib.bus import MessageBus
from lib.commands import Command
from lib.events import Event
from tests.utils.tracked_handler import tracked_handler
from tests.utils.tracked_handler import TrackedHandler


# --------------------------------------
# Messages definition
# --------------------------------------


@dataclass
class CreateUserCommand(Command):
    username: str
    email: str = ""
    password: str = ""


@dataclass
class UserCreatedEvent(Event):
    username: str


# --------------------------------------
# Fixtures
# --------------------------------------

CommandHandler = TrackedHandler["CreateUserCommand", None]
EventHandler = TrackedHandler["UserCreatedEvent", None]


@pytest.fixture()
def create_user_handler(bus: MessageBus) -> CommandHandler:
    """
    A handler that emits UserCreatedEvent()
    """

    @tracked_handler
    def create_user_handler(command: "CreateUserCommand"):
        event = UserCreatedEvent(username=command.username)
        bus.emit_event(event)

    bus.subscribe_command(CreateUserCommand, create_user_handler)
    return create_user_handler


@pytest.fixture()
def user_created_handler(bus: MessageBus) -> EventHandler:
    """
    Dumb handler
    """
    @tracked_handler
    def user_created_handler(event: "UserCreatedEvent"):
        return

    bus.subscribe_event(UserCreatedEvent, user_created_handler)
    return user_created_handler