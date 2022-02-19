from django.db import models

from cq.contrib.django.models import BusModel
from tests.fixtures.scenarios.create_user import UserCreatedEvent


class User(BusModel):

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = "testapp_user"

    def save(self, *args, **kwargs):
        is_new = not self.id

        super().save(*args, **kwargs)

        if is_new:
            event = UserCreatedEvent(username=self.username)
            self.uow.emit_event(event)
