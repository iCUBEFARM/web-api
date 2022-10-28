import csv
import datetime
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

from icf_entity.models import Entity
from icf_generic.models import Type
from icf_orders.models import CreditDistribution
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

CREDIT_DISTRIBUTION_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "credit_distribution_latest.csv")

WRITE_CREDIT_DISTRIBUTION_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "credit_distribution_save_success.txt")
WRITE_CREDIT_DISTRIBUTION_FAILED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "credit_distribution_save_failed.txt")


with open(CREDIT_DISTRIBUTION_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        credit_distribution_save_success_file = open(WRITE_CREDIT_DISTRIBUTION_SAVED_FILE, "a+")
        credit_distribution_save_failure_file = open(WRITE_CREDIT_DISTRIBUTION_FAILED_FILE, "a+")

        for row in dr:
            entity_id = int(row['entity_id'].lstrip().rstrip())
            type_id = int(row['app_id'].lstrip().rstrip())
            credits = int(row['credits'].lstrip().rstrip())
            updated = row['updated'].lstrip().rstrip()

            if updated:
                updated = datetime.datetime.strptime(updated, "%Y-%m-%d %H:%M:%S.%f+00")

            try:
                with transaction.atomic():
                    app = Type.objects.get(id=type_id)
                    entity = Entity.objects.get(id=entity_id)

                    credit_distribution = CreditDistribution.objects.\
                        create(entity=entity, app=app, credits=credits, updated=updated)

                    credit_distribution_save_success_file.write("credit distribution created successfully,"
                                                           "for entity:{entity}\n".format(entity=entity.name))
                    logger.info("credit distribution created successfully, for entity:{entity}\n".format(entity=entity.name))

            except Type.DoesNotExist as udne:
                credit_distribution_save_failure_file.write("Type not found with id :{id}\n".format(id=type_id))
                logger.info("Type not found.  with id :{id},{exception}\n".format(id=type_id, exception=str(udne)))
                pass

            except Entity.DoesNotExist as edne:
                credit_distribution_save_failure_file.write("entity not found with id :{id}\n".format(id=entity_id))
                logger.info("entity not found.  with id :{id},{exception}\n".format(id=entity_id, exception=str(edne)))
                pass

            except Exception as e:
                credit_distribution_save_failure_file.write("{exception}\n".format(exception=str(e)))
                logger.info("Could not create credit distribution  with - {exception}\n".format(exception=str(e)))
                # pass
    finally:
        credit_distribution_save_success_file.close()
        credit_distribution_save_failure_file.close()