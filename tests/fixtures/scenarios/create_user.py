import typing as t
from dataclasses import dataclass

import pytest

from cq.bus.commands import Command
from cq.bus.events import Event
from cq.utils.tracked_handler import TrackedHandler
from cq.utils.tracked_handler import tracked_handler

if t.TYPE_CHECKING:
    from cq.unit_of_work.base import MessageBus
    from cq.unit_of_work.base import UnitOfWork


# --------------------------------------
# Messages definition
# --------------------------------------


@dataclass
class CreateUserCommand(Command):
    username: str
    email: str = ""
    password: str = ""

    def __hash__(self):
        return hash((self.NAME, self.username))


@dataclass
class UserCreatedEvent(Event):
    username: str

    def __hash__(self):
        return hash((self.NAME, self.username))


# --------------------------------------
# Fixtures
# --------------------------------------

CommandHandler = TrackedHandler["CreateUserCommand", None]
EventHandler = TrackedHandler["UserCreatedEvent", None]


@pytest.fixture()
def create_user_handler(bus: "MessageBus") -> CommandHandler:
    """
    A handler that emits UserCreatedEvent()
    """

    @tracked_handler
    def create_user_handler(command: "CreateUserCommand", uow: "UnitOfWork"):
        with uow:
            event = UserCreatedEvent(username=command.username)
            uow.emit_event(event)

    bus.subscribe_command(CreateUserCommand, create_user_handler)
    return create_user_handler


@pytest.fixture()
def user_created_handler(bus: "MessageBus") -> EventHandler:
    """
    Dumb handler
    """

    @tracked_handler
    def user_created_handler(event: "UserCreatedEvent", uow: "UnitOfWork"):
        return

    bus.subscribe_event(UserCreatedEvent, user_created_handler)
    return user_created_handler
