from modeltranslation.translator import translator, TranslationOptions
from .models import ICFNotification

class NotificationTranslationOptions(TranslationOptions):
    fields = ('message', 'details')

translator.register(ICFNotification, NotificationTranslationOptions)