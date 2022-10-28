import threading
import mailchimp
from django.conf import settings

import logging

from mailchimp import ListDoesNotExistError, EmailNotExistsError, ListAlreadySubscribedError


logger = logging.getLogger(__name__)
failed_users_logger = logging.getLogger("icf.integrations.newsletter")


def get_user_from_email(email):
    return email.split('@')[0]


class SubscribeNewsletterMail(object):
    def __init__(self, email, preferred_language, user):
        self.email = email
        self.preferred_language = preferred_language
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.mobile = user.mobile
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        API_KEY = settings.MAILCHIMP_API_KEY
        api = mailchimp.Mailchimp(API_KEY)
        try:
            list_id = settings.MAILCHIMP_NL_LIST.get(self.preferred_language)

            # result = api.lists.subscribe(list_id, {'email': self.email}, double_optin=False)

            result = api.lists.subscribe(list_id, email={'email': self.email}, merge_vars={'email': self.email,
                'FNAME': self.first_name,
                'LNAME': self.last_name,
                'PHONE': self.mobile,
            }, double_optin=False)
            logger.info("Successfully added the  user with email:{email} to the {language} list Newsletter\n".format(
                email=self.email, language=self.preferred_language))
        except ListDoesNotExistError as le:
            failed_users_logger.error("could not add user because list does not exist with id :{id} \n".format(id=settings.MAILCHIMP_NL_LIST.get(self.preferred_language)))
        except EmailNotExistsError:
            failed_users_logger.error("could not add user with email:{email} does not exist \n".format(email=self.email))
        except ListAlreadySubscribedError as ae:
            failed_users_logger.error("could not add user because user with email: {email} already added to {language} list\n".format(
                            email=self.email, language=self.preferred_language))
        except Exception as e:
            failed_users_logger.error("Could not add the user with email {email} to {language} list. {cause} \n".format(
                email=self.email, language=self.preferred_language, cause=str(e)))


class ICFNewsletterManager:

    # def __init__(self, email=None, preferred_language=None):
    #     self.email = email
    #     self.preferred_language = preferred_language
    #     # self.get_newsletter_service()

    def get_newsletter_service(self, email, preferred_language, user):
        return SubscribeNewsletterMail(email, preferred_language, user)
