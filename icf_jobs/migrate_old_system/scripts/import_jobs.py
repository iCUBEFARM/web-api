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
from icf_jobs.models import Occupation, JobType, Job, EducationLevel, Skill, JobSkill, SalaryFrequency
import logging

logger = logging.getLogger(__name__)

# JOB_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "updated-extra-jobs-from-production.csv")
# JOB_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-jobs-nov26.csv")
JOB_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "latest-jobs-dec7th-production-csv.csv")      # 7th dec Jobs data


WRITE_JOB_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "jobs-save-success.txt")
WRITE_JOB_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "jobs-save-failed.txt")
WRITE_NOT_FOUND_FOR_USER_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "user_not_found_for_job.txt")
WRITE_KEY_SKILL_NOT_FOUND_FOR_JOB_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "key_skill_not_found_for_job.txt")
WRITE_COMPUTER_SKILL_NOT_FOUND_FOR_JOB_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "computer_skill_not_found_for_job.txt")
WRITE_LANGUAGE_SKILL_NOT_FOUND_FOR_JOB_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "language_skill_not_found_for_job.txt")



with open(JOB_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        job_save_success_file = open(WRITE_JOB_SAVED_FILE, "a+")
        job_save_failure_file = open(WRITE_JOB_UNSAVED_FILE, "a+")
        user_not_found_for_job_file = open(WRITE_NOT_FOUND_FOR_USER_FILE, "a+")
        key_skill_not_found_for_job_file = open(WRITE_KEY_SKILL_NOT_FOUND_FOR_JOB_FILE, "a+")
        computer_skill_not_found_for_job_file = open(WRITE_COMPUTER_SKILL_NOT_FOUND_FOR_JOB_FILE, "a+")
        language_skill_not_found_for_job_file = open(WRITE_LANGUAGE_SKILL_NOT_FOUND_FOR_JOB_FILE, "a+")


        for row in dr:
            title = row['job_title'].lstrip().rstrip()
            owner = row['email'].lstrip().rstrip()
            entity_name = row['name'].lstrip().rstrip()
            description = row['description'].lstrip().rstrip()
            # description = ''
            expiry = row['end_date'].lstrip().rstrip()
            start_date = row['publish_date'].lstrip().rstrip()
            updated_date = row['last_modified_date'].lstrip().rstrip()
            occupation_name = row['description_en'].lstrip().rstrip()
            language_skills_id_string = row['language'].lstrip().rstrip()
            key_skills_id_string = row['keyskils'].lstrip().rstrip()
            computer_skills_id_string = row['computerskills'].lstrip().rstrip()

            try:
                owner = User.objects.get(email=owner)
            except User.DoesNotExist as ue:
                job_save_failure_file.write("User Does  not exist - {owner}\n".format(owner=owner))
                pass

            try:
                entity = Entity.objects.get(name__iexact=entity_name)
            except Entity.DoesNotExist as edn:
                job_save_failure_file.write("Entity Does  not exist - {entity_name}\n".format(entity_name=entity_name))
                pass

            if occupation_name:
                try:
                    # if occupation_name == 'Business, Finance, Information Technology (IT), Human Resources and Administrative Occupations':
                    #     occupation_obj = Occupation.objects.get(name__iexact=occupation_name)
                    # else:
                    occupation_obj = Occupation.objects.get(name__icontains=occupation_name)
                except Occupation.DoesNotExist as one:
                    job_save_failure_file.write("Occupation Does  not exist - {occupation_name}\n".format(occupation_name=occupation_name))
                    pass
            experience_years = row['total_years_experience']
            if experience_years:
                experience_years = int(experience_years)
            else:
                experience_years = 0

            experience_months = row['total_months_experience'].lstrip().rstrip()

            if experience_months:
                experience_months = int(experience_months)
                if experience_months <= 0:
                    experience_months = 0
                else:
                    experience_months = int(experience_months)
            try:
                salary_currency = Currency.objects.get(name__iexact='XAF')
            except Currency.DoesNotExist as cne:
                job_save_failure_file.write("Currency Does  not exist - {Currency}\n".format(Currency='XAF'))
                pass
            try:

                salary_frequency = SalaryFrequency.objects.get(frequency__iexact='/ Month')
            except SalaryFrequency.DoesNotExist as cne:
                job_save_failure_file.write("SalaryFrequency Does  not exist - {SalaryFrequency}\n".format(SalaryFrequency='/ Month'))
                pass
            salary = 0
            salary_is_public = False

            education_level_name = row['education_level_name'].lstrip().rstrip()

            try:
                education_level_obj = EducationLevel.objects.get(level__iexact=education_level_name)
            except EducationLevel.DoesNotExist as en:
                job_save_failure_file.write("EducationLevel Does  not exist - {education_level_name}\n".format(education_level_name=education_level_name))
                pass

            open_positions = int(row['positions'].lstrip().rstrip())
            job_type_name = row['job_type'].lstrip().rstrip()

            try:
                job_type_obj = JobType.objects.get(job_type__iexact=job_type_name)
            except JobType.DoesNotExist as jne:
                job_save_failure_file.write("Job Type Does  not exist - {job_type}\n".format(job_type=job_type_name))
                pass

            location = row['job_location'].lstrip().rstrip()

            city = City.objects.get(city__iexact='Malabo')

            address = Address.objects.create(address_1=location, city=city)

            if expiry:
                # expiry_date = datetime.datetime(expiry)
                # expiry_str = str(expiry_date)
                expiry = datetime.datetime.strptime(expiry, '%m/%d/%Y %H:%M')

            if start_date:
                # start_date = datetime.datetime(start_date)
                # start_date_str = str(start_date)
                start_date = datetime.datetime.strptime(start_date, '%m/%d/%Y %H:%M')

            if updated_date:
                # updated_date = datetime.datetime(updated_date)
                # updated_date_str = str(updated_date)
                updated_date = datetime.datetime.strptime(updated_date, '%m/%d/%Y %H:%M')

            try:
                type = Type.objects.get(slug='job')
            except Type.DoesNotExist as tne:
                raise

            item_type = type

            status = 2

            try:
                category = Category.objects.get(name__iexact='Other')
            except Category.DoesNotExist as cdn:
                type_obj = Type.objects.get(slug='job')
                category = Category.objects.create(name='Other', type=type_obj)

            job = Job.objects.create(title=title, entity=entity, category=category, item_type=item_type, description=description,
                                     location=address, status=status, expiry=expiry, start_date=start_date, owner=owner,
                                     updated=updated_date, occupation=occupation_obj, experience_years=experience_years,
                                     experience_months=experience_months, salary_is_public=salary_is_public,salary=salary,
                                     salary_currency=salary_currency,salary_frequency=salary_frequency,
                                     education_level=education_level_obj, open_positions=open_positions, job_type=job_type_obj)

            job_save_success_file.write("Created Job - {job}\n".format(job=title))
            logger.info("Created Job - {job}\n".format(job=title))

            # Key Skills data
            if key_skills_id_string:
                key_skills_id_string_list = key_skills_id_string.split(',')

                for key_skill_id in key_skills_id_string_list:
                    key_skill_name = key_skills_dict.get(key_skill_id.lstrip().rstrip())
                    try:
                        skill_obj = Skill.objects.get(name_en__iexact=key_skill_name, skill_type='key_skill')
                        job_skill = JobSkill()
                        job_skill.job = job
                        job_skill.skill = skill_obj
                        job_skill.save()
                    except Skill.DoesNotExist as sdn:
                        key_skill_not_found_for_job_file.write("{skill},{exception}\n".format(skill=key_skill_name, exception=sdn))
                        pass

            # Computer Skills data
            if computer_skills_id_string:
                computer_skills_id_string_list = computer_skills_id_string.split(',')

                for computer_skill_id in computer_skills_id_string_list:
                    computer_skill_name = computer_skills_dict.get(computer_skill_id.lstrip().rstrip())
                    try:
                        skill_obj = Skill.objects.get(name_en__iexact=computer_skill_name,
                                                      skill_type='computer_skill')
                        job_skill = JobSkill()
                        job_skill.job = job
                        job_skill.skill = skill_obj
                        job_skill.save()
                    except Skill.DoesNotExist as sdn:
                        computer_skill_not_found_for_job_file.write("{email},{skill},{exception}\n".format(email=email, skill=computer_skill_name, exception=sdn))
                        pass

            # Language Skills data
            if language_skills_id_string:
                language_skills_id_string_list = language_skills_id_string.split(',')

                for language_skill_id in language_skills_id_string_list:
                    language_skill_name_value = language_skills_dict.get(
                        language_skill_id.lstrip().rstrip())
                    language_skill_name_value_list = language_skill_name_value.split('.')
                    language_skill_name = language_skill_name_value_list[1]
                    try:
                        skill_obj = Skill.objects.get(name_en__iexact=language_skill_name, skill_type='language')
                        job_skill = JobSkill()
                        job_skill.job = job
                        job_skill.skill = skill_obj
                        job_skill.save()

                    except Skill.DoesNotExist as sdn:
                        language_skill_not_found_for_job_file.write("{title},{skill},{exception}\n".format(title=title, skill=language_skill_name, exception=sdn))
                        pass

    except Exception as e:
        job_save_failure_file.write("{job},{exception}\n".format(job=title, exception=e))
        logger.info("Could not create job  with - {job},{exception}\n".format(job=occupation_name, exception=e))
        pass
    finally:
        job_save_success_file.close()
        job_save_failure_file.close()
        key_skill_not_found_for_job_file.close()
        computer_skill_not_found_for_job_file.close()
        language_skill_not_found_for_job_file.close()