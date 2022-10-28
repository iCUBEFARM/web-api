import os
import ssl
from datetime import datetime, timedelta

import stripe
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.template.loader import get_template
from rest_framework import status
from weasyprint import HTML
from rest_framework.response import Response

from icf import settings
from icf.settings import MEDIA_ROOT
from icf_orders import app_settings
from icf_orders.models import ICFPaymentTransaction, PaymentType, PaymentStatus, CreditInvoices, Product, \
    SubscriptionPlan
from icf_featuredevents.models import Participant
from icf_generic.Exceptions import ICFException
from icf_messages.manager import ICFNotificationManager
from django.utils.translation import ugettext_lazy as _
from icf_featuredevents import app_settings as featured_event_app_settings
from django.utils.safestring import mark_safe


import logging

payment_logger = logging.getLogger("icf.integrations.payment")


class ICFCharge:
    def __init__(self, paid=None, resp_amount_in_cents=None, resp_amount_in_dollars=None, resp_date=None, resp_status=None, resp_error_code=None, resp_error_details=None, resp_transaction_id=None, resp_currency=None, resp_failure_code=None, resp_failure_message=None):
        self.paid = paid
        self.resp_amount_in_cents = resp_amount_in_cents
        self.resp_amount_in_dollars = resp_amount_in_dollars
        self.resp_date = resp_date
        self.resp_status = resp_status
        self.resp_error_code = resp_error_code
        self.resp_error_details = resp_error_details
        self.resp_transaction_id = resp_transaction_id
        self.resp_currency = resp_currency
        self.resp_failure_code = resp_failure_code
        self.resp_failure_message = resp_failure_message


class PaymentByStripe:

    def make_payment(self, token, total_amount_with_tax_in_cents, currency, description):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        token = token
        total_amount_with_tax_in_cents = total_amount_with_tax_in_cents
        currency = currency
        description = description
        icf_charge_obj = ICFCharge()

        try:
            charge = stripe.Charge.create(
                amount=total_amount_with_tax_in_cents,
                currency=currency,
                source=token,
                description=description

            )

            if charge.paid:  # 'paid' is a boolean field of Charge object  if it is true then payment is Successful

                icf_charge_obj.paid = charge.paid
                icf_charge_obj.resp_error_details = None
                icf_charge_obj.resp_amount_in_cents = charge.amount
                icf_charge_obj.resp_amount_in_dollars = (charge.amount / 100)
                icf_charge_obj.resp_date = datetime.now()
                icf_charge_obj.resp_status = PaymentStatus.SUCCESS
                icf_charge_obj.resp_error_code = None
                icf_charge_obj.resp_transaction_id = charge.balance_transaction
                icf_charge_obj.resp_currency = charge.currency
                icf_charge_obj.resp_failure_code = charge.failure_code
                icf_charge_obj.resp_failure_message = None
                return icf_charge_obj

        except stripe.error.CardError as ce:
            # return False, ce
            # Since it's a decline, stripe.error.CardError will be caught
            body = ce.json_body
            err = body.get('error', {})

            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = err.get('code')
            icf_charge_obj.resp_error_details = err
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_failure_code = err.get('code')
            icf_charge_obj.resp_failure_message = err.get('message')
            return icf_charge_obj

        except stripe.error.RateLimitError as re:
            # Too many requests made to the API too quickly
            body = re.json_body
            err = body.get('error', {})

            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = err.get('code')
            icf_charge_obj.resp_error_details = err
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_failure_code = err.get('code')
            icf_charge_obj.resp_failure_message = err.get('message')
            return icf_charge_obj

        except stripe.error.InvalidRequestError as ie:

            body = ie.json_body
            err = body.get('error', {})


            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = err.get('code')
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_error_details = err
            icf_charge_obj.resp_failure_code = err.get('code')
            icf_charge_obj.resp_failure_message = err.get('message')
            return icf_charge_obj

        except stripe.error.AuthenticationError as ae:

            body = ae.json_body
            err = body.get('error', {})


            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = err.get('code')
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_error_details = err
            icf_charge_obj.resp_failure_code = err.get('code')
            icf_charge_obj.resp_failure_message = err.get('message')
            return icf_charge_obj

        except stripe.error.APIConnectionError as ape:

            body = ape.json_body
            err = body.get('error', {})


            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = err.get('code')
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_error_details = err
            icf_charge_obj.resp_failure_code = err.get('code')
            icf_charge_obj.resp_failure_message = err.get('message')
            return icf_charge_obj

        except stripe.error.StripeError as se:
            # Display a very generic error to the user, and maybe send
            body = se.json_body
            err = body.get('error', {})

            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = err.get('code')
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_error_details = err
            icf_charge_obj.resp_failure_code = err.get('code')
            icf_charge_obj.resp_failure_message = err.get('message')
            return icf_charge_obj

        except Exception as e:

            body = str(e)
            # err = body.get('error', {})

            icf_charge_obj.paid = False
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = None
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.FAILURE
            icf_charge_obj.resp_error_code = None
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = None
            icf_charge_obj.resp_error_details = None
            icf_charge_obj.resp_failure_code = None
            icf_charge_obj.resp_failure_message = str(e)
            return icf_charge_obj


############################################################################################################

class PaymentByPayPal:

    def make_payment(self, token, total_amount_with_tax_in_USD, currency, description):
        try:
            # Construct the charge object and return back to the calling function

            token = token   # is the payment_id got from front end once the payment is succesful
            total_amount_with_tax_in_USD = total_amount_with_tax_in_USD
            currency = currency
            description = description
            icf_charge_obj = ICFCharge()

            icf_charge_obj.paid = True      # because payment with paypal is  successful in the front end itself
            icf_charge_obj.resp_error_details = None
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = total_amount_with_tax_in_USD
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.SUCCESS
            icf_charge_obj.resp_error_code = None
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = currency
            icf_charge_obj.resp_failure_code = None
            icf_charge_obj.resp_failure_message = None
            return icf_charge_obj

        except Product.DoesNotExist as ce:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(ce)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            payment_logger.error("Transaction failed. reason :{reason}".format(reason=str(e)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)


#####################################################################


class PaymentByBankDeposit:

    def make_payment(self, total_amount_with_tax_in_USD, currency, description):
        try:
            # Construct the charge object and return back to the calling function

            # paymeny_id = offline_payment_id  # is the payment_id got from front end once the payment is succesful
            total_amount_with_tax_in_USD = total_amount_with_tax_in_USD
            currency = currency
            description = description
            icf_charge_obj = ICFCharge()

            icf_charge_obj.paid = True  # because payment is successful in the front end itself
            icf_charge_obj.resp_error_details = None
            icf_charge_obj.resp_amount_in_cents = None
            icf_charge_obj.resp_amount_in_dollars = total_amount_with_tax_in_USD
            icf_charge_obj.resp_date = datetime.now()
            icf_charge_obj.resp_status = PaymentStatus.SUCCESS
            icf_charge_obj.resp_error_code = None
            icf_charge_obj.resp_transaction_id = None
            icf_charge_obj.resp_currency = currency
            icf_charge_obj.resp_failure_code = None
            icf_charge_obj.resp_failure_message = None
            return icf_charge_obj

        except Product.DoesNotExist as ce:
            payment_logger.error("transaction failed. reason : {reason}".format(reason=str(ce)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            payment_logger.error("Transaction failed. reason :{reason}".format(reason=str(e)))
            return Response({"detail": _("Transaction failed.")}, status=status.HTTP_400_BAD_REQUEST)


#####################################################################


class ICFPaymentLogger:

    def log_stripe_payment_details(self, request_dict, icf_charge_obj):
        payment_logger.info(" is payment successful :{payment_status},\n user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                    "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                    " req_token : {req_token},\n req_desc : {req_desc},\n"
                    "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                    "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                    "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                    "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                    "resp_failure_message : {resp_failure_message},\n"
                    "resp_error_details : {resp_error_details}".format(
                                                                        payment_status=icf_charge_obj.paid,
                                                                        user=request_dict['user'],
                                                                        entity=request_dict['entity'],
                                                                        payment_type=request_dict['payment_type'],
                                                                        req_amount_in_cents=request_dict['total_amount_with_tax_in_cents'],
                                                                        req_amount_in_dollars=request_dict['total_amount_with_tax_in_USD'],
                                                                        req_token=request_dict['token'],
                                                                        req_desc=request_dict['description'],
                                                                        resp_amount_in_cents=icf_charge_obj.resp_amount_in_cents,
                                                                        resp_amount_in_dollars=icf_charge_obj.resp_amount_in_dollars,
                                                                        resp_date=icf_charge_obj.resp_date,
                                                                        resp_status=icf_charge_obj.resp_status,
                                                                        resp_error_code=icf_charge_obj.resp_error_code,
                                                                        resp_transaction_id=icf_charge_obj.resp_transaction_id,
                                                                        resp_currency=icf_charge_obj.resp_currency,
                                                                        resp_failure_code=icf_charge_obj.resp_failure_code,
                                                                        resp_failure_message=icf_charge_obj.resp_failure_message,
                                                                        resp_error_details=icf_charge_obj.resp_error_details
                                                                        ))


    def log_paypal_payment_details(self, request_dict, icf_charge_obj):
        payment_logger.info(" is payment successful :{payment_status},\n user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
                    "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
                    " req_token : {req_token},\n req_desc : {req_desc},\n"
                    "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
                    "resp_date : {resp_date},\n resp_status : {resp_status},\n"
                    "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
                    "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
                    "resp_failure_message : {resp_failure_message},\n"
                    "resp_error_details : {resp_error_details}".format(
                                                                        payment_status=icf_charge_obj.paid,
                                                                        user=request_dict['user'],
                                                                        entity=request_dict['entity'],
                                                                        payment_type=request_dict['payment_type'],
                                                                        req_amount_in_cents=request_dict['total_amount_with_tax_in_cents'],
                                                                        req_amount_in_dollars=request_dict['total_amount_with_tax_in_USD'],
                                                                        req_token=request_dict['token'],
                                                                        req_desc=request_dict['description'],
                                                                        resp_amount_in_cents=icf_charge_obj.resp_amount_in_cents,
                                                                        resp_amount_in_dollars=icf_charge_obj.resp_amount_in_dollars,
                                                                        resp_date=icf_charge_obj.resp_date,
                                                                        resp_status=icf_charge_obj.resp_status,
                                                                        resp_error_code=icf_charge_obj.resp_error_code,
                                                                        resp_transaction_id=request_dict['transaction_id'],
                                                                        resp_currency=icf_charge_obj.resp_currency,
                                                                        resp_failure_code=icf_charge_obj.resp_failure_code,
                                                                        resp_failure_message=icf_charge_obj.resp_failure_message,
                                                                        resp_error_details=icf_charge_obj.resp_error_details
                                                                        ))


    def log_offline_payment_trasaction_details(self, request_dict, icf_charge_obj):
        payment_logger.info(
            " is payment successful :{payment_status},\n user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
            "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
            " req_token : {req_token},\n req_desc : {req_desc},\n"
            "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
            "resp_date : {resp_date},\n resp_status : {resp_status},\n"
            "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
            "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
            "resp_failure_message : {resp_failure_message},\n"
            "resp_error_details : {resp_error_details}".format(
                payment_status=icf_charge_obj.paid,
                user=request_dict['user'],
                entity=request_dict['entity'],
                payment_type=request_dict['payment_type'],
                req_amount_in_cents=request_dict['total_amount_with_tax_in_cents'],
                req_amount_in_dollars=request_dict['total_amount_with_tax_in_USD'],
                req_token=request_dict['token'],
                req_desc=request_dict['description'],
                resp_amount_in_cents=icf_charge_obj.resp_amount_in_cents,
                resp_amount_in_dollars=icf_charge_obj.resp_amount_in_dollars,
                resp_date=icf_charge_obj.resp_date,
                resp_status=icf_charge_obj.resp_status,
                resp_error_code=icf_charge_obj.resp_error_code,
                resp_transaction_id=icf_charge_obj.resp_transaction_id,
                resp_currency=icf_charge_obj.resp_currency,
                resp_failure_code=icf_charge_obj.resp_failure_code,
                resp_failure_message=icf_charge_obj.resp_failure_message,
                resp_error_details=icf_charge_obj.resp_error_details
            ))


    def log_featured_event_payment_details(self, request_dict_log, icf_charge_obj):
        payment_logger.info(
            " is payment successful :{payment_status},\n user : {user},\n entity: {entity_info},\n payment_type : {payment_type},\n"
            "req_amount_in_cents : {req_amount_in_cents},\n req_amount_in_dollars : {req_amount_in_dollars},\n"
            " req_token : {req_token},\n req_desc : {req_desc},\n"
            "resp_amount_in_cents : {resp_amount_in_cents},\n resp_amount_in_dollars : {resp_amount_in_dollars},\n"
            "resp_date : {resp_date},\n resp_status : {resp_status},\n"
            "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
            "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
            "resp_failure_message : {resp_failure_message},\n"
            "resp_error_details : {resp_error_details}".format(
                payment_status=icf_charge_obj.paid,
                user=request_dict_log['user'],
                entity_info=request_dict_log['entity_info'],
                payment_type=request_dict_log['payment_type'],
                req_amount_in_cents=request_dict_log['total_amount_with_tax_in_cents'],
                req_amount_in_dollars=request_dict_log['total_amount_with_tax_in_USD'],
                req_token=request_dict_log['token'],
                req_desc=request_dict_log['description'],
                resp_amount_in_cents=icf_charge_obj.resp_amount_in_cents,
                resp_amount_in_dollars=icf_charge_obj.resp_amount_in_dollars,
                resp_date=icf_charge_obj.resp_date,
                resp_status=icf_charge_obj.resp_status,
                resp_error_code=icf_charge_obj.resp_error_code,
                resp_transaction_id=request_dict_log['transaction_id'],
                resp_currency=icf_charge_obj.resp_currency,
                resp_failure_code=icf_charge_obj.resp_failure_code,
                resp_failure_message=icf_charge_obj.resp_failure_message,
                resp_error_details=icf_charge_obj.resp_error_details
            ))


    def log_credit_payment_using_stripe_details(self ,request_dict_credit, icf_charge_obj):
        payment_logger.info(
            " is payment successful for credits  :{payment_status},\n user : {user},\n entity: {entity},\n payment_type : {payment_type},\n"
            "req_amount_in_dollars : {req_amount_in_dollars},\n"
            "req_token : {req_token},\n req_desc : {req_desc},\n"
            "resp_amount_in_dollars : {resp_amount_in_dollars},\n"
            "resp_date : {resp_date},\n resp_status : {resp_status},\n"
            "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
            "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
            "resp_failure_message : {resp_failure_message},\n"
            "resp_error_details : {resp_error_details}".format(
                payment_status=icf_charge_obj.paid,
                user=request_dict_credit['user'],
                entity=request_dict_credit['entity'],
                payment_type=request_dict_credit['payment_type'],
                req_amount_in_dollars=request_dict_credit['total_amount_with_tax_in_USD'],
                req_token=request_dict_credit['token'],
                req_desc=request_dict_credit['description'],
                resp_amount_in_dollars=icf_charge_obj.resp_amount_in_dollars,
                resp_date=icf_charge_obj.resp_date,
                resp_status=icf_charge_obj.resp_status,
                resp_error_code=icf_charge_obj.resp_error_code,
                resp_transaction_id=icf_charge_obj.resp_transaction_id,
                resp_currency=icf_charge_obj.resp_currency,
                resp_failure_code=icf_charge_obj.resp_failure_code,
                resp_failure_message=icf_charge_obj.resp_failure_message,
                resp_error_details=icf_charge_obj.resp_error_details
            ))

    def log_all_product_payment_details(self, update_transaction_dict):
        payment_logger.info(
            " is payment successful for credits  :{payment_status},\n user : {user},\n"
            " entity: {entity},\n payment_type : {payment_type},\n req_date : {req_date},\n"
            "req_amount_in_dollars : {req_amount_in_dollars},\n"
            "req_token : {req_token},\n req_desc : {req_desc},\n"
            "resp_amount_in_dollars : {resp_amount_in_dollars},\n"
            "resp_date : {resp_date},\n resp_status : {resp_status},\n"
            "resp_error_code : {resp_error_code},\n resp_transaction_id : {resp_transaction_id},\n"
            "resp_currency : {resp_currency},\n resp_failure_code : {resp_failure_code},\n"
            "resp_failure_message : {resp_failure_message},\n"
            "resp_error_details : {resp_error_details}".format(
                payment_status=update_transaction_dict.get('payment_status'),
                user=update_transaction_dict.get('user'),
                entity=update_transaction_dict.get('entity'),
                payment_type=update_transaction_dict.get('payment_type'),
                req_date=update_transaction_dict.get('req_date'),
                req_amount_in_dollars=update_transaction_dict.get('req_amount_in_dollars'),
                req_token=update_transaction_dict.get('req_token'),
                req_desc=update_transaction_dict.get('req_desc'),
                resp_amount_in_dollars=update_transaction_dict.get('resp_amount_in_dollars'),
                resp_date=update_transaction_dict.get('resp_date'),
                resp_status=update_transaction_dict.get('resp_status'),
                resp_error_code=update_transaction_dict.get('resp_error_code'),
                resp_transaction_id=update_transaction_dict.get('resp_transaction_id'),
                resp_currency=update_transaction_dict.get('resp_currency'),
                resp_failure_code=update_transaction_dict.get('resp_failure_code'),
                resp_failure_message=update_transaction_dict.get('resp_failure_message'),
                resp_error_details=update_transaction_dict.get('resp_error_details')
            ))


class PaymentManager:

    def get_payment_service(self, payment_type):
        if payment_type == PaymentType.PAYMENT_TYPE_STRIPE:
            return PaymentByStripe()
        if payment_type == PaymentType.PAYMENT_TYPE_PAYPAL:
            return PaymentByPayPal()
        if payment_type == PaymentType.PAYMENT_TYPE_OFFLINE:
            return PaymentByBankDeposit()


class ICFPayment:
    payment_type = None

    def __init__(self, payment_type):
        payment_type = payment_type

    payment_service = PaymentManager().get_payment_service(payment_type)


class ICF_Payment_Transaction_Manager:

    def create_stripe_payment_transaction_details(self, create_transaction_dict):
        icf_payment_transaction = ICFPaymentTransaction()
        icf_payment_transaction.user = create_transaction_dict['user']
        icf_payment_transaction.entity = create_transaction_dict['entity']
        icf_payment_transaction.payment_type = create_transaction_dict['payment_type']
        icf_payment_transaction.req_amount_in_cents = create_transaction_dict['req_amount_in_cents']
        icf_payment_transaction.req_amount_in_dollars = create_transaction_dict['req_amount_in_dollars']
        icf_payment_transaction.req_token = create_transaction_dict['req_token']
        icf_payment_transaction.req_desc = create_transaction_dict['req_desc']

        icf_payment_transaction.resp_amount_in_cents = create_transaction_dict['resp_amount_in_cents']
        icf_payment_transaction.resp_amount_in_dollars = create_transaction_dict['resp_amount_in_dollars']
        icf_payment_transaction.resp_date = create_transaction_dict['resp_date']
        icf_payment_transaction.payment_status = create_transaction_dict['payment_status']
        icf_payment_transaction.resp_error_code = create_transaction_dict['resp_error_code']
        icf_payment_transaction.resp_error_details = create_transaction_dict['resp_error_details']
        icf_payment_transaction.resp_transaction_id = create_transaction_dict['resp_transaction_id']
        icf_payment_transaction.resp_currency = create_transaction_dict['resp_currency']
        icf_payment_transaction.resp_failure_code = create_transaction_dict['resp_failure_code']
        icf_payment_transaction.resp_failure_message = create_transaction_dict['resp_failure_message']
        icf_payment_transaction.save()
        return icf_payment_transaction
        # return transaction_dict

    def update_stripe_payment_transaction_details(self, icf_payment_transaction_obj, update_transaction_dict):
        try:
            icf_payment_transaction = ICFPaymentTransaction.objects.get(id=icf_payment_transaction_obj.id)
            # icf_payment_transaction.user = update_transaction_dict['user']
            # icf_payment_transaction.entity = update_transaction_dict['entity']
            # icf_payment_transaction.payment_type = update_transaction_dict['payment_type']
            # icf_payment_transaction.req_amount_in_cents = update_transaction_dict['total_amount_with_tax_in_cents']
            # icf_payment_transaction.req_amount_in_dollars = update_transaction_dict['total_amount_with_tax_in_USD']
            # icf_payment_transaction.req_token = update_transaction_dict['token']
            # icf_payment_transaction.req_desc = update_transaction_dict['description']

            icf_payment_transaction.resp_amount_in_cents = update_transaction_dict['resp_amount_in_cents']
            icf_payment_transaction.resp_amount_in_dollars = update_transaction_dict['resp_amount_in_dollars']
            icf_payment_transaction.resp_date = update_transaction_dict['resp_date']
            icf_payment_transaction.payment_status = update_transaction_dict['payment_status']
            icf_payment_transaction.resp_error_code = update_transaction_dict['resp_error_code']
            icf_payment_transaction.resp_error_details = update_transaction_dict['resp_error_details']
            icf_payment_transaction.resp_transaction_id = update_transaction_dict['resp_transaction_id']
            icf_payment_transaction.resp_currency = update_transaction_dict['resp_currency']
            icf_payment_transaction.resp_failure_code = update_transaction_dict['resp_failure_code']
            icf_payment_transaction.resp_failure_message = update_transaction_dict['resp_failure_message']
            icf_payment_transaction.save(update_fields=['resp_amount_in_cents', 'resp_amount_in_dollars',
                                                        'resp_date', 'payment_status', 'resp_error_code',
                                                        'resp_error_details', 'resp_transaction_id',
                                                        'resp_currency', 'resp_failure_code',
                                                        'resp_failure_message'])

        except ICFPaymentTransaction.DoesNotExist as tdn:
            raise ICFException
        return icf_payment_transaction

    # --------------------------------------------------------

    def create_paypal_payment_transaction_details(self, create_transaction_dict):
        icf_payment_transaction = ICFPaymentTransaction()
        icf_payment_transaction.user = create_transaction_dict['user']
        icf_payment_transaction.entity = create_transaction_dict['entity']
        icf_payment_transaction.payment_type = create_transaction_dict['payment_type']
        icf_payment_transaction.req_amount_in_cents = create_transaction_dict['req_amount_in_cents']
        icf_payment_transaction.req_amount_in_dollars = create_transaction_dict['req_amount_in_dollars']
        icf_payment_transaction.req_token = create_transaction_dict['req_token']
        icf_payment_transaction.req_desc = create_transaction_dict['req_desc']

        icf_payment_transaction.resp_amount_in_cents = create_transaction_dict['resp_amount_in_cents']
        icf_payment_transaction.resp_amount_in_dollars = create_transaction_dict['resp_amount_in_dollars']
        icf_payment_transaction.resp_date = create_transaction_dict['resp_date']
        icf_payment_transaction.payment_status = create_transaction_dict['payment_status']
        icf_payment_transaction.resp_error_code = create_transaction_dict['resp_error_code']
        icf_payment_transaction.resp_error_details = create_transaction_dict['resp_error_details']
        icf_payment_transaction.resp_transaction_id = create_transaction_dict['resp_transaction_id']
        icf_payment_transaction.resp_currency = create_transaction_dict['resp_currency']
        icf_payment_transaction.resp_failure_code = create_transaction_dict['resp_failure_code']
        icf_payment_transaction.resp_failure_message = create_transaction_dict['resp_failure_message']
        icf_payment_transaction.save()
        return icf_payment_transaction

    def update_paypal_payment_transaction_details(self, icf_payment_transaction_obj, update_transaction_dict):

        try:
            icf_payment_transaction = ICFPaymentTransaction.objects.get(id=icf_payment_transaction_obj.id)
            # icf_payment_transaction.user = update_transaction_dict['user']
            # icf_payment_transaction.entity = update_transaction_dict['entity']
            # icf_payment_transaction.payment_type = update_transaction_dict['payment_type']
            # icf_payment_transaction.req_amount_in_cents = update_transaction_dict['total_amount_with_tax_in_cents']
            # icf_payment_transaction.req_amount_in_dollars = update_transaction_dict['total_amount_with_tax_in_USD']
            # icf_payment_transaction.req_token = update_transaction_dict['token']
            # icf_payment_transaction.req_desc = update_transaction_dict['description']

            icf_payment_transaction.resp_amount_in_cents = update_transaction_dict['resp_amount_in_cents']
            icf_payment_transaction.resp_amount_in_dollars = update_transaction_dict['resp_amount_in_dollars']
            icf_payment_transaction.resp_date = update_transaction_dict['resp_date']
            icf_payment_transaction.payment_status = update_transaction_dict['payment_status']
            icf_payment_transaction.resp_error_code = update_transaction_dict['resp_error_code']
            icf_payment_transaction.resp_error_details = update_transaction_dict['resp_error_details']
            icf_payment_transaction.resp_transaction_id = update_transaction_dict['resp_transaction_id']
            icf_payment_transaction.resp_currency = update_transaction_dict['resp_currency']
            icf_payment_transaction.resp_failure_code = update_transaction_dict['resp_failure_code']
            icf_payment_transaction.resp_failure_message = update_transaction_dict['resp_failure_message']
            icf_payment_transaction.save(update_fields=['resp_amount_in_cents', 'resp_amount_in_dollars',
                                                        'resp_date', 'payment_status', 'resp_error_code',
                                                        'resp_error_details', 'resp_transaction_id',
                                                        'resp_currency', 'resp_failure_code',
                                                        'resp_failure_message'])

        except ICFPaymentTransaction.DoesNotExist as tdn:
            raise ICFException
        return icf_payment_transaction

    # -------------------------------------------------------------------------

    def create_offline_payment_transaction_details(self, create_transaction_dict):
        icf_payment_transaction = ICFPaymentTransaction()
        icf_payment_transaction.user = create_transaction_dict['user']
        icf_payment_transaction.entity = create_transaction_dict['entity']
        icf_payment_transaction.payment_type = create_transaction_dict['payment_type']
        icf_payment_transaction.req_amount_in_cents = create_transaction_dict['req_amount_in_cents']
        icf_payment_transaction.req_amount_in_dollars = create_transaction_dict['req_amount_in_dollars']
        icf_payment_transaction.req_token = create_transaction_dict['req_token']
        icf_payment_transaction.req_desc = create_transaction_dict['req_desc']

        icf_payment_transaction.resp_amount_in_cents = create_transaction_dict['resp_amount_in_cents']
        icf_payment_transaction.resp_amount_in_dollars = create_transaction_dict['resp_amount_in_dollars']
        icf_payment_transaction.resp_date = create_transaction_dict['resp_date']
        icf_payment_transaction.payment_status = create_transaction_dict['payment_status']
        icf_payment_transaction.resp_error_code = create_transaction_dict['resp_error_code']
        icf_payment_transaction.resp_error_details = create_transaction_dict['resp_error_details']
        icf_payment_transaction.resp_transaction_id = create_transaction_dict['resp_transaction_id']
        icf_payment_transaction.resp_currency = create_transaction_dict['resp_currency']
        icf_payment_transaction.resp_failure_code = create_transaction_dict['resp_failure_code']
        icf_payment_transaction.resp_failure_message = create_transaction_dict['resp_failure_message']
        icf_payment_transaction.save()
        return icf_payment_transaction




    def update_stripe_trasaction_details(self, req_dict, icf_charge_obj):
        icf_payment_transaction = ICFPaymentTransaction()
        icf_payment_transaction.user = req_dict['user']
        icf_payment_transaction.entity = req_dict['entity']
        icf_payment_transaction.payment_type = req_dict['payment_type']
        icf_payment_transaction.req_amount_in_cents = req_dict['total_amount_with_tax_in_cents']
        icf_payment_transaction.req_amount_in_dollars = req_dict['total_amount_with_tax_in_USD']
        icf_payment_transaction.req_token = req_dict['token']
        icf_payment_transaction.req_desc = req_dict['description']

        # icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=token)
        icf_payment_transaction.resp_amount_in_cents = icf_charge_obj.resp_amount_in_cents
        icf_payment_transaction.resp_amount_in_dollars = icf_charge_obj.resp_amount_in_dollars
        icf_payment_transaction.resp_date = datetime.now()
        icf_payment_transaction.resp_status = PaymentStatus.SUCCESS
        icf_payment_transaction.resp_error_code = None
        icf_payment_transaction.resp_error_details = None
        icf_payment_transaction.resp_transaction_id = icf_charge_obj.resp_transaction_id
        icf_payment_transaction.resp_currency = icf_charge_obj.resp_currency
        icf_payment_transaction.resp_failure_code = icf_charge_obj.resp_failure_code
        icf_payment_transaction.resp_failure_message = None
        icf_payment_transaction.save()

    def update_paypal_trasaction_details(self, req_dict, icf_charge_obj):
        icf_payment_transaction = ICFPaymentTransaction()
        icf_payment_transaction.user = req_dict['user']
        icf_payment_transaction.entity = req_dict['entity']
        icf_payment_transaction.payment_type = req_dict['payment_type']
        icf_payment_transaction.req_amount_in_cents = req_dict['total_amount_with_tax_in_cents']
        icf_payment_transaction.req_amount_in_dollars = req_dict['total_amount_with_tax_in_USD']
        icf_payment_transaction.req_token = req_dict['token']
        icf_payment_transaction.req_desc = req_dict['description']

        # icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=token)
        icf_payment_transaction.resp_amount_in_cents = icf_charge_obj.resp_amount_in_cents
        icf_payment_transaction.resp_amount_in_dollars = icf_charge_obj.resp_amount_in_dollars
        icf_payment_transaction.resp_date = datetime.now()
        icf_payment_transaction.resp_status = PaymentStatus.SUCCESS
        icf_payment_transaction.resp_error_code = None
        icf_payment_transaction.resp_error_details = None
        icf_payment_transaction.resp_transaction_id = req_dict['transaction_id']
        icf_payment_transaction.resp_currency = icf_charge_obj.resp_currency
        icf_payment_transaction.resp_failure_code = icf_charge_obj.resp_failure_code
        icf_payment_transaction.resp_failure_message = None
        icf_payment_transaction.save()

    def update_offline_payment_trasaction_details(self, req_dict, icf_charge_obj):
        icf_payment_transaction = ICFPaymentTransaction()
        icf_payment_transaction.user = req_dict['user']
        icf_payment_transaction.entity = req_dict['entity']
        icf_payment_transaction.payment_type = req_dict['payment_type']
        icf_payment_transaction.req_amount_in_cents = req_dict['total_amount_with_tax_in_cents']
        icf_payment_transaction.req_amount_in_dollars = req_dict['total_amount_with_tax_in_USD']
        icf_payment_transaction.req_token = req_dict['token']
        icf_payment_transaction.req_desc = req_dict['description']

        # icf_payment_transaction_update = ICFPaymentTransaction.objects.get(req_token=token)
        icf_payment_transaction.resp_amount_in_cents = icf_charge_obj.resp_amount_in_cents
        icf_payment_transaction.resp_amount_in_dollars = icf_charge_obj.resp_amount_in_dollars
        icf_payment_transaction.resp_date = datetime.now()
        icf_payment_transaction.resp_status = PaymentStatus.SUCCESS
        icf_payment_transaction.resp_error_code = None
        icf_payment_transaction.resp_error_details = None
        icf_payment_transaction.resp_transaction_id = req_dict['transaction_id']
        icf_payment_transaction.resp_currency = icf_charge_obj.resp_currency
        icf_payment_transaction.resp_failure_code = icf_charge_obj.resp_failure_code
        icf_payment_transaction.resp_failure_message = None
        icf_payment_transaction.save()


class ProductDetailsForPDF:
    def __init__(self, product_name=None, qty=None, unit_price=None, details=None, amount=None):
        self.product_name = product_name
        self.qty = qty
        self.unit_price = unit_price
        self.details = details
        self.amount = amount


class IcfBillGenerator:
    def generate_bill(self, user, entity, no_of_credits, total_amount_in_USD, currency, VAT, total_amount_with_tax, base_url):
        path = os.path.join(MEDIA_ROOT, "payment_receipt")
        filename = os.path.join(path, "{}_payment_receipt_{}.pdf".format(entity.slug, 1))

        try:
            cost_for_credit = Product.objects.get(product_type=Product.CREDIT, currency__name=currency)
            unit_cost = cost_for_credit.cost
            unit_credits = cost_for_credit.unit
        except Product.DoesNotExist as cdne:
            raise Product.DoesNotExist

        template = get_template('credits/payment_receipt.html')
        context = {}
        invoice = {}
        this_day = datetime.today()
        this_date = this_day.date
        invoice['date'] = this_date
        invoice['total_credits'] = no_of_credits
        invoice['cost'] = total_amount_in_USD
        invoice['unit_cost'] = unit_cost
        invoice['unit_credits'] = unit_credits
        invoice['currency'] = currency
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
            #pdf_file = HTML(string=html, base_url=base_url).write_pdf(filename)
            pass
        except Exception as e:
            payment_logger.error("Could not create payment bill reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create payment bill, please try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        email_body = str(app_settings.PAYMENT_RECEIPT_EMAIL_BODY).format(user.display_name)

        msg = EmailMessage(subject=app_settings.PAYMENT_RECEIPT_SUBJECT,
                           body=email_body,
                           to=[user.email, ],
                           cc=[app_settings.PAYMENT_RECEIPT_EMAIL_CC, ])

        #msg.attach('iCUBEFARM-Credits-Payment-Receipt.pdf', open(filename, 'rb').read(), 'application/pdf')
        msg.content_subtype = "html"
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('PAYMENT_BILL_NOTIFICATION')
        details = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL').format(user.display_name, message, entity.display_name)
        ICFNotificationManager.add_notification(user=user, message=message, details=details)


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
            pdf_file = HTML(string=html, base_url=base_url).write_pdf(filename)
            # pass
        except Exception as e:
            payment_logger.error("Could not create payment bill reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create payment bill, please try again."),
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

        ###############################################################################################################

    def generate_bill_for_subscription(self, user, entity, subscription_plan_obj, subscription_list, total_amount_without_tax_in_USD, currency, VAT_USD, total_amount_with_tax_in_USD, base_url, is_offline):

        path = os.path.join(MEDIA_ROOT, "subscriptions")
        filename = os.path.join(path, "{}_reciept{}.pdf".format(subscription_plan_obj.name.replace(' ', '_'), 1))

        template = get_template('subscriptions/subscription_purchase_reciept.html')
        context = {}
        invoice = {}
        this_day = datetime.today()
        this_date = this_day.date
        invoice['date'] = this_date
        invoice['cost'] = total_amount_without_tax_in_USD
        invoice['currency'] = currency
        invoice['VAT'] = VAT_USD
        invoice['total_cost'] = total_amount_with_tax_in_USD
        invoice['subscription_plan_obj'] = subscription_plan_obj
        invoice['subscription_list'] = subscription_list
        invoice['entity'] = entity
        invoice['is_offline'] = is_offline
        context['subscription_bank_details'] = app_settings.SUBSCRIPTION_BANK_DETAILS
        context['subscription_plan_details'] = app_settings.SUBSCRIPTION_DETAILS
        context['subscription_info'] = app_settings.SUBSCRIPTION_INFO
        invoice['sub_total'] = str(round(total_amount_without_tax_in_USD, 2))

        inv_num = 1
        try:
            inv_num += subscription_plan_obj.objects.filter(created__year=this_day.year).last().invoice_num
        except AttributeError as ae:
            pass

        invoice['number'] = inv_num
        context['invoice'] = invoice
        context['icube'] = app_settings.ICUBE_ADDRESS
        context['subscription_account'] = app_settings.SUBSCRIPTION_PLAN_ACCOUNT_DETAILS
        context['policy'] = app_settings.Non_Refund_Policy
        context['exchange_rate'] = app_settings.EXCHANGE_RATE

        ssl._create_default_https_context = ssl._create_unverified_context
        html = template.render(context)
        try:
            #pdf_file = HTML(string=html, base_url=base_url).write_pdf(filename)
            pass
        except Exception as e:
            payment_logger.error("Could not create payment bill reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create payment bill, please try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        email_body = str(app_settings.SUBSCRIPTION_PLAN_RECEIPT_EMAIL_BODY).format(user.display_name, subscription_plan_obj.name)

        msg = EmailMessage(subject=app_settings.SUBSCRIPTION_PLAN_RECEIPT_SUBJECT,
                           body=email_body,
                           to=[user.email, ],
                           cc=app_settings.SUBSCRIPTION_PLAN_RECEIPT_EMAIL_CC)

        #msg.attach('iCUBEFARM-Subscription-Payment-Receipt.pdf', open(filename, 'rb').read(), 'application/pdf')
        msg.content_subtype = "html"
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('PAYMENT_BILL_NOTIFICATION')
        # details = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL').format(user.display_name, message, entity.display_name)
        # ICFNotificationManager.add_notification(user=user, message=message, details=details)

    # ---------------------------------------------------------------------------------------------------

    def generate_receipt_or_invoice_for_products_purchase(self, order_no, user, currency, all_order_details_list, total_products_cost_without_tax_in_USD, total_products_cost_with_tax_in_USD, base_url, is_offline, billing_address_obj, is_free_checkout):
        ''' generate pdf for products purchase '''

        path = os.path.join(MEDIA_ROOT, "products")
        # filename = os.path.join(path, "products_purchase_reciept.pdf")
        if not os.path.exists(path):
            os.makedirs(path)
        filename = os.path.join(path, "products_purchase_reciept.pdf")

        # filename = os.path.join(path, "products_purchase_reciept{}.pdf".format(subscription_plan_obj.name.replace(' ', '_'), 1))

        template = get_template('orders/product_purchase_reciept.html')
        context = {}
        invoice = {}
        this_day = datetime.today()
        this_date = this_day.date

        products_list = []

        for order_details_obj in all_order_details_list:
            # content_type = order_details_obj.content_type
            # content_type_obj = ContentType.objects.get(id=content_type.id)
            # model = content_type_obj.model_class()
            # product_item_obj = model.objects.get(id=order_details_obj.object_id)

            product_details_for_pdf_obj = ProductDetailsForPDF()
            product_details_for_pdf_obj.product_name = order_details_obj.product.name
            product_details_for_pdf_obj.qty = order_details_obj.quantity
            product_details_for_pdf_obj.unit_price = order_details_obj.product.cost / order_details_obj.product.unit
            product_details_for_pdf_obj.amount = product_details_for_pdf_obj.qty * product_details_for_pdf_obj.unit_price

            if order_details_obj.product.product_type == Product.CREDIT:

                entity_name_str = app_settings.CREDIT_DETAILS.get('entity_name')+":" + \
                                  order_details_obj.entity.name + "<br/>"
                if order_details_obj.entity.address.address_1:
                    entity_address_1_str = app_settings.CREDIT_DETAILS.get('entity_address') + ":" + order_details_obj.entity.address.address_1 + "<br/>"
                else:
                    entity_address_1_str = ''
                if order_details_obj.entity.address.address_2:
                    entity_address_2_str = order_details_obj.entity.address.address_2 + "<br/>"
                else:
                    entity_address_2_str = ''
                entity_address_str = entity_address_1_str + entity_address_2_str

                entity_city_str = app_settings.CREDIT_DETAILS.get('entity_city') + ":" + str(order_details_obj.entity.address.city)

                credit_details = '{0}{1}{2}'.format(entity_name_str, entity_address_str, entity_city_str)

                product_details_for_pdf_obj.details = mark_safe(credit_details)

                products_list.append(product_details_for_pdf_obj)

            elif order_details_obj.product.product_type == Product.SUBSCRIPTION:

                # content_type = order_details_obj.content_type
                # content_type_obj = ContentType.objects.get(id=content_type.id)
                # model = content_type_obj.model_class()
                # subscription = model.objects.get(id=order_details_obj.object_id)
                subscription_plan = SubscriptionPlan.objects.get(product=order_details_obj.product)

                entity_name_str = app_settings.SUBSCRIPTION_DETAILS.get('entity_name')+":"+order_details_obj.entity.name + "<br/>"
                duration_str = app_settings.SUBSCRIPTION_DETAILS.get('duration') + ":" + str(subscription_plan.duration) + "<br/>"
                subscription_description_str = app_settings.SUBSCRIPTION_DETAILS.get('description') + ":" + order_details_obj.product.description

                subscription_details = '{0}{1}{2}'.format(entity_name_str, duration_str, subscription_description_str)

                product_details_for_pdf_obj.details = mark_safe(subscription_details)

                products_list.append(product_details_for_pdf_obj)

            elif order_details_obj.product.product_type == Product.EVENT_PRODUCT:

                content_type = order_details_obj.content_type
                content_type_obj = ContentType.objects.get(id=content_type.id)
                model = content_type_obj.model_class()
                participant = model.objects.get(id=order_details_obj.object_id)

                featured_event_name_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('featured_event_name') + \
                    ":" + participant.featured_event.title + "<br/>"

                if participant.entity_name is not None:
                    entity_name_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('entity_name') + ":" + \
                        participant.entity_name + "<br/>"
                else:
                    entity_name_str = None

                if participant.entity_email is not None:
                    entity_email_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('entity_email') + ":" + \
                        participant.entity_email + "<br/>"
                else:
                    entity_email_str = None

                if participant.phone_no is not None:
                    entity_contact_no_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('contact_no') + ":" + \
                        participant.phone_no + "<br/>"
                else:
                    entity_contact_no_str = None

                if participant.name_of_representative is not None:
                    entity_name_of_representative_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('name_of_representative') + ":" + \
                        participant.name_of_representative + "<br/>"
                else:
                    entity_name_of_representative_str = None

                if participant.participants is not None:
                    participants_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('participants') + \
                        ":" + participant.participants + "<br/>"
                else:
                    participants_str = None

                if participant.address is not None:
                    entity_address_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('address') +\
                        ":" + str(participant.address) + "<br/>"
                else:
                    entity_address_str = None

                # featured_event_participant_details = '{0}{1}{2}{3}{4}{5}{6}'.format(featured_event_name_str,
                #     entity_name_str, entity_email_str, entity_contact_no_str, entity_name_of_representative_str, participants_str, entity_address_str)

                featured_event_participant_details = ''
                if featured_event_name_str:
                    featured_event_participant_details = featured_event_participant_details + featured_event_name_str
                if entity_name_str:
                    featured_event_participant_details = featured_event_participant_details + entity_name_str
                if entity_email_str:
                    featured_event_participant_details = featured_event_participant_details + entity_email_str
                if entity_contact_no_str:
                    featured_event_participant_details = featured_event_participant_details + entity_contact_no_str
                if entity_name_of_representative_str:
                    featured_event_participant_details = featured_event_participant_details + entity_name_of_representative_str
                if participants_str:
                    featured_event_participant_details = featured_event_participant_details + participants_str
                if entity_address_str:
                    featured_event_participant_details = featured_event_participant_details + entity_address_str

                product_details_for_pdf_obj.details = mark_safe(featured_event_participant_details)

                products_list.append(product_details_for_pdf_obj)

           # ----------------------------------------------------------

            elif order_details_obj.product.product_type == Product.CAREER_FAIR_PRODUCT:

                content_type = order_details_obj.content_type
                content_type_obj = ContentType.objects.get(id=content_type.id)
                model = content_type_obj.model_class()
                career_fair_participant = model.objects.get(id=order_details_obj.object_id)

                career_fair_name_str = app_settings.CAREER_FAIR_PARTICIPANT_DETAILS.get('career_fair_name') + \
                    ":" + career_fair_participant.career_fair.title + "<br/>"

                if career_fair_participant:
                    entity_name_str = app_settings.CAREER_FAIR_PARTICIPANT_DETAILS.get('entity_name') + ":" + \
                        order_details_obj.product.entity.name + "<br/>"
                else:
                    entity_name_str = None

                if career_fair_participant.representative_email is not None:
                    representative_email_str = app_settings.CAREER_FAIR_PARTICIPANT_DETAILS.get('representative_email') + ":" + \
                        career_fair_participant.representative_email + "<br/>"
                else:
                    representative_email_str = None
                #
                # if career_fair_participant.phone_no is not None:
                #     career_fair_participant_contact_no_str = app_settings.CAREER_FAIR_PARTICIPANT_DETAILS.get('contact_no') + ":" + \
                #         career_fair_participant.phone_no + "<br/>"
                # else:
                #     career_fair_participant_contact_no_str = None

                if career_fair_participant.name_of_representative is not None:
                    name_of_representative_str = app_settings.CAREER_FAIR_PARTICIPANT_DETAILS.get('name_of_representative') + ":" + \
                        career_fair_participant.name_of_representative + "<br/>"
                else:
                    name_of_representative_str = None

                # if career_fair_participant.participants is not None:
                #     participants_str = app_settings.FEATURED_EVENT_PARTICIPANT_DETAILS.get('participants') + \
                #         ":" + participant.participants + "<br/>"
                # else:
                #     participants_str = None

                if career_fair_participant.address is not None:
                    career_fair_participant_address_str = app_settings.CAREER_FAIR_PARTICIPANT_DETAILS.get('address') +\
                        ":" + str(career_fair_participant.address) + "<br/>"
                else:
                    career_fair_participant_address_str = None

                # featured_event_participant_details = '{0}{1}{2}{3}{4}{5}{6}'.format(featured_event_name_str,
                #     entity_name_str, entity_email_str, entity_contact_no_str, entity_name_of_representative_str, participants_str, entity_address_str)

                career_fair_participant_details = ''
                if career_fair_name_str:
                    career_fair_participant_details = career_fair_participant_details + career_fair_name_str
                if entity_name_str:
                    career_fair_participant_details = career_fair_participant_details + entity_name_str
                if representative_email_str:
                    career_fair_participant_details = career_fair_participant_details + representative_email_str
                if name_of_representative_str:
                    career_fair_participant_details = career_fair_participant_details + name_of_representative_str
                if career_fair_participant_address_str:
                    career_fair_participant_details = career_fair_participant_details + career_fair_participant_address_str

                product_details_for_pdf_obj.details = mark_safe(career_fair_participant_details)

                products_list.append(product_details_for_pdf_obj)

            else:
                payment_logger.info("pdf cannot be generated for products purchase.\n")
                raise ICFException("something went wrong reason:{reason}.".
                                   format(reason="Unknown Product Type to generate bill."),
                                   status_code=status.HTTP_400_BAD_REQUEST)

            # object_id = order_detail_obj.object_id
            # transaction_obj = order_detail_obj.transaction

        invoice['date'] = this_date
        invoice['order_no'] = order_no
        invoice['cost'] = total_products_cost_without_tax_in_USD
        invoice['currency'] = currency
        invoice['VAT'] = total_products_cost_with_tax_in_USD - float(total_products_cost_without_tax_in_USD)
        invoice['total_cost'] = total_products_cost_with_tax_in_USD
        invoice['is_offline'] = is_offline
        context['featured_event_bank_details'] = app_settings.PRODUCTS_BANK_DETAILS
        # context['subscription_bank_details'] = app_settings.SUBSCRIPTION_BANK_DETAILS
        context['products_list'] = products_list
        context['billing_address_details'] = app_settings.BILLING_ADDRESS_DETAILS
        context['billing_address_obj'] = billing_address_obj
        context['space_string'] = ''
        invoice['sub_total'] = str(round(total_products_cost_without_tax_in_USD, 2))
        invoice['is_free_checkout'] = is_free_checkout


        # inv_num = 1
        # try:
        #     # inv_num += subscription_plan_obj.objects.filter(created__year=this_day.year).last().invoice_num
        #     pass
        # except AttributeError as ae:
        #     pass

        # invoice['number'] = order_no
        context['invoice'] = invoice
        context['icube'] = app_settings.ICUBE_ADDRESS
        context['subscription_account'] = app_settings.SUBSCRIPTION_PLAN_ACCOUNT_DETAILS
        context['fe_account'] = app_settings.PRODUCTS_ACCOUNT_DETAILS
        context['policy'] = app_settings.Non_Refund_Policy
        context['exchange_rate'] = app_settings.EXCHANGE_RATE

        ssl._create_default_https_context = ssl._create_unverified_context
        html = template.render(context)
        try:
            pdf_file = HTML(string=html, base_url=base_url).write_pdf(filename)
            # pass
        except Exception as e:
            payment_logger.error("Could not create payment bill reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create payment bill, please try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        email_body = str(app_settings.PRODUCT_PURCHASE_RECEIPT_EMAIL_BODY).format(user.display_name)

        for order_details_obj in all_order_details_list:
            if order_details_obj.product.product_type == Product.EVENT_PRODUCT:

                content_type = order_details_obj.content_type
                content_type_obj = ContentType.objects.get(id=content_type.id)
                model = content_type_obj.model_class()
                participant = model.objects.get(id=order_details_obj.object_id)

                featured_event = participant.featured_event

                email_body = str(app_settings.PRODUCT_PURCHASE_RECEIPT_EMAIL_BODY).\
                                 format(user.display_name)+"\n"+str(featured_event.email_content)

        msg = EmailMessage(subject=app_settings.PRODUCT_PURCHASE_RECEIPT_SUBJECT,
                           body=email_body,
                           to=[user.email, ],
                           cc=app_settings.PRODUCT_PURCHASE_RECEIPT_EMAIL_CC)

        msg.attach('iCUBEFARM-Products-Payment-Receipt.pdf', open(filename, 'rb').read(), 'application/pdf')
        msg.content_subtype = "html"
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('PAYMENT_BILL_NOTIFICATION')
        # details = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL').format(user.display_name, message, entity.display_name)
        # ICFNotificationManager.add_notification(user=user, message=message, details=details)











