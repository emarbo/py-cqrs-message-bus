import typing as t
from uuid import uuid4

import pytest

from cq.unit_of_work import UnitOfWork
from tests.fixtures.scenarios.create_user import (
    CommandHandler,
    CreateUserCommand,
    EventHandler,
)
from tests.fixtures.scenarios.create_user import UserCreatedEvent

UOW = t.TypeVar("UOW", bound=UnitOfWork)


class FakeException(Exception):
    pass


def username():
    return str(uuid4())


class _TestUnitOfWork(t.Generic[UOW]):
    """
    Test common UnitOfWork interface
    """

    def test_context(self, uow: UOW):
        with uow:
            pass

    def test_nested_context(self, uow: UOW):
        with uow:
            with uow:
                pass

    def test_context_rollback(self, uow: UOW):
        with pytest.raises(FakeException):
            with uow:
                raise FakeException()

    def test_events_are_handled(
        self,
        uow: UOW,
        user_created_handler: EventHandler,
    ):
        with uow:
            event = UserCreatedEvent("mike")
            uow.emit_event(event)
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event

    def test_commands_and_events_are_handled(
        self,
        uow: UOW,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        with uow:
            command = CreateUserCommand(username())
            uow.bus.handle_command(command)
        assert create_user_handler.calls == [command]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command.username


class _TestTransactionalUnitOfWork(t.Generic[UOW]):
    """
    Test UnitOfWork that implements nested transactions management
    """

    def test_events_are_handled_on_commit(
        self,
        uow: UOW,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        with uow:
            command = CreateUserCommand(username())
            uow.bus.handle_command(command)
            assert not user_created_handler.calls

        assert create_user_handler.calls == [command]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command.username

    def test_events_are_discarded_on_rollback(
        self,
        uow: UOW,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        try:
            with uow:
                command = CreateUserCommand(username())
                uow.bus.handle_command(command)
                assert not user_created_handler.calls
                raise FakeException()
        except FakeException:
            pass

        assert create_user_handler.calls == [command]
        assert not user_created_handler.calls

    def test_nested_events_are_handled_on_outermost_commit(
        self,
        uow: UOW,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        with uow:
            with uow:
                command_1 = CreateUserCommand(username())
                uow.bus.handle_command(command_1)
            assert not user_created_handler.calls
            command_2 = CreateUserCommand(username())
            uow.bus.handle_command(command_2)
            assert not user_created_handler.calls

        assert create_user_handler.calls == [command_1, command_2]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command_1.username
        assert user_created_handler.calls[1].username == command_2.username

    def test_nested_rolled_back_events_are_discarded(
        self,
        uow: UOW,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        with uow:
            try:
                with uow:
                    command_1 = CreateUserCommand(username())
                    uow.bus.handle_command(command_1)
                    raise FakeException()
            except FakeException:
                pass
            assert not user_created_handler.calls
            command_2 = CreateUserCommand(username())
            uow.bus.handle_command(command_2)
            assert not user_created_handler.calls

        assert create_user_handler.calls == [command_1, command_2]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command_2.username
