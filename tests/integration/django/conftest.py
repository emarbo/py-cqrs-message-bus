import typing as t
import pytest
from tests.integration.django.testapp.events import UserCreatedEvent
from tests.integration.django.testapp.bus import bus as _bus
from tests.utils.tracked_handler import tracked_handler
from tests.utils.tracked_handler import TrackedHandler
from tests.integration.django.testapp.commands import CreateUserCommand
from cq.bus import MessageBus


CommandHandler = TrackedHandler["CreateUserCommand", t.Any]
EventHandler = TrackedHandler["UserCreatedEvent", None]


@pytest.fixture(autouse=True, scope="function")
def bus() -> MessageBus:
    _bus._clear()
    return _bus


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
    def handler(event: UserCreatedEvent) -> None:
        return None

    bus.subscribe_event(UserCreatedEvent, handler)
    return handler
