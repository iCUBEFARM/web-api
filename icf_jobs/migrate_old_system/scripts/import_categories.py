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
WRITE_CATEGORY_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "category-save-success.txt")
WRITE_CATEGORY_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "category-save-failed.txt")



with open(CATEGORIES_FILE, "rt", encoding="UTF-8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        category_save_success_file = open(WRITE_CATEGORY_SAVED_FILE, "a+")
        category_save_failure_file = open(WRITE_CATEGORY_UNSAVED_FILE, "a+")

        try:
            type_obj = Type.objects.get(slug='entity')
        except Type.DoesNotExist as tdn:
            content_obj = ContentType.objects.get(model='entity')
            type_obj = Type.objects.create(content_type=content_obj)

        for row in dr:

            name_en = row['English'].lstrip().rstrip()
            name_fr = row['French'].lstrip().rstrip()
            name_es = row['Spanish'].lstrip().rstrip()
            try:

                category = Category.objects.get(name__iexact=name_en, type=type_obj)
                if name_fr:
                    category.name_fr = name_fr
                    category.save()
                if name_es:
                    category.name_es = name_es
                    category.save()

            except Category.DoesNotExist as cne:
                if name_es:
                    category = Category.objects.create(name=name_en, name_en=name_en, name_fr=name_fr, name_es=name_es, type=type_obj)
                    category_save_success_file.write("{category}\n".format(category=category.name))
                    logger.info("Created category  -  {category}\n".format(category=category.name))

                else:
                    category = Category.objects.create(name=name_en, name_en=name_en, name_fr=name_fr, type=type_obj)
                    category_save_success_file.write("{category}\n".format(category=category.name))
                    logger.info("Created category  -  {category}\n".format(category=category.name))

            except IntegrityError as ie:
                logger.info(" Could not create category  -  {category},{exception}\n".format(category=name_en, exception=ie))
                category_save_failure_file.write("{category},{exception}\n".format(category=name_en, exception=ie))
                pass

            except Exception as e:
                logger.info(" Could not create category  -  {category},{exception}\n".format(category=name_en, exception=e))
                category_save_failure_file.write("{category},{exception}\n".format(category=name_en, exception=e))
                pass
    finally:
        category_save_success_file.close()
        category_save_failure_file.close()
