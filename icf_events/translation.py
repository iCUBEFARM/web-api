from modeltranslation.translator import translator, TranslationOptions

from icf_events.models import Event, EventDraft


class EventTypeTranslationOptions(TranslationOptions):
    fields = ('name', )


# class EventTranslationOptions(TranslationOptions):
#     fields = ('name', )


# translator.register(EventType, EventTypeTranslationOptions)
translator.register(Event)
translator.register(EventDraft)



