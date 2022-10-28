from django.core.mail import EmailMessage
from django.urls import reverse

from icf_career_fair import app_settings
from icf_item.models import Item
from django.contrib.sites.models import Site
from icf_career_fair.models import CareerFairImageType, CareerFairAdvertisement
import logging

logger = logging.getLogger(__name__)


class CareerFairUtil:
    def send_career_fair_review_email(request, career_fair_obj):
        email_subject = None
        email_body = None
        email_to = None
        """
        Sending emails to the customer / user in cases of review, approved and rejected.
        """
        email_subject = str(app_settings.CAREER_FAIR_REVIEW_EMAIL_SUBJECT).format(career_fair_obj.title)

        if career_fair_obj.status == Item.ITEM_UNDER_REVIEW:
            logger.info("Career Fair under review {0}".format(career_fair_obj.slug))
            email_body = str(app_settings.CAREER_FAIR_SENT_FOR_REVIEW_EMAIL_BODY).format(request.user.display_name)
        elif career_fair_obj.status == Item.ITEM_REJECTED:
            logger.info("Career Fair rejected {0}".format(career_fair_obj.slug))
            # Send reject email
            email_body = str(app_settings.CAREER_FAIR_ADMIN_REJECTED_EMAIL_BODY).format(request.user.display_name)
        elif career_fair_obj.status == Item.ITEM_ACTIVE:
            logger.info("Career Fair approved {0}".format(career_fair_obj.slug))
            email_body = str(app_settings.CAREER_FAIR_ADMIN_APPROVED_EMAIL_BODY).format(request.user.display_name)

        try:
            user_mail = EmailMessage(subject=email_subject,
                                     body=email_body,
                                     to=[career_fair_obj.owner.email, ],
                                     cc=[str(app_settings.CAREER_FAIR_EMAIL_CC), ])
            user_mail.content_subtype = "html"
            user_mail.send()
        except Exception as e:
            logger.info("Could not send the Career Fair email to user")

        """
        In case of under review send a notification to the admin 
        """
        admin_url = reverse('admin:%s_%s_change' % (career_fair_obj._meta.app_label, career_fair_obj._meta.model_name),
                            args=[career_fair_obj.id])
        if career_fair_obj.status == Item.ITEM_UNDER_REVIEW:
            try:

                email_body = str(app_settings.CAREER_FAIR_ADMIN_REVIEW_EMAIL_BODY).format(admin_url)
                admin_mail = EmailMessage(subject=email_subject,
                                          body=email_body,
                                          to=[app_settings.CAREER_FAIR_EMAIL_CC, ])
                admin_mail.content_subtype = "html"
                admin_mail.send()
            except Exception as e:
                logger.info("Could not send the Career Fair Review email to admin")

    @staticmethod
    def send_free_subscription_email(entity, user, start_date, end_date):
        email_subject = None
        email_body = None
        email_to = None
        """
        Sending emails to the customer / user in cases of review, approved and rejected.
        """
        email_subject = str(app_settings.FREE_CAREER_FAIR_SUBSCRIPTION_EMAIL_SUBJECT)

        logger.info("Free Subscription Activated")

        email_body = str(app_settings.FREE_CAREER_FAIR_SUBSCRIPTION_EMAIL_BODY).format(user.display_name, entity.name,
                                                                                       start_date,
                                                                                       end_date)

        try:
            user_mail = EmailMessage(subject=email_subject,
                                     body=email_body,
                                     to=[user.email, ],
                                     cc=[str(app_settings.CAREER_FAIR_EMAIL_CC), ])
            user_mail.content_subtype = "html"
            user_mail.send()
        except Exception as e:
            logger.info("Could not send the Career Fair free subscription  email to user")

        """
        In case of under review send a notification to the admin 
        """

    @staticmethod
    def send_add_advertisement_link_to_owner(entity, user, link):
        email_subject = None
        email_body = None
        email_to = None
        """
        Sending emails to the customer / user in cases of review, approved and rejected.
        """
        email_subject = str(app_settings.ADD_ADVERTISEMENT_LINK_TO_OWNER_EMAIL_SUBJECT)

        current_site = Site.objects.get_current()
        base_url = current_site.domain
        manage_entity_url = "https://" + base_url + '/entity/manage-entity/{}/'.format(entity.slug)

        logger.info("Send advertisement to owner")

        email_body = str(app_settings.ADD_ADVERTISEMENT_LINK_TO_OWNER_EMAIL_BODY).format(user.display_name, entity.name,
                                                                                         manage_entity_url)

        try:
            user_mail = EmailMessage(subject=email_subject,
                                     body=email_body,
                                     to=[user.email,],
                                     cc=[str(app_settings.CAREER_FAIR_EMAIL_CC), ])
            user_mail.content_subtype = "html"
            user_mail.send()
        except Exception as e:
            logger.info("Could not send the Career Fair free subscription  email to user")

        """
        In case of under review send a notification to the admin 
        """

    @staticmethod
    def send_add_advertisement_link_buyer(entity, user, link):
        email_subject = None
        email_body = None
        email_to = None
        """
        Sending emails to the customer / user in cases of review, approved and rejected.
        """
        email_subject = str(app_settings.ADD_ADVERTISEMENT_LINK_TO_OWNER_EMAIL_SUBJECT)

        logger.info("Advertisement purchased, send notification email")

        current_site = Site.objects.get_current()
        base_url = current_site.domain
        manage_entity_url = "https://" + base_url + '/entity/manage-entity/{}/'.format(entity.slug)

        email_body = str(app_settings.ADD_ADVERTISEMENT_LINK_TO_OWNER_EMAIL_BODY).format(user.display_name, entity.name,
                                                                                         manage_entity_url)

        try:
            user_mail = EmailMessage(subject=email_subject,
                                     body=email_body,
                                     to=[user.email,],
                                     cc=[str(app_settings.CAREER_FAIR_EMAIL_CC), ])
            user_mail.content_subtype = "html"
            user_mail.send()
        except Exception as e:
            logger.info("Could not send the Career Fair free subscription  email to user")

        """
        In case of under review send a notification to the admin 
        """

    @staticmethod
    def advertisement_status_change_email(request, obj):
        email_subject = None
        email_body = None
        email_to = None
        current_site = Site.objects.get_current()
        base_url = current_site.domain
        manage_entity_url = "https://" + base_url + '/entity/manage-entity/{}/'.format(obj.entity.slug)
        type = None
        if obj.ad_image_type == CareerFairImageType.DESKTOP_IMAGE:
            type = "Desktop"
        else:
            type = "Mobile"
        if obj.ad_status == CareerFairAdvertisement.APPROVED:

            email_subject = str(app_settings.ADVERTISEMENT_APPROVED_EMAIL_SUBJECT).format(type, obj.career_fair.title)
            email_body = str(app_settings.ADVERTISEMENT_APPROVED_EMAIL_BODY).format(obj.user.display_name,
                                                                                    obj.entity.name, type,
                                                                                    obj.career_fair.title,
                                                                                    manage_entity_url)
            logger.info("advertisement status approved email")
        if obj.ad_status == CareerFairAdvertisement.REJECTED:
            email_subject = str(app_settings.ADVERTISEMENT_REJECTED_EMAIL_SUBJECT).format(type,
                                                                                          obj.career_fair.title)
            email_body = str(app_settings.ADVERTISEMENT_REJECTED_EMAIL_BODY).format(obj.user.display_name,
                                                                                    obj.entity.name, type,
                                                                                    obj.career_fair.title,
                                                                                    manage_entity_url)
            logger.info("advertisement status rejected  email")



        try:
            user_mail = EmailMessage(subject=email_subject,
                                     body=email_body,
                                     to=[obj.user.email,],
                                     cc=[str(app_settings.CAREER_FAIR_EMAIL_CC), ])
            user_mail.content_subtype = "html"
            user_mail.send()
        except Exception as e:
            logger.info("Could not send the Career Fair free subscription  email to user")

            """
            In case of under review send a notification to the admin 
            """
