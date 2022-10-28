import os
import datetime
import ssl

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.core.validators import RegexValidator
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string, get_template
# from weasyprint import HTML, CSS
from rest_framework.utils import model_meta

from icf import settings
from icf.settings import MEDIA_ROOT
from icf_entity.permissions import ICFEntityUserPermManager
from icf_featuredevents.models import EventProduct
from icf_generic.api.serializers import CitySerializer, AddressSerializer, AddressRetrieveSerializer
from icf_orders import app_settings
from icf_orders.api.mixins import ICFCreditManager
from icf_orders.models import CreditHistory, CreditPurchase, CreditDistribution, CreditAction, \
    CreditInvoices, CountryTax, SubscriptionPlan, ICFPaymentTransaction, Subscription, Product, Cart, BillingAddress, \
    OrderDetails, PaymentStatus, Wallet, WithdrawalTransaction
from icf_entity.models import Entity, Logo, EntityPerms
from icf_generic.Exceptions import ICFException
from icf_generic.models import City, Type
from rest_framework import status, serializers
from rest_framework.serializers import ModelSerializer, Serializer
from django.utils.translation import ugettext_lazy as _

import logging

from icf_messages.manager import ICFNotificationManager

logger = logging.getLogger(__name__)
payment_logger = logging.getLogger("icf.integrations.payment")

PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                             message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")


class CreditCostSerializerForCountryTax(ModelSerializer):
    class Meta:
        model = Product
        fields = ['cost', 'unit']


class CreditActionSerializer(ModelSerializer):
    content_type = serializers.StringRelatedField()
    credit = serializers.StringRelatedField()

    class Meta:
        model = CreditAction
        fields = '__all__'


class CreditSummarySerializer(ModelSerializer):
    action = serializers.StringRelatedField()
    entity = serializers.StringRelatedField()
    user = serializers.StringRelatedField()

    class Meta:
        model = CreditHistory
        fields = '__all__'


class CreditHistorySerializer(ModelSerializer):
    entity = serializers.StringRelatedField()
    user = serializers.StringRelatedField()
    action = serializers.StringRelatedField()

    class Meta:
        model = CreditHistory
        fields = '__all__'


class CreditDistributionSerializer(ModelSerializer):
    app_name = serializers.SerializerMethodField()

    class Meta:
        model = CreditDistribution
        fields = ['app', 'app_name', 'credits', ]

    def get_app_name(self, obj):
        return obj.app.name


class CreditSummarySerializer(Serializer):
    available_credit = serializers.SerializerMethodField()
    cost_for_credit = serializers.SerializerMethodField()
    distribution = serializers.SerializerMethodField()
    unassigned_credits = serializers.SerializerMethodField()
    country_tax = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = ['available_credit', 'cost_for_credit', 'distribution', 'unassigned_credits', 'country_tax']

    def get_available_credit(self, obj):
        return ICFCreditManager.get_available_credit(entity=obj)

    def initialize_credit(self, entity):
        app_types = Type.objects.all()
        for app_type in app_types:
            try:
                cd_obj = CreditDistribution.objects.get(entity=entity, app=app_type)
            except ObjectDoesNotExist as oe:
                CreditDistribution.objects.create(entity=entity, app=app_type, credits=0)

    def get_distribution(self, obj):

        #
        # Create empty entries for each app in the credit distribution model for the entity ( if not there already )
        #
        self.initialize_credit(obj)
        cd_qs = CreditDistribution.objects.filter(entity=obj)
        # if not cd_qs:
        #     self.initialize_credit(obj)
        #     cd_qs = CreditDistribution.objects.filter(entity=obj)

        serializer = CreditDistributionSerializer(cd_qs, many=True)
        return serializer.data

    def get_cost_for_credit(self, obj):
        try:
            curr_code = app_settings.DEFAULT_CURRENCY or "USD"
            cost = Product.objects.get(product_type=Product.CREDIT, currency__name=curr_code)
            return CreditCostSerializerForCountryTax(cost).data
            # resp = "{} credit = {} {} ".format(cost.credits, cost.cost, cost.currency.code)
            # return resp
        except Exception as e:
            logger.exception(e)
            raise ICFException(_("Default currency and cost is not configured, please contact system administrator"),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_unassigned_credits(self, obj):
        # return get_unassigned_credit(entity = obj)
        return ICFCreditManager.get_unassigned_credit(entity=obj)

    def get_country_tax(self, obj):
        try:
            c_tax = CountryTax.objects.get(country=obj.address.city.state.country)
            return c_tax.percentage
        except Exception as e:
            country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
            return country_tax.percentage


class TransactionHistotySerializer(ModelSerializer):
    entity = serializers.StringRelatedField()
    user = serializers.StringRelatedField()

    class Meta:
        model = CreditPurchase
        fields = '__all__'


class AssignCreditsSerializer(ModelSerializer):
    class Meta:
        model = CreditDistribution
        fields = ['app', 'credits']

    def create(self, validated_data):
        request = self.context['request']
        entity_slug = request.parser_context.get('kwargs')['entity_slug']
        try:
            entity = Entity.objects.get(slug=entity_slug)
            app = validated_data.get('app')
        except Entity.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(
                _("You cannot assign credits to an invalid entity. Please recheck the entity and try again."),
                status_code=status.HTTP_404_NOT_FOUND)
        except Type.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(
                _("You cannot assign credits to an invalid application. Please recheck the application and try again."),
                status_code=status.HTTP_404_NOT_FOUND)

        # unassigned_credit = get_unassigned_credit(entity)
        unassigned_credit = ICFCreditManager.get_unassigned_credit(entity=entity)
        new_credit = validated_data.get('credits')

        try:
            existing_cdo = CreditDistribution.objects.get(entity=entity, app=app)
            app_credit = existing_cdo.credits

            if new_credit <= app_credit:
                existing_cdo.credits = new_credit
                existing_cdo.save(update_fields=['credits'])
            elif new_credit > app_credit:
                difference = new_credit - app_credit
                if difference <= unassigned_credit:
                    existing_cdo.credits = new_credit
                    existing_cdo.save(update_fields=['credits', ])
                else:
                    logger.exception("Insufficient credits available, cannot assign credits.")
                    raise ICFException(
                        _("You need more credits to perform this action. Please click here to purchase credits."),
                        status_code=status.HTTP_400_BAD_REQUEST)
            return existing_cdo
        except CreditDistribution.DoesNotExist:
            if unassigned_credit >= new_credit:
                created_cdo = CreditDistribution.objects.create(entity=entity, app=app, credits=new_credit)
                return created_cdo
        except ICFException as e:
            logger.exception(e)
            raise
        except Exception as e:
            logger.exception(e)
            raise ICFException("Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetCreditForActionSerializer(ModelSerializer):
    start_date = serializers.DateTimeField(default=None)
    end_date = serializers.DateTimeField(default=None)

    class Meta:
        model = CreditAction
        fields = ['credit_required', 'start_date', 'end_date']
        read_only_fields = ['credit_required']

    def get_credits(self, instance):
        start_date = self.validated_data.get('start_date')
        end_date = self.validated_data.get('end_date')

        if start_date and end_date:
            if ICFCreditManager.is_valid_interval(start_date, end_date):
                intervals = ICFCreditManager.get_num_of_intervals(start_date, end_date, instance.action)
                instance.credit_required = ICFCreditManager.get_credit_for_action(action=instance.action,
                                                                                  interval=intervals)
                instance.start_date = start_date
                instance.end_date = end_date
            else:
                logger.exception("Invalid time duration")
                raise ICFException(
                    _("Please review your start date and end date and try again. You can contact customer support to get help."),
                    status_code=status.HTTP_400_BAD_REQUEST)

        else:
            instance.credits = instance.credit_required

        return instance


class InvoiceSerializer(serializers.Serializer):
    credits = serializers.IntegerField()
    currency = serializers.CharField(max_length=20, allow_null=True, required=False)

    def create(self, validated_data):

        request = self.context['request']

        entity_slug = request.parser_context.get('kwargs')['entity_slug']
        try:
            entity = Entity.objects.get(slug=entity_slug)
        except Entity.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(
                _("You cannot assign credits to an invalid entity. Please review your entity and try again."),
                status_code=status.HTTP_400_BAD_REQUEST)

        path = os.path.join(MEDIA_ROOT, "invoices")
        filename = os.path.join(path, "{}_invoice_{}.pdf".format(entity_slug, 1))

        # Cost for credit
        icf_credits = validated_data.get('credits')
        currency = getattr(validated_data, 'currency', 'USD').lower()

        cost_for_credit = Product.objects.get(product_type=Product.CREDIT, currency__name=currency)
        unit_cost = cost_for_credit.cost
        unit_credits = cost_for_credit.unit
        if icf_credits > unit_credits:
            cost = eval(unit_cost) * icf_credits / unit_credits
        else:
            logger.exception("Minimum purchase of credits should more than {}".format(cost_for_credit.credits))
            raise ICFException(_("The minimum order for purchase of credits is {}".format(cost_for_credit.credits)),
                               status_code=status.HTTP_400_BAD_REQUEST)
        try:
            if entity.address:
                country_tax = CountryTax.objects.get(country=entity.address.city.state.country)
                # VAT = cost * (country_tax.percentage/100)
                # total_cost = cost + VAT
            else:
                country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)

            VAT = cost * (country_tax.percentage / 100)
            total_cost = cost + VAT

        except CountryTax.DoesNotExist:
            country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
            VAT = cost * (country_tax.percentage / 100)
            total_cost = cost + VAT

        template = get_template('credits/invoice.html')

        context = {}

        # date
        invoice = {}
        this_day = datetime.datetime.today()
        this_date = this_day.date
        invoice['date'] = this_date
        invoice['total_credits'] = icf_credits
        invoice['cost'] = cost
        invoice['unit_cost'] = unit_cost
        invoice['unit_credits'] = unit_credits
        invoice['currency'] = cost_for_credit.currency.name
        valid_till = datetime.datetime.today() + datetime.timedelta(days=30)
        invoice['valid_till'] = valid_till.date
        invoice['VAT'] = VAT
        invoice['total_cost'] = total_cost

        inv_num = 1
        try:
            inv_num += CreditInvoices.objects.filter(created__year=this_day.year).last().invoice_num
        except AttributeError as ae:
            pass

        invoice['number'] = inv_num
        context['invoice'] = invoice

        customer = {}
        customer['name'] = entity.name
        customer['address_1'] = entity.address.address_1
        customer['address_2'] = entity.address.address_2
        customer['city'] = entity.address.city
        customer['phone'] = entity.phone
        customer['email'] = request.user.email
        customer['contactperson'] = request.user.display_name

        context['customer'] = customer

        context['icube'] = app_settings.ICUBE_ADDRESS
        context['account'] = app_settings.ACCOUNT_DETAILS
        context['policy'] = app_settings.Non_Refund_Policy
        context['exchange_rate'] = app_settings.EXCHANGE_RATE

        ssl._create_default_https_context = ssl._create_unverified_context
        html = template.render(context)
        try:
            # pdf_file = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(filename)
            pass
        except Exception as e:
            logger.exception(e)
            raise ICFException(_("Could not create invoice, please try again"),
                               status_code=status.HTTP_400_BAD_REQUEST)

        email_body = str(app_settings.INVOICE_EMAIL_BODY).format(request.user.display_name)

        msg = EmailMessage(subject=app_settings.INVOICE_EMAIL_SUBJECT,
                           body=email_body,
                           to=[request.user.email, ],
                           cc=[app_settings.INVOICE_EMAIL_CC, ])

        msg.attach('iCUBEFARM-Credits-Invoice.pdf', open(filename, 'rb').read(), 'application/pdf')
        msg.content_subtype = "html"
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION')
        detail_msg = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL')
        details = detail_msg.format(request.user.display_name, message, entity.display_name)
        ICFNotificationManager.add_notification(user=request.user, message=message, details=details)

        obj = CreditInvoices.objects.create(entity=entity, user=request.user, credits=icf_credits, invoice_num=inv_num)
        obj.credits = icf_credits
        obj.currency = currency
        return obj


class BuyCreditsUsingStripeInputSerilizer(Serializer):
    credits = serializers.IntegerField()
    currency = serializers.CharField(max_length=20, allow_null=True, required=False)
    entity_slug = serializers.CharField(max_length=20, allow_null=True, required=False)
    stripeToken = serializers.CharField(max_length=50, allow_null=True, required=False)


class BuyCreditsUsingPaypalInputSerilizer(Serializer):
    credits = serializers.IntegerField()
    currency = serializers.CharField(max_length=20, allow_null=True, required=False)
    entity_slug = serializers.CharField(max_length=50, allow_null=True, required=False)
    paymentToken = serializers.CharField(allow_null=True, required=False)
    paymentID = serializers.CharField(allow_null=True, required=False)
    total_amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_amount_with_tax = serializers.DecimalField(max_digits=8, decimal_places=2)
    VAT = serializers.DecimalField(max_digits=8, decimal_places=2)


class ProductListSerializer(ModelSerializer):
    currency = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = '__all__'


class SubscriptionPlanListSerializer(ModelSerializer):
    product = ProductListSerializer()

    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class ICFPaymentTransactionListSerializer(ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = ICFPaymentTransaction
        fields = ['id', 'user', 'resp_transaction_id', 'req_date', 'resp_amount_in_dollars', 'payment_status']


class ICFPaymentTransactionSerializer(ModelSerializer):
    class Meta:
        model = ICFPaymentTransaction
        fields = '__all__'
        # fields = ['id', 'user', 'resp_transaction_id', 'req_date', 'resp_amount_in_dollars', 'payment_status']


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class OrderDetailsSerializer(ModelSerializer):
    # transaction = ICFPaymentTransactionSerializer()
    user = serializers.SerializerMethodField()
    resp_amount_in_dollars = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    req_date = serializers.SerializerMethodField()
    order_no = serializers.SerializerMethodField()
    resp_transaction_id = serializers.SerializerMethodField()

    class Meta:
        model = OrderDetails
        fields = ['id', 'user', 'order_no', 'resp_transaction_id', 'req_date', 'resp_amount_in_dollars',
                  'payment_status']

    def get_user(self, obj):
        return obj.user.email

    def get_resp_amount_in_dollars(self, obj):
        return obj.transaction.resp_amount_in_dollars

    def get_payment_status(self, obj):
        # return obj.transaction.payment_status
        payment_status_str = ''
        for tuple_obj in PaymentStatus.PAYMENT_STATUS_CHOICES:
            if tuple_obj[0] == int(obj.transaction.payment_status):
                payment_status_str = tuple_obj[1]
        return payment_status_str

    def get_req_date(self, obj):
        return obj.transaction.req_date

    def get_resp_transaction_id(self, obj):
        return obj.transaction.resp_transaction_id

    def get_order_no(self, obj):
        return obj.transaction.order_no


class ProductDetailSerializer(ModelSerializer):
    product_item_id = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_product_item_id(self, obj):
        try:
            if obj.product_type == Product.SUBSCRIPTION:
                return SubscriptionPlan.objects.get(product=obj.pk).pk
            if obj.product_type == Product.EVENT_PRODUCT:
                return EventProduct.objects.get(product=obj.pk).pk
        except Exception:
            return None


class SubscriptionCreateUsingStripeSerializer(Serializer):
    currency = serializers.CharField()
    subscription_plan_id = serializers.IntegerField()
    entity_slug = serializers.CharField()
    stripeToken = serializers.CharField()
    total_amount_without_tax_in_USD = serializers.DecimalField(max_digits=8, decimal_places=2)


class SubscriptionCreateUsingPaypalSerializer(Serializer):
    currency = serializers.CharField()
    subscription_plan_id = serializers.IntegerField()
    entity_slug = serializers.CharField()
    paymentToken = serializers.CharField(allow_null=True, required=False)
    paymentID = serializers.CharField(allow_null=True, required=False)
    total_amount_with_tax_in_USD = serializers.DecimalField(max_digits=8, decimal_places=2)
    VAT = serializers.DecimalField(max_digits=8, decimal_places=2)


class SubscriptionCreateByOfflineSerializer(Serializer):
    currency = serializers.CharField()
    entity_slug = serializers.CharField()
    subscription_plan_id = serializers.IntegerField()
    # offline_paymentId = serializers.CharField(allow_null=True, required=False)
    total_amount_without_tax_in_USD = serializers.DecimalField(max_digits=8, decimal_places=2)
    # VAT = serializers.DecimalField(max_digits=8, decimal_places=2)


class PurchaseProductsListSerializer(Serializer):
    product_name = serializers.CharField(max_length=500)
    qty = serializers.IntegerField()
    entity = serializers.CharField(max_length=500, allow_null=True)
    unit_price = serializers.DecimalField(max_digits=8, decimal_places=2)
    details = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=1500)
    sub_total = serializers.DecimalField(max_digits=8, decimal_places=2)


class SubscriptionDetailSerializer(ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'

    entity = serializers.StringRelatedField()
    subscription_plan = serializers.StringRelatedField()
    action = serializers.StringRelatedField()


class ProductPurchaseUsingStripeSerializer(Serializer):
    product_info_list = serializers.ListField()
    stripeToken = serializers.CharField(max_length=50, allow_null=True, required=False)
    currency = serializers.CharField(max_length=50, allow_null=True, required=False)
    first_name = serializers.CharField(max_length=500)
    last_name = serializers.CharField(max_length=500)
    address_1 = serializers.CharField(max_length=50)
    address_2 = serializers.CharField(max_length=50, allow_null=True, required=False)
    entityPhone = serializers.CharField(validators=[PHONE_REGEX], max_length=17,
                                        allow_null=True)  # validators should be a list
    billingEmail = serializers.EmailField(allow_null=True)
    city = serializers.IntegerField()
    zip_code = serializers.CharField(max_length=25, allow_null=True, required=False)


class GenericProductSerializer(Serializer):
    product_name = serializers.CharField(max_length=50, allow_null=True, required=False)
    product_unit = serializers.IntegerField()
    individual_product_cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    product_description = serializers.CharField(max_length=50, allow_null=True, required=False)
    currency = serializers.CharField(max_length=20, allow_null=True, required=False)


class CreditPaymentSerializer(GenericProductSerializer):
    no_of_credits = serializers.IntegerField()
    stripeToken = serializers.CharField(max_length=50, allow_null=True, required=False)


class SubscriptionPaymentSerializer(GenericProductSerializer):
    stripeToken = serializers.CharField(max_length=50, allow_null=True, required=False)


class CartListSerializer(ModelSerializer):
    product = ProductListSerializer()
    product_id = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = '__all__'

    def get_product_id(self, obj):
        return obj.product.id


class CartSerializer(ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        cart = Cart.objects.filter(user=request.user)
        product = validated_data.get('product')
        if product.product_type == product.SUBSCRIPTION or product.product_type == product.CREDIT:
            if not ICFEntityUserPermManager.has_entity_perm(request.user, validated_data.get('entity'),
                                                            EntityPerms.ENTITY_ADMIN):
                ICFException("you do not permissions to buy credit or subscription")

        try:
            cart_item = cart.filter(product=validated_data.get('product')).first()

            """
            The user should be able to add product items to cart for one entity only at a time.
            """
            if cart_item and cart_item.entity:
                cart_item_entity = Entity.objects.get(id=cart_item.entity.id)
                if cart_item_entity.name != validated_data.get('entity_name'):
                    raise ICFException(
                        _("You already have product in the cart for entity {}. Please complete the purchase before adding product to another entity ").format(
                            cart_item_entity.name),
                        status_code=status.HTTP_400_BAD_REQUEST)

            if cart_item:
                cart_item.price = validated_data.get('quantity', 1) * product.cost
                cart_item.quantity = validated_data.get('quantity')
                cart_item.product_item_id = validated_data.get('product_item_id')
                cart_item.entity_name = validated_data.get('entity_name')
                cart_item.entity_email = validated_data.get('entity_email')
                cart_item.entity_phone = validated_data.get('entity_phone')
                cart_item.name_of_representative = validated_data.get('name_of_representative')
                cart_item.address = validated_data.get('address')
                cart_item.participants = validated_data.get('participants')
                cart_item.featured_event_slug = validated_data.get('featured_event_slug')
                cart_item.career_fair_slug = validated_data.get('career_fair_slug', None)
                cart_item.product_sub_type = validated_data.get('product_sub_type', None)
                cart_item.entity = validated_data.get('entity')
                # cart_item.entity = product.entity
                cart_item.save()
            else:
                cart_item = Cart.objects.create(**validated_data, user=request.user,
                                                price=product.cost * validated_data.get('quantity'))

            return cart_item

        except Exception:
            raise

    def update(self, instance, validated_data):
        product = validated_data.get('product', None)

        try:
            instance.price = validated_data.get('quantity', 1) * product.cost
            instance.quantity = validated_data.get('quantity', 1)
            instance.product_item_id = validated_data.get('product_item_id', None)
            instance.entity_name = validated_data.get('entity_name', None)
            instance.entity_email = validated_data.get('entity_email', None)
            instance.entity_phone = validated_data.get('entity_phone', None)
            instance.name_of_representative = validated_data.get('name_of_representative', None)
            instance.address = validated_data.get('address', None)
            instance.participants = validated_data.get('participants', None)
            instance.featured_event_slug = validated_data.get('featured_event_slug', None)
            instance.career_fair_slug = validated_data.get('career_fair_slug', None)
            instance.product_sub_type = validated_data.get('product_sub_type', None)
            instance.entity = validated_data.get('entity', None)
            instance.save()

            return instance

        except Exception:
            raise


class ProductPurchaseUsingPaypalSerializer(serializers.Serializer):
    product_info_list = serializers.ListField()
    currency = serializers.CharField(max_length=50, allow_null=True, required=False)
    paymentToken = serializers.CharField(allow_null=True, required=False)
    paymentID = serializers.CharField(allow_null=True, required=False)
    first_name = serializers.CharField(max_length=500)
    last_name = serializers.CharField(max_length=500)
    address_1 = serializers.CharField(max_length=50)
    address_2 = serializers.CharField(max_length=50, allow_null=True, required=False)
    entityPhone = serializers.CharField(validators=[PHONE_REGEX], max_length=17,
                                        allow_null=True)  # validators should be a list
    billingEmail = serializers.EmailField(allow_null=True)
    city = serializers.IntegerField()
    zip_code = serializers.CharField(max_length=25, allow_null=True, required=False)


class InvoiceForProductsSerializer(serializers.Serializer):
    product_info_list = serializers.ListField()
    currency = serializers.CharField(max_length=50, allow_null=True, required=False)
    first_name = serializers.CharField(max_length=500)
    last_name = serializers.CharField(max_length=500)
    address_1 = serializers.CharField(max_length=50)
    address_2 = serializers.CharField(max_length=50, allow_null=True, required=False)
    entityPhone = serializers.CharField(validators=[PHONE_REGEX], max_length=17,
                                        allow_null=True)  # validators should be a list
    billingEmail = serializers.EmailField(allow_null=True)
    city = serializers.IntegerField()
    zip_code = serializers.CharField(max_length=25, allow_null=True, required=False)


class BillingAddressRetrieveSerializer(ModelSerializer):
    address = AddressSerializer()

    class Meta:
        model = BillingAddress
        fields = '__all__'


class BuyerInformationRetrieveSerializer(Serializer):
    name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    entity = serializers.CharField(max_length=100, allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    phone = serializers.CharField(validators=[PHONE_REGEX], max_length=17,
                                  allow_null=True)  # validators should be a list
    billing_address = serializers.CharField(max_length=100, allow_null=True, required=False)


class ProductCreateSerializer(ModelSerializer):
    slug = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ["name", "unit", "cost", "currency", "description", "product_type", "buyer_type", "slug"]

    @transaction.atomic
    def create(self, validated_data):
        logger.info("Create product")

        entity = validated_data.get("entity")

        created_product = super(ProductCreateSerializer, self).create(validated_data)

        logger.info("Product created {}".format(created_product))

        return created_product


class ProductRetrieveSerializer(ModelSerializer):
    product_type = serializers.SerializerMethodField()
    product_type_name = serializers.SerializerMethodField()

    buyer_type = serializers.SerializerMethodField()
    buyer_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        # exclude_fields = ['career_fair', 'slug']
        fields = '__all__'

    def get_product_type(self, object):
        return object.support_type

    def get_product_type_name(self, obj):
        return Product.get_product_types().get(obj.product_type)

    def get_buyer_type(self, object):
        return object.buyer_type

    def get_buyer_type_name(self, obj):
        return Product.get_buyer_types().get(obj.buyer_type)


class ProductRetrieveUpdateSerializer(ModelSerializer):
    product_type = serializers.SerializerMethodField()
    product_type_name = serializers.SerializerMethodField()

    buyer_type = serializers.SerializerMethodField()
    buyer_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        exclude = ['entity', ]

    def update(self, instance, validated_data):

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot update product.\n")
            raise ICFException(_("Unknown user, cannot update product."), status_code=status.HTTP_400_BAD_REQUEST)

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    def get_product_type(self, object):
        return object.support_type

    def get_product_type_name(self, obj):
        return Product.get_product_types().get(obj.product_type)

    def get_buyer_type(self, object):
        return object.buyer_type

    def get_buyer_type_name(self, obj):
        return Product.get_buyer_types().get(obj.buyer_type)


class OrderDetailsForSalesSerializer(ModelSerializer):
    transaction = ICFPaymentTransactionSerializer()
    user = serializers.SerializerMethodField()
    product = ProductSerializer()
    resp_amount_in_dollars = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    req_date = serializers.SerializerMethodField()
    order_no = serializers.SerializerMethodField()
    resp_transaction_id = serializers.SerializerMethodField()

    class Meta:
        model = OrderDetails
        fields = ['id', 'user', 'product', 'transaction', 'order_no', 'resp_transaction_id', 'req_date', 'resp_amount_in_dollars',
                  'payment_status']

    def get_user(self, obj):
        return obj.user.email

    def get_product(self, obj):
        return obj.product

    # def get_transaction(self, obj):
    #     return obj.transaction

    def get_resp_amount_in_dollars(self, obj):
        return obj.transaction.resp_amount_in_dollars

    def get_payment_status(self, obj):
        # return obj.transaction.payment_status
        payment_status_str = ''
        for tuple_obj in PaymentStatus.PAYMENT_STATUS_CHOICES:
            if tuple_obj[0] == int(obj.transaction.payment_status):
                payment_status_str = tuple_obj[1]
        return payment_status_str

    def get_req_date(self, obj):
        return obj.transaction.req_date

    def get_resp_transaction_id(self, obj):
        return obj.transaction.resp_transaction_id

    def get_order_no(self, obj):
        return obj.transaction.order_no

class WithdrawalTransactionSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WithdrawalTransaction
        fields = [
                    "id",
                    "withdrawal_type",
                    "amount",
                    "fees",
                    "description",
                    "bank_account_no",
                    "bank_account_provider",
                    "bank_account_country",
                    "bank_account_name",
                    "bank_code",
                    "bank_branch_code",
                    "bank_account_key",
                    "bank_account_swift",
                    "bank_account_IBAN",

                    "mm_account",
                    "mm_account_provider",
                    "mm_account_country",
                    "mm_account_name",

                    "currency",
                    "message",
                    "created",

                    "status",
                    "city",
                    "city_name",
                 ]

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def validate(self, data):
        """
        Check that the amount to withdraw is not more than the entity's wallet balance.
        """
        # Pull in the wallet of the entity to be withdrawn from
        entity = self.context['entity']
        wallet = Wallet.objects.get(entity__slug=entity)
        if data['amount'] > wallet.balance:
            raise serializers.ValidationError("You do not have enough money to make this transaction")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'Withdrawal transaction'.
        """
        user = self.context['user']
        entity = self.context['entity']
        try:
        # Retrieve slug passed in to the context on the view and pull an entity object with it
            withdrawal_entity = entity.objects.get(slug=entity)
            return WithdrawalTransaction.objects.create(user=user, entity=withdrawal_entity, **validated_data)
        except entity.DoesNotExist as e:
            logger.exception(e)
            raise

class WalletRetrieveSerializer(ModelSerializer):
    name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    entity = serializers.CharField(max_length=100, allow_null=True, required=False)
    class Meta:
        model = Wallet
        fields = '__all__'
