import typing as t

from django.db.models import Model
from django.db.transaction import get_connection

from mb.exceptions import UowContextRequired

if t.TYPE_CHECKING:
    from mb.unit_of_work.base import UnitOfWork


class BusModel(Model):
    class Meta:
        abstract = True

    @property
    def uow(self) -> "UnitOfWork":
        connection = get_connection(using=self._state.db)

        uow: t.Optional["UnitOfWork"] = getattr(connection, "uow", None)
        if not uow:
            raise UowContextRequired(
                "This instance is not attached ot any UnitOfWork. "
                "Did you forget opening the bus transaction (with uow:...)? "
            )
        return uow
