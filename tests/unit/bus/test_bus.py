import pytest

from cq.bus.bus import MessageBus
from cq.exceptions import MissingCommandHandler
from cq.unit_of_work.base import UnitOfWork
from tests.fixtures.scenarios.create_user import CommandHandler
from tests.fixtures.scenarios.create_user import CreateUserCommand
from tests.fixtures.scenarios.create_user import EventHandler
from tests.fixtures.scenarios.create_user import UserCreatedEvent


def test_bus_handles_commands(
    uow: UnitOfWork,
    create_user_handler: CommandHandler,
):
    """
    Test simple command configuration
    """
    command = CreateUserCommand("pepe")
    uow.handle_command(command)
    assert create_user_handler.calls
    assert create_user_handler.calls[0] == command


def test_bus_handles_events(
    uow: UnitOfWork,
    user_created_handler: EventHandler,
):
    """
    Test simple event configuration
    """
    event = UserCreatedEvent("pepe")
    with uow:
        uow.emit_event(event)
    assert user_created_handler.calls
    assert user_created_handler.calls[0] == event


def test_missing_command_handler_raises_error(uow: UnitOfWork):
    """
    Test commands must have handlers
    """
    command = CreateUserCommand("pepe")
    with pytest.raises(MissingCommandHandler):
        with uow:
            uow.handle_command(command)


def test_missing_event_handler_is_fine(uow: UnitOfWork):
    """
    Test events don't require handlers
    """
    event = UserCreatedEvent("pepe")
    with uow:
        uow.emit_event(event)


def test_bus_handles_commands_emitting_events(
    uow: UnitOfWork,
    create_user_handler: CommandHandler,
    user_created_handler: EventHandler,
):
    """
    Test simple commands and events scenario
    """
    with uow:
        command = CreateUserCommand("pepe")
        uow.handle_command(command)
    assert create_user_handler.calls
    assert create_user_handler.calls[0] == command
    assert user_created_handler.calls
    assert user_created_handler.calls[0].username == "pepe"
