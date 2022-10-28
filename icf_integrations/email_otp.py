import pyotp
import requests
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template import loader
from pyotp import TOTP
from rest_framework import status
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from urllib3.exceptions import NewConnectionError, MaxRetryError, ConnectTimeoutError

from django.utils.translation import gettext_lazy as _
from icf_generic.Exceptions import ICFException
from icf_integrations import app_settings
from icf_integrations.app_settings import OTP_NUMBER_OF_DIGITS
from django.conf import settings
import logging

from icf_integrations.mobile import IcfOTPManager
from icf_integrations.models import SentGroupSms

logger = logging.getLogger(__name__)


class IcfEmailOTPManager(IcfOTPManager):

    def generate_email_otp(self, email, message=None):
        try:
            otp = self.generate_otp()

            if message:
                message = message.replace("ICF_OTP", str(otp))
            else:
                message = otp

            logger.info("Send {1} to email {0}".format(message, email))

            """
            Write the code to integrate with the third party service provider here
            """

            # try:
            #     if settings.ICF_SEND_OTP_DISABLED:
            #         return otp
            # except AttributeError:
            #     pass

            # sms_gateway = self.get_sms_gateway()
            # ret = sms_gateway.send_sms(to_num=mobile, msg_body=message)
            email_otp_response = {
                'otp': otp,
                "message": message
            }
            return email_otp_response
        except Exception as e:
            logger.exception("Could not generate otp. reason:{reason}".format(reason=str(e)))
            print(str(e))
            return None

    def send_email_otp(self, email, message=None):
        otp = self.generate_otp()

        if message:
            message = message.replace("ICF_OTP", str(otp))
        else:
            message = otp

        logger.info("Send {1} to email {0}".format(message, email))

        """
        Write the code to integrate with the third party service provider here
        """

        try:
            if settings.ICF_SEND_OTP_DISABLED:
                return otp
        except AttributeError:
            pass

        # sms_gateway = self.get_sms_gateway()
        # ret = sms_gateway.send_sms(to_num=mobile, msg_body=message)
        ret = False
        email = email
        current_site = Site.objects.get_current()
        site_name = current_site.name
        domain = current_site.domain

        context = {
            'email': email,
            'domain': domain,
            'site_name': site_name,
            'message': message,
        }

        try:
            from_email = settings.DEFAULT_FROM_EMAIL
            subject = app_settings.VARIFY_EMAIL_OTP_SUBJECT
            # Email subject *must not* contain newlines
            html_email_template_name = 'account/email/password_reset_email.html'
            email_body = loader.render_to_string(html_email_template_name, context)
            # email_body = transform(email_body)
            msg = EmailMessage(subject=subject, body=email_body, from_email=from_email, to=[email])
            msg.content_subtype = "html"  # Main content is now text/html
            msg.send()
            ret = True
        except Exception as e:
            logger.exception("Could not send email. reason:{reason}".format(reason=str(e)))
            print(str(e))

        if ret:
            return otp
        else:
            return None

    def verify_top(self, *args, **kwargs):
        return self.totp.verify(*args, **kwargs)



