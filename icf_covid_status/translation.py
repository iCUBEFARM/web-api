from modeltranslation.translator import TranslationOptions, translator

from icf_covid_status.models import EGSector, CurrentWorkStatus, CurrentCompensationStatus


class EGSectorTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


class CurrentWorkStatusTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)


class CurrentCompensationStatusTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)


translator.register(EGSector, EGSectorTranslationOptions)
translator.register(CurrentWorkStatus, CurrentWorkStatusTranslationOptions)
translator.register(CurrentCompensationStatus, CurrentCompensationStatusTranslationOptions)
