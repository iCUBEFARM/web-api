import csv
import os, sys
import random
import shutil

import PIL
from allauth.account import signals
from pip._vendor.distlib.compat import raw_input



FILE_DIR=os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# This is so Django knows where to find stuff.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "icf.settings")
sys.path.append(PROJ_PATH)

# This is so my local_settings.py gets loaded.
os.chdir(PROJ_PATH)

# This is so models get loaded.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from allauth.utils import generate_unique_username
import datetime
from icf_generic.models import City, Country, State
from django.db import transaction
from icf_auth.migrate_old_system.Helper import Helper
from django.core.files import File
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

# USERS_FILE = os.path.join(FILE_DIR, "temp_data.csv")
CITIES_FILE = os.path.join(FILE_DIR, "cities-system.csv")
WRITE_CITY_SAVED_FILE = os.path.join(FILE_DIR, "city-save-success.csv")
WRITE_CITY_UNSAVED_FILE = os.path.join(FILE_DIR, "city-save-failed.csv")



with open(CITIES_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        city_save_success_file = open(WRITE_CITY_SAVED_FILE, "a+")
        city_save_failure_file = open(WRITE_CITY_UNSAVED_FILE, "a+")

        try:
            country = Country.objects.get(country='Uganda')
            state = State.objects.get(country=country)
        except Country.DoesNotExist as cdne:
            raise
        except State.DoesNotExist as cdne:
            raise

        for row in dr:

            city = row['registered_address_city']
            if city:
                try:
                    with transaction.atomic():
                        city = City.objects.create(city=city, state=state)
                        city_save_success_file.write("{city}\n".format(city=city,state=state))
                except Exception as e:
                    raise
                    # city_save_failure_file.write("{city}\n".format(city=city,state=state))
                    # logger.info("Could not create city with - {city},{exception}".format(city = city,exception = e))
    except Exception as e:
        city_save_failure_file.write("{city}\n".format(city=city, state=state))
        logger.info("Could not create city with - {city},{exception}".format(city=city, exception=e))

    finally:
        city_save_success_file.close()
        city_save_failure_file.close()