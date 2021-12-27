from django.db.transaction import atomic

from cq.bus import MessageBus
from cq.databases import SqlTransactionManager
from tests.integration.django.testapp.commands import CreateUserCommand
from tests.integration.django.conftest import CommandHandler
from tests.integration.django.conftest import EventHandler
from tests.integration.django.testapp.models import User


def test_django_orm():
    """
    Test Django ORM works with cq.contrib.django.backends.postgresql
    """
    User.objects.create(username="test")
    assert len(list(User.objects.all())) > 0


def test_transaction_is_tracked(
    bus: MessageBus,
):
    assert isinstance(bus.transaction_manager, SqlTransactionManager)
    manager: SqlTransactionManager = bus.transaction_manager

    assert not manager.in_transaction
    with atomic():
        assert manager.in_transaction
    assert not manager.in_transaction


def test_events_are_handled_on_commit(
    bus: MessageBus,
    create_user_handler: CommandHandler,
    user_created_handler: EventHandler,
):
    with atomic():
        cmd = CreateUserCommand(username="pepe")
        user = bus.handle_command(cmd)
        assert create_user_handler.calls
        assert create_user_handler.calls[0] == cmd
        assert not user_created_handler.calls
    assert user_created_handler.calls
    assert user_created_handler.calls[0].id == user.id
    assert user_created_handler.calls[0].username == "pepe"
