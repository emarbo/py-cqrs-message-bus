import typing as t

import pytest

from cq.bus.bus import MessageBus
from cq.contrib.django.unit_of_work import DjangoUnitOfWork
from cq.utils.tracked_handler import TrackedHandler
from cq.utils.tracked_handler import tracked_handler
from tests.fixtures.scenarios.create_user import CreateUserCommand
from tests.fixtures.scenarios.create_user import UserCreatedEvent

CommandHandler = TrackedHandler["CreateUserCommand", t.Any]
EventHandler = TrackedHandler["UserCreatedEvent", None]


@pytest.fixture()
def uow(bus: MessageBus):
    return DjangoUnitOfWork(bus)


@pytest.fixture(autouse=True, scope="function")
def create_user_handler(bus: MessageBus) -> CommandHandler:
    from tests.integration.django.testapp.models import User

    @tracked_handler
    def handler(cmd: CreateUserCommand, uow: DjangoUnitOfWork) -> "User":
        with uow.atomic():
            # The User.save emits the event
            return User.objects.create(username=cmd.username)

    bus.subscribe_command(CreateUserCommand, handler)
    return handler


@pytest.fixture(autouse=True, scope="function")
def user_created_handler(bus: MessageBus) -> EventHandler:
    @tracked_handler
    def handler(event: UserCreatedEvent, uow: DjangoUnitOfWork):
        pass

    bus.subscribe_event(UserCreatedEvent, handler)
    return handler
