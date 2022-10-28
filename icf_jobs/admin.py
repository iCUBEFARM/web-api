from django.contrib import admin
from django.contrib.admin import ModelAdmin
from modeltranslation.admin import TranslationAdmin

# Register your models here.
from icf_jobs.models import Occupation, \
    SalaryFrequency, EducationLevel, \
    JobType, Skill, Relationship, CandidateSearchForJobMaster, Job


class EducationLevelAdmin(TranslationAdmin):
    list_display = ('level', 'desc', )

    class Meta:
        model = EducationLevel


class OccupationAdmin(TranslationAdmin):
    list_display = ('name', 'desc',)

    class Meta:
        model = Occupation


class SkillAdmin(TranslationAdmin):
    list_display = ('name', 'skill_type',)

    class Meta:
        model = Skill


class JobTypeAdmin(TranslationAdmin):
    list_display = ('job_type',)

    class Meta:
        model = JobType


class SalaryFrequencyAdmin(TranslationAdmin):
    list_display = ('frequency', 'desc',)

    class Meta:
        model = SalaryFrequency


class RelationshipAdmin(TranslationAdmin):
    list_display = ('relation', 'description',)

    class Meta:
        model = Relationship


class CandidateSearchForJobMasterAdmin(admin.ModelAdmin):
    class Meta:
        model = CandidateSearchForJobMaster

class JobAdmin(admin.ModelAdmin):
    search_fields = ['title']

    class Meta:
        model = Job


admin.site.register(Occupation, OccupationAdmin)
admin.site.register(SalaryFrequency, SalaryFrequencyAdmin)
admin.site.register(JobType, JobTypeAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Relationship, RelationshipAdmin)
admin.site.register(EducationLevel, EducationLevelAdmin)
admin.site.register(CandidateSearchForJobMaster, CandidateSearchForJobMasterAdmin)
admin.site.register(Job, JobAdmin)

