import os
import threading

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import get_template
from django.urls import reverse
from django.utils import six
from django.utils.timezone import now
from django.contrib.sites.models import Site
from icf import settings
from icf_auth.models import User
from icf_generic.Exceptions import ICFException

from icf_jobs import app_settings
from icf_jobs.api.mixins import  SearchCandidateListMixinForNotification
from icf_jobs.models import UserJobProfile
import logging
logger = logging.getLogger(__name__)


class JobNotification(SearchCandidateListMixinForNotification):
    """
    New Job Notification to be run a separate thread.
    """
    queryset = UserJobProfile.objects.all()

    def __init__(self, **kwargs):
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def run(self):

        job_slug = getattr(self, 'slug')
        job_url = None
        if job_slug:
            current_site = Site.objects.get_current()
            base_url = current_site.domain
            job_url = base_url + '/job/{}/'.format(job_slug)

        email_subject = str(app_settings.NEW_JOB_NOTIFICATION_EMAIL_SUBJECT)
        current_site = Site.objects.get_current()
        plaintext = get_template('../templates/jobs/users/send_new_job_notification_job_seeker.html')

        if job_url:
            queryset = self.get_queryset()
            if queryset:
                for user_job_profile in queryset:

                    dict = {'job_seeker_user_name': user_job_profile.user.display_name, 'job_url': job_url, 'current_site':current_site}
                    text_content = plaintext.render(dict)
                    msg = EmailMultiAlternatives(subject=email_subject, body=text_content,
                                                 to=[user_job_profile.user.email, ])
                    msg.content_subtype = "html"
                    msg.send()

            logger.info("End of sending new job notification email {} : {}".format(now(), threading.get_ident()))

def get_user_name(user):
    if user:
        if user.first_name and user.last_name:
            return user.first_name + " " + user.last_name
        else:
            return user.username
    else:
        logger.exception("user object is none.")
        raise ICFException(_("Something went wrong, please contact admin."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def send_recommender_email(email):
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

            email_template = 'templates/account/email/recommender_email.html'
            html = get_template(os.path.join(settings.BASE_DIR, email_template))

            html_content = html.render(ctx)

            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [email, ]

            subject = "Recommendation Email"

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
