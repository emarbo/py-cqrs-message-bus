from django.db import models
from django.db.transaction import get_connection

from cq.bus import MessageBus
from cq.contrib.django.databases import CqbusDjangoTransactionBridge
from tests.integration.django.testapp.events import UserCreatedEvent

# ---------------------------------------
# Utils
# ---------------------------------------


def get_cq_connection(using=None) -> CqbusDjangoTransactionBridge:
    connection = get_connection(using=using)
    if not isinstance(connection, CqbusDjangoTransactionBridge):
        raise Exception("Connection is not CqbusDjangoTransactionBridge")
    return connection


def get_cq_bus(using=None) -> MessageBus:
    connection = get_cq_connection(using)
    if not connection.cq_bus:
        raise Exception("MessageBus not configured yet")
    return connection.cq_bus


# ---------------------------------------
# Managers
# ---------------------------------------


class BusManager(models.Manager):
    """
    Allows fixing the database
    """

    def set_db(self, db: str):
        self._db = db

    @property
    def cq_connection(self) -> CqbusDjangoTransactionBridge:
        return get_cq_connection(self._db)

    @property
    def cq_bus(self) -> MessageBus:
        return get_cq_bus(self._db)


# ---------------------------------------
# Model
# ---------------------------------------


class BusModel(models.Model):
    """
    Provides some generic capabilities
    """

    class Meta:
        abstract = True

    @property
    def cq_connection(self) -> CqbusDjangoTransactionBridge:
        return get_cq_connection(self._state.db)

    @property
    def cq_bus(self) -> MessageBus:
        return get_cq_bus(self._state.db)


class User(BusModel):

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=200)

    objects = BusManager()

    class Meta:
        managed = False
        db_table = "testapp_user"

    def save(self, *args, **kwargs):
        is_new = not self.id

        super().save(*args, **kwargs)

        if is_new:
            event = UserCreatedEvent(id=self.id, username=self.username)
            self.cq_bus.emit_event(event)
