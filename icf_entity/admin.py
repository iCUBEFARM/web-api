from django.contrib import admin
from django import forms

# Register your models here.
from django.forms.widgets import RadioSelect
from icf_auth.models import User
from icf_orders.models import Product, Subscription
from modeltranslation.admin import TranslationAdmin

from icf_entity.models import Entity, Industry, Sector, CompanySize, FeaturedEntity, TeamMember


class IndustryAdmin(TranslationAdmin):
    list_display = ('industry', 'description',)
    class Meta:
        model = Industry
        verbose_name_plural = 'Industries'


class SectorAdmin(TranslationAdmin):
    list_display = ('sector', 'description',)

    class Meta:
        model = Sector
        verbose_name_plural = 'Sectors'


class CompanySizeAdmin(TranslationAdmin):
    list_display = ('size', 'description',)

    class Meta:
        model = CompanySize
        verbose_name_plural = 'CompanySizes'





# def boolean_coerce(value):
#     # value is received as a unicode string
#    if str(value).lower() in ( '1', 'true' ):
#        return True
#    elif str(value).lower() in ( '0', 'false' ):
#        return False
#    return None


# class TeamMemberAdminForm(forms.ModelForm):
#
#     class Meta:
#         fields = ["name", "position", "featured_entity", "is_incharge", "image"]
#         model = TeamMember

    # def __init__(self, *args, **kwargs):
    #     super(TeamMemberAdminForm, self).__init__(*args, **kwargs)
    #     self.fields['is_incharge'] = forms.BooleanField(
    #         widget=forms.RadioSelect(choices=((self.prefix, 'status'),)))
    #
    #     # enter your fields except primary as you had before.
    #
    # def add_prefix(self, field_name):
    #     if field_name == 'is_incharge':
    #         return field_name
    #     else:
    #         return self.prefix and ('%s-%s' % (self.prefix, field_name)) or field_name



class TeamMemberAdmin(admin.TabularInline):
    model = TeamMember
    fields = ["name", "position", "featured_entity", "is_incharge", "image"]
    # form = TeamMemberAdminForm
    # extra = 1


class FeaturedEntityAdmin(admin.ModelAdmin):
    list_display = ('get_entity_name', 'title', 'start_date', 'end_date', 'status',)
    inlines = [TeamMemberAdmin, ]

    def save_model(self, request, obj, form, change):
        f_id = None

        if obj.status == FeaturedEntity.FEATURED_ENTITY_ACTIVE:
            f_id = obj.id
        for a in FeaturedEntity.objects.all():
            if a.id != f_id:
                a.status = FeaturedEntity.FEATURED_ENTITY_INACTIVE
                a.save()
        obj.save()

    def get_entity_name(self, obj):
        return obj.entity.name

    get_entity_name.admin_order_field = 'entity__name'  # Allows column order sorting
    get_entity_name.short_description = 'Entity Name'  # Renames column head


class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_by', 'has_subscription', 'created')
    search_fields = ['name']
    list_filter = ['status']

    # def save_model(self, request, obj, form, change):
    #
    #     if obj.status == Entity.ENTITY_ACTIVE:
    #         f_id = obj.id
    #     for a in FeaturedEntity.objects.all():
    #         if a.id != f_id:
    #             a.status = FeaturedEntity.FEATURED_ENTITY_INACTIVE
    #             a.save()
    #     obj.save()

    def get_entity_name(self, obj):
        return obj.entity.name

    # Retrieve Entity via the entity email
    def created_by(self, obj):
        user = User.objects.filter(email=obj.email).first()
        return user

    # From oder.subscription model retrieve Entity subscription details
    def has_subscription(self, obj):
        sub =  Subscription.objects.filter(entity__pk=obj.pk).first()
        if sub: return sub.subscription_plan

    get_entity_name.admin_order_field = 'entity__name'  # Allows column order sorting
    get_entity_name.short_description = 'Entity Name'  # Renames column head


# New EntityAdmin class for
# for Admin Entity management
# class EntityAdmin(admin.ModelAdmin):
#     list_display = ['name', 'status', 'created_by', 'has_subscription', 'created']
#     # list_display = ( 'name','status', 'created_by', 'has_subscription', 'created')
#     search_fields = ['name']
#     list_filter = ['status']
#
#     class Meta:
#         model = Entity
#         verbose_name_plural = 'Entities'
#
#     # Retrieve Entity via the entity email
#     def created_by(self, obj):
#         user = User.objects.filter(email=obj.email).first()
#         return user
#
#     # From oder.subscription model retrieve Entity subscription details
#     def has_subscription(self, obj):
#         sub =  Subscription.objects.filter(entity__pk=obj.pk).first()
#         if sub: return sub.subscription_plan


admin.site.register(Industry, IndustryAdmin)
admin.site.register(Sector, SectorAdmin)
admin.site.register(CompanySize, CompanySizeAdmin)
admin.site.register(FeaturedEntity, FeaturedEntityAdmin)
admin.site.register(Entity, EntityAdmin)

