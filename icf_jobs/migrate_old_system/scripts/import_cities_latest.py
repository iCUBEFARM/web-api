import csv
import os, sys
import random
import shutil

import PIL
from allauth.account import signals
from pip._vendor.distlib.compat import raw_input

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "CAMEROON.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "DR CANGO.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "EQUATORIAL GUINEA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "FRANCE.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "GABON.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "INDIA.csv")             ### not done due to error
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "INDIA_TEMP.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "IVORY COAST.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "NETHERLANDS.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "NIGERIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "SCOTLAND.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "SPAIN.csv")         ### not done due to error
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "SPAIN_TEMP.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "USA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "MADAGASCAR.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ETHIOPIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ZIMBABWE.csv")
CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "KENYA.csv")
WRITE_CITY_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-save-success.txt")
WRITE_CITY_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-save-failed.txt")


with open(CITIES_FILE, "rt", encoding="UTF-8") as fin: # `with` statement available in 2.5+

    # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin)  # comma is default delimiter
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

            country_en = row['COUNTRY_EN'].lstrip().rstrip()
            country_fr = row['COUNTRY_FR'].lstrip().rstrip()
            country_es = row['COUNTRY_ES'].lstrip().rstrip()

            state_en = row['STATE_EN'].lstrip().rstrip()
            state_fr = row['STATE_FR'].lstrip().rstrip()
            state_es = row['STATE_ES'].lstrip().rstrip()

            city_en = row['CITY_EN'].lstrip().rstrip()
            city_fr = row['CITY_FR'].lstrip().rstrip()
            city_es = row['CITY_ES'].lstrip().rstrip()

            with transaction.atomic():
                if country_en:
                    try:
                        # country_name = country_name.lower()
                        country = Country.objects.get(country__iexact=country_en)
                    except Country.DoesNotExist as cdne:
                        country = Country.objects.create(country=country_en,
                                                         country_fr=country_fr,
                                                         country_es=country_es)

                if state_en:
                    try:
                        # state_name = state_name.lower()
                        state = State.objects.get(state__iexact=state_en, country=country)
                    except State.DoesNotExist as sde:
                        state = State.objects.create(state=state_en, state_fr=state_fr,
                                                     state_es=state_es, country=country)

                if city_en:
                    try:
                        # city_name = city_name.lower()
                        city = City.objects.get(city__iexact=city_en, state=state)
                    except City.DoesNotExist as cde:
                        city = City.objects.create(city=city_en, city_fr=city_fr,
                                                   city_es=city_es, state=state)
                        city_save_success_file.write("{city}\n".format(city=city))

                # else:
                #     city = City.objects.create(city=state_name, state=state)
                #     city_save_success_file.write("{city}\n".format(city=city))

    except Exception as e:
        city_save_failure_file.write("{country_en}, {state_en}, {city_en}, {exception}\n".format(country_en=country_en,
            state_en=state_en, city_en=city_en, exception=str(e)))
        logger.info("Could not create city with - {city},{exception}".format(city=city_en, exception=e))

    finally:
        city_save_success_file.close()
        city_save_failure_file.close()