import pyotp
import requests
from pyotp import TOTP
from rest_framework import status
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from urllib3.exceptions import NewConnectionError, MaxRetryError, ConnectTimeoutError

from django.utils.translation import gettext_lazy as _
from icf_generic.Exceptions import ICFException
from icf_integrations.app_settings import OTP_NUMBER_OF_DIGITS
from django.conf import settings
import logging

from icf_integrations.models import SentGroupSms

logger = logging.getLogger(__name__)


class ICFTwilio:

    def __init__(self):

        # Your Account SID from twilio.com/console
        self.account_sid = settings.TWILIO_ACCOUNT_SID

        # Your Auth Token from twilio.com/console
        self.auth_token = settings.TWILIO_AUTH_TOKEN

        # The from phone number from twilio/console
        self.from_num = settings.TWILIO_FROM_NUM

    def send_sms(self, to_num=None, msg_body=None):

        client = Client(self.account_sid, self.auth_token)

        logger.info("Sending SMS to - {}, Message = {}".format(to_num, msg_body))
        try:

            message = client.messages.create(
                to=to_num,
                from_=self.from_num,
                body=msg_body)

            if not message.error_code:
                logger.info("Response: Sid - {}, Message = {}".format(message.sid, msg_body))
                return message.sid
            else:
                return None
        except TwilioRestException as e:
            # if 'not a valid phone number' in e.msg:
            logger.info("Failed to send OTP: {}".format(e))
            raise ICFException(_("Please provide a valid phone number."), status_code=status.HTTP_400_BAD_REQUEST)
            # else:
            #     raise

        except Exception as e:
            logger.info("Failed to send OTP: {}".format(e))
            raise

    def send_group_sms(self, user_list=[], msg_body=None):
        success_count = 0
        failure_count = 0

        client = Client(self.account_sid, self.auth_token)
        for user in user_list:
            logger.info("Sending SMS to - {}, Message = {}".format(user, msg_body))
            try:

                message = client.messages.create(
                    to=user.mobile,
                    from_=self.from_num,
                    body=msg_body)

                if not message.error_code:
                    logger.info("Response: Sid - {}, Message = {}".format(message.sid, msg_body))
                    success_count+=1
                    # return message.sid
                else:
                    logger.info("Failed to send messages for: Sid - {}, Message = {}".format(message.sid, msg_body))
                    failure_count+=1
                    # return None
            except Exception as e:
                failure_count+=1
                logger.exception("Failed to send SMS: {}".format(e))
                continue

        SentGroupSms.objects.create(messages=msg_body,success_count=success_count,failure_count=failure_count)
        return None

class IcfOTPManager:

    key = None
    totp = None

    def __init__(self, key=None):
        if key:
            self.key = key
        else:
            self.key = pyotp.random_base32()
        self.totp = TOTP(self.key, digits=OTP_NUMBER_OF_DIGITS)

    def get_key(self):
        return self.key

    def generate_otp(self):
        return self.totp.now()

    def send_otp(self, mobile, message=None):
        otp = self.generate_otp()

        if message:
            message = message.replace("ICF_OTP", str(otp))
        else:
            message = otp

        logger.info("Send {1} to the number {0}".format(mobile, message))

        """
        Write the code to integrate with the third party service provider here
        """

        try:
            if settings.ICF_SEND_OTP_DISABLED:
                return otp
        except AttributeError:
            pass

        sms_gateway = self.get_sms_gateway()
        ret = sms_gateway.send_sms(to_num=mobile, msg_body=message)

        if ret:
            return otp
        else:
            return None

    def verify_top(self, *args, **kwargs):
        return self.totp.verify(*args, **kwargs)

    def get_sms_gateway(self):
        return ICFTwilio()


class SMSManager:

    def get_sms_gateway(self):
        return ICFTwilio()


