import contextlib
from cq.contrib.django.unit_of_work import DjangoUnitOfWork

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
