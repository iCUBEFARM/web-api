import csv
import os, sys



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

from icf_generic.models import Category, Type
from django.db import transaction, IntegrityError
from icf_entity.models import Industry
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

CATEGORIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "Industry_categories__in_all_languages.csv")
WRITE_INDUSTRY_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "industry_save_success.txt")
WRITE_INDUSTRY_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "industry_save_failed.txt")


with open(CATEGORIES_FILE, "rt", encoding="UTF-8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        industry_save_success_file = open(WRITE_INDUSTRY_SAVED_FILE, "a+")
        industry_save_failure_file = open(WRITE_INDUSTRY_UNSAVED_FILE, "a+")

        for row in dr:

            name_en = row['English'].lstrip().rstrip()
            name_fr = row['French'].lstrip().rstrip()
            name_es = row['Spanish'].lstrip().rstrip()
            try:
                industry = Industry.objects.get(industry__iexact=name_en)
                if name_fr:
                    industry.industry_fr = name_fr
                    industry.save()
                if name_es:
                    industry.industry_es = name_es
                    industry.save()

            except Industry.DoesNotExist as ine:
                if name_es:
                    industry = Industry.objects.create(industry=name_en, industry_en=name_en, industry_fr=name_fr, industry_es=name_es)
                    industry_save_success_file.write("{industry_en}\n".format(industry_en=industry.industry))
                    logger.info("Created industry  -  {industry_en},{industry_fr}\n".format(industry_en=name_en, industry_fr=name_fr, industry_es=name_es))
                else:
                    industry = Industry.objects.create(industry=name_en, industry_en=name_en, industry_fr=name_fr)
                    industry_save_success_file.write("{industry_en}\n".format(industry_en=industry.industry))
                    logger.info("Created industry  -  {industry_en},{industry_fr}\n".format(industry_en=name_en, industry_fr=name_fr))

            except IntegrityError as ie:
                logger.info(" Could not create industry  -  {industry},{exception}\n".format(industry=name_en, exception=ie))
                industry_save_failure_file.write("{industry},{exception}\n".format(industry=name_en, exception=ie))
                pass

            except Exception as e:
                logger.info(" Could not create industry  -  {industry},{exception}\n".format(industry=name_en, exception=e))
                industry_save_failure_file.write("{industry},{exception}\n".format(industry=name_en, exception=e))
                pass

    finally:
        industry_save_success_file.close()
        industry_save_failure_file.close()