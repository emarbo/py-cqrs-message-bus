import typing as t

from django.db.models import Model
from django.db.transaction import get_connection

from cq.exceptions import UowContextRequired

if t.TYPE_CHECKING:
    from cq.unit_of_work.base import UnitOfWork
    from cq.bus.bus import MessageBus


class BusModel(Model):
    @property
    def bus(self) -> "MessageBus":
        connection = get_connection(using=self._state.db)

        uow: t.Optional["UnitOfWork"] = getattr(connection, "uow", None)
        if not uow:
            raise UowContextRequired(
                "This instance is not attached ot any UnitOfWork. "
                "Did you forget opening the bus transaction (with uow:...)? "
            )
        return uow.bus
