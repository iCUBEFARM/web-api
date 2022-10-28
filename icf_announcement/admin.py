from django.contrib import admin

from icf_announcement.models import Announcement

# Register your models here.
class AnnouncementAdmin(admin.ModelAdmin):
    search_fields = ['title']

    class Meta:
        model = Announcement

admin.site.register(Announcement, AnnouncementAdmin)
