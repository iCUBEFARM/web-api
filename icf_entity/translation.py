from modeltranslation.translator import translator, TranslationOptions

from icf_entity.models import Sector, Industry, CompanySize


class SectorTranslationOptions(TranslationOptions):
    fields = ('sector', 'description')


class IndustryTranslationOptions(TranslationOptions):
    fields = ('industry', 'description')


class CompanySizeTranslationOptions(TranslationOptions):
    fields = ('size', 'description',)


translator.register(Sector, SectorTranslationOptions)
translator.register(Industry, IndustryTranslationOptions)
translator.register(CompanySize, CompanySizeTranslationOptions)
