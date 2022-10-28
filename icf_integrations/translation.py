from modeltranslation.translator import translator, TranslationOptions

from icf_integrations.models import SentGroupSms


class SentGroupSmsTranslationOptions(TranslationOptions):
    fields = ('messages',)

translator.register(SentGroupSms,SentGroupSmsTranslationOptions)
