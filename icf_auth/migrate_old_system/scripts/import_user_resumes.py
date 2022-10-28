import csv
import os, sys
import random
import shutil

# import PIL
from allauth.account import signals
from pip._vendor.distlib.compat import raw_input


FILE_DIR = os.path.dirname(os.path.abspath(__file__))
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
from icf_jobs.models import JobProfileFileUpload
import datetime
from django.db import transaction, IntegrityError
from icf_auth.migrate_old_system.scripts.Helper import Helper
# import PIL.Image
from PIL import Image
from django.core.files import File
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()


# USERS_RESUME_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "users-with-resumes-latest-csv.csv")
# USERS_RESUME_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "users-without-countrycodes-resumes-latest-6.csv")
# USERS_RESUME_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "user-without-country codes-jobseekers-ex.csv")  # latest user file with resume info
# USERS_RESUME_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "lastest-users-nov26.csv")   # Nov 26th 43 users
USERS_RESUME_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "latest-users-dec7th-production-csv.csv")   # Dec 7th 83 users

WRITE_USER_RESUME_SAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "users-resume-save-success.txt")
WRITE_USER_RESUME_UNSAVED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "users-resume-save-failed.txt")
# USER_IMAGE_PATH= os.path.join(FILE_DIR, "userResumes")
# IMAGE_MAX_HEIGHT = IMAGE_MAX_WIDTH = 200
# USERS_RESUME_FILE = os.path.join(FILE_DIR, "users-resume-temp-data.csv")


with open(USERS_RESUME_FILE, "r", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        user_resume_save_success_file = open(WRITE_USER_RESUME_SAVED_FILE, "a+")
        user_resume_save_failure_file = open(WRITE_USER_RESUME_UNSAVED_FILE, "a+")

        user_resume_file_path = raw_input("enter path of Resume file:\n")
        user_resume_file_path = user_resume_file_path.lstrip().rstrip()
        if not user_resume_file_path.lstrip().rstrip():
            raise ValueError("Please enter user resume path")
        if not (os.path.isdir(user_resume_file_path.lstrip().rstrip())):
            raise ValueError("Please enter proper directory path ")

        for row in dr:

            document_type = row['document_type'].lstrip().rstrip()
            document_url = row['document_url'].lstrip().rstrip()
            # document_url = r'document_url'
            # document_url = document_url.replace('\\','')
            email = row['email']
            status = row['status']

            if document_url and document_type == '1' and status == '2':
                try:
                    with transaction.atomic():
                        user = User.objects.get(email=email)
                        jpfu = JobProfileFileUpload()
                        jpfu.user = user

                        resume_full_path = os.path.join(user_resume_file_path, document_url)
                        if os.path.exists(resume_full_path):
                            resume_fd = open(resume_full_path, 'rb')
                            resume_file = File(resume_fd)
                            jpfu.resume_src.save(document_url, resume_file)
                            jpfu.save()
                            logger.info("Created User Resume - {}".format(email))
                            user_resume_save_success_file.write("{email}\n".format(email=email))

                except User.DoesNotExist as udn:
                    user_resume_save_failure_file.write("{email} {exception}\n".format(email=email, exception=udn))  # Todo : Write to failure file and continue or pass
                    pass
                except IOError as ioe:
                    user_resume_save_failure_file.write("{email} {exception}\n".format(email=email, exception=ioe))  # Todo : Write to failure file and continue or pass
                    pass
                except OSError as oe:
                    user_resume_save_failure_file.write("{email} {exception}\n".format(email=email, exception=oe))
                    pass
                except IntegrityError as ie:
                    user_resume_save_failure_file.write("{email} {exception}\n".format(email=email, exception=ie))
                    pass
                except Exception as e:
                    user_resume_save_failure_file.write("{email} {exception}\n".format(email=email, exception=e))
                    logger.info("Could not create JobProfileFileUpload with - {email} {exception}\n".format(email=email,exception=e))
                    pass

    finally:
        user_resume_save_success_file.close()
        user_resume_save_failure_file.close()