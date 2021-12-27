import os

# --------------------------------------
# General
# --------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_NAME = "TestApp"

# --------------------------------------
# Security
# --------------------------------------

SECRET_KEY = "secret"

# --------------------------------------
# Testing
# --------------------------------------

TESTING = True

# --------------------------------------
# Networking
# --------------------------------------

ALLOWED_HOSTS: list[str] = []


# --------------------------------------
# Application definition
# --------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "tests.integration.django.testapp.apps.TestAppConfig",
]

MIDDLEWARE: list[str] = []

# --------------------------------------
# Database
# --------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "cq.contrib.django.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# --------------------------------------
# i18n
# --------------------------------------

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = False

# --------------------------------------
# Static files
# --------------------------------------

STATIC_URL = None
STATIC_ROOT = None

# ---------------------------------------
# Logging
# ---------------------------------------

LOGGING_CONFIG = None
