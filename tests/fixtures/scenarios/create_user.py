import typing as t
from dataclasses import dataclass

import pytest

from mb import MessageBus
from mb.commands import Command
from mb.events import Event
from mb.unit_of_work import UnitOfWork
from mb.utils.tracked_handler import TrackedHandler
from mb.utils.tracked_handler import tracked_handler

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


@pytest.fixture()
def create_user_handler(bus: MessageBus) -> TrackedHandler:
    """
    A handler that emits UserCreatedEvent()
    """

    @tracked_handler
    def create_user_handler(command: CreateUserCommand, uow: UnitOfWork):
        with uow:
            event = UserCreatedEvent(username=command.username)
            uow.emit_event(event)

    bus.subscribe_command(CreateUserCommand, create_user_handler)
    return create_user_handler


@pytest.fixture()
def user_created_handler(bus: MessageBus) -> TrackedHandler:
    """
    Dumb handler
    """

    @tracked_handler
    def user_created_handler(event: UserCreatedEvent):
        return

    bus.subscribe_event(UserCreatedEvent, user_created_handler)
    return user_created_handler
