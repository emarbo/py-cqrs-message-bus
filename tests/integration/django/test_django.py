import contextlib

import pytest
from mb.bus import MessageBus
from mb.contrib.django.exceptions import DjangoUnitOfWorkBindError

from mb.contrib.django.unit_of_work import DjangoUnitOfWork
from tests.unit.unit_of_work.base import _TestTransactionalUnitOfWork


class TestNestedUnitOfWork(
    _TestTransactionalUnitOfWork[DjangoUnitOfWork],
):
    @contextlib.contextmanager
    def open_context(self, uow: DjangoUnitOfWork):
        with uow.atomic():
            yield

    def user_exists(self, username: str):
        from tests.integration.django.testapp.models import User

        return User.objects.filter(username=username).exists()


def test_cannot_mix_uow_in_the_same_transaction(bus: MessageBus):
    """
    Once an uow is bound, it is bound until the end of the current database
    transaction. No other uow can be bound.
    """
    with DjangoUnitOfWork(bus):
        with pytest.raises(DjangoUnitOfWorkBindError):
            with DjangoUnitOfWork(bus):
                pass
