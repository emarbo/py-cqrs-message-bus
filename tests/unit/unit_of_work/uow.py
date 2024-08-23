import contextlib
import typing as t
from uuid import uuid4

from mb.unit_of_work import UnitOfWork
from mb.utils.tracked_handler import TrackedHandler
from tests.fixtures.scenarios.create_user import CreateUserCommand
from tests.fixtures.scenarios.create_user import UserCreatedEvent

UOW = t.TypeVar("UOW", bound=UnitOfWork)

UCH: t.TypeAlias = TrackedHandler[t.Any, t.Any, UserCreatedEvent]


class FakeException(Exception):
    pass


class Base(t.Generic[UOW]):
    """
    Uses create_user scenario.
    """

    @contextlib.contextmanager
    def open_context(self, uow: UOW):
        """
        Subclasses may override how the uow context is started
        """
        with uow:
            yield

    @classmethod
    def make_username(cls):
        """
        Unique username
        """
        return str(uuid4())

    def assert_user_created(self, username: str):
        try:
            assert self.user_exists(username)
        except NotImplementedError:
            pass

    def assert_user_not_created(self, username: str):
        try:
            assert not self.user_exists(username)
        except NotImplementedError:
            pass

    def user_exists(self, username: str):
        """
        Subclasses may verify changes are committed to database
        """
        raise NotImplementedError()


class _TestUnitOfWork(Base[UOW]):
    """
    Test UnitOfWork implementing nested transactions management.

    Use case: create users on the system.
    """

    def test_emtpy_context(self, uow: UOW):
        with self.open_context(uow):
            pass

    def test_empty_nested_context(self, uow: UOW):
        with self.open_context(uow):
            with self.open_context(uow):
                pass

    def test_events_are_handled(
        self,
        uow: UOW,
        user_created_handler: UCH,
    ):
        with self.open_context(uow):
            event = UserCreatedEvent("mike")
            uow.emit_event(event)
        assert user_created_handler.calls
        assert user_created_handler.calls[0] == event

    def test_commit_transaction(
        self,
        uow: UOW,
        create_user_handler: TrackedHandler,
        user_created_handler: UCH,
    ):
        with self.open_context(uow):
            command = CreateUserCommand(self.make_username())
            uow.handle_command(command)
        assert create_user_handler.calls == [command]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command.username
        self.assert_user_created(command.username)

    def test_commit_transaction(
        self,
        uow: UOW,
        create_user_handler: TrackedHandler,
        user_created_handler: UCH,
    ):
        with self.open_context(uow):
            command = CreateUserCommand(self.make_username())
            uow.handle_command(command)
            assert not user_created_handler.calls  # != _TestUnitOfWork

        assert create_user_handler.calls == [command]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command.username
        self.assert_user_created(command.username)

    def test_rollback_transaction(
        self,
        uow: UOW,
        create_user_handler: TrackedHandler,
        user_created_handler: TrackedHandler,
    ):
        try:
            with self.open_context(uow):
                command = CreateUserCommand(self.make_username())
                uow.handle_command(command)
                assert not user_created_handler.calls
                raise FakeException()
        except FakeException:
            pass

        assert create_user_handler.calls == [command]
        assert not user_created_handler.calls
        self.assert_user_not_created(command.username)

    def test_commiting_nested_transaction(
        self,
        uow: UOW,
        create_user_handler: TrackedHandler,
        user_created_handler: TrackedHandler,
    ):
        with self.open_context(uow):
            with self.open_context(uow):
                command_1 = CreateUserCommand(self.make_username())
                uow.handle_command(command_1)
            assert not user_created_handler.calls
            command_2 = CreateUserCommand(self.make_username())
            uow.handle_command(command_2)
            assert not user_created_handler.calls

        assert create_user_handler.calls == [command_1, command_2]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command_1.username
        assert user_created_handler.calls[1].username == command_2.username
        self.assert_user_created(command_1.username)
        self.assert_user_created(command_2.username)

    def test_rolling_back_nested_transaction(
        self,
        uow: UOW,
        create_user_handler: TrackedHandler,
        user_created_handler: TrackedHandler,
    ):
        with self.open_context(uow):
            try:
                with self.open_context(uow):
                    command_1 = CreateUserCommand(self.make_username())
                    uow.handle_command(command_1)
                    raise FakeException()
            except FakeException:
                pass
            assert not user_created_handler.calls
            command_2 = CreateUserCommand(self.make_username())
            uow.handle_command(command_2)
            assert not user_created_handler.calls

        assert create_user_handler.calls == [command_1, command_2]
        assert user_created_handler.calls
        assert user_created_handler.calls[0].username == command_2.username
        self.assert_user_not_created(command_1.username)
        self.assert_user_created(command_2.username)


class TestUnitOfWork(_TestUnitOfWork[UnitOfWork]):
    pass
