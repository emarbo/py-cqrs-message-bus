from django.db.backends.sqlite3 import base

from cq.contrib.django.databases import CqbusDjangoTransactionBridge


class DatabaseWrapper(CqbusDjangoTransactionBridge, base.DatabaseWrapper):
    pass
