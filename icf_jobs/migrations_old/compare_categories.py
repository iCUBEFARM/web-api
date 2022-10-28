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

from icf_generic.models import City, Country, State, Category, Type
from django.db import transaction
from icf_entity.models import Industry
from icf_jobs.migrations_old import Utility
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

# CATEGORIES_FILE = os.path.join(FILE_DIR, "Industry_Categories.csv")
CATEGORIES_FILE = os.path.join(FILE_DIR, "industries.csv")
WRITE_CATEGORY_MATCHED_FILE = os.path.join(FILE_DIR, "category_match_success_file.csv")
WRITE_CATEGORY_NOT_MATCHED_FILE = os.path.join(FILE_DIR, "non_matching_categories.csv")



with open(CATEGORIES_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        category_match_success_file = open(WRITE_CATEGORY_MATCHED_FILE, "a+")
        category_match_failure_file = open(WRITE_CATEGORY_NOT_MATCHED_FILE, "a+")

        # try:
        #     # type_name = 'entity'
        #     # type_obj = Utility.get_type(type_name)
        #     type_obj = Type.objects.get(slug='entity')
        # except Type.DoesNotExist as tdn:
        #     raise

        for row in dr:

            name = row['name_en']
            # name = row['English']
            # description = row['description_en']
            try:
                name = name.lower()
                category = Category.objects.get(slug=name)
                category_match_success_file.write("{category}\n".format(category=name))
            except Category.DoesNotExist as e:
                category_match_failure_file.write("{category}\n".format(category=name))
                # logger.info(
                #     "Could not create Category with - {category},{exception}".format(category=name, exception=e))

    except Exception as e:
        # category_match_failure_file.write("{category}\n".format(category=name))
        logger.info("Could not create Category with - {category},{exception}".format(category=name, exception=e))

    finally:
        category_match_success_file.close()
        category_match_failure_file.close()