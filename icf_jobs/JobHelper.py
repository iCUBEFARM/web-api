from datetime import datetime

from django.core.files.base import ContentFile
import os.path
from PIL import Image
from io import BytesIO
from dateutil.parser import parse
import logging

from icf_generic.fields import ICFApproxDate

logger = logging.getLogger(__name__)


class CreateUserResumeThumbnail:

    def make_thumbnail(self, dst_image_field, src_image_field, size, name_suffix, sep='_'):
        """
        make thumbnail image and field from source image field

        @example
            thumbnail(self.thumbnail, self.image, (200, 200), 'thumb')
        """
        # create thumbnail image
        image = Image.open(src_image_field)
        image.thumbnail(size, Image.ANTIALIAS)

        # build file name for dst
        dst_path, dst_ext = os.path.splitext(src_image_field.name)
        dst_ext = dst_ext.lower()
        dst_fname = dst_path + sep + name_suffix + dst_ext

        # check extension
        if dst_ext in ['.jpg', '.jpeg']:
            filetype = 'JPEG'
        elif dst_ext == '.gif':
            filetype = 'GIF'
        elif dst_ext == '.png':
            filetype = 'PNG'
        else:
            raise RuntimeError('unrecognized file type of "%s"' % dst_ext)

        # Save thumbnail to in-memory file as StringIO
        dst_bytes = BytesIO()
        image.save(dst_bytes, filetype)
        dst_bytes.seek(0)

        # set save=False, otherwise it will run in an infinite loop
        dst_image_field.save(dst_fname, ContentFile(dst_bytes.read()), save=False)
        dst_bytes.close()


def get_intersection_of_lists(list_1, list_2):
    # Converting the lists into sets
    if not list_1 and not list_2:
        return []
    if not list_1:
        s_r = set(list_2)
        s_l = list(s_r)
        return s_l
    if not list_2:
        s_r = set(list_1)
        s_l = list(s_r)
        return s_l

    s1 = set(list_1)
    s2 = set(list_2)

    # Calculates intersection of
    # sets on s1 and s2
    # Calculates intersection of sets
    result_set = s1.intersection(s2)

    # Converts resulting set to list
    final_list = list(result_set)
    return final_list


def get_user_work_experience_in_seconds(work_experience_from, work_experience_till):
    try:
        if work_experience_from and work_experience_till:

            # following code converts datetime to string
            work_experience_from_string = get_work_experience_in_string(work_experience_from)
            work_experience_till_string = get_work_experience_in_string(work_experience_till)

            if work_experience_from_string:
                # following code converts string to datetime of given format
                work_experience_from = datetime.strptime(work_experience_from_string, '%Y-%m-%d')
            if work_experience_till_string:
                work_experience_till = datetime.strptime(work_experience_till_string, '%Y-%m-%d')
            timedelta = work_experience_till - work_experience_from
            return timedelta.days * 24 * 3600 + timedelta.seconds
        else:
            logger.exception("Could not calculate work experience of the user.")
            return 0
    except ValueError as ve:
        logger.exception("Could not calculate work experience of the user.")
        # print(str(ve))
        return 0
    except Exception as e:
        logger.exception("Could not calculate work experience of the user. reason: {reason}".format(reason=str(e)))
        # print(str(e))
        return 0


def get_work_experience_in_string(icf_work_experience):
    if (isinstance(icf_work_experience, type(ICFApproxDate)) and icf_work_experience.present == True) or \
            (int(icf_work_experience.day) == 0 and int(icf_work_experience.month) == 0 and int(
                icf_work_experience.year) == 9999):
        icf_work_experience_str = datetime.today().strftime('%Y-%m-%d')
        icf_work_experience = datetime.strptime(icf_work_experience_str, '%Y-%m-%d')

    year = icf_work_experience.year
    month = icf_work_experience.month
    date = icf_work_experience.day

    if int(date) == 0:
        date = 1
    if int(month) == 0 or int(year) == 0:
        raise ValueError

    string_format = str(year) + "-" + str(month) + "-" + str(date)
    return string_format


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


