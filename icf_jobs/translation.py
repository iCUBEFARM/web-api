from modeltranslation.translator import translator, TranslationOptions

from icf_item.models import Item
from icf_item.translation import ItemTranslationOptions
from icf_jobs.models import EducationLevel, Occupation, Skill, SalaryFrequency, JobType, Job, Relationship, JobDraft


class EducationLevelTranslationOptions(TranslationOptions):
    fields = ('level', )


class OccupationTranslationOptions(TranslationOptions):
    fields = ('name', )


class SkillTranslationOptions(TranslationOptions):
    fields = ('name', )


class SalaryFrequencyTranslationOptions(TranslationOptions):
    fields = ('frequency', )


class JobTypeTranslationOptions(TranslationOptions):
    fields = ('job_type', )


class RelationshipTranslationOptions(TranslationOptions):
    fields = ('relation', 'description',)

translator.register(Job)
translator.register(EducationLevel, EducationLevelTranslationOptions)
translator.register(Occupation, OccupationTranslationOptions)
translator.register(Skill, SkillTranslationOptions)
translator.register(SalaryFrequency, SalaryFrequencyTranslationOptions)
translator.register(JobType, JobTypeTranslationOptions)
translator.register(Relationship, RelationshipTranslationOptions)
translator.register(JobDraft)
