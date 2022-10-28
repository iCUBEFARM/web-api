import csv
import os, sys

from django.core.management import BaseCommand
from django.core.management.base import AppCommand
from modeltranslation.utils import auto_populate

from icf_entity.api.serializers import SectorSerializer
from icf_entity.models import Sector, Industry
from icf_generic.models import Currency
from icf_jobs.models import EducationLevel, Occupation, Skill, SalaryFrequency, JobType


class LoadPath:
    DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    SECTOR_CSV = os.path.join(DATA_PATH, 'sectors.csv')
    INDUSTRY_CSV = os.path.join(DATA_PATH, 'industries.csv')


class Command(BaseCommand):

    help = "Load master data for the applications"

    # def add_arguments(self, parser):
    #     parser.add_argument('csv_file', nargs='+', type=str)

    def populate_sectors(self, *args, **options):
        sec_csv = open(LoadPath.SECTOR_CSV, encoding="utf-8")
        sec_reader = csv.reader(sec_csv)
        for row in sec_reader:
            print("Loading Sectors {}".format(str(row)).encode('utf-8'))
            try:
                obj, created = Sector.objects.get_or_create(sector=row[0], sector_en=row[0], sector_fr=row[1],
                                                            sector_es=row[2], description=row[3], description_en=row[3],
                                                            description_fr=row[4], description_es=row[5])
            except Exception as e:
                print(str(e))
                exit(1)

    def populate_industries(self, *args, **options):
        ind_csv = open(LoadPath.INDUSTRY_CSV, encoding="utf-8")
        ind_reader = csv.reader(ind_csv)
        for row in ind_reader:
            print('Loading Industries {}'.format(str(row)).encode('utf-8'))
            try:
                obj, created = Industry.objects.get_or_create(industry=row[0], industry_en=row[0], industry_fr=row[1],
                                                            industry_es=row[2], description=row[5], description_en=row[5],
                                                            description_fr=row[6], description_es=row[7])
            except Exception as e:
                print(str(e))
                exit(1)

    def handle(self, **options):
        self.populate_sectors()
        self.populate_industries()




