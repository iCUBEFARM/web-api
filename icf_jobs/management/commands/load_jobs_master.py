import csv
import os, sys

from django.core.management import BaseCommand
from django.core.management.base import AppCommand
from modeltranslation.utils import auto_populate

from icf_jobs.models import EducationLevel, Occupation, Skill, SalaryFrequency, JobType


class LoadPath:
    DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    EDU_LEVEL_CSV = os.path.join(DATA_PATH, 'education_level.csv')
    OCCUPATION_CSV = os.path.join(DATA_PATH, 'job_occupations.csv')
    KEY_SKILLS_CSV = os.path.join(DATA_PATH, 'key_skills.csv')
    COMPUTER_SKILLS_CSV = os.path.join(DATA_PATH, 'computer_skills.csv')
    LANGUAGE_SKILLS_CSV = os.path.join(DATA_PATH, 'language_skills.csv')
    SALARY_FREQUENCIES_CSV = os.path.join(DATA_PATH, 'salary_frequencies.csv')
    JOB_TYPES_CSV = os.path.join(DATA_PATH, 'job_types.csv')


class Command(BaseCommand):

    help = "Load master data for the applications"

    # def add_arguments(self, parser):
    #     parser.add_argument('csv_file', nargs='+', type=str)

    def populate_edu_level(self, *args, **options):
        edu_csv = open(LoadPath.EDU_LEVEL_CSV, encoding="utf-8")
        edu_reader = csv.reader(edu_csv)
        for row in edu_reader:
            print('Loading Education Level {}'.format(str(row)).encode('utf-8'))
            try:
                obj, created = EducationLevel.objects.get_or_create(level=row[0], level_en=row[0], level_fr=row[1], level_es=row[2])
            except Exception as e:
                print(str(e))
                exit(1)

    def populate_occupation(self, *args, **options):
        occ_csv = open(LoadPath.OCCUPATION_CSV, encoding="utf-8")
        occ_reader = csv.reader(occ_csv)
        for row in occ_reader:
            print('Loading Occupation {}'.format(str(row)).encode('utf-8'))
            try:
                obj, created = Occupation.objects.get_or_create(name=row[0], name_en=row[0], name_fr=row[1], name_es=row[2])
            except Exception as e:
                print(str(e))
                exit(1)

    def populate_skills(self, *args, file=None, skill_type=None, **options):
        skill_csv = open(file, encoding="utf-8")
        skill_reader = csv.reader(skill_csv)
        for row in skill_reader:
            print('Loading Skills {} : {}'.format(skill_type, str(row)).encode('utf-8'))
            try:
                obj, created = Skill.objects.get_or_create(name=row[0], name_en=row[0], name_fr=row[1],
                                                                name_es=row[2], skill_type=skill_type)
            except Exception as e:
                print(str(e))
                exit(1)

    def populate_key_skills(self, *args, **options):
        self.populate_skills(file=LoadPath.KEY_SKILLS_CSV, skill_type=Skill.KEY_SKILLS)

    def populate_language_skills(self, *args, **options):
        self.populate_skills(file=LoadPath.LANGUAGE_SKILLS_CSV, skill_type=Skill.LANGUAGE)

    def populate_computer_skills(self, *args, **options):
        computer_skill_csv = open(LoadPath.COMPUTER_SKILLS_CSV, encoding="utf-8")
        computer_skill_reader = csv.reader(computer_skill_csv)
        for row in computer_skill_reader:
            print('Loading Skills {} : {}'.format(Skill.COMPUTER_SKILLS, str(row)).encode('utf-8'))
            try:
                with auto_populate(True):
                    obj, created = Skill.objects.get_or_create(name=row[0], skill_type=Skill.COMPUTER_SKILLS)
            except Exception as e:
                print(str(e))
                exit(1)

    def populate_salary_frequencies(self, *args, **options):
        sal_freq_csv = open(LoadPath.SALARY_FREQUENCIES_CSV, encoding="utf-8")
        sal_freq_reader = csv.reader(sal_freq_csv)
        for row in sal_freq_reader:
            print('Loading Salary Frequencies {}'.format(str(row)).encode('utf-8'))
            try:
                obj, created = SalaryFrequency.objects.get_or_create(frequency=row[0], frequency_en=row[0],
                                                                     frequency_fr=row[1], frequency_es=row[2])
            except Exception as e:
                print(str(e))
                exit(1)

    def populate_job_types(self, *args, **options):
        job_type_csv = open(LoadPath.JOB_TYPES_CSV, encoding="utf-8")
        job_type_reader = csv.reader(job_type_csv)
        for row in job_type_reader:
            print('Loading Job Types {}'.format(str(row)).encode('utf-8'))
            try:
                obj, created = JobType.objects.get_or_create(job_type=row[0], job_type_en=row[0],
                                                                     job_type_fr=row[1], job_type_es=row[2])
            except Exception as e:
                print(str(e))
                exit(1)

    def handle(self, **options):
        self.populate_edu_level()
        self.populate_occupation()
        self.populate_key_skills()
        self.populate_language_skills()
        self.populate_computer_skills()
        self.populate_salary_frequencies()
        self.populate_job_types()




