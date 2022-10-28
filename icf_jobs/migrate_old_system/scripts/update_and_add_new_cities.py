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

# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CAMEROON.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "DOMINICAN REPUBLIC OF CONGO.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "EQUATORIAL GUINEA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "FRANCE.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "GABON.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "INDIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "IVORY COAST.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "NETHERLANDS.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "NIGERIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "SCOTLAND.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "SPAIN.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "USA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "FINLAND.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "GUINEA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "NIGERIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ANGOLA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ALGERIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "BELGIUM.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "BENIN.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "BURKINA FASO.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CAPE VERDE.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CENTRAL AFRICAN REPUBLIC.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CHAD.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ESTONIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "GHANA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "IRELAND.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ITALY.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "MALI.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "MOROCCO.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "RWANDA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "SENEGAL.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "SOUTH AFRICA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "TOGO.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "UNITED KINGDOM.csv")
# ------------------------------------------------
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ARGENTINA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "BOLIVIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CANADA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CHILE.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CHINA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "COSTA RICA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CUBA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ECUADOR.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "INDONESIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "MALAYSIA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "MEXICO.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "PANAMA.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "PARAGUAY.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "PERU.csv")
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "VENEZUELA.csv")
CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "PHILIPPINES.csv")





# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "ERITREA.csv") ### processing failed
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "GERMANY.csv") ### processing failed
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "KAZAKHSTAN.csv")  ### excel data not there
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "EL SALVADOR.csv") ### excel data not there
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "CAMBODIA.csv") ### excel data not there
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "MALTA.csv")  ### excel data is not proper
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "TUNISIA.csv") ### excel data is not proper
# CITIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "countries", "COLOMBIA.csv") ### excel data is not proper

WRITE_CITY_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-save-success.txt")
WRITE_CITY_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-save-failed.txt")
WRITE_CITY_UPDATED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "city-update-success.txt")



with open(CITIES_FILE, "rt", encoding="UTF-8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        city_save_success_file = open(WRITE_CITY_SAVED_FILE, "a+")
        city_save_failure_file = open(WRITE_CITY_UNSAVED_FILE, "a+")
        city_update_success_file = open(WRITE_CITY_UPDATED_FILE, "a+")

        # try:
        #     country = Country.objects.get(country='Uganda')
        #     state = State.objects.get(country=country)
        # except Country.DoesNotExist as cdne:
        #     raise
        # except State.DoesNotExist as cdne:
        #     raise

        for row in dr:

            country_name_en = row['COUNTRY_EN']
            country_name_fr = row['COUNTRY_FR']
            country_name_es = row['COUNTRY_ES']
            country_code = row['COUNTRY_CODE']

            state_name_en = row['STATE_EN']
            state_name_fr = row['STATE_FR']
            state_name_es = row['STATE_ES']
            state_code = row['STATE_CODE']

            city_name_en = row['CITY_EN']
            city_name_fr = row['CITY_FR']
            city_name_es = row['CITY_ES']

            with transaction.atomic():
                if country_name_en:
                    # country = Country.objects.get(country_en__iexact=country_name_en)
                    country_name_en = country_name_en.lstrip().rstrip()
                    country, created = Country.objects.get_or_create(country__iexact=country_name_en)
                    country.country_en = country_name_en
                    country.save()
                    if country_name_fr:
                        country_name_fr = country_name_fr.lstrip().rstrip()
                        country.country_fr = country_name_fr
                        country.save()
                    if country_name_es:
                        country_name_es = country_name_es.lstrip().rstrip()
                        country.country_es = country_name_es
                        country.save()
                    if country_code:
                        country_code = country_code.lstrip().rstrip()
                        country.code = country_code
                        country.save()

                    # except Country.DoesNotExist as cdne:
                    #     country = Country.objects.create(country_en=country_name_en)

                if state_name_en:
                    state_name_en = state_name_en.lstrip().rstrip()
                    state, created = State.objects.get_or_create(state__iexact=state_name_en, country=country)
                    state.state_en = state_name_en
                    state.save()
                    # state = State.objects.get(state__iexact=state_name_en)
                    if state_name_fr:
                        state_name_fr = state_name_fr.lstrip().rstrip()
                        state.state_fr = state_name_fr
                        state.save()
                    if state_name_es:
                        state_name_es = state_name_es.lstrip().rstrip()
                        state.state_es = state_name_es
                        state.save()
                    if state_code:
                        state_code = state_code.lstrip().rstrip()
                        state.code = state_code
                        state.save()

                if city_name_en:
                    city_name_en = city_name_en.lstrip().rstrip()
                    city, created = City.objects.get_or_create(city__iexact=city_name_en, state=state)
                    city.city_en = city_name_en
                    city.save()
                    if city_name_fr:
                        city_name_fr = city_name_fr.lstrip().rstrip()
                        city.city_fr = city_name_fr
                        city.save()
                    if city_name_es:
                        city_name_es = city_name_es.lstrip().rstrip()
                        city.city_es = city_name_es
                        city.save()
                    # if created:
                    city_save_success_file.write("{city}\n".format(city=city))
                    # if not created:
                    #     city_update_success_file.write("{city}\n".format(city=city))

    except Exception as e:
        city_save_failure_file.write("{country_name_en}, {state_name_en}, {city_name_en} ,{exception}\n".format(country_name_en=country_name_en, state_name_en=state_name_en, city_name_en=city_name_en, exception=e))
        logger.info("Could not create city with - {city},{exception}".format(city=city_name_en, exception=e))

    finally:
        city_save_success_file.close()
        city_save_failure_file.close()