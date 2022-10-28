from django.contrib import admin

# Register your models here.
from django_summernote.admin import SummernoteModelAdmin

from icf_generic.models import City, Country, State, Language, Address, Currency, FeaturedVideo, FeaturedEvent, FAQ, \
    AdminEmail, FAQCategory, QuestionCategory
from icf_auth.models import UserProfile
from icf_item.models import Type, Category
from modeltranslation.admin import TranslationAdmin


class CategoryAdmin(TranslationAdmin):
    list_display = ('name', 'description', 'get_type', )

    class Meta:
        model = Category
        verbose_name_plural = 'Categories'
        fields = ["name", "description", "type__app_label"]

    def get_type(self, obj):
        return obj.type.content_type.model

    # get_type.admin_order_field = 'type.content_type.model'  # Allows column order sorting
    get_type.short_description = 'Type'  # Renames column head


class CountryAdmin(TranslationAdmin):
    list_display = ('country',)
    #fields = ["name", "code"]

    class Meta:
        model = Country
        verbose_name_plural = 'Countries'
        ordering = ('country',)

    def __str__(self):
        return '%s' % (self.country or self.code)


class StateAdmin(TranslationAdmin):
    list_display = ('state',)
    # fields = ["name", "code", "country"]
    search_fields = ("state", "code", "country__country")

    class Meta:
        model = State
        verbose_name_plural = 'States'


class CityAdmin(TranslationAdmin):
    list_display = ('city',)
    search_fields = ("city", "state__state")
    # fields = ["city", "state"]

    class Meta:
        model = City
        verbose_name_plural = 'Cities'


class LanguageAdmin(TranslationAdmin):
    list_display = ('name', 'code',)

    class Meta:
        model = Language


class AddressAdmin(admin.ModelAdmin):
    class Meta:
        model = Address


class CurrencyAdmin(TranslationAdmin):
    list_display = ('name', 'code', )

    class Meta:
        model = Currency

    # code.short_description = 'Type'  # Renames column head


class FeaturedVideoAdmin(TranslationAdmin):
    list_display = ('title', 'description', 'status', 'is_main_video',)
    class Meta:
        model = FeaturedVideo
        verbose_name_plural = 'FeaturedVideos'


class FeaturedEventAdmin(TranslationAdmin):
    list_display = ('title', 'description', 'status', 'start_date', 'contact_email')
    class Meta:
        model = FeaturedEvent
        verbose_name_plural = 'FeaturedEvents'

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("slug",)
        form = super(FeaturedEventAdmin, self).get_form(request, obj, **kwargs)
        return form


class FAQCategoryAdmin(TranslationAdmin):
    class Meta:
        model = FAQCategory

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("slug",)
        form = super(FAQCategoryAdmin, self).get_form(request, obj, **kwargs)
        return form


class FAQAdmin(TranslationAdmin, SummernoteModelAdmin):
    list_display = ('question',)

    summernote_fields = ('answer',)

    class Meta:
        model = FAQ
        verbose_name_plural = 'FAQs'

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("slug",)
        form = super(FAQAdmin, self).get_form(request, obj, **kwargs)
        return form


class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ('category', 'faq',)

    # change_list_template = "admin/question_category_button.html"

    # def has_add_permission(self, request, obj=None):
    #     return True

    class Meta:
        model = QuestionCategory
        verbose_name_plural = 'QuestionCategories'


class AdminEmailsAdmin(admin.ModelAdmin):
    class Meta:
        model = AdminEmail
        verbose_name_plural = 'AdminEmails'


class TypeAdmin(TranslationAdmin):
    list_display = ('content_type', 'name', 'description',)

    class Meta:
        model = Type


admin.site.register(Country, CountryAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Language, LanguageAdmin)
#admin.site.register(Address, AddressAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(FeaturedVideo, FeaturedVideoAdmin)
admin.site.register(FeaturedEvent, FeaturedEventAdmin)
admin.site.register(FAQ, FAQAdmin)
admin.site.register(FAQCategory, FAQCategoryAdmin)
admin.site.register(QuestionCategory, QuestionCategoryAdmin)
