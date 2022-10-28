import pytz
from django.core.mail import EmailMessage
from django.utils.timezone import now
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
import logging
from django.utils.translation import ugettext_lazy as _
from rest_framework.views import APIView
from django.shortcuts import render
from drf_yasg.utils import swagger_auto_schema

from icf import settings
from icf_orders.models import PaymentType
from icf_featuredevents import app_settings
from icf_generic.Exceptions import ICFException
from icf_integrations.sample_pay import ICF_Payment_Transaction_Manager, ICFPaymentLogger, IcfBillGenerator, \
    PaymentManager

logger = logging.getLogger(__name__)
featured_event_failed_transaction_log_file = logging.getLogger('icf.integrations.featured_event_transaction_failed')


from icf_featuredevents.api.serializers import FeaturedEventsListSerializer, FeaturedEventsRetrieveSerializer, \
    FeaturedEventGalleryDetailSerializer, FeaturedEventsUpcomingOrPastSerializer, FeaturedEventsProductSerializer, \
    ParticipantCreateSerializer, ProductSerializer, TermsAndConditionsSerializer, \
    LatestFeaturedEventSerializer, PurchaseTicketsByStripePaymentSerializer, PurchaseTicketsByPayPalPaymentSerializer, \
    OfflinePaymentInvoiceForTicketSerializer
from icf_featuredevents.models import FeaturedEvent, FeaturedEventGallery, EventProduct, Participant, \
    TermsAndConditions, FeaturedEventAndProduct


class GetFeaturedEventsListView(ListAPIView):
    serializer_class = FeaturedEventsListSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="List all Featured Event"
    )
    def get_queryset(self):
        queryset = FeaturedEvent.objects.filter(status=FeaturedEvent.FEATURED_EVENT_ACTIVE). \
            filter(start_date__lte=now(), end_date__gte=now()).order_by('-updated')
        # queryset = FeaturedEvent.objects.filter(status=FeaturedEvent.FEATURED_EVENT_ACTIVE). \
        #     filter(start_date__lte=datetime.now(pytz.utc).date(), end_date__gt=datetime.now(pytz.utc).date()).order_by('-updated')
        return queryset


class GetLatestFeaturedEventView(RetrieveAPIView):
    serializer_class = LatestFeaturedEventSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve all recently added Featured Event"
    )
    def get_object(self):
        try:
            featured_event = FeaturedEvent.objects.latest('created')
        except Exception as e:
            featured_event = None
        return featured_event


@swagger_auto_schema(
    operation_summary="Retrieve details of a single Featured Event"
)
class FeaturedEventDetailAPIView(RetrieveAPIView):
    queryset = FeaturedEvent.objects.all()
    serializer_class = FeaturedEventsRetrieveSerializer
    lookup_field = "slug"


class FeaturedEventGalleryDetailAPIView(ListAPIView):
    queryset = FeaturedEventGallery.objects.all()
    serializer_class = FeaturedEventGalleryDetailSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve gallery of Featured Event"
    )
    def get_queryset(self):
        queryset = self.queryset.filter(is_active=True).order_by('id')
        return queryset


class UpcomingFeaturedEventsListAPIView(ListAPIView):
    serializer_class = FeaturedEventsUpcomingOrPastSerializer

    @swagger_auto_schema(
        operation_summary="List upcoming Featured Event"
    )
    def get_queryset(self):


        # slug = self.kwargs.get('slug')
        queryset = FeaturedEvent.objects.filter(status=FeaturedEvent.FEATURED_EVENT_ACTIVE). \
            filter(start_date__gte=now()).order_by('-updated')
        qp_slug = self.request.query_params.get('exclude_event_slug', None)
        qp_event_title = self.request.query_params.get('search_text', None)
        qp_country_name = self.request.query_params.get('country_name', None)

        if qp_slug is not None:
            queryset = queryset.exclude(slug=qp_slug)

        if qp_event_title is not None:
            queryset = queryset.filter(title__icontains=qp_event_title)

        if qp_country_name is not None:
            queryset = queryset.filter(location__icontains=qp_country_name)

        return queryset


class PastFeaturedEventsListAPIView(ListAPIView):
    serializer_class = FeaturedEventsUpcomingOrPastSerializer

    @swagger_auto_schema(
        operation_summary="List past Featured Event"
    )
    def get_queryset(self):
        # slug = self.kwargs.get('slug')
        queryset = FeaturedEvent.objects.filter(status=FeaturedEvent.FEATURED_EVENT_ACTIVE). \
            filter(end_date__lt=datetime.today().date()).order_by('-updated')

        qp_slug = self.request.query_params.get('exclude_event_slug', None)
        qp_event_title = self.request.query_params.get('search_text', None)
        qp_country_name = self.request.query_params.get('country_name', None)

        if qp_slug is not None:
            queryset = queryset.exclude(slug=qp_slug)

        if qp_event_title is not None:
            queryset = queryset.filter(title__icontains=qp_event_title)

        if qp_country_name is not None:
            queryset = queryset.filter(location__icontains=qp_country_name)
        return queryset


# class FeaturedEventCategoryListAPIView(ListAPIView):
#     queryset = FeaturedEventCategory.objects.all()
#     serializer_class = FeaturedEventsCategorySerializer
#     pagination_class = None
#
#     def get_queryset(self):
#         queryset = self.queryset.filter(is_active=True).order_by('id')
#         return queryset


# class ProductsByCategoryListAPIView(ListAPIView):
#     serializer_class = FeaturedEventsProductSerializer
#     pagination_class = None
#
#     def get_queryset(self):
#         try:
#             featured_event_slug = self.kwargs.get('slug')
#             category_slug = self.kwargs.get('category_slug')
#             category = FeaturedEventCategory.objects.get(slug=category_slug)
#             featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)
#             product_id_list = FeaturedEventAndCategory.objects.filter(featured_event=featured_event, category=category).values_list('product', flat=True).distinct()
#             product_list = []
#             for value in product_id_list:
#                 product = EventProduct.objects.get(id=value)
#                 product_list.append(product)
#             queryset = product_list
#             return queryset
#         except FeaturedEvent.DoesNotExist as fedn:
#             logger.exception("FeaturedEvent does not exist.")
#             Response({"detail": "FeaturedEvent does not exist."}, status=status.HTTP_400_BAD_REQUEST)
#         except FeaturedEventCategory.DoesNotExist as fen:
#             logger.exception("FeaturedEventCategory does not exist.")
#             Response({"detail": "FeaturedEventCategory does not exist."}, status=status.HTTP_400_BAD_REQUEST)



# class PurchaseTicketsByStripePaymentAPIView(CreateAPIView):
#     serializer_class = PurchaseTicketsByStripePaymentSerializer
#     queryset = Participant.objects.all()
#     permission_classes = (IsAuthenticated,)
#
#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#
#             user = self.request.user
#             entityName = serializer.validated_data.get("entityName")
#             entityEmail = serializer.validated_data.get("entityEmail")
#             entityPhone = serializer.validated_data.get("entityPhone")
#             name_of_representative = serializer.validated_data.get("name_of_representative")
#             address = serializer.validated_data.get("address")
#             participants = serializer.validated_data.get("participants")
#             total_amount_with_tax_in_USD = float(serializer.validated_data.get("totalCost"))
#             productList = serializer.validated_data.get("productList")
#             stripeToken = serializer.validated_data.get("stripeToken")
#             feature_event_slug = serializer.validated_data.get("event_slug")
#             currency = serializer.validated_data.get("currency")
#             VAT_USD = float(serializer.validated_data.get("VAT"))
#
#             total_amount_without_tax_in_USD = total_amount_with_tax_in_USD - VAT_USD
#
#             featured_event = FeaturedEvent.objects.get(slug=feature_event_slug)
#
#             total_amount_with_tax_in_cents = int(round((total_amount_with_tax_in_USD * 100), 2))
#
#             participant_list = []
#
#             productList = list(filter(None.__ne__, productList))
#
#             if productList:
#
#                 # for product in productList:
#                 #     product_obj = Product.objects.get(id=product['id'])
#                 #     quantity = int(product['qty'])
#                 #     price = float(product['price'])
#                 #     name = product['name']
#                 #     amount = price * quantity
#                 #
#                 #     featured_event_and_category = FeaturedEventAndCategory.objects.get(featured_event=featured_event,
#                 #                                                                        product=product_obj)
#                 #     expiry_date = featured_event_and_category.product.expiry_date
#                 #     current_date_time = timezone.now()
#                 #     if expiry_date > current_date_time:
#                 #         participant = Participant.objects.create(user=user, featured_event=featured_event,
#                 #                                                  product=product_obj,
#                 #                                                  quantity=quantity, entity_name=entityName,
#                 #                                                  entity_email=entityEmail,
#                 #                                                  phone_no=entityPhone,
#                 #                                                  name_of_representative=name_of_representative,
#                 #                                                  address=address, participants=participants,
#                 #                                                  is_payment_successful=False,
#                 #                                                  total_cost=amount
#                 #                                                  )
#                 #         participant_list.append(participant)
#                 #     else:
#                 #         logger.exception("You can't purchase this package because expiry date")
#                 #         return Response({"detail": _("You can't purchase this package because expiry date.")}, status=status.HTTP_400_BAD_REQUEST)
#
#                 description = "Featured event participation"
#                 base_url = request.build_absolute_uri()
#
#                 entity_info = {
#                     "entityName": entityName,
#                     "entityEmail": entityEmail,
#                     "entityPhone": entityPhone,
#                     "name_of_representative": name_of_representative,
#                     "address": address,
#                     "participants": participants
#                 }
#
#                 request_dict = {
#
#                     'user': user,
#                     'entity': None,
#                     'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
#                     'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
#                     'token': stripeToken,
#                     'description': description,
#                     'payment_type': PAYMENT_TYPE.PAYMENT_TYPE_STRIPE.value
#
#                 }
#
#                 icf_charge_obj = PaymentManager().get_payment_service(PAYMENT_TYPE.PAYMENT_TYPE_STRIPE).make_payment(stripeToken, total_amount_with_tax_in_cents, currency, description)
#
#                 request_dict_log = {
#
#                     'user': user,
#                     'entity_info': entity_info,
#                     'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
#                     'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
#                     'token': stripeToken,
#                     'description': description,
#                     'transaction_id': icf_charge_obj.resp_transaction_id,
#                     'payment_type': PAYMENT_TYPE.PAYMENT_TYPE_STRIPE.value
#                 }
#
#
#                 if icf_charge_obj.paid:
#
#                     for participant in participant_list:
#                         participant.is_payment_successful = True
#                         participant.save(update_fields=["is_payment_successful"])
#
#                     for product in productList:
#                         product_obj = EventProduct.objects.get(id=product['id'])
#                         quantity = int(product['qty'])
#                         price = float(product['price'])
#                         name = product['name']
#                         amount = price * quantity
#
#                         featured_event_and_category = FeaturedEventAndCategory.objects.get(
#                             featured_event=featured_event,
#                             product=product_obj)
#                         # expiry_date = featured_event_and_category.product.expiry_date
#                         # current_date_time = timezone.now()
#                         # if expiry_date > current_date_time:
#                         participant = Participant.objects.create(user=user, featured_event=featured_event,
#                                                                      product=product_obj,
#                                                                      quantity=quantity, entity_name=entityName,
#                                                                      entity_email=entityEmail,
#                                                                      phone_no=entityPhone,
#                                                                      name_of_representative=name_of_representative,
#                                                                      address=address, participants=participants,
#                                                                      total_cost=amount,
#                                                                      is_payment_successful=True
#                                                                      )
#
#                     ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict, icf_charge_obj)
#
#                     ICFPaymentLogger().log_featured_event_payment_details(request_dict_log, icf_charge_obj)
#                     is_offline = False
#                     IcfBillGenerator().generate_event_reciept(user, featured_event, productList, total_amount_with_tax_in_USD, entity_info, currency, VAT_USD, base_url, is_offline)
#
#                     return Response({"response_message": _("Transaction is successful."),
#                                      "amount_paid": icf_charge_obj.resp_amount_in_dollars
#                                      },
#                                     status=status.HTTP_200_OK)
#
#                 else:
#
#                     ICF_Payment_Transaction_Manager().update_stripe_trasaction_details(request_dict, icf_charge_obj)
#
#                     ICFPaymentLogger().log_featured_event_payment_details(request_dict_log, icf_charge_obj)
#
#                     # send an email to FEATURED_EVENT_PAYMENT_FAILURE_NOTIFICATION_EMAIL  failure payments
#
#                     email_subject = str(app_settings.FEATURED_EVENT_PAYMENT_FAILURE_SUBJECT).format(featured_event.title),
#                     product_info_str = ""
#                     for product in productList:
#                         quantity = int(product['qty'])
#                         name = product['name']
#                         product_info_str.append(str(app_settings.PRODUCT_INFO_STR).format(name, quantity))
#
#                     payment_type = "Credit Card"
#
#                     featured_event_failed_transaction_log_file.info("transaction failed for featured_event:{featured_event},\n entity_info:{entity_info},\n"
#                                                                         "payment_type : {payment_type},\n while purchasing products:{products},"
#                                                                         "\n participants:{participants},\n".format(featured_event=featured_event.title, entity_info=entity_info,
#                                                                         payment_type=payment_type, products=product_info_str, participants=participants))
#
#                     email_body = str(app_settings.FEATURED_EVENT_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type, entity_info.get("entityName"),
#                                         user.display_name, entity_info.get("entityEmail"), entity_info.get("entityPhone"), product_info_str,
#                                                                                                         entity_info.get("participants"), total_amount_with_tax_in_USD)
#                     msg = EmailMessage(subject=email_subject,
#                                            body=email_body,
#                                            to=[app_settings.FEATURED_EVENT_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ])
#                     msg.content_subtype = "html"
#                     msg.send()
#
#                     return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
#
#             else:
#                 return Response({"detail": _("Transaction failed. No product choosen.")}, status=status.HTTP_400_BAD_REQUEST)
#
#         except EventProduct.DoesNotExist as pdn:
#             logger.exception("Product not found.")
#             Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)
#         except FeaturedEventAndCategory.DoesNotExist as e:
#             logger.exception("FeaturedEventAndCategory not found.")
#             Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             logger.exception(e)
#             Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)
#


# class PurchaseTicketsByPayPalPaymentAPIView(CreateAPIView):
#     serializer_class = PurchaseTicketsByPayPalPaymentSerializer
#     queryset = Participant.objects.all()
#     permission_classes = (IsAuthenticated,)
#
#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#
#             user = self.request.user
#             entityName = serializer.validated_data.get("entityName")
#             entityEmail = serializer.validated_data.get("entityEmail")
#             entityPhone = serializer.validated_data.get("entityPhone")
#             name_of_representative = serializer.validated_data.get("name_of_representative")
#             address = serializer.validated_data.get("address")
#             participants = serializer.validated_data.get("participants")
#             total_amount_with_tax_in_USD = float(serializer.validated_data.get("totalCost"))
#             productList = serializer.validated_data.get("productList")
#             token = serializer.validated_data.get("paymentToken")
#             payment_id = serializer.validated_data.get("paymentID")
#             feature_event_slug = serializer.validated_data.get("event_slug")
#             currency = serializer.validated_data.get("currency")
#             VAT_USD = float(serializer.validated_data.get("VAT"))
#
#             productList = list(filter(None.__ne__, productList))
#
#             featured_event = FeaturedEvent.objects.get(slug=feature_event_slug)
#
#             # totalCost_in_cents = round(float(totalCost), 2) * 100
#
#             for product in productList:
#                 product_obj = EventProduct.objects.get(id=product['id'])
#                 quantity = int(product['qty'])
#                 price = float(product['price'])
#                 name = product['name']
#                 amount = price * quantity
#
#                 featured_event_and_category = FeaturedEventAndCategory.objects.get(featured_event=featured_event,
#                                                                                    product=product_obj)
#                 expiry_date = featured_event_and_category.product.expiry_date
#                 current_date_time = timezone.now()
#                 if expiry_date > current_date_time:
#                     participant = Participant.objects.create(user=user, featured_event=featured_event,
#                                                              product=product_obj,
#                                                              quantity=quantity, entity_name=entityName,
#                                                              entity_email=entityEmail,
#                                                              phone_no=entityPhone,
#                                                              name_of_representative=name_of_representative,
#                                                              address=address, participants=participants,
#                                                              is_payment_successful=True,
#                                                              total_cost=amount
#                                                              )
#                 else:
#                     logger.exception("You can't purchase this package because expiry date")
#                     Response({"detail": _("You can't purchase this package because expiry date.")},
#                              status=status.HTTP_400_BAD_REQUEST)
#
#             description = "Featured event participation"
#             base_url = request.build_absolute_uri()
#
#             entity_info = {
#                 "entityName": entityName,
#                 "entityEmail": entityEmail,
#                 "entityPhone": entityPhone,
#                 "name_of_representative": name_of_representative,
#                 "address": address,
#                 "participants": participants
#             }
#
#             # total_amount_with_tax_in_USD = total_amount_with_tax_in_USD
#             # VAT_USD = VAT_USD
#
#             request_dict = {
#
#                 'user': user,
#                 'entity': None,
#                 'total_amount_with_tax_in_cents': None,
#                 'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
#                 'token': token,
#                 'description': description,
#                 'transaction_id': payment_id,
#                 'payment_type': PAYMENT_TYPE.PAYMENT_TYPE_PAYPAL.value
#
#             }
#
#             request_dict_log = {
#
#                 'user': user,
#                 'entity_info': entity_info,
#                 'total_amount_with_tax_in_cents': None,
#                 'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
#                 'token': token,
#                 'description': description,
#                 'transaction_id': payment_id,
#                 'payment_type': PAYMENT_TYPE.PAYMENT_TYPE_PAYPAL.value
#             }
#
#             icf_charge_obj = PaymentManager().get_payment_service(PAYMENT_TYPE.PAYMENT_TYPE_PAYPAL).make_payment(token, total_amount_with_tax_in_USD, currency, description)
#
#             if icf_charge_obj.paid:
#
#                 ICF_Payment_Transaction_Manager().update_paypal_trasaction_details(request_dict, icf_charge_obj)
#
#                 ICFPaymentLogger().log_featured_event_payment_details(request_dict_log, icf_charge_obj)
#                 is_offline = False
#                 IcfBillGenerator().generate_event_reciept(user, featured_event, productList, total_amount_with_tax_in_USD,
#                                                           entity_info, currency, VAT_USD, base_url, is_offline)
#
#                 return Response({"response_message": _("Transaction is successful."),
#                                  "amount_paid": icf_charge_obj.resp_amount_in_dollars
#                                  },
#                                 status=status.HTTP_200_OK)
#
#             else:
#
#                 ICF_Payment_Transaction_Manager().update_paypal_trasaction_details(request_dict, icf_charge_obj)
#
#                 ICFPaymentLogger().log_featured_event_payment_details(request_dict_log, icf_charge_obj)
#
#                 # send an email to FEATURED_EVENT_PAYMENT_FAILURE_NOTIFICATION_EMAIL  failure payments
#
#                 email_subject = str(app_settings.FEATURED_EVENT_PAYMENT_FAILURE_SUBJECT).format(featured_event.title),
#                 product_info_str = ""
#                 for product in productList:
#                     quantity = int(product['qty'])
#                     name = product['name']
#                     product_info_str.append(str(app_settings.PRODUCT_INFO_STR).format(name, quantity))
#
#                 payment_type = "Credit Card"
#
#                 featured_event_failed_transaction_log_file.info(
#                     "transaction failed for featured_event:{featured_event},\n entity_info:{entity_info},\n"
#                     "payment_type : {payment_type},\n while purchasing products:{products},"
#                     "\n participants:{participants},\n".format(featured_event=featured_event.title, entity_info=entity_info,
#                                                                payment_type=payment_type, products=product_info_str,
#                                                                participants=participants))
#
#                 email_body = str(app_settings.FEATURED_EVENT_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type, entity_info.get("entityName"), user.display_name, entity_info.get("entityEmail"),
#                                                                                                 entity_info.get("entityPhone"),product_info_str, entity_info.get("participants"),total_amount_with_tax_in_USD)
#                 msg = EmailMessage(subject=email_subject,
#                                    body=email_body,
#                                    to=[app_settings.FEATURED_EVENT_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
#                                    )
#                 msg.content_subtype = "html"
#                 msg.send()
#
#                 return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
#
#         except EventProduct.DoesNotExist as pdn:
#             logger.exception("Product not found.")
#             Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)
#         except FeaturedEventAndCategory.DoesNotExist as e:
#             logger.exception("FeaturedEventAndCategory not found.")
#             Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             logger.exception(e)
#             Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)


class GenerateInvoiceForPurchaseTicketsAPIView(CreateAPIView):

    serializer_class = OfflinePaymentInvoiceForTicketSerializer
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="Create invoice for a  Featured Event ticket"
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = self.request.user
            entityName = serializer.validated_data.get("entityName").lstrip().rstrip()
            entityEmail = serializer.validated_data.get("entityEmail").lstrip().rstrip()
            entityPhone = serializer.validated_data.get("entityPhone").lstrip().rstrip()
            name_of_representative = serializer.validated_data.get("name_of_representative").lstrip().rstrip()
            address = serializer.validated_data.get("address").lstrip().rstrip()
            participants = serializer.validated_data.get("participants").lstrip().rstrip()
            total_amount_with_tax_in_USD = float(serializer.validated_data.get("totalCost"))
            productList = serializer.validated_data.get("productList")
            featured_event_slug = serializer.validated_data.get("event_slug").lstrip().rstrip()
            currency = serializer.validated_data.get("currency").lstrip().rstrip()
            VAT_USD = float(serializer.validated_data.get("VAT"))
            featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)
            base_url = request.build_absolute_uri()
            is_offline = True

            productList = list(filter(None.__ne__, productList))


            entity_info = {
                "entityName": entityName,
                "entityEmail": entityEmail,
                "entityPhone": entityPhone,
                "name_of_representative": name_of_representative,
                "address": address,
                "participants": participants
            }

            if productList:

                IcfBillGenerator().generate_event_reciept(user, featured_event, productList, total_amount_with_tax_in_USD, entity_info, currency, VAT_USD, base_url, is_offline)

                return Response({"response_message": _("Invoice generation is successful."),
                                 "amount_paid": total_amount_with_tax_in_USD,
                                 },
                                status=status.HTTP_200_OK)
            else:

                return Response({"response_message": _("Could not generate invoice because the no product list is empty."),
                                 "amount_paid": None,
                                 },
                                status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(str(e))
            Response({"detail": _("Could not create participant.")}, status=status.HTTP_400_BAD_REQUEST)



class GetRelatedProductListView(APIView):

    @swagger_auto_schema(
        operation_summary="Retrieve all related Featured Event"
    )
    def get(self, request):
        category_name = request.GET.get('category')
        try:
            products = EventProduct.objects.filter(category__name=category_name)
        except Exception:
            products = []
        serialized = ProductSerializer(products, many=True)
        return Response(serialized.data)


# class GetCategoryDetailView(RetrieveAPIView):
#     queryset = FeaturedEventCategory.objects.all()
#     serializer_class = FeaturedEventsCategorySerializer
#     lookup_field = "slug"
#
#
# class FeaturedEventRelatedCategoriesListAPIView(ListAPIView):
#     serializer_class = FeaturedEventsCategorySerializer
#
#     def get_queryset(self):
#         featured_event_slug = self.kwargs.get('slug')
#         queryset = []
#         try:
#             featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)
#             # queryset = FeaturedEventAndCategory.objects.filter(featured_event=featured_event).values('category').distinct
#             id_values_queryset = FeaturedEventAndCategory.objects.filter(featured_event=featured_event).values_list('category', flat=True).distinct()
#             category_list = []
#             for value in id_values_queryset:
#                 category = FeaturedEventCategory.objects.get(id=value)
#                 category_list.append(category)
#             queryset = category_list
#         except FeaturedEvent.DoesNotExist as fen:
#             logger.exception(fen)
#         return queryset


class TermsAndConditionsByFeaturedEventAPIView(RetrieveAPIView):
    serializer_class = TermsAndConditionsSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="RetrieveTerms and condition of Featured Event"
    )
    def get_object(self):
        featured_event_slug = self.kwargs.get('slug')
        try:
            featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)
            return featured_event.terms_and_conditions
        except FeaturedEvent.DoesNotExist as fne:
            raise ICFException("Featured event does not exist")

    @swagger_auto_schema(
        operation_summary="RetrieveTerms and condition of Featured Event"
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(serializer.data)


class EmailFailedEventsPaypalTrasactionsAPIView(APIView):
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            user = request.user
            entityName = request.data.get("entityName").lstrip().rstrip()
            entityEmail = request.data.get("entityEmail").lstrip().rstrip()
            entityPhone = request.data.get("entityPhone").lstrip().rstrip()
            name_of_representative = request.data.get("name_of_representative").lstrip().rstrip()
            address = request.data.get("address").lstrip().rstrip()
            participants = request.data.get("participants").lstrip().rstrip()
            totalCost = request.data.get("totalCost")
            productList = request.data.get("productList")
            # token = request.data.get("paymentToken").lstrip().rstrip()
            # payment_id = request.data.get("paymentID").lstrip().rstrip()
            featured_event_slug = request.data.get("event_slug").lstrip().rstrip()
            # currency = request.data.get("currency").lstrip().rstrip()
            # VAT_USD = request.data.get("VAT")
            productList = list(filter(None.__ne__, productList))

            featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)
            # description = "Featured event participation"

            entity_info = {
                "entityName": entityName,
                "entityEmail": entityEmail,
                "entityPhone": entityPhone,
                "name_of_representative": name_of_representative,
                "address": address,
                "participants": participants
            }

            email_subject = str(app_settings.FEATURED_EVENT_PAYMENT_FAILURE_SUBJECT).format(featured_event.title),
            product_info_str = ""
            for product in productList:
                quantity = int(product['qty'])
                name = product['name']
                product_info_str.append(str(app_settings.PRODUCT_INFO_STR).format(name, quantity))

            payment_type = "Paypal"

            featured_event_failed_transaction_log_file.info("transaction failed for featured_event:{featured_event},\n entity_info:{entity_info},\n "
                                                            "payment_type : {payment_type},\n while purchasing products:{products},"
                                                            "\n participants:{participants},\n".format(featured_event=featured_event.title, entity_info=entity_info,
                                                             payment_type=payment_type, products=product_info_str, participants=participants))

            email_body = str(app_settings.FEATURED_EVENT_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
                entity_info.get("entityName"),
                user.display_name, entity_info.get("entityEmail"), entity_info.get("entityPhone"), product_info_str,
                entity_info.get("participants"), totalCost)
            msg = EmailMessage(subject=email_subject,
                               body=email_body,
                               to=[app_settings.FEATURED_EVENT_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
                               )
            msg.content_subtype = "html"
            msg.send()

        except Exception as e:
            logger.exception(e)
            Response({"detail": _("Could not send email.")}, status=status.HTTP_400_BAD_REQUEST)


class FeaturedEventProductsListAPIView(ListAPIView):
    serializer_class = FeaturedEventsProductSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="List all Products for a Featured Event"
    )
    def get_queryset(self):
        try:
            featured_event_slug = self.kwargs.get('slug')
            featured_event = FeaturedEvent.objects.get(slug=featured_event_slug)

            featured_event_related_products_list = []
            featured_event_related_products_ids = FeaturedEventAndProduct.objects.\
                filter(featured_event=featured_event).values_list('product', flat=True)
            if featured_event_related_products_ids:
                for id in featured_event_related_products_ids:
                    event_product = EventProduct.objects.get(id=id)
                    # if event_product.expiry_date > timezone.now():
                    featured_event_related_products_list.append(event_product)
                queryset = featured_event_related_products_list
                return queryset
            else:
                Response({"detail": "FeaturedEvent does not have any products."}, status=status.HTTP_200_OK)
        except FeaturedEvent.DoesNotExist as fedn:
            logger.exception("FeaturedEvent does not exist.")
            Response({"detail": "FeaturedEvent does not exist."}, status=status.HTTP_400_BAD_REQUEST)


def payment_form(request):
    context = {"stripe_key": settings.STRIPE_PUBLIC_KEY}
    return render(request, "payments\checkout.html", context)





