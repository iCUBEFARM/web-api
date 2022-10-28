from django.contrib import admin

# Register your models here.
from icf_messages.models import AppMessagePerm


class AppMessagePermAdmin(admin.ModelAdmin):

    list_display = ['app_type', 'get_perm']

    class Meta:
        model = AppMessagePerm
        fields = ["app_type", "perm_reqd__codename"]
        verbose_name_plural = 'App Messaging Permissions'

    def get_perm(self, obj):
        return obj.perm_reqd.name

    get_perm.short_description = 'Permission required'  # Renames column head




admin.site.register(AppMessagePerm, AppMessagePermAdmin)
