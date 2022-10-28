from modeltranslation.translator import translator, TranslationOptions
from icf_orders.models import CreditAction, Product, ProductDraft


class CreditActionTranslationOptions(TranslationOptions):
    fields = ('action_desc',)


class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description', )


class ProductDraftTranslationOptions(TranslationOptions):
    fields = ('name', 'description', )


translator.register(CreditAction, CreditActionTranslationOptions)
translator.register(Product, ProductTranslationOptions)
translator.register(ProductDraft, ProductDraftTranslationOptions)
