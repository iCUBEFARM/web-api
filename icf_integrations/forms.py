import threading
import time

from dal import autocomplete
from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.forms import ModelForm, Textarea
from django.shortcuts import render

from icf_auth.models import User
from icf_generic.models import Country
from icf_integrations.app_settings import RECIPIENT_CHOICES
from icf_integrations.models import SentGroupSms


class SendGroupSmsForm(ModelForm):

    # nationality = forms.ModelChoiceField(queryset=Country.objects.all(),to_field_name='id',empty_label=None,
    #                                      widget=autocomplete.ModelSelect2Multiple(
    #                                          url='/api/generic/country-autocomplete/'))

    nationality = forms.ModelMultipleChoiceField(queryset=Country.objects.all(),
                                          widget=autocomplete.ModelSelect2Multiple(
                                            url='/api/generic/country-autocomplete/'), required=False)

    recipient_type = forms.MultipleChoiceField(choices=RECIPIENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super(SendGroupSmsForm, self).__init__(*args, **kwargs)
        # self.fields['messages'].required = False


    # def clean_nationality(self):
    #     if self.errors.get('nationality'):
    #         del self.errors['nationality']
    #
    #     country = Country
    #     data['nationality'] = Country.objects.get(pk=nationality)
    #
    # def clean(self):
    #     if self.errors.get('nationality'):
    #         del self.errors['nationality']
    #     if self.errors.get('recipient_type'):
    #         del self.errors['recipient_type']
    #
    #     data = self.cleaned_data
    #     nationality = self.data.get('nationality')
    #     data['nationality'] = Country.objects.get(pk=nationality)
    #     data['recipient_type'] = self.data.get('recipient_type')
    #     return data

    class Meta:
        model = SentGroupSms
        exclude = ['messages','success_count','failure_count']
        widgets = {
            # 'messages': Textarea(attrs={'cols': 33, 'rows': 3}),
            'messages_en':Textarea(attrs={'cols': 33, 'rows': 3}),
            'messages_es': Textarea(attrs={'cols': 33, 'rows': 3}),
            'messages_fr': Textarea(attrs={'cols': 33, 'rows': 3}),
        }

# class GroupSmsModel(object):
#     class _meta:
#         app_label = 'icf_integrations'  # This is the app that the form will exist under
#         model_name = 'custom-form'
#         app_config = 'send-group-sms'# This is what will be used in the link url
#         verbose_name_plural = 'Send Group Sms'  # This is the name used in the link text
#         object_name = 'ObjectName'
#
#         swapped = False
#         abstract = False


# class CustomSendGroupSmsAdminForm(admin.ModelAdmin):
#
#     def has_add_permission(*args, **kwargs):
#         return False
#
#     def has_change_permission(*args, **kwargs):
#         return True
#
#     def has_delete_permission(*args, **kwargs):
#         return False
#
#
#     def send_group_message_english(self):
#         # time.sleep(5)
#         pass
#
#     def send_group_message_spanish(self):
#         # time.sleep(5)
#         pass
#
#
#     def send_group_message_french(self):
#         pass
#
#
#     def changelist_view(self, request):
#         context = {'title': 'Group Sms Form'}
#         if request.method == 'POST':
#             form = SendGroupSmsForm(request.POST)
#             if form.is_valid():
#
#                 nationality = form.cleaned_data.get('nationality')
#                 message_spanish = form.cleaned_data.get('message_spanish')
#                 message_english = form.cleaned_data.get('message_english')
#                 message_french = form.cleaned_data.get('message_french')
#                 recipient_type = form.cleaned_data.get('recipient_type')
#
#                 user_list = User.objects.filter(userprofile__nationality=nationality)
#
#                 # SentGroupSms.objects.create(messages_en=message_english, messages_fr=message_french,
#                 #                             messages_es=message_spanish, users=user_list)
#
#                 english_message_thread = threading.Thread(target=self.send_group_message_english, name='Thread-english')
#                 spanish_message_thread = threading.Thread(target=self.send_group_message_spanish, name='Thread-spanish')
#                 french_message_thread = threading.Thread(target=self.send_group_message_french, name='Thread-french')
#
#                 english_message_thread.start()
#                 spanish_message_thread.start()
#                 french_message_thread.start()
#
#
#             else:
#                 raise Exception
#
#         else:
#             form = SendGroupSmsForm()
#
#         context['form'] = form
#         return render(request, 'admin/group_sms.html', context)