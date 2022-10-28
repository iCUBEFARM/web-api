import csv
import datetime
import os, sys
import random

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
from icf_generic.models import Category, Type, Address, City, Currency
from icf_jobs.migrate_old_system.data.Key_Skills_Dictionary import key_skills_dict, computer_skills_dict, \
    language_skills_dict
from icf_jobs.models import Occupation, JobType, Job, EducationLevel, Skill, JobSkill, SalaryFrequency, JobUserApplied
import logging

logger = logging.getLogger(__name__)

# JOB_USER_APPLIED_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "job-applicants.csv")
# JOB_USER_APPLIED_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-job-applicants-nov26-Excel.csv")
# JOB_USER_APPLIED_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "latest-job-applicants-dec7th-production-csv.csv")
JOB_USER_APPLIED_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "user_job_applied_dec_7th_data_part.csv")


WRITE_JOB_USER_APPLIED_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job-user-applied-success.txt")
WRITE_JOB_USER_APPLIED_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job-user-applied-failed.txt")
WRITE_NOT_FOUND_FOR_JOB__APPLIED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "user_not_found_for_job-user-applied.txt")




with open(JOB_USER_APPLIED_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        job_user_applied_save_success_file = open(WRITE_JOB_USER_APPLIED_SAVED_FILE, "a+")
        job_user_applied_save_failure_file = open(WRITE_JOB_USER_APPLIED_UNSAVED_FILE, "a+")
        user_not_found_for_job_user_applied_file = open(WRITE_NOT_FOUND_FOR_JOB__APPLIED_FILE, "a+")

        for row in dr:
            job_title = row['job_title'].lstrip().rstrip()
            user_email = row['email'].lstrip().rstrip()
            # entity_name = row['name'].lstrip().rstrip()
            applied_date = row['applied_date'].lstrip().rstrip()
            decision = row['decision'].lstrip().rstrip()

            if applied_date:
                # start_date = datetime.datetime(start_date)
                # start_date_str = str(start_date)
                applied_date = datetime.datetime.strptime(applied_date, '%m/%d/%y %H:%M')

            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist as ue:
                user_not_found_for_job_user_applied_file.write("User Does  not exist - {user_email}\n".format(user_email=user_email))
                job_user_applied_save_failure_file.write("User Does  not exist - {user_email}\n".format(user_email=user_email))
                pass

            try:
                job = Job.objects.get(title__iexact=job_title)
            except Job.DoesNotExist as jdn:
                job_user_applied_save_failure_file.write("Job Does  not exist - {job_title}\n".format(job_title=job_title))
                pass
            status = JobUserApplied.NEW
            if decision:
                if decision == 'n':
                    status = JobUserApplied.NO
                elif decision == 'm':
                    status = JobUserApplied.MAY_BE
                else:
                    status = JobUserApplied.NEW

            if job and user:
                job_user_applied = JobUserApplied.objects.create(job=job, user=user, updated=applied_date, status=status)
                job_user_applied_save_success_file.write("Created Job Applicant- {job}\n".format(job=job_title))
                logger.info("Created Job Applicant - {job}\n".format(job=job_title))

    except Exception as e:
        job_user_applied_save_failure_file.write("{job},{exception}\n".format(job=job_title, exception=e))
        logger.info("Could not create job applicant  with - {job},{exception}\n".format(job=job_title, exception=e))
        pass
    finally:
        job_user_applied_save_success_file.close()
        job_user_applied_save_failure_file.close()
