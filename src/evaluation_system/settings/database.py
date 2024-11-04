from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import django
from django.conf import settings
from evaluation_system.misc import config
from evaluation_system.misc.config import reloadConfiguration

SETTINGS = dict(
    TIME_ZONE="UTC",
    USE_TZ=False,
    ATOMIC_REQUESTS=True,
    CONN_HEALTH_CHECKS=True,
)
# DB_LOADED: bool = False
# DB_OVERRIDDEN: bool = False
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
        "NAME": config.get(config.DB_DB) or "",
        "USER": config.get(config.DB_USER) or "",
        "PASSWORD": config.get(config.DB_PASSWD) or "",
        "HOST": config.get(config.DB_HOST)
        or "",  # Or an IP Address that your DB is hosted on
        "PORT": config.get(str(config.DB_PORT), "3306"),
    }
}

try:
    settings.configure(**SETTINGS)
    django.setup()
except RuntimeError:
    pass


def reconfigure_django(config_file: Optional[Path] = None) -> None:
    """Reconfigure the django settings."""
    django_settings: Dict[str, Any] = deepcopy(SETTINGS)
    reloadConfiguration(config_file)
    django_settings["DATABASES"] = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": config.get(config.DB_DB) or "",
            "USER": config.get(config.DB_USER) or "",
            "PASSWORD": config.get(config.DB_PASSWD) or "",
            "HOST": config.get(config.DB_HOST) or "",
            "PORT": config.get(str(config.DB_PORT), "3306"),
        }
    }
    try:
        settings.configure(**django_settings)
        django.setup()
    except RuntimeError:
        for key, value in django_settings["DATABASES"]["default"].items():
            settings.DATABASES["default"][key] = value
