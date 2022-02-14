from django.contrib.gis.db.backends.postgis import base

from cq.contrib.django.databases import CqbusDjangoTransactionBridge


class DatabaseWrapper(CqbusDjangoTransactionBridge, base.DatabaseWrapper):
    pass
