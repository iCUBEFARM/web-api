import os
import ssl
from datetime import datetime
from django.core.files import File
from django.template.loader import render_to_string
from rest_framework import status
from weasyprint import HTML

from icf.settings import MEDIA_ROOT
from icf_auth.models import UserProfile
from icf_generic.Exceptions import ICFException
from icf_jobs.models import Skill, UserSkill

import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class PDFGeneratorForResume:
    def generate_resume_for_user(self, user_resume, user_education_list, user_work_experience_list,
                                                             user_skill_list, user_project_list,
                                                             user_relevant_link_list,
                                                             user_hobbie_list, base_url, user_profile_image_url):
        try:
            ''' generate pdf for resume user '''

            path = os.path.join(MEDIA_ROOT, "user_dynamic_resumes")
            filename = os.path.join(path, "user_resume.pdf")
            png_filename = os.path.join(path, "user_resume_screenshot.png")
            # template = get_template('jobs/users/dynamic_resume/user_dynamic_resume.html')
            user_key_skill_list = []
            user_language_skill_list = []
            user_computer_skill_list = []

            for user_skill in user_skill_list:
                if user_skill.skill.skill_type == Skill.KEY_SKILLS:
                    user_key_skill_list.append(user_skill)
                elif user_skill.skill.skill_type == Skill.LANGUAGE:
                    user_language_skill_list.append(user_skill)
                elif user_skill.skill.skill_type == Skill.COMPUTER_SKILLS:
                    user_computer_skill_list.append(user_skill)
                else:
                    raise Exception

            context = {}
            invoice = {}
            this_day = datetime.today()
            this_date = this_day.date
            invoice['date'] = this_date
            user = user_resume.job_profile.user
            user_profile = UserProfile.objects.get(user=user)
            context['user_mobile_no'] = user_resume.job_profile.user.mobile
            context['user_email'] = user_resume.job_profile.user.email
            context['user_location'] = str(user_profile.location.city)
            context['user_resume'] = user_resume
            context['user_education_list'] = user_education_list
            context['user_work_experience_list'] = user_work_experience_list
            context['user_skill_list'] = user_skill_list
            context['user_key_skill_list'] = user_key_skill_list
            context['user_language_skill_list'] = user_language_skill_list
            context['user_computer_skill_list'] = user_computer_skill_list
            context['user_relevant_link_list'] = user_relevant_link_list
            context['user_project_list'] = user_project_list
            context['user_hobbie_list'] = user_hobbie_list
            if user_profile_image_url:
                context['user_profile_image_url'] = user_profile_image_url
            else:
                context['user_profile_image_url'] = None
            context['space_string'] = ''
            context['skill_expertise_beginner'] = UserSkill.BEGINNER
            context['skill_expertise_novice'] = UserSkill.NOVICE
            context['skill_expertise_intermediate'] = UserSkill.INTERMEDIATE
            context['skill_expertise_advanced'] = UserSkill.ADVANCED
            context['skill_expertise_expert'] = UserSkill.EXPERT

            ssl._create_default_https_context = ssl._create_unverified_context
            html_string = render_to_string('jobs/users/dynamic_resume/user_dynamic_resume.html', context)
            html = HTML(string=html_string, base_url=base_url)
            pdf_file_data = html.write_pdf()

            with open(filename, 'wb') as f:
                f.seek(0)
                f.write(pdf_file_data)
            os.chmod(filename, 0o777)
            pdf_file = open(filename, 'rb')
            user_resume.resume = File(pdf_file)
            user_resume.save(update_fields=['resume'])

            # generate screen shot of the first page of the PDF

            doc = html.render()  # returns the Document object
            # print(type(doc))
            page = doc.pages[0]
            doc.copy([page]).write_png(png_filename, resolution=300)

            image_file = open(png_filename, 'rb')
            user_resume.thumbnail = File(image_file)
            user_resume.save(update_fields=['thumbnail'])

            resume_urls_dict = {}
            resume_urls_dict['resume_url'] = user_resume.resume.url
            resume_urls_dict['thumbnail_url'] = user_resume.thumbnail.url

            return resume_urls_dict

        except UserProfile.DoesNotExist as upde:
            logger.error("UserProfile does not exist :{reason}".format(reason=str(upde)))
            raise ICFException(_("Could not create User resume, please try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error("Could not create User resume reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Could not create User resume, please try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        # email_body = str(app_settings.PRODUCT_PURCHASE_RECEIPT_EMAIL_BODY).format(user.display_name)

        # msg = EmailMessage(subject=app_settings.PRODUCT_PURCHASE_RECEIPT_SUBJECT,
        #                    body=email_body,
        #                    to=[user.email, ],
        #                    cc=app_settings.PRODUCT_PURCHASE_RECEIPT_EMAIL_CC)

        # msg.attach('iCUBEFARM-Products-Payment-Receipt.pdf', open(filename, 'rb').read(), 'application/pdf')
        # msg.content_subtype = "html"
        # msg.send()
        # message = settings.ICF_NOTIFICATION_SETTINGS.get('PAYMENT_BILL_NOTIFICATION')
        # details = settings.ICF_NOTIFICATION_SETTINGS.get('INVOICE_NOTIFICATION_DETAIL').format(user.display_name, message, entity.display_name)
        # ICFNotificationManager.add_notification(user=user, message=message, details=details)

