from modeltranslation.translator import translator, TranslationOptions

from icf_career_fair.models import CareerFair, CareerFairDraft, SessionOptional, SupportOptional, SpeakerOptional, \
    Session, Support, Speaker
from icf_item.models import Item
from icf_item.translation import ItemTranslationOptions
# from icf_jobs.models import EducationLevel, Occupation, Skill, SalaryFrequency, JobType, Job, Relationship, JobDraft
#
#
# class EducationLevelTranslationOptions(TranslationOptions):
#     fields = ('level', )
#
#
# class OccupationTranslationOptions(TranslationOptions):
#     fields = ('name', )
#
#
# class SkillTranslationOptions(TranslationOptions):
#     fields = ('name', )
#
#


class SessionTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


class SupportTranslationOptions(TranslationOptions):
    fields = ('brand_name', 'support_type')


class SpeakerTranslationOptions(TranslationOptions):
    fields = ('name', 'entity_name', 'position')


class SessionOptionalTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


class SupportOptionalTranslationOptions(TranslationOptions):
    fields = ('brand_name', 'support_type')


class SpeakerOptionalTranslationOptions(TranslationOptions):
    fields = ('name', 'entity_name', 'position')



translator.register(CareerFair)
translator.register(Session, SessionTranslationOptions)
translator.register(Support, SupportTranslationOptions)
translator.register(Speaker, SpeakerTranslationOptions)
# translator.register(EducationLevel, EducationLevelTranslationOptions)
# translator.register(Occupation, OccupationTranslationOptions)
# translator.register(Skill, SkillTranslationOptions)
# translator.register(SalaryFrequency, SalaryFrequencyTranslationOptions)
# translator.register(JobType, JobTypeTranslationOptions)
# translator.register(Relationship, RelationshipTranslationOptions)
translator.register(CareerFairDraft)
translator.register(SessionOptional, SessionOptionalTranslationOptions)
translator.register(SupportOptional, SupportOptionalTranslationOptions)
translator.register(SpeakerOptional, SpeakerOptionalTranslationOptions)
