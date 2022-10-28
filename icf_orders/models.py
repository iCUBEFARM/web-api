from enum import Enum

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models

# Create your models here.
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver
from icf_auth.models import User
from icf_entity.models import Entity
from icf_generic.models import City, Currency, Type, Country, Address
from django.utils.translation import ugettext_lazy as _


class ProductType(Enum):
    SUBSCRIPTION = 1
    CREDIT = 2
    EVENT_PRODUCT = 3
    CAREER_FAIR_PRODUCT = 4
    OTHER = 5


class Product(models.Model):
    SUBSCRIPTION = 1
    CREDIT = 2
    EVENT_PRODUCT = 3
    CAREER_FAIR_PRODUCT = 4
    OTHER = 5

    PRODUCT_TYPE_CHOICES = (
        (SUBSCRIPTION, "SUBSCRIPTION"), (CREDIT, "CREDIT"), (EVENT_PRODUCT, "EVENT_PRODUCT"),
        (CAREER_FAIR_PRODUCT, "CAREER_FAIR_PRODUCT"), (OTHER, "OTHER"))

    INDIVIDUAL = 1
    ENTITY = 2
    SPONSOR = 3
    OTHER = 4

    BUYER_TYPE_CHOICES = (
        (INDIVIDUAL, "Individual"), (ENTITY, "Entity"), (SPONSOR, "Sponsor"), (OTHER, "Other"))

    name = models.CharField(_("name"), max_length=100)
    # here entity is the company which is creating this product
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='product')
    unit = models.PositiveIntegerField(default=1)
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    parent_product = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(_("description"), blank=True, null=True)
    product_type = models.SmallIntegerField(choices=PRODUCT_TYPE_CHOICES, default=EVENT_PRODUCT)
    buyer_type = models.SmallIntegerField(choices=BUYER_TYPE_CHOICES, default=INDIVIDUAL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_product_types(cls):
        return dict(cls.PRODUCT_TYPE_CHOICES)

    @classmethod
    def get_buyer_types(cls):
        return dict(cls.BUYER_TYPE_CHOICES)


class ProductDraft(models.Model):
    SUBSCRIPTION = 1
    CREDIT = 2
    EVENT_PRODUCT = 3
    CAREER_FAIR_PRODUCT = 4
    OTHER = 5

    PRODUCT_TYPE_CHOICES = (
        (SUBSCRIPTION, "SUBSCRIPTION"), (CREDIT, "CREDIT"), (EVENT_PRODUCT, "EVENT_PRODUCT"),
        (CAREER_FAIR_PRODUCT, "CAREER_FAIR_PRODUCT"), (OTHER, "OTHER"))

    INDIVIDUAL = 1
    ENTITY = 2
    SPONSOR = 3
    OTHER = 4

    BUYER_TYPE_CHOICES = (
        (INDIVIDUAL, "Individual"), (ENTITY, "Entity"), (SPONSOR, "Sponsor"), (OTHER, "Other"))

    name = models.CharField(_("name"), max_length=100)
    # here entity is the company which is creating this product
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='product_draft')
    unit = models.PositiveIntegerField(default=1)
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    parent_product = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(_("description"), blank=True, null=True)
    product_type = models.SmallIntegerField(choices=PRODUCT_TYPE_CHOICES, default=EVENT_PRODUCT)
    buyer_type = models.SmallIntegerField(choices=BUYER_TYPE_CHOICES, default=INDIVIDUAL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_product_types(cls):
        return dict(cls.PRODUCT_TYPE_CHOICES)

    @classmethod
    def get_buyer_types(cls):
        return dict(cls.BUYER_TYPE_CHOICES)



class CreditAction(models.Model):
    content_type = models.ForeignKey(Type,on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    action_desc = models.CharField(max_length=100, blank=True, null=True)
    credit_required = models.IntegerField()
    interval = models.IntegerField()

    def __str__(self):
        return "{}".format(self.action_desc)

#
# class CreditCost(models.Model):
#     currency = models.ForeignKey(Currency,on_delete=models.CASCADE)
#     cost = models.CharField(max_length=20)
#     credits = models.IntegerField()
#
#     def __str__(self):
#         return "{} Credit = {} {}".format(self.credits, self.cost, self.currency)


class CreditHistory(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    action = models.ForeignKey(CreditAction, on_delete=models.CASCADE,null = True,blank=True)
    debits = models.IntegerField(default=0)
    available_credits = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated', ]

    def __str__(self):
        return "{}".format(self.entity)

    # def available_credit_for_entity(self, entity):
    #     return CreditHistory.objects.filter(entity=entity).orderby(-id).first().available_credits


class CreditPurchase(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now_add=False,auto_now=True)
    transaction = models.IntegerField()
    gateway = models.CharField(max_length=50)
    status = models.BooleanField()

    def __str__(self):
        return "{}".format(self.entity)


class CreditDistribution(models.Model):
    entity = models.ForeignKey(Entity,on_delete=models.CASCADE)
    app = models.ForeignKey(Type,on_delete=models.CASCADE)
    credits = models.IntegerField()
    updated = models.DateTimeField(auto_now_add=False,auto_now=True)

    def __str__(self):
        return "{}".format(self.app)


class AvailableBalance(models.Model):
    entity = models.ForeignKey(Entity,on_delete=models.CASCADE)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    available_credits = models.IntegerField()

# @receiver(pre_save, sender=CreditPurchase)
# def credit_usage_pre_save_receiver(sender, instance, *args, **kwargs):
#     credit_usage = CreditHistory.objects.get(entity = instance.entity)
#     available_credit = credit_usage + instance.available_credits
#     instance.available_credits = available_credit


class CreditInvoices(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    invoice_num = models.IntegerField()
    credits = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_num


class TaxType(models.Model):
    tax_type = models.CharField(max_length=50)

    def __str__(self):
        return self.tax_type


class CountryTax(models.Model):
    tax_type = models.ForeignKey(TaxType, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE,null=True,blank=True)
    percentage = models.IntegerField()


class PaymentType:
    PAYMENT_TYPE_STRIPE = 1
    PAYMENT_TYPE_PAYPAL = 2
    PAYMENT_TYPE_OFFLINE = 3
    PAYMENT_TYPE_FREE_CHECKOUT = 4

    PAYMENT_TYPE_CHOICES = (
        (PAYMENT_TYPE_STRIPE, "PAYMENT_TYPE_STRIPE"), (PAYMENT_TYPE_PAYPAL, "PAYMENT_TYPE_PAYPAL"),
        (PAYMENT_TYPE_OFFLINE, "PAYMENT_TYPE_OFFLINE"), (PAYMENT_TYPE_FREE_CHECKOUT, "PAYMENT_TYPE_FREE_CHECKOUT"))


class PaymentStatus:
    SUCCESS = 1
    PENDING = 2
    ERROR = 3
    FAILURE = 4
    PAYMENT_STATUS_CHOICES = (
        (SUCCESS, "SUCCESS"), (PENDING, "PENDING"), (ERROR, "ERROR"), (FAILURE, "FAILURE"))


class ICFPaymentTransaction(models.Model):
    order_no = models.SlugField(blank=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True)
    payment_type = models.CharField(max_length=2, choices=[(str(x), y) for x, y in PaymentType.PAYMENT_TYPE_CHOICES])  # Choices is a list of Tuple
    req_date = models.DateTimeField(auto_now_add=True)
    req_amount_in_cents = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    req_amount_in_dollars = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    req_token = models.CharField(max_length=150, null=True)
    req_desc = models.CharField(max_length=500, null=True)

    resp_date = models.DateTimeField(null=True, blank=True)
    payment_status = models.CharField(max_length=2, choices=[(str(x), y) for x, y in PaymentStatus.PAYMENT_STATUS_CHOICES], default=PaymentStatus.FAILURE)  # Choices is a list of Tuple
    resp_error_code = models.CharField(max_length=150, null=True, blank=True)
    resp_error_details = models.CharField(max_length=1000, null=True, blank=True)
    resp_amount_in_cents = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    resp_amount_in_dollars = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    resp_transaction_id = models.CharField(max_length=500, null=True, blank=True)
    resp_currency = models.CharField(max_length=100, null=True, blank=True)
    resp_failure_code = models.CharField(max_length=100, null=True, blank=True)
    resp_failure_message = models.CharField(max_length=200, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


class WithdrawalType:
    WITHDRAWAL_TYPE_ACCOUNT = 1
    WITHDRAWAL_TYPE_MM = 2

    WITHDRAWAL_TYPE_CHOICES = (
        (WITHDRAWAL_TYPE_ACCOUNT, "WITHDRAWAL_TYPE_ACCOUNT"), (WITHDRAWAL_TYPE_MM, "WITHDRAWAL_TYPE_MM"),
       )
class WithdrawalTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True)
    withdrawal_type = models.CharField(max_length=2, choices=[(str(x), y) for x, y in WithdrawalType.WITHDRAWAL_TYPE_CHOICES])  # Choices is a list of Tuple
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    fees = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    description = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=2, choices=[(str(x), y) for x, y in PaymentStatus.PAYMENT_STATUS_CHOICES], default=PaymentStatus.FAILURE)  # Choices is a list of Tuple

    bank_account_no = models.CharField(max_length=100, null=True, blank=True)
    bank_account_provider = models.CharField(max_length=100, null=True, blank=True)
    bank_account_country = models.CharField(max_length=100, null=True, blank=True)
    bank_account_name = models.CharField(max_length=100, null=True, blank=True)
    bank_code = models.CharField(max_length=100, null=True, blank=True)
    bank_branch_code = models.CharField(max_length=100, null=True, blank=True)
    bank_account_key = models.CharField(max_length=100, null=True, blank=True)
    bank_account_swift = models.CharField(max_length=100, null=True, blank=True)
    bank_account_IBAN = models.CharField(max_length=100, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)

    mm_account = models.CharField(max_length=100, null=True, blank=True)
    mm_account_provider = models.CharField(max_length=100, null=True, blank=True)
    mm_account_country = models.CharField(max_length=100, null=True, blank=True)
    mm_account_name = models.CharField(max_length=100, null=True, blank=True)

    currency = models.CharField(max_length=100, null=True, blank='$')
    message = models.CharField(max_length=200, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

class Wallet(models.Model):
    entity = models.OneToOneField(
        Entity,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    withdrals = models.ForeignKey(WithdrawalTransaction, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

class SubscriptionPlan(models.Model):
    product = models.OneToOneField(Product, unique=True, on_delete=models.CASCADE)
    duration = models.IntegerField()

    def __str__(self):
        return self.product.name


class ActionSubscriptionPlan(models.Model):
    action = models.ForeignKey(CreditAction, on_delete=models.CASCADE)
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    max_limit = models.IntegerField(null=True)

    def __str__(self):
        return self.action.action


class Subscription(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.entity.name


class SubscriptionAction(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    action = models.ForeignKey(CreditAction, on_delete=models.CASCADE)
    action_count = models.IntegerField(default=0)
    max_count = models.IntegerField(null=True)

    class Meta:
        unique_together = ('subscription', 'action',)

    def __str__(self):
        return self.subscription.subscription_plan.product.name


class OrderDetails(models.Model):
    transaction = models.ForeignKey(ICFPaymentTransaction, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, null=True, related_name='entity_order', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, related_name="base_product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    content_type = models.ForeignKey(ContentType, related_name="content_type_order_details", on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, blank=True,null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_sub_type = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    product_item_id = models.IntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=50,null=True, blank=True)
    entity_email = models.CharField(max_length=50, null=True, blank=True)
    entity_phone = models.CharField(max_length=50, null=True, blank=True)
    name_of_representative = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    participants = models.CharField(max_length=500, null=True, blank=True)
    featured_event_slug = models.CharField(max_length=200, null=True, blank=True)
    career_fair_slug = models.CharField(max_length=200, null=True, blank=True)


class BillingAddress(models.Model):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered "
                                         "in the format: '+999999999'. Up to 15 digits allowed.")

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=200, null=True, blank=True)
    last_name = models.CharField(max_length=200, null=True, blank=True)
    billingEmail = models.EmailField()
    entityPhone = models.CharField(validators=[PHONE_REGEX], max_length=25, blank=True) # validators should be a list
    zip_code = models.CharField(max_length=25, null=True, blank=True)  # validators should be a list
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.address.address_1


