import logging
import os

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from rest_framework import status

from icf import settings
from icf_auth import app_settings
from icf_auth.models import User
from icf_generic.Exceptions import ICFException
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


def get_user_from_email(email):
    return email.split('@')[0]


def send_email_verification_confirmation(email):
    try:
        if email:
            user = User.objects.get(email=email)
            try:
                current_site = Site.objects.get_current()
            except Exception as ex:
                logger.error("Failed to get site information: {e}".format(e=str(ex)))
                current_site = None
            ctx = {
                "user_name": get_user_name(user),
                "user": user,
                "current_site": current_site,
                "to_email": email
            }

            email_template = 'templates/account/email/verify_email_success.html'
            html = get_template(os.path.join(settings.BASE_DIR, email_template))

            html_content = html.render(ctx)

            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [email, ]

            # try:
            #     current_site = Site.objects.get_current()
            # except Exception as ex:
            #     logger.error("Failed to get site information: {e}".format(e=str(ex)))
            #     current_site = None

            subject = app_settings.EMAIL_VERIFICATION_SUCCESS_SUBJECT

            if current_site:
                logger.debug("Current Site domain: {domain}".format(domain=current_site.domain))
                subject = "[{domain}] {subject}".format(domain=current_site.name, subject=subject)
            else:
                logger.debug("Current Site domain: {domain}".format(domain=current_site.domain))
                subject = "[{domain}] {subject}".format(domain="iCUBEFARM.com", subject=subject)

            message = EmailMultiAlternatives(subject=subject,
                                             body=html_content,
                                             from_email=from_email,
                                             to=to_email)

            message.attach_alternative(html_content, "text/html")
            message.send()
        else:
            raise ICFException
    except User.DoesNotExist as ue:
        logger.exception("User object not found.reason:{reason}\n".format(reason=str(ue)))
        pass
    except Exception as e:
        logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(e)))
        pass


def verified_email_address_exists(email):
    from allauth.account import app_settings as account_settings
    from allauth.account.models import EmailAddress

    ret = False
    existing_users = None
    email_field = account_settings.USER_MODEL_EMAIL_FIELD
    if email_field:
        users = get_user_model().objects
        existing_users = users.filter(**{email_field + '__iexact': email}).exists()
    if existing_users:
        emailaddresses = EmailAddress.objects
        ret = emailaddresses.filter(email__iexact=email, verified=True).exists()

    return ret


def get_user_name(user):
    if user:
        if user.first_name and user.last_name:
            return user.first_name + " " + user.last_name
        else:
            return user.username
    else:
        logger.exception("user object is none.")
        raise ICFException(_("Something went wrong, please contact admin."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

