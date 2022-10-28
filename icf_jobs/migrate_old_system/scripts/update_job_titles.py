import csv
import os, sys



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

from icf_jobs.models import Job
import logging

logger = logging.getLogger(__name__)


# cur = con.cursor()

JOB_TITLE_FILE = os.path.join(os.path.dirname(FILE_DIR), "data", "job_titles_in_all_languages.csv")
WRITE_JOB_UPDATE_SUCCESS_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_title_update_success_file.txt")
WRITE_JOB_UPDATE_FAILURE_FILE = os.path.join(os.path.dirname(FILE_DIR), "logs", "job_title_update_failure_file.txt")



with open(JOB_TITLE_FILE, "rt", encoding="UTF-8") as fin: # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    try:
        job_update_success_file = open(WRITE_JOB_UPDATE_SUCCESS_FILE, "a+")
        job_update_failure_file = open(WRITE_JOB_UPDATE_FAILURE_FILE, "a+")

        for row in dr:
            title_en = row['description_en'].lstrip().rstrip()
            title_fr = row['description_fr'].lstrip().rstrip()
            title_es = row['description_es'].lstrip().rstrip()
            try:

                jobs = Job.objects.filter(title_en=title_en)

                for job in jobs:
                    job.title_en = title_en
                    job.title_fr = title_fr
                    job.title_es = title_es
                    job.save()
                    logger.info(" Successfully updated job title   -  {title_en}\n".format(title_en=title_en))
                    job_update_success_file.write("{title_en}\n".format(title_en=title_en))

            except Exception as e:
                logger.info(" Could not update job title   -  {title_en},{exception}\n".format(title_en=title_en, exception=e))
                job_update_failure_file.write("{title_en},{exception}\n".format(title_en=title_en, exception=e))
                pass
    finally:
        job_update_success_file.close()
        job_update_failure_file.close()
