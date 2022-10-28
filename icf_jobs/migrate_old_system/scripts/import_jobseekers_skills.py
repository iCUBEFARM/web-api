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
from icf_jobs.models import UserJobProfile, UserSkill, Skill
from icf_jobs.migrate_old_system.data.Key_Skills_Dictionary import key_skills_dict, computer_skills_dict, \
    language_skills_dict
from django.db import transaction
import logging


logger = logging.getLogger(__name__)


# cur = con.cursor()

# JOB_SEEKER_SKILLS_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "jobseekers-skills-1.csv")
# JOB_SEEKER_SKILLS_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-job-seekers-skills-from-production.csv")
# JOB_SEEKER_SKILLS_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-jobseekers-skills-nov26.csv")
JOB_SEEKER_SKILLS_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "latest-jobseekers-skill-dec7th-production-csv.csv")   ## 7th Dec  Job Seeker's skills



# JOB_SEEKER_SKILLS_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "job_seeker_temp_data.csv")
WRITE_JOB_SEEKER_SKILLS_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seeker_skills_save_success.txt")
WRITE_JOB_SEEKER_SKILLS_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seeker_skills_save_failed.txt")
WRITE_JOB_SEEKER_FOR_SKILLS_NOT_FOUND_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "users_not_found_for_skills.txt")
WRITE_JOB_SEEKER_USER_JOB_PROFILE_NOT_FOUND_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seeker_profile_not_found.txt")
WRITE_JOB_SEEKER_KEY_SKILLS_SAVE_SUCCESS_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seekers_key_skills_save_success.txt")
WRITE_JOB_SEEKER_COMPUTER_SKILLS_SAVE_SUCCESS_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seekers_computer_skills_save_success.txt")
WRITE_JOB_SEEKER_LANGUAGE_SKILLS_SAVE_SUCCESS_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_seekers_language_skills_save_success.txt")

SKILL_NOT_FOUND_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "skill_not_found.txt")


with open(JOB_SEEKER_SKILLS_FILE, "r", encoding="utf8") as fin:
    # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin)  # comma is default delimiter
    try:
        job_seeker_skills_save_success_file = open(WRITE_JOB_SEEKER_SKILLS_SAVED_FILE, "a+")
        job_seeker_skills_save_failure_file = open(WRITE_JOB_SEEKER_SKILLS_UNSAVED_FILE, "a+")
        user_not_found_for_skills_file = open(WRITE_JOB_SEEKER_FOR_SKILLS_NOT_FOUND_FILE, "a+")
        skill_not_found_file = open(SKILL_NOT_FOUND_FILE, "a+")
        job_seekers_key_skills_save_success_file = open(WRITE_JOB_SEEKER_KEY_SKILLS_SAVE_SUCCESS_FILE, "a+")
        job_seekers_computer_skills_save_success_file = open(WRITE_JOB_SEEKER_COMPUTER_SKILLS_SAVE_SUCCESS_FILE, "a+")
        job_seekers_language_skills_save_success_file = open(WRITE_JOB_SEEKER_LANGUAGE_SKILLS_SAVE_SUCCESS_FILE, "a+")
        job_seeker_user_job_profile_not_found_file = open(WRITE_JOB_SEEKER_USER_JOB_PROFILE_NOT_FOUND_FILE, "a+")

        for row in dr:
            email = row['email'].lstrip().rstrip()
            key_skills_id_string = row['key_skills'].lstrip().rstrip()
            computer_skills_id_string = row['computer_skills'].lstrip().rstrip()
            language_skills_id_string = row['language_spoken'].lstrip().rstrip()

            try:
                with transaction.atomic():
                    user = User.objects.get(email=email)
                    user_job_profile = UserJobProfile.objects.get(user=user)

                    # Key Skills data
                    if key_skills_id_string:
                        key_skills_id_string_list = key_skills_id_string.split(',')

                        for key_skill_id in key_skills_id_string_list:
                            key_skill_name = key_skills_dict.get(key_skill_id.lstrip().rstrip())
                            try:
                                skill_obj = Skill.objects.get(name_en__iexact=key_skill_name, skill_type='key_skill')
                                user_skill = UserSkill()
                                user_skill.job_profile = user_job_profile
                                user_skill.skill = skill_obj
                                user_skill.save()

                            except Skill.DoesNotExist as sdn:
                                skill_not_found_file.write("{email},{skill},{exception}\n".format(email=email, skill=key_skill_name, exception=sdn))
                                raise
                        job_seekers_key_skills_save_success_file.write("{email}\n".format(email=email))
                        logger.info("User Skill Successful with email - {email}\n".format(email=email))

                    # Computer Skills data
                    if computer_skills_id_string:
                        computer_skills_id_string_list = computer_skills_id_string.split(',')

                        for computer_skill_id in computer_skills_id_string_list:
                            computer_skill_name = computer_skills_dict.get(computer_skill_id.lstrip().rstrip())
                            try:
                                skill_obj = Skill.objects.get(name_en__iexact=computer_skill_name, skill_type='computer_skill')
                                user_skill = UserSkill()
                                user_skill.job_profile = user_job_profile
                                user_skill.skill = skill_obj
                                user_skill.save()
                            except Skill.DoesNotExist as sdn:
                                skill_not_found_file.write("{email},{skill},{exception}\n".format(email=email, skill=computer_skill_name, exception=sdn))
                                raise
                        job_seekers_computer_skills_save_success_file.write("{email}\n".format(email=email))
                        logger.info("User Skill Successful with email - {email}\n".format(email=email))

                    # Language Skills data
                    if language_skills_id_string:
                        language_skills_id_string_list = language_skills_id_string.split(',')

                        for language_skill_id in language_skills_id_string_list:
                            language_skill_name_value = language_skills_dict.get(language_skill_id.lstrip().rstrip())
                            language_skill_name_value_list = language_skill_name_value.split('.')
                            language_skill_name = language_skill_name_value_list[1]
                            try:
                                skill_obj = Skill.objects.get(name_en__iexact=language_skill_name, skill_type='language')
                                user_skill = UserSkill()
                                user_skill.job_profile = user_job_profile
                                user_skill.skill = skill_obj
                                user_skill.save()

                            except Skill.DoesNotExist as sdn:
                                skill_not_found_file.write("{email},{skill},{exception}\n".format(email=email, skill=language_skill_name, exception=sdn))
                                raise
                        job_seekers_language_skills_save_success_file.write("{email}\n".format(email=email))
                        logger.info("User Skill Successful with email - {email}\n".format(email=email))

            except UserJobProfile.DoesNotExist as ue:
                job_seeker_user_job_profile_not_found_file.write("{email}\n".format(email=email))
                pass

            except User.DoesNotExist as udn:
                user_not_found_for_skills_file.write("{email}\n".format(email=email))
                pass

    except Exception as e:
        job_seeker_skills_save_failure_file.write("{email} {exception}\n".format(email=email, exception=e))
        logger.info("Could not create UserSkills with - {email} {exception}\n".format(email=email, exception=e))

    finally:
        job_seeker_skills_save_success_file.close()
        job_seeker_skills_save_failure_file.close()
        user_not_found_for_skills_file.close()
        skill_not_found_file.close()
        job_seeker_user_job_profile_not_found_file.close()