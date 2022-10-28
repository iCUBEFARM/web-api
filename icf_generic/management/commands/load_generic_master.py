import csv
import os, sys

from django.core.management import BaseCommand
from django.core.management.base import AppCommand
from modeltranslation.utils import auto_populate

from icf_generic.models import Currency
from icf_jobs.models import EducationLevel, Occupation, Skill, SalaryFrequency, JobType


class LoadPath:
    DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    CURRENCY_CSV = os.path.join(DATA_PATH, 'currencies.csv')


class Command(BaseCommand):

    help = "Load master data for the applications"

    # def add_arguments(self, parser):
    #     parser.add_argument('csv_file', nargs='+', type=str)
    def populate_currencies(self, *args, **options):
        curr_csv = open(LoadPath.CURRENCY_CSV, encoding="utf-8")
        curr_reader = csv.reader(curr_csv)
        for row in curr_reader:
            print('Loading Currencies {}'.format(str(row)).encode("utf-8"))
            try:
                obj, created = Currency.objects.get_or_create(code=row[0], name=row[0])
            except Exception as e:
                print(str(e))
                exit(1)

    def handle(self, **options):
        self.populate_currencies()




