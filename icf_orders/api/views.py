from datetime import datetime
from django.utils import timezone

import stripe
from icf_career_fair.util import CareerFairUtil
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.test import TransactionTestCase
from rest_framework.exceptions import NotFound, ValidationError

from icf import settings
from icf_auth.models import User
from icf_auth.api.serializers import UserEmailSerializer
from icf_career_fair.models import CareerFairImageType,CareerFairAdvertisement,CareerFairProductSubType,CareerFair, CareerFairAndProduct, CareerFairParticipant, ParticipantAndProduct
from icf_featuredevents.models import EventProduct, FeaturedEvent, Participant, FeaturedEventAndProduct
from icf_generic.models import Currency, Address, City
from icf_orders import app_settings
from icf_orders.CalculateCreditHelper import CalculateCreditChargeHelper
from icf_orders.EmailHelper import PaymentEmailHelper

from icf_orders.api.serializers import CreditActionSerializer, CreditSummarySerializer, CreditHistorySerializer, OrderDetailsForSalesSerializer, \
    TransactionHistotySerializer, AssignCreditsSerializer, GetCreditForActionSerializer, \
    InvoiceSerializer, ICFPaymentTransactionListSerializer, SubscriptionPlanListSerializer, \
    BuyCreditsUsingStripeInputSerilizer, ProductDetailSerializer, SubscriptionCreateUsingStripeSerializer, \
    BuyCreditsUsingPaypalInputSerilizer, SubscriptionCreateUsingPaypalSerializer, SubscriptionCreateByOfflineSerializer, \
    SubscriptionDetailSerializer, ProductListSerializer, ProductPurchaseUsingStripeSerializer, \
    CreditPaymentSerializer, CartSerializer, ProductPurchaseUsingPaypalSerializer, InvoiceForProductsSerializer, \
    CartListSerializer, BillingAddressRetrieveSerializer, OrderDetailsSerializer, PurchaseProductsListSerializer, \
    BuyerInformationRetrieveSerializer, ProductCreateSerializer, ProductRetrieveSerializer, \
    ProductRetrieveUpdateSerializer, WalletRetrieveSerializer, WithdrawalTransactionSerializer
from icf_orders.app_settings import PURCHASE_CREDITS
from icf_orders.models import CreditHistory, CreditPurchase, CreditDistribution, CreditAction, \
    ICFPaymentTransaction, PaymentType, PaymentStatus, AvailableBalance, SubscriptionPlan, ActionSubscriptionPlan, \
    Subscription, Product, ProductType, SubscriptionAction, OrderDetails, Cart, CountryTax, BillingAddress, Wallet, WithdrawalTransaction
from icf_entity.models import Entity, EntityPerms
from icf_entity.permissions import IsEntityAdmin
from icf_generic.Exceptions import ICFException
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView, GenericAPIView, ListCreateAPIView, \
    DestroyAPIView, UpdateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import ugettext_lazy as _
import datetime as main_datetime_module

import logging

from icf_integrations.payments import ICFPaymentManager
from icf_integrations.sample_pay import ICFPayment, ICF_Payment_Transaction_Manager, ICFPaymentLogger, IcfBillGenerator, \
    PaymentManager
from icf_orders.purchase_product_detail_helper import PurchaseProductDetail

logger = logging.getLogger(__name__)

payment_logger = logging.getLogger("icf.integrations.payment")


class CreditForAction(ListAPIView):
    queryset = CreditAction.objects.all()
    serializer_class = CreditActionSerializer
    permission_classes = (IsAuthenticated,)


class EntityCreditSummaryView(RetrieveAPIView):
    queryset = Entity.objects.all()
    serializer_class = CreditSummarySerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)
    pagination_class = None

    def get_object(self):
        try:
            return Entity.objects.get(slug=self.kwargs.get('entity_slug'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise NotFound(detail="entity does not exist")


class CreditHistoryListView(ListAPIView):
    queryset = CreditHistory.objects.all()
    serializer_class = CreditHistorySerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)

    def get_queryset(self):
        queryset = self.queryset
        return queryset.filter(entity__slug=self.kwargs.get('entity_slug'))


# class ProductCreateApiView(CreateAPIView):
#     permission_classes = (IsAuthenticated,)
#     queryset = Product.objects.all()
#     serializer_class = ProductCreateSerializer
#
#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         headers = self.get_success_headers(serializer.data)
#         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#
#
# class ProductDetailApiView(RetrieveAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductRetrieveSerializer
#     # permission_classes = (IsAuthenticated, )
#     lookup_field = "slug"
#
#
# class ProductUpdateApiView(RetrieveUpdateAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductRetrieveUpdateSerializer
#     permission_classes = (IsAuthenticated)
#     lookup_field = "slug"
#
#     def get(self, request, *args, **kwargs):
#         return self.retrieve(request, *args, **kwargs)
#
#     def perform_update(self, serializer):
#         serializer.save()
#
#
# class ProductDeleteView(DestroyAPIView):
#
#     def get_object(self):
#         try:
#             entity = Entity.objects.get(slug=self.kwargs.get('entity_slug'))
#             return Product.objects.get(pk=self.kwargs.get('id'), entity=entity)
#
#         except ObjectDoesNotExist as e:
#             logger.debug(e)
#             raise NotFound(detail="Object does not exist")


class TransactionHistory(ListAPIView):
    queryset = CreditPurchase.objects.all()
    serializer_class = TransactionHistotySerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)


class AssignCreditView(CreateAPIView):
    queryset = CreditDistribution.objects.all()
    serializer_class = AssignCreditsSerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)
    pagination_class = None

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError:
            logger.exception("Cannot assign credits, Invalid app or entity")
            return Response({"detail": _("Cannot assign credits, invalid parameters, please check and try again")},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.debug(e)
            return Response(
                {"detail": _("The system is experiencing an error, please contact Customer Support for assistance")},
                status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class GetCreditForActionView(GenericAPIView):
    serializer_class = GetCreditForActionSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        resp_obj = serializer.get_credits(instance)
        resp_obj.start_date = serializer.validated_data.get('start_date')
        resp_obj.end_date = serializer.validated_data.get('end_date')
        resp_serializer = self.get_serializer(resp_obj)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)

    def get_object(self):
        try:
            return CreditAction.objects.get(action=self.kwargs.get('action'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise ICFException(_("Invalid action, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class GenerateInvoice(CreateAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = (IsEntityAdmin,)


class GetEntityUserForAdminList(APIView):

    def get(self, request):
        entity_name = request.GET.get('entity')
        try:
            entity = Entity.objects.get(name=entity_name)
        except:
            raise ICFException("Entity not found", status_code=status.HTTP_400_BAD_REQUEST)
        entity_user = User.objects.filter(entityuser__entity=entity)
        admin_user = []
        for user in entity_user:
            if user.has_perm(EntityPerms.ENTITY_ADMIN, entity):
                admin_user.append(user)
        serialized = UserEmailSerializer(admin_user, many=True)
        return Response(serialized.data)


def payment_form(request):
    context = {"stripe_key": settings.STRIPE_PUBLIC_KEY}
    return render(request, "payments\checkout.html", context)


class PurchaseCreditsByStripePaymentApiView(CreateAPIView):
    # queryset = Job.objects.all()
    serializer_class = BuyCreditsUsingStripeInputSerilizer
    permission_classes = (IsAuthenticated, IsEntityAdmin)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # stripe.api_key = "sk_test_BJUliYkgS5VZEKFM1UQAz9cF"
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            no_of_credits = int(serializer.validated_data.get("credits"))
            if no_of_credits <= 0:
                payment_logger.error("transaction failed. reason : {reason}".format(
                    reason="no of credits should be a non zero positive integer"))
                return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

            user = self.request.user
            cost_for_credit = Product.objects.get(product_type=Product.CREDIT, currency__name="USD")
            stripe.api_key = settings.STRIPE_SECRET_KEY
            entity_slug = serializer.validated_data.get("entity_slug").lstrip().rstrip()
            entity = Entity.objects.get(slug=entity_slug)
            token = serializer.validated_data.get("stripeToken").lstrip().rstrip()
            currency = serializer.validated_data.get("currency").lstrip().rstrip()
            description = "To buy credits"
            base_url = request.build_absolute_uri()

            total_amount_without_tax_dict = CalculateCreditChargeHelper().calculate_charges_without_tax_in_cents(
                cost_for_credit, no_of_credits)
            total_amount_without_tax_in_cents = total_amount_without_tax_dict['total_amount_without_tax_in_cents']
            total_amount_without_tax_in_USD = total_amount_without_tax_dict['total_amount_without_tax_in_USD']

            total_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(entity,
                                                                                                         total_amount_without_tax_in_USD)

            total_amount_with_tax_in_cents = total_amount_dict['total_amount_with_tax_in_cents']
            total_amount_with_tax_in_USD = total_amount_dict['total_amount_with_tax_in_USD']
            VAT_USD = total_amount_dict['VAT_USD']

            request_dict = {

                'user': user,
                'entity': entity,
                'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
                'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
                'token': token,
                'description': description,
                'payment_type': PaymentType.PAYMENT_TYPE_STRIPE.value

            }

            # payment = ICFPayment()
            # icf_charge_obj = payment.payment_service.make_payment(token, total_amount_with_tax_in_cents, currency, description)

            icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_STRIPE).make_payment(token,
                                                                                                                total_amount_with_tax_in_cents,
                                                                                                                currency,
                                                                                                                description)

            if icf_charge_obj.paid:
                # create  new record in AvailableBalance Table and CreditHistory Table to the user for this entity
                try:
                    action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                except CreditAction.DoesNotExist:
                    raise ICFException(_("Invalid action, please check and try again."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                CreditHistory.objects.create(entity=entity, user=user,
                                             available_credits=no_of_credits, action=action)

                try:
                    # entity_balance = AvailableBalance.objects.get(entity=self.entity, user=self.user)
                    entity_balance = AvailableBalance.objects.get(entity=entity)
                    total_balance = entity_balance.available_credits + no_of_credits
                    entity_balance.available_credits = total_balance
                    entity_balance.save(update_fields=['available_credits'])
                except AvailableBalance.DoesNotExist as dne:
                    entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
                                                                     available_credits=no_of_credits)
                CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
                ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict, icf_charge_obj)

                ICFPaymentLogger().log_stripe_payment_details(request_dict, icf_charge_obj)
                IcfBillGenerator().generate_bill(user, entity, no_of_credits, total_amount_without_tax_in_USD, currency,
                                                 VAT_USD, total_amount_with_tax_in_USD, base_url)

                return Response({"response_message": _("Transaction is successful."),
                                 "amount_paid": icf_charge_obj.resp_amount_in_dollars,
                                 "available_credits": entity_balance.available_credits,
                                 "no_of_credits": no_of_credits
                                 },
                                status=status.HTTP_200_OK)

            else:

                ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict, icf_charge_obj)
                ICFPaymentLogger().log_stripe_payment_details(request_dict, icf_charge_obj)
                # send an email to PURCHASE_CREDITS_PAYMENT_FAILURE_NOTIFICATION_EMAIL  failure payments
                email_subject = str(app_settings.PURCHASE_CREDITS_PAYMENT_FAILURE_SUBJECT).format(entity.name),
                payment_type = "Credit Card"

                payment_logger.info(
                    "transaction failed while purchase credits:{entity},\n "
                    "payment_type : {payment_type},\n ".format(entity=entity.name, payment_type=payment_type))

                email_body = str(app_settings.PURCHASE_CREDITS_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
                                                                                                  entity.name,
                                                                                                  user.display_name,
                                                                                                  user.email,
                                                                                                  total_amount_with_tax_in_USD)
                msg = EmailMessage(subject=email_subject,
                                   body=email_body,
                                   to=[app_settings.PURCHASE_CREDITS_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
                                   )
                msg.content_subtype = "html"
                msg.send()

                return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist as ce:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(ce)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except Entity.DoesNotExist as edn:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(e)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseCreditsByPayPalPaymentApiView(CreateAPIView):
    serializer_class = BuyCreditsUsingPaypalInputSerilizer
    permission_classes = (IsAuthenticated, IsEntityAdmin)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            currency = serializer.validated_data.get("currency").lstrip().rstrip()
            user = self.request.user
            entity_slug = serializer.validated_data.get("entity_slug").lstrip().rstrip()
            entity = Entity.objects.get(slug=entity_slug)
            token = serializer.validated_data.get("paymentToken")
            payment_id = serializer.validated_data.get("paymentID")
            no_of_credits = int(serializer.validated_data.get("credits"))
            total_amount_without_tax_in_USD = float(serializer.validated_data.get("total_amount"))
            total_amount_with_tax_in_USD = float(serializer.validated_data.get("total_amount_with_tax"))
            VAT_USD = serializer.validated_data.get("VAT")
            description = "To buy credits"
            base_url = request.build_absolute_uri()
            request_dict = {

                'user': user,
                'entity': entity,
                'total_amount_with_tax_in_cents': None,
                'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
                'token': token,
                'description': description,
                'transaction_id': payment_id,
                'payment_type': PaymentType.PAYMENT_TYPE_PAYPAL.value

            }

            # payment = ICFPayment()
            # icf_charge_obj = payment.payment_service.make_payment(token, total_amount_with_tax_in_USD, currency,
            #                                                       description)

            icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_PAYPAL).make_payment(token,
                                                                                                                total_amount_with_tax_in_USD,
                                                                                                                currency,
                                                                                                                description)

            if icf_charge_obj.paid:

                # create  new record in AvailableBalance Table and CreditHistory Table to the user for this entity
                try:
                    action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                except CreditAction.DoesNotExist:
                    raise ICFException(_("Invalid action, please check and try again."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                CreditHistory.objects.create(entity=entity, user=user,
                                             available_credits=no_of_credits, action=action)

                try:
                    # entity_balance = AvailableBalance.objects.get(entity=self.entity, user=self.user)
                    entity_balance = AvailableBalance.objects.get(entity=entity)
                    total_balance = entity_balance.available_credits + no_of_credits
                    entity_balance.available_credits = total_balance
                    entity_balance.save(update_fields=['available_credits'])
                except AvailableBalance.DoesNotExist as dne:
                    entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
                                                                     available_credits=no_of_credits)

                CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
                ICF_Payment_Transaction_Manager().update_paypal_trasaction_details(request_dict, icf_charge_obj)

                ICFPaymentLogger().log_paypal_payment_details(request_dict, icf_charge_obj)
                IcfBillGenerator().generate_bill(user, entity, no_of_credits, total_amount_without_tax_in_USD, currency,
                                                 VAT_USD, total_amount_with_tax_in_USD, base_url)

                return Response({"response_message": _("Transaction is successful."),
                                 "amount_paid": icf_charge_obj.resp_amount_in_dollars,
                                 "available_credits": entity_balance.available_credits,
                                 "no_of_credits": no_of_credits
                                 },
                                status=status.HTTP_200_OK)

            else:

                ICF_Payment_Transaction_Manager().update_paypal_trasaction_details(request_dict, icf_charge_obj)

                ICFPaymentLogger().log_paypal_payment_details(request_dict, icf_charge_obj)

                return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist as ce:
            logger.error("transaction failed. reason : {reason}".format(reason=str(ce)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except Entity.DoesNotExist as edn:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(e)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionPlanListApiView(ListAPIView):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        return queryset.filter(product__is_active=True)


class CheckSubscriptionApiView(APIView):
    queryset = Subscription.objects.all()
    permission_classes = (IsAuthenticated, IsEntityAdmin)
    pagination_class = None

    def get(self, request, *args, **kwargs):
        try:
            entity_slug = self.kwargs.get('entity_slug')
            subscription_plan_id = self.kwargs.get('subscription_id')

            entity = Entity.objects.get(slug=entity_slug)
            subscription_plan = SubscriptionPlan.objects.get(id=subscription_plan_id)

            subscription = Subscription.objects.get(entity=entity, subscription_plan=subscription_plan,
                                                    start_date__lte=datetime.today(), end_date__gt=datetime.today())

            if subscription:
                return Response({"is_subscribed": True}, status=status.HTTP_200_OK)
            else:
                return Response({"is_subscribed": False}, status=status.HTTP_200_OK)
        except Entity.DoesNotExist as e:
            return Response({"is_subscribed": False}, status=status.HTTP_400_BAD_REQUEST)
        except Subscription.DoesNotExist as sde:
            return Response({"is_subscribed": False}, status=status.HTTP_400_BAD_REQUEST)


class CheckEntitySubscriptionApiView(RetrieveAPIView):
    queryset = Subscription.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = SubscriptionDetailSerializer
    pagination_class = None

    def get_object(self):
        entity_slug = self.kwargs.get('entity_slug')
        entity = Entity.objects.get(slug=entity_slug)
        return Subscription.objects.filter(entity=entity, start_date__lte=datetime.today(),
                                           end_date__gt=datetime.today()).first()


class ProductListApiView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        product_type = self.kwargs.get('product_type')
        return Product.objects.filter(product_type=product_type, is_active=True)

    # def get_object(self):
    #     try:
    #         product_type = self.kwargs.get('subscription_type')
    #         return Product.objects.get(product_type=product_type, is_active=True)
    #     except Product.DoesNotExist as spdn:
    #         return None
    #
    # def retrieve(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     if instance:
    #         serializer = self.get_serializer(instance)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     else:
    #         return Response({"detail": "Subscription plan not found"}, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionCreateUsingStripeApiView(CreateAPIView):
    serializer_class = SubscriptionCreateUsingStripeSerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            user = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            entity_slug = serializer.validated_data.get('entity_slug')
            # entity_slug = 'tct'
            subscription_plan_id = serializer.validated_data.get('subscription_plan_id')
            # subscription_plan_id = 1
            total_amount_without_tax_in_USD = float(serializer.validated_data.get('total_amount_without_tax_in_USD'))
            # total_amount_without_tax_in_USD = float(550.50)
            currency = serializer.validated_data.get('currency')
            # currency = 'USD'
            token = serializer.validated_data.get('stripeToken')
            # token = request.data.get('stripeToken')
            description = "To buy Subscription"
            base_url = request.build_absolute_uri()

            entity = Entity.objects.get(slug=entity_slug)
            subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
            start_date = datetime.today()
            end_date = start_date + main_datetime_module.timedelta(subscription_plan_obj.duration)
            stripe.api_key = settings.STRIPE_SECRET_KEY

            total_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(entity,
                                                                                                         total_amount_without_tax_in_USD)

            total_amount_with_tax_in_cents = total_amount_dict['total_amount_with_tax_in_cents']
            total_amount_with_tax_in_USD = total_amount_dict['total_amount_with_tax_in_USD']
            VAT_USD = total_amount_dict['VAT_USD']

            request_dict = {

                'user': user,
                'entity': entity,
                'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
                'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
                'token': token,
                'description': description,
                'payment_type': PaymentType.PAYMENT_TYPE_STRIPE.value

            }

            action_subscriptions = ActionSubscriptionPlan.objects.filter(subscription_plan=subscription_plan_obj)

            if action_subscriptions:

                icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_STRIPE).make_payment(
                    token, total_amount_with_tax_in_cents, currency, description)

                subscription_list = []

                if icf_charge_obj.paid:

                    for action_subscription in action_subscriptions:
                        subscription = Subscription.objects.create(user=user, entity=entity, start_date=start_date,
                                                                   end_date=end_date,
                                                                   subscription_plan=subscription_plan_obj,
                                                                   action=action_subscription.action,
                                                                   max_count=action_subscription.max_limit)
                        # subscription.save()
                        subscription_list.append(subscription)

                    ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict, icf_charge_obj)

                    ICFPaymentLogger().log_stripe_payment_details(request_dict, icf_charge_obj)
                    is_offline = False
                    IcfBillGenerator().generate_bill_for_subscription(user, entity, subscription_plan_obj,
                                                                      subscription_list,
                                                                      total_amount_without_tax_in_USD,
                                                                      currency, VAT_USD, total_amount_with_tax_in_USD,
                                                                      base_url, is_offline)

                    return Response({"response_message": _("Transaction is successful."),
                                     "amount_paid": float(icf_charge_obj.resp_amount_in_dollars)
                                     },
                                    status=status.HTTP_200_OK)

                else:

                    ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict, icf_charge_obj)

                    ICFPaymentLogger().log_stripe_payment_details(request_dict, icf_charge_obj)

                    # send an email to PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT  failure payments

                    email_subject = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT).format(entity.name),
                    payment_type = "Credit Card"
                    payment_logger.info(
                        "transaction failed while purchase credits:{entity},\n "
                        "payment_type : {payment_type},\n ".format(entity=entity.name, payment_type=payment_type))

                    email_body = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
                                                                                                           entity.name,
                                                                                                           user.display_name,
                                                                                                           user.email,
                                                                                                           total_amount_with_tax_in_USD)
                    msg = EmailMessage(subject=email_subject,
                                       body=email_body,
                                       to=[app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
                                       )
                    msg.content_subtype = "html"
                    msg.send()

                    return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            else:

                return Response(
                    {"response_message": _("Transaction failed because there is no actions for this subscription."),
                     "amount_paid": None
                     },
                    status=status.HTTP_400_BAD_REQUEST)


        except Entity.DoesNotExist as edn:
            payment_logger.error(
                "Could not buy subscription for this entity. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error(
                "Could not buy subscription for this entity. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy subscription plan for this entity. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy Subscription plan.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.error("Could not buy subscription for this entity. because : {reason}".format(reason=str(e)))
            return Response({"detail": _("Could not buy subscription.")}, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionCreateUsingPaypalApiView(CreateAPIView):
    serializer_class = SubscriptionCreateUsingPaypalSerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = self.request.user
            entity_slug = serializer.validated_data.get('entity_slug')
            subscription_plan_id = serializer.validated_data.get('subscription_plan_id')
            total_amount_with_tax_in_USD = float(serializer.validated_data.get('total_amount_with_tax_in_USD'))
            currency = serializer.validated_data.get('currency')
            description = "To buy Subscription"
            VAT_USD = float(serializer.validated_data.get(
                'VAT'))  # total tax for total amount. the calculation happens in front end
            total_amount_without_tax_in_USD = total_amount_with_tax_in_USD - VAT_USD
            base_url = request.build_absolute_uri()
            entity = Entity.objects.get(slug=entity_slug)
            subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
            start_date = datetime.today()
            end_date = start_date + main_datetime_module.timedelta(subscription_plan_obj.duration)
            token = serializer.validated_data.get("paymentToken")
            payment_id = serializer.validated_data.get("paymentID")

            request_dict = {

                'user': user,
                'entity': entity,
                'total_amount_with_tax_in_cents': None,
                'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
                'token': token,
                'description': description,
                'transaction_id': payment_id,
                'payment_type': PaymentType.PAYMENT_TYPE_PAYPAL.value

            }

            action_subscriptions = ActionSubscriptionPlan.objects.filter(subscription_plan=subscription_plan_obj)

            if action_subscriptions:

                # payment = ICFPayment()
                icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_PAYPAL).make_payment(
                    token, total_amount_with_tax_in_USD, currency, description)

                subscription_list = []

                if icf_charge_obj.paid:

                    # action_subscriptions = ActionSubscriptionPlan.objects.filter(subscription_plan=subscription_plan_obj)

                    for action_subscription in action_subscriptions:
                        subscription = Subscription.objects.create(user=user, entity=entity, start_date=start_date,
                                                                   end_date=end_date,
                                                                   subscription_plan=subscription_plan_obj,
                                                                   action=action_subscription.action,
                                                                   max_count=action_subscription.max_limit)
                        # subscription.save()
                        subscription_list.append(subscription)

                    ICF_Payment_Transaction_Manager().update_paypal_trasaction_details(request_dict, icf_charge_obj)

                    ICFPaymentLogger().log_paypal_payment_details(request_dict, icf_charge_obj)
                    is_offline = False
                    IcfBillGenerator().generate_bill_for_subscription(user, entity, subscription_plan_obj,
                                                                      subscription_list,
                                                                      total_amount_without_tax_in_USD,
                                                                      currency, VAT_USD, total_amount_with_tax_in_USD,
                                                                      base_url, is_offline)

                    return Response({"response_message": _("Transaction is successful."),
                                     "amount_paid": icf_charge_obj.resp_amount_in_dollars
                                     },
                                    status=status.HTTP_200_OK)

                else:

                    ICF_Payment_Transaction_Manager().update_paypal_trasaction_details(request_dict, icf_charge_obj)

                    ICFPaymentLogger().log_paypal_payment_details(request_dict, icf_charge_obj)

                    return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response(
                    {"response_message": _("Transaction failed because there is no actions for this subscription."),
                     "amount_paid": None
                     },
                    status=status.HTTP_400_BAD_REQUEST)

        except Entity.DoesNotExist as edn:
            payment_logger.error(
                "Could not buy subscription for this entity. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error(
                "Could not buy subscription for this entity. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy subscription plan for this entity. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy Subscription plan.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.error("Could not buy subscription for this entity. because : {reason}".format(reason=str(e)))
            return Response({"detail": _("Could not buy subscription.")}, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionCreateOfflineApiView(CreateAPIView):
    permission_classes = (IsAuthenticated, IsEntityAdmin)
    serializer_class = SubscriptionCreateByOfflineSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = self.request.user
            currency = serializer.validated_data.get('currency')
            entity_slug = serializer.validated_data.get('entity_slug')
            subscription_plan_id = serializer.validated_data.get("subscription_plan_id")
            total_amount_without_tax_in_USD = float(serializer.validated_data.get("total_amount_without_tax_in_USD"))
            description = "To buy credits"
            base_url = request.build_absolute_uri()
            entity = Entity.objects.get(slug=entity_slug)
            subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)

            total_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(entity,
                                                                                                         total_amount_without_tax_in_USD)

            # total_amount_with_tax_in_cents = total_amount_dict['total_amount_with_tax_in_cents']
            total_amount_with_tax_in_USD = total_amount_dict['total_amount_with_tax_in_USD']
            VAT_USD = total_amount_dict['VAT_USD']

            start_date = datetime.today()
            end_date = start_date + main_datetime_module.timedelta(subscription_plan_obj.duration)

            action_subscriptions = ActionSubscriptionPlan.objects.filter(subscription_plan=subscription_plan_obj)

            subscription_list = []

            if action_subscriptions:
                for action_subscription in action_subscriptions:
                    subscription = Subscription(user=user, entity=entity, start_date=start_date, end_date=end_date,
                                                subscription_plan=subscription_plan_obj,
                                                action=action_subscription.action,
                                                max_count=action_subscription.max_limit)
                    subscription_list.append(subscription)

                # request_dict = {
                #
                #     'user': user,
                #     'entity': entity,
                #     'total_amount_with_tax_in_cents': None,
                #     'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
                #     'token': None,
                #     'description': description,
                #     'transaction_id': None,
                #     'payment_type': PAYMENT_TYPE.PAYMENT_TYPE_OFFLINE.value
                #
                # }

                # icf_charge_obj = PaymentManager().get_payment_service(PAYMENT_TYPE.PAYMENT_TYPE_OFFLINE).make_payment(total_amount_with_tax_in_USD, currency, description)

                # ICF_Payment_Transaction_Manager().update_offline_payment_trasaction_details(request_dict, icf_charge_obj)
                # ICFPaymentLogger().log_offline_payment_trasaction_details(request_dict, icf_charge_obj)

                is_offline = True
                IcfBillGenerator().generate_bill_for_subscription(user, entity, subscription_plan_obj,
                                                                  subscription_list,
                                                                  total_amount_without_tax_in_USD,
                                                                  currency, VAT_USD, total_amount_with_tax_in_USD,
                                                                  base_url,
                                                                  is_offline)

                return Response({"response_message": _("Invoice generation is successful."),
                                 "amount_to_be_paid": total_amount_with_tax_in_USD
                                 },
                                status=status.HTTP_200_OK)
            else:

                return Response(
                    {"response_message": _("Invoice generation because there is no actions for this subscription."),
                     "amount_paid": None
                     },
                    status=status.HTTP_400_BAD_REQUEST)

        except Entity.DoesNotExist as edn:
            payment_logger.error(
                "Could not buy subscription for this entity. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error(
                "Could not buy subscription for this entity. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy subscription plan for this entity. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy Subscription plan.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.error("Could not buy subscription for this entity. because : {reason}".format(reason=str(e)))
            return Response({"detail": _("Could not buy subscription.")}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseHistoryListApiView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderDetailsSerializer

    def get_queryset(self):
        try:
            entity_slug = self.kwargs.get('entity_slug')
            entity = Entity.objects.get(slug=entity_slug)
            queryset = OrderDetails.objects.filter(entity=entity).order_by('-created')
            return queryset

        except Entity.DoesNotExist as edn:
            return Response({"detail": _("entity does not exists.")}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseHistoryForUserListApiView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderDetailsSerializer

    def get_queryset(self):
        try:
            user = self.request.user
            if user:
                queryset = OrderDetails.objects.filter(user=user).order_by('-created')
                return queryset
            else:
                raise ICFException
        except Exception as e:
            return Response({"detail": _("Something went wrong. reason:{reason}".format(reason=str(e)))},
                            status=status.HTTP_400_BAD_REQUEST)


class GetProductsByProductTypeApiView(ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = Product.objects.all()
            product_type = self.kwargs.get('product_type')
            product_type = product_type.upper()
            pt = ProductType[product_type]
            return queryset.filter(product_type=pt, is_active=True)

        except KeyError as ke:
            return Response({"detail": _("Product Type not found.")}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseProductsUsingStripePaymentApiView(CreateAPIView):
    serializer_class = ProductPurchaseUsingStripeSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            user = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            product_info_list = serializer.validated_data.get('product_info_list')
            # currency is string like 'USD'
            currency = serializer.validated_data.get('currency')
            token = serializer.validated_data.get('stripeToken')
            description = "purchase products using stripe payment"
            base_url = request.build_absolute_uri()
            first_name = serializer.validated_data.get('first_name')
            last_name = serializer.validated_data.get('last_name')
            address_1 = serializer.validated_data.get('address_1')
            address_2 = serializer.validated_data.get('address_2', '')
            billingEmail = serializer.validated_data.get('billingEmail', '')
            entityPhone = serializer.validated_data.get('entityPhone', '')
            zip_code = serializer.validated_data.get('zip_code', '')
            city_id = int(serializer.validated_data.get('city'))
            city_obj = City.objects.get(id=city_id)

            address_obj = Address.objects.create(address_1=address_1, address_2=address_2, city=city_obj,
                                                 address_type=Address.BILLING)
            try:
                billing_address_obj = BillingAddress.objects.get(user=user)
                billing_address_obj.first_name = first_name
                billing_address_obj.last_name = last_name
                billing_address_obj.address = address_obj
                billing_address_obj.billingEmail = billingEmail
                billing_address_obj.entityPhone = entityPhone
                billing_address_obj.zip_code = zip_code
                billing_address_obj.save(update_fields=['first_name', 'last_name', 'address',
                                                        'billingEmail', 'entityPhone', 'zip_code'])
            except BillingAddress.DoesNotExist as badne:
                billing_address_obj = BillingAddress.objects.create(user=user, address=address_obj,
                                                                    first_name=first_name,
                                                                    last_name=last_name, billingEmail=billingEmail,
                                                                    entityPhone=entityPhone, zip_code=zip_code)

            total_products_cost_without_tax_in_USD = 0
            total_products_cost_with_tax_in_USD = 0
            total_products_cost_with_tax_in_cents = 0
            total_VAT_in_USD = 0

            product_info_list = list(filter(None.__ne__, product_info_list))

            entity = None
            for product_info_dict in product_info_list:
                try:
                    product_id = int(product_info_dict.get('product_id'))
                    try:
                        entity_id = product_info_dict.get('entity', None)
                        if entity_id is not None:
                            entity = Entity.objects.get(id=int(entity_id))
                        else:
                            entity = None
                    except KeyError as ke:
                        entity = None
                    if product_id:
                        product = Product.objects.get(id=product_id, is_active=True)
                        # product_cost = product.cost

                        quantity = int(product_info_dict.get('quantity'))
                        if quantity > 0:
                            product_total_cost = (product.cost / product.unit) * quantity

                            product_cost_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(
                                product_total_cost, entity)

                            individual_product_amount_with_tax_in_cents = product_cost_amount_dict[
                                'total_amount_with_tax_in_cents']
                            individual_product_amount_with_tax_in_USD = product_cost_amount_dict[
                                'total_amount_with_tax_in_USD']
                            # individual_product_VAT_USD = product_cost_amount_dict['VAT_USD']

                            total_products_cost_without_tax_in_USD += product_total_cost
                            total_products_cost_with_tax_in_USD += individual_product_amount_with_tax_in_USD
                            total_products_cost_with_tax_in_cents += individual_product_amount_with_tax_in_cents

                            # if product.product_type == Product.CREDIT:
                            #     no_of_credits = product_info_dict.get('quantity')
                        else:
                            payment_logger.info("invalid quantity.")
                            raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

                    else:
                        payment_logger.info("invalid product_id.")
                        raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Product.DoesNotExist as pdne:
                    payment_logger.info("product not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("invalid key  product_id.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Entity.DoesNotExist as edne:
                    payment_logger.info("entity not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

            payment_type = PaymentType.PAYMENT_TYPE_STRIPE

            create_transaction_dict = {
                'user': user,
                'entity': entity,
                'payment_type': payment_type,
                'req_date': datetime.today().date(),
                'req_amount_in_cents': total_products_cost_with_tax_in_cents,
                'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                'req_token': token,
                'req_desc': description,
                'resp_date': None,
                'payment_status': PaymentStatus.FAILURE,
                'resp_error_code': None,
                'resp_error_details': None,
                'resp_amount_in_cents': None,
                'resp_amount_in_dollars': None,
                'resp_transaction_id': None,
                'resp_currency': currency,
                'resp_failure_code': None,
                'resp_failure_message': None

            }
            # create row transaction(order) table to keep track of the products user
            # is purchasing with payment status is failed

            icf_payment_transaction = ICF_Payment_Transaction_Manager().create_stripe_payment_transaction_details(
                create_transaction_dict)

            # loop through the product_info_dict to create instance of the actual product
            # with is_product_active status as invalid
            # all_product_item_dict = []

            all_order_details_list = []
            all_products_list = []

            credits_info_dict_list = []

            for product_info_dict in product_info_list:
                try:
                    # base product's id
                    product_id = product_info_dict.get('product_id')
                    # actual product's id(SubscriptionPlan,EventProduct)
                    product_item_id = product_info_dict.get('product_item_id', None)
                    product = Product.objects.get(id=product_id)
                    # product_name = product.name
                    # product_unit = product.unit
                    # individual_product_cost = product.cost
                    # product_currency_id = product.currency
                    # currency = Currency.objects.get(id=product_currency_id)
                    currency = serializer.validated_data.get('currency')
                    # product_currency = currency
                    # product_is_active = product.is_active
                    # product_parent_product = product.parent_product
                    # product_description = product.description
                    product_type = product.product_type
                    quantity = int(product_info_dict.get('quantity'))
                    entity_id = product_info_dict.get("entity")

                    if product_type == Product.CREDIT:
                        no_of_credits = quantity
                        entity_id = product_info_dict.get("entity")
                        entity = Entity.objects.get(id=entity_id)
                        if no_of_credits <= 0:
                            payment_logger.error("transaction failed. reason : {reason}".format(
                                reason="no of credits should be a non zero positive integer"))
                            return Response({"detail": _("Transaction failed.")},
                                            status=status.HTTP_400_BAD_REQUEST)

                        # create  new record in AvailableBalance Table and CreditHistory Table
                        # to the user for this entity
                        try:
                            action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                        except CreditAction.DoesNotExist:
                            raise ICFException(_("Invalid action, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        credit_history = CreditHistory.objects.create(entity=entity, user=user,
                                                                      available_credits=no_of_credits,
                                                                      action=action, is_active=False)
                        model_name = credit_history.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                        # transaction_id = icf_payment_transaction.id
                        # transaction = ICFPaymentTransaction.objects.get(id=transaction_id)
                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost, content_type=content_type,
                                                                        object_id=credit_history.id
                                                                        )
                        credits_info_dict = {
                            'product': product,
                            'no_of_credits': no_of_credits,
                            'entity': entity
                        }
                        credits_info_dict_list.append(credits_info_dict)

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.SUBSCRIPTION:
                        # product_id = product_id
                        # product_obj = Product.objects.get(id=product_id)
                        # entity_id = product_info_dict.get("entity")
                        entity = Entity.objects.get(id=entity_id)
                        subscription_plan_id = product_item_id
                        subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
                        subscription_plan_start_date = datetime.today().date()
                        subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
                            subscription_plan_obj.duration)

                        action_subscriptions = ActionSubscriptionPlan.objects.filter(
                            subscription_plan=subscription_plan_obj)

                        if action_subscriptions:

                            # subscription_list = []
                            subscription = Subscription.objects.create(user=user, entity=entity,
                                                                       start_date=subscription_plan_start_date,
                                                                       end_date=subscription_plan_end_date,
                                                                       subscription_plan=subscription_plan_obj,
                                                                       is_active=False
                                                                       )

                            for action_subscription in action_subscriptions:
                                subscription_action, created = SubscriptionAction.objects.get_or_create(
                                    subscription=subscription, action=action_subscription.action,
                                    max_count=action_subscription.max_limit)

                                # subscription_action.action_count = subscription_action.action_count + 1
                                # subscription_action.save(update_fields=['action_count'])

                            model_name = subscription.__class__.__name__.lower()

                            content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                            order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                            product=product,
                                                                            entity=entity, user=user, quantity=quantity,
                                                                            price=product.cost,
                                                                            content_type=content_type,
                                                                            object_id=subscription.id
                                                                            )

                            all_order_details_list.append(order_details_obj)
                            all_products_list.append(product)

                    elif product_type == Product.EVENT_PRODUCT:
                        event_product_id = product_item_id
                        event_product_obj = EventProduct.objects.get(id=event_product_id)

                        entityName = product_info_dict.get("entity_name")
                        entityEmail = product_info_dict.get("entity_email")
                        entityPhone = product_info_dict.get("entity_phone")
                        name_of_representative = product_info_dict.get("name_of_representative")
                        address = product_info_dict.get("address")
                        participants = product_info_dict.get("participants")
                        featured_event_slug = product_info_dict.get("featured_event_slug")
                        featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            featured_event_and_product = FeaturedEventAndProduct.objects.get(product=event_product_obj,
                                                                                             featured_event=featured_event)
                        except FeaturedEventAndProduct.DoesNotExist as fepne:
                            payment_logger.info("FeaturedEventAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Featured event don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        expiry_date = EventProduct.objects.get(product=product).expiry_date
                        current_date_time = timezone.now()
                        if expiry_date < current_date_time or featured_event.end_date < datetime.today().date():
                            payment_logger.info(" EventProduct already expired or featured event "
                                                "end date is less than the current date ")
                            raise ICFException(_("Cannot buy products, because of products expiry date."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        participant = Participant.objects.create(user=user, featured_event=featured_event,
                                                                 product=event_product_obj,
                                                                 quantity=quantity, entity_name=entityName,
                                                                 entity_email=entityEmail,
                                                                 phone_no=entityPhone,
                                                                 name_of_representative=name_of_representative,
                                                                 address=address, participants=participants,
                                                                 total_cost=amount,
                                                                 is_payment_successful=False,
                                                                 is_active=False
                                                                 )

                        model_name = participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_featuredevents', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=None, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.CAREER_FAIR_PRODUCT:

                        # # in this condition there will not be product_item_id
                        # # product id itself is a product_item_id
                        # # product id is Product Table (Base Product Id)
                        # # career_fair_product_id = product_id
                        # # product_obj = Product.objects.get(id=career_fair_product_id)

                        # entityName = product_info_dict.get("entity_name")
                        # entityEmail = product_info_dict.get("entity_email")
                        # entityPhone = product_info_dict.get("entity_phone")
                        name_of_representative = product_info_dict.get("name_of_representative")
                        representative_email = product_info_dict.get("representative_email")
                        address = product_info_dict.get("address", None)
                        career_fair_slug = product_info_dict.get("career_fair_slug")
                        career_fair = CareerFair.objects.get(slug=career_fair_slug)
                        product_sub_type = product_info_dict.get("product_sub_type")
                        if entity and product_sub_type==CareerFairProductSubType.ADVERTISEMENT:
                            link="no link"
                            is_ad_already_exist = CareerFairAdvertisement.objects.filter(career_fair=career_fair,
                                                                                         entity=entity)
                            if is_ad_already_exist.count() == 0:
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.MOBILE_IMAGE

                                )
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.DESKTOP_IMAGE

                                )
                                CareerFairUtil.send_add_advertisement_link_buyer(entity, user, link)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            career_fair_and_product = CareerFairAndProduct.objects.get(product=product,
                                                                                       career_fair=career_fair,
                                                                                       product_sub_type=product_sub_type)
                        except CareerFairAndProduct.DoesNotExist as fepne:
                            payment_logger.info("CareerFairAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Career fair don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        # if address is None:
                        #     address = address_1
                        #     if address_2:
                        #         address = address + ","+address_2
                        #     if city_obj:
                        #         address = address + ","+city_obj.city
                        # participant type is nothing but product buyer type
                        career_fair_participant = CareerFairParticipant.objects.create(user=user,
                                                                                       career_fair=career_fair,
                                                                                       participant_type=product.buyer_type,
                                                                                       name_of_representative=name_of_representative,
                                                                                       total_cost=amount,
                                                                                       representative_email=representative_email,
                                                                                       address=address,
                                                                                       entity_id=entity_id,
                                                                                       is_payment_successful=False,
                                                                                       is_active=False)

                        participant_and_product = ParticipantAndProduct.objects.create(
                            participant=career_fair_participant,
                            product=product, quantity=quantity)

                        model_name = career_fair_participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_career_fair', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=product.entity, user=user,
                                                                        quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=career_fair_participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)
                        if entity and product_sub_type==CareerFairProductSubType.TICKET:
                            add_free_subscription_on_participate_as_entity.add_free_subscription(user, entity);




                    else:
                        payment_logger.info("Invalid product with unknown product type")
                        raise ICFException(_("Invalid product, please check and try again."),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                except Product.DoesNotExist as pdne:
                    payment_logger.info("Product not found.")
                    raise ICFException(_("Invalid product, please check and try again."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except EventProduct.DoesNotExist as pdne:
                    payment_logger.info("EventProduct not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("transaction id not found.")
                    raise ICFException(_("transaction id not found."), status_code=status.HTTP_400_BAD_REQUEST)
                except ContentType.DoesNotExist as ctne:
                    payment_logger.info("ContentType object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except SubscriptionPlan.DoesNotExist as spdne:
                    payment_logger.info("SubscriptionPlan object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except FeaturedEvent.DoesNotExist as fedne:
                    payment_logger.info("FeaturedEvent object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFair.DoesNotExist as fedne:
                    payment_logger.info("CareerFair object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFairAndProduct.DoesNotExist as fedne:
                    payment_logger.info("CareerFairAndProduct object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)

            icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_STRIPE). \
                make_payment(token, total_products_cost_with_tax_in_cents, currency, description)

            if icf_charge_obj.paid:
                icf_payment_transaction.payment_status = PaymentStatus.SUCCESS
                icf_payment_transaction.save(update_fields=["payment_status"])

                update_transaction_dict = {
                    'user': user,
                    'entity': entity,
                    'payment_type': payment_type,
                    'req_date': datetime.today().date(),
                    'req_amount_in_cents': total_products_cost_with_tax_in_cents,
                    'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                    'req_token': token,
                    'req_desc': description,
                    'resp_date': icf_charge_obj.resp_date,
                    'payment_status': PaymentStatus.SUCCESS,
                    'resp_error_code': icf_charge_obj.resp_error_code,
                    'resp_error_details': icf_charge_obj.resp_error_details,
                    'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
                    'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
                    'resp_transaction_id': icf_charge_obj.resp_transaction_id,
                    'resp_currency': icf_charge_obj.resp_currency,
                    'resp_failure_code': icf_charge_obj.resp_failure_code,
                    'resp_failure_message': icf_charge_obj.resp_failure_message

                }

                # update remaining fields of transaction table
                icf_payment_transaction = ICF_Payment_Transaction_Manager().update_stripe_payment_transaction_details(
                    icf_payment_transaction, update_transaction_dict)

                for item in all_order_details_list:
                    content_type_obj = ContentType.objects.get_for_id(item.content_type_id)
                    model = content_type_obj.model_class()
                    product_sub_type_obj = model.objects.get(id=item.object_id)
                    product_sub_type_obj.is_active = True
                    product_sub_type_obj.save(update_fields=["is_active"])
                    if model == 'Participant':
                        product_sub_type_obj = model.objects.get(id=item.object_id)
                        product_sub_type_obj.is_payment_successful = True
                        product_sub_type_obj.save(update_fields=["is_payment_successful"])

                    if model == 'CareerFairParticipant':
                        product_sub_type_obj = model.objects.get(id=item.object_id)
                        product_sub_type_obj.is_payment_successful = True
                        product_sub_type_obj.save(update_fields=["is_payment_successful"])

                for credits_info_dict in credits_info_dict_list:
                    try:
                        # generic product's id
                        product = credits_info_dict.get('product')
                        product_type = product.product_type
                        no_of_credits = int(credits_info_dict.get('no_of_credits'))
                        entity = credits_info_dict.get('entity')
                        try:
                            entity_balance = AvailableBalance.objects.get(entity=entity)
                            total_balance = entity_balance.available_credits + no_of_credits
                            entity_balance.available_credits = total_balance
                            entity_balance.save(update_fields=['available_credits'])
                        except AvailableBalance.DoesNotExist as dne:
                            entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
                                                                             available_credits=no_of_credits)
                        CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
                    except Exception as e:
                        payment_logger.error("Something went wrong. reason :{reason}".format(reason=str(e)))
                        raise ICFException(_("Something went wrong. Try again later"),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                ####
                # delete all items in Cart table for the product and user

                for product_obj in all_products_list:
                    try:
                        Cart.objects.filter(product=product_obj, user=user).delete()
                    except Exception as ce:
                        payment_logger.error("Could not delete cart items reason :{reason}".format(reason=str(ce)))
                        raise ICFException(_("Something went wrong. Try again later"),
                                           status_code=status.HTTP_400_BAD_REQUEST)
                ####
                # log transaction details

                ICFPaymentLogger().log_all_product_payment_details(update_transaction_dict)

                ####
                # generate receipt

                order_no = icf_payment_transaction.order_no
                is_offline = False
                is_free_checkout = False
                IcfBillGenerator().generate_receipt_or_invoice_for_products_purchase(order_no, user, currency,
                                                                                     all_order_details_list,
                                                                                     total_products_cost_without_tax_in_USD,
                                                                                     total_products_cost_with_tax_in_USD,
                                                                                     base_url, is_offline,
                                                                                     billing_address_obj,
                                                                                     is_free_checkout)

                return Response({"response_message": _("Transaction is successful."),
                                 "amount_paid": float(icf_charge_obj.resp_amount_in_dollars)},
                                status=status.HTTP_200_OK)

            else:

                # delete all items from order_details table

                for order_detail_obj in all_order_details_list:
                    order_detail_obj.delete()

                # send an email to PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT  failure payments
                PaymentEmailHelper().send_email_on_payment_failure_for_products_purchase(user, all_products_list,
                                                                                         icf_payment_transaction,
                                                                                         total_products_cost_with_tax_in_USD)

                # email_subject = str(app_settings.PURCHASE_PRODUCTS_PAYMENT_FAILURE_SUBJECT)
                # payment_type = "Credit Card"
                # payment_logger.info(
                #         "transaction failed while purchase products with order_no:{order_no}.\n "
                #         "payment_type : {payment_type},\n ".format(order_no=icf_payment_transaction.order_no, payment_type=payment_type))
                #
                # email_body = str(app_settings.PURCHASE_PRODUCTS_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
                #                                                                         user.display_name,
                #                                                                         user.email,
                #                                                                         total_products_cost_with_tax_in_USD)
                # msg = EmailMessage(subject=email_subject,
                #                        body=email_body,
                #                        to=[app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
                #                        )
                # msg.content_subtype = "html"
                # msg.send()

                ####
                # log filed transaction or payment details

                failed_transaction_dict = {
                    'user': user,
                    'payment_type': payment_type,
                    'req_date': datetime.today().date(),
                    'req_amount_in_cents': total_products_cost_with_tax_in_cents,
                    'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                    'req_token': token,
                    'req_desc': description,
                    'resp_date': icf_charge_obj.resp_date,
                    'payment_status': icf_charge_obj.paid,
                    'resp_error_code': icf_charge_obj.resp_error_code,
                    'resp_error_details': icf_charge_obj.resp_error_details,
                    'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
                    'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
                    'resp_transaction_id': icf_charge_obj.resp_transaction_id,
                    'resp_currency': icf_charge_obj.resp_currency,
                    'resp_failure_code': icf_charge_obj.resp_failure_code,
                    'resp_failure_message': icf_charge_obj.resp_failure_message

                }

                # update remaining fields of transaction table
                icf_payment_transaction = ICF_Payment_Transaction_Manager().update_stripe_payment_transaction_details(
                    icf_payment_transaction, failed_transaction_dict)

                ICFPaymentLogger().log_all_product_payment_details(failed_transaction_dict)
                return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as ke:
            payment_logger.error("Could not buy product. because : {reason}".format(reason=str(ke)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except City.DoesNotExist as cdn:
            payment_logger.error("Could not buy product. because : {reason}".format(reason=str(cdn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except Entity.DoesNotExist as edn:
            payment_logger.error("Could not buy product for this entity. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error("Could not buy product for this entity. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy product for this entity. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy products. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
        except EventProduct.DoesNotExist as pdn:
            payment_logger.exception("EventProduct not found.")
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.exception("something went wrong. reason: {reason} ".format(reason=str(e)))
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------------------------------


class PurchaseProductsUsingPaypalPaymentApiView(CreateAPIView):
    serializer_class = ProductPurchaseUsingPaypalSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            user = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            product_info_list = serializer.validated_data.get('product_info_list')
            # currency is string. ex: 'USD'
            currency = serializer.validated_data.get('currency')
            token = serializer.validated_data.get('paymentToken')
            paymentId = serializer.validated_data.get('paymentID')
            description = "purchase products using Paypal payment"
            base_url = request.build_absolute_uri()
            first_name = serializer.validated_data.get('first_name')
            last_name = serializer.validated_data.get('last_name')
            address_1 = serializer.validated_data.get('address_1')
            address_2 = serializer.validated_data.get('address_2', '')
            billingEmail = serializer.validated_data.get('billingEmail', '')
            entityPhone = serializer.validated_data.get('entityPhone', '')
            zip_code = serializer.validated_data.get('zip_code', '')
            city_id = int(serializer.validated_data.get('city'))
            city_obj = City.objects.get(id=city_id)

            address_obj = Address.objects.create(address_1=address_1, address_2=address_2, city=city_obj,
                                                 address_type=Address.BILLING)
            try:
                billing_address_obj = BillingAddress.objects.get(user=user)
                billing_address_obj.first_name = first_name
                billing_address_obj.last_name = last_name
                billing_address_obj.address = address_obj
                billing_address_obj.billingEmail = billingEmail
                billing_address_obj.entityPhone = entityPhone
                billing_address_obj.zip_code = zip_code
                billing_address_obj.save(update_fields=['first_name', 'last_name', 'address',
                                                        'billingEmail', 'entityPhone', 'zip_code'])
            except BillingAddress.DoesNotExist as badne:
                billing_address_obj = BillingAddress.objects.create(user=user, address=address_obj,
                                                                    first_name=first_name,
                                                                    last_name=last_name, billingEmail=billingEmail,
                                                                    entityPhone=entityPhone, zip_code=zip_code)

            total_products_cost_without_tax_in_USD = 0
            total_products_cost_with_tax_in_USD = 0
            total_products_cost_with_tax_in_cents = 0
            total_VAT_in_USD = 0

            product_info_list = list(filter(None.__ne__, product_info_list))

            for product_info_dict in product_info_list:
                try:
                    product_id = int(product_info_dict.get('product_id'))
                    try:
                        entity_id = product_info_dict.get('entity', None)
                        if entity_id is not None:
                            entity = Entity.objects.get(id=int(entity_id))
                        else:
                            entity = None
                    except KeyError as ke:
                        entity = None
                    if product_id:
                        product = Product.objects.get(id=product_id)
                        # product_cost = product.cost

                        quantity = int(product_info_dict.get('quantity'))
                        if quantity > 0:

                            product_total_cost = (product.cost / product.unit) * quantity

                            product_cost_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(
                                product_total_cost, entity)

                            individual_product_amount_with_tax_in_cents = product_cost_amount_dict[
                                'total_amount_with_tax_in_cents']
                            individual_product_amount_with_tax_in_USD = product_cost_amount_dict[
                                'total_amount_with_tax_in_USD']
                            # individual_product_VAT_USD = product_cost_amount_dict['VAT_USD']

                            total_products_cost_without_tax_in_USD += product_total_cost
                            total_products_cost_with_tax_in_USD += individual_product_amount_with_tax_in_USD
                            total_products_cost_with_tax_in_cents += individual_product_amount_with_tax_in_cents
                        else:
                            payment_logger.info("invalid quantity.")
                            raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

                        # if product.product_type == Product.CREDIT:
                        #     no_of_credits = product_info_dict.get('quantity')

                    else:
                        payment_logger.info("invalid product_id.")
                        raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Product.DoesNotExist as pdne:
                    payment_logger.info("product not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("invalid key  product_id.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Entity.DoesNotExist as edne:
                    payment_logger.info("entity not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

            payment_type = PaymentType.PAYMENT_TYPE_PAYPAL

            create_transaction_dict = {
                'user': user,
                'entity': entity,
                'payment_type': payment_type,
                'req_date': datetime.today().date(),
                'req_amount_in_cents': None,
                'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                'req_token': token,
                'req_desc': description,
                'resp_date': None,
                'payment_status': PaymentStatus.FAILURE,
                'resp_error_code': None,
                'resp_error_details': None,
                'resp_amount_in_cents': None,
                'resp_amount_in_dollars': None,
                'resp_transaction_id': paymentId,
                'resp_currency': currency,
                'resp_failure_code': None,
                'resp_failure_message': None

            }
            # create row transaction(order) table to keep track of the products user
            # is purchasing with payment status is failed

            icf_payment_transaction = ICF_Payment_Transaction_Manager().create_paypal_payment_transaction_details(
                create_transaction_dict)

            # loop through the product_info_dict to create instance of the actual product
            # with is_product_active status as invalid
            # all_product_item_dict = []

            all_order_details_list = []
            all_products_list = []

            credits_info_dict_list = []

            for product_info_dict in product_info_list:
                try:
                    # base product's id
                    product_id = product_info_dict.get('product_id')
                    # actual product's id(SubscriptionPlan,EventProduct)
                    product_item_id = product_info_dict.get('product_item_id', None)
                    product = Product.objects.get(id=product_id)
                    # product_name = product.name
                    # product_unit = product.unit
                    # individual_product_cost = product.cost
                    # product_currency_id = product.currency
                    # currency = Currency.objects.get(id=product_currency_id)
                    currency = serializer.validated_data.get('currency')
                    # product_currency = currency
                    # product_is_active = product.is_active
                    # product_parent_product = product.parent_product
                    # product_description = product.description
                    product_type = product.product_type
                    quantity = int(product_info_dict.get('quantity'))
                    entity_id = product_info_dict.get('entity')

                    if product_type == Product.CREDIT:
                        no_of_credits = quantity
                        entity_id = product_info_dict.get("entity")
                        entity = Entity.objects.get(id=entity_id)
                        if no_of_credits <= 0:
                            payment_logger.error("transaction failed. reason : {reason}".format(
                                reason="no of credits should be a non zero positive integer"))
                            return Response({"detail": _("Transaction failed.")},
                                            status=status.HTTP_400_BAD_REQUEST)

                        # create  new record in AvailableBalance Table and CreditHistory Table
                        # to the user for this entity
                        try:
                            action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                        except CreditAction.DoesNotExist:
                            raise ICFException(_("Invalid action, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        credit_history = CreditHistory.objects.create(entity=entity, user=user,
                                                                      available_credits=no_of_credits,
                                                                      action=action, is_active=False)
                        model_name = credit_history.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost, content_type=content_type,
                                                                        object_id=credit_history.id
                                                                        )
                        credits_info_dict = {
                            'product': product,
                            'no_of_credits': no_of_credits,
                            'entity': entity
                        }
                        credits_info_dict_list.append(credits_info_dict)

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.SUBSCRIPTION:
                        # product_id = product_id
                        # product_obj = Product.objects.get(id=product_id)
                        subscription_plan_id = product_item_id
                        entity_id = product_info_dict.get('entity')
                        entity = Entity.objects.get(id=entity_id)
                        subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
                        subscription_plan_start_date = datetime.today().date()
                        subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
                            subscription_plan_obj.duration)

                        action_subscriptions = ActionSubscriptionPlan.objects.filter(
                            subscription_plan=subscription_plan_obj)

                        if action_subscriptions:

                            # subscription_list = []
                            subscription = Subscription.objects.create(user=user, entity=entity,
                                                                       start_date=subscription_plan_start_date,
                                                                       end_date=subscription_plan_end_date,
                                                                       subscription_plan=subscription_plan_obj,
                                                                       is_active=False
                                                                       )

                            for action_subscription in action_subscriptions:
                                subscription_action, created = SubscriptionAction.objects.get_or_create(
                                    subscription=subscription, action=action_subscription.action,
                                    max_count=action_subscription.max_limit)

                                # subscription_action.action_count = subscription_action.action_count + 1
                                # subscription_action.save(update_fields=['action_count'])

                            model_name = subscription.__class__.__name__.lower()

                            content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                            order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                            product=product,
                                                                            entity=entity, user=user, quantity=quantity,
                                                                            price=product.cost,
                                                                            content_type=content_type,
                                                                            object_id=subscription.id
                                                                            )

                            all_order_details_list.append(order_details_obj)
                            all_products_list.append(product)

                    elif product_type == Product.EVENT_PRODUCT:
                        event_product_id = product_item_id
                        event_product_obj = EventProduct.objects.get(id=event_product_id)

                        entityName = product_info_dict.get("entity_name")
                        entityEmail = product_info_dict.get("entity_email")
                        entityPhone = product_info_dict.get("entity_phone")
                        name_of_representative = product_info_dict.get("name_of_representative")
                        address = product_info_dict.get("address")
                        participants = product_info_dict.get("participants")
                        featured_event_slug = product_info_dict.get("featured_event_slug")
                        featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            featured_event_and_product = FeaturedEventAndProduct.objects.get(product=event_product_obj,
                                                                                             featured_event=featured_event)
                        except FeaturedEventAndProduct.DoesNotExist as fepne:
                            payment_logger.info("FeaturedEventAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Featured event don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        expiry_date = EventProduct.objects.get(product=product).expiry_date
                        current_date_time = timezone.now()
                        if expiry_date < current_date_time or featured_event.end_date < datetime.today().date():
                            payment_logger.info(" EventProduct already expired or featured event "
                                                "end date is less than the current date ")
                            raise ICFException(_("Cannot buy products, because of products expiry date."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        participant = Participant.objects.create(user=user, featured_event=featured_event,
                                                                 product=event_product_obj,
                                                                 quantity=quantity, entity_name=entityName,
                                                                 entity_email=entityEmail,
                                                                 phone_no=entityPhone,
                                                                 name_of_representative=name_of_representative,
                                                                 address=address, participants=participants,
                                                                 total_cost=amount,
                                                                 is_payment_successful=False,
                                                                 is_active=False
                                                                 )

                        model_name = participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_featuredevents', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=None, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.CAREER_FAIR_PRODUCT:
                        # in this condition both product id is Product Table (Base Product Id)
                        # career_fair_product_id = product_id
                        # product_obj = Product.objects.get(id=career_fair_product_id)

                        # entityName = product_info_dict.get("entity_name")
                        # entityEmail = product_info_dict.get("entity_email")
                        # entityPhone = product_info_dict.get("entity_phone")
                        name_of_representative = product_info_dict.get("name_of_representative")
                        representative_email = product_info_dict.get("representative_email")
                        address = product_info_dict.get("address", None)
                        # participant_type = product_info_dict.get("participant_type")
                        career_fair_slug = product_info_dict.get("career_fair_slug")
                        career_fair = CareerFair.objects.get(slug=career_fair_slug)
                        product_sub_type = product_info_dict.get("product_sub_type")
                        if entity and product_sub_type==CareerFairProductSubType.ADVERTISEMENT:
                            link="no link"
                            # send email here
                            # when product subtype is an advertisement create 2 entry for desktop and mobile adds
                            is_ad_already_exist = CareerFairAdvertisement.objects.filter(career_fair=career_fair,
                                                                                         entity=entity)
                            if is_ad_already_exist.count() == 0:
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.MOBILE_IMAGE

                                )
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.DESKTOP_IMAGE

                                )
                                CareerFairUtil.send_add_advertisement_link_buyer(entity, user, link)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            career_fair_and_product = CareerFairAndProduct.objects.get(product=product,
                                                                                       career_fair=career_fair,
                                                                                       product_sub_type=product_sub_type)
                        except CareerFairAndProduct.DoesNotExist as fepne:
                            payment_logger.info("CareerFairAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Career fair don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        # if address is None:
                        #     address = address_1
                        #     if address_2:
                        #         address = address + ","+address_2
                        #     if city_obj:
                        #         address = address + ","+city_obj.city

                        # here participant type is nothing but product buyer type
                        career_fair_participant = CareerFairParticipant.objects.create(user=user,
                                                                                       career_fair=career_fair,
                                                                                       participant_type=product.buyer_type,
                                                                                       name_of_representative=name_of_representative,
                                                                                       total_cost=amount,
                                                                                       representative_email=representative_email,
                                                                                       address=address,
                                                                                       entity_id=entity_id,
                                                                                       is_payment_successful=False,
                                                                                       is_active=False)

                        participant_and_product = ParticipantAndProduct.objects.create(
                            participant=career_fair_participant,
                            product=product, quantity=quantity)

                        model_name = career_fair_participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_career_fair', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=career_fair_participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)
                        if entity and product_sub_type==CareerFairProductSubType.TICKET:
                            add_free_subscription_on_participate_as_entity.add_free_subscription(user, entity);


                    else:
                        payment_logger.info("Invalid product with unknown product type")
                        raise ICFException(_("Invalid product, please check and try again."),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                except Product.DoesNotExist as pdne:
                    payment_logger.info("Product not found.")
                    raise ICFException(_("Invalid product, please check and try again."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except EventProduct.DoesNotExist as pdne:
                    payment_logger.info("EventProduct not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("transaction id not found.")
                    raise ICFException(_("transaction id not found."), status_code=status.HTTP_400_BAD_REQUEST)
                except ContentType.DoesNotExist as ctne:
                    payment_logger.info("ContentType object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except SubscriptionPlan.DoesNotExist as spdne:
                    payment_logger.info("SubscriptionPlan object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except FeaturedEvent.DoesNotExist as fedne:
                    payment_logger.info("FeaturedEvent object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFair.DoesNotExist as fedne:
                    payment_logger.info("CareerFair object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFairAndProduct.DoesNotExist as fedne:
                    payment_logger.info("CareerFairAndProduct object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)

            icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_PAYPAL). \
                make_payment(token, total_products_cost_with_tax_in_USD, currency, description)

            if icf_charge_obj.paid:
                icf_payment_transaction.payment_status = PaymentStatus.SUCCESS
                icf_payment_transaction.save(update_fields=["payment_status"])

                update_transaction_dict = {
                    'user': user,
                    'entity': entity,
                    'payment_type': payment_type,
                    'req_date': datetime.today().date(),
                    'req_amount_in_cents': None,
                    'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                    'req_token': token,
                    'req_desc': description,
                    'resp_date': icf_charge_obj.resp_date,
                    'payment_status': PaymentStatus.SUCCESS,
                    'resp_error_code': icf_charge_obj.resp_error_code,
                    'resp_error_details': icf_charge_obj.resp_error_details,
                    'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
                    'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
                    'resp_transaction_id': icf_charge_obj.resp_transaction_id,
                    'resp_currency': icf_charge_obj.resp_currency,
                    'resp_failure_code': icf_charge_obj.resp_failure_code,
                    'resp_failure_message': icf_charge_obj.resp_failure_message

                }

                # update remaining fields of transaction table
                icf_payment_transaction = ICF_Payment_Transaction_Manager().update_paypal_payment_transaction_details(
                    icf_payment_transaction, update_transaction_dict)

                for item in all_order_details_list:
                    content_type_obj = ContentType.objects.get_for_id(item.content_type_id)
                    model = content_type_obj.model_class()
                    product_sub_type_obj = model.objects.get(id=item.object_id)
                    product_sub_type_obj.is_active = True
                    product_sub_type_obj.save(update_fields=["is_active"])
                    if model == 'Participant':
                        product_sub_type_obj = model.objects.get(id=item.object_id)
                        product_sub_type_obj.is_payment_successful = True
                        product_sub_type_obj.save(update_fields=["is_payment_successful"])
                    if model == 'CareerFairParticipant':
                        product_sub_type_obj = model.objects.get(id=item.object_id)
                        product_sub_type_obj.is_payment_successful = True
                        product_sub_type_obj.save(update_fields=["is_payment_successful"])

                for credits_info_dict in credits_info_dict_list:
                    try:
                        # generic product's id
                        product = credits_info_dict.get('product')
                        product_type = product.product_type
                        no_of_credits = int(credits_info_dict.get('no_of_credits'))
                        entity = credits_info_dict.get('entity')
                        try:
                            entity_balance = AvailableBalance.objects.get(entity=entity)
                            total_balance = entity_balance.available_credits + no_of_credits
                            entity_balance.available_credits = total_balance
                            entity_balance.save(update_fields=['available_credits'])
                        except AvailableBalance.DoesNotExist as dne:
                            entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
                                                                             available_credits=no_of_credits)
                        CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
                    except Exception as e:
                        payment_logger.error("Something went wrong. reason :{reason}".format(reason=str(e)))
                        raise ICFException(_("Something went wrong. Try again later"),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                ####
                # delete all items in Cart table for the product and user

                for product_obj in all_products_list:
                    try:
                        Cart.objects.filter(product=product_obj, user=user).delete()
                    except Exception as ce:
                        payment_logger.error("Could not delete cart items reason :{reason}".format(reason=str(ce)))
                        raise ICFException(_("Something went wrong. Try again later"),
                                           status_code=status.HTTP_400_BAD_REQUEST)
                ####
                # log transaction details

                ICFPaymentLogger().log_all_product_payment_details(update_transaction_dict)

                ####
                # generate receipt

                order_no = icf_payment_transaction.order_no
                is_offline = False
                is_free_checkout = False
                IcfBillGenerator().generate_receipt_or_invoice_for_products_purchase(order_no, user, currency,
                                                                                     all_order_details_list,
                                                                                     total_products_cost_without_tax_in_USD,
                                                                                     total_products_cost_with_tax_in_USD,
                                                                                     base_url, is_offline,
                                                                                     billing_address_obj,
                                                                                     is_free_checkout)

                return Response({"response_message": _("Transaction is successful."),
                                 "amount_paid": float(icf_charge_obj.resp_amount_in_dollars)
                                 },
                                status=status.HTTP_200_OK)

            else:

                # delete all items from order_details table

                for order_detail_obj in all_order_details_list:
                    order_detail_obj.delete()

                # send an email to PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT  failure payments

                PaymentEmailHelper().email_failure_payment_details(user, all_products_list,
                                                                   total_products_cost_with_tax_in_USD)

                #
                # email_subject = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT).format(entity.name),
                # payment_type = "Credit Card"
                # payment_logger.info(
                #         "transaction failed while purchase credits:{entity},\n "
                #         "payment_type : {payment_type},\n ".format(entity=entity.name, payment_type=payment_type))
                #
                # email_body = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
                #                                                                                            entity.name,
                #                                                                                            user.display_name,
                #                                                                                            user.email,
                #                                                                                            total_product_amount_with_tax_in_USD)
                # msg = EmailMessage(subject=email_subject,
                #                        body=email_body,
                #                        to=[app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
                #                        )
                # msg.content_subtype = "html"
                # msg.send()

                ####
                # log filed transaction or payment details

                failed_transaction_dict = {
                    'user': user,
                    'entity': entity,
                    'payment_type': payment_type,
                    'req_date': datetime.today().date(),
                    'req_amount_in_cents': None,
                    'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                    'req_token': token,
                    'req_desc': description,
                    'resp_date': icf_charge_obj.resp_date,
                    'payment_status': icf_charge_obj.paid,
                    'resp_error_code': icf_charge_obj.resp_error_code,
                    'resp_error_details': icf_charge_obj.resp_error_details,
                    'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
                    'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
                    'resp_transaction_id': paymentId,
                    'resp_currency': icf_charge_obj.resp_currency,
                    'resp_failure_code': icf_charge_obj.resp_failure_code,
                    'resp_failure_message': icf_charge_obj.resp_failure_message

                }

                ICFPaymentLogger().log_all_product_payment_details(failed_transaction_dict)

                return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as ke:
            payment_logger.error("Could not buy product. because : {reason}".format(reason=str(ke)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except City.DoesNotExist as cdn:
            payment_logger.error("Could not buy product. because : {reason}".format(reason=str(cdn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except Entity.DoesNotExist as edn:
            payment_logger.error("Could not buy product for this entity. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error("Could not buy product for this entity. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy product for this entity. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as spdn:
            payment_logger.error(
                "Could not buy products. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
        except EventProduct.DoesNotExist as pdn:
            payment_logger.exception("EventProduct not found.")
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.exception("something went wrong. reason: {reason} ".format(reason=str(e)))
            return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------------
# ***********************************************************************************
# -----------------------------------------------------------------------------------

class GenerateInvoiceForProductsApiView(CreateAPIView):
    serializer_class = InvoiceForProductsSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            user = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            product_info_list = serializer.validated_data.get('product_info_list')
            # currency is string. ex: 'USD'
            currency = serializer.validated_data.get('currency')
            # token = serializer.validated_data.get('paymentToken')
            # paymentId = serializer.validated_data.get('paymentID')
            description = "Invoice for products"
            base_url = request.build_absolute_uri()
            first_name = serializer.validated_data.get('first_name')
            last_name = serializer.validated_data.get('last_name')
            address_1 = serializer.validated_data.get('address_1')
            address_2 = serializer.validated_data.get('address_2', '')
            billingEmail = serializer.validated_data.get('billingEmail', '')
            entityPhone = serializer.validated_data.get('entityPhone', '')
            zip_code = serializer.validated_data.get('zip_code', '')
            city_id = int(serializer.validated_data.get('city'))
            city_obj = City.objects.get(id=city_id)

            address_obj = Address.objects.create(address_1=address_1, address_2=address_2, city=city_obj,
                                                 address_type=Address.BILLING)
            try:
                billing_address_obj = BillingAddress.objects.get(user=user)
                billing_address_obj.first_name = first_name
                billing_address_obj.last_name = last_name
                billing_address_obj.address = address_obj
                billing_address_obj.billingEmail = billingEmail
                billing_address_obj.entityPhone = entityPhone
                billing_address_obj.zip_code = zip_code
                billing_address_obj.save(update_fields=['first_name', 'last_name', 'address',
                                                        'billingEmail', 'entityPhone', 'zip_code'])
            except BillingAddress.DoesNotExist as badne:
                billing_address_obj = BillingAddress.objects.create(user=user, address=address_obj,
                                                                    first_name=first_name,
                                                                    last_name=last_name, billingEmail=billingEmail,
                                                                    entityPhone=entityPhone, zip_code=zip_code)

            total_products_cost_without_tax_in_USD = 0
            total_products_cost_with_tax_in_USD = 0
            total_products_cost_with_tax_in_cents = 0
            total_VAT_in_USD = 0

            product_info_list = list(filter(None.__ne__, product_info_list))

            for product_info_dict in product_info_list:
                try:
                    product_id = int(product_info_dict.get('product_id'))
                    try:
                        entity_id = product_info_dict.get('entity', None)
                        if entity_id is not None:
                            entity = Entity.objects.get(id=int(entity_id))
                        else:
                            entity = None
                    except KeyError as ke:
                        entity = None
                    if product_id:
                        product = Product.objects.get(id=product_id, is_active=True)
                        # product_cost = product.cost

                        quantity = int(product_info_dict.get('quantity'))
                        if quantity > 0:

                            product_total_cost = (product.cost / product.unit) * quantity

                            product_cost_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(
                                product_total_cost, entity)

                            individual_product_amount_with_tax_in_cents = product_cost_amount_dict[
                                'total_amount_with_tax_in_cents']
                            individual_product_amount_with_tax_in_USD = product_cost_amount_dict[
                                'total_amount_with_tax_in_USD']
                            # individual_product_VAT_USD = product_cost_amount_dict['VAT_USD']

                            total_products_cost_without_tax_in_USD += product_total_cost
                            total_products_cost_with_tax_in_USD += individual_product_amount_with_tax_in_USD
                            total_products_cost_with_tax_in_cents += individual_product_amount_with_tax_in_cents
                        else:
                            payment_logger.info("invalid quantity.")
                            raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

                        # if product.product_type == Product.CREDIT:
                        #     no_of_credits = product_info_dict.get('quantity')

                    else:
                        payment_logger.info("invalid product_id.")
                        raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Product.DoesNotExist as pdne:
                    payment_logger.info("product not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("invalid key  product_id.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Entity.DoesNotExist as edne:
                    payment_logger.info("entity not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

            payment_type = PaymentType.PAYMENT_TYPE_OFFLINE

            create_transaction_dict = {
                'user': user,
                'entity': entity,
                'payment_type': payment_type,
                'req_date': datetime.today().date(),
                'req_amount_in_cents': None,
                'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                'req_token': None,
                'req_desc': description,
                'resp_date': None,
                'payment_status': PaymentStatus.PENDING,
                'resp_error_code': None,
                'resp_error_details': None,
                'resp_amount_in_cents': None,
                'resp_amount_in_dollars': None,
                'resp_transaction_id': None,
                'resp_currency': currency,
                'resp_failure_code': None,
                'resp_failure_message': None

            }
            # create row transaction(order) table to keep track of the products user
            # is purchasing with payment status is failed

            icf_payment_transaction = ICF_Payment_Transaction_Manager(). \
                create_offline_payment_transaction_details(create_transaction_dict)

            # loop through the product_info_dict to create instance of the actual product
            # with is_product_active status as invalid
            # all_product_item_dict = []

            all_order_details_list = []
            all_products_list = []

            credits_info_dict_list = []

            for product_info_dict in product_info_list:
                try:
                    # base product's id
                    product_id = product_info_dict.get('product_id')
                    # actual product's id(SubscriptionPlan,EventProduct)
                    product_item_id = product_info_dict.get('product_item_id', None)
                    product = Product.objects.get(id=product_id, is_active=True)
                    # product_name = product.name
                    # product_unit = product.unit
                    # individual_product_cost = product.cost
                    # product_currency_id = product.currency
                    # currency = Currency.objects.get(id=product_currency_id)
                    currency = serializer.validated_data.get('currency')
                    # product_currency = currency
                    # product_is_active = product.is_active
                    # product_parent_product = product.parent_product
                    # product_description = product.description
                    product_type = product.product_type
                    quantity = int(product_info_dict.get('quantity'))

                    if product_type == Product.CREDIT:
                        no_of_credits = quantity
                        entity_id = product_info_dict.get("entity")
                        entity = Entity.objects.get(id=entity_id)
                        if no_of_credits <= 0:
                            payment_logger.error("transaction failed. reason : {reason}".format(
                                reason="No of credits should be a non zero positive integer."))
                            return Response({"detail": _(
                                "Transaction failed. No of credits should be a non zero positive integer.")},
                                status=status.HTTP_400_BAD_REQUEST)

                        # create  new record in AvailableBalance Table and CreditHistory Table
                        # to the user for this entity
                        try:
                            action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                        except CreditAction.DoesNotExist:
                            raise ICFException(_("Invalid action, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        credit_history = CreditHistory.objects.create(entity=entity, user=user,
                                                                      available_credits=no_of_credits,
                                                                      action=action, is_active=False)
                        model_name = credit_history.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost, content_type=content_type,
                                                                        object_id=credit_history.id
                                                                        )
                        credits_info_dict = {
                            'product': product,
                            'no_of_credits': no_of_credits,
                            'entity': entity
                        }
                        credits_info_dict_list.append(credits_info_dict)

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.SUBSCRIPTION:
                        # product_id = product_id
                        # product_obj = Product.objects.get(id=product_id)
                        subscription_plan_id = product_item_id
                        entity_id = product_info_dict.get('entity')
                        entity = Entity.objects.get(id=entity_id)
                        subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
                        subscription_plan_start_date = datetime.today().date()
                        subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
                            subscription_plan_obj.duration)

                        action_subscriptions = ActionSubscriptionPlan.objects.filter(
                            subscription_plan=subscription_plan_obj)

                        if action_subscriptions:

                            # subscription_list = []
                            subscription = Subscription.objects.create(user=user, entity=entity,
                                                                       start_date=subscription_plan_start_date,
                                                                       end_date=subscription_plan_end_date,
                                                                       subscription_plan=subscription_plan_obj,
                                                                       is_active=False
                                                                       )

                            for action_subscription in action_subscriptions:
                                subscription_action, created = SubscriptionAction.objects.get_or_create(
                                    subscription=subscription, action=action_subscription.action,
                                    max_count=action_subscription.max_limit)

                                # subscription_action.action_count = subscription_action.action_count + 1
                                # subscription_action.save(update_fields=['action_count'])

                            model_name = subscription.__class__.__name__.lower()

                            content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                            order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                            product=product,
                                                                            entity=entity, user=user, quantity=quantity,
                                                                            price=product.cost,
                                                                            content_type=content_type,
                                                                            object_id=subscription.id
                                                                            )

                            all_order_details_list.append(order_details_obj)
                            all_products_list.append(product)

                    elif product_type == Product.EVENT_PRODUCT:
                        event_product_id = product_item_id
                        event_product_obj = EventProduct.objects.get(id=event_product_id)

                        entityName = product_info_dict.get("entity_name", None)
                        entityEmail = product_info_dict.get("entity_email", None)
                        entityPhone = product_info_dict.get("entity_phone", None)
                        name_of_representative = product_info_dict.get("name_of_representative", None)
                        address = product_info_dict.get("address", None)
                        participants = product_info_dict.get("participants", None)
                        featured_event_slug = product_info_dict.get("featured_event_slug")
                        featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            featured_event_and_product = FeaturedEventAndProduct.objects.get(product=event_product_obj,
                                                                                             featured_event=featured_event)
                        except FeaturedEventAndProduct.DoesNotExist as fepne:
                            payment_logger.info("FeaturedEventAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Featured event don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        expiry_date = EventProduct.objects.get(product=product).expiry_date
                        current_date_time = timezone.now()
                        if expiry_date < current_date_time or featured_event.end_date < datetime.today().date():
                            payment_logger.info(" EventProduct already expired or featured event "
                                                "end date is less than the current date ")
                            raise ICFException(_("Cannot buy products, because of products expiry date."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        participant = Participant.objects.create(user=user, featured_event=featured_event,
                                                                 product=event_product_obj,
                                                                 quantity=quantity, entity_name=entityName,
                                                                 entity_email=entityEmail,
                                                                 phone_no=entityPhone,
                                                                 name_of_representative=name_of_representative,
                                                                 address=address, participants=participants,
                                                                 total_cost=amount,
                                                                 is_payment_successful=False,
                                                                 is_active=False
                                                                 )

                        model_name = participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_featuredevents', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=None, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.CAREER_FAIR_PRODUCT:

                        # in this condition both product id is Product Table (Base Product Id)
                        # career_fair_product_id = product_id
                        # product_obj = Product.objects.get(id=career_fair_product_id)

                        # entityName = product_info_dict.get("entity_name")
                        # entityEmail = product_info_dict.get("entity_email")
                        # entityPhone = product_info_dict.get("entity_phone")
                        name_of_representative = product_info_dict.get("name_of_representative")
                        representative_email = product_info_dict.get("representative_email")
                        address = product_info_dict.get("address", None)
                        # participant_type = product_info_dict.get("participant_type")
                        career_fair_slug = product_info_dict.get("career_fair_slug")
                        career_fair = CareerFair.objects.get(slug=career_fair_slug)
                        product_sub_type = product_info_dict.get("product_sub_type")
                        if entity and product_sub_type==CareerFairProductSubType.ADVERTISEMENT:
                            link="no link"
                            # send email here
                            # when product subtype is an advertisement create 2 entry for desktop and mobile adds
                            is_ad_already_exist=CareerFairAdvertisement.objects.filter(career_fair=career_fair,entity=entity)
                            if is_ad_already_exist.count()==0:
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.MOBILE_IMAGE

                                )
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.DESKTOP_IMAGE

                                )
                                CareerFairUtil.send_add_advertisement_link_buyer(entity, user, link)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            # Recover the careerFair - Product model
                            career_fair_and_product = CareerFairAndProduct.objects.get(product=product,
                                                                                       career_fair=career_fair,
                                                                                       product_sub_type=product_sub_type)
                        except CareerFairAndProduct.DoesNotExist as fepne:
                            payment_logger.info("CareerFairAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Career fair don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        # if address is None:
                        #     address = address_1
                        #     if address_2:
                        #         address = address + ","+address_2
                        #     if city_obj:
                        #         address = address + ","+city_obj.city
                        #
                        if (entity):
                            # If everything is ok then add the participant
                            career_fair_participant = CareerFairParticipant.objects.create(user=user,
                                                                                           career_fair=career_fair,
                                                                                           participant_type=product.buyer_type,
                                                                                           name_of_representative=name_of_representative,
                                                                                           total_cost=amount,
                                                                                           representative_email=representative_email,
                                                                                           address=address,
                                                                                           entity_id=entity.id,
                                                                                           is_payment_successful=False,
                                                                                           is_active=False)
                        else:
                            career_fair_participant = CareerFairParticipant.objects.create(user=user,
                                                                                           career_fair=career_fair,
                                                                                           participant_type=product.buyer_type,
                                                                                           name_of_representative=name_of_representative,
                                                                                           total_cost=amount,
                                                                                           representative_email=representative_email,
                                                                                           address=address,
                                                                                           is_payment_successful=False,
                                                                                           is_active=False)

                        participant_and_product = ParticipantAndProduct.objects.create(
                            participant=career_fair_participant,
                            product=product, quantity=quantity)

                        model_name = career_fair_participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_career_fair', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=career_fair_participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)
                        if entity and product_sub_type==CareerFairProductSubType.TICKET:
                            add_free_subscription_on_participate_as_entity.add_free_subscription(user, entity);

                    else:
                        payment_logger.info("Invalid product with unknown product type")
                        raise ICFException(_("Invalid product, please check and try again."),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                except Product.DoesNotExist as pdne:
                    payment_logger.info("Could not generate invoice because Product not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except EventProduct.DoesNotExist as pdne:
                    payment_logger.info("Could not generate invoice because EventProduct not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("Could not generate invoice because transaction id not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except ContentType.DoesNotExist as ctne:
                    payment_logger.info("Could not generate invoice because ContentType object not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except SubscriptionPlan.DoesNotExist as spdne:
                    payment_logger.info("Could not generate invoice because SubscriptionPlan object not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except FeaturedEvent.DoesNotExist as fedne:
                    payment_logger.info("Could not generate invoice because FeaturedEvent object not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFair.DoesNotExist as fedne:
                    payment_logger.info("CareerFair object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFairAndProduct.DoesNotExist as fedne:
                    payment_logger.info("CareerFairAndProduct object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)

            # icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_PAYPAL).\
            #     make_payment(token, total_products_cost_with_tax_in_USD, currency, description)

            # if icf_charge_obj.paid:
            #     icf_payment_transaction.payment_status = PaymentStatus.SUCCESS
            #     icf_payment_transaction.save(update_fields=["payment_status"])

            # update_transaction_dict = {
            #     'user': user,
            #     'entity': None,
            #     'payment_type': payment_type,
            #     'req_date': datetime.today().date(),
            #     'req_amount_in_cents': None,
            #     'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
            #     'req_token': token,
            #     'req_desc': description,
            #     'resp_date': icf_charge_obj.resp_date,
            #     'payment_status': icf_charge_obj.paid,
            #     'resp_error_code': icf_charge_obj.resp_error_code,
            #     'resp_error_details': icf_charge_obj.resp_error_details,
            #     'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
            #     'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
            #     'resp_transaction_id': icf_charge_obj.resp_transaction_id,
            #     'resp_currency': icf_charge_obj.resp_currency,
            #     'resp_failure_code': icf_charge_obj.resp_failure_code,
            #     'resp_failure_message': icf_charge_obj.resp_failure_message
            #
            # }

            # update remaining fields of transaction table
            # icf_payment_transaction = ICF_Payment_Transaction_Manager().update_paypal_payment_transaction_details(icf_payment_transaction, update_transaction_dict)

            # for item in all_order_details_list:
            #     content_type_obj = ContentType.objects.get_for_id(item.content_type_id)
            #     model = content_type_obj.model_class()
            #     product_sub_type_obj = model.objects.get(id=item.object_id)
            #     product_sub_type_obj.is_active = True
            #     product_sub_type_obj.save(update_fields=["is_active"])
            #     if model == 'Participant':
            #         product_sub_type_obj = model.objects.get(id=item.object_id)
            #         product_sub_type_obj.is_payment_successful = True
            #         product_sub_type_obj.save(update_fields=["is_payment_successful"])

            # for credits_info_dict in credits_info_dict_list:
            #     try:
            #         # generic product's id
            #         product = credits_info_dict.get('product')
            #         product_type = product.product_type
            #         no_of_credits = int(credits_info_dict.get('no_of_credits'))
            #         entity = credits_info_dict.get('entity')
            #         try:
            #             entity_balance = AvailableBalance.objects.get(entity=entity)
            #             total_balance = entity_balance.available_credits + no_of_credits
            #             entity_balance.available_credits = total_balance
            #             entity_balance.save(update_fields=['available_credits'])
            #         except AvailableBalance.DoesNotExist as dne:
            #             entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
            #                                                              available_credits=no_of_credits)
            #         CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
            #     except Exception as e:
            #         payment_logger.error("Something went wrong. reason :{reason}".format(reason=str(e)))
            #         raise ICFException(_("Something went wrong. Try again later"),
            #                            status_code=status.HTTP_400_BAD_REQUEST)

            ####
            # delete all items in Cart table for the product and user

            for product_obj in all_products_list:
                try:
                    Cart.objects.filter(product=product_obj, user=user).delete()
                except Exception as ce:
                    payment_logger.error("Could not delete cart items reason :{reason}".format(reason=str(ce)))
                    raise ICFException(_("Something went wrong. Try again later"),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                ####
                # log transaction details

            ICFPaymentLogger().log_all_product_payment_details(create_transaction_dict)

            ####
            # generate receipt

            order_no = icf_payment_transaction.order_no
            is_offline = True
            is_free_checkout = False
            IcfBillGenerator().generate_receipt_or_invoice_for_products_purchase(order_no, user, currency,
                                                                                 all_order_details_list,
                                                                                 total_products_cost_without_tax_in_USD,
                                                                                 total_products_cost_with_tax_in_USD,
                                                                                 base_url, is_offline,
                                                                                 billing_address_obj, is_free_checkout)

            return Response({"response_message": _("Invoice generated successfully."),
                             "amount_to_be_paid": float(total_products_cost_with_tax_in_USD)
                             },
                            status=status.HTTP_200_OK)

            # else:
            #
            #     # delete all items from order_details table
            #
            #     for order_detail_obj in all_order_details_list:
            #         order_detail_obj.delete()
            #
            #
            #     # # send an email to PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT  failure payments
            #     #
            #     # email_subject = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT).format(entity.name),
            #     # payment_type = "Credit Card"
            #     # payment_logger.info(
            #     #         "transaction failed while purchase credits:{entity},\n "
            #     #         "payment_type : {payment_type},\n ".format(entity=entity.name, payment_type=payment_type))
            #     #
            #     # email_body = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
            #     #                                                                                            entity.name,
            #     #                                                                                            user.display_name,
            #     #                                                                                            user.email,
            #     #                                                                                            total_product_amount_with_tax_in_USD)
            #     # msg = EmailMessage(subject=email_subject,
            #     #                        body=email_body,
            #     #                        to=[app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
            #     #                        )
            #     # msg.content_subtype = "html"
            #     # msg.send()
            #
            #     ####
            #     # log filed transaction or payment details
            #
            #     failed_transaction_dict = {
            #         'user': user,
            #         'entity': None,
            #         'payment_type': payment_type,
            #         'req_date': datetime.today().date(),
            #         'req_amount_in_cents': None,
            #         'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
            #         'req_token': token,
            #         'req_desc': description,
            #         'resp_date': icf_charge_obj.resp_date,
            #         'payment_status': icf_charge_obj.paid,
            #         'resp_error_code': icf_charge_obj.resp_error_code,
            #         'resp_error_details': icf_charge_obj.resp_error_details,
            #         'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
            #         'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
            #         'resp_transaction_id': icf_charge_obj.resp_transaction_id,
            #         'resp_currency': icf_charge_obj.resp_currency,
            #         'resp_failure_code': icf_charge_obj.resp_failure_code,
            #         'resp_failure_message': icf_charge_obj.resp_failure_message
            #
            #     }
            #
            #     ICFPaymentLogger().log_all_product_payment_details(failed_transaction_dict)
            #
            #     return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as ke:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(ke)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except City.DoesNotExist as cdn:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(cdn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except Entity.DoesNotExist as edn:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not generate invoice. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as spdn:
            payment_logger.error(
                "Could not generate invoice. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except EventProduct.DoesNotExist as pdn:
            payment_logger.exception("Could not generate invoice.")
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.exception("Could not generate invoice. reason: {reason} ".format(reason=str(e)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------------------------------
# ************************************************************************************************
# ----------------------------------------------------------------------------------

class GenerateInvoiceForProductsByFreeCheckoutApiView(CreateAPIView):
    serializer_class = InvoiceForProductsSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            user = self.request.user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            product_info_list = serializer.validated_data.get('product_info_list')
            # currency is string. ex: 'USD'
            currency = serializer.validated_data.get('currency')
            # token = serializer.validated_data.get('paymentToken')
            # paymentId = serializer.validated_data.get('paymentID')
            description = "Invoice for products"
            base_url = request.build_absolute_uri()
            first_name = serializer.validated_data.get('first_name')
            last_name = serializer.validated_data.get('last_name')
            address_1 = serializer.validated_data.get('address_1')
            address_2 = serializer.validated_data.get('address_2', '')
            billingEmail = serializer.validated_data.get('billingEmail', '')
            entityPhone = serializer.validated_data.get('entityPhone', '')
            zip_code = serializer.validated_data.get('zip_code', '')
            city_id = int(serializer.validated_data.get('city'))
            city_obj = City.objects.get(id=city_id)

            address_obj = Address.objects.create(address_1=address_1, address_2=address_2, city=city_obj,
                                                 address_type=Address.BILLING)
            try:
                billing_address_obj = BillingAddress.objects.get(user=user)
                billing_address_obj.first_name = first_name
                billing_address_obj.last_name = last_name
                billing_address_obj.address = address_obj
                billing_address_obj.billingEmail = billingEmail
                billing_address_obj.entityPhone = entityPhone
                billing_address_obj.zip_code = zip_code
                billing_address_obj.save(update_fields=['first_name', 'last_name', 'address',
                                                        'billingEmail', 'entityPhone', 'zip_code'])
            except BillingAddress.DoesNotExist as badne:
                billing_address_obj = BillingAddress.objects.create(user=user, address=address_obj,
                                                                    first_name=first_name,
                                                                    last_name=last_name, billingEmail=billingEmail,
                                                                    entityPhone=entityPhone, zip_code=zip_code)

            total_products_cost_without_tax_in_USD = 0
            total_products_cost_with_tax_in_USD = 0
            total_products_cost_with_tax_in_cents = 0
            total_VAT_in_USD = 0

            product_info_list = list(filter(None.__ne__, product_info_list))

            for product_info_dict in product_info_list:
                try:
                    product_id = int(product_info_dict.get('product_id'))
                    try:
                        entity_id = product_info_dict.get('entity', None)
                        if entity_id is not None:
                            entity = Entity.objects.get(id=int(entity_id))
                        else:
                            entity = None
                    except KeyError as ke:
                        entity = None
                    if product_id:
                        product = Product.objects.get(id=product_id, is_active=True)
                        # product_cost = product.cost

                        quantity = int(product_info_dict.get('quantity'))
                        if quantity > 0:

                            product_total_cost = (product.cost / product.unit) * quantity

                            product_cost_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(
                                product_total_cost, entity)

                            individual_product_amount_with_tax_in_cents = product_cost_amount_dict[
                                'total_amount_with_tax_in_cents']
                            individual_product_amount_with_tax_in_USD = product_cost_amount_dict[
                                'total_amount_with_tax_in_USD']
                            # individual_product_VAT_USD = product_cost_amount_dict['VAT_USD']

                            total_products_cost_without_tax_in_USD += product_total_cost
                            total_products_cost_with_tax_in_USD += individual_product_amount_with_tax_in_USD
                            total_products_cost_with_tax_in_cents += individual_product_amount_with_tax_in_cents
                        else:
                            payment_logger.info("invalid quantity.")
                            raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

                        # if product.product_type == Product.CREDIT:
                        #     no_of_credits = product_info_dict.get('quantity')

                    else:
                        payment_logger.info("invalid product_id.")
                        raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Product.DoesNotExist as pdne:
                    payment_logger.info("product not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("invalid key  product_id.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except Entity.DoesNotExist as edne:
                    payment_logger.info("entity not found.")
                    raise ICFException(_("Transaction Failed."), status_code=status.HTTP_400_BAD_REQUEST)

            payment_type = PaymentType.PAYMENT_TYPE_FREE_CHECKOUT

            create_transaction_dict = {
                'user': user,
                'entity': entity,
                'payment_type': payment_type,
                'req_date': datetime.today().date(),
                'req_amount_in_cents': None,
                'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
                'req_token': None,
                'req_desc': description,
                'resp_date': None,
                'payment_status': PaymentStatus.PENDING,
                'resp_error_code': None,
                'resp_error_details': None,
                'resp_amount_in_cents': None,
                'resp_amount_in_dollars': None,
                'resp_transaction_id': None,
                'resp_currency': currency,
                'resp_failure_code': None,
                'resp_failure_message': None

            }
            # create row transaction(order) table to keep track of the products user
            # is purchasing with payment status is failed

            icf_payment_transaction = ICF_Payment_Transaction_Manager(). \
                create_offline_payment_transaction_details(create_transaction_dict)

            # loop through the product_info_dict to create instance of the actual product
            # with is_product_active status as invalid
            # all_product_item_dict = []

            all_order_details_list = []
            all_products_list = []

            credits_info_dict_list = []

            for product_info_dict in product_info_list:
                try:
                    # base product's id
                    product_id = product_info_dict.get('product_id')
                    # actual product's id(SubscriptionPlan,EventProduct)
                    product_item_id = product_info_dict.get('product_item_id', None)
                    product = Product.objects.get(id=product_id, is_active=True)
                    # product_name = product.name
                    # product_unit = product.unit
                    # individual_product_cost = product.cost
                    # product_currency_id = product.currency
                    # currency = Currency.objects.get(id=product_currency_id)
                    currency = serializer.validated_data.get('currency')
                    # product_currency = currency
                    # product_is_active = product.is_active
                    # product_parent_product = product.parent_product
                    # product_description = product.description
                    product_type = product.product_type
                    quantity = int(product_info_dict.get('quantity'))

                    if product_type == Product.CREDIT:
                        no_of_credits = quantity
                        entity_id = product_info_dict.get("entity")
                        entity = Entity.objects.get(id=entity_id)
                        if no_of_credits <= 0:
                            payment_logger.error("transaction failed. reason : {reason}".format(
                                reason="No of credits should be a non zero positive integer."))
                            return Response({"detail": _(
                                "Transaction failed. No of credits should be a non zero positive integer.")},
                                status=status.HTTP_400_BAD_REQUEST)

                        # create  new record in AvailableBalance Table and CreditHistory Table
                        # to the user for this entity
                        try:
                            action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                        except CreditAction.DoesNotExist:
                            raise ICFException(_("Invalid action, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        credit_history = CreditHistory.objects.create(entity=entity, user=user,
                                                                      available_credits=no_of_credits,
                                                                      action=action, is_active=False)
                        model_name = credit_history.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost, content_type=content_type,
                                                                        object_id=credit_history.id
                                                                        )
                        credits_info_dict = {
                            'product': product,
                            'no_of_credits': no_of_credits,
                            'entity': entity
                        }
                        credits_info_dict_list.append(credits_info_dict)

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.SUBSCRIPTION:
                        # product_id = product_id
                        # product_obj = Product.objects.get(id=product_id)
                        subscription_plan_id = product_item_id
                        entity_id = product_info_dict.get('entity')
                        entity = Entity.objects.get(id=entity_id)
                        subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
                        subscription_plan_start_date = datetime.today().date()
                        subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
                            subscription_plan_obj.duration)

                        action_subscriptions = ActionSubscriptionPlan.objects.filter(
                            subscription_plan=subscription_plan_obj)

                        if action_subscriptions:

                            # subscription_list = []
                            subscription = Subscription.objects.create(user=user, entity=entity,
                                                                       start_date=subscription_plan_start_date,
                                                                       end_date=subscription_plan_end_date,
                                                                       subscription_plan=subscription_plan_obj,
                                                                       is_active=False
                                                                       )

                            for action_subscription in action_subscriptions:
                                subscription_action, created = SubscriptionAction.objects.get_or_create(
                                    subscription=subscription, action=action_subscription.action,
                                    max_count=action_subscription.max_limit)

                                # subscription_action.action_count = subscription_action.action_count + 1
                                # subscription_action.save(update_fields=['action_count'])

                            model_name = subscription.__class__.__name__.lower()

                            content_type = ContentType.objects.get(app_label='icf_orders', model=model_name)

                            order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                            product=product,
                                                                            entity=entity, user=user, quantity=quantity,
                                                                            price=product.cost,
                                                                            content_type=content_type,
                                                                            object_id=subscription.id
                                                                            )

                            all_order_details_list.append(order_details_obj)
                            all_products_list.append(product)

                    elif product_type == Product.EVENT_PRODUCT:
                        event_product_id = product_item_id
                        event_product_obj = EventProduct.objects.get(id=event_product_id)

                        entityName = product_info_dict.get("entity_name", None)
                        entityEmail = product_info_dict.get("entity_email", None)
                        entityPhone = product_info_dict.get("entity_phone", None)
                        name_of_representative = product_info_dict.get("name_of_representative", None)
                        address = product_info_dict.get("address", None)
                        participants = product_info_dict.get("participants", None)
                        featured_event_slug = product_info_dict.get("featured_event_slug")
                        featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            featured_event_and_product = FeaturedEventAndProduct.objects.get(product=event_product_obj,
                                                                                             featured_event=featured_event)
                        except FeaturedEventAndProduct.DoesNotExist as fepne:
                            payment_logger.info("FeaturedEventAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Featured event don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                        expiry_date = EventProduct.objects.get(product=product).expiry_date
                        current_date_time = timezone.now()
                        if expiry_date < current_date_time or featured_event.end_date < datetime.today().date():
                            payment_logger.info(" EventProduct already expired or featured event "
                                                "end date is less than the current date ")
                            raise ICFException(_("Cannot buy products, because of products expiry date."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        participant = Participant.objects.create(user=user, featured_event=featured_event,
                                                                 product=event_product_obj,
                                                                 quantity=quantity, entity_name=entityName,
                                                                 entity_email=entityEmail,
                                                                 phone_no=entityPhone,
                                                                 name_of_representative=name_of_representative,
                                                                 address=address, participants=participants,
                                                                 total_cost=amount,
                                                                 is_payment_successful=False,
                                                                 is_active=False
                                                                 )

                        model_name = participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_featuredevents', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=None, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)

                    elif product_type == Product.CAREER_FAIR_PRODUCT:
                        # in this condition both product id is Product Table (Base Product Id)
                        # career_fair_product_id = product_id
                        # product_obj = Product.objects.get(id=career_fair_product_id)

                        # entityName = product_info_dict.get("entity_name")
                        # entityEmail = product_info_dict.get("entity_email")
                        # entityPhone = product_info_dict.get("entity_phone")
                        name_of_representative = product_info_dict.get("name_of_representative")
                        representative_email = product_info_dict.get("representative_email")
                        address = product_info_dict.get("address", None)
                        # participant_type = product_info_dict.get("participant_type")
                        career_fair_slug = product_info_dict.get("career_fair_slug")
                        career_fair = CareerFair.objects.get(slug=career_fair_slug)
                        product_sub_type = product_info_dict.get("product_sub_type")
                        if entity and product_sub_type==CareerFairProductSubType.ADVERTISEMENT:
                            link="no link"
                            # send email here
                            # when product subtype is an advertisement create 2 entry for desktop and mobile adds
                            is_ad_already_exist = CareerFairAdvertisement.objects.filter(career_fair=career_fair,
                                                                                         entity=entity)
                            if is_ad_already_exist.count() == 0:
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.MOBILE_IMAGE

                                )
                                CareerFairAdvertisement.objects.create(
                                    user=user,
                                    career_fair=career_fair,
                                    entity=entity,
                                    product=product,
                                    ad_image_type=CareerFairImageType.DESKTOP_IMAGE

                                )
                                CareerFairUtil.send_add_advertisement_link_buyer(entity, user, link)

                        cost = product.cost
                        amount = cost * quantity
                        try:
                            career_fair_and_product = CareerFairAndProduct.objects.get(product=product,
                                                                                       career_fair=career_fair,
                                                                                       product_sub_type=product_sub_type)
                        except CareerFairAndProduct.DoesNotExist as fepne:
                            payment_logger.info("CareerFairAndProduct does not found.")
                            raise ICFException(_("Transaction failed. Career fair don't have this product."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        # if address is None:
                        #     address = address_1
                        #     if address_2:
                        #         address = address + ","+address_2
                        #     if city_obj:
                        #         address = address + ","+city_obj.city

                        if (entity):
                            career_fair_participant = CareerFairParticipant.objects.create(user=user,
                                                                                           career_fair=career_fair,
                                                                                           participant_type=product.buyer_type,
                                                                                           name_of_representative=name_of_representative,
                                                                                           total_cost=amount,
                                                                                           representative_email=representative_email,
                                                                                           address=address,
                                                                                           entity_id=entity.id,
                                                                                           is_payment_successful=False,
                                                                                           is_active=False)
                        else:
                            career_fair_participant = CareerFairParticipant.objects.create(user=user,
                                                                                           career_fair=career_fair,
                                                                                           participant_type=product.buyer_type,
                                                                                           name_of_representative=name_of_representative,
                                                                                           total_cost=amount,
                                                                                           representative_email=representative_email,
                                                                                           address=address,
                                                                                           is_payment_successful=False,
                                                                                           is_active=False)
                        participant_and_product = ParticipantAndProduct.objects.create(
                            participant=career_fair_participant,
                            product=product, quantity=quantity)

                        model_name = career_fair_participant.__class__.__name__.lower()

                        content_type = ContentType.objects.get(app_label='icf_career_fair', model=model_name)

                        order_details_obj = OrderDetails.objects.create(transaction=icf_payment_transaction,
                                                                        product=product,
                                                                        entity=entity, user=user, quantity=quantity,
                                                                        price=product.cost,
                                                                        content_type=content_type,
                                                                        object_id=career_fair_participant.id
                                                                        )

                        all_order_details_list.append(order_details_obj)
                        all_products_list.append(product)
                        if entity and product_sub_type==CareerFairProductSubType.TICKET:
                            add_free_subscription_on_participate_as_entity.add_free_subscription(user, entity);


                    else:
                        payment_logger.info("Invalid product with unknown product type")
                        raise ICFException(_("Invalid product, please check and try again."),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                except Product.DoesNotExist as pdne:
                    payment_logger.info("Could not generate invoice because Product not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except EventProduct.DoesNotExist as pdne:
                    payment_logger.info("Could not generate invoice because EventProduct not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except KeyError as ke:
                    payment_logger.info("Could not generate invoice because transaction id not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except ContentType.DoesNotExist as ctne:
                    payment_logger.info("Could not generate invoice because ContentType object not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except SubscriptionPlan.DoesNotExist as spdne:
                    payment_logger.info("Could not generate invoice because SubscriptionPlan object not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except FeaturedEvent.DoesNotExist as fedne:
                    payment_logger.info("Could not generate invoice because FeaturedEvent object not found.")
                    raise ICFException(_("Could not generate invoice."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFair.DoesNotExist as fedne:
                    payment_logger.info("CareerFair object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)
                except CareerFairAndProduct.DoesNotExist as fedne:
                    payment_logger.info("CareerFairAndProduct object not found.")
                    raise ICFException(_("Transaction failed."), status_code=status.HTTP_400_BAD_REQUEST)

            # icf_charge_obj = PaymentManager().get_payment_service(PaymentType.PAYMENT_TYPE_PAYPAL).\
            #     make_payment(token, total_products_cost_with_tax_in_USD, currency, description)

            # if icf_charge_obj.paid:
            #     icf_payment_transaction.payment_status = PaymentStatus.SUCCESS
            #     icf_payment_transaction.save(update_fields=["payment_status"])

            # update_transaction_dict = {
            #     'user': user,
            #     'entity': None,
            #     'payment_type': payment_type,
            #     'req_date': datetime.today().date(),
            #     'req_amount_in_cents': None,
            #     'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
            #     'req_token': token,
            #     'req_desc': description,
            #     'resp_date': icf_charge_obj.resp_date,
            #     'payment_status': icf_charge_obj.paid,
            #     'resp_error_code': icf_charge_obj.resp_error_code,
            #     'resp_error_details': icf_charge_obj.resp_error_details,
            #     'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
            #     'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
            #     'resp_transaction_id': icf_charge_obj.resp_transaction_id,
            #     'resp_currency': icf_charge_obj.resp_currency,
            #     'resp_failure_code': icf_charge_obj.resp_failure_code,
            #     'resp_failure_message': icf_charge_obj.resp_failure_message
            #
            # }

            # update remaining fields of transaction table
            # icf_payment_transaction = ICF_Payment_Transaction_Manager().update_paypal_payment_transaction_details(icf_payment_transaction, update_transaction_dict)

            # for item in all_order_details_list:
            #     content_type_obj = ContentType.objects.get_for_id(item.content_type_id)
            #     model = content_type_obj.model_class()
            #     product_sub_type_obj = model.objects.get(id=item.object_id)
            #     product_sub_type_obj.is_active = True
            #     product_sub_type_obj.save(update_fields=["is_active"])
            #     if model == 'Participant':
            #         product_sub_type_obj = model.objects.get(id=item.object_id)
            #         product_sub_type_obj.is_payment_successful = True
            #         product_sub_type_obj.save(update_fields=["is_payment_successful"])

            # for credits_info_dict in credits_info_dict_list:
            #     try:
            #         # generic product's id
            #         product = credits_info_dict.get('product')
            #         product_type = product.product_type
            #         no_of_credits = int(credits_info_dict.get('no_of_credits'))
            #         entity = credits_info_dict.get('entity')
            #         try:
            #             entity_balance = AvailableBalance.objects.get(entity=entity)
            #             total_balance = entity_balance.available_credits + no_of_credits
            #             entity_balance.available_credits = total_balance
            #             entity_balance.save(update_fields=['available_credits'])
            #         except AvailableBalance.DoesNotExist as dne:
            #             entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
            #                                                              available_credits=no_of_credits)
            #         CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
            #     except Exception as e:
            #         payment_logger.error("Something went wrong. reason :{reason}".format(reason=str(e)))
            #         raise ICFException(_("Something went wrong. Try again later"),
            #                            status_code=status.HTTP_400_BAD_REQUEST)

            ####
            # delete all items in Cart table for the product and user

            for product_obj in all_products_list:
                try:
                    Cart.objects.filter(product=product_obj, user=user).delete()
                except Exception as ce:
                    payment_logger.error("Could not delete cart items reason :{reason}".format(reason=str(ce)))
                    raise ICFException(_("Something went wrong. Try again later"),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                ####
                # log transaction details

            ICFPaymentLogger().log_all_product_payment_details(create_transaction_dict)

            ####
            # generate receipt

            order_no = icf_payment_transaction.order_no
            is_offline = False
            is_free_checkout = True
            IcfBillGenerator().generate_receipt_or_invoice_for_products_purchase(order_no, user, currency,
                                                                                 all_order_details_list,
                                                                                 total_products_cost_without_tax_in_USD,
                                                                                 total_products_cost_with_tax_in_USD,
                                                                                 base_url, is_offline,
                                                                                 billing_address_obj, is_free_checkout)

            return Response({"response_message": _("Invoice generated successfully."),
                             "amount_to_be_paid": float(total_products_cost_with_tax_in_USD)
                             },
                            status=status.HTTP_200_OK)

            # else:
            #
            #     # delete all items from order_details table
            #
            #     for order_detail_obj in all_order_details_list:
            #         order_detail_obj.delete()
            #
            #
            #     # # send an email to PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT  failure payments
            #     #
            #     # email_subject = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT).format(entity.name),
            #     # payment_type = "Credit Card"
            #     # payment_logger.info(
            #     #         "transaction failed while purchase credits:{entity},\n "
            #     #         "payment_type : {payment_type},\n ".format(entity=entity.name, payment_type=payment_type))
            #     #
            #     # email_body = str(app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
            #     #                                                                                            entity.name,
            #     #                                                                                            user.display_name,
            #     #                                                                                            user.email,
            #     #                                                                                            total_product_amount_with_tax_in_USD)
            #     # msg = EmailMessage(subject=email_subject,
            #     #                        body=email_body,
            #     #                        to=[app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
            #     #                        )
            #     # msg.content_subtype = "html"
            #     # msg.send()
            #
            #     ####
            #     # log filed transaction or payment details
            #
            #     failed_transaction_dict = {
            #         'user': user,
            #         'entity': None,
            #         'payment_type': payment_type,
            #         'req_date': datetime.today().date(),
            #         'req_amount_in_cents': None,
            #         'req_amount_in_dollars': total_products_cost_with_tax_in_USD,
            #         'req_token': token,
            #         'req_desc': description,
            #         'resp_date': icf_charge_obj.resp_date,
            #         'payment_status': icf_charge_obj.paid,
            #         'resp_error_code': icf_charge_obj.resp_error_code,
            #         'resp_error_details': icf_charge_obj.resp_error_details,
            #         'resp_amount_in_cents': icf_charge_obj.resp_amount_in_cents,
            #         'resp_amount_in_dollars': icf_charge_obj.resp_amount_in_dollars,
            #         'resp_transaction_id': icf_charge_obj.resp_transaction_id,
            #         'resp_currency': icf_charge_obj.resp_currency,
            #         'resp_failure_code': icf_charge_obj.resp_failure_code,
            #         'resp_failure_message': icf_charge_obj.resp_failure_message
            #
            #     }
            #
            #     ICFPaymentLogger().log_all_product_payment_details(failed_transaction_dict)
            #
            #     return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as ke:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(ke)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except City.DoesNotExist as cdn:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(cdn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except Entity.DoesNotExist as edn:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(edn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except CreditAction.DoesNotExist as cadn:
            payment_logger.error("Could not generate invoice. because : {reason}".format(reason=str(cadn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist as spdn:
            payment_logger.error(
                "Could not generate invoice. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as spdn:
            payment_logger.error(
                "Could not generate invoice. because : {reason}".format(reason=str(spdn)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except EventProduct.DoesNotExist as pdn:
            payment_logger.exception("Could not generate invoice.")
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payment_logger.exception("Could not generate invoice. reason: {reason} ".format(reason=str(e)))
            return Response({"detail": _("Could not generate invoice.")}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------------------------
# **********************************************************************************************
# ---------------------------------------------------------------------------------------------


# class GenerateInvoiceForProductsApiView(CreateAPIView):
#     serializer_class = InvoiceForProductsSerializer
#     permission_classes = (IsAuthenticated,)
#
#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         try:
#             user = self.request.user
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#             entity_slug = self.kwargs.get('entity_slug')
#
#             product_info_list = serializer.validated_data.get('product_info_list')
#             currency = serializer.validated_data.get('currency')
#             # token = serializer.validated_data.get('paymentToken')
#             # payment_id = serializer.validated_data.get('paymentID')
#             description = "generating invoice for  products using offline payment"
#             base_url = request.build_absolute_uri()
#             entity = Entity.objects.get(slug=entity_slug)
#             total_products_cost = 0
#             credits_quantity = 0
#
#             product_info_list = list(filter(None.__ne__, product_info_list))
#
#             for product_info_dict in product_info_list:
#                 try:
#                     product_id = product_info_dict.get('product_id')
#                     if product_id:
#                         product = Product.objects.get(id=product_id)
#                         product_cost = product.cost
#                         total_products_cost += product_cost
#                     else:
#                         logger.exception("invalid product_id")
#                         raise ICFException(_("Invalid key product_id. \n"), status_code=status.HTTP_400_BAD_REQUEST)
#                 except Product.DoesNotExist as pdne:
#                     payment_logger.exception(str(pdne))
#                     raise ICFException(_("Product not found. \n"), status_code=status.HTTP_400_BAD_REQUEST)
#                 except KeyError as ke:
#                     payment_logger.exception(str(ke))
#                     raise ICFException(_("Invalid key product_id. \n"), status_code=status.HTTP_400_BAD_REQUEST)
#
#             total_product_cost_without_tax_in_USD = total_products_cost
#
#             total_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(entity,
#                                                                                                          total_product_cost_without_tax_in_USD)
#
#             # total_amount_with_tax_in_cents = total_amount_dict['total_amount_with_tax_in_cents']
#             total_product_amount_with_tax_in_USD = total_amount_dict['total_amount_with_tax_in_USD']
#             total_product_VAT_USD = total_amount_dict['VAT_USD']
#             payment_type = PaymentType.PAYMENT_TYPE_OFFLINE
#
#             create_transaction_dict = {
#                 'user': user,
#                 'entity': entity,
#                 'payment_type': payment_type,
#                 'req_date': datetime.today().date(),
#                 'req_amount_in_cents': None,
#                 'req_amount_in_dollars': total_product_amount_with_tax_in_USD,
#                 'req_token': None,
#                 'req_desc': description,
#                 'resp_date':  None,
#                 'payment_status': PaymentStatus.PENDING,
#                 'resp_error_code': None,
#                 'resp_error_details': None,
#                 'resp_amount_in_cents': None,
#                 'resp_amount_in_dollars': None,
#                 'resp_transaction_id': None,
#                 'resp_currency': currency,
#                 'resp_failure_code': None,
#                 'resp_failure_message': None
#
#             }
#             # create row transaction(order) table to keep track of the products user
#             # is purchasing with payment status is failed
#
#             transaction_dict = ICF_Payment_Transaction_Manager().\
#                 create_offline_payment_transaction_details(create_transaction_dict)
#
#             # loop through the product_info_dict to create instance of the actual product
#             # with is_product_active status as invalid
#             # all_product_item_dict = []
#
#             all_order_details_list = []
#             all_products_list = []
#             for product_info_dict in product_info_list:
#                 try:
#                     # generic product's id
#                     product_id = product_info_dict.get('product_id')
#                     # actual product's id(SubscriptionPlan,EventProduct)
#                     product_item_id = product_info_dict.get('product_item_id', None)
#                     product = Product.objects.get(id=product_id)
#                     product_name = product.name
#                     product_unit = product.unit
#                     # individual_product_cost = product.cost
#                     currency = currency
#                     product_is_active = product.is_active
#                     product_parent_product = product.parent_product
#                     product_description = product.description
#                     product_type = product.product_type
#
#                     if product_type == Product.CREDIT:
#                         no_of_credits = product_info_dict.get("quantity")
#                         product_id = product_id
#                         product_obj = Product.objects.get(id=product_id)
#                         product_obj.is_active = True
#                         product_obj.save(update_fields=["is_active"])
#                         credits_quantity = no_of_credits
#
#                         # # create  new record in AvailableBalance Table and CreditHistory Table to the user for this entity
#                         # try:
#                         #     action = CreditAction.objects.get(action=PURCHASE_CREDITS)
#                         # except CreditAction.DoesNotExist:
#                         #     raise ICFException(_("Invalid action, please check and try again."),
#                         #                        status_code=status.HTTP_400_BAD_REQUEST)
#                         #
#                         # CreditHistory.objects.create(entity=entity, user=user,
#                         #                              available_credits=no_of_credits, action=action)
#                         #
#                         # try:
#                         #     # entity_balance = AvailableBalance.objects.get(entity=self.entity, user=self.user)
#                         #     entity_balance = AvailableBalance.objects.get(entity=entity)
#                         #     total_balance = entity_balance.available_credits + no_of_credits
#                         #     entity_balance.available_credits = total_balance
#                         #     entity_balance.save(update_fields=['available_credits'])
#                         # except AvailableBalance.DoesNotExist as dne:
#                         #     entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
#                         #                                                      available_credits=no_of_credits)
#                         # CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
#
#                         content_type = ContentType.objects.get(app_label='icf_orders', model='product')
#                         transaction_id = transaction_dict.get('transaction_id')
#                         transaction = ICFPaymentTransaction.objects.get(id=transaction_id)
#                         order_details_obj = OrderDetails.objects.create(transaction=transaction, product=product_obj,
#                                                                         content_type=content_type,
#                                                                         object_id=product_id)
#                         all_order_details_list.append(order_details_obj)
#                         all_products_list.append(product_obj)
#
#                     elif product_type == Product.SUBSCRIPTION:
#                         product_id = product_id
#                         product_obj = Product.objects.get(id=product_id)
#                         subscription_plan_id = product_item_id
#                         subscription_plan_obj = SubscriptionPlan.objects.get(id=subscription_plan_id)
#                         subscription_plan_start_date = datetime.today().date()
#                         subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
#                             subscription_plan_obj.duration)
#                         # total_amount_without_tax_in_USD_for_subscription = product_obj.cost
#                         # total_amount_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(
#                         #     entity, total_amount_without_tax_in_USD_for_subscription)
#                         #
#                         # total_amount_with_tax_in_cents = total_amount_dict['total_amount_with_tax_in_cents']
#                         # total_amount_with_tax_in_USD = total_amount_dict['total_amount_with_tax_in_USD']
#                         # VAT_USD = total_amount_dict['VAT_USD']
#
#                         action_subscriptions = ActionSubscriptionPlan.objects.filter(subscription_plan=subscription_plan_obj)
#
#                         if action_subscriptions:
#
#                             # subscription_list = []
#                             subscription = Subscription.objects.create(user=user, entity=entity,
#                                                                        start_date=subscription_plan_start_date,
#                                                                        end_date=subscription_plan_end_date,
#                                                                        subscription_plan=subscription_plan_obj,
#                                                                        is_active=False
#                                                                        )
#
#                             for action_subscription in action_subscriptions:
#                                 subscription_action, created = SubscriptionAction.objects.get_or_create(
#                                                                    subscription=subscription,
#                                                                    action=action_subscription.action,
#                                                                    max_count=action_subscription.max_limit)
#
#                                 subscription_action.action_count = subscription_action.action_count + 1
#                                 subscription_action.save(update_fields=['action_count'])
#
#                                 # subscription_list.append(subscription)
#
#                                 # ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict,
#                                 #                                                                    icf_charge_obj)
#
#                             content_type = ContentType.objects.get(app_label='icf_orders', model='subscription')
#                             transaction_id = transaction_dict.get('transaction_id')
#                             transaction = ICFPaymentTransaction.objects.get(id=transaction_id)
#                             order_details_obj = OrderDetails.objects.create(transaction=transaction, product=product_obj,
#                                                                             content_type=content_type,
#                                                                             object_id=subscription.id)
#
#                             all_order_details_list.append(order_details_obj)
#                             all_products_list.append(product_obj)
#
#                     elif product_type == Product.EVENT_PRODUCT:
#                         product_id = product_id
#                         product_obj = Product.objects.get(id=product_id)
#                         event_product_id = product_item_id
#                         event_product_obj = EventProduct.objects.get(id=event_product_id)
#
#                         entityName = product_info_dict.get("entityName")
#                         entityEmail = product_info_dict.get("entityEmail")
#                         entityPhone = product_info_dict.get("entityPhone")
#                         quantity = int(product_info_dict.get('qty'))
#                         name_of_representative = product_info_dict.get("name_of_representative")
#                         address = product_info_dict.get("address")
#                         participants = product_info_dict.get("participants")
#                         featured_event_slug = serializer.validated_data.get("featured_event_slug")
#                         featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)
#
#                         cost = product.cost
#                         amount = cost * quantity
#
#                         # expiry_date = featured_event_and_category.product.expiry_date
#                         # current_date_time = timezone.now()
#                         # if expiry_date > current_date_time:
#                         participant = Participant.objects.create(user=user, featured_event=featured_event,
#                                                                  product=event_product_obj,
#                                                                  quantity=quantity, entity_name=entityName,
#                                                                  entity_email=entityEmail,
#                                                                  phone_no=entityPhone,
#                                                                  name_of_representative=name_of_representative,
#                                                                  address=address, participants=participants,
#                                                                  total_cost=amount,
#                                                                  is_payment_successful=False,
#                                                                  is_active=False
#                                                                  )
#                         content_type = ContentType.objects.get(app_label='icf_featuredevents', model='participant')
#
#                         transaction_id = transaction_dict.get('transaction_id')
#                         transaction = ICFPaymentTransaction.objects.get(id=transaction_id)
#                         order_details_obj = OrderDetails.objects.create(transaction=transaction, product=product_obj,
#                                                                         content_type=content_type,
#                                                                         object_id=product_id)
#                         all_order_details_list.append(order_details_obj)
#                         all_products_list.append(product_obj)
#
#                     else:
#                         payment_logger.info("Invalid product type.")
#                         raise ICFException(_("Invalid product type. \n"), status_code=status.HTTP_400_BAD_REQUEST)
#
#                 except Product.DoesNotExist as pdne:
#                     payment_logger.info("Product not found.")
#                     raise ICFException(_("Product not found. \n"), status_code=status.HTTP_400_BAD_REQUEST)
#
#
#             # for product_obj in all_products_list:
#             #     try:
#             #         cart = Cart.objects.get(product=product_obj, user=user)
#             #         cart.delete()
#             #     except Cart.DoesNotExist as cdne:
#             #         payment_logger.error(
#             #             "Could not delete cart items reason :{reason}".format(reason=str(cdne)))
#             #         raise ICFException(_("Something went wrong. try again later"),
#             #                            status_code=status.HTTP_400_BAD_REQUEST)
#
#             ####
#             # log transaction details
#
#             ICFPaymentLogger().log_invoice_genaration_for_products_details(create_transaction_dict)
#
#             order_no = transaction_dict.get('transaction_order_no')
#             is_offline = True
#             IcfBillGenerator.generate_receipt_or_invoice_for_products_purchase(order_no, user, entity, currency, all_order_details_list, credits_quantity, total_product_cost_without_tax_in_USD, total_product_VAT_USD, total_product_amount_with_tax_in_USD, base_url, is_offline)
#
#             return Response({"response_message": _("Invoice generated successfully."),
#                              "amount_to_be_paid": float(total_product_amount_with_tax_in_USD)
#                              },
#                             status=status.HTTP_200_OK)
#
#         except Entity.DoesNotExist as edn:
#             payment_logger.error("Could not buy product. because : {reason}".format(reason=str(edn)))
#             return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
#         except CreditAction.DoesNotExist as cadn:
#             payment_logger.error("Could not buy product. because : {reason}".format(reason=str(cadn)))
#             return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
#         except SubscriptionPlan.DoesNotExist as spdn:
#             payment_logger.error(
#                 "Could not buy products. because : {reason}".format(reason=str(spdn)))
#             return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
#         except ContentType.DoesNotExist as spdn:
#             payment_logger.error(
#                 "Could not buy products. because : {reason}".format(reason=str(spdn)))
#             return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
#         except EventProduct.DoesNotExist as pdn:
#             payment_logger.exception("EventProduct not found.")
#             return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             payment_logger.exception("something went wrong. reason: {reason} ".format(reason=str(e)))
#             return Response({"detail": _("Could not buy products.")}, status=status.HTTP_400_BAD_REQUEST)

def get_total_cart_amount(user):
    total_amt = 0.0
    cart = Cart.objects.filter(user=user)
    if cart:
        for c in cart:
            total_amt = total_amt + float(c.price)
    return total_amt


def get_country_tax(entity):
    try:
        if entity.address:
            country_tax = CountryTax.objects.get(country=entity.address.city.state.country)
        else:
            country_tax = CountryTax.objects.get(
                country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX).percentage
    except:
        country_tax = CountryTax.objects.get(
            country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX).percentage
    return country_tax


def get_total_amount_for_products(query_list):
    total_amt_without_tax = 0.0
    for c in query_list:
        total_amt_individual_product = c.qty * c.unit_price
        total_amt_without_tax += float(total_amt_individual_product)
    return total_amt_without_tax


def get_total_tax(query_list):
    total_total_tax = 0.0
    for c in query_list:
        if c.entity:
            entity = c.entity_obj
        else:
            entity = None
        amt_individual_product = c.qty * c.unit_price
        total_amout_dict = CalculateCreditChargeHelper().calculate_charge_with_tax_in_cents_and_USD(
            amt_individual_product, entity)
        tax_for_individual_product = total_amout_dict.get('VAT_USD')
        total_total_tax += float(tax_for_individual_product)
    return total_total_tax


def get_payment_status(transaction_obj):
    payment_status_str = ''
    for tuple_obj in PaymentStatus.PAYMENT_STATUS_CHOICES:
        if tuple_obj[0] == int(transaction_obj.payment_status):
            payment_status_str = tuple_obj[1]
    return payment_status_str


class CartCreateListView(ListCreateAPIView):

    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            serializer_class = CartListSerializer
        else:
            serializer_class = CartSerializer
        return serializer_class

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        total_amount = get_total_cart_amount(self.request.user)
        tax = get_country_tax(request.data.get('entity', None))
        return Response({'results': serializer.data, 'total_amount': total_amount, 'tax': tax})


class CartUpdateView(UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CartSerializer

    def get_object(self):
        try:
            return Cart.objects.get(pk=self.kwargs.get('id'))
        except Exception:
            return None


class CartDeleteView(DestroyAPIView):

    def get_object(self):
        try:
            return Cart.objects.get(pk=self.kwargs.get('id'))
        except Exception:
            return None


class GetCartCount(APIView):

    def get(self, request, *args, **kwargs):
        count = 0
        try:
            if self.request.user.is_authenticated():
                count = Cart.objects.filter(user=self.request.user).count()
        except Exception:
            pass

        return Response({"cart_count": count}, status=status.HTTP_200_OK)


class CartDetailView(RetrieveAPIView):
    serializer_class = CartListSerializer

    def get_object(self):
        try:
            return Cart.objects.get(pk=self.kwargs.get('id'))
        except Exception:
            return None


class PurchaseDetailsListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PurchaseProductsListSerializer

    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            total_amount_without_tax = get_total_amount_for_products(queryset)
            total_tax = get_total_tax(queryset)
            order_no = self.kwargs.get('order_no').lstrip().rstrip()
            transaction_obj = ICFPaymentTransaction.objects.get(order_no=order_no)
            payment_status_str = get_payment_status(transaction_obj)
            return Response({'results': serializer.data, 'total_amount_without_tax': total_amount_without_tax,
                             'total_tax': total_tax, 'created_date': transaction_obj.updated,
                             'payment_status': payment_status_str})
        except ICFPaymentTransaction.DoesNotExist as tdne:
            logger.exception("ICFPaymentTransaction object not found. {reason} ".format(reason=str(tdne)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        try:
            user = self.request.user
            # order_no = self.kwargs.get('order_no').lstrip().rstrip()
            order_no = self.kwargs.get('order_no').rstrip()
            transaction_obj = ICFPaymentTransaction.objects.get(order_no=order_no)
            all_order_details_list = OrderDetails.objects.filter(transaction=transaction_obj).order_by('created')

            products_list = []

            for order_details_obj in all_order_details_list:
                # content_type = order_details_obj.content_type
                # content_type_obj = ContentType.objects.get(id=content_type.id)
                # model = content_type_obj.model_class()
                # product_item_obj = model.objects.get(id=order_details_obj.object_id)

                product_details_obj = PurchaseProductDetail()
                product_details_obj.product_name = order_details_obj.product.name
                product_details_obj.qty = order_details_obj.quantity
                product_details_obj.description = order_details_obj.product.description
                if order_details_obj.entity:
                    product_details_obj.entity = order_details_obj.entity.name
                else:
                    product_details_obj.entity = None
                product_details_obj.unit_price = order_details_obj.product.cost / order_details_obj.product.unit
                product_details_obj.sub_total = product_details_obj.qty * product_details_obj.unit_price
                if order_details_obj.entity:
                    product_details_obj.entity_obj = order_details_obj.entity
                else:
                    product_details_obj.entity_obj = None
                if order_details_obj.product.product_type == Product.CREDIT:

                    # entity_name_str = app_settings.CREDIT_DETAILS.get('entity_name') + ":" + \
                    #                   order_details_obj.entity.name + "<br/>"
                    # if order_details_obj.entity.address.address_1:
                    #     entity_address_1_str = app_settings.CREDIT_DETAILS.get(
                    #         'entity_address') + ":" + order_details_obj.entity.address.address_1 + "<br/>"
                    # else:
                    #     entity_address_1_str = ''
                    # if order_details_obj.entity.address.address_2:
                    #     entity_address_2_str = order_details_obj.entity.address.address_2 + "<br/>"
                    # else:
                    #     entity_address_2_str = ''
                    # entity_address_str = entity_address_1_str + entity_address_2_str
                    #
                    # entity_city_str = app_settings.CREDIT_DETAILS.get('entity_city') + ":" + str(
                    #     order_details_obj.entity.address.city)
                    #
                    # credit_details = '{0}{1}{2}'.format(entity_name_str, entity_address_str, entity_city_str)
                    #
                    # product_details_obj.details = mark_safe(credit_details)

                    products_list.append(product_details_obj)

                elif order_details_obj.product.product_type == Product.SUBSCRIPTION:

                    # content_type = order_details_obj.content_type
                    # content_type_obj = ContentType.objects.get(id=content_type.id)
                    # model = content_type_obj.model_class()
                    # subscription = model.objects.get(id=order_details_obj.object_id)
                    # subscription_plan = SubscriptionPlan.objects.get(product=order_details_obj.product)
                    #
                    # entity_name_str = app_settings.SUBSCRIPTION_DETAILS.get(
                    #     'entity_name') + ":" + order_details_obj.entity.name + "<br/>"
                    # duration_str = app_settings.SUBSCRIPTION_DETAILS.get('duration') + ":" + str(
                    #     subscription_plan.duration) + "<br/>"
                    # subscription_description_str = app_settings.SUBSCRIPTION_DETAILS.get(
                    #     'description') + ":" + order_details_obj.product.description
                    #
                    # subscription_details = '{0}{1}{2}'.format(entity_name_str, duration_str,
                    #                                           subscription_description_str)
                    #
                    # product_details_obj.details = mark_safe(subscription_details)

                    products_list.append(product_details_obj)

                elif order_details_obj.product.product_type == Product.EVENT_PRODUCT:

                    # content_type = order_details_obj.content_type
                    # content_type_obj = ContentType.objects.get(id=content_type.id)
                    # model = content_type_obj.model_class()
                    # participant = model.objects.get(id=order_details_obj.object_id)
                    #
                    # featured_event_name_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get(
                    #     'featured_event_name') + \
                    #                           ":" + participant.featured_event.title + "<br/>"
                    #
                    # entity_name_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('entity_name') + ":" + \
                    #                   participant.entity_name + "<br/>"
                    #
                    # entity_email_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('entity_email') + ":" + \
                    #                    participant.entity_email + "<br/>"
                    #
                    # entity_contact_no_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('contact_no') + ":" + \
                    #                         participant.phone_no + "<br/>"
                    #
                    # entity_name_of_representative_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get(
                    #     'name_of_representative') + ":" + \
                    #                                     participant.name_of_representative + "<br/>"
                    #
                    # participants_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('participants') + \
                    #                    ":" + participant.participants + "<br/>"
                    #
                    # entity_address_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('address') + \
                    #                      ":" + str(participant.address) + "<br/>"
                    #
                    # featured_event_participant_details = '{0}{1}{2}{3}{4}{5}{6}'.format(featured_event_name_str,
                    #                                                                     entity_name_str,
                    #                                                                     entity_email_str,
                    #                                                                     entity_contact_no_str,
                    #                                                                     entity_name_of_representative_str,
                    #                                                                     participants_str,
                    #                                                                     entity_address_str)
                    #
                    # product_details_obj.details = mark_safe(featured_event_participant_details)

                    products_list.append(product_details_obj)

                else:
                    payment_logger.info("pdf cannot be generated for products purchase.\n")
                    raise ICFException("something went wrong reason:{reason}.".
                                       format(reason="Unknown Product Type to generate bill."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            queryset = products_list
            return queryset
        except ICFPaymentTransaction.DoesNotExist as tdne:
            logger.exception("ICFPaymentTransaction object not found. {reason} ".format(reason=str(tdne)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)


class GetBillingAddressForUserApiView(RetrieveAPIView):
    queryset = BillingAddress.objects.all()
    serializer_class = BillingAddressRetrieveSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        try:
            user = self.request.user
            billing_address = BillingAddress.objects.get(user=user)
            return billing_address
        except BillingAddress.DoesNotExist as bae:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetBuyerInformationForUserApiView(RetrieveAPIView):
    serializer_class = BuyerInformationRetrieveSerializer
    permission_classes = (IsAuthenticated,)

    # def get_object(self):
    #     try:
    #         user = self.request.user
    #         billing_address = BillingAddress.objects.get(user=user)
    #         return billing_address
    #     except BillingAddress.DoesNotExist as bae:
    #         return None

    def retrieve(self, request, *args, **kwargs):
        try:
            user = self.request.user
            billing_address = BillingAddress.objects.get(user=user)
            if user.last_name:
                user_name_str = user.first_name + " " + user.last_name
            else:
                user_name_str = user.first_name
            data = {
                'name': user_name_str,
                'entity': None,
                'email': user.email,
                'phone': user.mobile,
                'billing_address': str(billing_address.address)
            }
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except BillingAddress.DoesNotExist as bae:
            logger.exception("BillingAddress object not found. {reason} ".format(reason=str(bae)))
            return Response({"detail": _("Billing address not found.")}, status=status.HTTP_400_BAD_REQUEST)


class add_free_subscription_on_participate_as_entity:
    @staticmethod
    def add_free_subscription(user, entity):
        logger.info("Add free subscription for company: {}".format(entity.name))
        is_free_careerfair_active = settings.FREE_CAREER_FAIR.get("is_active")
        if is_free_careerfair_active:
            plan_name = settings.FREE_CAREER_FAIR.get("plan_name")
            logger.info("Active free subscription plan: {}".format(plan_name))
            # product=Product.objects.filter(name=plan_name).first()

            subscription_plan_obj = SubscriptionPlan.objects.filter(product__name=plan_name).first()
            if subscription_plan_obj:
                subscription_plan_start_date = datetime.today().date()
                subscription_plan_end_date = subscription_plan_start_date + main_datetime_module.timedelta(
                    subscription_plan_obj.duration)
                action_subscriptions = ActionSubscriptionPlan.objects.filter(
                    subscription_plan=subscription_plan_obj)
                entity = entity
                user = user
                currently_active_subscriptions = Subscription.objects.filter(entity_id=entity.id,
                                                                                end_date__gte=subscription_plan_start_date)
                if currently_active_subscriptions.count() == 0:
                    logger.info("Creating a free subscription {} for the entity {}".format(plan_name, entity.name))
                    if action_subscriptions:
                        # subscription_list = []
                        subscription = Subscription.objects.create(user=user, entity=entity,
                                                                   start_date=subscription_plan_start_date,
                                                                   end_date=subscription_plan_end_date,
                                                                   subscription_plan=subscription_plan_obj,
                                                                   is_active=True
                                                                   )
                        for action_subscription in action_subscriptions:
                            subscription_action, created = SubscriptionAction.objects.get_or_create(
                                subscription=subscription, action=action_subscription.action,
                                max_count=action_subscription.max_limit)

                        CareerFairUtil.send_free_subscription_email(entity, user, subscription_plan_start_date,
                                                                    subscription_plan_end_date)
                    else:
                        logger.info("Action limits not configured for subscription plan: {}".format(plan_name))

                else:
                    logger.info("The entity already has an active subscription plan")
            else:
                logger.info("The free subscription plan configured is not found in DB: {}".format(plan_name))


class SalesHistoryForEntity(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderDetailsForSalesSerializer
    queryset = OrderDetails.objects.all()

# 1. Collect the slug of the entity we need to get it's sales
# 2.
    def get_queryset(self):
        queryset = self.queryset.filter(entity__slug = self.kwargs.get('slug'))
        return queryset

class WithdrawalTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalTransactionSerializer
    permission_classes = (IsAuthenticated,)
    queryset = WithdrawalTransaction.objects.all()

    def get_serializer(self, *args, **kwargs):
        return WithdrawalTransactionSerializer(*args, **kwargs)

    def get_object(self):
        try:
        # Return transactio n where
            return WithdrawalTransaction.objects.get(entity__slug=self.kwargs.get('entity'), pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = WithdrawalTransaction.objects.filter(entity__slug=kwargs.get('entity'))
        serializer = WithdrawalTransactionSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user, 'entity': kwargs.get('entity')}
        serializer = WithdrawalTransactionSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot perform Withdrawal Transaction , create  an entity before WithdrawalTransaction")
            return Response({"detail": "Cannot perform Withdrawal Transaction , create  an entity before WithdrawalTransaction"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = WithdrawalTransaction.objects.get(entity__slug=kwargs.get('entity'), pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except WithdrawalTransaction.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Withdrawal Transaction object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = WithdrawalTransaction.objects.get(entity__slug=kwargs.get('entity'), pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update Withdrawal Transaction")
            return Response({"detail": "Cannot update Withdrawal Transaction"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update Withdrawal Transaction")
            return Response({"detail": "Cannot  update Withdrawal Transaction"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "Withdrawal Transaction got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Withdrawal Transaction not found, cannot delete")
            return Response({'detail': "Withdrawal Transaction not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

class WalletDetailApiView(RetrieveAPIView):
    queryset = Wallet.objects.all()
    serializer_class = WalletRetrieveSerializer
    permission_classes = (IsAuthenticated, IsEntityAdmin)
    lookup_field = "entity"
