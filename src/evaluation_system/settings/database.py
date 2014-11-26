from django.conf import settings

import json,time

SETTINGS = dict()
SETTINGS['DATABASES'] = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'evaluationsystem',
        'USER': 'evaluationsystem',
        'PASSWORD': 'miklip',
        'HOST': '136.172.30.208',   # Or an IP Address that your DB is hosted on
        'PORT': '3306',

    }
}

try:
    settings.configure(**SETTINGS)
except:
    pass
