import os

from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.template.loader import get_template

from icf import settings

from django.utils.translation import ugettext_lazy as _

import logging

from icf_messages import app_settings

logger = logging.getLogger(__name__)


def send_email_notification_to_job_seeker(email_context):
    try:
        job_seeker_email_template = os.path.join("templates", "jobs", "send_job_invitation_to_job_seeker.html")
        template = get_template(os.path.join(settings.BASE_DIR, job_seeker_email_template))

        email_message = email_context.get('body')

        from_email = email_context.get('entity_email')
        to_email = email_context.get('job_seeker_email')

        try:
            current_site = Site.objects.get_current()
        except Exception as ex:
            logger.error("Failed to get site information: {e}".format(e=str(ex)))
            current_site = None
        # job_slug_list = email_context.get('job_slug_list', None)
        # protocol = 'https'
        # email_context.update({'current_site': current_site})
        # email_context.update({'protocol': protocol})
        # email_context.update({'job_slug_list': job_slug_list})
        email_context.update({'email_message': email_message})

        html_content = template.render(email_context)

        subject = app_settings.SEND_INVITE_TO_JOB_SEEKER_EMAIL

        if current_site:
            logger.debug("Current Site domain: {domain}".format(domain=current_site.domain))
            subject = "[{domain}] {subject}".format(domain=current_site.name, subject=subject)

        msg = EmailMessage(subject=subject,
                           body=html_content,
                           to=[to_email, ],
                           cc=[])

        msg.content_subtype = "html"
        msg.send()

    except Exception as ex:
        logger.exception("Failed to send message")
        pass


