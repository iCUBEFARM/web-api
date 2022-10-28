import csv
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

from allauth.utils import generate_unique_username
from icf_auth.models import User, UserProfile, UserProfileImage
from icf_jobs.models import JobProfileFileUpload
import datetime
from django.db import transaction
from icf_auth.migrate_old_system.Helper import Helper
import PIL.Image
from django.core.files import File
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

# USERS_FILE = os.path.join(FILE_DIR, "temp_data.csv")
ENTITY_FILE = os.path.join(FILE_DIR, "companies-temp-data.csv")
WRITE_ENTITY_SAVED_FILE = os.path.join(FILE_DIR, "companies-save-success.csv")
WRITE_ENTITY_UNSAVED_FILE = os.path.join(FILE_DIR, "companies-save-failed.csv")
ENTITY_IMAGE_PATH= os.path.join(FILE_DIR, "companyLogos")
IMAGE_MAX_HEIGHT = IMAGE_MAX_WIDTH = 200
# USERS_RESUME_FILE = os.path.join(FILE_DIR, "users-resume-temp-data.csv")


def create_thumbnail(orig_image_path, max_height=200, max_width=200):

    # print("Create a new thumbnail for {0}".format(orig_image_path))
    logger.info("Create a new thumbnail for {0}".format(orig_image_path))

    orig_filename = os.path.basename(orig_image_path)

    try:
        orig_image = PIL.Image.open(orig_image_path)
    except ValueError:
        # print("Could not open the file at {0}".format(orig_image_path))
        logger.info("Could not open the file at {0}".format(orig_image_path))
        raise
    except Exception as e:
        raise

    orig_file_basename, ext = os.path.splitext(orig_filename)

    size = (max_height, max_width)

    orig_image.thumbnail(size, PIL.Image.ANTIALIAS)

    tmp_dir = "%s/tmp" % FILE_DIR
    if not os.path.exists(tmp_dir):
        try:
            os.makedirs(tmp_dir)
        except OSError as ose:
            # print("Cannot create directory {0}, error {1}".format(tmp_dir, ose.strerror))
            logger.info("Cannot create directory {0}, error {1}".format(tmp_dir, ose.strerror))
            raise


    #
    # If the filename already exists in the tmp directory, create the file in another temp directory
    #
    tmp_file_path = os.path.join(tmp_dir, orig_filename)
    if os.path.exists(tmp_file_path):
        temp_path = os.path.join(tmp_dir, "%s" % random.random)
        try:
            os.makedirs(temp_path)
            tmp_file_path = os.path.join(temp_path, orig_filename)
        except OSError as ose:
            # print("Cannot create directory, error {0}".format(ose.strerror))
            logger.info("Cannot create directory, error {0}".format(ose.strerror))
            raise

    try:
        orig_image = orig_image.convert('RGB')
        orig_image.save(tmp_file_path)
    except KeyError:
        logger.info("Ambiguous format, not a valid image filename")
        raise
    except IOError:
        logger.info("IO Error, Could not write to file")
        raise

    thumb_data = open(tmp_file_path, "rb")

    thumb_file = File(thumb_data)

    return thumb_file


with open(ENTITY_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        entity_save_success_file = open(WRITE_ENTITY_SAVED_FILE, "a+")
        entity_save_failure_file = open(WRITE_ENTITY_UNSAVED_FILE, "a+")

        entity_image_logo_path = raw_input("enter path of image file:\n")
        entity_image_logo_path = entity_image_logo_path.lstrip().rstrip()
        if not entity_image_logo_path.lstrip().rstrip():
            raise ValueError("Please enter user imagefile path")
        if not (os.path.isdir(entity_image_logo_path.lstrip().rstrip())):
            raise ValueError("Please enter proper directory path ")
        # user_resume_file_path = raw_input("enter path of resume file:\n")
        # if not user_resume_file_path:
        #     raise ValueError("Please enter user resume file path")

        for row in dr:
            if row['company_state'] == '1':
                company_id = row['company_id']
                email = row['email_id']
                name = row['name']
                registration_date = row['registration_date']
                company_state = row['company_state']
                logo_url=row['logo_url']
                telephone_code = row['telephone_code']
                telephone_no = row['telephone_no']
                web_adr = row['web_adr']
                alternate_tele_no = row['alternate_tele_no']

                phone = "+{telephone_code}{telephone_no}".format(code=telephone_code, number=telephone_no)
                alternate_phone = "+{telephone_code}{alternate_tele_no}".format(code=telephone_code, number=alternate_tele_no)


                date_joined = last_login = None
                language_code = 'en'
                if registration_date:
                    date_joined = datetime.datetime.strptime(registration_date, '%m/%d/%y %H:%M')

                if last_login_date:
                    last_login = datetime.datetime.strptime(last_login_date, '%m/%d/%y %H:%M')

                if preferred_language:
                    language_code = row['prefered_lang']

                try:
                    with transaction.atomic():

                        username = generate_unique_username([email, first_name, last_name])

                        user = User.objects.create(email=email, password=password, first_name=first_name,
                                                  last_name=last_name, username=username, date_joined=date_joined, is_active=True,
                                                  mobile=mobile, last_login=last_login)

                        # logger.info("Created user - {}".format(user.email))
                        # user_save_success_file.write("{email},{first_name}\n".format(email=user.email, first_name=user.first_name))
                        language = Helper.get_language_id(preferred_language)
                        # try:
                        user_profile = UserProfile.objects.create(user=user, language=language)

                        if profile_image_url:
                            upi = UserProfileImage()
                            upi.user_profile = user_profile
                            #img_data = open(os.path.join(USER_IMAGE_PATH, profile_image_url), 'rb')
                            # print("enter path of file")
                            try:

                            # img_data = create_thumbnail(os.path.join(USER_IMAGE_PATH, profile_image_url), IMAGE_MAX_HEIGHT, IMAGE_MAX_WIDTH)
                                image_full_path = os.path.join(str(entity_image_logo_path), profile_image_url)
                                if os.path.exists(image_full_path):
                                    img_data = create_thumbnail(image_full_path,IMAGE_MAX_HEIGHT, IMAGE_MAX_WIDTH)
                                    img_file = File(img_data)
                                    upi.image.save(profile_image_url, img_file)
                                    upi.save()
                            # except FileNotFoundError as fne:
                            #     pass
                            except IOError as e:
                                logger.info("No Such file or directory  - {}".format(e))
                                raise

                        # except Exception as ue:
                        #     logger.info("Could not create UserProfile - {}".format(ue))
                        logger.info("Created user - {}".format(user.email))
                        entity_save_success_file.write("{email}\n".format(email=user.email))
                except Exception as e:
                    entity_save_failure_file.write("{email}\n".format(email=email))
                    logger.info("Could not create user with - {email},{exception}".format(email = email,exception = e))
    finally:
        entity_save_success_file.close()
        entity_save_failure_file.close()