import os
import django
from django.db import connection

from cq.contrib.django.databases import patch_django_atomic


def setup_django():
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.integration.django.testapp.settings"

    patch_django_atomic()
    django.setup()

    with connection.cursor() as cursor:
        cursor.execute("drop table if exists testapp_user")
        cursor.execute("create table testapp_user (id serial, username varchar(200))")


# Setup django before any module in this package is loaded.
# This strategy is better than autouse fixtures because it allows us to import
# the User Model at module level instead of at function level (expect for fixtures)
setup_django()
