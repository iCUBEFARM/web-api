from email.message import EmailMessage

from django.contrib import admin

# Register your models here.
from modeltranslation.admin import TranslationAdmin
from django.utils.safestring import mark_safe
from django.forms import Textarea

from icf_career_fair import app_settings
from icf_career_fair.models import CareerFair, CareerFairParticipant, CareerFairAdvertisement, Session, \
    CareerFairAndProduct, CareerFairImageType, CareerFairAdvertisementViews
from icf_career_fair.util import CareerFairUtil
from icf_entity.models import Entity
from django.conf import settings
from icf_generic.Exceptions import ICFException
from icf_item.models import Item
from icf_orders.models import Product, SubscriptionPlan, ActionSubscriptionPlan, Subscription, SubscriptionAction
from icf_entity.models import EntityUser
from django.db.models import Q
from datetime import datetime
import datetime as main_datetime_module
import logging

logger = logging.getLogger(__name__)


class CareerFairStatusFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Career Fair Status'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """

        return (
            (Item.ITEM_ACTIVE, 'Active Career Fairs'),
            (Item.ITEM_UNDER_REVIEW, 'Career Fairs Under Review'),
            (Item.ITEM_REJECTED, 'Career Fairs Rejected'),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value():
            return queryset.filter(status=self.value())


class CareerFairAdmin(TranslationAdmin):
    list_display = ['entity', 'title', 'start_date', 'expiry', 'status']
    list_filter = [CareerFairStatusFilter, 'created']
    search_fields = ['entity__name', 'title']
    list_editable = ['status', ]

    ordering = ['entity', 'title_en', 'title_es', 'title_fr', 'category', 'description_en', 'description_es',
                'description_fr', 'location', 'expiry', 'owner', 'slug', 'start_date', 'organiser_contact_email',
                'organiser_contact_phone', 'mode_of_cf', 'status']

    exclude = ['item_type']

    class Meta:
        model = CareerFair
        verbose_name_plural = 'CareerFairs'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['entity', 'title_en', 'title_es', 'title_fr', 'category', 'description_en', 'description_es',
                    'description_fr', 'location', 'expiry', 'owner', 'slug', 'start_date', 'organiser_contact_email',
                    'organiser_contact_phone', 'mode_of_cf']
        else:
            return []

    # def career_fair_status(self, obj):
    #     return ()

    # def get_queryset(self, request):
    #     qs = super(CareerFairAdmin, self).get_queryset(request)
    #     return qs.filter(Q(status=Item.ITEM_UNDER_REVIEW) | Q(status=Item.ITEM_REJECTED))

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.save()

        email_subject = None
        email_body = None
        email_to = None
        if 'status' in form.changed_data:
            CareerFairUtil.send_career_fair_review_email(request, obj)

        """
        if the admin approves careerfair , enable 90 days subscription plan for entity
        """
        # if obj.status == Item.ITEM_ACTIVE:
        #     is_free_careerfair_active = settings.FREE_CAREER_FAIR.get("is_active")
        #     if is_free_careerfair_active:
        #         plan_name = settings.FREE_CAREER_FAIR.get("plan_name")
        #         # product=Product.objects.filter(name=plan_name).first()
        #
        #         subscription_plan_obj = SubscriptionPlan.objects.filter(product__name=plan_name).first()
        #         if subscription_plan_obj:
        #
        #             subscription_plan_start_date = datetime.today().date()
        #             subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
        #                 subscription_plan_obj.duration)
        #             action_subscriptions = ActionSubscriptionPlan.objects.filter(
        #                 subscription_plan=subscription_plan_obj)
        #             entity = obj.entity
        #             user_entity = EntityUser.objects.filter(entity_id=entity.id).first()
        #             user = user_entity.user
        #             get_currently_active_subscription = Subscription.objects.filter(entity_id=entity.id,
        #                                                                             end_date__gte=subscription_plan_start_date)
        #             if get_currently_active_subscription.count() == 0:
        #                 if action_subscriptions:
        #                     # subscription_list = []
        #                     subscription = Subscription.objects.create(user=user, entity=entity,
        #                                                                start_date=subscription_plan_start_date,
        #                                                                end_date=subscription_plan_end_date,
        #                                                                subscription_plan=subscription_plan_obj,
        #                                                                is_active=True
        #                                                                )
        #                     for action_subscription in action_subscriptions:
        #                         subscription_action, created = SubscriptionAction.objects.get_or_create(
        #                             subscription=subscription, action=action_subscription.action,
        #                             max_count=action_subscription.max_limit)
        #
        #                     CareerFairUtil.send_free_subscription_email(request, obj, subscription_plan_start_date,
        #                                                                  subscription_plan_end_date,user)
        #                 else:
        #                     logger.info("no action subscription")
        #
        #             else:
        #                 logger.info("there are some active subscription")
        #                 print("there are some active subscription")
        #         else:
        #             logger("info there is no given subscription plan")


class CareerFairParticipantAdmin(admin.ModelAdmin):
    list_display = ['career_fair_title', 'career_fair_entity_name', 'user_email', 'participant_company',
                    'name_of_representative', 'representative_email']
    # list_filter = ['career_fair_title',]
    search_fields = ['career_fair_entity_name', 'career_fair_title', 'user_email', 'participant_company',
                     'name_of_representative', 'representative_email']

    # fields = '__all__'

    class Meta:
        model = CareerFairParticipant
        verbose_name_plural = 'CareerFairParticipants'

    def career_fair_title(self, obj):
        return obj.career_fair.title

    def career_fair_entity_name(self, obj):
        return obj.career_fair.entity.name

    def user_email(self, obj):
        return obj.user.email

    def participant_company(self, obj):
        entity = Entity.objects.get(id=obj.entity_id)
        return entity.name


class CareerFairAdvertisementStatusFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Career Fair Advertisement Status'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'ad_status'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """

        return (
            (CareerFairAdvertisement.APPROVED, 'Active'),
            (CareerFairAdvertisement.PENDING, 'Pending Review'),
            (CareerFairAdvertisement.REJECTED, 'Rejected'),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value():
            return queryset.filter(ad_status=self.value())


class CareerFairAdvertisementAdmin(admin.ModelAdmin):
    list_display = ['career_fair', 'entity', 'ad_image_type', 'image_tag', 'admin_comments', 'ad_status', 'number_of_views']
    readonly_fields = ['career_fair', 'entity', 'image_tag', 'product', 'number_of_views']
    list_editable = ['ad_status', 'admin_comments']
    list_per_page = 100
    list_display_links = None
    list_filter = [CareerFairAdvertisementStatusFilter, 'created']
    search_fields = ['entity__name', 'career_fair__title']


    class Meta:
        model = CareerFairAdvertisement
        verbose_name_plural = 'CareerFairAdvertisements'

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Make the admin comments as a text area
        :param db_field:
        :param kwargs:
        :return:
        """
        formfield = super(CareerFairAdvertisementAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'admin_comments':
            formfield.widget = Textarea(attrs=formfield.widget.attrs)

        return formfield

    def changelist_view(self, request, extra_context=None):
        extra_context = {'title': 'Career Fair Advertisements'}
        return super(CareerFairAdvertisementAdmin, self).changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        """
        Remove the add CareerFairAdvertisement option
        :param request:
        :return:
        """
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def image_tag(self, obj):
        if obj.ad_image_url:
            if obj.ad_image_type == CareerFairImageType.MOBILE_IMAGE:
                # return mark_safe('<img src="%s" style="width: 373px; height:104px;" />' % obj.ad_image_url)
                return mark_safe(
                    '<a href="{0}" target="_blank"><img src="{0}" style="width: 373px; height:104px;" /></a>'.format(
                        obj.ad_image_url))

            elif obj.ad_image_type == CareerFairImageType.DESKTOP_IMAGE:
                # return mark_safe('<img src="%s" style="width: 264px; height:445px;" />' % obj.ad_image_url)
                return mark_safe(
                    '<a href="{0}" target="_blank"><img src="{0}" style="width: 264px; height:445px;" /></a>'.format(
                        obj.ad_image_url))
        else:
            return 'No Image Found'

    image_tag.short_description = 'Ad Image'

    def career_fair(self, obj):
        return obj.career_fair.title

    def entity(self, obj):
        return obj.entity.name

    def product(self, obj):
        return obj.product.description

    def number_of_views(self, obj):
        return CareerFairAdvertisementViews.objects.filter(career_fair_advertisement=obj.id).values_list('number_of_views', flat=True).first()

    def save_model(self, request, obj, form, change):
        obj.save()

        email_subject = None
        email_body = None
        email_to = None
        if 'ad_status' in form.changed_data:
            CareerFairUtil.advertisement_status_change_email(request, obj)


class SessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'start_time', 'end_time', 'start_date_string']

    class Meta:
        model = Session
        verbose_name_plural = 'Sessions'


class CareerFairAndProductAdmin(admin.ModelAdmin):
    list_display = ['career_fair_title', 'product_sub_type']

    class Meta:
        model = CareerFairAndProduct
        verbose_name_plural = 'CareerFairAndProducts'

    def career_fair_title(self, obj):
        return obj.career_fair.title


admin.site.register(CareerFair, CareerFairAdmin)
# admin.site.register(Session, SessionAdmin)
# admin.site.register(CareerFairAndProduct, CareerFairAndProductAdmin)
admin.site.register(CareerFairAdvertisement, CareerFairAdvertisementAdmin)
# admin.site.register(CareerFairParticipant, CareerFairParticipantAdmin)
