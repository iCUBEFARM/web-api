import csv
import os, sys
import random
import shutil

# import PIL
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
from icf_jobs.models import UserJobProfile, UserSkill, Skill, JobPerms
from icf_jobs.migrate_old_system.data.Key_Skills_Dictionary import key_skills_dict, computer_skills_dict, \
    language_skills_dict
from django.db import transaction
from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import Entity, EntityPerms, EntityUser
from icf_jobs.permissions import ICFJobsUserPermManager
import logging


logger = logging.getLogger(__name__)


# cur = con.cursor()

# RECRUITER_COMPANIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "recruiters-companies.csv")
# RECRUITER_COMPANIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-recruiter-users-from-production.csv")
# RECRUITER_COMPANIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-recruiters-nov26.csv")
# RECRUITER_COMPANIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "latest-recruiters-dec7th-production-csv.csv")    ## Dec 7th  data
RECRUITER_COMPANIES_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "test_recruiter_job_admin_Jan16.csv")    ## Jan 16th  data



WRITE_RECRUITER_PERMISSION_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "recruiter_permission_save_success.txt")
WRITE_RECRUITER_PERMISSION_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "recruiter_permission_save_failed.txt")
WRITE_USER_NOT_FOUND_FOR_RECRUITER_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "user_not_found_for_recruiter_permission.txt")
WRITE_ENTITY_NOT_FOUND_FOR_RECRUITER_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "entity_not_found_for_recruiter_permission.txt")

# SKILL_NOT_FOUND_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "skill_not_found.txt")


with open(RECRUITER_COMPANIES_FILE, "r", encoding="UTF-8") as fin:
    # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin)  # comma is default delimiter
    try:
        recruiter_permission_save_success_file = open(WRITE_RECRUITER_PERMISSION_SAVED_FILE, "a+")
        recruiter_permission_save_failure_file = open(WRITE_RECRUITER_PERMISSION_UNSAVED_FILE, "a+")
        user_not_found_for_recruiter_permission_file = open(WRITE_USER_NOT_FOUND_FOR_RECRUITER_FILE, "a+")
        entity_not_found_for_recruiter_permission_file = open(WRITE_ENTITY_NOT_FOUND_FOR_RECRUITER_FILE, "a+")

        for row in dr:
            email = row['user_email'].lstrip().rstrip()
            company_name = row['company_name'].lstrip().rstrip()

            if email and company_name:
                try:
                    with transaction.atomic():
                        user = User.objects.get(email=email)
                        # entity = Entity.objects.get(name=company_name)
                        entity = Entity.objects.filter(name=company_name).first()

                        entity_user, created = EntityUser.objects.get_or_create(user=user, entity=entity)
                        # entity_user_obj = EntityUser()
                        # entity_user_obj.user = user
                        # entity_user_obj.entity = entity
                        # entity_user_obj.save()

                        ICFEntityUserPermManager.add_user_perm(user=user, entity=entity, perm=EntityPerms.ENTITY_USER)
                        ICFJobsUserPermManager.add_user_perm(None, user=user, entity=entity, perm=JobPerms.JOB_ADMIN)
                        # ICFJobsUserPermManager.add_user_perm(user, entity, JobPerms.JOB_ADMIN)
                        recruiter_permission_save_success_file.write("{email}\n".format(email=email))
                        logger.info("Created EntityUser and JobAdmin Permission for user with email - {email}\n".format(email=email))
                except User.DoesNotExist as udn:
                    recruiter_permission_save_failure_file.write("{email}, {exception}\n".format(email=email, exception=udn))
                    user_not_found_for_recruiter_permission_file.write("{email}, {exception}\n".format(email=email, exception=udn))
                    pass
                except Entity.DoesNotExist as edn:
                    recruiter_permission_save_failure_file.write("{entity},{email}, {exception}\n".format(entity=company_name,email=email, exception=edn))
                    entity_not_found_for_recruiter_permission_file.write("{entity},{email}, {exception}\n".format(entity=company_name, email=email, exception=edn))
                    pass

                except Exception as e:
                    recruiter_permission_save_failure_file.write("{email} {exception}\n".format(email=email, exception=e))
                    logger.info("Could not create EntityUser with - {email} {exception}\n".format(email=email, exception=e))
                    pass

    finally:
        recruiter_permission_save_success_file.close()
        recruiter_permission_save_failure_file.close()
        user_not_found_for_recruiter_permission_file.close()
