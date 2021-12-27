import typing as t
import pytest
from django.db import connection
from tests.integration.django.testapp.events import UserCreatedEvent

from tests.utils.tracked_handler import tracked_handler
from tests.utils.tracked_handler import TrackedHandler
from tests.integration.django.testapp.commands import CreateUserCommand
from cq.bus import MessageBus

# Fixtures can't import testapp models (direct or indirectly)
if t.TYPE_CHECKING:
    from tests.integration.django.testapp.models import User

CommandHandler = TrackedHandler["CreateUserCommand", "User"]
EventHandler = TrackedHandler["UserCreatedEvent", None]


@pytest.fixture(autouse=True, scope="function")
def configure_bus(bus: MessageBus):
    connection.bind_cqbus(bus)


@pytest.fixture(autouse=True, scope="function")
def create_user_handler(bus: MessageBus) -> CommandHandler:
    from tests.integration.django.testapp.models import User

    @tracked_handler
    def handler(cmd: CreateUserCommand) -> "User":
        return User.objects.create(username=cmd.username)

    bus.subscribe_command(CreateUserCommand, handler)

    return handler


@pytest.fixture(autouse=True, scope="function")
def user_created_handler(bus: MessageBus) -> EventHandler:
    @tracked_handler
    def handler(event: UserCreatedEvent) -> "User":
        return None

    bus.subscribe_event(UserCreatedEvent, handler)
    return handler
