import json
import time

import django
from django.conf import settings

from evaluation_system.misc import config

SETTINGS = dict(TIME_ZONE="UTC", USE_TZ=False)
config.reloadConfiguration()
# Application definition
SETTINGS["INSTALLED_APPS"] = (
    "django.contrib.auth",  # We need this to access user groups
    "django.contrib.flatpages",
    "django.contrib.contenttypes",
    "django.contrib.sites",
)
SETTINGS["DATABASES"] = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "CONN_HEALTH_CHECKS": True,
        "CONN_MAX_AGE": 0,
        "NAME": config.get(config.DB_DB),
        "USER": config.get(config.DB_USER),
        "PASSWORD": config.get(config.DB_PASSWD),
        "HOST": config.get(
            config.DB_HOST
        ),  # Or an IP Address that your DB is hosted on
        "PORT": config.get(str(config.DB_PORT), "3306"),
    }
}
try:
    settings.configure(**SETTINGS)
    django.setup()
except RuntimeError:
    pass
