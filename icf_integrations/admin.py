from django.conf.urls import url
from django.contrib import admin

# Register your models here.
from modeltranslation.admin import TranslationAdmin

from icf_auth.models import User
from icf_integrations.models import SentGroupSms


class UserAdmin(admin.ModelAdmin):
    list_display = ('display_name','mobile','get_language','get_nationality',)
    list_filter = ('userprofile__language','userprofile__nationality')

    class Meta:
        model = User
        fields = '__all__'


    def get_nationality(self, obj):
        return obj.userprofile.nationality.country

    def get_language(self, obj):
        return obj.userprofile.language.name

class SendGroupSmsAdmin(TranslationAdmin):
    list_display = ('messages','sent_at','success_count','failure_count')
    change_list_template = "admin/group_sms_button.html"

    def has_add_permission(self, request, obj=None):
        return False

    class Meta:
        model = SentGroupSms
        fields = '__all__'


# admin.site.register(SentGroupSms, CustomSendGroupSmsAdminForm)
# admin.site.register(User,UserAdmin)
admin.site.register(SentGroupSms,SendGroupSmsAdmin)


