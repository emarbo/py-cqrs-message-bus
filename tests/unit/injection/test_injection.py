import pytest

from mb.bus import MessageBus
from mb.commands import Command
from mb.events import Event
from mb.exceptions import MissingHandlerError
from mb.messages import Message
from mb.unit_of_work.base import UnitOfWork
from mb.utils.tracked_handler import TrackedHandler, tracked_handler
from tests.fixtures.scenarios.create_user import CreateUserCommand
from tests.fixtures.scenarios.create_user import UserCreatedEvent


def test_injection_no_args(uow: UnitOfWork):
    """
    Test injection of no args
    """

    @tracked_handler
    def handler():
        pass

    uow.bus.subscribe_command(CreateUserCommand, handler)

    command = CreateUserCommand("pepe")
    uow.handle_command(command)
    assert handler.calls
    assert handler.calls[0] is None


def test_injection_by_name(uow: UnitOfWork):
    """
    Test injection by common names matching
    """
    _uow = uow  # alias
    _message = CreateUserCommand("pepe")

    @tracked_handler
    def handler(message, command, cmd, event, unit_of_work, uow):
        assert _message is message
        assert _message is command
        assert _message is cmd
        assert _message is event
        assert _uow is unit_of_work
        assert _uow is uow

    uow.bus.subscribe_command(CreateUserCommand, handler)
    uow.handle_command(_message)
    assert handler.calls
    assert handler.calls[0] is _message


def test_injection_with_by_name_using_kwargs(uow: UnitOfWork):
    """
    Test injection by common names matching using kwargs
    """
    _uow = uow  # alias
    _message = CreateUserCommand("pepe")

    @tracked_handler
    def handler(
        message=None,
        command=None,
        cmd=None,
        event=None,
        unit_of_work=None,
        uow=None,
    ):
        assert _message is message
        assert _message is command
        assert _message is cmd
        assert _message is event
        assert _uow is unit_of_work
        assert _uow is uow

    uow.bus.subscribe_command(CreateUserCommand, handler)
    uow.handle_command(_message)
    assert handler.calls
    assert handler.calls[0] is _message


def test_injection_by_typed_annoatation(uow: UnitOfWork):
    """
    Test injection by typed annotations
    """
    _uow = uow  # alias
    _message = CreateUserCommand("pepe")

    @tracked_handler
    def handler(
        a1: Message,
        a2: CreateUserCommand,
        a3: CreateUserCommand,
        a4: Event,
        a5: UnitOfWork,
        a6: UnitOfWork,
    ):
        assert _message is a1
        assert _message is a2
        assert _message is a3
        assert _message is a4
        assert _uow is a5
        assert _uow is a6

    uow.bus.subscribe_command(CreateUserCommand, handler)
    uow.handle_command(_message)
    assert handler.calls
    assert handler.calls[0] is _message


def test_injection_with_unknown_default_params(uow: UnitOfWork):
    """
    Test injection don't break with unknown default params
    """
    _message = CreateUserCommand("pepe")

    @tracked_handler
    def handler(
        a1: Message,
        unknown: str = "default",
    ):
        assert _message is a1
        assert unknown == "default"

    uow.bus.subscribe_command(CreateUserCommand, handler)
    uow.handle_command(_message)
    assert handler.calls
    assert handler.calls[0] is _message
