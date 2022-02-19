import os
import django
from django.db import connections


def setup_django():
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.integration.django.testapp.settings"
    django.setup()

    with connections["default"].cursor() as cursor:
        cursor.execute("drop table if exists testapp_user")
        cursor.execute(
            "create table testapp_user ("
            "   id integer primary key autoincrement,"
            "   username varchar(200) "
            ")"
        )


# Setup django before any module in this package is loaded.
# This strategy is better than autouse fixtures because it allows us to import
# the User Model at module level instead of at function level (expect for fixtures)
setup_django()
