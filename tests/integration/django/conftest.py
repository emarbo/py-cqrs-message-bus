import pytest

from mb.bus import MessageBus
from mb.contrib.django.unit_of_work import DjangoUnitOfWork
from mb.utils.tracked_handler import TrackedHandler
from mb.utils.tracked_handler import tracked_handler
from tests.fixtures.scenarios.create_user import CreateUserCommand
from tests.fixtures.scenarios.create_user import UserCreatedEvent


@pytest.fixture()
def uow(bus: MessageBus):
    return DjangoUnitOfWork(bus)


@pytest.fixture(autouse=True, scope="function")
def create_user_handler(bus: MessageBus) -> TrackedHandler:
    from tests.integration.django.testapp.models import User

    @tracked_handler
    def handler(cmd: CreateUserCommand, uow: DjangoUnitOfWork) -> "User":
        with uow.atomic():
            # The User.save emits the event
            return User.objects.create(username=cmd.username)

    bus.subscribe_command(CreateUserCommand, handler)
    return handler


@pytest.fixture(autouse=True, scope="function")
def user_created_handler(bus: MessageBus) -> TrackedHandler:
    @tracked_handler
    def handler(event: UserCreatedEvent):
        pass

    bus.subscribe_event(UserCreatedEvent, handler)
    return handler
