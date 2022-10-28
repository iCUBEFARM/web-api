
from icf.settings import *

#DEBUG = False

#SERVER_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'server')


#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'icfdb',
#         'USER': 'icfadmin',
#         'PASSWORD': 'icfadmin',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

WEBPACK_LOADER = {
   'DEFAULT': {
            'BUNDLE_DIR_NAME': 'bundles/',
            'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.prod.json'),
        }
}

# Twilio live account
TWILIO_ACCOUNT_SID = "ACbdf0ee506ca8bf961db2ce12cf9cebef"
TWILIO_AUTH_TOKEN = "c8e029fbd713bfe61f54d60d513addc4"
TWILIO_FROM_NUM = "+18322517576"
