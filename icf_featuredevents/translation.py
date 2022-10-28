from modeltranslation.translator import translator, TranslationOptions

from icf_featuredevents.models import FeaturedEvent, TermsAndConditions, EventProduct, FeaturedEventGallery


class FeaturedEventTranslationOptions(TranslationOptions):
    fields = ('title', 'sub_title', 'description', 'email_content')


class TermsAndConditionsTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


# class ProductTranslationOptions(TranslationOptions):
#     fields = ('name', 'description')


class FeaturedEventGalleryTranslationOptions(TranslationOptions):
    fields = ('title',)


class FeaturedEventCategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


translator.register(FeaturedEvent, FeaturedEventTranslationOptions)
translator.register(TermsAndConditions, TermsAndConditionsTranslationOptions)
# translator.register(EventTicket, ProductTranslationOptions)
translator.register(FeaturedEventGallery, FeaturedEventGalleryTranslationOptions)
# translator.register(FeaturedEventCategory, FeaturedEventCategoryTranslationOptions)


