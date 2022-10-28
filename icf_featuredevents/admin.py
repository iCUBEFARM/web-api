from django import forms
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.forms import BaseInlineFormSet, ModelForm

# Register your models here.
from django_summernote.admin import SummernoteModelAdmin
from modeltranslation.admin import TranslationAdmin

from icf_featuredevents.models import FeaturedEvent, TermsAndConditions, FeaturedEventGallery, \
    EventProduct, Participant, FeaturedEventAndProduct


# class FeaturedEventCategoryInlineFormset(BaseInlineFormSet):
#     def save_new(self, form, commit=True):
#         return super(FeaturedEventCategoryInlineFormset, self).save_new(form, commit=commit)
#
#     def save_existing(self, form, instance, commit=True):
#         return form.save(commit=commit)


# class ProductInlineFormset(BaseInlineFormSet):
#     def save_new(self, form, commit=True):
#         return super(ProductInlineFormset, self).save_new(form, commit=commit)
#
#     def save_existing(self, form, instance, commit=True):
#         return form.save(commit=commit)


# class ProductInline(admin.TabularInline):
#     model = Product
#     formset = ProductInlineFormset
#     verbose_name_plural = 'FeaturedEvent by Product'
#     extra = 1
#     can_delete = True
#     show_change_link = True


# class FeaturedEventAndCategoryInline(admin.TabularInline):
#     model = FeaturedEventAndCategory
#     formset = FeaturedEventCategoryInlineFormset
#     verbose_name_plural = 'FeaturedEvent by Category'
#     extra = 1
#     can_delete = True
#     show_change_link = True
#     # inlines = [ProductInline, ]

    # def get_field_queryset(self, db, db_field, request):
    #     """ filter the City queryset by selected country """
    #     queryset = super().get_field_queryset(db, db_field, request)
    #     if db_field.name == 'product':
    #         if queryset is None:
    #             # If "ordering" is not set on the City admin, get_field_queryset returns
    #             # None, so we have to get it ourselves. See original source:
    #             # github.com/django/django/blob/2.1.5/django/contrib/admin/options.py#L209
    #             queryset = Product.objects.all()
    #         # Filter by country
    #         queryset = queryset.filter(category=1)
    #     return queryset

# ---------------------------------------------------------------------------------------------------------

# class FeaturedEventAndProductForm(forms.ModelForm):
#     class Meta:
#         model = FeaturedEventAndProduct
#         fields = '__all__'
#
#     product = forms.ModelMultipleChoiceField(queryset=EventProduct.objects.all(), widget=forms.CheckboxSelectMultiple(), required=True)
#
#     def __init__(self, *args, **kwargs):
#         super(FeaturedEventAndProductForm, self).__init__(*args, **kwargs)
#         if self.instance:
#             self.fields['product'].initial = EventProduct.objects.all()
#
#     def save(self, *args, **kwargs):
#         # FIXME: 'commit' argument is not handled
#         # TODO: Wrap reassignments into transaction
#         # NOTE: Previously assigned Foos are silently reset
#         instance = super(FeaturedEventAndProductForm, self).save(commit=False)
#
#         featured_event = self.cleaned_data.get('featured_event')
#         product_list = self.cleaned_data.get('product')
#         for product in product_list:
#             instance.product = product
#             instance.featured_event = featured_event
#             instance.save()
#             # FeaturedEventAndProduct.objects.save(featured_event=featured_event, product=product)
#
#         # self.fields['product'].initial.update(featuredevent=None)
#         # self.cleaned_data['product'].update(featuredevent=instance)
#         return instance
#

class FeaturedEventAndProductAdmin(admin.ModelAdmin):
    class Meta:
        model = FeaturedEventAndProduct
        verbose_name_plural = 'FeaturedEvent and Products'


class FeaturedEventAdmin(TranslationAdmin, SummernoteModelAdmin):
    inline_type = 'tabular'  # or could be 'stacked'
    fieldsets = (
        ('FeaturedEvent Details', {
            'fields': ('title', 'sub_title', 'image', 'description', 'email_content',
                       'status', 'location', 'start_date', 'end_date',
                       'start_date_timing', 'end_date_timing', 'contact_email',
                       'terms_and_conditions', 'is_featured_event', 'contact_no')
        }),
    )

    summernote_fields = ('description', 'email_content')

    # inlines = [FeaturedEventAndCategoryInline, ]

    class Meta:
        model = FeaturedEvent
        verbose_name_plural = 'FeaturedEvents'

    # class Media:
    #     js = ('getRelatedProducts.js',)
    #
    # def get_form(self, request, obj=None, **kwargs):
    #     self.exclude = ("slug", "category")
    #     form = super(FeaturedEventAdmin, self).get_form(request, obj, **kwargs)
    #     return form


class EventProductAdmin(ModelAdmin):
    class Meta:
        model = EventProduct
        verbose_name_plural = 'Event Products'

    # summernote_fields = ('description',)

    class Media:
        js = ('getRelatedProducts.js',)


# class FeaturedEventAndProductAdmin(ModelAdmin):
#
#     class Meta:
#         model = FeaturedEventAndProduct
#         verbose_name_plural = 'FeaturedEventAndProducts'


class TermsAndConditionsAdmin(TranslationAdmin, SummernoteModelAdmin):

    class Meta:
        model = TermsAndConditions
        verbose_name_plural = 'TermsAndConditions'

    summernote_fields = ('description',)


class FeaturedEventGalleryAdmin(TranslationAdmin):

    class Meta:
        model = FeaturedEventGallery
        verbose_name_plural = 'FeaturedEventGallery'


# class ParticipationTypeAdmin(admin.ModelAdmin):
#
#     class Meta:
#         model = ParticipationType
#         verbose_name_plural = 'ParticipationTypes'


# class FeaturedEventCategoryAdmin(TranslationAdmin, SummernoteModelAdmin):
#
#     class Meta:
#         model = FeaturedEventCategory
#         verbose_name_plural = 'FeaturedEventCategories'
#
#     summernote_fields = ('description',)
#
#     def get_form(self, request, obj=None, **kwargs):
#         self.exclude = ("slug",)
#         form = super(FeaturedEventCategoryAdmin, self).get_form(request, obj, **kwargs)
#         return form


class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('get_user_name', 'get_featured_event', 'get_product_name', 'quantity', 'entity_name', 'entity_email',
                    'phone_no', 'name_of_representative', 'address', 'is_payment_successful', 'total_cost')

    def get_user_name(self, obj):
        return obj.user.display_name

    def get_featured_event(self, obj):
        return obj.featured_event.title

    def get_product_name(self, obj):
        return obj.product.product.name

    class Meta:
        model = Participant
        verbose_name_plural = 'Participants'

    get_user_name.admin_order_field = 'user__dislayname'  # Allows column order sorting
    get_user_name.short_description = 'User Name'  # Renames column head
    get_featured_event.admin_order_field = 'featured_event__title'  # Allows column order sorting
    get_featured_event.short_description = 'User Name'  # Renames column head
    get_product_name.admin_order_field = 'product__name'  # Allows column order sorting
    get_product_name.short_description = 'Product Name'  # Renames column head


admin.site.register(FeaturedEvent, FeaturedEventAdmin)
admin.site.register(TermsAndConditions, TermsAndConditionsAdmin)
admin.site.register(FeaturedEventGallery, FeaturedEventGalleryAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(EventProduct, EventProductAdmin)
admin.site.register(FeaturedEventAndProduct, FeaturedEventAndProductAdmin)
# admin.site.register(FeaturedEventCategory, FeaturedEventCategoryAdmin)
