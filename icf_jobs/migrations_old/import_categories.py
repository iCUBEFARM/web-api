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

from icf_generic.models import City, Country, State, Category, Type
from django.db import transaction, IntegrityError
from icf_entity.models import Industry
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

CATEGORIES_FILE = os.path.join(FILE_DIR, "Industry_Categories.csv")
WRITE_CATEGORY_SAVED_FILE = os.path.join(FILE_DIR, "category-save-success.csv")
WRITE_CATEGORY_UNSAVED_FILE = os.path.join(FILE_DIR, "category-save-failed.csv")



with open(CATEGORIES_FILE, "rt", encoding="windows-1252") as fin: # `with` statement available in 2.5+
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
            # description = row['description_en']
            try:
                with transaction.atomic():
                    industry = Industry.objects.filter(industry__iexact=name_en).first()
                    if not industry:
                        industry = Industry.objects.create(industry=name_en, industry_en=name_en, industry_fr=name_fr)
                        # industry = Industry.objects.create(industry=name_en)
                    category = Category.objects.filter(name__iexact=name_en).first()
                    if not category:
                        category = Category.objects.create(name=name_en, type=type_obj)
                    category_save_success_file.write("{category}\n".format(category=category.name))

            except IntegrityError as e:
                category_save_failure_file.write("{category_en},{category_fr}\n".format(category_en=name_en, category_fr=name_fr))
                pass

            except Exception as e:
                category_save_failure_file.write("{category_en},{category_fr}\n".format(category_en=name_en, category_fr=name_fr))
                raise

    except Exception as e:
        logger.info("Could not create Category because of {exception}".format(exception=e))

    finally:
        category_save_success_file.close()
        category_save_failure_file.close()