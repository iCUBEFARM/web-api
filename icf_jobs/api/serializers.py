import json
import threading
from datetime import datetime, timezone

import pytz
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import transaction

from icf import settings
from icf_auth.api.serializers import UserEmailMobileSerializer, UserProfileRetrieveSerializer, \
    UserProfileRetrieveUpdateSerializer, UserProfileRetrieveSerializerForList, UserFirstAndLastNameSerializer
from icf_auth.models import User, UserProfile
from icf_jobs.JobHelper import get_user_work_experience_in_seconds
from icf_jobs.util import JobNotification, send_recommender_email
from icf_messages.models import ICFMessage
from icf_orders.app_settings import CREATE_JOB, SPONSORED_JOB
from icf_orders.models import CreditAction, Subscription
from icf_entity.models import Logo, Entity
from icf_orders.api.mixins import ICFCreditManager
from icf_generic.Exceptions import ICFException
from icf_generic.api.serializers import AddressSerializer, AddressRetrieveSerializer, AddressOptionalSerializer, \
    CitySerializer, CurrencySerializer
from icf_item.api.serializers import ItemCreateUpdateSerializer, ItemListSerializer, EntitySerializer, \
    ItemCreateUpdateDraftSerializer, ItemDraftListSerializer
from icf_generic.models import Address, Currency, Sponsored, AddressOptional, City, Type
from icf_item.models import Item, ItemUserView, FavoriteItem
from icf_jobs.models import Job, Occupation, EducationLevel, JobSkill, Skill, SalaryFrequency, JobType, UserAwardRecognition, UserConferenceWorkshop, UserCourse, UserExtraCurricularActivities, UserFreelanceService, UserInfluencer, UserInterviewQuestion, UserLicenseCertification, UserPreferedCountry, UserPreferedFunctionalArea, UserPreferedIndustry, UserPreferedJobStaffLevel, UserPreferedJobType, UserPreferedWage, UserPreferedWorkSiteType, UserProfessionalMembership, UserPublication, UserReference, \
    Relationship, UserRelevantLink, UserSkill, UserVisionMission, UserVolunteering, UserWorkExperience, UserEducation, JobProfileFileUpload, UserJobProfile, JobUserApplied, \
    DraftJob, JobDraft, JobSkillOptional, UnregisteredUserFileUpload, UserRelevantLink, UserHobbie, UserProject, \
    Reference, Task, UserResume, UserResumeComponent, CandidateSearch
from modeltranslation.admin import TranslationBaseModelAdmin
from modeltranslation.management.commands import update_translation_fields
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.utils import model_meta
from rest_framework import serializers
from rest_framework import status
from django.utils.translation import ugettext_lazy as _

import logging

from icf_messages.manager import ICFNotificationManager

logger = logging.getLogger(__name__)


class JobSkillSerializer(PrimaryKeyRelatedField,ModelSerializer):
    skill_type = serializers.SerializerMethodField()
    class Meta:
        model = JobSkill
        fields = ['job', 'skill']

    def get_skill_type(self, object):
        return object.skill.skill_type


class JobRetrieveSkillSerializer(ModelSerializer):
    skill_type = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = JobSkill
        fields = ['skill', 'skill_type', 'name']

    def get_skill_type(self, object):
        return object.skill.skill_type

    def get_name(self, object):
        return object.skill.name


class JobRetrieveOptionalSkillSerializer(ModelSerializer):
    skill_type = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = JobSkillOptional
        fields = ['skill','skill_type', 'name']

    def get_skill_type(self,object):
        return object.skill.skill_type

    def get_name(self, object):
        return object.skill.name


class SponsoredSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(default=None)
    end_date = serializers.DateTimeField(default=None)

    class Meta:
        model = Sponsored
        fields = ['start_date', 'end_date']


class JobCreateSerializer(ItemCreateUpdateSerializer):
    job_skills = JobRetrieveSkillSerializer(many=True)
    item_type = serializers.SerializerMethodField()
    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = Job
        exclude = ['owner', ]
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(JobCreateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    @transaction.atomic
    def create(self, validated_data):
        print('----------', validated_data)
        job_skills_data = validated_data.pop("job_skills")

        location_data = validated_data.pop("location")
        location = Address.objects.create(**location_data)

        entity = validated_data.get("entity")

        sponsored_start_dt = validated_data.pop('sponsored_start_dt')
        sponsored_end_dt = validated_data.pop('sponsored_end_dt')
        is_sponsored = validated_data.pop('is_sponsored')

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create job")
            raise ICFException(_("You do not have the permissions to create jobs for {}".format(entity)), status_code=status.HTTP_400_BAD_REQUEST)

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('expiry')

        is_allowed_interval = ICFCreditManager.is_allowed_interval(start_date, end_date)
        if not is_allowed_interval:
            logger.exception("Invalid duration for posting the job. "
                             "The job's start date should be between {X} and {Y}.\n"
                             .format(X=str(datetime.now(pytz.utc).date()), Y=str(end_date)))
            raise ICFException(_("The job's start date should be between {X} and {Y}."
                                 .format(X=str(datetime.now(pytz.utc).date()), Y=str(end_date))))
        # title = validated_data.pop('title')
        # description = validated_data.pop('description')

        title = validated_data.pop('title')
        title_en = validated_data.pop('title_en')
        title_fr = validated_data.pop('title_fr')
        title_es = validated_data.pop('title_es')

        description = validated_data.pop('description')
        description_en = validated_data.pop('description_en')
        description_fr = validated_data.pop('description_fr')
        description_es = validated_data.pop('description_es')

        job = Job.objects.create(owner=user, location=location,
                                 title=title, title_en=title, title_fr=title, title_es=title,
                                 description=description, description_en=description, description_es=description,
                                 description_fr=description, **validated_data)

        job_model = ContentType.objects.get_for_model(job)

        for skills in job_skills_data:
            skill = skills.pop('skill')
            JobSkill.objects.update_or_create(skill=skill, job=job)

        if job.status == Item.ITEM_ACTIVE:
            ICFCreditManager.manage_entity_subscription(entity=entity, action=CREATE_JOB, item_start_date=start_date,
                                                        item_end_date=end_date, user=user, app=job_model)

            # result_dict = ICFCreditManager.check_entity_subscription(entity=entity, action=CREATE_JOB, job_start_date=start_date, job_end_date=end_date,
            #                                                     user=user, app=job_model)
            # if result_dict['subscription_without_overflow']:
            #     subscribed_entity.action_count = subscribed_entity.action_count + 1
            #     subscribed_entity.save(update_fields=['status'])
            # if result:
            #     pass

            # else:
            #     intervals = ICFCreditManager.get_num_of_intervals(start_date, end_date, CREATE_JOB)
            #     ICFCreditManager.charge_for_action(user=user, entity=entity, app=job_model, action=CREATE_JOB,
            #                                        intervals=intervals)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid values for sponsored start date and sponsored end date.\n")
                    raise ICFException(_("Please provide job's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # A job can be sponsored anywhere during the period when the job is active.
                if sponsored_start_dt >= job.start_date and sponsored_end_dt <= job.expiry:
                    intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt, SPONSORED_JOB)
                    Sponsored.objects.create(content_object=job, start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                    ICFCreditManager.charge_for_action(user=user, entity=entity, app=job_model, action=SPONSORED_JOB,
                                                       intervals=intervals)
                    job.is_sponsored = True
                    job.sponsored_start_dt = sponsored_start_dt
                    job.sponsored_end_dt = sponsored_end_dt
                else:
                    logger.exception("A job can be sponsored from {X} till {Y}. "
                                     "Choose valid sponsored start date and end date.\n".
                                     format(X=str(job.start_date), Y=str(job.expiry)))
                    raise ICFException(_("A job can be sponsored from {X} till {Y}. "
                                         "Choose valid sponsored start date and end date.".
                                         format(X=str(job.start_date), Y=str(job.expiry))),
                                           status_code=status.HTTP_400_BAD_REQUEST)

            #
            # Add teh sponsored information to tbe job object to be serialized.
            # The sponsored information is added to the job object even though the information
            # is not part of the Job model.
            #

        logger.info("Job created {}".format(job))

        return job

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None


class JobRetrieveUpdateSerializer(ItemCreateUpdateSerializer):
    # job_skills = JobSkillSerializer(many=True, queryset=Skill.objects.all())
    job_skills = JobRetrieveSkillSerializer(many=True)
    item_type = serializers.SerializerMethodField()
    is_fav_item = serializers.SerializerMethodField()
    is_applied_by_user = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    entity = serializers.StringRelatedField()

    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = Job
        exclude = ['owner', ]
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(JobRetrieveUpdateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    @transaction.atomic
    def update(self, instance, validated_data):

        job_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create job")
            raise ICFException("Unknown user, cannot create job", status_code=status.HTTP_400_BAD_REQUEST)

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            location, address_created = Address.objects.update_or_create(userprofile=instance, **location_data)
            instance.location = location

        job_skills_data = validated_data.pop("job_skills")

        # to avoid redudency of skill
        JobSkill.objects.filter(job=instance.job).delete()

        for skills in job_skills_data:
             skill = skills.pop('skill')
             job_skill = JobSkill.objects.update_or_create(skill=skill, job=instance.job)

        prev_job_status = instance.status
        prev_start_date = instance.start_date
        prev_end_date = instance.expiry

        current_status = validated_data.get('status')
        curr_start_date = validated_data.get('start_date')
        curr_end_date = validated_data.get('expiry')

        is_sponsored = validated_data.get('is_sponsored')
        sponsored_start_dt = validated_data.get('sponsored_start_dt')
        sponsored_end_dt = validated_data.get('sponsored_end_dt')

        ########################################
        # Getting published for the first time
        ########################################
        if prev_job_status != current_status and current_status == Item.ITEM_ACTIVE:
            logger.info("Publishing the job first time : {}.\n".format(instance.slug))
            is_allowed_interval = ICFCreditManager.is_allowed_interval(curr_start_date, curr_end_date)
            if not is_allowed_interval:
                logger.exception("Invalid duration for posting the job. "
                                 "The job's start date should be between {X} and {Y}.\n"
                                 .format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date)))
                raise ICFException(_("The job's start date should be between {X} and {Y}."
                                     .format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date))))
            # intervals = ICFCreditManager.get_num_of_intervals(curr_start_date, curr_end_date, 'create_job')
            # ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model, action='create_job',
            #                                    intervals=intervals)

            ICFCreditManager.manage_entity_subscription(entity=instance.entity, action=CREATE_JOB, item_start_date=curr_start_date,
                                                        item_end_date=curr_end_date,
                                                        user=user, app=job_model)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid values for sponsored start date and sponsored end date.\n")
                    raise ICFException(_("Please provide job's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # A job can be sponsored anywhere during the period when the job is active.
                if sponsored_start_dt >= curr_start_date and sponsored_end_dt <= curr_end_date:
                    intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt, 'sponsored_job')
                    Sponsored.objects.create(content_object=instance,
                                             start_date=sponsored_start_dt,end_date =sponsored_end_dt)
                    ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model, action='sponsored_job',
                                                       intervals=intervals)
                    instance.is_sponsored = True
                    instance.sponsored_start_dt = sponsored_start_dt
                    instance.sponsored_end_dt = sponsored_end_dt
                else:
                    logger.exception("Duration for sponsoring job not within the job posting duration.\n")
                    raise ICFException(_("The start date of your sponsored job campaign cannot be before {X} "
                                         "and the end date cannot be after {Y}.".format(X=str(curr_start_date.date()), Y=str(curr_end_date.date()))),
                                          status_code=status.HTTP_400_BAD_REQUEST)

        ######################################
        # Updating an already published job
        ######################################
        if prev_job_status == current_status and current_status == Item.ITEM_ACTIVE:
            logger.info("Updating a published job : {}.\n".format(instance.slug))

            if prev_start_date != curr_start_date:
                if prev_start_date.date() < datetime.now(pytz.utc).date():
                    logger.exception("Cannot change start date for an active and published job.\n")
                    raise ICFException(_("You cannot change the start date for an active and published job."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                elif curr_start_date.date() < datetime.now(pytz.utc).date():
                    logger.exception("The start date cannot be before {X}.\n".format(X=str(datetime.now(pytz.utc).date())))
                    raise ICFException(_("The start date cannot be before {X}.".format(X=str(datetime.now(pytz.utc).date()))),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            if curr_end_date.date() < datetime.now(pytz.utc).date():
                logger.exception("The end date cannot be before {X}.\n".format(X=str(datetime.now(pytz.utc).date())))
                raise ICFException(_("The end date cannot be before {X}.".format(X=str(datetime.now(pytz.utc).date()))),
                                   status_code=status.HTTP_400_BAD_REQUEST)

            # Charge for the difference in duration.
            intervals = ICFCreditManager.change_to_interval(prev_start_date, prev_end_date, curr_start_date,
                                                            curr_end_date, action=CREATE_JOB)
            if intervals:
                # ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model,
                #                                    action=CREATE_JOB, intervals=intervals)

                ICFCreditManager.manage_entity_subscription(entity=instance.entity, action=CREATE_JOB,
                                                            item_start_date=curr_start_date,
                                                            item_end_date=curr_end_date,
                                                            user=user, app=job_model)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid values for sponsored start date and sponsored end date.\n")
                    raise ICFException(_("Please provide job's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # Check if the job was already sponsored before
                try:

                    # The job was already sponsored. Charge for the difference if any in the duration.
                    sponsored = Sponsored.objects.get(object_id=instance.id,status=Sponsored.SPONSORED_ACTIVE)

                    prev_sponsored_start_date = sponsored.start_date
                    prev_sponsored_end_date = sponsored.end_date

                    if prev_sponsored_start_date != sponsored_start_dt:
                        if prev_sponsored_start_date < datetime.now(pytz.utc):
                            logger.exception("Cannot change start date of an already sponsored job.\n")
                            raise ICFException(
                                _("You cannot change the start date of an ongoing sponsored job campaign."),
                                status_code=status.HTTP_400_BAD_REQUEST)
                        elif sponsored_start_dt < datetime.now(pytz.utc) or \
                                sponsored_start_dt > curr_end_date:
                            logger.exception("Invalid start date for sponsoring the job. The Sponsored job start date "
                                             "should be between {X} and {Y}.\n".
                                             format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                            raise ICFException(_("The Sponsored job start date should be between "
                                                 "{X} and {Y}.".format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date()))),
                                                 status_code=status.HTTP_400_BAD_REQUEST)

                    if sponsored_end_dt < datetime.now(pytz.utc) or \
                            sponsored_end_dt > curr_end_date:
                        logger.exception("Invalid end date for sponsoring the job. The Sponsored job end date "
                                         "should be between {X} and {Y}.\n".
                                         format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                        raise ICFException(_("The Sponsored job end date should be between "
                                             "{X} and {Y}.".format(X=str(datetime.now(pytz.utc).date()),
                                                                   Y=str(curr_end_date.date()))),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                    sponsored.start_date = sponsored_start_dt
                    sponsored.end_date = sponsored_end_dt
                    sponsored.status = Sponsored.SPONSORED_ACTIVE
                    sponsored.save(update_fields=['start_date', 'end_date', 'status'])
                    # Charge for the difference in duration.
                    intervals = ICFCreditManager.change_to_interval(prev_sponsored_start_date,
                                                                    prev_sponsored_end_date, sponsored_start_dt,
                                                                    sponsored_end_dt, action=SPONSORED_JOB)
                    if intervals:
                        ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model,
                                                           action=SPONSORED_JOB, intervals=intervals)

                except Sponsored.DoesNotExist:
                    # to check whether job is already sponsored and inactive
                    try:
                        pre_sponsored = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_INACTIVE)
                        # delete to avoid redundant row in table
                        pre_sponsored.delete()
                    except ObjectDoesNotExist:
                        pass

                    # Job sponsored first time during this update, did not exist earlier

                    if sponsored_start_dt >= curr_start_date and sponsored_end_dt <= curr_end_date:
                        intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
                                                                          'sponsored_job')
                        Sponsored.objects.create(content_object=instance,
                                                 start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                        ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model,
                                                           action='sponsored_job',
                                                           intervals=intervals)
                        instance.is_sponsored = True
                        instance.sponsored_start_dt = sponsored_start_dt
                        instance.sponsored_end_dt = sponsored_end_dt
                    else:
                        logger.exception("Duration for sponsoring job not within the job posting duration.\n")
                        raise ICFException(_("The start date of your sponsored job campaign cannot "
                                             "be before {X} and the end date cannot be after {Y}."
                                             .format(X=str(curr_start_date.date()), Y=str(curr_end_date.date()))),
                                           status_code=status.HTTP_400_BAD_REQUEST)

            else:
                # Check if an earlier sponsored job has been removed
                try:
                    sponsored = Sponsored.objects.get(object_id=instance.id)
                    sponsored.status = Sponsored.SPONSORED_INACTIVE
                    sponsored.save(update_fields=["status"])
                except Sponsored.DoesNotExist:
                    pass

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    def get_is_fav_item(self,obj):
        request = self.context.get("request")

        try:
            fav = FavoriteItem.objects.get(user=request.user,item=obj)
            if fav is not None:
                return True
            else:
                return False
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return False

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    def get_is_applied_by_user(self, obj):
        request = self.context.get("request")
        try:
            job_user_applied = JobUserApplied.objects.get(user=request.user, job=obj)
            if job_user_applied:
                return True
            else:
                return False
        except JobUserApplied.DoesNotExist as e:
            logger.debug(e)
            return False

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None


class JobDraftRetrieveUpdateSerializer(ItemCreateUpdateDraftSerializer):
    job_optional_skills = JobRetrieveOptionalSkillSerializer(many=True)
    item_type = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    entity = serializers.StringRelatedField()

    class Meta:
        model = JobDraft
        exclude = ['owner', ]

    def update(self, instance, validated_data):

        job_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create draft job")
            raise ICFException("Unknown user, cannot create draft job", status_code=status.HTTP_400_BAD_REQUEST)

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            location, address_created = AddressOptional.objects.update_or_create(userprofile=instance, **location_data)
            instance.location = location

        job_skills_data = validated_data.pop("job_optional_skills")

        # to avoid redudency of skill
        JobSkillOptional.objects.filter(job=instance).delete()

        for skills in job_skills_data:
             skill = skills.pop('skill')
             job_skill = JobSkillOptional.objects.update_or_create(skill=skill, job=instance)

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None


class JobRetrieveSerializer(ModelSerializer):
    location = AddressRetrieveSerializer()
    job_skills = JobRetrieveSkillSerializer(many=True)
    item_type = serializers.SerializerMethodField()
    is_fav_item = serializers.SerializerMethodField()
    is_applied_by_user = serializers.SerializerMethodField()
    entity = EntitySerializer()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry = serializers.DateTimeField(format='%B %d, %Y')
    salary_currency = serializers.StringRelatedField()
    salary_frequency = serializers.StringRelatedField()
    education_level = serializers.StringRelatedField()
    category = serializers.StringRelatedField()
    occupation = serializers.StringRelatedField()
    job_type = serializers.StringRelatedField()

    class Meta:
        model = Job
        exclude = ['owner', ]

    def get_title(self, obj):
        request = self.context.get("request")
        if request.LANGUAGE_CODE == 'en':
            if obj.title_en:
                return obj.title_en
            elif obj.title_fr:
                return obj.title_fr
            else:
                return obj.title_es
        elif request.LANGUAGE_CODE == 'fr':
            if obj.title_fr:
                return obj.title_fr
            elif obj.title_es:
                return obj.title_es
            else:
                return obj.title_en
        elif request.LANGUAGE_CODE == 'es':
            if obj.title_es:
                return obj.title_es
            elif obj.title_fr:
                return obj.title_fr
            else:
                return obj.title_en
        else:
            return obj.title

    def get_description(self, obj):
        request = self.context.get("request")
        if request.LANGUAGE_CODE == 'en':
            if obj.description_en:
                return obj.description_en
            elif obj.description_fr:
                return obj.description_fr
            else:
                return obj.description_es
        elif request.LANGUAGE_CODE == 'fr':
            if obj.description_fr:
                return obj.description_fr
            elif obj.description_es:
                return obj.description_es
            else:
                return obj.description_es
        elif request.LANGUAGE_CODE == 'es':
            if obj.description_es:
                return obj.description_es
            elif obj.description_fr:
                return obj.description_fr
            else:
                return obj.description_en
        else:
            return obj.description

    def get_is_fav_item(self, obj):
        request = self.context.get("request")

        #number of user viewed
        if not request.user.is_anonymous:
            ItemUserView.objects.update_or_create(user=request.user, item=obj)

        try:
            if not request.user.is_anonymous:
                fav = FavoriteItem.objects.get(user=request.user,item=obj)
                if fav is not None:
                    return True
            else:
                return False
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return False

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None

    def get_is_applied_by_user(self,obj):
        request = self.context.get("request")
        try:
            if not request.user.is_anonymous:
                job_user_applied = JobUserApplied.objects.get(user=request.user, job=obj)
                if job_user_applied:
                    return True
            else:
                return False
        except JobUserApplied.DoesNotExist as e:
            logger.debug(e)
            return False


class JobDraftRetrieveSerializer(ModelSerializer):
    location = AddressOptionalSerializer()
    job_optional_skills = JobRetrieveOptionalSkillSerializer(many=True)
    item_type = serializers.SerializerMethodField()

    entity = EntitySerializer()
    salary_currency = serializers.StringRelatedField()
    salary_frequency = serializers.StringRelatedField()
    education_level = serializers.StringRelatedField()
    category = serializers.StringRelatedField()
    occupation = serializers.StringRelatedField()
    job_type = serializers.StringRelatedField()

    class Meta:
        model = JobDraft
        exclude = ['owner', ]

    def get_title(self, obj):
        request = self.context.get("request")
        if request.LANGUAGE_CODE == 'en':
            if obj.title_en:
                return obj.title_en
            elif obj.title_fr:
                return obj.title_fr
            else:
                return obj.title_es
        elif request.LANGUAGE_CODE == 'fr':
            if obj.title_fr:
                return obj.title_fr
            elif obj.title_es:
                return obj.title_es
            else:
                return obj.title_en
        elif request.LANGUAGE_CODE == 'es':
            if obj.title_es:
                return obj.title_es
            elif obj.title_fr:
                return obj.title_fr
            else:
                return obj.title_en
        else:
            return obj.title

    def get_description(self, obj):
        request = self.context.get("request")
        if request.LANGUAGE_CODE == 'en':
            if obj.description_en:
                return obj.description_en
            elif obj.description_fr:
                return obj.description_fr
            else:
                return obj.description_es
        elif request.LANGUAGE_CODE == 'fr':
            if obj.description_fr:
                return obj.description_fr
            elif obj.description_es:
                return obj.description_es
            else:
                return obj.description_es
        elif request.LANGUAGE_CODE == 'es':
            if obj.description_es:
                return obj.description_es
            elif obj.description_fr:
                return obj.description_fr
            else:
                return obj.description_en
        else:
            return obj.description

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None


class JobListSerializer(ItemListSerializer):
    salary_currency = serializers.StringRelatedField()

    class Meta(ItemListSerializer.Meta):
        model = Job
        fields = ItemListSerializer.Meta.fields + ('experience_years', 'experience_months',
                                                   'entity', 'salary_currency')


class JobDraftListSerializer(ItemDraftListSerializer):
    salary_currency = serializers.StringRelatedField()

    class Meta(ItemDraftListSerializer.Meta):
        model = JobDraft
        fields = ItemDraftListSerializer.Meta.fields + ('experience_years', 'experience_months',
                                                        'entity', 'salary_currency')


class EntityJobListSerializer(ItemListSerializer):
    salary_currency = serializers.StringRelatedField()
    is_sponsored_job = serializers.SerializerMethodField()
    no_of_views = serializers.SerializerMethodField()
    no_of_applied_user = serializers.SerializerMethodField()

    class Meta(ItemListSerializer.Meta):
        model = Job
        fields = ItemListSerializer.Meta.fields + ('experience_years', 'experience_months',
                                                   'entity', 'salary_currency', 'is_sponsored_job',
                                                   'no_of_views', 'no_of_applied_user')

    def get_is_sponsored_job(self, obj):
        try:
            content_type = ContentType.objects.get(model='job')
            sponsored_job = Sponsored.objects.filter(object_id=obj.id, content_type=content_type.id,
                                                     status=Sponsored.SPONSORED_ACTIVE).last()

            if sponsored_job:
                if sponsored_job.start_date <= datetime.now(pytz.utc) < sponsored_job.end_date:
                    return True
                else:
                    return False
            else:
                return False
        except Sponsored.DoesNotExist as e:
            logger.debug(e)
            return False

    def get_no_of_views(self, obj):
        # number of user viewed
        view_count = ItemUserView.objects.filter(item=obj)
        return view_count.count()

    def get_no_of_applied_user(self, obj):
        return JobUserApplied.objects.filter(job=obj).count()


class EducationLevelSerializer(ModelSerializer):

    class Meta:
        model = EducationLevel
        fields = ["level", "id"]


class OccupationSerializer(ModelSerializer):

    class Meta:
        model = Occupation
        fields = ["id", "name", ]


class SalaryFrequencySerializer(ModelSerializer):

    class Meta:
        model = SalaryFrequency
        fields = ["id", "frequency"]


class JobTypeSerializer(ModelSerializer):

    class Meta:
        model = JobType
        fields = ["id", "job_type"]


class SkillSerializer(ModelSerializer):

    class Meta:
        model = Skill
        fields = ["id", "name", "skill_type"]


# class SkillTypeSerializer(ModelSerializer):
#
#     class Meta:
#         model = SkillType
#         fields = ["id", "skill_type"]


class UserEducationSerializer(ModelSerializer):
    education_level_name = serializers.SerializerMethodField(read_only=True)
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserEducation
        fields = [
                    "id",
                    "education_level",
                    "education_level_name",
                    "school",
                    "from_year",
                    "to_year",
                    "certification",
                    "city",
                    "city_name",
                 ]

    def get_education_level_name(self, obj):
        try:
            serializer = EducationLevelSerializer(EducationLevel.objects.filter(id=obj.education_level_id).first())
            return serializer.data['level']
        except Exception as e:
            logger.exception('Could not get education level name, reason: {reason}.\n'.format(reason=str(e)))
            return None

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def validate(self, data):
        """
        Check that the from_year is before the to_year.
        """
        if data['from_year'] > data['to_year']:
            raise serializers.ValidationError("to year must be after from year")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'User Education'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserEducation.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise
#  Seroalier for conference and workshops the job seeker attended.
class UserConferenceWorkshopSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserConferenceWorkshop
        fields = [
                    "id",
                    "name",
                    "organizer",
                    "description",
                    "role",
                    "start_date",
                    "end_date",
                    "city",
                    "city_name",
                 ]

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def validate(self, data):
        """
        Check that the from_year is before the to_year.
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("end date must be after start_date")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'User Conference and Workshops'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserConferenceWorkshop.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for For Licenses and Certifications obtained by the jobe seeker
class UserLicenseCertificationSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserLicenseCertification
        fields = [
                    "id",
                    "title",
                    "Body",
                    "description",
                    "start_date",
                 ]

    def validate(self, data):
        """
        Check that the from_year is before the to_year.
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("end date must be after start_date")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'User Education'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserLicenseCertification.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for For courses completed obtained by the jobe seeker
class UserCourseSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = UserCourse
        fields = [
                    "id",
                    "title",
                    "instructor",
                    "completed_on",
                    "length",
                    "duration",
                 ]

    # def validate(self, data):
    #     """
    #     Check that the from_year is before the to_year.
    #     """
    #     if data['start_date'] > data['end_date']:
    #         raise serializers.ValidationError("end date must be after start_date")
    #     return data

    def create(self, validated_data):
        """
        Create and return a new 'User Course'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserCourse.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for For Freelance services of the jobe seeker
class UserFreelanceServiceSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    currency_name = serializers.SerializerMethodField(read_only=True)
    delivery_time_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserFreelanceService
        fields = [
                    "id",
                    "name",
                    "service_description",
                    "deliverable_description",
                    "price_min",
                    "price_max",
                    "currency",
                    "currency_name",
                    "delivery_time",
                    "delivery_time_name",
                    "delivery_min",
                    "delivery_max"
                 ]

    def get_currency_name(self, obj):
        if obj.city:
            serializer = CurrencySerializer(Currency.objects.filter(id=obj.city_id).first())
            return serializer.data['currency']
        else:
            return None

    def get_currency_name(self, obj):
        if obj.city:
            serializer = SalaryFrequencySerializer(SalaryFrequency.objects.filter(id=obj.city_id).first())
            return serializer.data['delivery_time_name']
        else:
            return None

    def create(self, validated_data):
        """
        Create and return a new 'User Freelance Service'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserFreelanceService.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for Award and Recognition of the jobe seeker
class UserAwardRecognitionSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserAwardRecognition
        fields = [
                    "id",
                    "title",
                    "year",
                    "award_institution",
                    "award_level"
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Award & Recognition'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserAwardRecognition.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for Award and Recognition of the jobe seeker
class UserInterviewQuestionSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserInterviewQuestion
        fields = [
                    "id",
                    "title",
                    "description",
                    "answer",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Interview Question'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserInterviewQuestion.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for For Professional Membership of the jobe seeker
class UserProfessionalMembershipSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserProfessionalMembership
        fields = [
                    "id",
                    "title",
                    "Body",
                    "description",
                    "joined_on",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Education'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserProfessionalMembership.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for Volunteering work of the jobe seeker
class UserVolunteeringSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserVolunteering
        fields = [
                    "id",
                    "name",
                    "description",
                    "role",
                    "start_date",
                    "end_date",
                    "city",
                    "city_name",
                 ]

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def validate(self, data):
        """
        Check that the from_year is before the to_year.
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("end date must be after start_date")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'User Education'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserVolunteering.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for Vision and mission of the jobe seeker
class UserVisionMissionSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = UserVisionMission
        fields = [
                    "id",
                    "vision",
                    "mission",
                 ]
    def create(self, validated_data):
        """
        Create and return a new 'User Vision Mission '.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserVisionMission.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for relevants links of the jobe seeker
class UserRelevantLinkSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserRelevantLink
        fields = [
                    "id",
                    "title",
                    "url",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Relevant Links'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserRelevantLink.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise


#  Serialier for Influencer of the jobe seeker
class UserInfluencerSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserInfluencer
        fields = [
                    "id",
                    "name",
                    "url",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Influencer'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserInfluencer.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for publications of the jobe seeker
class UserPublicationSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPublication
        fields = [
                    "id",
                    "name",
                    "url",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Influencer'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPublication.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for publications of the jobe seeker
class UserPreferedJobTypeSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedJobType
        fields = [
                    "id",
                    "job_type",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Prefered Job type'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedJobType.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for UserPreferedIndustry
class UserPreferedIndustrySerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedIndustry
        fields = [
                    "id",
                    "industry",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'UserPreferedIndustry
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedIndustry.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise



#  Serialier for UserPreferedJobStaffLevel
class UserPreferedJobStaffLevelSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedJobStaffLevel
        fields = [
                    "id",
                    "staff_level",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'User Prefered Job type'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedJobStaffLevel.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise


#  Serialier for UserPreferedFunctionalArea
class UserPreferedFunctionalAreaSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedFunctionalArea
        fields = [
                    "id",
                    "area",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'UserPreferedFunctionalArea
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedFunctionalArea.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for UserPreferedWorkSiteType
class UserPreferedWorkSiteTypeSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedWorkSiteType
        fields = [
                    "id",
                    "type",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'UserPreferedWorkSiteType
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedWorkSiteType.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise


#  Serialier for UserPreferedCountry
class UserPreferedCountrySerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedCountry
        fields = [
                    "id",
                    "country",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'UserPreferedCountry
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedCountry.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

#  Serialier for UserPreferedWage
class UserPreferedWageSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserPreferedWage
        fields = [
                    "id",
                    "currency",
                    "period",
                 ]

    def create(self, validated_data):
        """
        Create and return a new 'UserPreferedWage
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserPreferedWage.objects.create(job_profile=user_job_profile, **validated_data)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

class TaskSerializer(ModelSerializer):

    class Meta:
        model = Task
        fields = ['id', 'description']


class UserWorkExperienceListSerializer(ModelSerializer):
    # PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
    #                              message="Phone number must be entered in the format: '+999999999'."
    #                                      " Up to 15 digits allowed.")
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)
    reference_name = serializers.SerializerMethodField(read_only=True)
    reference_position = serializers.SerializerMethodField(read_only=True)
    reference_phone = serializers.SerializerMethodField(read_only=True)
    # validators should be a list
    reference_email = serializers.SerializerMethodField(read_only=True)
    task_list = serializers.SerializerMethodField(read_only=True)
    worked_from_month = serializers.SerializerMethodField(read_only=True)
    worked_from_year = serializers.SerializerMethodField(read_only=True)
    worked_till_month = serializers.SerializerMethodField(read_only=True)
    worked_till_year = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserWorkExperience
        exclude = ['job_profile']
        extra_fields = ['reference_name', 'reference_position', 'reference_phone',
                        'reference_email', 'task_list', 'worked_from_month', 'worked_from_year',
                        'worked_till_month', 'worked_till_year']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(UserWorkExperienceListSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def get_reference_name(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.name
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_reference_position(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.position
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_reference_phone(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.phone
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_reference_email(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.email
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_task_list(self, obj):
        task_list_in_serializer = []
        task_list = Task.objects.filter(work_experience=obj)
        for task in task_list:
            task_serializer = TaskSerializer(task)
            task_list_in_serializer.append(task_serializer.data)
        return task_list_in_serializer

    def get_worked_from_month(self, obj):
        if obj.worked_from:
            return obj.worked_from.month
        else:
            return None

    def get_worked_from_year(self, obj):
        if obj.worked_from:
            return obj.worked_from.year
        else:
            return None

    def get_worked_till_month(self, obj):
        if obj.worked_till:
            return obj.worked_till.month
        else:
            return None

    def get_worked_till_year(self, obj):
        if obj.worked_till:
            return obj.worked_till.year
        return None


class UserWorkExperienceSerializer(ModelSerializer):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the"
                                         " format: '+999999999'. Up to 15 digits allowed.")
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)
    reference_name = serializers.CharField(allow_blank=True, default=None)
    reference_position = serializers.CharField(allow_blank=True, default=None)
    reference_phone = serializers.CharField(validators=[PHONE_REGEX], max_length=25, allow_blank=True, default=None)
    # validators should be a list
    reference_email = serializers.EmailField(allow_blank=True, default=None)
    task_list = serializers.ListField(default=None)
    # worked_from_month = serializers.CharField(read_only=True)
    # worked_from_year = serializers.CharField(read_only=True)
    # worked_till_month = serializers.CharField(read_only=True)
    # worked_till_year = serializers.CharField(read_only=True)

    class Meta:
        model = UserWorkExperience
        exclude = ['job_profile']
        extra_fields = ['reference_name', 'reference_position', 'reference_phone',
                        'reference_email', 'task_list', ]

        # extra_fields = ['reference_name', 'reference_position', 'reference_phone',
        #                 'reference_email', 'task_list', 'worked_from_month',
        #                 'worked_from_year', 'worked_till_month', 'worked_till_year']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(UserWorkExperienceSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def get_reference_name(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.name
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_reference_position(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.position
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_reference_phone(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.phone
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_reference_email(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.email
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_task_list(self, obj):
        task_list_in_serializer = []
        task_list = Task.objects.filter(user=self.request.user, work_experience=obj)
        for task in task_list:
            task_serializer = TaskSerializer(task)
            task_list_in_serializer.append(task_serializer.data)
        return task_list_in_serializer

    # def get_worked_from_month(self, obj):
    #     return obj.worked_from.month
    #
    # def get_worked_from_year(self, obj):
    #     return obj.worked_from.year
    #
    # def get_worked_till_month(self, obj):
    #     return obj.worked_till.month
    #
    # def get_worked_till_year(self, obj):
    #     return obj.worked_till.year

    def validate_worked_from(self, value):
        """
        Check that value is a valid name.
        """
        if str(value) == 'present':  #
            raise serializers.ValidationError("worked from should not be present")  # raise ValidationError
        else:
            try:
                months = range(1, 13)
                year, month, day = map(int, value.split('-'))
                if month not in months:
                    raise serializers.ValidationError("invalid month")  # raise ValidationError
                if len(str(year)) != 4 or not(str(year).isdigit()):
                    raise serializers.ValidationError("invalid year")  # raise ValidationError
                return value
            except:
                raise serializers.ValidationError("invalid date")  # raise ValidationError

    def validate_worked_till(self, value):
        """
        Check that value is a valid name.
        """
        if not value == "present":
            months = range(1, 13)
            try:
                year, month, day = map(int, value.split('-'))
                if month not in months:
                    raise serializers.ValidationError("invalid month")  # raise ValidationError
                if len(str(year)) != 4 or not(str(year).isdigit()):
                    raise serializers.ValidationError("invalid year")  # raise ValidationError
                return value
            except:
                raise serializers.ValidationError("invalid input for worked_till. "
                                                  "input should be a valid date or present")  # raise ValidationError
        elif value == "present":
            return value
        else:
            raise serializers.ValidationError("invalid input for worked_till")  # raise ValidationError

    def validate(self, data):
        """
        Check that the worked_from is before worked_till.
        """
        if data['worked_from'] > data['worked_till']:
            raise serializers.ValidationError("worked_till must occur worked_from")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            reference_name = validated_data.pop('reference_name')
            reference_email = validated_data.pop('reference_email')
            reference_position = validated_data.pop('reference_position')
            reference_phone = validated_data.pop('reference_phone')
            task_list = validated_data.pop('task_list')

            user_work_experience = UserWorkExperience.objects.create(job_profile=user_job_profile, **validated_data)
            content_type_obj = ContentType.objects.get_for_model(user_work_experience)

            if reference_name or reference_email or reference_position or reference_phone:
                reference = Reference.objects.create(content_object=user_work_experience,
                                                        name=reference_name, position=reference_position,
                                                        email=reference_email, phone=reference_phone)
                user_work_experience.reference_name = reference.name
                user_work_experience.reference_position = reference.position
                user_work_experience.reference_email = reference.email
                user_work_experience.reference_phone = reference.phone
            else:
                user_work_experience.reference_name = None
                user_work_experience.reference_position = None
                user_work_experience.reference_email = None
                user_work_experience.reference_phone = None

            user_task_list_in_serializer = []
            # task_list = ['abc', 'abc1', 'abc2', 'abc4']
            if task_list:
                task_list = list(filter(None.__ne__, task_list))
                for task in task_list:
                    user_task = Task.objects.create(user=user, work_experience=user_work_experience,
                                                    description=task)
                    task_serializer = TaskSerializer(user_task)
                    user_task_list_in_serializer.append(task_serializer.data)

            user_work_experience.task_list = user_task_list_in_serializer

            return user_work_experience
        except UserWorkExperience.DoesNotExist:
            raise

    def update(self, instance, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            # if hasattr(validated_data, 'reference_name'):
            #     print(validated_data.get('reference_name'))
            reference_name = validated_data.pop('reference_name')
            # if validated_data.get('reference_email'):
            reference_email = validated_data.pop('reference_email')
            # if validated_data.get('reference_position'):
            reference_position = validated_data.pop('reference_position')
            # if validated_data.get('reference_phone'):
            reference_phone = validated_data.pop('reference_phone')

            # user_work_experience = UserWorkExperience.objects.get(id=instance.id, job_profile=user_job_profile)

            info = model_meta.get_field_info(instance)

            for attr, value in validated_data.items():
                if attr in info.relations and info.relations[attr].to_many:
                    field = getattr(instance, attr)
                    field.set(value)
                else:
                    setattr(instance, attr, value)
            instance.save()

            content_type_obj = ContentType.objects.get_for_model(instance)

            if reference_name or reference_email or reference_position or reference_phone:
                try:
                    reference = Reference.objects.get(object_id=instance.id, content_type=content_type_obj)
                    reference.name = reference_name
                    reference.position = reference_position
                    reference.email = reference_email
                    reference.phone = reference_phone
                    reference.save(update_fields=['name', 'position', 'email', 'phone'])

                except Reference.DoesNotExist as re:
                    reference = Reference.objects.create(content_object=instance,
                                                        name=reference_name, position=reference_position,
                                                        email=reference_email, phone=reference_phone
                                                         )
                instance.reference_name = reference.name
                instance.reference_position = reference.position
                instance.reference_email = reference.email
                instance.reference_phone = reference.phone

            else:
                try:
                    Reference.objects.get(object_id=instance.id, content_type=content_type_obj).delete()
                except Reference.DoesNotExist as re:
                    pass
                instance.reference_name = None
                instance.reference_position = None
                instance.reference_email = None
                instance.reference_phone = None

            return instance
        except Exception as e:
            raise


class RelationshipSerializer(ModelSerializer):

    class Meta:
        model = Relationship
        fields = '__all__'


class UserReferenceSerializer(ModelSerializer):
    relation_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserReference
        fields = [
            "id",
            "name",
            "relation",
            # "entity",
            # "phone",
            "email",
            "relation_name",
        ]

    def create(self, validated_data):
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            # brfore createing the recommendation fire an email to the recommender's email address
            send_recommender_email(validated_data.email)
            return UserReference.objects.create(job_profile=user_job_profile, **validated_data)

        except UserReference.DoesNotExist:
            raise

    def get_relation_name(self, obj):
        return obj.relation.relation


class UserSkillSerializer(ModelSerializer):
    skill_name = serializers.SerializerMethodField(read_only=True)
    skill_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserSkill
        fields = [
            "id",
            "skill",
            "skill_name",
            "skill_type",
            "expertise"
        ]

    def get_skill_name(self, obj):
        return obj.skill.name

    def get_skill_type(self, obj):
        return obj.skill.skill_type

    def create(self, validated_data):
        user = self.context['user']
        skills_data = validated_data.pop("skill")
        expertise = validated_data.pop("expertise")
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            return UserSkill.objects.create(job_profile=user_job_profile, skill=skills_data, expertise=expertise)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise

        # user_skills = UserSkill.objects.create(user=user, skill=skills_data)
        # for skill in skills_data:
        #      user_skills.skill.add(skill)


class FileUploadSerializer(ModelSerializer):

    class Meta:
        model = JobProfileFileUpload
        fields = ['resume_src', 'id']

    def create(self, validated_data):
        user = self.context['user']
        try:
            obj = JobProfileFileUpload.objects.get(user=user)
            obj.resume_src = validated_data.get('resume_src')
            obj.save()
        except ObjectDoesNotExist:
            obj = JobProfileFileUpload.objects.create(user=user, **validated_data)
        return obj

    def update(self, instance, validated_data):
        file = validated_data.get('resume_src')
        instance.resume_src = file
        instance.save()
        return instance


class UserJobProfileRetrieveUpdateSerializer(ModelSerializer):
    resume_id = serializers.SerializerMethodField(read_only=True)
    resume_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserJobProfile
        exclude = ['user']

    def get_resume_id(self, object):
        try:
            return JobProfileFileUpload.objects.get(user=object.user).pk
        except ObjectDoesNotExist:
            return None

    def get_resume_url(self,object):
        try:
           return JobProfileFileUpload.objects.get(user=object.user).resume_src.url
        except ObjectDoesNotExist as e:
            # logger.exception(e)
            return None


class FavoriteItemSerializer(ModelSerializer):

    class Meta:
        model = FavoriteItem
        fields = ['id', 'item']

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create job.\n")
            raise ICFException("Unknown user, cannot create job", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            favorite_item = FavoriteItem.objects.get(user=request.user, **validated_data)
        except ObjectDoesNotExist:
            favorite_item = FavoriteItem.objects.create(user=request.user, **validated_data)

        return favorite_item


class JobUserAppliedSerializer(ModelSerializer):
    class Meta:
        model = JobUserApplied
        fields = ['id', 'job', 'resume']

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user")
            raise ICFException("Unknown user", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            job_user_applied = JobUserApplied.objects.get(user=user, **validated_data)
        except ObjectDoesNotExist:
            try:
                jobseeker_profile = UserJobProfile.objects.get(user=user)
                if jobseeker_profile is not None:
                    try:
                        jobseeker_education = UserEducation.objects.filter(job_profile=jobseeker_profile)
                        if jobseeker_education is not None:
                            job_user_applied = JobUserApplied.objects.create(user=user, **validated_data)
                            job = validated_data.get('job')
                            message = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_APPLIED_NOTIFICATION')
                            message_french = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_APPLIED_NOTIFICATION_FRENCH')
                            message_spanish = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_APPLIED_NOTIFICATION_SPANISH')
                            details_msg = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_APPLIED_DETAIL_NOTIFICATION')
                            details_msg_french = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_APPLIED_DETAIL_NOTIFICATION_FRENCH')
                            details_msg_spanish = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_APPLIED_DETAIL_NOTIFICATION_SPANISH')

                            details = details_msg.format(request.user.display_name,job.owner)
                            details_french = details_msg_french.format(request.user.display_name,job.owner)
                            details_spanish = details_msg_spanish.format(request.user.display_name,job.owner)
                            ICFNotificationManager.add_notification(user=job.owner,
                                                                    message=message,
                                                                    message_french=message_french,
                                                                    message_spanish=message_spanish,
                                                                    details=details,
                                                                    details_french=details_french,
                                                                    details_spanish=details_spanish
                                                                )
                        else:
                            logger.exception("Education details not Found.\n")
                            raise ICFException("Education details not Found", status_code=status.HTTP_400_BAD_REQUEST)
                    except UserEducation.DoesNotExist as e:
                        logger.exception(e)
                        raise ICFException("Education details not Found", status_code=status.HTTP_400_BAD_REQUEST)
            except UserJobProfile.DoesNotExist as e:
                logger.exception(e)
                raise ICFException("user profile DoesNotExist", status_code=status.HTTP_400_BAD_REQUEST)

        return job_user_applied


class UserJobProfileRetrieveSerializer(ModelSerializer):

    class Meta:
        model = UserJobProfile
        fields = '__all__'


class UserEducationRetrieveSerializer(ModelSerializer):
    education_level = serializers.StringRelatedField()
    education_level_name = serializers.SerializerMethodField()
    city = CitySerializer()
    city_name = serializers.SerializerMethodField()

    class Meta:
        model = UserEducation
        fields = [
            "id",
            "education_level",
            "education_level_name",
            "school",
            "from_year",
            "to_year",
            "certification",
            "city",
            "city_name",
        ]

    def get_education_level_name(self, obj):
        if obj.education_level:
            return obj.education_level.level
        else:
            return None

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None


class UserReferenceSerializerForList(ModelSerializer):
    relation = serializers.StringRelatedField()

    class Meta:
        model = UserReference
        fields = '__all__'


class JobAppliedUserSerializer(ModelSerializer):
    resume_url = serializers.SerializerMethodField()
    user_profile = serializers.SerializerMethodField()
    job_profile = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    user_slug = serializers.SerializerMethodField()

    class Meta:
        model = JobUserApplied
        fields = "__all__"

    def get_user_profile(self, obj):
        try:
            message = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION')
            details_msg = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION_DETAIL')
            details = details_msg.format(obj.job.entity)
            try:
                ICFNotificationManager.objects.get(user=obj.user, details=details)
            except Exception:
                ICFNotificationManager.add_notification(user=obj.user, message=message, details=details)

            return UserProfileRetrieveSerializerForList(UserProfile.objects.get(user=obj.user)).data
        except UserProfile.DoesNotExist:
            logger.exception("User profile does not exist for {}".format(obj.user.email))
            return None

    def get_user_slug(self, obj):
        return obj.user.slug

    def get_resume_url(self, obj):
        try:
            if obj.resume:
                try:
                    user_resume = UserResume.objects.get(id=obj.resume.id)
                    if user_resume.resume:
                        return user_resume.resume.url
                    else:
                        try:
                            job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                            if job_profile_file_upload:
                                if job_profile_file_upload.resume_src:
                                    return job_profile_file_upload.resume_src.url
                                else:
                                    return None
                            else:
                                return None

                        except JobProfileFileUpload.DoesNotExist as jpfe:
                            logger.debug(str(jpfe))
                            return None
                except UserResume.DoesNotExist as urdne:
                    logger.debug(str(urdne))
                    try:
                        job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                        if job_profile_file_upload:
                            if job_profile_file_upload.resume_src:
                                return job_profile_file_upload.resume_src.url
                            else:
                                return None
                        else:
                            return None

                    except JobProfileFileUpload.DoesNotExist as jpfe:
                        logger.debug(str(jpfe))
                        return None
                except Exception as e:
                    logger.exception(str(e))
                    raise ICFException(_("Something went wrong, please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
            else:
                # checks if user has default resume that is in JobProfileFileUpload table
                # if user did not upload default resume it returns None
                try:
                    job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                    if job_profile_file_upload:
                        if job_profile_file_upload.resume_src:
                            return job_profile_file_upload.resume_src.url
                        else:
                            return None
                    else:
                        return None
                except JobProfileFileUpload.DoesNotExist as jpfe:
                    logger.debug(str(jpfe))
                    return None
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_job_profile(self, obj):
        try:
            return UserJobProfileRetrieveSerializer(UserJobProfile.objects.get(user=obj.user)).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None

    def get_education(self, obj):
        try:
         return UserEducationRetrieveSerializer(UserEducation.objects.filter(job_profile__user=obj.user), many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for education")
            return None

    def get_experience(self, obj):
        try:
            return UserWorkExperienceSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),many=True).data
        except ValueError as ve:
            logger.exception("Error in getting a value for experience")
            return None
        except ObjectDoesNotExist:
            return None

    def get_reference(self, obj):
        try:
            return UserReferenceSerializerForList(UserReference.objects.filter(job_profile__user=obj.user),many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for reference")
            return None

    def get_skills(self, obj):
        try:
            return UserSkillSerializer(UserSkill.objects.filter(job_profile__user=obj.user),many=True).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for skill")
            return None


class JobAppliedUserStatusSerializer(ModelSerializer):

    class Meta:
        model = JobUserApplied
        fields = ['status']


class DraftJobSerializer(ModelSerializer):

    class Meta:
        model = DraftJob
        fields = ['id', 'contents']


class DraftJobRetrieveSerializer(ModelSerializer):
    data = serializers.SerializerMethodField()

    class Meta:
        model = DraftJob
        fields = ['id', 'contents', 'data']

    def get_data(self, obj):
        try:
            return json.loads(obj.contents)
        except Exception as e:
            return None


class DraftJobListSerializer(ModelSerializer):
    data = serializers.SerializerMethodField()

    class Meta:
        model = DraftJob
        fields = ['id', 'data']

    def get_data(self, obj):
        return json.loads(obj.contents)


# class JobRetrieveOptionalSkillSerializer(ModelSerializer):
#     skill_type = serializers.SerializerMethodField()
#     name = serializers.SerializerMethodField()
#
#     class Meta:
#         model = JobSkillOptional
#         fields = ['skill','skill_type', 'name']
#
#     def get_skill_type(self,object):
#         return object.skill.skill_type
#
#     def get_name(self, object):
#         return object.skill.name


class JobCreateDraftSerializer(ItemCreateUpdateDraftSerializer):
    job_optional_skills = JobRetrieveOptionalSkillSerializer(many=True)
    item_type = serializers.SerializerMethodField()
    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = JobDraft
        exclude = ['owner', ]

    def create(self, validated_data):
        job_skills_data = validated_data.pop("job_optional_skills")

        location_data = validated_data.pop("location")
        location = AddressOptional.objects.create(**location_data)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create job")
            raise ICFException(_("Unknown user, cannot create job"), status_code=status.HTTP_400_BAD_REQUEST)

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('expiry')

        title = validated_data.pop('title')
        title_en = validated_data.pop('title_en')
        title_fr = validated_data.pop('title_fr')
        title_es = validated_data.pop('title_es')

        description = validated_data.pop('description')
        description_en = validated_data.pop('description_en')
        description_fr = validated_data.pop('description_fr')
        description_es = validated_data.pop('description_es')

        job = JobDraft.objects.create(owner=user, location=location,
                                title=title, title_en=title, title_fr=title, title_es=title,
                                 description=description, description_en=description, description_es=description,
                                 description_fr=description, **validated_data)

        job_model = ContentType.objects.get_for_model(job)

        if job_skills_data:
            for skills in job_skills_data:
                skill = skills.pop('skill')
                JobSkillOptional.objects.update_or_create(skill=skill, job=job)

        logger.info("Job created {}".format(job))
        return job

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None


class CheckIfExistingUserSerializer(Serializer):
    mobile_no = serializers.CharField(validators=[User.PHONE_REGEX], max_length=25) # validators should be a list


class UnregisteredUserFileUploadSerializer(ModelSerializer):

    class Meta:
        model = UnregisteredUserFileUpload
        fields = ['mobile', 'resume_src', 'id']

    def create(self, validated_data):
        # mobile = self.context['mobile']
        try:
            obj = UnregisteredUserFileUpload.objects.get(mobile=validated_data.get('mobile'))
            obj.resume_src = validated_data.get('resume_src')
            obj.save()
        except ObjectDoesNotExist:
            obj = UnregisteredUserFileUpload.objects.create(**validated_data)
        return obj

    def update(self, instance, validated_data):
        file = validated_data.get('resume_src')
        instance.resume_src = file
        instance.save()
        return instance


# class UserRelevantLinkSerializer(ModelSerializer):
#     id = serializers.IntegerField(read_only=True)

#     class Meta:
#         model = UserRelevantLink
#         fields = ['id', 'relevant_link']
#         # fields = "__all__"

#     def create(self, validated_data):
#         user = self.context['user']
#         try:
#             user_job_profile = UserJobProfile.objects.get(user=user)
#             relevant_link = validated_data.pop('relevant_link')
#             return UserRelevantLink.objects.create(job_profile=user_job_profile, relevant_link=relevant_link)
#         except UserJobProfile.DoesNotExist as e:
#             logger.exception(e)
#             raise

#  Serializer for creating a new Extra curicular activities.
class UserExtraCurricularActivitiesSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserExtraCurricularActivities
        fields = ['id', 'activitiy', ]
        # fields = "__all__"

    def create(self, validated_data):
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            activitiy = validated_data.pop('activitiy')
            return UserExtraCurricularActivities.objects.create(job_profile=user_job_profile, activitiy=activitiy)
        except UserExtraCurricularActivities.DoesNotExist as e:
            logger.exception(e)
            raise


class UserHobbieSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserHobbie
        fields = ['id', 'hobbie', ]
        # fields = "__all__"

    def create(self, validated_data):
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            hobbie = validated_data.pop('hobbie')
            return UserHobbie.objects.create(job_profile=user_job_profile, hobbie=hobbie)
        except UserJobProfile.DoesNotExist as e:
            logger.exception(e)
            raise


class UserProjectSerializer(ModelSerializer):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'."
                                         " Up to 15 digits allowed.")
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)
    reference_name = serializers.CharField(allow_blank=True, default=None)
    reference_position = serializers.CharField(allow_blank=True, default=None)
    reference_phone = serializers.CharField(validators=[PHONE_REGEX], max_length=25, allow_blank=True, default=None)
    # validators should be a list
    reference_email = serializers.EmailField(allow_blank=True, default=None)

    class Meta:
        model = UserProject
        exclude = ['job_profile']
        extra_fields = ['reference_name', 'reference_position', 'reference_phone', 'reference_email', ]

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(UserProjectSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def validate_start_date(self, value):
        """
        Check that value is a valid start date.
        """
        if str(value) == 'present':  #
            raise serializers.ValidationError("start date should not be present")  # raise ValidationError
        else:
            try:
                months = range(1, 13)
                year, month, day = map(int, value.split('-'))
                if month not in months:
                    raise serializers.ValidationError("invalid month")  # raise ValidationError
                if len(str(year)) != 4 or not (str(year).isdigit()):
                    raise serializers.ValidationError("invalid year")  # raise ValidationError
                return value
            except:
                raise serializers.ValidationError("invalid date")  # raise ValidationError

    def validate_end_date(self, value):
        """
        Check that value is a valid end_date.
        """
        if not value == "present":
            months = range(1, 13)
            try:
                year, month, day = map(int, value.split('-'))
                if month not in months:
                    raise serializers.ValidationError("invalid month")  # raise ValidationError
                if len(str(year)) != 4 or not (str(year).isdigit()):
                    raise serializers.ValidationError("invalid year")  # raise ValidationError
                return value
            except:
                raise serializers.ValidationError(
                    "invalid input for end date. input should be a valid date or present")  # raise ValidationError
        elif value == "present":
            return value
        else:
            raise serializers.ValidationError("invalid input for end date")  # raise ValidationError

    def validate(self, data):
        """
        Check that the start_date is before the end_date.
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("end_date must be after start date")
        return data

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def get_reference_name(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.name
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_reference_position(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.position
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_reference_phone(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.phone
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    def get_reference_email(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(content_obj=obj, content_type=content_type_obj)
            return reference.email
        except ContentType.DoesNotExist as cde:
            raise
        except Reference.DoesNotExist as rde:
            return None

    # def validate_worked_from(self, value):
    #     """
    #     Check that value is a valid name.
    #     """
    #     if str(value) == 'present':  #
    #         raise serializers.ValidationError("worked from should not be present")  # raise ValidationError
    #     else:
    #         try:
    #             months = range(1, 13)
    #             year, month, day = map(int, value.split('-'))
    #             if month not in months:
    #                 raise serializers.ValidationError("invalid month")  # raise ValidationError
    #             if len(str(year)) != 4 or not (str(year).isdigit()):
    #                 raise serializers.ValidationError("invalid year")  # raise ValidationError
    #             return value
    #         except:
    #             raise serializers.ValidationError("invalid date")  # raise ValidationError
    #
    # def validate_worked_till(self, value):
    #     """
    #     Check that value is a valid name.
    #     """
    #     if not value == "present":
    #         months = range(1, 13)
    #         try:
    #             year, month, day = map(int, value.split('-'))
    #             if month not in months:
    #                 raise serializers.ValidationError("invalid month")  # raise ValidationError
    #             if len(str(year)) != 4 or not (str(year).isdigit()):
    #                 raise serializers.ValidationError("invalid year")  # raise ValidationError
    #             return value
    #         except:
    #             raise serializers.ValidationError(
    #                 "invalid input for worked_till. input should be a valid date or present")  # raise ValidationError
    #     elif value == "present":
    #         return value
    #     else:
    #         raise serializers.ValidationError("invalid input for worked_till")  # raise ValidationError

    # def validate(self, data):
    #     """
    #     Check that the worked_from is before worked_till.
    #     """
    #     if data['worked_from'] > data['worked_till']:
    #         raise serializers.ValidationError("worked_till must occur worked_from")
    #     return data

    def create(self, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            reference_name = validated_data.pop('reference_name')
            reference_email = validated_data.pop('reference_email')
            reference_position = validated_data.pop('reference_position')
            reference_phone = validated_data.pop('reference_phone')

            user_project = UserProject.objects.create(job_profile=user_job_profile, **validated_data)
            content_type_obj = ContentType.objects.get_for_model(user_project)

            if reference_name or reference_email or reference_position or reference_phone:
                reference = Reference.objects.create(content_object=user_project,
                                                     name=reference_name, position=reference_position,
                                                     email=reference_email, phone=reference_phone)
                user_project.reference_name = reference.name
                user_project.reference_position = reference.position
                user_project.reference_email = reference.email
                user_project.reference_phone = reference.phone
            else:
                user_project.reference_name = None
                user_project.reference_position = None
                user_project.reference_email = None
                user_project.reference_phone = None

            return user_project
        except UserProject.DoesNotExist:
            raise

    def update(self, instance, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        user = self.context['user']
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            reference_name = validated_data.pop('reference_name')
            reference_email = validated_data.pop('reference_email')
            reference_position = validated_data.pop('reference_position')
            reference_phone = validated_data.pop('reference_phone')

            info = model_meta.get_field_info(instance)

            for attr, value in validated_data.items():
                if attr in info.relations and info.relations[attr].to_many:
                    field = getattr(instance, attr)
                    field.set(value)
                else:
                    setattr(instance, attr, value)
            instance.save()

            content_type_obj = ContentType.objects.get_for_model(instance)

            if reference_name or reference_email or reference_position or reference_phone:
                try:
                    reference = Reference.objects.get(object_id=instance.id, content_type=content_type_obj)
                    reference.name = reference_name
                    reference.position = reference_position
                    reference.email = reference_email
                    reference.phone = reference_phone
                    reference.save(update_fields=['name', 'position', 'email', 'phone'])

                except Reference.DoesNotExist as re:
                    reference = Reference.objects.create(content_object=instance,
                                                         name=reference_name, position=reference_position,
                                                         email=reference_email, phone=reference_phone
                                                         )
                instance.reference_name = reference.name
                instance.reference_position = reference.position
                instance.reference_email = reference.email
                instance.reference_phone = reference.phone

            else:
                try:
                    Reference.objects.get(object_id=instance.id, content_type=content_type_obj).delete()
                except Reference.DoesNotExist as re:
                    pass
                instance.reference_name = None
                instance.reference_position = None
                instance.reference_email = None
                instance.reference_phone = None

            return instance
        except Exception as e:
            raise


class UserProjectListSerializer(ModelSerializer):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'."
                                         " Up to 15 digits allowed.")
    id = serializers.ReadOnlyField()
    city_name = serializers.SerializerMethodField(read_only=True)
    reference_name = serializers.SerializerMethodField(read_only=True)
    reference_position = serializers.SerializerMethodField(read_only=True)
    reference_phone = serializers.SerializerMethodField(read_only=True)
    # validators should be a list
    reference_email = serializers.SerializerMethodField(read_only=True)
    start_date_month = serializers.SerializerMethodField(read_only=True)
    start_date_year = serializers.SerializerMethodField(read_only=True)
    end_date_month = serializers.SerializerMethodField(read_only=True)
    end_date_year = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserProject
        exclude = ['job_profile']
        extra_fields = ['reference_name', 'reference_position', 'reference_phone',
                        'reference_email', 'start_date_month', 'start_date_year',
                        'end_date_month', 'end_date_year']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(UserProjectListSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def get_city_name(self, obj):
        if obj.city:
            serializer = CitySerializer(City.objects.filter(id=obj.city_id).first())
            return serializer.data['city']
        else:
            return None

    def get_reference_name(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.name
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_reference_position(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.position
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_reference_phone(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.phone
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_reference_email(self, obj):
        try:
            content_type_obj = ContentType.objects.get_for_model(obj)
            reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
            return reference.email
        except ContentType.DoesNotExist as ce:
            raise
        except Reference.DoesNotExist as re:
            return None

    def get_start_date_month(self, obj):
        if obj.start_date:
            return obj.start_date.month
        else:
            return None

    def get_start_date_year(self, obj):
        if obj.start_date:
            return obj.start_date.year
        else:
            return None

    def get_end_date_month(self, obj):
        if obj.end_date:
            return obj.end_date.month
        else:
            return None

    def get_end_date_year(self, obj):
        if obj.end_date:
            return obj.end_date.year
        else:
            return None


class UserResumeCreateSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    title = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    biography = serializers.ReadOnlyField()
    user_education_list = serializers.SerializerMethodField(read_only=True)
    user_work_experience_list = serializers.SerializerMethodField(read_only=True)
    user_project_list = serializers.SerializerMethodField(read_only=True)
    user_skill_list = serializers.SerializerMethodField(read_only=True)
    user_hobbie_list = serializers.SerializerMethodField(read_only=True)
    user_relevant_link_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserResume
        exclude = ['job_profile', 'thumbnail', 'resume', 'slug']
        extra_fields = ['biography', 'title', 'name', 'user_education_list', 'user_work_experience_list',
                        'user_project_list', 'user_skill_list', 'user_hobbie_list', 'user_relevant_link_list']

    def create(self, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create resume.")
            raise ICFException(_("Unknown user, cannot create resume."), status_code=status.HTTP_400_BAD_REQUEST)
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            # biography = validated_data.pop('biography')
            # reference_email = validated_data.pop('reference_email')
            # reference_position = validated_data.pop('reference_position')
            # reference_phone = validated_data.pop('reference_phone')

            if user.first_name and user.last_name:
                user_resume_title = user.first_name+"-"+user.last_name
            else:
                user_resume_title = user.username
            user_resume = UserResume.objects.create(job_profile=user_job_profile, biography=user_job_profile.pro_bio,
                                                    title=user_resume_title, name=user_resume_title)

            user_educations = UserEducation.objects.filter(job_profile=user_job_profile)

            for index, user_education in enumerate(user_educations):
                try:
                    user_resume_component_education = UserResumeComponent.objects.create(content_object=user_education,
                                                                                         user_resume=user_resume,
                                                                                         sort_order=index)
                except ContentType.DoesNotExists as ctdne:
                    raise

            user_work_experiences = UserWorkExperience.objects.filter(job_profile=user_job_profile)

            for index, user_work_experience in enumerate(user_work_experiences):
                try:
                    i = 0
                    user_resume_component_experience = UserResumeComponent.objects.create(content_object=user_work_experience,
                                                                                          user_resume=user_resume,
                                                                                          sort_order=index)
                    i = i + 1
                except Exception as e:
                    logger.exception(str(e))
                    raise

            user_skills = UserSkill.objects.filter(job_profile=user_job_profile)

            for user_skill in user_skills:
                try:

                    user_resume_component_skill = UserResumeComponent.objects.\
                        create(content_object=user_skill, user_resume=user_resume)

                except Exception as e:
                    logger.exception(str(e))
                    raise

            user_hobbies = UserHobbie.objects.filter(job_profile=user_job_profile)

            for user_hobbie in user_hobbies:
                try:
                    user_resume_component_hobbie = UserResumeComponent.objects.create(content_object=user_hobbie,
                                                                               user_resume=user_resume)
                except Exception as e:
                    logger.exception(str(e))
                    raise

            user_relevant_links = UserRelevantLink.objects.filter(job_profile=user_job_profile)

            for user_relevant_link in user_relevant_links:
                try:
                    user_resume_relevant_link = UserResumeComponent.objects.create(content_object=user_relevant_link,
                                                                                      user_resume=user_resume)
                except Exception as e:
                    logger.exception(str(e))
                    raise

            user_projects = UserProject.objects.filter(job_profile=user_job_profile)

            for index, user_project in enumerate(user_projects):
                try:
                    user_resume_project = UserResumeComponent.objects.create(content_object=user_project,
                                                                             user_resume=user_resume,
                                                                             sort_order=index
                                                                             )
                except Exception as e:
                    logger.exception(str(e))
                    raise

            return user_resume
        except UserJobProfile.DoesNotExist as je:
            logger.exception('UserJobProfile object not found for the logged in user.')
            raise ICFException(_("You does not have job profile please create it."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            raise

    def get_user_education_list(self, obj):
        try:
            user_education_serializer_list = []
            content_type = ContentType.objects.get(model='usereducation')
            user_resume_component_education_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type).order_by('sort_order')
            if user_resume_component_education_list is not None:
                for resume_education in user_resume_component_education_list:
                    education_obj = UserEducation.objects.get(id=resume_education.object_id)
                    education_serializer = UserEducationRetrieveSerializer(education_obj)
                    # print(education_serializer.data)
                    user_education_serializer_list.append(education_serializer.data)
                return user_education_serializer_list
            else:
                return None
        except UserEducation.DoesNotExist as ue:
            logger.exception('UserEducation object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user education.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_work_experience_list(self, obj):
        try:
            user_work_experience_serializer_list = []
            content_type = ContentType.objects.get(model='userworkexperience')
            user_resume_work_experience_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type).order_by('sort_order')
            if user_resume_work_experience_list is not None:
                for user_resume_work_experience in user_resume_work_experience_list:
                    work_experience = UserWorkExperience.objects.get(id=user_resume_work_experience.object_id)
                    work_experience_serializer = UserWorkExperienceListSerializer(work_experience)
                    user_work_experience_serializer_list.append(work_experience_serializer.data)
                return user_work_experience_serializer_list
            else:
                return None
        except UserWorkExperience.DoesNotExist as uene:
            logger.exception('UserWorkExperience object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user work experience.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_project_list(self, obj):
        try:
            user_project_serializer_list = []
            content_type = ContentType.objects.get(model='userproject')
            user_resume_project_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                           content_type=content_type).order_by('sort_order')
            if user_resume_project_list is not None:
                for user_resume_project in user_resume_project_list:
                    project = UserProject.objects.get(id=user_resume_project.object_id)
                    project_serializer = UserProjectListSerializer(project)
                    user_project_serializer_list.append(project_serializer.data)
                return user_project_serializer_list
            else:
                return None

        except UserProject.DoesNotExist as upne:
            logger.exception('UserProject object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user project.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_skill_list(self, obj):
        try:
            user_skill_serializer_list = []
            content_type = ContentType.objects.get(model='userskill')
            user_resume_skill_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                   content_type=content_type)
            if user_resume_skill_list is not None:
                for user_resume_skill in user_resume_skill_list:
                    skill = UserSkill.objects.get(id=user_resume_skill.object_id)
                    skill_serializer = UserSkillSerializer(skill)
                    user_skill_serializer_list.append(skill_serializer.data)
                return user_skill_serializer_list
            else:
                return None

        except UserSkill.DoesNotExist as usdne:
            logger.exception('UserSkill object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user skill.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_hobbie_list(self, obj):
        try:
            user_hobby_serializer_list = []
            content_type = ContentType.objects.get(model='userhobbie')
            user_resume_hobbie_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                 content_type=content_type)
            if user_resume_hobbie_list is not None:
                for user_resume_hobby in user_resume_hobbie_list:
                    hobby = UserHobbie.objects.get(id=user_resume_hobby.object_id)
                    hobby_serializer = UserHobbieSerializer(hobby)
                    user_hobby_serializer_list.append(hobby_serializer.data)
                return user_hobby_serializer_list
            else:
                return None

        except UserHobbie.DoesNotExist as hbe:
            logger.exception('UserHobbie object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user hobbie.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_relevant_link_list(self, obj):
        try:
            user_relevant_link_serializer_list = []
            content_type = ContentType.objects.get(model='userrelevantlink')
            user_relevant_link_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                   content_type=content_type)
            if user_relevant_link_list is not None:
                for user_relevant_link in user_relevant_link_list:
                    link = UserRelevantLink.objects.get(id=user_relevant_link.object_id)
                    relevant_link_serializer = UserRelevantLinkSerializer(link)
                    user_relevant_link_serializer_list.append(relevant_link_serializer.data)
                return user_relevant_link_serializer_list
            else:
                return None

        except UserSkill.DoesNotExist as usdne:
            logger.exception('UserSkill object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user skill.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class UserResumeUpdateSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    title = serializers.CharField(default=None, allow_blank=True)
    name = serializers.CharField(default=None, allow_blank=True)
    biography = serializers.CharField(default=None, allow_blank=True)
    user_resume_id = serializers.IntegerField(write_only=True)
    user_education_list = serializers.SerializerMethodField(read_only=True)
    user_work_experience_list = serializers.SerializerMethodField(read_only=True)
    user_project_list = serializers.SerializerMethodField(read_only=True)
    user_skill_list = serializers.SerializerMethodField(read_only=True)
    user_hobbie_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserResume
        exclude = ['job_profile', 'thumbnail', 'resume', 'slug']
        extra_fields = ['biography', 'title', 'name', 'user_education_list', 'user_work_experience_list',
                        'user_project_list', 'user_skill_list', 'user_hobbie_list']

    def update(self, instance, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create resume.")
            raise ICFException(_("Unknown user, cannot create resume."), status_code=status.HTTP_400_BAD_REQUEST)
        try:
            biography = validated_data.get('biography', None)

            # user_resume = UserResume.objects.get(job_profile=user_job_profile)

            if biography:
                instance.biography = biography
                instance.save(update_fields=['biography'])

            title = validated_data.get('title', None)

            if title:
                instance.title = title
                instance.save(update_fields=['title'])

            name = validated_data.get('name', None)

            if name:
                instance.name = name
                instance.save(update_fields=['name'])

            return instance
        except UserJobProfile.DoesNotExist as je:
            logger.exception('UserJobProfile object not found for the logged in user.')
            raise ICFException(_("You does not have job profile please create it."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except UserResume.DoesNotExist as re:
            logger.exception('UserResume object not found.')
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Could not update resume, reason :{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_education_list(self, obj):
        try:
            user_education_serializer_list = []
            content_type = ContentType.objects.get(model='usereducation')
            user_resume_component_education_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type)
            if user_resume_component_education_list is not None:
                for resume_education in user_resume_component_education_list:
                    education_obj = UserEducation.objects.get(id=resume_education.object_id)
                    education_serializer = UserEducationRetrieveSerializer(education_obj)
                    user_education_serializer_list.append(education_serializer.data)
                return user_education_serializer_list
            else:
                return None
        except UserEducation.DoesNotExist as ue:
            logger.exception('UserEducation object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user education.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_work_experience_list(self, obj):
        try:
            user_work_experience_serializer_list = []
            content_type = ContentType.objects.get(model='userworkexperience')
            user_resume_work_experience_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type)
            if user_resume_work_experience_list is not None:
                for user_resume_work_experience in user_resume_work_experience_list:
                    work_experience = UserWorkExperience.objects.get(id=user_resume_work_experience.object_id)
                    work_experience_serializer = UserWorkExperienceListSerializer(work_experience)
                    user_work_experience_serializer_list.append(work_experience_serializer.data)
                return user_work_experience_serializer_list
            else:
                return None
        except UserWorkExperience.DoesNotExist as uene:
            logger.exception('UserWorkExperience object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user work experience.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_project_list(self, obj):
        try:
            user_project_serializer_list = []
            content_type = ContentType.objects.get(model='userproject')
            user_resume_project_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                           content_type=content_type)
            if user_resume_project_list is not None:
                for user_resume_project in user_resume_project_list:
                    project = UserProject.objects.get(id=user_resume_project.object_id)
                    project_serializer = UserProjectListSerializer(project)
                    user_project_serializer_list.append(project_serializer.data)
                return user_project_serializer_list
            else:
                return None

        except UserProject.DoesNotExist as upne:
            logger.exception('UserProject object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user project.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_skill_list(self, obj):
        try:
            user_skill_serializer_list = []
            content_type = ContentType.objects.get(model='userskill')
            user_resume_skill_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                   content_type=content_type)
            if user_resume_skill_list is not None:
                for user_resume_skill in user_resume_skill_list:
                    skill = UserSkill.objects.get(id=user_resume_skill.object_id)
                    skill_serializer = UserSkillSerializer(skill)
                    user_skill_serializer_list.append(skill_serializer.data)
                return user_skill_serializer_list
            else:
                return None

        except UserSkill.DoesNotExist as usdne:
            logger.exception('UserSkill object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user skill.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_hobbie_list(self, obj):
        try:
            user_hobby_serializer_list = []
            content_type = ContentType.objects.get(model='userhobbie')
            user_resume_hobbie_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                 content_type=content_type)
            if user_resume_hobbie_list is not None:
                for user_resume_hobby in user_resume_hobbie_list:
                    hobby = UserHobbie.objects.get(id=user_resume_hobby.object_id)
                    hobby_serializer = UserHobbieSerializer(hobby)
                    user_hobby_serializer_list.append(hobby_serializer.data)
                return user_hobby_serializer_list
            else:
                return None

        except UserHobbie.DoesNotExist as hbe:
            logger.exception('UserHobbie object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user hobbie.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class UserResumeListSerializer(ModelSerializer):

    class Meta:
        model = UserResume
        fields = '__all__'


class UserResumeRetrieveSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    slug = serializers.ReadOnlyField()
    title = serializers.CharField(default=None, allow_blank=True)
    name = serializers.CharField(default=None, allow_blank=True)
    biography = serializers.CharField(default=None, allow_blank=True)
    user_resume_id = serializers.IntegerField(write_only=True)
    user_education_list = serializers.SerializerMethodField(read_only=True)
    user_work_experience_list = serializers.SerializerMethodField(read_only=True)
    user_project_list = serializers.SerializerMethodField(read_only=True)
    user_skill_list = serializers.SerializerMethodField(read_only=True)
    user_hobbie_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserResume
        exclude = ['job_profile']
        extra_fields = ['biography', 'title', 'name', 'thumbnail', 'resume', 'user_education_list',
                        'user_work_experience_list',
                        'user_project_list', 'user_skill_list', 'user_hobbie_list']

    def get_user_education_list(self, obj):
        try:
            user_education_serializer_list = []
            content_type = ContentType.objects.get(model='usereducation')
            user_resume_component_education_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type).order_by('sort_order')
            if user_resume_component_education_list is not None:
                for resume_education in user_resume_component_education_list:
                    education_obj = UserEducation.objects.get(id=resume_education.object_id)
                    education_serializer = UserEducationRetrieveSerializer(education_obj)
                    # print(education_serializer.data)
                    user_education_serializer_list.append(education_serializer.data)
                return user_education_serializer_list
            else:
                return None
        except UserEducation.DoesNotExist as ue:
            logger.exception('UserEducation object does not exist.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user education.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_work_experience_list(self, obj):
        try:
            user_work_experience_serializer_list = []
            content_type = ContentType.objects.get(model='userworkexperience')
            user_resume_work_experience_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type).order_by('sort_order')
            if user_resume_work_experience_list is not None:
                for user_resume_work_experience in user_resume_work_experience_list:
                    work_experience = UserWorkExperience.objects.get(id=user_resume_work_experience.object_id)
                    work_experience_serializer = UserWorkExperienceListSerializer(work_experience)
                    user_work_experience_serializer_list.append(work_experience_serializer.data)
                return user_work_experience_serializer_list
            else:
                return None
        except UserWorkExperience.DoesNotExist as uene:
            logger.exception('UserWorkExperience object does not exist.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user work experience.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_project_list(self, obj):
        try:
            user_project_serializer_list = []
            content_type = ContentType.objects.get(model='userproject')
            user_resume_project_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                           content_type=content_type).order_by('sort_order')
            if user_resume_project_list is not None:
                for user_resume_project in user_resume_project_list:
                    project = UserProject.objects.get(id=user_resume_project.object_id)
                    project_serializer = UserProjectListSerializer(project)
                    user_project_serializer_list.append(project_serializer.data)
                return user_project_serializer_list
            else:
                return None

        except UserProject.DoesNotExist as upne:
            logger.exception('UserProject object does not exist.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user project.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_skill_list(self, obj):
        try:
            user_skill_serializer_list = []
            content_type = ContentType.objects.get(model='userskill')
            user_resume_skill_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                   content_type=content_type)
            if user_resume_skill_list is not None:
                for user_resume_skill in user_resume_skill_list:
                    skill = UserSkill.objects.get(id=user_resume_skill.object_id)
                    skill_serializer = UserSkillSerializer(skill)
                    user_skill_serializer_list.append(skill_serializer.data)
                return user_skill_serializer_list
            else:
                return None

        except UserSkill.DoesNotExist as usdne:
            logger.exception('UserSkill object does not exist.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user skill.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_hobbie_list(self, obj):
        try:
            user_hobby_serializer_list = []
            content_type = ContentType.objects.get(model='userhobbie')
            user_resume_hobbie_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                 content_type=content_type)
            if user_resume_hobbie_list is not None:
                for user_resume_hobby in user_resume_hobbie_list:
                    hobby = UserHobbie.objects.get(id=user_resume_hobby.object_id)
                    hobby_serializer = UserHobbieSerializer(hobby)
                    user_hobby_serializer_list.append(hobby_serializer.data)
                return user_hobby_serializer_list
            else:
                return None

        except UserHobbie.DoesNotExist as hbe:
            logger.exception('UserHobbie object does not exist.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user hobbie.')
            raise ICFException(_("Could not get resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class UserResumeCreateCloneSerializer(ModelSerializer):
    id = serializers.ReadOnlyField()
    title = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    biography = serializers.ReadOnlyField()
    user_education_list = serializers.SerializerMethodField(read_only=True)
    user_work_experience_list = serializers.SerializerMethodField(read_only=True)
    user_project_list = serializers.SerializerMethodField(read_only=True)
    user_skill_list = serializers.SerializerMethodField(read_only=True)
    user_hobbie_list = serializers.SerializerMethodField(read_only=True)
    user_relevant_link_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserResume
        exclude = ['job_profile', 'thumbnail', 'resume', 'slug']
        extra_fields = ['biography', 'title', 'name', 'user_education_list', 'user_work_experience_list',
                        'user_project_list', 'user_skill_list', 'user_hobbie_list', 'user_relevant_link_list']

    def create(self, validated_data):
        """
        Create and return a new 'User Work Experience'.
        """
        resume_slug = self.context['slug']
        user = self.context.get("user")
        if user:
            user = user
        else:
            logger.exception("Unknown user, cannot create resume.")
            raise ICFException(_("Unknown user, cannot create resume."), status_code=status.HTTP_400_BAD_REQUEST)
        try:
            user_job_profile = UserJobProfile.objects.get(user=user)
            user_resume_to_be_cloned = UserResume.objects.get(slug=resume_slug, job_profile=user_job_profile)

            user_resume_new = UserResume.objects.create(job_profile=user_resume_to_be_cloned.job_profile,
                                                        title=user_resume_to_be_cloned.title,
                                                        name=user_resume_to_be_cloned.name,
                                                        biography=user_resume_to_be_cloned.biography)

            # create education user components

            content_type_education = ContentType.objects.get(model='usereducation')
            user_education_resume_components = UserResumeComponent.objects.filter(user_resume=user_resume_to_be_cloned,
                                                                 content_type=content_type_education)

            for user_education_resume_component in user_education_resume_components:
                try:
                    user_education = UserEducation.objects.get(id=user_education_resume_component.object_id)
                    user_resume_component_education = UserResumeComponent.objects.create(content_object=user_education,
                                                                                         user_resume=user_resume_new)

                except UserEducation.DoesNotExists as ctdne:
                    raise

            # create work experience user components

            content_type_work_experience = ContentType.objects.get(model='userworkexperience')
            user_work_exp_resume_components = UserResumeComponent.objects.filter(user_resume=user_resume_to_be_cloned,
                                                                                  content_type=content_type_work_experience)

            for user_work_exp_resume_component in user_work_exp_resume_components:
                try:
                    user_work_exp = UserWorkExperience.objects.get(id=user_work_exp_resume_component.object_id)
                    user_resume_component_work_exp = UserResumeComponent.objects.create(content_object=user_work_exp,
                                                                                         user_resume=user_resume_new)

                except UserWorkExperience.DoesNotExists as ctdne:
                    raise

            # ------------------------------------------
            # create skill user components

            content_type_user_skill = ContentType.objects.get(model='userskill')
            user_user_skill_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume_to_be_cloned,
                content_type=content_type_user_skill)

            for user_user_skill_resume_component in user_user_skill_resume_components:
                try:
                    user_skill = UserSkill.objects.get(id=user_user_skill_resume_component.object_id)
                    user_resume_component_skill = UserResumeComponent.objects.create(
                        content_object=user_skill,
                        user_resume=user_resume_new)

                except UserSkill.DoesNotExists as ctdne:
                    raise

            # ----------------------------------
            # create relevant link user components

            content_type_user_relevant_link = ContentType.objects.get(model='userrelevantlink')
            user_relevant_link_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume_to_be_cloned,
                content_type=content_type_user_relevant_link)

            for user_relevant_link_resume_component in user_relevant_link_resume_components:
                try:
                    user_relevant_link = UserRelevantLink.objects.get(id=user_relevant_link_resume_component.object_id)
                    user_resume_relevant_link = UserResumeComponent.objects.create(
                        content_object=user_relevant_link,
                        user_resume=user_resume_new)

                except UserRelevantLink.DoesNotExists as ctdne:
                    raise

            # ----------------------------------
            # create project user components

            content_type_user_project = ContentType.objects.get(model='userproject')
            user_project_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume_to_be_cloned,
                content_type=content_type_user_project)

            for user_project_resume_component in user_project_resume_components:
                try:
                    user_project = UserProject.objects.get(
                        id=user_project_resume_component.object_id)
                    user_resume_project = UserResumeComponent.objects.create(
                        content_object=user_project,
                        user_resume=user_resume_new)

                except UserProject.DoesNotExists as ctdne:
                    raise

            # ----------------------------------
            # create hobby user components

            content_type_user_hobbie = ContentType.objects.get(model='userhobbie')
            user_hobbie_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume_to_be_cloned,
                content_type=content_type_user_hobbie)

            for user_hobbie_resume_component in user_hobbie_resume_components:
                try:
                    user_hobbie = UserHobbie.objects.get(
                        id=user_hobbie_resume_component.object_id)
                    user_resume_hobbie = UserResumeComponent.objects.create(
                        content_object=user_hobbie,
                        user_resume=user_resume_new)

                except UserHobbie.DoesNotExists as ctdne:
                    raise

            return user_resume_new

        except UserResume.DoesNotExist as udne:
            logger.exception('UserResume object not found for the logged in user.')
            raise ICFException(_("Something went wrong. Contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except UserJobProfile.DoesNotExist as je:
            logger.exception('UserJobProfile object not found for the logged in user.')
            raise ICFException(_("You does not have job profile please create it."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            raise

    def get_user_education_list(self, obj):
        try:
            user_education_serializer_list = []
            content_type = ContentType.objects.get(model='usereducation')
            user_resume_component_education_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type)
            if user_resume_component_education_list is not None:
                for resume_education in user_resume_component_education_list:
                    education_obj = UserEducation.objects.get(id=resume_education.object_id)
                    education_serializer = UserEducationRetrieveSerializer(education_obj)
                    # print(education_serializer.data)
                    user_education_serializer_list.append(education_serializer.data)
                return user_education_serializer_list
            else:
                return None
        except UserEducation.DoesNotExist as ue:
            logger.exception('UserEducation object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user education.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_work_experience_list(self, obj):
        try:
            user_work_experience_serializer_list = []
            content_type = ContentType.objects.get(model='userworkexperience')
            user_resume_work_experience_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                     content_type=content_type)
            if user_resume_work_experience_list is not None:
                for user_resume_work_experience in user_resume_work_experience_list:
                    work_experience = UserWorkExperience.objects.get(id=user_resume_work_experience.object_id)
                    work_experience_serializer = UserWorkExperienceListSerializer(work_experience)
                    user_work_experience_serializer_list.append(work_experience_serializer.data)
                return user_work_experience_serializer_list
            else:
                return None
        except UserWorkExperience.DoesNotExist as uene:
            logger.exception('UserWorkExperience object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user work experience.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_project_list(self, obj):
        try:
            user_project_serializer_list = []
            content_type = ContentType.objects.get(model='userproject')
            user_resume_project_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                           content_type=content_type)
            if user_resume_project_list is not None:
                for user_resume_project in user_resume_project_list:
                    project = UserProject.objects.get(id=user_resume_project.object_id)
                    project_serializer = UserProjectListSerializer(project)
                    user_project_serializer_list.append(project_serializer.data)
                return user_project_serializer_list
            else:
                return None

        except UserProject.DoesNotExist as upne:
            logger.exception('UserProject object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user project.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_skill_list(self, obj):
        try:
            user_skill_serializer_list = []
            content_type = ContentType.objects.get(model='userskill')
            user_resume_skill_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                   content_type=content_type)
            if user_resume_skill_list is not None:
                for user_resume_skill in user_resume_skill_list:
                    skill = UserSkill.objects.get(id=user_resume_skill.object_id)
                    skill_serializer = UserSkillSerializer(skill)
                    user_skill_serializer_list.append(skill_serializer.data)
                return user_skill_serializer_list
            else:
                return None

        except UserSkill.DoesNotExist as usdne:
            logger.exception('UserSkill object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user skill.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_hobbie_list(self, obj):
        try:
            user_hobby_serializer_list = []
            content_type = ContentType.objects.get(model='userhobbie')
            user_resume_hobbie_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                 content_type=content_type)
            if user_resume_hobbie_list is not None:
                for user_resume_hobby in user_resume_hobbie_list:
                    hobby = UserHobbie.objects.get(id=user_resume_hobby.object_id)
                    hobby_serializer = UserHobbieSerializer(hobby)
                    user_hobby_serializer_list.append(hobby_serializer.data)
                return user_hobby_serializer_list
            else:
                return None

        except UserHobbie.DoesNotExist as hbe:
            logger.exception('UserHobbie object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user hobbie.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_user_relevant_link_list(self, obj):
        try:
            user_relevant_link_serializer_list = []
            content_type = ContentType.objects.get(model='userrelevantlink')
            user_relevant_link_list = UserResumeComponent.objects.filter(user_resume=obj,
                                                                   content_type=content_type)
            if user_relevant_link_list is not None:
                for user_relevant_link in user_relevant_link_list:
                    link = UserRelevantLink.objects.get(id=user_relevant_link.object_id)
                    relevant_link_serializer = UserRelevantLinkSerializer(link)
                    user_relevant_link_serializer_list.append(relevant_link_serializer.data)
                return user_relevant_link_serializer_list
            else:
                return None

        except UserSkill.DoesNotExist as usdne:
            logger.exception('UserSkill object does not exist.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ContentType.DoesNotExist as ctne:
            logger.exception('ContentType object does not exist for user skill.')
            raise ICFException(_("Could not create resume, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class TaskCreateSerializer(ModelSerializer):
    work_experience_id = serializers.IntegerField()

    class Meta:
        model = Task
        exclude = ['user', 'work_experience']
        extra_fields = ['work_experience_id']

    def create(self, validated_data):
        try:
            """
            Create and return a new 'User Work Experience'.
            """
            work_experience_id = self.context['work_experience_id']
            task_desc = self.context['task_desc']
            user = self.context.get("user")

            work_experience = UserWorkExperience.objects.get(id=work_experience_id)
            if user:
                user = user
            else:
                logger.exception("Unknown user, cannot create resume.")
                raise ICFException(_("Unknown user, cannot create resume."), status_code=status.HTTP_400_BAD_REQUEST)
            task = Task.objects.create(user=user, work_experience=work_experience, description=task_desc)
            return task

        except UserWorkExperience.DoesNotExist as wde:
            logger.info("Could not create task {}".format(str(wde)))
            raise ICFException(_("Could not create task. Please try again"), status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.info("Could not create task {}".format(str(e)))
            raise ICFException(_("Could not create task. Please try again"), status_code=status.HTTP_400_BAD_REQUEST)


class CountryJobListSerializer(ItemListSerializer):
    salary_currency = serializers.StringRelatedField()
    is_sponsored_job = serializers.SerializerMethodField()
    no_of_views = serializers.SerializerMethodField()
    no_of_applied_user = serializers.SerializerMethodField()

    class Meta(ItemListSerializer.Meta):
        model = Job
        fields = ItemListSerializer.Meta.fields + ('experience_years', 'experience_months',
                                                   'entity', 'salary_currency', 'is_sponsored_job',
                                                   'no_of_views', 'no_of_applied_user')

    def get_is_sponsored_job(self, obj):
        try:
            content_type = ContentType.objects.get(model='job')
            sponsored_job = Sponsored.objects.filter(object_id=obj.id, content_type=content_type.id,
                                                     status=Sponsored.SPONSORED_ACTIVE).last()

            if sponsored_job:
                if sponsored_job.start_date <= datetime.now(pytz.utc) < sponsored_job.end_date:
                    return True
                else:
                    return False
            else:
                return False
        except Sponsored.DoesNotExist as e:
            logger.debug(e)
            return False

    def get_no_of_views(self, obj):
        # number of user viewed
        view_count = ItemUserView.objects.filter(item=obj)
        return view_count.count()

    def get_no_of_applied_user(self, obj):
        return JobUserApplied.objects.filter(job=obj).count()


class CandidateSearchUserJobProfileSerializer(ModelSerializer):
    resume_url = serializers.SerializerMethodField()
    user_profile = serializers.SerializerMethodField()
    job_profile = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    user_slug = serializers.SerializerMethodField()
    user_last_work_experience = serializers.SerializerMethodField()
    user_total_experience = serializers.SerializerMethodField()
    is_job_invitation_sent = serializers.SerializerMethodField()

    class Meta:
        model = UserJobProfile
        fields = '__all__'

    def get_user_profile(self, obj):
        try:
            # message = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION')
            # details_msg = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION_DETAIL')
            # details = details_msg.format(obj.job.entity)
            # try:
            #     ICFNotificationManager.objects.get(user=obj.user, details=details)
            # except Exception:
            #     ICFNotificationManager.add_notification(user=obj.user, message=message, details=details)

            return UserProfileRetrieveSerializerForList(UserProfile.objects.get(user=obj.user)).data
        except UserProfile.DoesNotExist:
            logger.exception("User profile does not exist for {}".format(obj.user.email))
            return None

    def get_user_slug(self, obj):
        return obj.user.slug

    def get_resume_url(self, obj):
        try:
            if obj.resume:
                try:
                    user_resume = UserResume.objects.get(id=obj.resume.id)
                    if user_resume.resume:
                        return user_resume.resume.url
                    else:
                        try:
                            job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                            if job_profile_file_upload:
                                if job_profile_file_upload.resume_src:
                                    return job_profile_file_upload.resume_src.url
                                else:
                                    return None
                            else:
                                return None

                        except JobProfileFileUpload.DoesNotExist as jpfe:
                            logger.debug(str(jpfe))
                            return None
                except UserResume.DoesNotExist as urdne:
                    logger.debug(str(urdne))
                    try:
                        job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                        if job_profile_file_upload:
                            if job_profile_file_upload.resume_src:
                                return job_profile_file_upload.resume_src.url
                            else:
                                return None
                        else:
                            return None

                    except JobProfileFileUpload.DoesNotExist as jpfe:
                        logger.debug(str(jpfe))
                        return None
                except Exception as e:
                    logger.exception(str(e))
                    raise ICFException(_("Something went wrong, please contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
        except AttributeError as ae:
            # checks if user has default resume that is in JobProfileFileUpload table
            # if user did not upload default resume it returns None
            try:
                job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                if job_profile_file_upload:
                    if job_profile_file_upload.resume_src:
                        return job_profile_file_upload.resume_src.url
                    else:
                        return None
                else:
                    return None
            except JobProfileFileUpload.DoesNotExist as jpfe:
                logger.debug(str(jpfe))
                return None
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_job_profile(self, obj):
        try:
            return UserJobProfileRetrieveSerializer(UserJobProfile.objects.get(user=obj.user)).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None

    def get_education(self, obj):
        try:
            return UserEducationRetrieveSerializer(UserEducation.objects.filter(job_profile__user=obj.user),
                                                   many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for education")
            return None

    def get_experience(self, obj):
        try:
            return UserWorkExperienceListSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),
                                                    many=True).data
            # return UserWorkExperienceSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),
            #                                     many=True).data
        except ValueError as ve:
            logger.exception("Error in getting a value for experience")
            return None
        except ObjectDoesNotExist:
            return None

    def get_reference(self, obj):
        try:
            return UserReferenceSerializerForList(UserReference.objects.filter(job_profile__user=obj.user),
                                                  many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for reference")
            return None

    def get_skills(self, obj):
        try:
            return UserSkillSerializer(UserSkill.objects.filter(job_profile__user=obj.user), many=True).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for skill")
            return None

    def get_user_last_work_experience(self, obj):
        user_work_experience_last_obj = UserWorkExperience.objects.filter(job_profile=obj).last()
        if user_work_experience_last_obj:
            work_experience_serializer = UserWorkExperienceListSerializer(user_work_experience_last_obj)
            return work_experience_serializer.data
        else:
            return None

    def get_user_total_experience(self, obj):
        try:
            work_exp_qs = UserWorkExperience.objects.filter(job_profile=obj)
            user_total_work_exp_in_seconds = 0
            for exp in work_exp_qs:
                # print("exp_from: {d}".format(d=exp.worked_from))
                # print("exp_till: {till}".format(till=exp.worked_till))
                user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from, exp.worked_till)
                # print("Single work experience: ", single_exp_in_seconds)
                user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
            if user_total_work_exp_in_seconds > 0:
                user_total_work_exp_in_years = user_total_work_exp_in_seconds/60/60/24/365
                return round(user_total_work_exp_in_years, 1)
            else:
                return 0
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            # raise ICFException(_("Something went wrong. reason:{reason}").format(reason=str(e)))
            return 0

    def get_is_job_invitation_sent(self, obj):
        try:
            jobseeker_user = obj.user
            to_user_type = ContentType.objects.get_for_model(jobseeker_user)

            app_type_slug = 'job'
            app_type = Type.objects.get(slug=app_type_slug)

            icf_user_messages_list = ICFMessage.objects.filter(topic_slug=self.context.get('view').kwargs.get('slug'),
                                           recipient_type =to_user_type,
                                           recipient_id=jobseeker_user.id, app_type=app_type, sent_at__isnull=False)
            if icf_user_messages_list:
                return True
            else:
                return False
        except Exception as e:
            pass


class CandidateSearchCreateSerializer(ModelSerializer):
    location = serializers.ListField(allow_null=True)
    education_level = serializers.ListField(allow_null=True)
    key_skill = serializers.ListField(allow_null=True)
    computer_skill = serializers.ListField(allow_null=True)
    language_skill = serializers.ListField(allow_null=True)
    recruiter = serializers.SerializerMethodField(read_only=True)
    slug = serializers.CharField(read_only=True)
    entity_slug = serializers.CharField(read_only=True)

    class Meta:
        model = CandidateSearch
        fields = '__all__'

    def create(self, validated_data):
        try:
            entity_slug = self.context.get('entity_slug')
            user = self.context.get("user")
            name = self.validated_data.pop('name')
            job_title = self.validated_data.pop('job_title', None)
            work_experience = self.validated_data.get('work_experience', None)
            work_experience = self.validated_data.pop('work_experience')

            if work_experience:
                work_experience = int(work_experience)
            location_id_list = validated_data.get('location', None)
            validated_data.pop('location')
            education_level_id_list = validated_data.get('education_level', None)
            validated_data.pop('education_level')
            key_skill_id_list = validated_data.get('key_skill', None)
            validated_data.pop('key_skill')
            computer_skill_id_list = validated_data.get('computer_skill', None)
            validated_data.pop('computer_skill')
            language_skill_id_list = validated_data.get('language_skill', None)
            validated_data.pop('language_skill')

            location_id_string = ''
            if location_id_list:
                location_converted_list = [str(element) for element in location_id_list]
                location_id_string = ",".join(location_converted_list)
            # print(location_id_string)

            education_level_id_string = ''
            if education_level_id_list:
                education_converted_list = [str(element) for element in education_level_id_list]
                education_level_id_string = ",".join(education_converted_list)
            # print(education_level_id_string)

            key_skill_id_string = ''
            if key_skill_id_list:
                key_skill_converted_list = [str(element) for element in key_skill_id_list]
                key_skill_id_string = ",".join(key_skill_converted_list)
            # print(key_skill_id_string)

            computer_skill_id_string = ''
            if computer_skill_id_list:
                computer_skill_converted_list = [str(element) for element in computer_skill_id_list]
                computer_skill_id_string = ",".join(computer_skill_converted_list)
            # print(computer_skill_id_string)

            language_skill_id_string = ''
            if language_skill_id_list:
                language_skill_converted_list = [str(element) for element in language_skill_id_list]
                language_skill_id_string = ",".join(language_skill_converted_list)
            # print(language_skill_id_string)

            candidate_search_obj = CandidateSearch.objects.create(name=name, entity_slug=entity_slug, recruiter=user, location=location_id_string,
                                                                  work_experience=work_experience, education_level=education_level_id_string,
                                                                  key_skill=key_skill_id_string, computer_skill=computer_skill_id_string,
                                                                  language_skill=language_skill_id_string, job_title=job_title
                                                                  )
            return candidate_search_obj

        except ValueError as ve:
            logger.exception("Cannot cast the value to integer.")
            raise ICFException(_("Something went wrong.Please contact administrator."), status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong.Please contact administrator.", status_code=status.HTTP_400_BAD_REQUEST))

    def get_recruiter(self, obj):
        if obj.recruiter:
            return UserFirstAndLastNameSerializer(obj.recruiter).data
        else:
            return None


class CandidateSearchListSerializer(ModelSerializer):
    recruiter = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CandidateSearch
        fields = '__all__'

    def get_recruiter(self, obj):
        if obj.recruiter:
            return UserFirstAndLastNameSerializer(obj.recruiter).data
        else:
            return None


class CandidateSearchRetrieveUpdateSerializer(ModelSerializer):
    location = serializers.ListField(allow_null=True)
    education_level = serializers.ListField(allow_null=True)
    key_skill = serializers.ListField(allow_null=True)
    computer_skill = serializers.ListField(allow_null=True)
    language_skill = serializers.ListField(allow_null=True)
    recruiter = serializers.SerializerMethodField(read_only=True)
    # entity_slug = serializers.CharField(read_only=True)

    class Meta:
        model = CandidateSearch
        exclude = ['slug', 'entity_slug']

    def update(self, instance, validated_data):
        try:
            search_slug = self.context.get('view').kwargs.get('search_slug')
            user = self.context.get("request").user
            # name = self.validated_data.pop('name')
            name = instance.name
            job_title = self.validated_data.pop('job_title', None)
            # entity_slug = self.validated_data.get('entity_slug', None)
            # entity_slug = self.validated_data.pop('entity_slug')
            work_experience = self.validated_data.get('work_experience', None)
            work_experience = self.validated_data.pop('work_experience')

            if work_experience:
                work_experience = int(work_experience)
            location_id_list = validated_data.get('location', None)
            validated_data.pop('location')
            education_level_id_list = validated_data.get('education_level', None)
            validated_data.pop('education_level')
            key_skill_id_list = validated_data.get('key_skill', None)
            validated_data.pop('key_skill')
            computer_skill_id_list = validated_data.get('computer_skill', None)
            validated_data.pop('computer_skill')
            language_skill_id_list = validated_data.get('language_skill', None)
            validated_data.pop('language_skill')

            location_id_string = ''
            if location_id_list:
                location_converted_list = [str(element) for element in location_id_list]
                location_id_string = ",".join(location_converted_list)
            # print(location_id_string)

            education_level_id_string = ''
            if education_level_id_list:
                education_converted_list = [str(element) for element in education_level_id_list]
                education_level_id_string = ",".join(education_converted_list)
            # print(education_level_id_string)

            key_skill_id_string = ''
            if key_skill_id_list:
                key_skill_converted_list = [str(element) for element in key_skill_id_list]
                key_skill_id_string = ",".join(key_skill_converted_list)
            # print(key_skill_id_string)

            computer_skill_id_string = ''
            if computer_skill_id_list:
                computer_skill_converted_list = [str(element) for element in computer_skill_id_list]
                computer_skill_id_string = ",".join(computer_skill_converted_list)
            # print(computer_skill_id_string)

            language_skill_id_string = ''
            if language_skill_id_list:
                language_skill_converted_list = [str(element) for element in language_skill_id_list]
                language_skill_id_string = ",".join(language_skill_converted_list)
            # print(language_skill_id_string)

            # candidate_search_obj = CandidateSearch.objects.get(slug=search_slug)
            instance.name = name
            # instance.entity_slug = entity_slug
            instance.recruiter = user
            instance.location=location_id_string
            instance.work_experience = work_experience
            instance.education_level = education_level_id_string
            instance.key_skill = key_skill_id_string
            instance.computer_skill = computer_skill_id_string
            instance.language_skill = language_skill_id_string
            instance.job_title = job_title
            instance.save(update_fields=['name', 'recruiter', 'location',
                                                                  'work_experience','education_level',
                                                                  'key_skill', 'computer_skill',
                                                                  'language_skill', 'job_title'])
            return instance
        except CandidateSearch.DoesNotExist as e:
            logger.exception("CandidateSearch object not found.")
            raise ICFException(_("Something went wrong.Please contact administrator."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.exception("Cannot cast the value to integer.")
            raise ICFException(_("Something went wrong.Please contact administrator."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(
                _("Something went wrong.Please contact administrator.", status_code=status.HTTP_400_BAD_REQUEST))

    def get_recruiter(self, obj):
        if obj.recruiter:
            return UserFirstAndLastNameSerializer(obj.recruiter).data
        else:
            return None














