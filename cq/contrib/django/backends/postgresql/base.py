from django.db.backends.postgresql import base

from cq.contrib.django.databases import CqbusDjangoTransactionBridge


class DatabaseWrapper(CqbusDjangoTransactionBridge, base.DatabaseWrapper):
    pass
