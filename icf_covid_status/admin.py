from django.contrib import admin
from django.contrib.admin import ModelAdmin
from modeltranslation.admin import TranslationAdmin

# Register your models here.
from icf_covid_status.models import UserWorkStatus, EGSector, CurrentWorkStatus, CurrentCompensationStatus


class EGSectorAdmin(TranslationAdmin):
    list_display = ('name', 'description')

    class Meta:
        model = EGSector


class CurrentWorkStatusAdmin(TranslationAdmin):
    list_display = ('name', 'description')

    class Meta:
        model = CurrentWorkStatus


class CurrentCompensationStatusAdmin(TranslationAdmin):
    list_display = ('name', 'description')

    class Meta:
        model = CurrentCompensationStatus


class UserWorkStatusAdmin(ModelAdmin):
    actions = ['export_as_csv']
    list_display = ('user', 'company_name', 'position', 'sector', 'country', 'current_work_status',
                    'current_compensation_status', 'created')

    # search_fields = ('sector', 'current_work_status', 'current_compensation_status',)
    # def company_name(self, instance):
    #     return instance.company_name
    #
    # def current_work_status(self, instance):
    #     return instance.current_work_status.name
    #
    # def current_compensation_status(self, instance):
    #     return instance.current_compensation_status.name
    #
    # company_name.short_description = 'Company Name'
    # current_work_status.short_description = 'Current Work Status'
    # current_compensation_status.short_description = 'Current Compensation Status'

    class Meta:
        model = UserWorkStatus

    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        f = open('icubefarm_user_work_status.csv', 'w')
        writer = csv.writer(f)
        writer.writerow(['user', 'company name', 'position', 'sector',
                         'country', 'current work status', 'current compensation status', 'created'])

        for s in queryset:
            writer.writerow([s.user, s.company_name, s.position, s.sector, s.country,
                             s.current_work_status, s.current_compensation_status, s.created, s.updated])

        f.close()

        f = open('icubefarm_user_work_status.csv', 'r')
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=icubefarm_user_work_status.csv'
        return response


admin.site.register(EGSector, EGSectorAdmin)
admin.site.register(CurrentWorkStatus, CurrentWorkStatusAdmin)
admin.site.register(CurrentCompensationStatus, CurrentCompensationStatusAdmin)
admin.site.register(UserWorkStatus, UserWorkStatusAdmin)

