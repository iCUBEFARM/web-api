

import itertools
from datetime import datetime, timezone

from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.db import models

# Create your models here.
from django.db.models.signals import pre_save
from django.dispatch.dispatcher import receiver
from django.utils.text import slugify
from icf_auth.models import User, UserProfile
from icf_entity.models import Entity, EntityPerms, Industry, Logo, Sector
from icf_generic.api.serializers import SponsoredListSerializer
from icf_generic.fields import ICFApproxDateField
from icf_generic.models import Country, Currency, Sponsored, City, Type, Category
from icf_item.models import Item, ItemDraft
from django.utils.translation import ugettext_lazy as _
import logging
import os

from icf_jobs.JobHelper import CreateUserResumeThumbnail
from icf_jobs.app_settings import USER_RESUME_SCREEN_SHOT_IMAGE_THUMBNAIL_SIZE

logger = logging.getLogger(__name__)

JOB_PROFILE_FILE_DIR = "jobs/resumes"


def upload_job_profile_file_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=JOB_PROFILE_FILE_DIR, file=instance.user.slug, ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=JOB_PROFILE_FILE_DIR, file=filename)


JOBSEEKER_DYNAMIC_RESUME_THUMBNAIL_FILE_DIR = "jobs/dynamic_resumes/"


def upload_dynamic_resume_thumbnail_media_location(instance, filename):
    try:
        return "{dir1}/{dir2}/{dir3}/{file}{ext}".format(dir1=JOBSEEKER_DYNAMIC_RESUME_THUMBNAIL_FILE_DIR, dir2=instance.job_profile.user.slug,
                                                  dir3='thumbnail', file=instance.job_profile.user.slug,
                                                  ext=os.path.splitext(filename)[1])
    except:
        return "{dir1}/{dir2}/{dir3}/{file}".format(dir1=JOBSEEKER_DYNAMIC_RESUME_THUMBNAIL_FILE_DIR, dir2=instance.job_profile.user.slug,
                                                  dir3='thumbnail', file=instance.job_profile.user.slug)


JOBSEEKER_DYNAMIC_RESUME_FILE_DIR = "jobs/dynamic_resumes"


def upload_dynamic_resume_media_location(instance, filename):
    try:
        # print(instance.job_profile.user.slug)
        return "{dir1}/{dir2}/{dir3}/{file}{ext}".format(dir1=JOBSEEKER_DYNAMIC_RESUME_FILE_DIR,
                                                  dir2=instance.job_profile.user.slug,
                                                  dir3='resumes',
                                                  file=instance.job_profile.user.slug,
                                                  ext=os.path.splitext(filename)[1])
    except:
        print(instance.job_profile.user.slug)
        return "{dir1}/{dir2}/{dir3}/{file}".format(dir1=JOBSEEKER_DYNAMIC_RESUME_FILE_DIR,
                                                  dir2=instance.job_profile.user.slug,
                                                  dir3='resumes',
                                                  file=instance.job_profile.user.slug)


class Skill(models.Model):
    KEY_SKILLS = "key_skill"
    COMPUTER_SKILLS = "computer_skill"
    LANGUAGE = "language"
    SKILL_CHOICES = ((KEY_SKILLS, _("key skills")), (COMPUTER_SKILLS, _("computer skills")), (LANGUAGE, _("language skills")))
    name = models.CharField(_("skill"), max_length=200)
    skill_type = models.CharField(_("skill type"), max_length=50, choices=SKILL_CHOICES)

    def __str__(self):
        return "{0} : {1}".format(self.name,  self.skill_type)

    class Meta:
        unique_together = ('name', 'skill_type')
        verbose_name_plural = 'skills'


class SalaryFrequency(models.Model):
    frequency = models.CharField(_("salary frequency"), max_length=40)
    desc = models.CharField(max_length=50)

    def __str__(self):
        return self.frequency

    class Meta:
        verbose_name_plural = 'SalaryFrequencies'


class EducationLevel(models.Model):
    level = models.CharField(_("level"), max_length=80)
    desc = models.CharField(max_length=80)

    def __str__(self):
        return self.level

    class Meta:
        verbose_name_plural = 'EducationLevels'

class Occupation(models.Model):
    name = models.CharField(_("name"), max_length=120)
    desc = models.CharField(max_length=80)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Occupations'


class JobPerms():
    JOB_CREATE = 'icf_job_cr'
    JOB_PUBLISH = 'icf_job_pub'
    JOB_RECRUIT = 'icf_job_rct'
    JOB_ADMIN = 'icf_job_adm'

    JOB_PERM_CHOICES = (("JOB_CREATE", JOB_CREATE),
                            ("JOB_PUBLISH", JOB_PUBLISH ),
                            ("JOB_RECRUIT", JOB_RECRUIT),
                            ("JOB_ADMIN", JOB_ADMIN), )


    @classmethod
    def get_job_perms(cls):
        return dict(cls.JOB_PERM_CHOICES)

    @classmethod
    def get_admin_perm(cls):
        return cls.JOB_ADMIN

    @classmethod
    def get_entity_group(cls, entity, perm):
        return EntityPerms.get_entity_group(entity, perm)


class JobType(models.Model):
    job_type = models.CharField(_("name"), max_length=32)

    def __str__(self):
        return self.job_type

    class Meta:
        verbose_name_plural = 'JobTypes'


class Job(Item):
    MAX_JOB_EXPERIENCE_YEARS = 40
    MONTHS = 12
    EXPERIENCE_YEARS_CHOICES = [(year, year) for year in range(0, MAX_JOB_EXPERIENCE_YEARS + 1)]  # 0 - 40 years
    MONTHS_CHOICES = [(month, month) for month in range(MONTHS + 1)]  # 0 - 12 months
    MIN_OPEN_POSITIONS = 1


    occupation = models.ForeignKey(Occupation, on_delete=models.CASCADE, related_name="jobs")

    experience_years = models.SmallIntegerField(choices=EXPERIENCE_YEARS_CHOICES)
    experience_months = models.SmallIntegerField(choices=MONTHS_CHOICES)

    salary_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="jobs")
    salary_frequency = models.ForeignKey(SalaryFrequency, on_delete=models.CASCADE, related_name="jobs")
    salary = models.DecimalField(max_digits=8, decimal_places=2)
    salary_is_public = models.BooleanField(default=False)

    education_level = models.ForeignKey(EducationLevel, on_delete=models.CASCADE, related_name="jobs")

    open_positions = models.SmallIntegerField(default=MIN_OPEN_POSITIONS)
    job_type = models.ForeignKey(JobType, on_delete=models.CASCADE,related_name="jobs")
    sponsored = GenericRelation(Sponsored, related_query_name="jobs")
    external_website_visibility = models.BooleanField(default=False)
    external_website_url = models.URLField(blank=True, null=True)
    recruiter_email_visibility = models.BooleanField(default=False)
    recruiter_email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Jobs'
        ordering = ['-created', ]

    def get_sponsored_info(self):
        if self.status == Job.ITEM_ACTIVE and self.expiry >= datetime.now(timezone.utc):
            serializer = SponsoredListSerializer()
            serializer.title = self.title
            serializer.description = self.entity.description
            serializer.entity_name = self.entity.name
            serializer.location = self.location
            serializer.slug = self.slug
            serializer.content_type = self.__class__.__name__
            # right now published date is created date itself
            # (published date field  is not present in Job model)
            serializer.published_date = self.created
            serializer.expiry_date = self.expiry
            serializer.logo = self.get_entity_logo()
            return serializer
        else:
            return None

    def get_entity_logo(self):
        try:
            return Logo.objects.get(entity=self.entity).image.url
        except ObjectDoesNotExist:
            return ""


class JobSkill(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="job_skills")

    def __str__(self):
        return "{0}:{1}".format(self.job, self.skill)

    class Meta:
        verbose_name_plural = 'JobSkills'


class UserJobProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pro_bio = models.CharField(_("professional biography"), max_length=500, null=True, blank=True)
    has_experience = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xlsx', '.xls']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u' Unsupported file extension.')


class UserResume(models.Model):
    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=True, blank=True)
    name = models.CharField(_("name"), max_length=100, null=True, blank=True)
    thumbnail = models.ImageField(upload_to=upload_dynamic_resume_thumbnail_media_location, null=True, blank=True)
    resume = models.FileField(upload_to=upload_dynamic_resume_media_location,
                              validators=[validate_file_extension], max_length=200, null=True, blank=True)
    biography = models.CharField(_("biography"), max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    slug = models.SlugField(blank=True, unique=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.job_profile.user.username

    def update(self, *args, **kwargs):
        # save for image
        # super(UserResume, self).save(*args, **kwargs)

        if self.thumbnail:
            CreateUserResumeThumbnail().make_thumbnail(self.thumbnail, self.thumbnail,
                                                   USER_RESUME_SCREEN_SHOT_IMAGE_THUMBNAIL_SIZE, 'thumbnail')
        else:
            pass

        # save for thumbnail and icon
        super(UserResume, self).save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     # save for image
    #     # super(UserResume, self).save(*args, **kwargs)
    #
    #     if self.thumbnail:
    #         CreateUserResumeThumbnail().make_thumbnail(self.thumbnail, self.thumbnail,
    #                                                USER_RESUME_SCREEN_SHOT_IMAGE_THUMBNAIL_SIZE, 'thumbnail')
    #     else:
    #         pass
    #
    #     # save for thumbnail and icon
    #     super(UserResume, self).save(*args, **kwargs)


class JobUserApplied(models.Model):
    NEW = 1
    MAY_BE = 2
    YES = 3
    NO = 4
    USER_STATUS_CHOICES = (
        (MAY_BE, _('Maybe')), (YES, _('Yes')), (NO, _('NO')))
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)
    status = models.SmallIntegerField(choices=USER_STATUS_CHOICES, default=NEW)
    resume = models.ForeignKey(UserResume, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return "{} : {}".format(self.user, self.job)

    class Meta:
        verbose_name_plural = 'JobsUserApplied'


# class UserJobProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     pro_bio = models.CharField(_("professional biography"), max_length=250, null=True, blank=True)
#     has_experience = models.BooleanField(default=False)
#
#     def __str__(self):
#         return self.user.username


class UserEducation(models.Model):
    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    education_level = models.ForeignKey(EducationLevel, on_delete=models.CASCADE)
    school = models.CharField(_("school"), max_length=100)
    from_year = models.PositiveIntegerField()
    to_year = models.PositiveIntegerField()
    certification = models.CharField(_("certification"), max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return "{} : {}".format(self.job_profile.user, self.education_level)

    class Meta:
        verbose_name_plural = 'UserEducation'

class Reference(models.Model):
    name = models.CharField(_('name'), max_length=100, blank=True)
    position = models.CharField(_('position'), max_length=100, blank=True)
    phone = models.CharField(validators=[User.PHONE_REGEX], max_length=25, blank=True)  # validators should be a list
    email = models.EmailField(_('email address'), blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        verbose_name_plural = 'References'


class UserWorkExperience(models.Model):
    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    job_title = models.CharField(_("job title"), max_length=250)
    worked_from = ICFApproxDateField()
    worked_till = ICFApproxDateField()
    entity = models.CharField(_("entity"), max_length=200)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    reference = GenericRelation(Reference, related_query_name="work-experience", null=True)

    def __str__(self):
        return "{} : {}".format(self.job_profile, self.job_title)

    class Meta:
        verbose_name_plural = 'UserWorkExperience'

#  Model For Conferences and workshops attended by the jobe seeker
class UserConferenceWorkshop(models.Model):
    PARTICIPANT = 1
    MODERATOR = 2
    USER_PARTICIPATION_ROLE_CHOICES = (
        (PARTICIPANT, _('Paticipant')), (MODERATOR, _('Moderator')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    name = models.CharField(_("name"), max_length=500, null=False, blank=False)
    organizer = models.CharField(_("organizer"), max_length=250, null=True, blank=True)
    description = models.TextField(_("description"), max_length=50000, blank=False, null=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    start_date = ICFApproxDateField()
    end_date = ICFApproxDateField()
    role = models.SmallIntegerField(choices=USER_PARTICIPATION_ROLE_CHOICES, default=PARTICIPANT)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserConferenceWorkshop'

#  Model For Licenses and Certifications obtained by the jobe seeker
class UserLicenseCertification(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=False, blank=False)
    Body = models.CharField(_("body"), max_length=250, null=True, blank=True)
    description = models.TextField(_("description"), max_length=50000, blank=False, null=False)
    start_date = ICFApproxDateField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserLicenseCertifications'

# User Courses Model
class UserCourse(models.Model):
    MINUTES = 1
    HOURS = 2
    DAYS = 3
    DURATION_CHOICES = (
        (MINUTES, _('Minutes')), (HOURS, _('Hours')), (DAYS, _('Days')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=False, blank=False)
    instructor = models.CharField(_("instructor"), max_length=250, null=True, blank=True)
    completed_on = ICFApproxDateField()
    length = models.IntegerField(_("length"),blank=False, null=False)
    duration = models.SmallIntegerField(choices=DURATION_CHOICES, default=MINUTES)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserCourse'

# User FreelanceService Model
class UserFreelanceService(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    name = models.CharField(_("name"), max_length=500, null=False, blank=False)
    # category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True)

    service_description = models.TextField(_("service_description"), blank=True, null=True)
    deliverable_description = models.TextField(_("deliverable_description"), blank=True, null=True)

    price_min = models.IntegerField(_("price_min"),blank=False, null=False)
    price_max = models.IntegerField(_("price_max"),blank=False, null=False)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, blank=True, null=True)
    delivery_min = models.IntegerField(_("delivery_min"),blank=False, null=False)
    delivery_max = models.IntegerField(_("delivery_max"),blank=False, null=False)
    delivery_time = models.ForeignKey(SalaryFrequency, on_delete=models.CASCADE, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username
    class Meta:
        verbose_name_plural = 'UserFreelanceServices'

#  Model For Award And Recognition by the jobe seeker
class UserAwardRecognition(models.Model):
    NOMITATED = 1
    AWARDED = 2
    USER_AWARD_LEVEL_CHOICES = (
        (NOMITATED, _('Nominated')), (AWARDED, _('Awarded')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=False, blank=False)
    year = models.PositiveIntegerField()
    award_institution =  models.CharField(_("award_institution"), max_length=500, null=False, blank=False)
    award_level = models.SmallIntegerField(choices=USER_AWARD_LEVEL_CHOICES, default=NOMITATED)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserAwardRecognitions'

#  Model For Interview Question
class UserInterviewQuestion(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=False, blank=False)

    description = models.TextField(_("description"), blank=True, null=True)
    answer = models.TextField(_("answer"), blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserInterviewQuestions'

#  Model For Professional membership of the jobe seeker
class UserProfessionalMembership(models.Model):
    ASSOCIATE = 1
    MODERATOR = 2
    USER_MEMBERSHIP_LEVEL_CHOICES = (
        (ASSOCIATE, _('Associate Member')), (MODERATOR, _('Moderator')))


    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=False, blank=False)
    Body = models.CharField(_("body"), max_length=250, null=True, blank=True)
    description = models.TextField(_("description"), max_length=50000, blank=False, null=False)
    membership_level = models.SmallIntegerField(choices=USER_MEMBERSHIP_LEVEL_CHOICES, default=ASSOCIATE)

    joined_on = ICFApproxDateField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserProfessionalMemberships'

#  Model For Professional membership of the jobe seeker
class UserVolunteering(models.Model):
    MANAGEMENT = 1
    MODERATOR = 2
    USER_STAFF_LEVEL_CHOICES = (
        (MANAGEMENT, _('Management')), (MODERATOR, _('Moderator')))


    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    name = models.CharField(_("name"), max_length=500, null=False, blank=False)
    description = models.TextField(_("description"), max_length=50000, blank=False, null=False)
    staff_level = models.SmallIntegerField(choices=USER_STAFF_LEVEL_CHOICES, default=MANAGEMENT)
    role = models.CharField(_("role"), max_length=500, null=False, blank=False)

    start_date = ICFApproxDateField()
    end_date = ICFApproxDateField()
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserVolunteerings'

#  Model For jobe seeker Vision & mission
class UserVisionMission(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    vision = models.TextField(_("vision"), max_length=50000, blank=False, null=False)
    mission = models.TextField(_("mission"), max_length=50000, blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserVisionMissions'

#  Model For job seeker RelevantLinks
class UserRelevantLink(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=True, blank=True)
    url = models.CharField(_("url"), max_length=500, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserRelevantLinks'

#  Model For job seeker Influencer
class UserInfluencer(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    name = models.CharField(_("title"), max_length=500, null=False, blank=False)
    url = models.CharField(_("url"), max_length=500, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserInfluencers'

#  Model For job seeker publications
class UserPublication(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    name = models.CharField(_("title"), max_length=500, null=False, blank=False)
    url = models.CharField(_("url"), max_length=500, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPublications'

#  Model For job seeker Prefered JobType
class UserPreferedJobType(models.Model):

    FULLTIME = 1
    CONTRACT = 2
    PARTTIME = 3
    USER_JOB_TYPE_CHOICES = (
        (FULLTIME, _('Full time')), (CONTRACT, _('Contract')), (PARTTIME, _('Part time')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    job_type = models.SmallIntegerField(choices=USER_JOB_TYPE_CHOICES, default=FULLTIME)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedJobTypes'


#  Model For job seeker Prefered Staff Level
class UserPreferedJobStaffLevel(models.Model):

    MANAGEMENT = 1
    JUNIOR = 2
    SENIOR = 4
    EXECUTIVE = 3
    USER_STAFF_LEVEL_CHOICES = (
        (MANAGEMENT, _('Management')), (JUNIOR, _('Junior')), (EXECUTIVE, _('Executive')), (SENIOR, _('Senior')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    staff_level = models.SmallIntegerField(choices=USER_STAFF_LEVEL_CHOICES, default=MANAGEMENT)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedJobStaffLevels'


#  Model For job seeker Prefered Industries
class UserPreferedIndustry(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name="UserPreferedIndustries", null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedIndustries'


#  Model For job seeker Prefered Functional area
class UserPreferedFunctionalArea(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    area = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="UserPreferedFunctionalArea", null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedFunctionalAreas'



#  Model For job seeker Prefered WorkSite Type
class UserPreferedWorkSiteType(models.Model):

    ONSITE = 1
    REMOTE = 2
    HYBRID = 3
    USER_WORKSITE_TYPE_CHOICES = (
        (ONSITE, _('Onsite')), (REMOTE, _('Remote')), (HYBRID, _('Hyrbrid')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    type = models.SmallIntegerField(choices=USER_WORKSITE_TYPE_CHOICES, default=ONSITE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedWorkSiteTypes'


#  Model For job seeker Prefered Country
class UserPreferedCountry(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="UserPreferedCountry", null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedCountry'


#  Model For job seeker Prefered Country
class UserPreferedWage(models.Model):

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    min = models.IntegerField(null=True)
    max = models.IntegerField(null=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="UserPreferedWage")
    period = models.ForeignKey(SalaryFrequency, on_delete=models.CASCADE, related_name="UserPreferedWage")

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username

    class Meta:
        verbose_name_plural = 'UserPreferedWages'



class UserSkill(models.Model):
    BEGINNER = 1
    NOVICE = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    USER_EXPERTISE_LEVEL_CHOICES = (
        (BEGINNER, _('Beginner')), (NOVICE, _('Novice')), (INTERMEDIATE, _('Intermediate')),
        (ADVANCED, _('Advanced')), (EXPERT, _('Expert')))

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    expertise = models.SmallIntegerField(choices=USER_EXPERTISE_LEVEL_CHOICES, default=BEGINNER)

    def __str__(self):
        return "{} : {}".format(self.job_profile, self.skill)

    class Meta:
        unique_together = ('job_profile', 'skill')
        verbose_name_plural = 'UserSkills'


class Relationship(models.Model):
    relation = models.CharField(_('relation'), max_length=50, blank=True)
    description = models.CharField(_('description'), max_length=50, blank=True)

    def __str__(self):
        # return "{} : {}".format(self.relation, self.relation)
        return self.relation

    class Meta:
        verbose_name_plural = 'Relationships'


class UserReference(models.Model):
    PUBLIC = 1
    PRIVATE = 2

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    name = models.CharField(_('name'), max_length=100, blank=True)
    relation = models.ForeignKey(Relationship, on_delete=models.CASCADE)
    # entity = models.CharField(_("entity"), max_length=200)
    # phone = models.CharField(validators=[User.PHONE_REGEX], max_length=25, blank=True) # validators should be a list
    email = models.EmailField(_('email address'), blank=True)
    status = models.SmallIntegerField(default=PUBLIC)

    def __str__(self):
        return "{} : {} : {}".format(self.job_profile.user.username, self.name, self.relation)

    class Meta:
        verbose_name_plural = 'UserReferences'

class UserRecommendation(models.Model):
    PUBLIC = 1
    PRIVATE = 2

    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    recommender = models.CharField(_("recommender"), max_length=200)
    recommender_email = models.CharField(_("email"), max_length=100)
    relation = models.ForeignKey(Relationship, on_delete=models.CASCADE)
    desc = models.CharField(max_length=80)
    status = models.SmallIntegerField(default=PUBLIC)


    def __str__(self):
        return "{} : {} : {}".format(self.job_profile.user.username, self.name, self.relation)

    class Meta:
        verbose_name_plural = 'UserRecommendation'


# def validate_file_extension(value):
#     ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
#     valid_extensions = ['.pdf', '.doc', '.docx', '.xlsx', '.xls']
#     if not ext.lower() in valid_extensions:
#         raise ValidationError(u' Unsupported file extension.')


# class UserRelevantLink(models.Model):
#     job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
#     relevant_link = models.URLField(blank=False, null=False)

#     def __str__(self):
#         # return "{} : {}".format(self.relation, self.relation)
#         return self.job_profile.user.username

#     class Meta:
#         verbose_name_plural = 'UserRelevantLinks'

#  New mode for extra curricular activities
class UserExtraCurricularActivities(models.Model):
    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    activitiy = models.CharField(_("activities"), max_length=500, null=False, blank=False)

    def __str__(self):
        return self.activitiy

    class Meta:
        verbose_name_plural = 'UserExtraCurricularActivities'


class UserHobbie(models.Model):
    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    hobbie = models.CharField(_("hobbie"), max_length=500, null=False, blank=False)

    def __str__(self):
        # return "{} : {}".format(self.relation, self.relation)
        return self.hobbie

    class Meta:
        verbose_name_plural = 'UserHobbies'


class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    work_experience = models.ForeignKey(UserWorkExperience, on_delete=models.CASCADE)
    description = models.CharField(_("description"), max_length=2000, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # return "{} : {}".format(self.relation, self.relation)
        return self.user.username

    class Meta:
        verbose_name_plural = 'Tasks'


class JobProfileFileUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resume_src = models.FileField(upload_to=upload_job_profile_file_location,
                                  validators=[validate_file_extension],max_length=200)

    def __str__(self):
        return self.resume_src.url


class JobMarkedForDelete(models.Model):
    NEW = 1
    DELETED = 2
    REJECTED = 3

    Approval_Status_STATUS_CHOICES = (
        (NEW, _('New')), (DELETED, _('Deleted')), (REJECTED, _('Rejected')))

    job = models.ForeignKey(Job, on_delete=models.CASCADE,related_name='marked_delete')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    approval_status = models.SmallIntegerField(choices=Approval_Status_STATUS_CHOICES, default=NEW)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{} : {}".format(self.user.username, self.job.slug)

#
# The below method is a signal receiver for pre_save called just before the Job model is saved
#


# @receiver(pre_save, sender=Job)
# def job_pre_save_receiver(sender, instance, *args, **kwargs):
#     logger.info("Pre save receiver to create slug called")
#     create_slug(instance)

# @receiver(pre_save, sender=Job)
# def job_pre_save_receiver(sender, instance, *args, **kwargs):
#
#     logger.info("Set item type before saving the job")
#
#     instance_type = ContentType.objects.get_for_model(instance)
#
#     item_type = Type.objects.get_or_create(app_name=instance_type.app_label)
#
#     instance.item_type = item_type


class DraftJob(models.Model):

    entity = models.ForeignKey(Entity,on_delete=models.CASCADE)
    contents = models.TextField(max_length=2000)

    def __str__(self):
        return self.entity


class JobDraft(ItemDraft):
    MAX_JOB_EXPERIENCE_YEARS = 40
    MONTHS = 12
    EXPERIENCE_YEARS_CHOICES = [(year, year) for year in range(0, MAX_JOB_EXPERIENCE_YEARS + 1)]  # 0 - 40 years
    MONTHS_CHOICES = [(month, month) for month in range(MONTHS + 1)]  # 0 - 12 months
    MIN_OPEN_POSITIONS = 1

    occupation = models.ForeignKey(Occupation, on_delete=models.CASCADE, blank=True, null=True)

    experience_years = models.SmallIntegerField(choices=EXPERIENCE_YEARS_CHOICES, blank=True, null=True)
    experience_months = models.SmallIntegerField(choices=MONTHS_CHOICES, blank=True, null=True)

    salary_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, blank=True, null=True)
    salary_frequency = models.ForeignKey(SalaryFrequency, on_delete=models.CASCADE, blank=True, null=True)
    salary = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    salary_is_public = models.BooleanField(default=False)

    education_level = models.ForeignKey(EducationLevel, on_delete=models.CASCADE, blank=True, null=True)

    open_positions = models.SmallIntegerField(default=MIN_OPEN_POSITIONS, blank=True, null=True)
    job_type = models.ForeignKey(JobType,on_delete=models.CASCADE, blank=True, null=True)
    external_website_visibility = models.BooleanField(default=False)
    external_website_url = models.URLField(blank=True, null=True)
    recruiter_email_visibility = models.BooleanField(default=False)
    recruiter_email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Jobs'
        ordering = ['-created', ]

    def get_entity_logo(self):
        try:
            return Logo.objects.get(entity=self.entity).image.url
        except ObjectDoesNotExist:
            return ""


class JobSkillOptional(models.Model):
    job = models.ForeignKey(JobDraft, on_delete=models.CASCADE, null=True,blank=True, related_name="job_optional_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, null=True,blank=True,related_name="job_optional_skills")

    def __str__(self):
        return "{0}:{1}".format(self.job,self.skill)

    class Meta:
        verbose_name_plural = 'JobSkillsOptional'


class UnregisteredUserFileUpload(models.Model):
    mobile = models.CharField(validators=[User.PHONE_REGEX], max_length=25, blank=True) # validators should be a list
    resume_src = models.FileField(upload_to=upload_job_profile_file_location, validators=[validate_file_extension], max_length=200)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.resume_src.url


class UserProject(models.Model):
    job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=500, null=False, blank=False)
    summary = models.TextField(_("summary"), max_length=50000, blank=False, null=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    start_date = ICFApproxDateField()
    end_date = ICFApproxDateField()
    reference = GenericRelation(Reference, related_query_name="project", null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_profile.user.username


# class UserResume(models.Model):
#     job_profile = models.ForeignKey(UserJobProfile, on_delete=models.CASCADE)
#     title = models.CharField(_("title"), max_length=500, null=True, blank=True)
#     thumbnail = models.ImageField(upload_to=upload_dynamic_resume_thumbnail_media_location, null=True, blank=True)
#     resume = models.FileField(upload_to=upload_dynamic_resume_media_location,
#                               validators=[validate_file_extension], max_length=200, null=True, blank=True)
#     biography = models.CharField(_("biography"), max_length=250, null=True, blank=True)
#     is_active = models.BooleanField(default=False)
#     slug = models.SlugField(blank=True, unique=True)
#     created = models.DateTimeField(auto_now_add=True, auto_now=False)
#     updated = models.DateTimeField(auto_now_add=False, auto_now=True)
#
#     def __str__(self):
#         return self.job_profile.user.username

#
# class UserResumeComponentType(models.Model):
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     name = models.CharField(max_length=50, blank=True, null=True)
#     description = models.CharField(_("Description of resume component type of item"), max_length=100)
#     slug = models.SlugField(blank=True)
#
#     def __str__(self):
#         return "{}".format(self.name)


class UserResumeComponent(models.Model):
    user_resume = models.ForeignKey(UserResume, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)
    sort_order = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.user_resume.job_profile.user.username


class CandidateSearchForJobMasterChoice:
    SKILL = 'skill'
    WORK_EXPERIENCE = 'work_experience'
    EDUCATION = 'education'
    LOCATION = 'location'

    CANDIDATE_SEARCH_FOR_JOB_MASTER_CHOICES = (
        (SKILL, _('skill')), (WORK_EXPERIENCE, _('work_experience')), (EDUCATION, _('education')), (LOCATION, _('location')))

    @classmethod
    def get_unit_choices(cls):
        return dict(cls.CANDIDATE_SEARCH_FOR_JOB_MASTER_CHOICES)


class CandidateSearchForJobMaster(models.Model):
    search_criteria = models.CharField(max_length=500, choices=CandidateSearchForJobMasterChoice.
                                        CANDIDATE_SEARCH_FOR_JOB_MASTER_CHOICES,
                                        default=CandidateSearchForJobMasterChoice.SKILL, unique=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.search_criteria


class CandidateSearch(models.Model):
    name = models.CharField(_("name"), max_length=200, blank=False, null=False)
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE)
    entity_slug = models.CharField(max_length=500,  null=False, blank=False)
    location = models.CharField(max_length=500, null=True, blank=True)
    work_experience = models.PositiveIntegerField(null=True, blank=True)
    education_level = models.CharField(max_length=500, null=True, blank=True)
    key_skill = models.CharField(max_length=500, null=True, blank=True)
    computer_skill = models.CharField(max_length=500, null=True, blank=True)
    language_skill = models.CharField(max_length=500, null=True, blank=True)
    job_title = models.CharField(max_length=500, null=True, blank=True)
    slug = models.SlugField(blank=True, max_length=200)
    functional_area = models.CharField(max_length=500, null=True, blank=True)
    industries = models.CharField(max_length=500, null=True, blank=True)
    job_level = models.CharField(max_length=500, null=True, blank=True)
    worksite_type = models.CharField(max_length=500, null=True, blank=True)
    salary = models.CharField(max_length=500, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.name





