from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import build_absolute_uri
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from icf_auth.util import get_user_from_email

import logging

from icf_generic.Exceptions import ICFException

logger = logging.getLogger(__name__)

VERIFICATION_SENT_MESSAGE = _("""A verification e-mail has been sent to you. Follow the link provided to finalize the 
signup process. Please contact us if you donot receive it within a few minutes.""")
ACCOUNT_INACTIVE = _("This account is not active")


class ICFAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url.

        Note that if you have architected your system such that email
        confirmations are sent outside of the request context `request`
        can be `None` here.
        """
        url = reverse(
            "icf-verify-email",
            args=[emailconfirmation.key])
        ret = build_absolute_uri(
            request,
            url)
        return ret

    def respond_email_verification_sent(self, request, user):
        return Response(data={'detail': VERIFICATION_SENT_MESSAGE})

    def respond_user_inactive(self, request, user):
        return Response(data={'detail': ACCOUNT_INACTIVE})

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        current_site = get_current_site(request)
        activate_url = self.get_email_confirmation_url(
            request,
            emailconfirmation)
        ctx = {
            "to_email": get_user_from_email(emailconfirmation.email_address.email),
            "user": emailconfirmation.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "key": emailconfirmation.key,
        }
        if signup:
            email_template = 'account/email/email_confirmation_signup'
        else:
            email_template = 'account/email/email_confirmation'
        self.send_mail(email_template,
                       emailconfirmation.email_address.email,
                       ctx)

    def save_user(self, request, user, form, commit=False):
        """
        This is called when saving user via allauth registration.
        We override this to set additional data on user object.
        """
        # Do not persist the user yet so we pass commit=False
        # (last argument)
        user = super(ICFAccountAdapter, self).save_user(request, user, form, commit=commit)
        user.mobile = form.cleaned_data.get('mobile')
        user.first_name = form.cleaned_data.get('first_name')
        user.last_name = form.cleaned_data.get('last_name')
        user.save()

    def save_user_info(self, request, user, form, commit=False):
        """
        This is called when saving user via allauth registration.
        We override this to set additional data on user object.
        """
        # Do not persist the user yet so we pass commit=False
        # (last argument)
        user = super(ICFAccountAdapter, self).save_user(request, user, form, commit=commit)
        user.mobile = form.cleaned_data.get('mobile')
        user.first_name = form.cleaned_data.get('first_name')
        user.last_name = form.cleaned_data.get('last_name')
        user.save()

    def send_confirmation_mail_with_otp(self, request, message, user, signup):
        # data = {
        #     "email": emailconfirmation.email_address.email,
        #     "mobile": request.data.get('mobile')
        # }
        # serializer = EmailOTPSerializer(data=data)
        # serializer.is_valid(raise_exception=True)
        # serializer.email = serializer.validated_data['email']
        # serializer.mobile = serializer.validated_data['mobile']
        # obj = serializer.save()

        current_site = get_current_site(request)
        # activate_url = self.get_email_confirmation_url(
        #     request,
        #     emailconfirmation)
        user_name_in_email = get_user_name(user)
        # gets user name from user's first name and last name if not user's username
        ctx = {
            "to_email": get_user_from_email(user.email),
            "user": user,
            "user_name": user_name_in_email,
            "message": message,
            # "activate_url": activate_url,
            "current_site": current_site,
            # "key": emailconfirmation.key,
        }
        if signup:
            email_template = 'account/email/new_email_confirmation_signup'
        else:
            email_template = 'account/email/new_email_confirmation'
        self.send_mail(email_template,
                       user.email,
                       ctx)


def get_user_name(user):
    if user:
        if user.first_name and user.last_name:
            return user.first_name + " " + user.last_name
        else:
            return user.username
    else:
        logger.exception("user object is none.")
        raise ICFException(_("Something went wrong, please contact admin."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)