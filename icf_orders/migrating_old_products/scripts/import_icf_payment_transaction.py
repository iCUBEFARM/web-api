import csv
import datetime
import os, sys
import random
import shutil
from decimal import Decimal

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

from icf_orders.models import ICFPaymentTransaction
from django.db import transaction
from icf_auth.models import User
import logging

logger = logging.getLogger(__name__)

ICF_PAYMENT_TRANSACTION_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "icf_payment_transaction.csv")

WRITE_ICF_PAYMENT_TRANSACTION_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "icf_payment_transaction_save_success.txt")
WRITE_ICF_PAYMENT_TRANSACTION_FAILED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "icf_payment_transaction_save_failed.txt")


with open(ICF_PAYMENT_TRANSACTION_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        icf_payment_transaction_save_success_file = open(WRITE_ICF_PAYMENT_TRANSACTION_SAVED_FILE, "a+")
        icf_payment_transaction_save_failure_file = open(WRITE_ICF_PAYMENT_TRANSACTION_FAILED_FILE, "a+")

        for row in dr:
            payment_type = int(row['payment_type'].lstrip().rstrip())
            req_date = row['req_date'].lstrip().rstrip()
            req_token = row['req_token'].lstrip().rstrip()
            req_desc = row['req_desc'].lstrip().rstrip()
            resp_date = row['resp_date'].lstrip().rstrip()
            resp_status = int(row['resp_status'].lstrip().rstrip())
            resp_error_code = row['resp_error_code'].lstrip().rstrip()
            resp_error_details = row['resp_error_details'].lstrip().rstrip()
            if row['resp_amount_in_cents'].lstrip().rstrip() == "":
                resp_amount_in_cents = None
            else:
                resp_amount_in_cents = Decimal(row['resp_amount_in_cents'].lstrip().rstrip())

            if row['resp_transaction_id'] == "":
                resp_transaction_id = None
            else:
                resp_transaction_id = row['resp_transaction_id'].lstrip().rstrip()
            if row['resp_currency']:
                resp_currency = row['resp_currency'].lstrip().rstrip()
            if row['resp_failure_code']:
                resp_failure_code = row['resp_failure_code'].lstrip().rstrip()
            if row['resp_failure_message']:
                resp_failure_message = row['resp_failure_message'].lstrip().rstrip()
            user_id = int(row['user_id'].lstrip().rstrip())
            if row['req_amount_in_cents'].lstrip().rstrip() == "":
                req_amount_in_cents = None
            else:
                req_amount_in_cents = Decimal(row['req_amount_in_cents'].lstrip().rstrip())
            if row['req_amount_in_dollars']:
                req_amount_in_dollars = Decimal(row['req_amount_in_dollars'].lstrip().rstrip())
            if row['resp_amount_in_dollars'] == "":
                resp_amount_in_dollars = None
            else:
                resp_amount_in_dollars = Decimal(row['resp_amount_in_dollars'].lstrip().rstrip())
            if req_date:
                req_date = datetime.datetime.strptime(req_date, "%Y-%m-%d %H:%M:%S.%f+00")
            if resp_date:
                resp_date = datetime.datetime.strptime(resp_date, "%Y-%m-%d %H:%M:%S.%f+00")

            try:
                with transaction.atomic():
                    # app = Type.objects.get(id=type_id)
                    # entity = Entity.objects.get(id=entity_id)

                    user = User.objects.get(id=user_id)

                    icf_payment_transaction = ICFPaymentTransaction.objects.\
                        create(user=user, payment_type=payment_type, req_date=req_date,
                               req_amount_in_cents=req_amount_in_cents, req_amount_in_dollars=req_amount_in_dollars,
                               req_token=req_token, req_desc=req_desc, resp_date=resp_date, payment_status=resp_status,
                               resp_error_code=resp_error_code, resp_error_details=resp_error_details,
                               resp_amount_in_cents=resp_amount_in_cents, resp_amount_in_dollars=resp_amount_in_dollars,
                               resp_transaction_id=resp_transaction_id, resp_currency=resp_currency,
                               resp_failure_code=resp_failure_code, resp_failure_message=resp_failure_message)


                    icf_payment_transaction_save_success_file.write("icf payment transaction created successfully,"
                                                           "for user:{user}\n".format(user=user.email))
                    logger.info("icf payment transaction created successfully, for user:{user}\n".format(user=user.email))

            except User.DoesNotExist as udne:
                icf_payment_transaction_save_failure_file.write("User not found with id :{id}\n".format(id=user_id))
                logger.info("User not found.  with id :{id},{exception}\n".format(id=user_id, exception=str(udne)))
                pass

            except Exception as e:
                icf_payment_transaction_save_failure_file.write("{exception}\n".format(exception=str(e)))
                logger.info("Could not create icf_payment_transaction  with - {exception}\n".format(exception=str(e)))
                # pass
    finally:
        icf_payment_transaction_save_success_file.close()
        icf_payment_transaction_save_failure_file.close()