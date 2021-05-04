from django.conf import settings
from evaluation_system.misc import config

import json,time
import django

SETTINGS = dict()

try:
    # Application definition
    SETTINGS['INSTALLED_APPS'] = (
        'django.contrib.flatpages',
	'django.contrib.auth',  # We need this to access user groups
        'django.contrib.sites'
    )
    SETTINGS['DATABASES'] = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config.get(config.DB_DB),
            'USER': config.get(config.DB_USER),
            'PASSWORD': config.get(config.DB_PASSWD),
            'HOST': config.get(config.DB_HOST),   # Or an IP Address that your DB is hosted on
            'PORT': '3306',

        }
    }
    settings.configure(**SETTINGS)
    django.setup()
except:
    pass
