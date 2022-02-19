from cq.contrib.django.unit_of_work import DjangoUnitOfWork

from tests.unit.unit_of_work.base import _TestUnitOfWork
from tests.unit.unit_of_work.base import _TestTransactionalUnitOfWork


# The local conftest configures the create_user scneario to work
# with the Django database models. Actually, the models are who
# emit the events on the UnitOfWork provided by the ModelBus parent


class TestNestedUnitOfWork(
    _TestUnitOfWork[DjangoUnitOfWork],
    _TestTransactionalUnitOfWork[DjangoUnitOfWork],
):
    pass
