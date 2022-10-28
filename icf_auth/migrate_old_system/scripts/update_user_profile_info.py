import csv
import os, sys

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

from allauth.account.models import EmailAddress
from allauth.utils import generate_unique_username
from icf_auth.models import User, UserProfile, UserProfileImage
import datetime
from django.db import transaction, IntegrityError
from icf_auth.migrate_old_system.scripts.Helper import Helper, gender_choices_dict
import logging
from icf_generic.models import Language, Country, Address, City

logger = logging.getLogger(__name__)

USERS_PROFILE_INFO_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "user-profile-data_1.csv")  # latest user file with resume info

WRITE_USER_PROFILE_INFO_UPDATE_SUCCESS_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "users-profile-info-update-success.txt")
WRITE_USER_PROFILE_INFO_UPDATE_FAILED_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "users-profile-info-update-failed.txt")
USER_NOT_FOUND_FOR_UPDATE_PROFILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "user_not_found_for_update_profile.txt")
COUNTRY_FAILURE_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "country_not_user_profile_info_update_failure_file.txt")
CITY_NOT_FOUND_FILE =  os.path.join(os.path.dirname(FILE_DIR), "logs", "city_not_found_file.txt")
CITY_IN_COUNTRY_NOT_FOUND_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "User_Profile_Update_Wrong_City_Data.csv")
# USER_IMAGE_PATH= os.path.join(FILE_DIR, "userImages")
IMAGE_MAX_HEIGHT = IMAGE_MAX_WIDTH = 200
# USERS_RESUME_FILE = os.path.join(FILE_DIR, "users-resume-temp-data.csv")



with open(USERS_PROFILE_INFO_FILE, "rt", encoding="utf8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        user_profile_info_update_success_file = open(WRITE_USER_PROFILE_INFO_UPDATE_SUCCESS_FILE, "a+")
        user_profile_info_update_failure_file = open(WRITE_USER_PROFILE_INFO_UPDATE_FAILED_FILE, "a+")
        user_not_found_file = open(USER_NOT_FOUND_FOR_UPDATE_PROFILE, "a+")
        country_not_user_profile_info_update_failure_file = open(COUNTRY_FAILURE_FILE, "a+")
        city_not_found_file = open(CITY_NOT_FOUND_FILE, "a+")
        city_in_country_not_found_file = open(CITY_IN_COUNTRY_NOT_FOUND_FILE, "a+")
        date_of_birth = None
        for row in dr:
            email = row['email'].lstrip().rstrip()
            date_of_birth = row['date_of_birth'].lstrip().rstrip()
            gender = row['gender'].lstrip().rstrip()
            address1 = row['address1'].lstrip().rstrip()
            address2 = row['address2'].lstrip().rstrip()
            city = row['city'].lstrip().rstrip()
            nationality_tmp = row['nationality'].lstrip().rstrip()
            nationality = nationality_tmp.split(".")[1]


            try:
                with transaction.atomic():
                    user = User.objects.get(email=email)
                    user_profile = UserProfile.objects.get(user=user)

                    if date_of_birth:
                        date_of_birth = datetime.datetime.strptime(date_of_birth, '%m/%d/%Y')
                    user_profile.dob = date_of_birth
                    user_profile.gender = gender_choices_dict.get(gender)

                    country = Country.objects.get(country__iexact=nationality)
                    user_profile.nationality = country
                    user_profile.save()

                    city = City.objects.get(city__iexact=city)
                    address = Address.objects.create(address_1=address1, address_2=address2, city=city)
                    user_profile.location = address

                    logger.info("Updated user profile - {}\n".format(user.email))
                    user_profile_info_update_success_file.write("{row}\n".format(row=row))
            except User.DoesNotExist as udn:
                # user_profile_info_update_failure_file.write("{row},{exception}\n".format(row=row, exception=udn))
                user_not_found_file.write("{row},{exception}\n".format(row=row, exception=udn))
                pass
            except City.DoesNotExist as cdn:
                # city_in_country_not_found_file.write("{email},{gender},{date_of_birth},{address1},{address2},{city},{nationality}\n".format(email=email, gender=gender, date_of_birth=date_of_birth, address1=address1, address2=address2, city=city, nationality=nationality))
                city_in_country_not_found_file.write("{email}\n".format(email=email))
                user_profile_info_update_failure_file.write("{row},{exception}\n".format(row=row, exception=cdn))
                city_not_found_file.write("{row},{exception}\n".format(row=row, exception=cdn))

                pass
            except Country.DoesNotExist as codn:
                user_profile_info_update_failure_file.write("{row},{exception}\n".format(row=row, exception=codn))
                country_not_user_profile_info_update_failure_file.write("{row},{exception}\n".format(row=row, exception=codn))
                pass
            except IntegrityError as ie:
                user_profile_info_update_failure_file.write("{row},{exception}\n".format(row=row, exception=ie))
                pass
            except Exception as e:
                user_profile_info_update_failure_file.write("{row}\n".format(row=row))
                logger.info("Could not update user profile with - {nationality},{exception}\n".format(nationality=nationality, exception=e))
                pass

    finally:
        user_profile_info_update_success_file.close()
        user_profile_info_update_failure_file.close()
        user_not_found_file.close()
        country_not_user_profile_info_update_failure_file.close()
        city_not_found_file.close()
        city_in_country_not_found_file.close()