from contextlib import contextmanager
from uuid import uuid4

import pytest
from django.db.transaction import atomic as django_atomic
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


class BaseTest:
    """
    Provides the connection setup and (db, autocommit) combos
    """

    DB: str
    autocommit: bool

    @pytest.fixture(
        autouse=True,
        params=[
            ("postgres", False),
            ("postgres", True),
            ("sqlite", False),
            ("sqlite", True),
        ],
        # e.g. "postgres,autocommit:OFF"
        ids=lambda p: f"{p[0]},autocommit:{p[1] and 'ON' or 'OFF'}",
    )
    def connection(self, request):
        self.DB = request.param[0]
        self.autocommit = request.param[1]
        # Clean up state from previous tests
        connection: CqbusDjangoTransactionBridge = connections[self.DB]
        connection.close()
        connection.set_autocommit(self.autocommit)
        # Bind the connection to the bus
        # connection.bind_cqbus(bus)
        # Bind models to the connection
        User.objects.set_db(self.DB)
        return connection

    @contextmanager
    def atomic(self, savepoint=True):
        """
        This is what you expect of an atomic block regardless the autocommit
        mode configuration
        """
        if self.autocommit:
            with django_atomic(using=self.DB, savepoint=savepoint):
                yield
        else:
            # The `django_atomic` roll backs but does not commit
            # when autocommit mode is OFF.
            connection: CqbusDjangoTransactionBridge = connections[self.DB]
            # Detect this means to be a transaction (the outermost atomic)
            is_transaction = not connection.in_atomic_block
            # Run the usual django machinery
            with django_atomic(using=self.DB, savepoint=savepoint):
                yield
            # Commit if everything went fine
            if is_transaction and connection.connection:
                connection.commit()


class TestDjangoOrm(BaseTest):
    """
    Test Django ORM works
    """

    def test_insert_and_select(self):
        username = f"test-{uuid4()}"
        User.objects.create(username=username)
        User.objects.get(username=username)

    def test_transaction_is_committed(self):
        username = f"test-{uuid4()}"
        with self.atomic():
            User.objects.create(username=username)
        User.objects.get(username=username)

    def test_transaction_is_rolled_back_on_error(self):
        username = f"test-{uuid4()}"
        try:
            with self.atomic():
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
        with self.atomic():
            User.objects.create(username=username)
            connection.close()
        assert not User.objects.filter(username=username).exists()

    def test_savepoints_are_rolled_back_on_error(self):
        username_1 = f"test-{uuid4()}"
        username_2 = f"test-{uuid4()}"
        with self.atomic():
            User.objects.create(username=username_1)
            try:
                with self.atomic():
                    User.objects.create(username=username_2)
                    raise BreakTransaction()
            except BreakTransaction:
                pass
        assert User.objects.filter(username=username_1).exists()
        assert not User.objects.filter(username=username_2).exists()


class TestDjangoIntegration(BaseTest):
    """
    Test bus/django transactions integration
    """

    def test_bus_is_bind(
        self, connection: CqbusDjangoTransactionBridge, bus: MessageBus
    ):
        """
        Bus should be automatically bind through DATABASES->MESSAGE_BUS option
        """
        assert connection.cq_bus is bus

    def test_bus_tracks_transaction_stack(
        self,
        bus: MessageBus,
    ):
        assert isinstance(bus.running_context, SqlTransactionManager)
        manager: SqlTransactionManager = bus.running_context

        # In autocommit OFF, there's always a transaction is progress
        if self.autocommit:
            offset = 0
            assert not manager.in_transaction
        else:
            offset = 1
            assert manager.in_transaction
        assert len(manager.context.stack) == offset

        with self.atomic():
            assert len(manager.context.stack) == 1 + offset
            with self.atomic():
                assert len(manager.context.stack) == 2 + offset
                with self.atomic(savepoint=False):
                    assert len(manager.context.stack) == 2 + offset

        if self.autocommit:
            assert not manager.in_transaction
        else:
            assert manager.in_transaction
        assert len(manager.context.stack) == offset

    def test_events_are_handled_on_commit(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,
        user_created_handler: EventHandler,
    ):
        username = f"test-{uuid4()}"
        cmd = CreateUserCommand(username=username)
        with self.atomic():
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
        create_user_handler: CommandHandler,  # set up the handler
        user_created_handler: EventHandler,
    ):
        username = f"test-{uuid4()}"
        cmd = CreateUserCommand(username=username)
        try:
            with self.atomic():
                bus.handle_command(cmd)
                raise BreakTransaction()
        except BreakTransaction:
            pass
        assert not User.objects.filter(username=username).exists()
        assert not user_created_handler.calls

    def test_events_are_discarded_on_close(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,  # set up the handler
        user_created_handler: EventHandler,
        connection: CqbusDjangoTransactionBridge,
    ):
        username = f"test-{uuid4()}"
        cmd = CreateUserCommand(username=username)
        with self.atomic():
            bus.handle_command(cmd)
            connection.close()
        assert not User.objects.filter(username=username).exists()
        assert not user_created_handler.calls

    def test_events_are_discarded_on_savepoint_rollback(
        self,
        bus: MessageBus,
        create_user_handler: CommandHandler,  # set up the handler
        user_created_handler: EventHandler,
    ):
        username_1 = f"test-{uuid4()}"
        username_2 = f"test-{uuid4()}"
        with self.atomic():
            bus.handle_command(CreateUserCommand(username=username_1))
            try:
                with self.atomic():
                    bus.handle_command(CreateUserCommand(username=username_2))
                    raise BreakTransaction()
            except BreakTransaction:
                pass
        assert not User.objects.filter(username=username_2).exists()
        user: User = User.objects.get(username=username_1)
        assert len(user_created_handler.calls) == 1
        assert user_created_handler.calls[0].id == user.id
        assert user_created_handler.calls[0].username == username_1
