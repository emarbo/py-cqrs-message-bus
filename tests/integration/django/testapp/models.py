from django.db import models

from mb import get_current_uow
from tests.fixtures.scenarios.create_user import UserCreatedEvent


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
            uow = get_current_uow()
            event = UserCreatedEvent(username=self.username)
            uow.emit_event(event)
