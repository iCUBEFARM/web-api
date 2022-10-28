import os
import ssl
from datetime import datetime, timedelta
from urllib import request

import stripe
from django.core.mail import EmailMessage
from django.template.loader import get_template
from icf_generic.models import Type
from rest_framework import status
from rest_framework.response import Response
#from weasyprint import HTML

from icf import settings
from icf.settings import MEDIA_ROOT
from icf_orders import app_settings
from icf_orders.app_settings import PURCHASE_CREDITS
from icf_orders.models import ICFPaymentTransaction, PaymentType, PaymentStatus, AvailableBalance, CreditHistory, \
    CreditAction, CountryTax, CreditInvoices, CreditDistribution, Product
from icf_entity.models import Entity
from icf_featuredevents.models import Participant
from icf_generic.Exceptions import ICFException
from icf_messages.manager import ICFNotificationManager
from django.utils.translation import ugettext_lazy as _
from icf_featuredevents import app_settings as featured_event_app_settings


import logging

logger = logging.getLogger("icf.integrations.payment")


def AssignCreditsForDefaultApp():
    app = Type.objects.get(name='job')
    CreditDistribution.objects.get_or_create(app=app)


class PaymentByStripe:
    def __init__(self, user, entity, no_of_credits, token, total_amount, currency, description, base_url):
        self.api_key = settings.STRIPE_SECRET_KEY
        self.user = user
        self.entity = entity
        self.no_of_credits = no_of_credits
        self.token = token
        self.total_amount = total_amount
        self.currency = currency
        self.description = description
        self.base_url = base_url
        self.total_amount_in_USD = (self.total_amount / 100)

    def make_payment(self):
        # print("hello person")
        stripe.api_key = self.api_key
        icf_payment_transaction = ICFPaymentTransaction()

        try:
            # total_amount_in_USD = (self.total_amount / 100)
            country_tax = CountryTax.objects.get(country=self.entity.address.city.state.country)
            VAT_CENTS = self.total_amount * (country_tax.percentage / 100)
            total_amount_with_tax = round(self.total_amount + VAT_CENTS)
            VAT_USD = (VAT_CENTS / 100)

        except CountryTax.DoesNotExist:
            country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
            VAT_CENTS = round(self.total_amount * (country_tax.percentage / 100))
            total_amount_with_tax = round(self.total_amount + VAT_CENTS)
            VAT_USD = (VAT_CENTS / 100)

        icf_payment_transaction.user = self.user
        icf_payment_transaction.entity = self.entity
        icf_payment_transaction.payment_type = PAYMENT_TYPE.PAYMENT_TYPE_STRIPE.value
        icf_payment_transaction.req_amount_in_cents = total_amount_with_tax
        icf_payment_transaction.req_amount_in_dollars = (total_amount_with_tax / 100)
        icf_payment_transaction.req_token = self.token
        icf_payment_transaction.req_desc = self.description
        icf_payment_transaction.save()

        try:
            charge = stripe.Charge.create(
                amount=total_amount_with_tax,
                currency=self.currency,
                source=self.token,
                description=self.description

            )

            if charge.paid:                         # 'paid' is a boolean field of Charge object  if it is true then payment is Successful
                try:
                    # create  new record in AvailableBalance Table and CreditHistory Table to the user for this entity
                    try:
                        action = CreditAction.objects.get(action=PURCHASE_CREDITS)
                    except CreditAction.DoesNotExist:
                        raise ICFException(_("Invalid action, please check and try again."),
                                           status_code=status.HTTP_400_BAD_REQUEST)


                    CreditHistory.objects.create(entity=self.entity, user=self.user, available_credits=self.no_of_credits, action=action)

                    try:
                        # entity_balance = AvailableBalance.objects.get(entity=self.entity, user=self.user)
                        entity_balance = AvailableBalance.objects.get(entity=self.entity)
                        total_balance = entity_balance.available_credits + self.no_of_credits
                        entity_balance.available_credits = total_balance
                        entity_balance.save(update_fields=['available_credits'])
                    except AvailableBalance.DoesNotExist as dne:
                        entity_balance = AvailableBalance.objects.create(entity=self.entity, user=self.user, available_credits=self.no_of_credits)

                    icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
                    icf_payment_transaction_update.resp_amount_in_cents = charge.amount
                    icf_payment_transaction_update.resp_amount_in_dollars = (charge.amount / 100)
                    icf_payment_transaction_update.resp_date = datetime.now()
                    icf_payment_transaction_update.resp_status = Payment_Status.SUCCESS.value
                    icf_payment_transaction_update.resp_error_code = None
                    icf_payment_transaction_update.resp_error_details = None
                    icf_payment_transaction_update.resp_transaction_id = charge.balance_transaction
                    icf_payment_transaction_update.resp_currency = charge.currency
                    icf_payment_transaction_update.resp_failure_code = charge.failure_code
                    icf_payment_transaction_update.resp_failure_message = None
                    icf_payment_transaction_update.save()

                    IcfBillGenerator().generate_bill(self.user, self.entity, self.no_of_credits, self.total_amount_in_USD, self.currency, VAT_USD, icf_payment_transaction_update.resp_amount_in_dollars, self.base_url)

                    logger.info("Payment Successful  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                                "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                                " req_token : {req_token},\n req_desc : {req_desc},\n"
                                "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                                "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                                "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                                "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                                "resp_failure_message : {resp_failure_message},\n"
                                "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                          entity=icf_payment_transaction.entity,
                                                          payment_type=icf_payment_transaction.payment_type,
                                                          req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                          req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                          req_token=icf_payment_transaction.req_token,
                                                          req_desc=icf_payment_transaction.req_desc,
                                                          resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                          resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                          resp_date=icf_payment_transaction_update.resp_date,
                                                          resp_status=icf_payment_transaction_update.resp_status,
                                                          resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                          resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                          resp_currency=icf_payment_transaction_update.resp_currency,
                                                          resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                          resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                          resp_error_details=icf_payment_transaction_update.resp_error_details
                                                        ))
                    return Response({"response_message": _("Transaction is successful."),
                                     "amount_paid": (charge.amount / 100),
                                     "available_credits": entity_balance.available_credits,
                                     "no_of_credits": self.no_of_credits
                                     },
                                    status=status.HTTP_200_OK)

                    # return Response({"detail": "Successfully paid"}, status=status.HTTP_200_OK)
                except ICFPaymentTransaction.DoesNotExist as tne:
                    # return Response({"detail": _("ICFPaymentTransaction object does not exist.")}, status=status.HTTP_400_BAD_REQUEST)
                    return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
                except AvailableBalance.DoesNotExist as ane:
                    return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
                    # return Response({"detail": _("AvailableBalance object does not exist.")}, status=status.HTTP_400_BAD_REQUEST)
            # The payment was successfully processed, the user's card was charged.

        except stripe.error.CardError as ce:
            # return False, ce

            # Since it's a decline, stripe.error.CardError will be caught
            body = ce.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))

            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.RateLimitError as re:
            # Too many requests made to the API too quickly
            body = re.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))

            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=re.http_status)
            # return Response({"detail": "Rate Limit Error"}, status=re.http_status)

        except stripe.error.InvalidRequestError as ie:
            body = ie.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))



            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=ie.http_status)
            # return Response({"detail": "Invalid Request Error"}, status=ie.http_status)

        except stripe.error.AuthenticationError as ae:
            body = ae.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))

            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=ae.http_status)
            # return Response({"detail": "Authentication Error"}, status=ae.http_status)
        except stripe.error.APIConnectionError as ape:
            body = ape.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=ape.http_status)
            # return Response({"detail": "API Connection Error"}, status=ape.http_status)

        except stripe.error.StripeError as se:
            # Display a very generic error to the user, and maybe send
            body = se.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=se.http_status)
            # return Response({"detail": "Stripe Error"}, status=se.http_status)

        except Exception as e:
            # body = e.json_body
            # err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = None
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = None
            icf_payment_transaction_update.resp_failure_code = None
            icf_payment_transaction_update.resp_failure_message = str(e)
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

####################################################################################################


class PaymentByStripeFeaturedEvent:
    def __init__(self, user, featured_event, productList, token, total_amount, currency, description, base_url, VAT_USD, entity_info):
        self.api_key = settings.STRIPE_SECRET_KEY
        self.user = user
        self.featured_event = featured_event
        self.productList = productList
        self.token = token
        self.total_amount = total_amount
        self.currency = currency
        self.description = description
        self.base_url = base_url
        self.total_amount_in_USD = (self.total_amount / 100)
        self.VAT_USD = VAT_USD
        self.entity_info = entity_info
        self.is_offline = False

    def make_payment_for_featured_event_participation(self):
        # print("hello person")
        stripe.api_key = self.api_key
        icf_payment_transaction = ICFPaymentTransaction()

            # country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
            # VAT_CENTS = round(self.total_amount * (country_tax.percentage / 100))
            # total_amount_with_tax = round(self.total_amount + VAT_CENTS)
        VAT_USD = self.VAT_USD
        icf_payment_transaction.user = self.user
        icf_payment_transaction.entity = None
        icf_payment_transaction.payment_type = PAYMENT_TYPE.PAYMENT_TYPE_STRIPE.value
        icf_payment_transaction.req_amount_in_cents = round(self.total_amount)
        icf_payment_transaction.req_amount_in_dollars = (self.total_amount / 100)
        icf_payment_transaction.req_date = datetime.now()
        icf_payment_transaction.req_token = self.token
        icf_payment_transaction.req_desc = self.description
        icf_payment_transaction.save()

        try:
            charge = stripe.Charge.create(
                amount=icf_payment_transaction.req_amount_in_cents,
                currency=self.currency,
                source=self.token,
                description=self.description

            )

            if charge.paid:  # 'paid' is a boolean field of Charge object  if it is true then payment is Successful
                try:
                    icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
                    icf_payment_transaction_update.resp_amount_in_cents = charge.amount
                    icf_payment_transaction_update.resp_amount_in_dollars = (charge.amount / 100)
                    icf_payment_transaction_update.resp_date = datetime.now()
                    icf_payment_transaction_update.resp_status = Payment_Status.SUCCESS.value
                    icf_payment_transaction_update.resp_error_code = None
                    icf_payment_transaction_update.resp_error_details = None
                    icf_payment_transaction_update.resp_transaction_id = charge.balance_transaction
                    icf_payment_transaction_update.resp_currency = charge.currency
                    icf_payment_transaction_update.resp_failure_code = charge.failure_code
                    icf_payment_transaction_update.resp_failure_message = None
                    icf_payment_transaction_update.save()

                    IcfBillGenerator().generate_event_reciept(self.user, self.featured_event, self.productList,
                                                     self.total_amount_in_USD, self.entity_info, self.currency, self.VAT_USD, self.base_url, self.is_offline)

                    logger.info(
                        "Payment Successful  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
                    return Response({"response_message": _("Transaction is successful."),
                                     "amount_paid": (charge.amount / 100),
                                     },
                                    status=status.HTTP_200_OK)

                except ICFPaymentTransaction.DoesNotExist as tne:
                    return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
                except AvailableBalance.DoesNotExist as ane:
                    return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # The payment was successfully processed, the user's card was charged.

        except stripe.error.CardError as ce:
            # return False, ce

            # Since it's a decline, stripe.error.CardError will be caught
            body = ce.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))

            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.RateLimitError as re:
            # Too many requests made to the API too quickly
            body = re.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))

            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.InvalidRequestError as ie:
            body = ie.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))





            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=ie.http_status)
            # return Response({"detail": "Invalid Request Error"}, status=ie.http_status)

        except stripe.error.AuthenticationError as ae:
            body = ae.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))

            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=ae.http_status)
            # return Response({"detail": "Authentication Error"}, status=ae.http_status)
        except stripe.error.APIConnectionError as ape:
            body = ape.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n  payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=ape.http_status)
            # return Response({"detail": "API Connection Error"}, status=ape.http_status)

        except stripe.error.StripeError as se:
            # Display a very generic error to the user, and maybe send
            body = se.json_body
            err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = err.get('code')
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = err
            icf_payment_transaction_update.resp_failure_code = err.get('code')
            icf_payment_transaction_update.resp_failure_message = err.get('message')
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": err.get('message')}, status=se.http_status)
            # return Response({"detail": "Stripe Error"}, status=se.http_status)

        except Exception as e:
            # body = e.json_body
            # err = body.get('error', {})

            icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=self.token)
            icf_payment_transaction_update.resp_amount_in_cents = None
            icf_payment_transaction_update.resp_amount_in_dollars = None
            icf_payment_transaction_update.resp_date = datetime.now()
            icf_payment_transaction_update.resp_status = Payment_Status.FAILURE.value
            icf_payment_transaction_update.resp_error_code = None
            icf_payment_transaction_update.resp_transaction_id = None
            icf_payment_transaction_update.resp_currency = None
            icf_payment_transaction_update.resp_error_details = None
            icf_payment_transaction_update.resp_failure_code = None
            icf_payment_transaction_update.resp_failure_message = str(e)
            icf_payment_transaction_update.save()

            logger.info("Payment failed  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction_update.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction_update.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction_update.resp_date,
                                                                            resp_status=icf_payment_transaction_update.resp_status,
                                                                            resp_error_code=icf_payment_transaction_update.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction_update.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction_update.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction_update.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction_update.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction_update.resp_error_details
                                                                            ))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


####################################################################################################


class PaymentByPayPal:
    def __init__(self, user, entity, no_of_credits, token, total_amount, currency, description, base_url, payment_id, total_amount_with_tax, VAT_USD):
        self.user = user
        self.entity = entity
        self.no_of_credits = no_of_credits
        self.token = token
        self.total_amount = total_amount
        self.total_amount_with_tax = total_amount_with_tax
        self.currency = currency
        self.description = description
        self.base_url = base_url
        self.payment_id = payment_id
        self.VAT_USD = VAT_USD

    def make_payment(self):
        try:
            icf_payment_transaction = ICFPaymentTransaction()
            icf_payment_transaction.user = self.user
            icf_payment_transaction.entity = self.entity
            icf_payment_transaction.payment_type = PAYMENT_TYPE.PAYMENT_TYPE_PAYPAL.value
            icf_payment_transaction.req_date = datetime.now()
            icf_payment_transaction.req_token = self.token
            icf_payment_transaction.req_desc = self.description
            icf_payment_transaction.req_amount_in_cents = None
            icf_payment_transaction.req_amount_in_dollars = self.total_amount_with_tax

            icf_payment_transaction.resp_date = datetime.now()
            icf_payment_transaction.resp_amount_in_cents = None
            icf_payment_transaction.resp_amount_in_dollars = self.total_amount_with_tax
            icf_payment_transaction.resp_status = Payment_Status.SUCCESS.value
            icf_payment_transaction.resp_error_code = None
            icf_payment_transaction.resp_error_details = None
            icf_payment_transaction.resp_transaction_id = self.payment_id
            icf_payment_transaction.resp_currency = self.currency
            icf_payment_transaction.resp_failure_code = None
            icf_payment_transaction.resp_failure_message = None
            icf_payment_transaction.save()

            # create  new record in AvailableBalance Table and CreditHistory Table to the user for this entity
            try:
                action = CreditAction.objects.get(action=PURCHASE_CREDITS)
            except CreditAction.DoesNotExist as ce:
                # logger.error("transaction failed. reason : {reason}".format(reason=str(ce)))
                raise ICFException(_("Invalid action, please check and try again."),
                                   status_code=status.HTTP_400_BAD_REQUEST)

            CreditHistory.objects.create(entity=icf_payment_transaction.entity, user=icf_payment_transaction.user, available_credits=self.no_of_credits, action=action)

            try:
                # entity_balance = AvailableBalance.objects.get(entity=icf_payment_transaction.entity, user=icf_payment_transaction.user)
                entity_balance = AvailableBalance.objects.get(entity=icf_payment_transaction.entity)
                total_balance = entity_balance.available_credits + self.no_of_credits
                entity_balance.available_credits = total_balance
                entity_balance.save(update_fields=['available_credits'])
            except AvailableBalance.DoesNotExist as dne:
                entity_balance = AvailableBalance.objects.create(entity=icf_payment_transaction.entity, user=icf_payment_transaction.user,
                                                                 available_credits=self.no_of_credits)

            IcfBillGenerator().generate_bill(icf_payment_transaction.user, icf_payment_transaction.entity, self.no_of_credits, self.total_amount,
                                             self.currency, self.VAT_USD,
                                             self.total_amount_with_tax, self.base_url)

            logger.info("Payment Successful  - user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            entity=icf_payment_transaction.entity,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_cents=icf_payment_transaction.resp_amount_in_cents,
                                                                            resp_amount_in_dollars=icf_payment_transaction.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction.resp_date,
                                                                            resp_status=icf_payment_transaction.resp_status,
                                                                            resp_error_code=icf_payment_transaction.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction.resp_failure_message
                                                                            ))
            return Response({"response_message": _("Transaction is successful."),
                             "amount_paid": self.total_amount_with_tax,
                             "available_credits": entity_balance.available_credits,
                             "no_of_credits": self.no_of_credits
                             },
                            status=status.HTTP_200_OK)

        except Product.DoesNotExist as ce:
            logger.error("transaction failed. reason : {reason}".format(reason=str(ce)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error("Transaction failed. reason :{reason}".format(reason=str(e)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)


#####################################################################

class PaymentByPayPalFeaturedEvent:
    def __init__(self, user, featured_event, productList, token, total_amount, currency, description, base_url, payment_id, VAT_USD, entity_info):
        self.user = user
        self.featured_event = featured_event
        self.productList = productList
        self.token = token
        self.total_amount = total_amount
        # self.total_amount_with_tax = total_amount_with_tax
        self.currency = currency
        self.description = description
        self.base_url = base_url
        self.payment_id = payment_id
        self.VAT_USD = VAT_USD
        self.entity_info = entity_info
        self.is_offline = False

    def make_payment(self):
        try:
            icf_payment_transaction = ICFPaymentTransaction()
            icf_payment_transaction.user = self.user
            icf_payment_transaction.featured_event = self.featured_event
            icf_payment_transaction.payment_type = PAYMENT_TYPE.PAYMENT_TYPE_PAYPAL.value
            icf_payment_transaction.req_date = datetime.now()
            icf_payment_transaction.req_token = self.token
            icf_payment_transaction.req_desc = self.description
            icf_payment_transaction.req_amount_in_cents = None
            icf_payment_transaction.req_amount_in_dollars = self.total_amount

            icf_payment_transaction.resp_date = datetime.now()
            icf_payment_transaction.resp_amount_in_cents = None
            icf_payment_transaction.resp_amount_in_dollars = self.total_amount
            icf_payment_transaction.resp_status = Payment_Status.SUCCESS.value
            icf_payment_transaction.resp_error_code = None
            icf_payment_transaction.resp_error_details = None
            icf_payment_transaction.resp_transaction_id = self.payment_id
            icf_payment_transaction.resp_currency = self.currency
            icf_payment_transaction.resp_failure_code = None
            icf_payment_transaction.resp_failure_message = None
            icf_payment_transaction.save()

            IcfBillGenerator().generate_event_reciept(self.user, self.featured_event, self.productList, self.total_amount, self.entity_info,
                                             self.currency, self.VAT_USD, self.base_url, self.is_offline)

            logger.info("Payment Successful  - user : {user},\n payment_type : {payment_type},\n"
                        "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                        " req_token : {req_token},\n req_desc : {req_desc},\n"
                        "resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                        "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                        "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                        "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                        "resp_failure_message : {resp_failure_message},\n"
                        "resp_error_details : {resp_error_details} ".format(user=icf_payment_transaction.user,
                                                                            payment_type=icf_payment_transaction.payment_type,
                                                                            req_amount_in_cents=icf_payment_transaction.req_amount_in_cents,
                                                                            req_amount_in_dollars=icf_payment_transaction.req_amount_in_dollars,
                                                                            req_token=icf_payment_transaction.req_token,
                                                                            req_desc=icf_payment_transaction.req_desc,
                                                                            resp_amount_in_dollars=icf_payment_transaction.resp_amount_in_dollars,
                                                                            resp_date=icf_payment_transaction.resp_date,
                                                                            resp_status=icf_payment_transaction.resp_status,
                                                                            resp_error_code=icf_payment_transaction.resp_error_code,
                                                                            resp_transaction_id=icf_payment_transaction.resp_transaction_id,
                                                                            resp_currency=icf_payment_transaction.resp_currency,
                                                                            resp_failure_code=icf_payment_transaction.resp_failure_code,
                                                                            resp_failure_message=icf_payment_transaction.resp_failure_message,
                                                                            resp_error_details=icf_payment_transaction.resp_failure_message
                                                                            ))
            return Response({"response_message": _("Transaction is successful."),
                             "amount_paid": self.total_amount,
                             },
                            status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Transaction failed. reason :{reason}".format(reason=str(e)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)


###########################################################################################################


class ICFPaymentManager:
    def get_payment_service(self, user, entity, no_of_credits, token, total_amount, currency, description, base_url):
        return PaymentByStripe(user, entity, no_of_credits, token, total_amount, currency, description, base_url)

    def get_paypal_payment_service(self, user, entity, no_of_credits, token, total_amount, currency, description, base_url, payment_id, total_amount_with_tax, VAT_USD):
        return PaymentByPayPal(user, entity, no_of_credits, token, total_amount, currency, description, base_url, payment_id, total_amount_with_tax, VAT_USD)

    def get_payment_service_featured_event(self, user, featured_event, productList, token, total_amount, currency, description, base_url, VAT_USD, entity_info):
        return PaymentByStripeFeaturedEvent(user, featured_event, productList, token, total_amount, currency, description, base_url, VAT_USD, entity_info)

    def get_payment_service_featured_event_paypal(self, user, featured_event, productList, token, total_amount, currency, description, base_url, payment_id, VAT_USD, entity_info):
        return PaymentByPayPalFeaturedEvent(user, featured_event, productList, token, total_amount, currency, description, base_url, payment_id, VAT_USD, entity_info)


class IcfBillGenerator:
    def generate_bill(self, user, entity, no_of_credits, total_amount_in_USD, currency, VAT, total_amount_with_tax, base_url):
        path = os.path.join(MEDIA_ROOT, "payment_receipt")
        filename = os.path.join(path, "{}_payment_receipt_{}.pdf".format(entity, 1))

        # icf_orders = validated_data.get('credits')
        # currency = getattr(validated_data, 'currency', 'USD').lower()
        try:
            cost_for_credit = Product.objects.get(product_type=Product.CREDIT,currency__name=currency)
            # unit_cost = (int(cost_for_credit.cost) / cost_for_credit.credits)
            # unit_credits = cost_for_credit.credits
            unit_cost = cost_for_credit.cost
            unit_credits = cost_for_credit.unit
        except Product.DoesNotExist as cdne:
            # return Response({"detail": cdne.message}, status=status.HTTP_400_BAD_REQUEST)
            raise Product.DoesNotExist

        template = get_template('credits/payment_receipt.html')
        context = {}
        invoice = {}
        # this_day = datetime.datetime.today()
        this_day = datetime.today()
        this_date = this_day.date
        invoice['date'] = this_date
        invoice['total_credits'] = no_of_credits
        invoice['cost'] = total_amount_in_USD
        invoice['unit_cost'] = unit_cost
        invoice['unit_credits'] = unit_credits
        # invoice['unit_credits'] = 1
        invoice['currency'] = currency
        # valid_till = datetime.today() + datetime.timedelta(days=30)
        valid_till = datetime.today() + timedelta(days=30)
        invoice['valid_till'] = valid_till.date
        invoice['VAT'] = VAT
        invoice['total_cost'] = total_amount_with_tax

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
        customer['email'] = user.email
        customer['contactperson'] = user.display_name

        context['customer'] = customer

        context['icube'] = app_settings.ICUBE_ADDRESS
        context['account'] = app_settings.ACCOUNT_DETAILS
        context['policy'] = app_settings.Non_Refund_Policy

        ssl._create_default_https_context = ssl._create_unverified_context
        html = template.render(context)
        try:
            # pdf_file = HTML(string=html, base_url=base_url).write_pdf(filename)
            pass
        except Exception as e:
            logger.error("Could not create payment bill reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create payment bill, please try again"),
                               status_code=status.HTTP_400_BAD_REQUEST)

        email_body = str(app_settings.PAYMENT_RECEIPT_EMAIL_BODY).format(user.display_name)

        msg = EmailMessage(subject=app_settings.PAYMENT_RECEIPT_SUBJECT,
                           body=email_body,
                           to=[user.email, ],
                           cc=[app_settings.PAYMENT_RECEIPT_EMAIL_CC, ])

        msg.attach('iCUBEFARM-Credits-Payment-Receipt.pdf', open(filename, 'rb').read(), 'application/pdf')
        msg.content_subtype = "html"
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('PAYMENT_BILL_NOTIFICATION')
        details = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL').format(user.display_name, message, entity.display_name)
        ICFNotificationManager.add_notification(user=user, message=message, details=details)

        # obj = CreditInvoices.objects.create(entity=entity, user=request.user, credits=icf_orders,
        #                                     invoice_num=inv_num)
        # obj.credits = icf_orders
        # obj.currency = currency
        # return obj

        ###############################################

    def generate_event_reciept(self, user, featured_event, productList, total_amount_in_USD, entity_info, currency, VAT, base_url, is_offline):
        path = os.path.join(MEDIA_ROOT, "featured_event")
        filename = os.path.join(path, "{}_featured_event_receipt_{}.pdf".format(featured_event.title, 1))

        template = get_template('featured_events/event_participation_reciept.html')
        context = {}
        invoice = {}
        this_day = datetime.today()
        this_date = this_day.date
        invoice['date'] = this_date
        invoice['cost'] = total_amount_in_USD
        invoice['currency'] = currency
        invoice['VAT'] = VAT
        invoice['total_cost'] = total_amount_in_USD
        invoice['productList'] = productList
        invoice['entity_info'] = entity_info
        invoice['featured_event'] = featured_event
        invoice['is_offline'] = is_offline
        # invoice['bank_details'] = app_settings.ACCOUNT_DETAILS
        context['featured_event_bank_details'] = featured_event_app_settings.BANK_DETAILS
        context['featured_event_details'] = featured_event_app_settings.FEATURED_EVENT_DETAILS
        context['product_info'] = featured_event_app_settings.PRODUCT_INFO
        invoice['sub_total'] = str(round(float(total_amount_in_USD) - float(VAT), 2))


        inv_num = 1
        try:
            inv_num += Participant.objects.filter(created__year=this_day.year).last().invoice_num
        except AttributeError as ae:
            pass

        invoice['number'] = inv_num
        context['invoice'] = invoice
        context['icube'] = app_settings.ICUBE_ADDRESS
        context['fe_account'] = featured_event_app_settings.FEATURED_EVENT_ACCOUNT_DETAILS
        context['policy'] = app_settings.Non_Refund_Policy
        context['exchange_rate'] = app_settings.EXCHANGE_RATE

        ssl._create_default_https_context = ssl._create_unverified_context
        html = template.render(context)
        try:
            # pdf_file = HTML(string=html, base_url=base_url).write_pdf(filename)
            pass
        except Exception as e:
            logger.error("Could not create payment bill reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create payment bill, please try again"),
                               status_code=status.HTTP_400_BAD_REQUEST)

        email_body = str(featured_event_app_settings.FEATURED_EVENT_RECEIPT_EMAIL_BODY).format(user.display_name, featured_event.title)

        msg = EmailMessage(subject=featured_event_app_settings.FEATURED_EVENT_RECEIPT_SUBJECT,
                           body=email_body,
                           to=[user.email, ],
                           cc=featured_event_app_settings.FEATURED_EVENT_RECEIPT_EMAIL_CC)

        msg.attach('iCUBEFARM-Event-Participation-Payment-Receipt.pdf', open(filename, 'rb').read(), 'application/pdf')
        msg.content_subtype = "html"
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('PAYMENT_BILL_NOTIFICATION')
        # details = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL').format(user.display_name, message, entity.display_name)
        # ICFNotificationManager.add_notification(user=user, message=message, details=details)






