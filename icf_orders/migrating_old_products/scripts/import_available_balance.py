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

from icf_auth.models import User
from icf_entity.models import Entity
from icf_orders.models import AvailableBalance
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

AVAILABLE_BALANCE_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "available_balance_latest.csv")

WRITE_AVAILABLE_BALANCE_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "available_balance_save_success.txt")
WRITE_AVAILABLE_BALANCE_FAILED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "available_balance_save_failed.txt")


with open(AVAILABLE_BALANCE_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        available_balance_save_success_file = open(WRITE_AVAILABLE_BALANCE_SAVED_FILE, "a+")
        available_balance_failure_file = open(WRITE_AVAILABLE_BALANCE_FAILED_FILE, "a+")

        for row in dr:
            entity_id = int(row['entity_id'].lstrip().rstrip())
            user_id = int(row['user_id'].lstrip().rstrip())
            available_credits = int(row['available_credits'].lstrip().rstrip())

            # if updated:
            #     # updated = datetime.datetime.strptime(updated, '%Y-%m-%d %H:%M:%S.%f')
            #     updated = datetime.datetime.strptime(updated, "%Y-%m-%d %H:%M:%S.%f+00")

            try:
                with transaction.atomic():
                    user = User.objects.get(id=user_id)
                    entity = Entity.objects.get(id=entity_id)

                    available_balance = AvailableBalance.objects.\
                        create(entity=entity, user=user, available_credits=available_credits)

                    available_balance_save_success_file.write("available balance created successfully,"
                                                           "for entity:{entity}\n".format(entity=str(available_balance)))
                    logger.info("available balance created successfully, for entity:{entity}\n".format(entity=str(available_balance)))

            except User.DoesNotExist as udne:
                available_balance_failure_file.write("user not found with id :{id}\n".format(id=user_id))
                logger.info("user not found.  with id :{id},{exception}\n".format(id=user_id, exception=str(udne)))
                pass

            except Entity.DoesNotExist as edne:
                available_balance_failure_file.write("entity not found with id :{id}\n".format(id=entity_id))
                logger.info("entity not found.  with id :{id},{exception}\n".format(id=entity_id, exception=str(edne)))
                pass

            except Exception as e:
                available_balance_failure_file.write("{exception}\n".format(exception=str(e)))
                logger.info("Could not create available balance  with - {exception}\n".format(exception=str(e)))
                # pass
    finally:
        available_balance_save_success_file.close()
        available_balance_failure_file.close()