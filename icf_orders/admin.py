from dal import autocomplete
from django import forms
from django.contrib import admin

# Register your models here.
from django.forms import ModelChoiceField, ModelForm, BaseInlineFormSet
from django_summernote.admin import SummernoteModelAdmin
from modeltranslation.admin import TranslationAdmin
from rest_framework import status

from icf_auth.models import User
from icf_orders.CalculateCreditHelper import CalculateCreditChargeHelper
from icf_orders.app_settings import PURCHASE_CREDITS
from icf_orders.models import CreditHistory, \
    CreditAction, AvailableBalance, CountryTax, TaxType, ICFPaymentTransaction, Subscription, ActionSubscriptionPlan, \
    CreditDistribution, SubscriptionPlan, Product, SubscriptionAction, PaymentType, PaymentStatus
from icf_entity.models import Entity
from icf_generic.Exceptions import ICFException


class UserEmailChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.id


class AvailablebalanceForm(ModelForm):
    entity = forms.ModelChoiceField(
        queryset=Entity.objects.all(),
        widget=autocomplete.ModelSelect2(url='/api/orders/entity-autocomplete/')
    )

    class Meta:
        model = AvailableBalance
        readonly_fields = ['available_credits', ]
        fields = "__all__"

    class Media:
        js = ('getentityuserinadmin.js',)

    def clean(self):
        if self.errors.get('user'):
            del self.errors['user']
        data = self.cleaned_data
        user = self.data.get('user')
        user = User.objects.get(email=user)
        data['user'] = user
        return data


class AvailablebalanceAdmin(admin.ModelAdmin):
    model = AvailableBalance
    list_display = ('entity', 'user_email', 'available_credits',)
    list_display_links = None
    list_filter = ('user__email',)
    search_fields = ['entity__name', 'user__email', ]
    raw_id_fields = ('user',)

    # Error: render() got an unexpected keyword argument 'renderer'
    # Had tocomment of this line below
    # form = AvailablebalanceForm

    # def get_readonly_fields(self, request, obj=None):
    #     if obj == None:
    #         return ()
    #     return ('available_credits',)

    def user_email(self, obj):
        return obj.user.email


    def save_model(self, request, obj, form, change):
        try:
            action = CreditAction.objects.get(action=PURCHASE_CREDITS)
        except CreditAction.DoesNotExist:
            raise ICFException("Invalid action, please check and try again.",
                               status_code=status.HTTP_400_BAD_REQUEST)

        CreditHistory.objects.create(entity=obj.entity, user=obj.user, available_credits=obj.available_credits,
                                     action=action, is_active=True)

        try:
            entity_balance = AvailableBalance.objects.get(entity=obj.entity)
            total_balance = entity_balance.available_credits + obj.available_credits
            entity_balance.available_credits = total_balance
            entity_balance.save(update_fields=['available_credits'])
            CalculateCreditChargeHelper().assign_all_credits_to_job(obj.entity, entity_balance.available_credits)
        except AvailableBalance.DoesNotExist as dne:
            obj.save()
            CalculateCreditChargeHelper().assign_all_credits_to_job(obj.entity, obj.available_credits)

    # DoneBy: Moses: Commented out so that raw_id_fields = ('user',) will replace the user field
    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == 'user':
    #         return UserEmailChoiceField(queryset=User.objects.all())
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CreditHistoryAdmin(admin.ModelAdmin):
    list_display = ('get_entity_name', 'get_user_name', 'updated', 'get_action', 'debits', 'available_credits',)
    list_filter = ['action', ]
    raw_id_fields = ('user',)

    class Meta:
        model = CreditHistory
        verbose_name = 'Credit History'
        verbose_name_plural = 'Credit Histories'

    def get_entity_name(self, obj):
        return obj.entity.name

    def get_user_name(self, obj):
        return obj.user.username

    def get_action(self, obj):
        try:
            return obj.action.action
        except:
            return None

    get_entity_name.admin_order_field = 'entity__name'  # Allows column order sorting
    get_entity_name.short_description = 'Entity Name'  # Renames column head
    get_user_name.admin_order_field = 'user__username'  # Allows column order sorting
    get_user_name.short_description = 'User Name'  # Renames column head
    get_action.admin_order_field = 'action__action'  # Allows column order sorting
    get_action.short_description = 'Action'  # Renames column head


class CountryTaxAdmin(admin.ModelAdmin):
    list_display = ('tax_type', 'country', 'percentage')

    class Meta:
        model = CountryTax
        fields = '__all__'


class ICFPaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'entity', 'get_user', 'payment_type', 'req_amount_in_dollars', 'payment_status']
    list_filter = ['payment_status', 'payment_type', ]
    list_editable = ['payment_status',]
    list_display_links = None
    search_fields = ['entity__name', ]

    class Meta:
        model = ICFPaymentTransaction
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        fields = '__all__'

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
    #
    # def save_model(self, request, obj, form, change):
    #     if 'payment_status' in form.changed_data:
    #         obj.payment.status = dict(PaymentStatus.PAYMENT_STATUS_CHOICES).get(int(obj.payment_status))
    #
    #     obj.save()

    def entity(self, obj):
        return obj.entity.name

    def get_payment_type(self, obj):
        payment_type_str = dict(PaymentType.PAYMENT_TYPE_CHOICES).get(int(obj.payment_type))
        return payment_type_str

    get_payment_type.short_description = 'Payment Type'

    def get_user(self, obj):
        return "{} {}".format(obj.user.first_name, obj.user.last_name)

    get_user.short_description = 'User'

    # def get_payment_status(self, obj):
    #     payment_status_str = dict(PaymentStatus.PAYMENT_STATUS_CHOICES).get(int(obj.payment_status))
    #     # ptl = [v for k, v in PaymentType.PAYMENT_TYPE_CHOICES if k == int(obj.payment_type)]
    #     return payment_status_str
    #
    # get_payment_type.short_description = 'Payment Type'  # Renames column head
    # get_payment_status.short_description = 'Payment Status'  # Renames column head


class CreditActionAdmin(TranslationAdmin):
    list_display = ('action', 'action_desc', 'credit_required', 'interval')

    class Meta:
        model = CreditAction
        fields = '__all__'


class SubscriptionForm(forms.ModelForm):
    entity = forms.ModelChoiceField(
        queryset=Entity.objects.all(),
        widget=autocomplete.ModelSelect2(url='/api/orders/entity-autocomplete/')
    )

    class Meta:
        model = Subscription
        # readonly_fields = ['action_count', ]
        fields = "__all__"

    class Media:
        js = ('getentityuserinadmin.js',)

    def clean(self):
        if self.errors.get('user'):
            del self.errors['user']
        data = self.cleaned_data
        # entity_user = self.data.get('user')
        # user = User.objects.get()
        # data['user'] = user
        return data


class SubscriptionAdmin(admin.ModelAdmin):
    # model = Subscription
    # list_display = ('entity', 'user_email', 'start_date', 'end_date', 'subscription_plan_name',)

    list_display = ['entity', 'start_date', 'end_date', 'subscription_plan_name', ]
    readonly_fields = ['entity', 'start_date', 'end_date', 'subscription_plan', 'user']

    # list_display_links = None
    # list_filter = ('user__email',)
    search_fields = ['entity__name', 'user__email', ]
    exclude = ['action_count', ]
    form = SubscriptionForm

    class Meta:
        model = Subscription
        # fields = '__all__'

    def entity(self, obj):
        return obj.entity.name

    def user_email(self, obj):
        return obj.user.email

    def subscription_plan_name(self, obj):
        return obj.subscription_plan.product.name

    def save_model(self, request, obj, form, change):

        try:
            action_subscriptions = ActionSubscriptionPlan.objects.filter(subscription_plan=obj.subscription_plan)
            if action_subscriptions:
                subscription, created = Subscription.objects.update_or_create(id=obj.id, entity=obj.entity,
                                                                              defaults={'user': obj.user,
                                                                                        'start_date': obj.start_date,
                                                                                        'end_date': obj.end_date,
                                                                                        'subscription_plan': obj.subscription_plan,
                                                                                        'is_active': obj.is_active}

                                                                              )
                if created:
                    for action_subscription in action_subscriptions:
                        SubscriptionAction.objects.create(subscription=subscription, action=action_subscription.action,
                                                          max_count=action_subscription.max_limit)
        except Exception as e:
            raise ICFException("something went wrong reason:{reason}.".format(reason=str(e)),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            return UserEmailChoiceField(queryset=User.objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProductAdmin(TranslationAdmin, SummernoteModelAdmin):
    # list_display = ('action', 'action_desc', 'credit_required', 'interval')

    summernote_fields = ('description',)
    list_filter = ('product_type',)
    search_fields = ('name', 'product_type',)

    class Meta:
        model = Product
        fields = '__all__'


class CreditDistributionAdmin(admin.ModelAdmin):
    list_display = ['entity', 'app', 'credits',]

    search_fields = ['entity__name' ]

    class Meta:
        model = CreditDistribution

    def entity(self, obj):
        return obj.entity.name


admin.site.register(CountryTax, CountryTaxAdmin)
admin.site.register(CreditHistory, CreditHistoryAdmin)
admin.site.register(AvailableBalance, AvailablebalanceAdmin)
admin.site.register(CreditAction, CreditActionAdmin)
admin.site.register(TaxType)
admin.site.register(ICFPaymentTransaction, ICFPaymentTransactionAdmin)
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(ActionSubscriptionPlan)
admin.site.register(CreditDistribution, CreditDistributionAdmin)
admin.site.register(Product, ProductAdmin)
