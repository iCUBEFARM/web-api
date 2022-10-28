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
from icf_jobs.migrate_old_system.scripts.Utility import Utility
from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import Sector, Entity, CompanySize, Logo, EntityUser, EntityPerms
from icf_generic.models import Address, Category, City
from icf_orders.models import AvailableBalance, CreditHistory, CreditAction
from django.db import transaction
import PIL.Image
from django.core.files import File
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

ENTITY_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "credit_history_latest.csv")


WRITE_CREDIT_HISTORY_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "credit-history-save-success.txt")
WRITE_CREDIT_HISTORY_FAILED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "credit-history-save-failed.txt")
# WRITE_NOT_FOUND_FOR_ENTITY_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "user_not_found_for_entity.txt")


with open(ENTITY_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        credit_history_save_success_file = open(WRITE_CREDIT_HISTORY_SAVED_FILE, "a+")
        credit_history_failure_file = open(WRITE_CREDIT_HISTORY_FAILED_FILE, "a+")

        for row in dr:
            entity_id = int(row['entity_id'].lstrip().rstrip())
            user_id = int(row['user_id'].lstrip().rstrip())
            action_id = int(row['action_id'].lstrip().rstrip())
            debits = int(row['debits'].lstrip().rstrip())
            updated = row['updated'].lstrip().rstrip()
            available_credits = int(row['available_credits'].lstrip().rstrip())

            if updated:
                # updated = datetime.datetime.strptime(updated, '%m/%d/%Y %H:%M')
                # updated = datetime.datetime.strptime(updated, '%Y-%m-%d %H:%M:%S.%f')
                updated = datetime.datetime.strptime(updated, "%Y-%m-%d %H:%M:%S.%f+00")

            try:
                with transaction.atomic():

                    user = User.objects.get(id=user_id)
                    entity = Entity.objects.get(id=entity_id)
                    credit_action = CreditAction.objects.get(id=action_id)

                    credit_history = CreditHistory.objects.\
                        create(entity=entity, user=user, action=credit_action, debits=debits,
                               available_credits=available_credits, updated=updated, is_active=True)

                    credit_history_save_success_file.write("credit history created successfully,"
                                                           "for entity:{entity}\n".format(entity=str(credit_history)))
                    logger.info("credit history created successfully, for entity:{entity}\n".format(entity=str(credit_history)))

            except User.DoesNotExist as udne:
                credit_history_failure_file.write("user not found with id :{id}\n".format(id=user_id))
                logger.info("user not found.  with id :{id},{exception}\n".format(id=user_id, exception=str(udne)))
                pass

            except Entity.DoesNotExist as edne:
                credit_history_failure_file.write("entity not found with id :{id}\n".format(id=entity_id))
                logger.info("entity not found.  with id :{id},{exception}\n".format(id=entity_id, exception=str(edne)))
                pass

            except CreditAction.DoesNotExist as adne:
                credit_history_failure_file.write("credit action  not found with id :{id}\n".format(id=action_id))
                logger.info("entity not found. with id :{id},{exception}\n".format(id=action_id, exception=str(adne)))
                pass

            except Exception as e:
                # entity_save_failure_file.write("{entity}\n".format(entity=entity.name))
                credit_history_failure_file.write("{exception}\n".format(exception=str(e)))
                logger.info("Could not create Credit history  with - {exception}\n".format(exception=str(e)))
                # pass
    finally:
        credit_history_save_success_file.close()
        credit_history_failure_file.close()