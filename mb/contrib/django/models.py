import typing as t

from django.db.models import Model

from mb.exceptions import UowTransactionError
from mb.globals import get_current_uow

if t.TYPE_CHECKING:
    from mb.contrib.django.unit_of_work import DjangoUnitOfWork


class BusModel(Model):
    class Meta:
        abstract = True

    @property
    def uow(self) -> "DjangoUnitOfWork":
        uow: t.Optional["DjangoUnitOfWork"] = get_current_uow()
        if not uow:
            raise UowTransactionError(
                "This instance is not attached ot any DjangoUnitOfWork. "
                "Did you forget opening the bus transaction (with uow:...)? "
            )
        return uow
