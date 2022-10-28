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

from icf_generic.models import City, Country, State
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "used_cities_old.csv")
WRITE_CITY_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-save-success.csv")
WRITE_CITY_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-save-failed.csv")



with open(CITIES_FILE, "rt", encoding="windows-1252") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        city_save_success_file = open(WRITE_CITY_SAVED_FILE, "a+")
        city_save_failure_file = open(WRITE_CITY_UNSAVED_FILE, "a+")

        # try:
        #     country = Country.objects.get(country='Uganda')
        #     state = State.objects.get(country=country)
        # except Country.DoesNotExist as cdne:
        #     raise
        # except State.DoesNotExist as cdne:
        #     raise

        for row in dr:

            country_name = row['COUNTRY']
            country_name = country_name.lstrip().rstrip()
            state_name = row['REGION']
            state_name = state_name.lstrip().rstrip()

            city_name = row['CITIES']
            city_name = city_name.lstrip().rstrip()

            with transaction.atomic():
                if country_name:
                    try:
                        # country_name = country_name.lower()
                        country = Country.objects.get(country__iexact=country_name)
                    except Country.DoesNotExist as cdne:
                        country = Country.objects.create(country=country_name)

                if state_name:
                    try:
                        # state_name = state_name.lower()
                        state = State.objects.get(state__iexact=state_name)
                    except State.DoesNotExist as sde:
                        state = State.objects.create(state=state_name, country=country)

                if city_name:
                    try:
                        # city_name = city_name.lower()
                        city = City.objects.get(city__iexact=city_name)
                    except City.DoesNotExist as cde:
                        city = City.objects.create(city=city_name, state=state)
                        city_save_success_file.write("{city}\n".format(city=city))
                else:
                    city = City.objects.create(city=state_name, state=state)
                    city_save_success_file.write("{city}\n".format(city=city))

    except Exception as e:
        if city_name:
            city_save_failure_file.write("{city}\n".format(city=city_name))
        else:
            city_save_failure_file.write("{city}\n".format(city=state_name))
        logger.info("Could not create city with - {city},{exception}".format(city=city_name, exception=e))

    finally:
        city_save_success_file.close()
        city_save_failure_file.close()