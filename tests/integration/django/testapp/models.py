from django.db import models
from django.db.transaction import get_connection

from cq.bus import MessageBus
from tests.integration.django.testapp.events import UserCreatedEvent


def get_bus(using=None) -> MessageBus:
    connection = get_connection(using=using)
    return connection.cq_bus


class User(models.Model):

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = "testapp_user"

    def save(self, *args, **kwargs):
        is_new = not self.id

        super().save(*args, **kwargs)

        if is_new:
            bus = get_bus(using=kwargs.get("using"))
            event = UserCreatedEvent(id=self.id, username=self.username)
            bus.emit_event(event)
