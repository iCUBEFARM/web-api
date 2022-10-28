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

from allauth.utils import generate_unique_username
from icf_auth.models import User, UserProfile, UserProfileImage
from icf_jobs.models import JobProfileFileUpload, UserJobProfile, UserReference, UserWorkExperience, Relationship
import datetime
from django.db import transaction, IntegrityError
from icf_auth.migrate_old_system.scripts.Helper import Helper
# import PIL.Image
from PIL import Image
from django.core.files import File
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

# JOB_SEEKER_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "jobseekers-details.csv")
# JOB_SEEKER_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-job-seekers-from-production.csv")
# JOB_SEEKER_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-jobseekers-nov26.csv")
JOB_SEEKER_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "latest-jobseekers-dec7th-production-csv.csv")


# JOB_SEEKER_FILE = os.path.join(FILE_DIR, "job_seeker_temp_data.csv")
WRITE_JOB_SEEKER_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seeker_profile_info_save_success.txt")
WRITE_JOB_SEEKER_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seeker_profile_info_save_failed.txt")
WRITE_JOB_SEEKER_NOT_FOUND_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "users_not_found_for_job_seeker.txt")
WRITE_DATABASE_ERROR_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "database_contraint_failed.txt")


with open(JOB_SEEKER_FILE, "r", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        job_seeker_info_save_success_file = open(WRITE_JOB_SEEKER_SAVED_FILE, "a+")
        job_seeker_save_failure_file = open(WRITE_JOB_SEEKER_UNSAVED_FILE, "a+")
        user_not_found_file = open(WRITE_JOB_SEEKER_NOT_FOUND_FILE, "a+")
        database_error_file = open(WRITE_DATABASE_ERROR_FILE, "a+")
        try:
            relation = Relationship.objects.get(relation__iexact='Other')
        except Relationship.DoesNotExist as rdn:
            relation = Relationship.objects.create(relation='Other', description='Other')

        for row in dr:
            email = row['email'].lstrip().rstrip()
            total_years_experience = row['total_years_experience'].lstrip().rstrip()
            total_months_experience = row['total_months_experience'].lstrip().rstrip()

            current_job_title = row['current_job_title'].lstrip().rstrip()
            current_employer_name = row['current_employer_name'].lstrip().rstrip()
            current_job_contact_person_name = row['current_job_contact_person_name'].lstrip().rstrip()
            current_job_contact_person_email = row['current_job_contact_person_email'].lstrip().rstrip()
            current_job_contact_person_telephone_number = row['current_job_contact_person_telephone_number'].lstrip().rstrip()
            current_job_joining_date = row['current_job_joining_date'].lstrip().rstrip()
            current_job_relieving_date = row['current_job_relieving_date'].lstrip().rstrip()
            current_job_contact_person_telephone_number = row['current_job_contact_person_telephone_number'].lstrip().rstrip()
            current_job_contact_person_telephone_code = row['current_job_contact_person_telephone_code'].lstrip().rstrip()

            previous_1_job_occupation_title_name = row['previous_1_job_occupation_title_name'].lstrip().rstrip()
            previous_1_employer_name = row['previous_1_employer_name'].lstrip().rstrip()
            previous_job_1_contact_person_name = row['previous_job_1_contact_person_name'].lstrip().rstrip()
            previous_job_1_contact_person_email = row['previous_job_1_contact_person_email'].lstrip().rstrip()  # is empty for few rows
            previous_job_1_contact_person_telephone_number = row['previous_job_1_contact_person_telephone_number'].lstrip().rstrip()
            previous_job_1_joining_date = row['previous_job_1_joining_date'].lstrip().rstrip()
            previous_job_1_relieving_date = row['previous_job_1_relieving_date'].lstrip().rstrip()
            previous_job_1_contact_person_telephone_number = row['previous_job_1_contact_person_telephone_number'].lstrip().rstrip()
            previous_job_1_contact_person_telephone_code = row['previous_job_1_contact_person_telephone_code'].lstrip().rstrip()

            previous_2_job_occupation_title_name = row['previous_2_job_occupation_title_name'].lstrip().rstrip()
            previous_job_2_employer_name = row['previous_job_2_employer_name'].lstrip().rstrip()
            previous_job_2_contact_person_name = row['previous_job_2_contact_person_name'].lstrip().rstrip()
            previous_job_2_contact_person_email = row['previous_job_2_contact_person_email'].lstrip().rstrip()
            previous_job_2_contact_person_telephone_number = row['previous_job_2_contact_person_telephone_number'].lstrip().rstrip()
            previous_job_2_joining_date = row['previous_job_2_joining_date'].lstrip().rstrip()
            previous_job_2_relieving_date = row['previous_job_2_relieving_date'].lstrip().rstrip()
            previous_job_2_contact_person_telephone_number = row['previous_job_2_contact_person_telephone_number'].lstrip().rstrip()
            previous_job_2_contact_person_telephone_code = row['previous_job_2_contact_person_telephone_code'].lstrip().rstrip()

            try:
                with transaction.atomic():
                    user = User.objects.get(email=email)
                    user_job_profile = UserJobProfile()
                    user_job_profile.user = user

                    if total_months_experience and total_years_experience:
                        if total_years_experience != '0' and total_months_experience != '0':
                            user_job_profile.has_experience = True
                        user_job_profile.save()
                        job_seeker_info_save_success_file.write("{email}\n".format(email=email))
                        logger.info(" created User Job Profile  with - {email}\n".format(email=email))
                    else:
                        user_job_profile.save()
                        job_seeker_info_save_success_file.write("{email}\n".format(email=email))
                        logger.info(" created User Job Profile  with - {email}\n".format(email=email))

                    # User Work Experience data

                    if previous_2_job_occupation_title_name:
                        user_work_experience_2 = UserWorkExperience()
                        user_work_experience_2.job_profile = user_job_profile
                        user_work_experience_2.job_title = previous_2_job_occupation_title_name
                        if previous_job_2_joining_date:
                            previous_job_2_joining_date = datetime.datetime.strptime(previous_job_2_joining_date, '%m/%d/%Y')
                            user_work_experience_2.worked_from = previous_job_2_joining_date
                        if previous_job_2_relieving_date:
                            previous_job_2_relieving_date = datetime.datetime.strptime(previous_job_2_relieving_date, '%m/%d/%Y')
                            user_work_experience_2.worked_till = previous_job_2_relieving_date
                        user_work_experience_2.entity = previous_job_2_employer_name
                        user_work_experience_2.save()

                    if previous_1_job_occupation_title_name:
                        user_work_experience_1 = UserWorkExperience()
                        user_work_experience_1.job_profile = user_job_profile
                        user_work_experience_1.job_title = previous_1_job_occupation_title_name
                        if previous_job_1_joining_date:
                            previous_job_1_joining_date = datetime.datetime.strptime(previous_job_1_joining_date, '%m/%d/%Y')
                            user_work_experience_1.worked_from = previous_job_1_joining_date
                        if previous_job_1_relieving_date:
                            previous_job_1_relieving_date = datetime.datetime.strptime(previous_job_1_relieving_date, '%m/%d/%Y')
                            user_work_experience_1.worked_till = previous_job_1_relieving_date
                        user_work_experience_1.entity = previous_1_employer_name
                        user_work_experience_1.save()

                    if current_job_title:
                        user_work_experience_current = UserWorkExperience()
                        user_work_experience_current.job_profile = user_job_profile
                        user_work_experience_current.job_title = current_job_title
                        if current_job_joining_date:
                            current_job_joining_date = datetime.datetime.strptime(current_job_joining_date, '%m/%d/%Y')
                            user_work_experience_current.worked_from = current_job_joining_date
                        if current_job_relieving_date:
                            current_job_relieving_date = datetime.datetime.strptime(current_job_relieving_date, '%m/%d/%Y')
                            user_work_experience_current.worked_till = current_job_relieving_date
                        else:
                            user_work_experience_current.worked_till = 'present'
                        user_work_experience_current.entity = current_employer_name
                        user_work_experience_current.save()

                    # User Reference data

                    if previous_job_2_contact_person_name:
                        user_reference_2 = UserReference()
                        user_reference_2.job_profile = user_job_profile
                        user_reference_2.name = previous_job_2_contact_person_name
                        user_reference_2.relation = relation
                        user_reference_2.entity = previous_job_2_employer_name
                        if previous_job_2_contact_person_telephone_code:
                            phone_no = "+{code}{number}".format(code=previous_job_2_contact_person_telephone_code, number=previous_job_2_contact_person_telephone_number)
                            user_reference_2.phone = phone_no
                        if previous_job_2_contact_person_email:
                            user_reference_2.email = previous_job_2_contact_person_email
                        user_reference_2.save()

                    if previous_job_1_contact_person_name:
                        user_reference_1 = UserReference()
                        user_reference_1.job_profile = user_job_profile
                        user_reference_1.name = previous_job_1_contact_person_name
                        user_reference_1.relation = relation
                        user_reference_1.entity = previous_1_employer_name
                        if previous_job_1_contact_person_telephone_code:
                            phone_no = "+{code}{number}".format(code=previous_job_1_contact_person_telephone_code, number=previous_job_1_contact_person_telephone_number)
                            user_reference_1.phone = phone_no
                        if user_reference_1.email:
                            user_reference_1.email = previous_job_1_contact_person_email
                        user_reference_1.save()

                    if current_job_contact_person_name:
                        user_reference_current = UserReference()
                        user_reference_current.job_profile = user_job_profile
                        user_reference_current.name = current_job_contact_person_name
                        user_reference_current.relation = relation
                        user_reference_current.entity = current_employer_name
                        if current_job_contact_person_telephone_code:
                            phone_no = "+{code}{number}".format(code=current_job_contact_person_telephone_code,
                                                                number=current_job_contact_person_telephone_number)
                            user_reference_current.phone = phone_no
                        if current_job_contact_person_email:
                            user_reference_current.email = current_job_contact_person_email
                        user_reference_current.save()

                    # job_seeker_info_save_success_file.write("{email}\n".format(email=email))
                    # logger.info(" created User Job Profile  with - {email}\n".format(email=email))

            except User.DoesNotExist as udn:
                user_not_found_file.write("{email} {exception}\n".format(email=email, exception=udn))
                pass
            except IntegrityError as e:
                database_error_file.write("{email} {exception}\n".format(email=email, exception=e))
                pass

    except Exception as e:
        job_seeker_save_failure_file.write("{email} {exception}\n".format(email=email, exception=e))
        logger.info("Could not create UserJobProfile with - {email} {exception}\n".format(email=email, exception=e))
        pass

    finally:
        job_seeker_info_save_success_file.close()
        job_seeker_save_failure_file.close()
        user_not_found_file.close()