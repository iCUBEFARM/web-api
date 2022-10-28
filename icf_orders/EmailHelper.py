import logging

from django.core.mail import EmailMessage
from rest_framework import status

from icf_generic.Exceptions import ICFException
from icf_orders import app_settings
from django.utils.translation import gettext_lazy as _

payment_logger = logging.getLogger("icf.integrations.payment")


class PaymentEmailHelper:

    def send_email_on_payment_failure_for_products_purchase(self, user, all_products_list, icf_payment_transaction, total_products_cost_with_tax_in_USD):
        """
        send email on failure payment with transaction details
        """
        try:
            email_subject = str(app_settings.PURCHASE_PRODUCTS_PAYMENT_FAILURE_SUBJECT)
            payment_type = "Credit Card"
            payment_logger.info(
                "transaction failed while purchase products with order_no:{order_no}.\n "
                "payment_type : {payment_type},\n ".format(order_no=icf_payment_transaction.order_no,
                                                           payment_type=payment_type))

            email_body = str(app_settings.PURCHASE_PRODUCTS_PAYMENT_FAILURE_EMAIL_BODY).format(payment_type,
                                                                                               user.display_name,
                                                                                               user.email,
                                                                                               total_products_cost_with_tax_in_USD)
            msg = EmailMessage(subject=email_subject,
                               body=email_body,
                               to=[app_settings.PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL, ]
                               )
            msg.content_subtype = "html"
            msg.send()
        except Exception as e:
            payment_logger.info("Email sending on unsuccessful product purchase failed. reason : {reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong. "), status_code=status.HTTP_400_BAD_REQUEST)
