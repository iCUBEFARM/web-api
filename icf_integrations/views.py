import threading
import time
from threading import Thread
from time import sleep

from django.contrib.messages.context_processors import messages
from django.http import HttpResponseRedirect, response, request
from django.shortcuts import render

# Create your views here.
from django.template import response
from django.utils.timezone import now
from django.views.generic import FormView
from rest_framework import reverse

from icf_auth.models import User
from icf_entity.models import Entity, EntityPerms
from icf_integrations.forms import SendGroupSmsForm
from icf_integrations.mobile import SMSManager
from icf_integrations.models import SentGroupSms
from icf_integrations import app_settings
from icf_jobs.models import JobPerms, UserEducation, UserJobProfile
import logging
from django.contrib import messages

logger = logging.getLogger(__name__)


class GroupSMSThread:
    def __init__(self,request=None, user_list=[],msg_body=[]):
        self.request = request
        self.en_list = user_list[0]
        self.en_msg = msg_body[0]
        self.es_list = user_list[1]
        self.es_msg = msg_body[1]
        self.fr_list = user_list[2]
        self.fr_msg = msg_body[2]


    def run(self):
        messages.add_message(self.request, messages.INFO, "Sending group SMS task triggered.Please refresh the page after some time")
        if self.en_msg:
            SMSManager.get_sms_gateway(self).send_group_sms(user_list=self.en_list, msg_body=self.en_msg)
        if self.es_msg:
            SMSManager.get_sms_gateway(self).send_group_sms(user_list=self.es_list, msg_body=self.es_msg)
        if self.fr_msg:
            SMSManager.get_sms_gateway(self).send_group_sms(user_list=self.fr_list, msg_body=self.fr_msg)

        logger.info("End of Group SMS send {} : {}".format(now(), threading.get_ident()))


class GroupSmsView(FormView):
    template_name = 'admin/group_sms.html'
    form_class = SendGroupSmsForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        qs = User.objects.all()
        form = self.form_class(request.POST)
        if form.is_valid():
            nationality = form.cleaned_data.get('nationality')
            message_spanish = form.cleaned_data.get('messages_es')
            message_english = form.cleaned_data.get('messages_en')
            message_french = form.cleaned_data.get('messages_fr')
            recipient_type = form.cleaned_data.get('recipient_type')

            # Get filter users based on country
            if nationality:
                qs = qs.filter(userprofile__nationality__in=nationality)

            for rtype in recipient_type:
                if rtype == app_settings.PROFESSIONAL_USERS:
                    # All users
                    qs = qs
                else:

                    if rtype == str(app_settings.ADMINISTRATORS):
                        # Find all administrators
                        qs = qs.filter(groups__name__endswith=EntityPerms.ENTITY_ADMIN)
                    if rtype == str(app_settings.RECRUITERS):
                        # Find all job admins
                        qs = qs.filter(groups__name__endswith=JobPerms.JOB_ADMIN)
                    if rtype == str(app_settings.JOBSEEKERS):
                        # Find all users with a completed job profile
                        qs = qs.filter(userjobprofile__usereducation__isnull=False)

            english_qs = qs
            french_qs = qs
            spanish_qs = qs

            english_users = english_qs.filter(userprofile__language__code='en')
            spanish_users = spanish_qs.filter(userprofile__language__code='es')
            french_users = french_qs.filter(userprofile__language__code='fr')



            user_list=[english_users,spanish_users,french_users]
            msg_body =[message_english,message_spanish,message_french]
            group_sms = GroupSMSThread(request=request,user_list=user_list, msg_body=msg_body)
            t = Thread(target=group_sms.run)
            t.start()

            logger.info("Starting Thread at {}".format(now(), threading.get_ident()))

            logger.info("Returning to UI at {}".format(now(), threading.get_ident()))

            return HttpResponseRedirect('/icube-admin/icf_integrations/sentgroupsms/')

        return render(request, self.template_name, {'form': form,'title': 'Group Sms Form'})

