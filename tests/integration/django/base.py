import typing as t
from uuid import uuid4

import pytest
from django.db.transaction import atomic
from django.db import connections

from cq.bus import MessageBus
from cq.databases import SqlTransactionManager
from cq.contrib.django.databases import CqbusDjangoTransactionBridge
from tests.integration.django.testapp.commands import CreateUserCommand
from tests.integration.django.conftest import CommandHandler
from tests.integration.django.conftest import EventHandler
from tests.integration.django.testapp.models import User


class BreakTransaction(Exception):
    pass


# TODO: Create a `def atomic(...)` that commits if autocommit is OFF
# for sharing tests between autocommit ON/OFF modes


class BaseTest:
    DB: t.ClassVar[str]

    @pytest.fixture(autouse=True)
    def connection(self, bus: MessageBus):
        # Bind the connection to the bus
        connection: CqbusDjangoTransactionBridge = connections[self.DB]
        connection.bind_cqbus(bus)
        connection.set_autocommit(True)
        # Bind models to the connection
        User.objects.set_db(self.DB)
        return connection


class _TestDjangoOrm(BaseTest):
    """
    Test Django ORM base cases
    """

    def test_insert_and_select(self):
        username = f"test-{uuid4()}"
        User.objects.create(username=username)
        User.objects.get(username=username)

    def test_transaction_is_committed(self):
        username = f"test-{uuid4()}"
        with atomic(using=self.DB):
            User.objects.create(username=username)
        User.objects.get(username=username)

    def test_transaction_is_rolled_back_on_error(self):
        username = f"test-{uuid4()}"
        try:
            with atomic(using=self.DB):
                User.objects.create(username=username)
                raise BreakTransaction()
        except BreakTransaction:
            pass
        assert not User.objects.filter(username=username).exists()

    def test_transaction_is_rolled_back_on_close(
        self,
        connection: CqbusDjangoTransactionBridge,
    ):
        username = f"test-{uuid4()}"
        with atomic(using=self.DB):
            User.objects.create(username=username)
            connection.close()
        assert not User.objects.filter(username=username).exists()

    def test_savepoints_are_rolled_back_on_error(self):
        username_1 = f"test-{uuid4()}"
        username_2 = f"test-{uuid4()}"
        with atomic(using=self.DB):
            User.objects.create(username=username_1)
            try:
                with atomic(using=self.DB):
                    User.objects.create(username=username_2)
                    raise BreakTransaction()
            except BreakTransaction:
                pass
        assert User.objects.filter(username=username_1).exists()
        assert not User.objects.filter(username=username_2).exists()


class _TestAutocommitOn(BaseTest):
    """
    Test behavior for autocommit ON configuration
    """

    def test_bus_tracks_transaction_stack(
        self,
        bus: MessageBus,
    ):
        assert isinstance(bus.transaction_manager, SqlTransactionManager)
        manager: SqlTransactionManager = bus.transaction_manager

        assert not manager.in_transaction
        with atomic(using=self.DB):
            assert len(manager.stack) == 1
            with atomic(using=self.DB):
                assert len(manager.stack) == 2
                with atomic(using=self.DB, savepoint=False):
                    assert len(manager.stack) == 2
        assert not manager.in_transaction

    def test_events_are_handled_on_commit(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        username = f"test-{uuid4()}"
        cmd = CreateUserCommand(username=username)
        with atomic(self.DB):
            bus.handle_command(cmd)
            assert create_user_handler.calls
            assert not user_created_handler.calls
        user: User = User.objects.get(username=username)
        assert user_created_handler.calls
        assert user_created_handler.calls[0].id == user.id
        assert user_created_handler.calls[0].username == user.username

    def test_events_are_discarded_on_rollback(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,  # set up handler
        user_created_handler: EventHandler,
    ):
        username = f"test-{uuid4()}"
        cmd = CreateUserCommand(username=username)
        try:
            with atomic(self.DB):
                bus.handle_command(cmd)
                raise BreakTransaction()
        except BreakTransaction:
            pass
        assert not User.objects.filter(username=username).exists()
        assert not user_created_handler.calls

    def test_events_are_discarded_on_close(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,  # set up handler
        user_created_handler: EventHandler,
        connection: CqbusDjangoTransactionBridge,
    ):
        username = f"test-{uuid4()}"
        cmd = CreateUserCommand(username=username)
        with atomic(self.DB):
            bus.handle_command(cmd)
            connection.close()
        assert not User.objects.filter(username=username).exists()
        assert not user_created_handler.calls

    def test_events_are_discarded_on_savepoint_rollback(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,  # set up handler
        user_created_handler: EventHandler,
    ):
        username_1 = f"test-{uuid4()}"
        username_2 = f"test-{uuid4()}"
        with atomic(self.DB):
            bus.handle_command(CreateUserCommand(username=username_1))
            try:
                with atomic(self.DB):
                    bus.handle_command(CreateUserCommand(username=username_2))
                    raise BreakTransaction()
            except BreakTransaction:
                pass
        assert not User.objects.filter(username=username_2).exists()
        user: User = User.objects.get(username=username_1)
        assert len(user_created_handler.calls) == 1
        assert user_created_handler.calls[0].id == user.id
        assert user_created_handler.calls[0].username == username_1
