from django.conf import settings
from evaluation_system.misc import config

import json,time
import django

SETTINGS = dict()

try:
    # Application definition
    SETTINGS['INSTALLED_APPS'] = (
        'django.contrib.auth',  # We need this to access user groups
        'django.contrib.flatpages'
    )
    SETTINGS['DATABASES'] = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/var/autofs/net/home/illing/workspace/evaluation_system/src/evaluation_system/tests/local.db'
        }
    }
    settings.configure(**SETTINGS)
    django.setup()
    print 'TEST SETUP'
except:  # pragma nocover
    print 'WARNING!!!'
    pass
