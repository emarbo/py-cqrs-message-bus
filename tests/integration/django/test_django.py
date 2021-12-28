from tests.integration.django.base import _TestDjangoOrm
from tests.integration.django.base import _TestAutocommitOn


class TestPostgresDjangoOrm(_TestDjangoOrm):
    DB = "postgres"


class TestPostgresAutocommitOn(_TestAutocommitOn):
    DB = "postgres"


class TestSqliteDjangoOrm(_TestDjangoOrm):
    DB = "sqlite"


class TestSqliteAutocommitOn(_TestAutocommitOn):
    DB = "sqlite"
