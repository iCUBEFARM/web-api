from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress


# Register your models here.
from icf_auth.models import UserProfile, User


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'mobile', 'is_staff', 'is_active',)
    search_fields = ['username', 'email']

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_first_name', 'get_last_name', 'get_email', 'get_mobile', 'gender', 'get_nationality',
                    'get_language',)

    class Meta:
        model = UserProfile

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, obj):
        return obj.user.last_name

    def get_email(self, obj):
        return obj.user.email

    def get_mobile(self, obj):
        return obj.user.mobile

    def get_nationality(self, obj):
        if obj.nationality:
            return obj.nationality.country
        else:
            return None

    def get_language(self, obj):
        if obj.language:
            return obj.language.name
        else:
            return None

    get_first_name.admin_order_field = 'user__first_name'  # Allows column order sorting
    get_first_name.short_description = 'First Name'  # Renames column head
    get_last_name.short_description = 'Last Name'  # Renames column head
    get_email.short_description = 'Email'  # Renames column head
    get_mobile.short_description = 'Mobile'  # Renames column head
    get_nationality.short_description = 'Nationality'  # Renames column head
    get_language.short_description = 'Language'  # Renames column head


admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(User, UserAdmin)
# admin.site.unregister(EmailAddress)
admin.site.unregister(Group)
# admin.site.register(Site)
#admin.site.unregister(Token)