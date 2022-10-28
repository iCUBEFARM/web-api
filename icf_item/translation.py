from modeltranslation.translator import translator, TranslationOptions

from icf_item.models import Item, ItemDraft
from icf_jobs.models import EducationLevel, Occupation, Skill, SalaryFrequency, JobType


class ItemTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


class ItemDraftTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


translator.register(Item, ItemTranslationOptions)
translator.register(ItemDraft, ItemDraftTranslationOptions)
