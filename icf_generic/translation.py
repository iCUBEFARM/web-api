from django.contrib.contenttypes.models import ContentType
from modeltranslation.translator import translator, TranslationOptions

from icf_generic.models import FAQ, FeaturedEvent, FeaturedVideo, City, Country, State, Category, Language, Currency, \
    Type, FAQCategory


class FAQTranslationOptions(TranslationOptions):
    fields = ('question', 'answer', 'video_url')


class FeaturedEventTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


class FeaturedVideoTranslationOptions(TranslationOptions):
    fields = ('title', 'video_url', 'description')


class CountryTranslationOptions(TranslationOptions):
    fields = ('country',)


class StateTranslationOptions(TranslationOptions):
    fields = ('state',)


class CityTranslationOptions(TranslationOptions):
    fields = ('city',)


class CategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


class LanguageTranslationOptions(TranslationOptions):
    fields = ('name',)


class CurrencyTranslationOptions(TranslationOptions):
    fields = ('name',)


class TypeTransaltionOptions(TranslationOptions):
    fields = ('name',)


class FAQCategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)


translator.register(FAQCategory, FAQCategoryTranslationOptions)
translator.register(FAQ, FAQTranslationOptions)
translator.register(FeaturedEvent, FeaturedEventTranslationOptions)
translator.register(FeaturedVideo, FeaturedVideoTranslationOptions)
translator.register(Country, CountryTranslationOptions)
translator.register(State, StateTranslationOptions)
translator.register(City, CityTranslationOptions)
translator.register(Category, CategoryTranslationOptions)
translator.register(Language, LanguageTranslationOptions)
translator.register(Currency, CurrencyTranslationOptions)
translator.register(Type, TypeTransaltionOptions)

