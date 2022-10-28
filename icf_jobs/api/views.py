# Create your views here.
import threading

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
# from weasyprint import HTML

from icf_auth.models import UserProfile, UserProfileImage
from icf_entity.models import Entity, MinistryMasterConfig, Industry, Sector
from icf_entity.permissions import IsEntityUser
from icf_generic.api.serializers import AddressSerializer

from icf_generic.mixins import ICFListMixin
from icf_generic.models import Sponsored, City, Address
from icf_item.models import FavoriteItem, Item
from icf_jobs.JobHelper import get_user_work_experience_in_seconds, get_intersection_of_lists
from icf_jobs.PDFGenerator import PDFGeneratorForResume
from icf_jobs.api.filters import JobFilters, StatusEntityFilter, AppliedUserStatusFilter
from icf_jobs.api.mixins import SearchCandidateListMixin
from icf_jobs.permissions import CanCreateJob, CanEditJob, CanMarkJobDelete, CanDeleteJob, \
    CanSeeJobsMarkedForDeleteList, CanRejectMarkedForDeleteJob, CanPublishJob
from icf_jobs.api.serializers import (
    JobListSerializer, EducationLevelSerializer,
    OccupationSerializer, JobCreateSerializer,
    SalaryFrequencySerializer, JobTypeSerializer,
    SkillSerializer, UserAwardRecognitionSerializer, UserConferenceWorkshopSerializer, UserCourseSerializer,
    UserEducationSerializer, UserExtraCurricularActivitiesSerializer, UserFreelanceServiceSerializer, UserInfluencerSerializer, UserInterviewQuestionSerializer, UserLicenseCertificationSerializer, UserPreferedCountrySerializer, UserPreferedFunctionalAreaSerializer, UserPreferedIndustrySerializer, UserPreferedJobStaffLevelSerializer, UserPreferedJobTypeSerializer, UserPreferedWageSerializer, UserPreferedWorkSiteTypeSerializer, UserProfessionalMembershipSerializer, UserPublicationSerializer, UserVisionMissionSerializer, UserVolunteeringSerializer, UserWorkExperienceSerializer, UserReferenceSerializer, UserSkillSerializer,
    RelationshipSerializer, FileUploadSerializer, UserJobProfileRetrieveUpdateSerializer, JobRetrieveUpdateSerializer,
    FavoriteItemSerializer, JobRetrieveSerializer, JobUserAppliedSerializer, EntityJobListSerializer,
    JobAppliedUserSerializer, JobAppliedUserStatusSerializer, DraftJobSerializer, DraftJobRetrieveSerializer,
    DraftJobListSerializer, JobCreateDraftSerializer, JobDraftListSerializer, JobDraftRetrieveUpdateSerializer,
    JobDraftRetrieveSerializer, UnregisteredUserFileUploadSerializer, UserRelevantLinkSerializer, UserHobbieSerializer,
    UserProjectSerializer, UserWorkExperienceListSerializer, UserProjectListSerializer, TaskSerializer,
    UserResumeCreateSerializer, UserResumeUpdateSerializer, UserResumeListSerializer,
    UserResumeCreateCloneSerializer, UserResumeRetrieveSerializer, TaskCreateSerializer, CountryJobListSerializer,
    CandidateSearchUserJobProfileSerializer, CandidateSearchCreateSerializer, CandidateSearchListSerializer,
    CandidateSearchRetrieveUpdateSerializer)
from icf_jobs.models import Job, EducationLevel, Occupation, SalaryFrequency, JobType, Skill, UserAwardRecognition, UserConferenceWorkshop, UserCourse, UserEducation, UserExtraCurricularActivities, UserFreelanceService, UserInfluencer, UserInterviewQuestion, UserLicenseCertification, UserPreferedCountry, UserPreferedFunctionalArea, UserPreferedIndustry, UserPreferedJobStaffLevel, UserPreferedJobType, UserPreferedWage, UserPreferedWorkSiteType, UserProfessionalMembership, UserPublication, UserVisionMission, UserVolunteering, \
    UserWorkExperience, UserReference, UserSkill, Relationship, JobProfileFileUpload, UserJobProfile, JobUserApplied, \
    JobMarkedForDelete, DraftJob, JobDraft, UnregisteredUserFileUpload, UserRelevantLink, UserHobbie, UserProject, \
    Reference, Task, UserResume, UserResumeComponent, CandidateSearchForJobMaster, CandidateSearchForJobMasterChoice, \
    JobSkill, CandidateSearch
from icf_generic.Exceptions import ICFException
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView, DestroyAPIView, \
    RetrieveUpdateDestroyAPIView, UpdateAPIView
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from icf import settings
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q, Count

import logging

from icf_jobs.util import JobNotification
from icf_messages.manager import ICFNotificationManager

logger = logging.getLogger(__name__)


class JobCreateApiView(CreateAPIView):
    queryset = Job.objects.all()
    serializer_class = JobCreateSerializer
    permission_classes = (IsAuthenticated, CanCreateJob)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        """
                Send notifications to the users matching the skills, education etc.
        """
        job_slug = serializer.data.get('slug')
        job_notification = JobNotification(slug=job_slug)
        t = threading.Thread(target=job_notification.run)
        t.start()
        # logger.info("Starting Job Notification Thread at {}".format(timezone.now(), threading.get_ident()))
        # logger.info("Returning to UI at {}".format(timezone.now(), threading.get_ident()))

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class GeneralJobListView(ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobListSerializer
    filter_class = JobFilters

    def get_queryset(self):
        queryset = Job.objects.all().filter(status=Item.ITEM_ACTIVE, start_date__lte=now(), expiry__gte=now()).order_by("-created")
        try:
            entity = self.request.query_params.get('entity', None)
            if entity:
                queryset = queryset.filter(entity__slug=entity)

            category_name = self.request.query_params.get('category', None)
            if category_name:
                queryset = queryset.filter(category__slug=category_name)

            fav_item = self.request.query_params.get('favourite', None)
            if fav_item:
                queryset = queryset.filter(fav_item__user=self.request.user)

            applied_job = self.request.query_params.get('applied', None)
            if applied_job:
                queryset = queryset.filter(jobuserapplied__user=self.request.user)

            #matched jobs based on occupation
            matched = self.request.query_params.get('matched', None)
            # location = self.request.query_params.get('location', None)
            if matched:
                user_education = UserEducation.objects.filter(job_profile__user=self.request.user).values_list('education_level')
                queryset = queryset.filter(education_level__in=list(user_education))
                try:
                    user_profile = UserProfile.objects.get(user=self.request.user)
                    queryset = queryset.filter(location__city__city=user_profile.location.city.city)
                except UserProfile.DoesNotExist as une:
                    queryset = queryset

            entity_realted_jobs = self.request.query_params.get('entity_realted_jobs',None)
            if entity_realted_jobs:
                job = Job.objects.get(slug=entity_realted_jobs)
                queryset = queryset.filter(entity=job.entity).exclude(pk=job.pk)

            location = self.request.query_params.get('location')
            if location:
                job = Job.objects.get(slug=location)
                queryset = queryset.filter(location__city__city=job.location.city.city).exclude(pk=job.pk)

            # related jobs based on education
            related = self.request.query_params.get('related',None)
            if related:
                job = Job.objects.get(slug=related)
                q1 = queryset.filter(occupation=job.occupation)
                q2 = queryset.filter(category=job.category)
                q3 = queryset.filter(experience_years=job.experience_years)
                queryset = (q1 | q2 | q3).distinct().exclude(pk=job.pk)

            return queryset

        except Exception as e:
            logger.debug(e)
            return Job.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EntityJobList(ICFListMixin, ListAPIView):
    queryset = Job.objects.all()
    serializer_class = EntityJobListSerializer
    filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(entity__slug=self.kwargs.get('slug'))
            # update the job status for the job which is
            # continues to be active even if it expired

            status = self.request.query_params.get('status', None)
            city_str = self.request.query_params.get('city', None)
            title = self.request.query_params.get('title', None)

            if status and int(status) == Item.ITEM_ACTIVE:
                queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)

            if city_str is not None:
                city_rpr = city_str.split(',')
                city = city_rpr[0].strip()  # gives the city name
                queryset = queryset.filter(location__city__city__icontains=city).order_by('created')
                # queryset = queryset.filter(entity__address__city__city__icontains=city).order_by('created')

            if title is not None:
                queryset = queryset.filter(title__icontains=title).order_by('created')

            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the job list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class EntityJobCountApiView(APIView):
    queryset = Job.objects.all()
    permission_classes = (IsAuthenticated, IsEntityUser)

    def list(self):
        try:
            queryset = self.queryset.filter(entity__slug=self.kwargs.get('entity_slug'), status=Item.ITEM_ACTIVE,
                                            start_date__lte=now(), expiry__gte=now()).order_by("-created")
            queryset_count = queryset.count()
            return Response({'active_job_count': queryset_count}, status=status.HTTP_200_OK)

        except Exception as e:
            pass


class CountryJobListAPIView(ListAPIView):
    serializer_class = CountryJobListSerializer
    queryset = Job.objects.all()

    def get_queryset(self):
        queryset = Job.objects.all().filter(status=Item.ITEM_ACTIVE, start_date__lte=now(),
                                            expiry__gte=now()).order_by("-created")
        try:
            ministry = self.kwargs.get('ministry', None)  # ministry parameter has string ministry type
            country = self.kwargs.get('country', None)  # country parameter has string country name
            industry_list = []
            sector_list = []

            if ministry and country:
                try:
                    queryset = queryset.filter(entity__address__city__state__country__country__iexact=country)
                    ministry_master_config = MinistryMasterConfig.objects.get(country__country__iexact=country,
                                                                              ministry_type__iexact=ministry)
                    industry_str = ministry_master_config.industries
                    if industry_str and industry_str != '':
                        industry_id_list = industry_str.split(',')
                        for industry_id in industry_id_list:
                            try:
                                industry_id = int(industry_id.strip())
                                industry = Industry.objects.get(id=industry_id)
                                industry_list.append(industry.industry)
                            except Industry.DoesNotExist as ie:
                                logger.exception("Industry object not exist for id:{id}".format(id=industry_id))
                                pass
                            except ValueError as ve:
                                logger.exception("Invalid parameter for industry id:{id}".format(id=industry_id))
                                raise ICFException(_("Could not get industries and sectors for "
                                                     "ministry:{ministry} and country: {country}."
                                                     "Please contact administrator.)"
                                                     .format(ministry=ministry, country=country),
                                                     status=status.HTTP_400_BAD_REQUEST))

                    sector_str = ministry_master_config.sectors
                    if sector_str and sector_str != '':
                        sector_id_list = sector_str.split(',')
                        for sector_id in sector_id_list:
                            try:
                                sector_id = int(sector_id.strip())
                                sector = Sector.objects.get(id=sector_id)
                                sector_list.append(sector.sector)
                            except Sector.DoesNotExist as se:
                                logger.exception(
                                    "Sector object not exist for id:{id}".format(id=sector_id))
                                pass
                            except ValueError as ve:
                                logger.exception("Invalid parameter for sector id:{id}".format(id=sector_id))
                                raise ICFException(_("Could not get industries and sectors for "
                                                     "ministry:{ministry} and country: {country}."
                                                     "Please contact administrator.)"
                                                     .format(ministry=ministry, country=country),
                                                     status=status.HTTP_400_BAD_REQUEST))

                    if industry_list and sector_list:
                        queryset = queryset.filter(Q(entity__industry__industry__in=industry_list) |
                                                   Q(entity__sector__sector__in=sector_list))

                    return queryset

                except MinistryMasterConfig.DoesNotExist as mde:
                    logger.exception("Could not get industries and sectors for "
                                     "ministry:{ministry} and country:{country}".format(ministry=ministry,
                                                                                        country=country))
                    raise ICFException(_("Could not get industries and sectors for "
                                         "ministry:{ministry} and country:{country}.)"
                                         .format(ministry=ministry, country=country),
                                         status=status.HTTP_400_BAD_REQUEST))

            else:
                logger.exception("Could not get industries and sectors for "
                                 "ministry:{ministry} and country:{country}".format(ministry=ministry, country=country))
                raise ICFException(_("Could not get industries and sectors for "
                                     "ministry:{ministry} and country:{country}. "
                                     "Please provide valid ministry type and country.)"
                                     .format(ministry=ministry, country=country), status=status.HTTP_400_BAD_REQUEST))

        except Exception as e:
            logger.exception("Could not get jobs reason:{reason}.\n".format(reason=str(e)))
            raise ICFException(_("You have already provided your work status."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class JobUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = Job.objects.all()
    serializer_class = JobRetrieveUpdateSerializer

    permission_classes = (IsAuthenticated, CanEditJob)

    lookup_field = "slug"

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if job is sponsored
        try:
            sp_obj = Sponsored.objects.get(object_id=instance.id,status=Sponsored.SPONSORED_ACTIVE)
            instance.sponsored_start_dt = sp_obj.start_date
            instance.sponsored_end_dt = sp_obj.end_date
            instance.is_sponsored = True
            serializer = self.get_serializer(instance)
        except Exception as e:
            serializer = self.get_serializer(instance)

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class JobDetailView(RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobRetrieveSerializer
    lookup_field = "slug"


class EducationLevelList(ListAPIView):
    serializer_class = EducationLevelSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = EducationLevel.objects.all().order_by('id')

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(level__istartswith=qp)
        return queryset


class OccupationList(ListAPIView):
    serializer_class = OccupationSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Occupation.objects.all().order_by('id')

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(name__istartswith=qp)
        return queryset


class SalaryFrequencyList(ListAPIView):
    serializer_class = SalaryFrequencySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = SalaryFrequency.objects.all().order_by('id')

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(frequency__istartswith=qp)
        return queryset


class JobTypeList(ListAPIView):
    serializer_class = JobTypeSerializer
    queryset = JobType.objects.all().order_by('id')
    pagination_class = None


class SkillList(ListAPIView):
    serializer_class = SkillSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Skill.objects.all().order_by('id')

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(skill_type__iexact=qp)
        return queryset


class UserEducationViewSet(viewsets.ModelViewSet):
    serializer_class = UserEducationSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserEducation.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserEducationSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserEducation.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserEducation.objects.filter(job_profile__user=user)
        serializer = UserEducationSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserEducationSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Education , create UserJobProfile before creating UserEducation")
            return Response({"detail": "Cannot add User Education , create UserJobProfile before creating UserEducation"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserEducation.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserEducation.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "User Education object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserEducation.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Education")
            return Response({"detail": "Cannot update User Education"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Education")
            return Response({"detail": "Cannot  update User Education"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Education got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Education not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


class UserWorkExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = UserWorkExperienceSerializer
    list_serializer_class = UserWorkExperienceListSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserWorkExperience.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserWorkExperienceSerializer(*args, **kwargs)

    def get_object(self):
        try:
            user_work_experience = UserWorkExperience.objects.\
                                    get(job_profile__user=self.request.user,
                                        pk=self.kwargs.get('pk'))
            return user_work_experience
        except UserWorkExperience.DoesNotExist as e:
            logger.info(str(e))
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserWorkExperience.objects.filter(job_profile__user=user)
        serializer = UserWorkExperienceListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserWorkExperienceSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserWorkExperience, "
                         "create UserJobProfile before adding UserWorkExperience")
            return Response({"detail": "Cannot add UserWorkExperience,"
                                       "create UserJobProfile before adding "
                                       "UserWorkExperience"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserWorkExperience.objects.get(job_profile__user=request.user, pk=pk)
            try:

                task_serializer_list = []
                task_list = Task.objects.filter(user=self.request.user, work_experience=obj)
                for task in task_list:
                    task_serializer = TaskSerializer(task)
                    task_serializer_list.append(task_serializer.data)
                obj.task_list = task_serializer_list
                content_type_obj = ContentType.objects.get_for_model(obj)
                reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
                obj.reference_name = reference.name
                obj.reference_position = reference.position
                obj.reference_email = reference.email
                obj.reference_phone = reference.phone

            except ContentType.DoesNotExist as ctne:
                logger.exception("Could not retrieve UserWorkExperience. ContentType does not exist. reason :{}".format(str(ctne)))
                raise ICFException(_("Could not retrieve UserWorkExperience."), status_code=status.HTTP_400_BAD_REQUEST)
            except Reference.DoesNotExist as re:
                pass
            serializer = UserWorkExperienceListSerializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserWorkExperience.DoesNotExist:
            logger.debug("UserWorkExperience object not found")
            return Response({"detail": "UserWorkExperience object not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        context = {'user': self.request.user}
        try:
            instance = UserWorkExperience.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update UserWorkExperience")
            return Response({"detail": "Cannot update UserWorkExperience"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({"detail": "Cannot add UserWorkExperience, "
                                       "create UserJobProfile before adding UserWorkExperience"},
                            status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserWorkExperience got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            logger.debug("UserWorkExperience not found, cannot delete")
            return Response({'detail': "UserWorkExperience not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


class UserConferenceWorkshopViewSet(viewsets.ModelViewSet):
    serializer_class = UserConferenceWorkshopSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserConferenceWorkshop.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserConferenceWorkshopSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserConferenceWorkshop.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserConferenceWorkshop.objects.filter(job_profile__user=user)
        serializer = UserConferenceWorkshopSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserConferenceWorkshopSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Conference & Workshop , create UserJobProfile before creating UserConferenceWorkshop")
            return Response({"detail": "Cannot add User Conference & Workshop , create UserJobProfile before creating UserConferenceWorkshop"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserConferenceWorkshop.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserConferenceWorkshop.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserConferenceWorkshop object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserConferenceWorkshop.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Conference-Workshop")
            return Response({"detail": "Cannot update User Conference-Workshop"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Conference-Workshop")
            return Response({"detail": "Cannot  update User Conference-Workshop"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Conference-Workshop got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Conference-Workshop not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for For Licenses and Certifications obtained by the jobe seeker
class UserLicenseCertificationViewSet(viewsets.ModelViewSet):
    serializer_class = UserLicenseCertificationSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserLicenseCertification.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserLicenseCertificationSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserLicenseCertification.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserLicenseCertification.objects.filter(job_profile__user=user)
        serializer = UserLicenseCertificationSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserLicenseCertificationSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User License & Certification , create UserJobProfile before creating UserLicenseCertification")
            return Response({"detail": "Cannot add User License & Certification , create UserJobProfile before creating UserLicenseCertification"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserLicenseCertification.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserLicenseCertification.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserLicenseCertification object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserLicenseCertification.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User License-Certification")
            return Response({"detail": "Cannot update User License-Certification"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User License-Certification")
            return Response({"detail": "Cannot  update User License-Certification"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User License-Certification got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User License-Certification not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


#  View for For Course completed by the jobe seeker
class UserCourseViewSet(viewsets.ModelViewSet):
    serializer_class = UserCourseSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserCourse.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserCourseSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserCourse.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserCourse.objects.filter(job_profile__user=user)
        serializer = UserCourseSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserCourseSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Courses , create UserJobProfile before creating UserCourse")
            return Response({"detail": "Cannot add User Courses , create UserJobProfile before creating UserCourse"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserCourse.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserCourse.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserCourse object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserCourse.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Courses")
            return Response({"detail": "Cannot update User Courses"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Courses")
            return Response({"detail": "Cannot  update User Courses"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Courses got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Courses not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for For Freelance Service completed by the jobe seeker
class UserFreelanceServiceViewSet(viewsets.ModelViewSet):
    serializer_class = UserFreelanceServiceSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserFreelanceService.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserFreelanceServiceSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserFreelanceService.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserFreelanceService.objects.filter(job_profile__user=user)
        serializer = UserFreelanceServiceSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserFreelanceServiceSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Freelance Service , create UserJobProfile before creating UserFreelanceService")
            return Response({"detail": "Cannot add User Freelance Service , create UserJobProfile before creating UserFreelanceService"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserFreelanceService.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserFreelanceService.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserFreelanceService object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserFreelanceService.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Freelance Service")
            return Response({"detail": "Cannot update User Freelance Service"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Freelance Service")
            return Response({"detail": "Cannot  update User Freelance Service"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Freelance Service got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Freelance Service not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


#  View for For Award & Recognition completed by the jobe seeker
class UserAwardRecognitionViewSet(viewsets.ModelViewSet):
    serializer_class = UserAwardRecognitionSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserAwardRecognition.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserAwardRecognitionSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserAwardRecognition.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserAwardRecognition.objects.filter(job_profile__user=user)
        serializer = UserAwardRecognitionSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserAwardRecognitionSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Award & Recognition , create UserJobProfile before creating UserAwardRecognition")
            return Response({"detail": "Cannot add User Award & Recognition , create UserJobProfile before creating UserAwardRecognition"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserAwardRecognition.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserAwardRecognition.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserAwardRecognition object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserAwardRecognition.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Award & Recognition")
            return Response({"detail": "Cannot update User Award & Recognition"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Award & Recognition")
            return Response({"detail": "Cannot  update User Award & Recognition"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Award & Recognition got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Award & Recognition not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for For Interview Question completed by the jobe seeker
class UserInterviewQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = UserInterviewQuestionSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserInterviewQuestion.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserInterviewQuestionSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserInterviewQuestion.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserInterviewQuestion.objects.filter(job_profile__user=user)
        serializer = UserInterviewQuestionSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserInterviewQuestionSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Interview Question , create UserJobProfile before creating UserInterviewQuestion")
            return Response({"detail": "Cannot add User Interview Question , create UserJobProfile before creating UserInterviewQuestion"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserInterviewQuestion.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserInterviewQuestion.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserInterviewQuestion object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserInterviewQuestion.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Interview Question")
            return Response({"detail": "Cannot update User Interview Question"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Interview Question")
            return Response({"detail": "Cannot  update User Interview Question"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Interview Question got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Interview Question not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


#  View for For Professional Membership of the jobe seeker
class UserProfessionalMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfessionalMembershipSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserProfessionalMembership.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserProfessionalMembershipSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserProfessionalMembership.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserProfessionalMembership.objects.filter(job_profile__user=user)
        serializer = UserProfessionalMembershipSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserProfessionalMembershipSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Professional Membershipn , create UserJobProfile before creating UserProfessionalMembership")
            return Response({"detail": "Cannot add User Professional Membershipn , create UserJobProfile before creating UserProfessionalMembership"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserProfessionalMembership.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfessionalMembership.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserProfessionalMembership object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserProfessionalMembership.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Professional Membershipn")
            return Response({"detail": "Cannot update User Professional Membershipn"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Professional Membershipn")
            return Response({"detail": "Cannot  update User Professional Membershipn"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Professional Membershipn got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Professional Membershipn not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for Volunteering work of the jobe seeker
class UserVolunteeringViewSet(viewsets.ModelViewSet):
    serializer_class = UserVolunteeringSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserVolunteering.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserVolunteeringSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserVolunteering.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserVolunteering.objects.filter(job_profile__user=user)
        serializer = UserVolunteeringSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserVolunteeringSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Volunteering , create UserJobProfile before creating UserVolunteering")
            return Response({"detail": "Cannot add User Volunteering , create UserJobProfile before creating UserVolunteering"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserVolunteering.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserVolunteering.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserVolunteering object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserVolunteering.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Volunteering")
            return Response({"detail": "Cannot update User Volunteering"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Volunteering")
            return Response({"detail": "Cannot  update User Volunteering"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Volunteering got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Volunteering not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for Vision and Mission of the jobe seeker
class UserVisionMissionViewSet(viewsets.ModelViewSet):
    serializer_class = UserVisionMissionSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserVisionMission.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserVisionMissionSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserVisionMission.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserVisionMission.objects.filter(job_profile__user=user)
        serializer = UserVisionMissionSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserVisionMissionSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Vision&Mission , create UserJobProfile before creating UserVisionMission")
            return Response({"detail": "Cannot add User Vision&Mission , create UserJobProfile before creating UserVisionMission"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserVisionMission.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserVisionMission.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserVisionMission object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserVisionMission.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Vision&Mission")
            return Response({"detail": "Cannot update User Vision&Mission"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Vision&Mission")
            return Response({"detail": "Cannot  update User Vision&Mission"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Vision&Mission got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Vision&Mission not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for Vision and Mission of the jobe seeker
class UserRelevantLinkViewSet(viewsets.ModelViewSet):
    serializer_class = UserRelevantLinkSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserRelevantLink.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserRelevantLinkSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserRelevantLink.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserRelevantLink.objects.filter(job_profile__user=user)
        serializer = UserRelevantLinkSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserRelevantLinkSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User RelevantLink , create UserJobProfile before creating UserRelevantLink")
            return Response({"detail": "Cannot add User RelevantLink , create UserJobProfile before creating UserRelevantLink"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserRelevantLink.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserRelevantLink.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserRelevantLink object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserRelevantLink.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User RelevantLink")
            return Response({"detail": "Cannot update User RelevantLink"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User RelevantLink")
            return Response({"detail": "Cannot  update User RelevantLink"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User RelevantLink got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User RelevantLink not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for influencer of the jobe seeker
class UserInfluencerViewSet(viewsets.ModelViewSet):
    serializer_class = UserInfluencerSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserInfluencer.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserInfluencerSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserInfluencer.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserInfluencer.objects.filter(job_profile__user=user)
        serializer = UserInfluencerSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserInfluencerSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Influencer , create UserJobProfile before creating UserInfluencer")
            return Response({"detail": "Cannot add User Influencer , create UserJobProfile before creating UserInfluencer"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserInfluencer.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserInfluencer.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserInfluencer object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserInfluencer.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Influencer")
            return Response({"detail": "Cannot update User Influencer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Influencer")
            return Response({"detail": "Cannot  update User Influencer"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Influencer got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Influencer not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for influencer of the jobe seeker
class UserPublicationViewSet(viewsets.ModelViewSet):
    serializer_class = UserPublicationSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPublication.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPublicationSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPublication.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPublication.objects.filter(job_profile__user=user)
        serializer = UserPublicationSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPublicationSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Publication , create UserJobProfile before creating UserPublication")
            return Response({"detail": "Cannot add User Publication , create UserJobProfile before creating UserPublication"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserPublication.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserPublication.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "UserPublication object not found"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserPublication.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Publication")
            return Response({"detail": "Cannot update User Publication"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Publication")
            return Response({"detail": "Cannot  update User Publication"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Publication got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("User Education not found, cannot delete")
            return Response({'detail': "User Publication not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for UserPreferedJobType
class UserPreferedJobTypeViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedJobTypeSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedJobType.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedJobTypeSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedJobType.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedJobType.objects.filter(job_profile__user=user)
        serializer = UserPreferedJobTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedJobTypeSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedJobType , create UserJobProfile before creating UserPreferedJobType")
            return Response({"detail": "Cannot add UserPreferedJobType , create UserJobProfile before creating UserPreferedJobType"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedJobType got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedJobType not found, cannot delete")
            return Response({'detail': "UserPreferedJobType not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for UserPreferedJobStaffLevel
class UserPreferedJobStaffLevelViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedJobStaffLevelSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedJobStaffLevel.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedJobStaffLevelSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedJobStaffLevel.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedJobStaffLevel.objects.filter(job_profile__user=user)
        serializer = UserPreferedJobStaffLevelSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedJobStaffLevelSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedJobStaffLevel , create UserJobProfile before creating UserPreferedJobStaffLevel")
            return Response({"detail": "Cannot add UserPreferedJobStaffLevel , create UserJobProfile before creating UserPreferedJobStaffLevel"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedJobStaffLevel got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedJobStaffLevel not found, cannot delete")
            return Response({'detail': "UserPreferedJobStaffLevel not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for UserPreferedIndustry
class UserPreferedIndustryViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedIndustrySerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedIndustry.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedIndustrySerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedIndustry.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedIndustry.objects.filter(job_profile__user=user)
        serializer = UserPreferedIndustrySerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedIndustrySerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedIndustry , create UserJobProfile before creating UserPreferedIndustry")
            return Response({"detail": "Cannot add UserPreferedIndustry , create UserJobProfile before creating UserPreferedIndustry"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedIndustry got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedIndustry not found, cannot delete")
            return Response({'detail': "UserPreferedIndustry not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for UserPreferedFunctionalArea
class UserPreferedFunctionalAreaViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedFunctionalAreaSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedFunctionalArea.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedFunctionalAreaSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedFunctionalArea.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedFunctionalArea.objects.filter(job_profile__user=user)
        serializer = UserPreferedFunctionalAreaSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedFunctionalAreaSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedFunctionalArea , create UserJobProfile before creating UserPreferedFunctionalArea")
            return Response({"detail": "Cannot add UserPreferedFunctionalArea , create UserJobProfile before creating UserPreferedFunctionalArea"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedFunctionalArea got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedFunctionalArea not found, cannot delete")
            return Response({'detail': "UserPreferedFunctionalArea not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for UserPreferedWorkSiteType
class UserPreferedWorkSiteTypeViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedWorkSiteTypeSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedWorkSiteType.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedWorkSiteTypeSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedWorkSiteType.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedWorkSiteType.objects.filter(job_profile__user=user)
        serializer = UserPreferedWorkSiteTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedWorkSiteTypeSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedWorkSiteType , create UserJobProfile before creating UserPreferedWorkSiteType")
            return Response({"detail": "Cannot add UserPreferedWorkSiteType , create UserJobProfile before creating UserPreferedWorkSiteType"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedWorkSiteType got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedWorkSiteType not found, cannot delete")
            return Response({'detail': "UserPreferedWorkSiteType not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

#  View for UserPreferedCountry
class UserPreferedCountryViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedCountrySerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedCountry.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedCountrySerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedCountry.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedCountry.objects.filter(job_profile__user=user)
        serializer = UserPreferedCountrySerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedCountrySerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedCountry , create UserJobProfile before creating UserPreferedCountry")
            return Response({"detail": "Cannot add UserPreferedCountry , create UserJobProfile before creating UserPreferedCountry"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedCountry got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedCountry not found, cannot delete")
            return Response({'detail': "UserPreferedCountry not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


#  View for UserPreferedWage
class UserPreferedWageViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferedWageSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserPreferedWage.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserPreferedWageSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserPreferedWage.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserPreferedWage.objects.filter(job_profile__user=user)
        serializer = UserPreferedWageSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserPreferedWageSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserPreferedWage , create UserJobProfile before creating UserPreferedWage")
            return Response({"detail": "Cannot add UserPreferedWage , create UserJobProfile before creating UserPreferedWage"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "UserPreferedWage got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("UserPreferedWage not found, cannot delete")
            return Response({'detail': "UserPreferedWage not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)




class UserReferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserReferenceSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserReference.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserReferenceSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserReference.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserReference.objects.filter(job_profile__user=user)
        serializer = UserReferenceSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserReferenceSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Reference, create UserJobProfile before adding UserReference")
            return Response({"detail": "Cannot add User Reference, create UserJobProfile before adding UserReference"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserReference.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserReference.DoesNotExist:
            logger.debug("User Reference object not found")
            return Response({"detail": "User Reference object not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserReference.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Reference")
            return Response({"detail": "Cannot update User Reference"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot  update User Reference")
            return Response({"detail": "Cannot  update User Reference"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Reference got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            logger.debug("User Reference not found, cannot delete")
            return Response({'detail': "User Reference not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


class UserSkillsViewSet(viewsets.ModelViewSet):
    serializer_class = UserSkillSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserSkill.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserSkillSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserSkill.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserSkill.objects.filter(job_profile__user=user)
        serializer = UserSkillSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        skill_id = int(self.request.data.get("skill"))

        serializer = UserSkillSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            user_skill = UserSkill.objects.get(job_profile__user=self.request.user, skill=skill_id)
            if user_skill:
                return Response({"detail": _("Skill already exist")}, status=status.HTTP_400_BAD_REQUEST)
        except UserSkill.DoesNotExist as e:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except UserJobProfile.DoesNotExist as e:
            logger.debug("Cannot add User Skill, create UserJobProfile before adding UserSkill")
            return Response({"detail": "Cannot add User Skill, create UserJobProfile before adding UserSkill"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserSkill.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserSkill.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "User Skill object not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserSkill.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot update User Skill"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot  update User Skill"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Skill got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({'detail': "User skill not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


class RelationShipList(ListAPIView):
    queryset = Relationship.objects.all()
    serializer_class = RelationshipSerializer
    permission_classes = (IsAuthenticated,)


class UserRelevantLinksViewSet(ModelViewSet):
    serializer_class = UserRelevantLinkSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserRelevantLink.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserRelevantLinkSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserRelevantLink.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserRelevantLink.objects.filter(job_profile__user=user)
        serializer = UserRelevantLinkSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserRelevantLinkSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add user relevant link, create User relevant link before adding UserRelevantLink")
            return Response({"detail": "Cannot add UserRelevantLink, create UserJobProfile before adding UserRelevantLink"},
                            status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserRelevantLink.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserRelevantLink.DoesNotExist:
            logger.debug("User Relevant Link object not found")
            return Response({"detail": "User Relevant Link object not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserRelevantLink.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Relevant Link")
            return Response({"detail": "Cannot update User Relevant Link"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Relevant Link")
            return Response({"detail": "Cannot  update User Relevant Link"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Relevant Link got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            logger.debug("User Relevant Link not found, cannot delete")
            return Response({'detail': "User Relevant Link not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)

# Viewset for the User extra curricular activities
class UserExtraCurricularActivitiesViewSet(ModelViewSet):
    serializer_class = UserExtraCurricularActivitiesSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserExtraCurricularActivities.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserExtraCurricularActivitiesSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserExtraCurricularActivities.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        try:
            user = request.user
            user_job_profile = UserJobProfile.objects.get(user=user)
            queryset = UserExtraCurricularActivities.objects.filter(job_profile=user_job_profile)
            serializer = UserExtraCurricularActivitiesSerializer(queryset, many=True)
            return Response(serializer.data)
        except UserJobProfile.ObjectDoesNotExist as jdne:
            logger.info("User does not have job profile. Create UserJobProfile\n")
            raise ICFException(_("User does not have job profile. Create UserJobProfile."), status_code=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserExtraCurricularActivitiesSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserExtraCurricularActivities, create UserJobProfile before adding UserExtraCurricularActivities")
            return Response(
                {"detail": "Cannot add UserExtraCurricularActivities, create UserJobProfile before adding UserExtraCurricularActivities"},
                status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserExtraCurricularActivities.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserRelevantLink.DoesNotExist:
            logger.debug("UserExtraCurricularActivities object not found")
            return Response({"detail": "User Activity object not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserExtraCurricularActivities.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Extra Curricular Activity.")
            return Response({"detail": "Cannot update User Extra Curricular Activity."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Extra Curricular Activity.")
            return Response({"detail": "Cannot  update User Extra Curricular Activity."}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Extra Curricular Activity got deleted successfully."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            logger.debug("User Extra Curricular Activity not found, cannot delete.")
            return Response({'detail': "User Extra Curricular Activity not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)


class UserHobbiesViewSet(ModelViewSet):
    serializer_class = UserHobbieSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserHobbie.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserHobbieSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return UserHobbie.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        try:
            user = request.user
            user_job_profile = UserJobProfile.objects.get(user=user)
            queryset = UserHobbie.objects.filter(job_profile=user_job_profile)
            serializer = UserHobbieSerializer(queryset, many=True)
            return Response(serializer.data)
        except UserJobProfile.ObjectDoesNotExist as jdne:
            logger.info("User does not have job profile. Create UserJobProfile\n")
            raise ICFException(_("User does not have job profile. Create UserJobProfile."), status_code=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserHobbieSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add UserHobbie, create UserJobProfile before adding UserHobbie")
            return Response(
                {"detail": "Cannot add UserHobbie, create UserJobProfile before adding UserHobbie"},
                status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserHobbie.objects.get(job_profile__user=request.user, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserRelevantLink.DoesNotExist:
            logger.debug("UserHobbie object not found")
            return Response({"detail": "User Hobbie object not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            instance = UserHobbie.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Hobbie.")
            return Response({"detail": "Cannot update User Hobbie."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Hobbie.")
            return Response({"detail": "Cannot  update User Hobbie."}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Hobbie got deleted successfully."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            logger.debug("User Hobbie not found, cannot delete.")
            return Response({'detail': "User Hobbie not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)

# -----------------------------------


# class UserProjectsViewSet(ModelViewSet):
#     serializer_class = UserProjectSerializer
#     permission_classes = (IsAuthenticated,)
#     queryset = UserHobbie.objects.all()
#
#     def get_serializer(self, *args, **kwargs):
#         return UserProjectSerializer(*args, **kwargs)
#
#     def get_object(self):
#         try:
#             return UserProject.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
#         except ObjectDoesNotExist as e:
#             logger.debug(e)
#             raise
#
#     def list(self, request, *args, **kwargs):
#         try:
#             user = request.user
#             user_job_profile = UserJobProfile.objects.get(user=user)
#             queryset = UserProject.objects.filter(job_profile=user_job_profile)
#             serializer = UserProjectSerializer(queryset, many=True)
#             return Response(serializer.data)
#         except UserJobProfile.ObjectDoesNotExist as jdne:
#             logger.info("User does not have job profile. Create UserJobProfile\n")
#             raise ICFException(_("User does not have job profile. Create UserJobProfile."),
#                                status_code=status.HTTP_400_BAD_REQUEST)
#
#     def create(self, request, *args, user=None, **kwargs):
#         context = {'user': self.request.user}
#         serializer = UserProjectSerializer(data=request.data, context=context)
#         serializer.is_valid(raise_exception=True)
#         try:
#             self.perform_create(serializer)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         except ObjectDoesNotExist as e:
#             logger.debug("Cannot add Project, create UserJobProfile before adding Project")
#             return Response(
#                 {"detail": "Cannot add Project, create UserJobProfile before adding Project"},
#                 status=status.HTTP_400_BAD_REQUEST)
#
#     def retrieve(self, request, pk=None, *args, **kwargs):
#         try:
#             obj = UserProject.objects.get(job_profile__user=request.user, pk=pk)
#             serializer = self.get_serializer(obj)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except UserProject.DoesNotExist:
#             logger.debug("Project object not found")
#             return Response({"detail": "Project object not found"},
#                             status=status.HTTP_400_BAD_REQUEST)
#
#     def update(self, request, pk=None, *args, **kwargs):
#         try:
#             instance = UserProject.objects.get(job_profile__user=self.request.user, pk=pk)
#             serializer = self.get_serializer(instance, data=request.data)
#             serializer.is_valid(raise_exception=True)
#         except ObjectDoesNotExist as e:
#             logger.debug("Cannot update Project.")
#             return Response({"detail": "Cannot update Project."}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             self.perform_update(serializer)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except ObjectDoesNotExist as e:
#             logger.debug("Cannot update Project.")
#             return Response({"detail": "Cannot update Project."}, status=status.HTTP_400_BAD_REQUEST)
#
#     def destroy(self, request, *args, pk=None, **kwargs):
#         try:
#             instance = self.get_object()
#             self.perform_destroy(instance)
#             return Response({"detail": "Project got deleted successfully."}, status=status.HTTP_200_OK)
#         except ObjectDoesNotExist:
#             logger.debug("Project not found, cannot delete.")
#             return Response({'detail': "Project not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)

# ---------------------------------------------------------------------------------------

class UserProjectsViewSet(ModelViewSet):
    serializer_class = UserProjectSerializer
    list_serializer_class = UserProjectListSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserProject.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UserProjectSerializer(*args, **kwargs)

    def get_object(self):
        try:
            user_project = UserProject.objects.get(job_profile__user=self.request.user, pk=self.kwargs.get('pk'))
            return user_project
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserProject.objects.filter(job_profile__user=user)
        serializer = UserProjectListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserProjectSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot add User Project, create UserJobProfile before adding User Project.")
            return Response({"detail": "Cannot add User Project, "
                                       "create UserJobProfile before adding User Project."},
                            status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = UserProject.objects.get(job_profile__user=request.user, pk=pk)
            try:
                content_type_obj = ContentType.objects.get_for_model(obj)
                reference = Reference.objects.get(object_id=obj.id, content_type=content_type_obj)
                obj.reference_name = reference.name
                obj.reference_position = reference.position
                obj.reference_email = reference.email
                obj.reference_phone = reference.phone
            except ContentType.DoesNotExist as ctne:
                logger.exception("Could not retrieve User Project. ContentType does not exist. reason :{}".format(str(ctne)))
                raise ICFException(_("Could not retrieve User Project."), status_code=status.HTTP_400_BAD_REQUEST)
            except Reference.DoesNotExist as re:
                pass
            serializer = UserProjectListSerializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProject.DoesNotExist:
            logger.debug("User Project object not found.")
            return Response({"detail": "User Project object not found."},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        context = {'user': self.request.user}
        try:
            instance = UserProject.objects.get(job_profile__user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot update User Project.")
            return Response({"detail": "Cannot update User Project"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({"detail": "Cannot add User Project, "
                                       "create UserJobProfile before adding User Project."}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "User Project got deleted successfully."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            logger.debug("User Project not found, cannot delete")
            return Response({'detail': "User Project not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)


class DeleteTaskView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Task.objects.all()

    def destroy(self, request, *args, work_exp_id=None, task_id=None, **kwargs):
        try:
            user_work_experience = UserWorkExperience.objects.get(id=work_exp_id, job_profile__user=request.user)
            instance = Task.objects.get(id=task_id, work_experience=user_work_experience)
            self.perform_destroy(instance)
            return Response({"detail": "Task got deleted successfully."}, status=status.HTTP_200_OK)

        except UserWorkExperience.DoesNotExist as wdne:
            logger.debug("User Work Experience not found, cannot delete")
            return Response({'detail': "User Work Experience not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)

        except Task.DoesNotExist as tne:
            logger.debug("Task not found, cannot delete")
            return Response({'detail': "Task not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)


class FileUploadViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser, FileUploadParser)
    serializer_class = FileUploadSerializer
    permission_classes = (IsAuthenticated,)
    queryset = JobProfileFileUpload.objects.all()

    def get_serializer(self, *args, **kwargs):
        return FileUploadSerializer(*args, **kwargs)

    def get_object(self, queryset=None):
        instance = JobProfileFileUpload.objects.filter(pk=self.kwargs['pk']).first()
        return instance

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = FileUploadSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot add job profile files"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        obj = JobProfileFileUpload.objects.filter(user=self.request.user, pk=pk)
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None, *args, **kwargs):
        context = {'user': self.request.user}
        try:
            instance = JobProfileFileUpload.objects.get(user=self.request.user, pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot update profile file upload"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot update profile file upload"}, status=status.HTTP_400_BAD_REQUEST)


class JobSeekerProfileAPIView(RetrieveUpdateAPIView):
    queryset = UserJobProfile.objects.all()
    serializer_class = UserJobProfileRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        user = self.request.user
        try:
            profile = UserJobProfile.objects.get(user=user)
        except UserJobProfile.DoesNotExist:
            profile = UserJobProfile.objects.create(user=user)
        return profile

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FavoriteJobCreate(CreateAPIView):
    queryset = FavoriteItem.objects.all()
    serializer_class = FavoriteItemSerializer
    permission_classes = (IsAuthenticated,)


class FavoriteJobDelete(RetrieveAPIView,DestroyAPIView):
    queryset = FavoriteItem.objects.all()
    serializer_class = FavoriteItemSerializer
    lookup_field = "id"
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        if self.request.user:
            return FavoriteItem.objects.get(item = self.kwargs.get('id'),user=self.request.user)
        else:
            return FavoriteItem.objects.none()


class JobApplyCreateView(CreateAPIView):
    queryset = JobUserApplied
    serializer_class = JobUserAppliedSerializer
    permission_classes = (IsAuthenticated,)


class CheckUserHasJobProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kw):
        try:
            jobseeker_profile = UserJobProfile.objects.get(user=self.request.user)
            jobseeker_education_list = UserEducation.objects.filter(job_profile=jobseeker_profile)
            if not jobseeker_education_list:
                return Response({"exists": False}, status=status.HTTP_200_OK)
            else:
                return Response({"exists": True}, status=status.HTTP_200_OK)
        except UserJobProfile.DoesNotExist:
            return Response({"exists": False}, status=status.HTTP_200_OK)


class JobAppliedUserList(ICFListMixin, ListAPIView):
    queryset = JobUserApplied.objects.all()
    serializer_class = JobAppliedUserSerializer
    # permission_classes = (IsAuthenticated, IsEntityAdmin)
    permission_classes = (IsAuthenticated,)
    filter_class = AppliedUserStatusFilter

    def get_queryset(self):
        queryset = self.queryset
        return queryset.filter(job__slug=self.kwargs.get('slug'))


class JobAppliedUserStatus(UpdateAPIView):
    queryset = JobUserApplied.objects.all()
    serializer_class = JobAppliedUserStatusSerializer
    # permission_classes = (IsAuthenticated, IsEntityAdmin)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        try:
            job_user_applied_queryset = JobUserApplied.objects.filter(job__slug=self.kwargs.get('job_slug'),
                                                                      user__slug=self.kwargs.get('user_slug'))
            if job_user_applied_queryset:
                return job_user_applied_queryset.last()
            else:
                logger.debug("Not able to change the status of applicant")
                raise ICFException("Not able to change the status of applicant")
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise ICFException("Not able to change the status of applicant")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        message = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_STATUS_NOTIFICATION')
        details = "your job profile status has been changed by an entity {} ".format(instance.job.entity)
        ICFNotificationManager.add_notification(user=instance.user, message=message, details=details)

        return Response(serializer.data)


class JobMarkForDeleteCreateView(APIView):
    queryset = Job.objects.all()
    permission_classes = (IsAuthenticated, CanMarkJobDelete)
    lookup_field = "slug"

    def post(self, request, *args, **kwargs):
        user = self.request.user
        job_slug = kwargs.get('slug')
        if job_slug is not None:
            try:
                job = Job.objects.get(slug=job_slug)
                if job.status is not Job.ITEM_ACTIVE:
                    return Response({'detail': 'Job is not active ,cannot mark the job for delete '}, status=status.HTTP_403_FORBIDDEN)

            except Job.DoesNotExist as jdn:
                logger.debug(jdn)
                return Response({'detail': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
            try:
                job_marked_for_delete = JobMarkedForDelete.objects.get(job=job)
                if job_marked_for_delete.approval_status == JobMarkedForDelete.REJECTED:
                    job_marked_for_delete.approval_status = JobMarkedForDelete.NEW
                    job_marked_for_delete.user = user
                    job_marked_for_delete.save(update_fields=['approval_status', 'user'])
                    return Response({'detail': 'Job marked for delete'}, status=status.HTTP_201_CREATED)
                elif job_marked_for_delete.approval_status == JobMarkedForDelete.NEW:
                    return Response({'detail':'Job has already been marked for delete'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'Job cannot be marked for delete because job has been Deleted'},status=status.HTTP_400_BAD_REQUEST)

            except ObjectDoesNotExist:
                JobMarkedForDelete.objects.create(user=user, job=job)
                return Response({'detail': 'Job marked for delete'}, status=status.HTTP_201_CREATED)
        else:
            return Response("bad Request", status=status.HTTP_400_BAD_REQUEST)


class JobDeleteView(DestroyAPIView):
    queryset = Job.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated, CanDeleteJob)
    lookup_field = "slug"

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({'detail': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        if instance.status == Job.ITEM_DRAFT:
            self.perform_destroy(instance)
            return Response({'detail': 'Draft job has been deleted permanently'}, status=status.HTTP_200_OK)

        elif instance.status == Job.ITEM_ACTIVE:
            try:
                job_marked_for_delete = JobMarkedForDelete.objects.get(job=instance)

                if job_marked_for_delete.approval_status is not JobMarkedForDelete.NEW:
                    return Response({'detail': 'Job cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)

                # Delete the job if JobMarkedForDelete is NEW
                instance.status = Job.ITEM_DELETED
                instance.save(update_fields=['status'])

                # Delete the job if JobMarkedForDelete is NEW
                job_marked_for_delete.approval_status = JobMarkedForDelete.DELETED
                job_marked_for_delete.save(update_fields=['approval_status'])
                return Response({'detail': 'Job has been deleted'}, status=status.HTTP_200_OK)
            except JobMarkedForDelete.DoesNotExist as jmdn:
                logger.debug(jmdn)
                return Response({'detail': 'Job cannot be deleted,because Job is Not Marked for Delete'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:

            if instance.status == Job.ITEM_DELETED:
                return Response({'detail': 'Job has been already deleted'}, status=status.HTTP_400_BAD_REQUEST)
            instance.status = Job.ITEM_DELETED
            instance.save(update_fields=['status'])
            return Response({'detail': 'Job has been deleted'}, status=status.HTTP_200_OK)


class JobMarkedForDeleteListView(ListAPIView):
    permission_classes = (IsAuthenticated, CanSeeJobsMarkedForDeleteList)
    queryset = Job.objects.all()
    serializer_class = JobListSerializer

    def list(self, request, *args, **kwargs):
        jobs_list = []
        job_marked_for_delete_list = JobMarkedForDelete.objects.all()
        entity_slug = self.kwargs['entity_slug']
        for job in self.get_queryset():
            for jmd in job_marked_for_delete_list:
                if job == jmd.job and jmd.approval_status == JobMarkedForDelete.NEW and job.entity.slug == entity_slug:
                    jobs_list.append(job)
        serializer = JobListSerializer(jobs_list, many=True)
        return Response(serializer.data)


class RejectJobMarkedForDeleteRequestView(APIView):
    queryset = Job.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated, CanRejectMarkedForDeleteJob)
    lookup_field = "slug"

    def put(self, request, *args, **kwargs):
        user = self.request.user
        job_slug = kwargs.get('slug')
        if job_slug is not None:

            try:
                job = Job.objects.get(slug=job_slug)
                job_marked_for_delete = JobMarkedForDelete.objects.get(job=job)
                if job_marked_for_delete.approval_status == JobMarkedForDelete.NEW:
                    #  if the job_marked_for_delete status is New, Change the job_marked_for_delete status to Rejected
                    job_marked_for_delete.approval_status = JobMarkedForDelete.REJECTED
                    job_marked_for_delete.save(update_fields=['approval_status'])
                    return Response({'detail': 'delete request for the job is rejected'}, status=status.HTTP_200_OK)

                elif job_marked_for_delete.approval_status == JobMarkedForDelete.REJECTED:
                    #  if the job_marked_for_delete status is Rejected, send message as it has been already rejected
                    return Response({'detail': 'the job delete request has been already rejected'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'Job  has been Deleted'},
                                    status=status.HTTP_400_BAD_REQUEST)

            except Job.DoesNotExist as jdn:
                logger.debug(jdn)
                return Response({'detail': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
            except JobMarkedForDelete.DoesNotExist as jmdn:
                logger.debug(jmdn)
                return Response({'detail': 'Job is not marked for delete'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response("bad Request", status=status.HTTP_400_BAD_REQUEST)


class JobSearchList(ListAPIView):
    queryset = Job.objects.all().filter(status=Job.ITEM_ACTIVE, start_date__lte=now(), expiry__gte=now())
    serializer_class = JobListSerializer

    def get_queryset(self):
        queryset = self.queryset

        qp_title = self.request.query_params.get('title', None)
        city_str = self.request.query_params.get('city',None)
        qp_fun_area = self.request.query_params.get('functional-area', None)

        if qp_title is not None:
            queryset = queryset.filter(title__icontains=qp_title).order_by('created')
        if city_str is not None:
            city_rpr = city_str.split(',')
            city = city_rpr[0].strip()
            queryset = queryset.filter(location__city__city__icontains=city).order_by('created')
        if qp_fun_area is not None:
            queryset = queryset.filter(occupation__name__icontains=qp_fun_area).order_by('created')
        return queryset


class JobCloseView(APIView):
    queryset = Job.objects.all()
    serializer_class = None
    lookup_field = "slug"
    permission_classes = (IsAuthenticated, CanPublishJob)


    def put(self, request, *args, **kwargs):
        job_slug = kwargs.get('slug')
        try:
            job = Job.objects.get(slug=job_slug)
            if job.status == Job.ITEM_CLOSED:
                return Response({'detail': 'Job has been already closed'}, status=status.HTTP_400_BAD_REQUEST)
            job.status = Job.ITEM_CLOSED
            job.save(update_fields=['status'])
            return Response({'detail': 'Job has been closed'}, status=status.HTTP_200_OK)

        except Job.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Job Not found'}, status=status.HTTP_404_NOT_FOUND)


class JobDraftPreviewView(RetrieveAPIView):
    serializer_class = JobDraftRetrieveSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_object(self):
        try:
            return JobDraft.objects.get(slug=self.kwargs.get('job_slug'))
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise


class DraftJobsViewSet(ModelViewSet):
    serializer_class = DraftJobSerializer
    permission_classes = (IsAuthenticated,CanCreateJob,)
    queryset = DraftJob.objects.all()

    def get_serializer(self, *args, **kwargs):
        return DraftJobRetrieveSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return DraftJob.objects.get(pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request,entity_slug=None,pagination=None):
        queryset = DraftJob.objects.filter(entity__slug=entity_slug)
        serializer = DraftJobListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, entity_slug=None, **kwargs):
        entity = Entity.objects.get(slug=entity_slug)
        context = {'entity': entity}

        serializer = DraftJobSerializer(data=request.data,context=context)

        serializer.is_valid(raise_exception=True)
        serializer.validated_data['entity'] = entity
        serializer.save()
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except:
            logger.exception("Cannot save job as draft")
            raise

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = self.get_object()
            serializer = DraftJobRetrieveSerializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Draft job not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request,pk=None, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Draft job not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Draft job not found"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, pk=None, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({"detail": "Draft job got deleted successfully "}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({'detail': "Draft job not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


class EntityJobDraftList(ICFListMixin,ListAPIView):
    queryset = JobDraft.objects.all()
    serializer_class = JobDraftListSerializer
    permission_classes = (IsAuthenticated,IsEntityUser)

    def get_queryset(self):
        queryset = self.queryset.filter(entity__slug = self.kwargs.get('slug'))
        return queryset


class JobDraftCreateApiView(CreateAPIView):
    queryset = JobDraft.objects.all()
    serializer_class = JobCreateDraftSerializer
    permission_classes = (IsAuthenticated, CanCreateJob)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class JobDraftDetailView(RetrieveAPIView):
    queryset = JobDraft.objects.all()
    serializer_class = JobDraftRetrieveSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class JobDraftUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = JobDraft.objects.all()
    serializer_class = JobDraftRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, CanEditJob)
    lookup_field = "slug"

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()


class UnregisteredUploadViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser, FileUploadParser)
    serializer_class = UnregisteredUserFileUploadSerializer
    # permission_classes = (IsAuthenticated,)
    queryset = UnregisteredUserFileUpload.objects.all()

    def get_serializer(self, *args, **kwargs):
        return UnregisteredUserFileUploadSerializer(*args, **kwargs)

    def get_object(self, queryset=None):
        instance = UnregisteredUserFileUpload.objects.filter(pk=self.kwargs['pk']).first()
        return instance

    def create(self, request, *args, mobile_no=None, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot add job profile files"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        obj = UnregisteredUserFileUpload.objects.filter(user=self.request.user, pk=pk)
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None, *args, **kwargs):
        context = {'user': self.request.user}
        try:
            instance = UnregisteredUserFileUpload.objects.get(pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot update profile file upload"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot update profile file upload"}, status=status.HTTP_400_BAD_REQUEST)


class UserResumeCreateAPIView(CreateAPIView):
    queryset = UserResume.objects.all()
    serializer_class = UserResumeCreateSerializer
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        context = {'user': self.request.user}

        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserResumeDeleteAPIView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = UserResume.objects.all()

    def destroy(self, request, *args, id=None, **kwargs):
        try:
            instance = UserResume.objects.get(id=id, job_profile__user=request.user)
            self.perform_destroy(instance)
            return Response({"detail": _("UserResume got deleted successfully.")}, status=status.HTTP_200_OK)

        except UserResume.DoesNotExist as wdne:
            logger.debug("UserResume not found, cannot delete")
            return Response({'detail': _("UserResume not found, cannot delete.")},
                            status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.debug("Something went wrong, cannot delete reason :{reason}".format(reason=str(e)))
            return Response({'detail': _("Something went wrong, cannot delete UserResume.")}, status=status.HTTP_404_NOT_FOUND)


class UserResumeComponentDeleteAPIView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)
    # serializer_class = UserResumeComponentDeleteSerializer
    queryset = UserResumeComponent.objects.all()

    def delete(self, request, *args, type=None, object_id=None, resume_id=None, **kwargs):
        try:
            # type = request.data.get('type')
            type = type
            # object_id = int(request.data.get('object_id'))
            object_id = int(object_id)
            # resume_id = int(request.data.get('resume_id'))
            resume_id = int(resume_id)

            if type and object_id and resume_id:
                pass
            else:
                raise Exception

            user_resume = UserResume.objects.get(id=resume_id)

            if type == 'education':
                try:
                    content_type = ContentType.objects.get(model='usereducation')
                    instance = UserResumeComponent.objects.get(user_resume=user_resume, object_id=object_id,
                                                               content_type=content_type)
                    self.perform_destroy(instance)
                    return Response({"detail": _("UserResumeComponent got deleted successfully.")}, status=status.HTTP_200_OK)
                except UserResumeComponent.DoesNotExist as ue:
                    raise ObjectDoesNotExist

            elif type == 'work_experience':
                try:
                    content_type = ContentType.objects.get(model='userworkexperience')
                    instance = UserResumeComponent.objects.get(user_resume=user_resume, object_id=object_id,
                                                               content_type=content_type)
                    self.perform_destroy(instance)
                    return Response({"detail": _("UserResumeComponent got deleted successfully.")}, status=status.HTTP_200_OK)
                except UserResumeComponent.DoesNotExist as ue:
                    raise ObjectDoesNotExist

            elif type == 'user_skill':
                try:
                    content_type = ContentType.objects.get(model='userskill')
                    instance = UserResumeComponent.objects.get(user_resume=user_resume, object_id=object_id,
                                                               content_type=content_type)
                    self.perform_destroy(instance)
                    return Response({"detail": _("UserResumeComponent got deleted successfully.")}, status=status.HTTP_200_OK)
                except UserResumeComponent.DoesNotExist as ue:
                    raise ObjectDoesNotExist

            elif type == 'relevant_link':
                try:
                    content_type = ContentType.objects.get(model='userrelevantlink')
                    instance = UserResumeComponent.objects.get(user_resume=user_resume, object_id=object_id,
                                                               content_type=content_type)
                    self.perform_destroy(instance)
                    return Response({"detail": _("UserResumeComponent got deleted successfully.")}, status=status.HTTP_200_OK)
                except UserResumeComponent.DoesNotExist as ue:
                    raise ObjectDoesNotExist

            elif type == 'hobbie':
                try:
                    content_type = ContentType.objects.get(model='userhobbie')
                    instance = UserResumeComponent.objects.get(user_resume=user_resume, object_id=object_id,
                                                               content_type=content_type)
                    self.perform_destroy(instance)
                    return Response({"detail": _("UserResumeComponent got deleted successfully.")}, status=status.HTTP_200_OK)
                except UserResumeComponent.DoesNotExist as ue:
                    raise ObjectDoesNotExist

            elif type == 'project':
                try:
                    content_type = ContentType.objects.get(model='userproject')
                    instance = UserResumeComponent.objects.get(user_resume=user_resume, object_id=object_id,
                                                               content_type=content_type)
                    self.perform_destroy(instance)
                    return Response({"detail": _("UserResumeComponent got deleted successfully.")}, status=status.HTTP_200_OK)
                except UserResumeComponent.DoesNotExist as ue:
                    raise ObjectDoesNotExist
            else:
                logger.exception('invalid type not found.')
                raise ICFException(_("Something went wrong, contact admin."),
                                   status_code=status.HTTP_400_BAD_REQUEST)

        except UserResume.DoesNotExist as wdne:
            logger.debug("UserResume not found, cannot delete user resume component.\n")
            return Response({'detail': _("UserResume not found, cannot delete.")},
                            status=status.HTTP_404_NOT_FOUND)
        except ValueError as ve:
            logger.debug("expected integer but found string.\n")
            return Response({'detail': _("Something went wrong, cannot delete UserResumeComponent.")},
                            status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.debug("Something went wrong, cannot delete reason :{reason}".format(reason=str(e)))
            return Response({'detail': _("Something went wrong, cannot delete UserResumeComponent.")}, status=status.HTTP_404_NOT_FOUND)


class UserResumeEditAPIView(UpdateAPIView):
    queryset = UserResume.objects.all()
    serializer_class = UserResumeUpdateSerializer
    permission_classes = (IsAuthenticated, )

    def update(self, request, *args, **kwargs):
        context = {'user': self.request.user}
        try:
            pk = int(request.data.get('user_resume_id'))
            # pk = 20
            instance = UserResume.objects.get(pk=pk)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
        except UserResume.DoesNotExist as e:
            logger.debug(str(e))
            return Response({"detail": _("Cannot update UserResume.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": _("Cannot update profile file upload")}, status=status.HTTP_400_BAD_REQUEST)


class UserResumeDetailAPIView(RetrieveAPIView):
    queryset = UserResume.objects.all()
    serializer_class = UserResumeRetrieveSerializer
    permission_classes = (IsAuthenticated,)

    lookup_field = "slug"


class UserResumeComponentCreateAPIView(CreateAPIView):
    queryset = UserResumeComponent.objects.all()
    # serializer_class = UserResumeComponentCreateSerializer
    permission_classes = (IsAuthenticated,)
    flag = False

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        context = {'user': self.request.user}

        type = self.request.data.get('type')
        object_id = self.request.data.get('object_id')
        resume_id = self.request.data.get('resume_id')
        global flag

        if type and object_id and resume_id:
            # global flag
            if type == 'education':
                try:
                    user_resume = UserResume.objects.get(id=int(resume_id))
                    user_education = UserEducation.objects.get(id=int(object_id))
                    user_resume_component = UserResumeComponent.objects.create(content_object=user_education,
                                                                              user_resume=user_resume)
                    # global flag
                    flag = True
                except ValueError as ex:
                    logger.exception('cannot convert string to integer.\n')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                except UserResume.DoesNotExist as re:
                    logger.exception('UserResume object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except UserEducation.DoesNotExist as re:
                    logger.exception('UserEducation object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            elif type == 'work_experience':
                try:
                    user_resume = UserResume.objects.get(id=int(resume_id))
                    user_work_experience = UserWorkExperience.objects.get(id=int(object_id))
                    user_resume_component = UserResumeComponent.objects.create(content_object=user_work_experience,
                                                                               user_resume=user_resume)
                    # global flag
                    flag = True
                except ValueError as ex:
                    logger.exception('cannot convert string to integer.\n')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                except UserResume.DoesNotExist as re:
                    logger.exception('UserResume object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except UserWorkExperience.DoesNotExist as re:
                    logger.exception('UserWorkExperience object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            elif type == 'user_skill':
                try:
                    user_resume = UserResume.objects.get(id=int(resume_id))
                    user_skill = UserSkill.objects.get(id=int(object_id))
                    user_resume_component = UserResumeComponent.objects.create(content_object=user_skill,
                                                                               user_resume=user_resume)

                    # global flag
                    flag = True
                except ValueError as ex:
                    logger.exception('cannot convert string to integer.\n')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                except UserResume.DoesNotExist as re:
                    logger.exception('UserResume object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except UserSkill.DoesNotExist as re:
                    logger.exception('UserSkill object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            elif type == 'relevant_link':
                try:
                    user_resume = UserResume.objects.get(id=int(resume_id))
                    user_relevant_link = UserRelevantLink.objects.get(id=int(object_id))
                    user_resume_component = UserResumeComponent.objects.create(content_object=user_relevant_link,
                                                                               user_resume=user_resume)
                    # global flag
                    flag = True
                except ValueError as ex:
                    logger.exception('cannot convert string to integer.\n')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                except UserResume.DoesNotExist as re:
                    logger.exception('UserResume object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except UserRelevantLink.DoesNotExist as re:
                    logger.exception('UserRelevantLink object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            elif type == 'hobbie':
                try:
                    user_resume = UserResume.objects.get(id=int(resume_id))
                    user_hobbie = UserHobbie.objects.get(id=int(object_id))
                    user_resume_component = UserResumeComponent.objects.create(content_object=user_hobbie,
                                                                               user_resume=user_resume)
                    # global flag
                    flag = True
                except ValueError as ex:
                    logger.exception('cannot convert string to integer.\n')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                except UserResume.DoesNotExist as re:
                    logger.exception('UserResume object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except UserHobbie.DoesNotExist as re:
                    logger.exception('UserHobbie object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            elif type == 'project':
                try:
                    user_resume = UserResume.objects.get(id=int(resume_id))
                    user_project = UserProject.objects.get(id=int(object_id))
                    user_resume_component = UserResumeComponent.objects.create(content_object=user_project,
                                                                               user_resume=user_resume)
                    # global flag
                    flag = True
                except ValueError as ex:
                    logger.exception('cannot convert string to integer.\n')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                except UserResume.DoesNotExist as re:
                    logger.exception('UserResume object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                except UserProject.DoesNotExist as re:
                    logger.exception('UserProject object not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
            else:
                logger.exception('invalid type object not found.')
                raise ICFException(_("Something went wrong, contact admin."),
                                   status_code=status.HTTP_400_BAD_REQUEST)

        else:
            logger.exception('invalid type or  object_id or resume_id.')
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        if flag:
            result = "success"
            status_code = status.HTTP_201_CREATED
        else:
            result = "error"
            status_code = status.HTTP_400_BAD_REQUEST

        return Response({"result": result}, status=status_code)


class UserResumeStatusUpdateAPIView(APIView):
    queryset = UserResume.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        context = {'user': self.request.user}
        try:
            resume_id = int(kwargs.get('resume_id'))
            user_job_profile = UserJobProfile.objects.get(user=self.request.user)
            user_resume = UserResume.objects.get(id=resume_id, job_profile=user_job_profile)
            user_resume.is_active = True
            user_resume.save(update_fields=['is_active'])

            user_education_list = []
            user_work_experience_list = []
            user_skill_list = []
            user_relevant_link_list = []
            user_project_list = []
            user_hobbie_list = []

            content_type_education = ContentType.objects.get(model='usereducation')
            user_education_resume_components = UserResumeComponent.objects.filter(user_resume=user_resume,
                                                content_type=content_type_education).order_by('sort_order')

            for user_education_resume_component in user_education_resume_components:
                try:
                    user_education = UserEducation.objects.get(id=user_education_resume_component.object_id)
                    user_education_list.append(user_education)

                except UserEducation.DoesNotExists as ctdne:
                    raise

            # ----------------------------------------------
            content_type_work_experience = ContentType.objects.get(model='userworkexperience')
            user_work_experience_resume_components = UserResumeComponent.objects.filter(user_resume=user_resume,
                                                    content_type=content_type_work_experience).order_by('sort_order')

            for user_work_experience_resume_component in user_work_experience_resume_components:
                try:
                    user_work_experience = UserWorkExperience.objects.get(id=user_work_experience_resume_component.object_id)
                    user_work_experience_list.append(user_work_experience)

                except UserWorkExperience.DoesNotExists as ctdne:
                    raise

            # ------------------------------------------------

            # create skill user components

            content_type_user_skill = ContentType.objects.get(model='userskill')
            user_user_skill_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume,
                content_type=content_type_user_skill)

            for user_user_skill_resume_component in user_user_skill_resume_components:
                try:
                    user_skill = UserSkill.objects.get(id=user_user_skill_resume_component.object_id)
                    user_skill_list.append(user_skill)

                except UserSkill.DoesNotExists as ctdne:
                    raise

            # ----------------------------------
            # create relevant link user components

            content_type_user_relevant_link = ContentType.objects.get(model='userrelevantlink')
            user_relevant_link_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume,
                content_type=content_type_user_relevant_link)

            for user_relevant_link_resume_component in user_relevant_link_resume_components:
                try:
                    user_relevant_link = UserRelevantLink.objects.get(
                        id=user_relevant_link_resume_component.object_id)
                    user_relevant_link_list.append(user_relevant_link)

                except UserRelevantLink.DoesNotExists as ctdne:
                    raise

            # ----------------------------------
            # create project user components

            content_type_user_project = ContentType.objects.get(model='userproject')
            user_project_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume,
                content_type=content_type_user_project).order_by('sort_order')

            for user_project_resume_component in user_project_resume_components:
                try:
                    user_project = UserProject.objects.get(
                        id=user_project_resume_component.object_id)
                    user_project_list.append(user_project)

                except UserProject.DoesNotExists as ctdne:
                    raise

            # ----------------------------------
            # create hobby user components

            content_type_user_hobbie = ContentType.objects.get(model='userhobbie')
            user_hobbie_resume_components = UserResumeComponent.objects.filter(
                user_resume=user_resume,
                content_type=content_type_user_hobbie)

            for user_hobbie_resume_component in user_hobbie_resume_components:
                try:
                    user_hobbie = UserHobbie.objects.get(
                        id=user_hobbie_resume_component.object_id)
                    user_hobbie_list.append(user_hobbie)

                except UserHobbie.DoesNotExists as ctdne:
                    raise ObjectDoesNotExist


            base_url = request.build_absolute_uri()

            base_url = base_url
            try:
                user_profile = UserProfile.objects.get(user=user_resume.job_profile.user)
                user_profile_image = UserProfileImage.objects.filter(user_profile=user_profile).first()
                if user_profile_image:
                    user_profile_image_url = user_profile_image.image.url
                else:
                    user_profile_image_url = None
            except ObjectDoesNotExist as upe:
                user_profile_image_url = None

            resume_pdf_image_dict = PDFGeneratorForResume().generate_resume_for_user(user_resume, user_education_list, user_work_experience_list,
                                                             user_skill_list, user_project_list,
                                                             user_relevant_link_list,
                                                             user_hobbie_list, base_url, user_profile_image_url)

            response_data = {"result": _("successfully updated user resume status."),
                             "resume_url": resume_pdf_image_dict.get('resume_url'),
                             "thumbnail_url": resume_pdf_image_dict.get('thumbnail_url'),

                            }

            return Response(response_data, status=status.HTTP_200_OK)

        except UserJobProfile.DoesNotExist as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except UserResume.DoesNotExist as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except ValueError as ve:
            logger.exception(str(ve))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class UserResumeCloneCreateAPIView(CreateAPIView):
    queryset = UserResume.objects.all()
    serializer_class = UserResumeCreateCloneSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, slug=None, **kwargs):
        context = {
                    'user': self.request.user,
                    'slug': self.kwargs.get('slug')
                   }

        serializer = UserResumeCreateCloneSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserResumeCountAPIView(APIView):
    queryset = UserResume.objects.all()
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        try:
            user = self.request.user
            user_resume_count = len(UserResume.objects.filter(job_profile__user=user))
            return Response({'user_resume_count': user_resume_count}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': 'Something went wrong, contact admin.'},
                            status=status.HTTP_400_BAD_REQUESTss)


class UserResumeListAPIView(ListAPIView):
    serializer_class = UserResumeListSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        try:
            job_profile = UserJobProfile.objects.get(user=self.request.user)
            queryset = UserResume.objects.filter(job_profile=job_profile)
            return queryset
        except UserJobProfile.DoesNotExist as je:
            logger.exception("UserJobProfile object not found for the user. reason:{reason}\n".format(reason=str(je)))
            raise ICFException(_("User does not have job profile. please create the job profile first."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class TaskCreateAPIView(CreateAPIView):
    serializer_class = TaskCreateSerializer
    permission_classes = (IsAuthenticated, )
    queryset = Task.objects.all()

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    # def get_serializer_class(self):
    #     return self.serializer_class

    def create(self, request, *args, **kwargs):
        work_experience_id = int(self.request.data.get('work_experience_id'))
        task_desc = self.request.data.get('description')
        user = self.request.user
        context = {
            'work_experience_id': work_experience_id,
            'task_desc': task_desc,
            'user': user
        }
        serializer = TaskCreateSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ModifyUserComponentSortOrderAPIView(APIView):
    queryset = UserResumeComponent.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            resume_id = int(self.request.data.get("resume_id"))
            type = self.request.data.get('type')
            user_job_profile = UserJobProfile.objects.get(user=self.request.user)
            user_resume = UserResume.objects.get(id=resume_id, job_profile=user_job_profile)

            user_component_list = self.request.data.get("user_component_list")

            if type and user_component_list and user_resume:

                if type == 'education':
                    content_type_education = ContentType.objects.get(model='usereducation')
                    for index, user_component in enumerate(user_component_list):
                        id = int(user_component.get("id", None))
                        if id:
                            user_education_resume_component = UserResumeComponent.objects.get(user_resume=user_resume,
                                                                object_id=id,
                                                                content_type=content_type_education)
                            user_education_resume_component.sort_order = index
                            user_education_resume_component.save(update_fields=['sort_order'])

                        else:
                            logger.exception("could not sort user education not a valid id.")
                            raise ICFException(_("Something went wrong, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                    return Response({'detail': 'user education sort order has been modified.'},
                                        status=status.HTTP_200_OK)

                elif type == 'work_experience':
                    content_type_work_experience = ContentType.objects.get(model='userworkexperience')
                    for index, user_component in enumerate(user_component_list):
                        id = int(user_component.get("id", None))
                        if id:
                            user_work_experience_component = UserResumeComponent.objects.get(user_resume=user_resume,
                                                                                            object_id=id,
                                                                                            content_type=content_type_work_experience)
                            user_work_experience_component.sort_order = index
                            user_work_experience_component.save(update_fields=['sort_order'])
                        else:
                            logger.exception("could not sort user work experience not a valid id.")
                            raise ICFException(_("Something went wrong, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                    return Response({'detail': 'user work experience sort order has been modified.'}, status=status.HTTP_200_OK)

                elif type == 'project':
                    content_type_user_project = ContentType.objects.get(model='userproject')
                    for index, user_component in enumerate(user_component_list):
                        id = int(user_component.get("id", None))
                        if id:
                            user_project_resume_component = UserResumeComponent.objects.get(user_resume=user_resume,
                                                                                          object_id=id,
                                                                                          content_type=content_type_user_project)
                            user_project_resume_component.sort_order = index
                            user_project_resume_component.save(update_fields=['sort_order'])
                        else:
                            logger.exception("could not sort user project not a valid id.")
                            raise ICFException(_("Something went wrong, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                    return Response({'detail': 'user project sort order has been modified.'},
                                    status=status.HTTP_200_OK)

                else:
                    logger.exception('invalid type not found.')
                    raise ICFException(_("Something went wrong, contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

        except UserJobProfile.DoesNotExist as ue:
            logger.exception("UserJobProfile object not found for the user. reason:{reason}\n".format(reason=str(ue)))
            raise ICFException(_("UserJobProfile object not found for the user."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except UserResume.DoesNotExist as ue:
            logger.exception("UserResume object not found for the user. reason:{reason}\n".format(reason=str(ue)))
            raise ICFException(_("UserResume object not found for the user."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except UserWorkExperience.DoesNotExist as re:
            logger.exception('UserWorkExperience object not found.')
            raise ICFException(_("Something went wrong, contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except UserResumeComponent.DoesNotExist as urc:
            logger.exception("UserResumeComponent object not found for the user. reason:{reason}\n".format(reason=str(urc)))
            raise ICFException(_("UserResumeComponent object not found for the user."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except ContentType.DoesNotExist as urc:
            logger.exception("ContentType object not found. reason:{reason}\n".format(reason=str(urc)))
            raise ICFException(_("ContentType object not found."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class SearchCandidatesAPIView(ListAPIView):
    queryset = UserJobProfile.objects.all()
    serializer_class = CandidateSearchUserJobProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:

            logger.info("City List: {}".format(self.request.data.get('city_id_list', None)))
            logger.info("Education Level ID List: {}".format(self.request.data.get('education_level_id_list', None)))
            logger.info("Key skills: {}".format(self.request.data.get('key_skills_id_list', None)))
            logger.info("Computer skills: {}".format(self.request.data.get('computer_skills_id_list', None)))
            logger.info("Language skills: {}".format(self.request.data.get('language_skills_id_list', None)))

            city_id_list = self.request.data.get('city_id_list', None)
            work_experience_in_years = self.request.data.get('work_experience_in_years', None)
            education_level_id_list = self.request.data.get('education_level_id_list', None)
            key_skills_id_list = self.request.data.get('key_skills_id_list', [])
            computer_skills_id_list = self.request.data.get('computer_skills_id_list', [])
            language_skills_id_list = self.request.data.get('language_skills_id_list', [])

            location_matching_user_profile_id_list = []
            experience_matching_user_profile_id_list = []
            education_level_matching_user_profile_id_list = []
            key_skill_matching_user_profile_id_list = []
            computer_skill_matching_user_profile_id_list = []
            language_skill_matching_user_profile_id_list = []

            # if city_id_list:
            #     for city_id in city_id_list:
            #         city_obj = City.objects.get(pk=city_id)
            #         user_profile_qs = UserProfile.objects.filter(location__city__city__iexact=city_obj.city)
            #         for user_profile in user_profile_qs:
            #             try:
            #                 user_job_profile_obj = UserJobProfile.objects.get(user=user_profile.user)
            #                 location_matching_user_profile_id_list.append(user_job_profile_obj.id)
            #             except UserJobProfile.DoesNotExist as ne:
            #                 logger.info("User does not have a job profile: {}". format(user_profile))
            #                 pass

            if city_id_list:
                city_ids = [s for s in city_id_list if isinstance(s, int)]
                c_users = UserProfile.objects.filter(location__city__id__in=city_ids).values_list("user__id",
                                                                                                      flat=True)
                location_matching_user_profile_id_list = UserJobProfile.objects.filter(
                    user__id__in=c_users).values_list("id", flat=True).order_by(
                    "id").distinct()

            # if work_experience_in_years:
            #     work_experience_in_years = int(work_experience_in_years)
            #     # convert experience in years to seconds
            #     total_required_work_experience_in_seconds = work_experience_in_years * (365*24*60*60)
            #     work_exp_job_profile_id_qs = UserWorkExperience.objects.values_list('job_profile_id', flat=True).distinct()
            #     # print(qs)
            #     # print(len(qs))
            #     # exp_job_profile_list = []
            #     for job_profile_id in work_exp_job_profile_id_qs:
            #         job_profile_obj = UserJobProfile.objects.get(id=job_profile_id)
            #         work_exp_qs = UserWorkExperience.objects.filter(job_profile=job_profile_obj)
            #         user_total_work_exp_in_seconds = 0
            #         for exp in work_exp_qs:
            #             # print("exp_from: {d}".format(d=exp.worked_from))
            #             # print("exp_till: {till}".format(till=exp.worked_till))
            #             user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from, exp.worked_till)
            #             # print("Single work experience: ", single_exp_in_seconds)
            #             user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
            #         if user_total_work_exp_in_seconds >= total_required_work_experience_in_seconds:
            #             experience_matching_user_profile_id_list.append(job_profile_id)

            # if education_level_id_list:
            #     for education_level_id in education_level_id_list:
            #         education_level_obj = EducationLevel.objects.get(id=education_level_id)
            #         education_job_profile_id_qs = UserEducation.objects.filter(education_level=education_level_obj).values_list('job_profile', flat=True)
            #         for job_profile_id in education_job_profile_id_qs:
            #             education_level_matching_user_profile_id_list.append(job_profile_id)

            if education_level_id_list:
                edu_ids = [s for s in education_level_id_list if isinstance(s, int)]
                education_level_matching_user_profile_id_list = UserEducation.objects.filter(
                    education_level__id__in=edu_ids).values_list(
                    "job_profile__id",
                    flat=True).order_by(
                    "job_profile__id").distinct()


            #
            # if key_skills_id_list:
            #     for skill_id in key_skills_id_list:
            #         key_skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
            #                                                      skill__skill_type=Skill.KEY_SKILLS).values_list('job_profile', flat=True)
            #         for job_profile_id in key_skill_job_profile_id_qs:
            #             key_skill_matching_user_profile_id_list.append(job_profile_id)
            # if computer_skills_id_list:
            #     for skill_id in computer_skills_id_list:
            #         computer_skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
            #                                                      skill__skill_type=Skill.COMPUTER_SKILLS).values_list('job_profile', flat=True)
            #         for job_profile_id in computer_skill_job_profile_id_qs:
            #             computer_skill_matching_user_profile_id_list.append(job_profile_id)
            # if language_skills_id_list:
            #     for skill_id in language_skills_id_list:
            #         language_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
            #                                                      skill__skill_type=Skill.LANGUAGE).values_list('job_profile', flat=True)
            #         for job_profile_id in language_job_profile_id_qs:
            #             language_skill_matching_user_profile_id_list.append(job_profile_id)

            skills_list = key_skills_id_list + computer_skills_id_list + language_skills_id_list
            if skills_list:
                skill_ids = [s for s in skills_list if isinstance(s, int)]
                key_skill_matching_user_profile_id_list = UserSkill.objects.filter(id__in=skill_ids).values_list(
                    "job_profile__id",
                    flat=True).annotate(
                    Count("job_profile__id")).order_by()

            final_job_profile_list = []
            # job_profile_list_1 = get_intersection_of_lists(location_matching_user_profile_id_list,
            #                                                experience_matching_user_profile_id_list)
            # job_profile_list_2 = get_intersection_of_lists(education_level_matching_user_profile_id_list,
            #                                                key_skill_matching_user_profile_id_list)
            # job_profile_list_3 = get_intersection_of_lists(computer_skill_matching_user_profile_id_list,
            #                                                language_skill_matching_user_profile_id_list)
            # final_job_profile_list_1 = get_intersection_of_lists(job_profile_list_1, job_profile_list_2)
            # final_job_profile_list_2 = job_profile_list_3
            # final_job_profile_list = get_intersection_of_lists(final_job_profile_list_1, final_job_profile_list_2)

            job_profile_list_1 = get_intersection_of_lists(location_matching_user_profile_id_list,
                                                           education_level_matching_user_profile_id_list)
            job_profile_list_2 = get_intersection_of_lists(job_profile_list_1,
                                                           key_skill_matching_user_profile_id_list)

            if work_experience_in_years:
                work_experience_in_years = int(work_experience_in_years)
                # convert experience in years to seconds
                total_required_work_experience_in_seconds = work_experience_in_years * (365*24*60*60)
                if job_profile_list_2 or job_profile_list_1:
                    work_exp_job_profile_id_qs = UserWorkExperience.objects.filter(
                        job_profile__id__in=job_profile_list_2).values_list('job_profile_id', flat=True).distinct()
                else:
                    work_exp_job_profile_id_qs = UserWorkExperience.objects.values_list('job_profile_id',
                                                                                        flat=True).distinct()
                # print(qs)
                # print(len(qs))
                # exp_job_profile_list = []
                for job_profile_id in work_exp_job_profile_id_qs:
                    job_profile_obj = UserJobProfile.objects.get(id=job_profile_id)
                    work_exp_qs = UserWorkExperience.objects.filter(job_profile=job_profile_obj)
                    user_total_work_exp_in_seconds = 0
                    for exp in work_exp_qs:
                        # print("exp_from: {d}".format(d=exp.worked_from))
                        # print("exp_till: {till}".format(till=exp.worked_till))
                        user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from, exp.worked_till)
                        # print("Single work experience: ", single_exp_in_seconds)
                        user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
                    if user_total_work_exp_in_seconds >= total_required_work_experience_in_seconds:
                        experience_matching_user_profile_id_list.append(job_profile_id)

            final_job_profile_list = get_intersection_of_lists(job_profile_list_2, experience_matching_user_profile_id_list)

            if final_job_profile_list:
                print(final_job_profile_list)
                # print(len(final_job_profile_list))
                final_job_profile_list = final_job_profile_list
                queryset = UserJobProfile.objects.filter(id__in=final_job_profile_list)
                return queryset
            else:
                queryset = UserJobProfile.objects.none()
                return queryset
            # queryset = UserJobProfile.objects.filter(id__in=final_job_profile_list)
            # return queryset
        except UserJobProfile.DoesNotExist as jpe:
            # logger.exception("UserJobProfile object does not exist")
            # raise ICFException(_("Something went wrong, Please contact admin."),
            # status_code=status.HTTP_400_BAD_REQUEST)
            # user does not have UserJobProfile so will ignore the user
            pass
        except EducationLevel.DoesNotExist as ele:
            logger.exception("Education level object does not exist")
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.exception("value of type is not matching {reason}".format(reason=str(ve)))
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # queryset = self.queryset
        # return queryset
        # do some filtering

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        if page is not None:
            # return self.get_paginated_response({'results': serializer.data})
            return self.get_paginated_response(serializer.data)
        else:
            # return Response({'results': serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)
        #
        # serializer = self.get_serializer(queryset, many=True)
        # return Response(serializer.data)


class SearchCandidatesForJobAPIView(SearchCandidateListMixin, ListAPIView):
    queryset = UserJobProfile.objects.all()
    serializer_class = CandidateSearchUserJobProfileSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        # return Response({'active_job_count': queryset_count}, status=status.HTTP_200_OK)
        search_criteria_list = []
        cs_for_job_parameters = CandidateSearchForJobMaster.objects.all()
        for search_criteria_obj in cs_for_job_parameters:
           search_criteria_list.append(search_criteria_obj.search_criteria)

        job_slug = self.kwargs.get('slug', None)
        try:
            job = Job.objects.get(slug=job_slug)
        except Job.DoesNotExist as je:
            logger.exception("Job object Not found")
            raise ICFException(_("Something went wrong. Please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        job_filters = {}
        for search_criteria in search_criteria_list:
            if search_criteria == CandidateSearchForJobMasterChoice.SKILL:
                job_key_skills = JobSkill.objects.filter(job=job, skill__skill_type=Skill.KEY_SKILLS)
                job_key_skills_id_list = []
                for job_key_skill in job_key_skills:
                    job_key_skills_id_list.append(job_key_skill.skill_id)
                job_filters.update({'key_skills': job_key_skills_id_list})

                job_computer_skills = JobSkill.objects.filter(job=job, skill__skill_type=Skill.COMPUTER_SKILLS)
                job_computer_skills_id_list = []
                for job_computer_skill in job_computer_skills:
                    job_computer_skills_id_list.append(job_computer_skill.skill_id)
                job_filters.update({'computer_skills': job_computer_skills_id_list})

                job_language_skills = JobSkill.objects.filter(job=job, skill__skill_type=Skill.LANGUAGE)
                job_language_skills_id_list = []
                for job_language_skill in job_language_skills:
                    job_language_skills_id_list.append(job_language_skill.skill_id)
                job_filters.update({'language_skills': job_language_skills_id_list})

            elif search_criteria == CandidateSearchForJobMasterChoice.WORK_EXPERIENCE:
                job_filters.update({'experience_years': job.experience_years, 'experience_months': job.experience_months})
            elif search_criteria == CandidateSearchForJobMasterChoice.EDUCATION:
                job_filters.update({'education_level': job.education_level_id})
            elif search_criteria == CandidateSearchForJobMasterChoice.LOCATION:
                address_obj = Address.objects.get(id=job.location_id)
                address_serializer = AddressSerializer(address_obj)
                job_filters.update({'location': address_serializer.data})
            else:
                pass

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({'results': serializer.data,
                                                'search_filter_list': search_criteria_list, 'job_filters': job_filters})
        else:
            return Response({'results': serializer.data, 'search_filter_list': search_criteria_list, 'job_filters': job_filters}, status=status.HTTP_200_OK)


class SaveCandidateSearchAPIView(CreateAPIView):
    serializer_class = CandidateSearchCreateSerializer
    queryset = CandidateSearch.objects.all()
    permission_classes = (IsAuthenticated, IsEntityUser)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            entity_slug = self.kwargs.get('entity_slug')
            entity = Entity.objects.get(slug=entity_slug)
            context = {'entity_slug': entity_slug, 'user': self.request.user}
            serializer = self.get_serializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Entity.DoesNotExist as ce:
            logger.exception("Entity object not found.")
            return Response({"detail": "Entity object not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong. reason:{reason}".format(reason=str(e))), status_code=status.HTTP_400_BAD_REQUEST)


class CandidateSearchUpdateApiView(RetrieveUpdateAPIView):
    queryset = CandidateSearch.objects.all()
    serializer_class = CandidateSearchRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self):
        try:
            search_slug = self.kwargs.get('search_slug', None)
            if search_slug:
                candidate_search_obj = CandidateSearch.objects.get(slug=search_slug)
                return candidate_search_obj
        except CandidateSearch.DoesNotExist as ce:
            logger.info("CandidateSearch object not found.")
            raise ICFException(_("Object not found."), status_code=status.HTTP_404_NOT_FOUND)


class DeleteCandidateSearchAPIView(DestroyAPIView):
    queryset = CandidateSearch.objects.all()
    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args,  **kwargs):
        try:
            instance = CandidateSearch.objects.get(slug=self.kwargs.get('search_slug'))
            self.perform_destroy(instance)
            return Response({"detail": "CandidateSearch got deleted successfully."}, status=status.HTTP_200_OK)

        except CandidateSearch.DoesNotExist as wdne:
            logger.debug("CandidateSearch object not found, cannot delete")
            return Response({'detail': "CandidateSearch object not found, cannot delete."},
                            status=status.HTTP_404_NOT_FOUND)


class CandidateSearchListAPIView(ListAPIView):
    serializer_class = CandidateSearchListSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_queryset(self):
        print('-------', self)
        try:
            queryset = CandidateSearch.objects.filter(entity_slug=self.kwargs.get('entity_slug')).order_by('-created')
            return queryset
        except Exception as cse:
            logger.exception("Something went wrong. reason:{reason}\n".format(reason=str(cse)))
            raise ICFException(_("Something went wrong. Please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class CandidateSearchBySearchSlugAPIView(ListAPIView):
    #
    # api to get candidates(job seekers based on saved search slug)
    #
    queryset = UserJobProfile.objects.all()
    serializer_class = CandidateSearchUserJobProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            search_slug = self.kwargs.get('search_slug', None)
            if search_slug:
                search_obj = CandidateSearch.objects.get(slug=search_slug)
                # if not search_obj.job_title:
                city_id_list = []
                city_id_str = search_obj.location
                if city_id_str:
                    city_id_list_str = city_id_str.split(",")
                    for i in city_id_list_str:
                        city_id_list.append(int(i))

                work_experience_in_years = search_obj.work_experience

                education_level_id_list = []
                education_level_id_str = search_obj.education_level
                if education_level_id_str:
                    education_level_id_list_str = education_level_id_str.split(",")
                    for i in education_level_id_list_str:
                        education_level_id_list.append(int(i))

                key_skills_id_list = []
                key_skills_id_str = search_obj.key_skill
                if key_skills_id_str:
                    key_skills_id_list_str = key_skills_id_str.split(",")
                    for i in key_skills_id_list_str:
                        key_skills_id_list.append(int(i))

                computer_skills_id_list = []
                computer_skills_id_str = search_obj.computer_skill
                if computer_skills_id_str:
                    computer_skills_id_list_str = computer_skills_id_str.split(",")
                    for i in computer_skills_id_list_str:
                        computer_skills_id_list.append(int(i))

                language_skills_id_list = []
                language_skills_id_str = search_obj.language_skill
                if language_skills_id_str:
                    language_skills_id_list_str = language_skills_id_str.split(",")
                    for i in language_skills_id_list_str:
                        language_skills_id_list.append(int(i))

                location_matching_user_profile_id_list = []
                experience_matching_user_profile_id_list = []
                education_level_matching_user_profile_id_list = []
                key_skill_matching_user_profile_id_list = []
                computer_skill_matching_user_profile_id_list = []
                language_skill_matching_user_profile_id_list = []

                if city_id_list:
                    for city_id in city_id_list:
                        city_obj = City.objects.get(pk=city_id)
                        user_profile_qs = UserProfile.objects.filter(location__city__city__iexact=city_obj.city)
                        for user_profile in user_profile_qs:
                            user_job_profile_obj = UserJobProfile.objects.get(user=user_profile.user)
                            location_matching_user_profile_id_list.append(user_job_profile_obj.pk)

                if work_experience_in_years:
                    work_experience_in_years = int(work_experience_in_years)
                    # convert experience in years to seconds
                    total_required_work_experience_in_seconds = work_experience_in_years * (365 * 24 * 60 * 60)
                    work_exp_job_profile_id_qs = UserWorkExperience.objects.values_list('job_profile_id', flat=True).distinct()
                    for job_profile_id in work_exp_job_profile_id_qs:
                        job_profile_obj = UserJobProfile.objects.get(id=job_profile_id)
                        work_exp_qs = UserWorkExperience.objects.filter(job_profile=job_profile_obj)
                        user_total_work_exp_in_seconds = 0
                        for exp in work_exp_qs:
                            user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from,
                                                                                             exp.worked_till)
                            user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
                        if user_total_work_exp_in_seconds >= total_required_work_experience_in_seconds:
                            experience_matching_user_profile_id_list.append(job_profile_id)

                if education_level_id_list:
                    for education_level_id in education_level_id_list:
                        education_level_obj = EducationLevel.objects.get(id=education_level_id)
                        education_job_profile_id_qs = UserEducation.objects.filter(
                            education_level=education_level_obj).values_list('job_profile', flat=True)
                        for job_profile_id in education_job_profile_id_qs:
                            education_level_matching_user_profile_id_list.append(job_profile_id)
                if key_skills_id_list:
                    for skill_id in key_skills_id_list:
                        key_skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
                                                                               skill__skill_type=Skill.KEY_SKILLS).values_list(
                            'job_profile', flat=True)
                        for job_profile_id in key_skill_job_profile_id_qs:
                            key_skill_matching_user_profile_id_list.append(job_profile_id)
                if computer_skills_id_list:
                    for skill_id in computer_skills_id_list:
                        computer_skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
                                                                                    skill__skill_type=Skill.COMPUTER_SKILLS).values_list(
                            'job_profile', flat=True)
                        for job_profile_id in computer_skill_job_profile_id_qs:
                            computer_skill_matching_user_profile_id_list.append(job_profile_id)
                if language_skills_id_list:
                    for skill_id in language_skills_id_list:
                        language_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
                                                                              skill__skill_type=Skill.LANGUAGE).values_list(
                            'job_profile', flat=True)
                        for job_profile_id in language_job_profile_id_qs:
                            language_skill_matching_user_profile_id_list.append(job_profile_id)
                final_job_profile_list = []
                job_profile_list_1 = get_intersection_of_lists(location_matching_user_profile_id_list,
                                                               experience_matching_user_profile_id_list)
                job_profile_list_2 = get_intersection_of_lists(education_level_matching_user_profile_id_list,
                                                               key_skill_matching_user_profile_id_list)
                job_profile_list_3 = get_intersection_of_lists(computer_skill_matching_user_profile_id_list,
                                                               language_skill_matching_user_profile_id_list)
                final_job_profile_list_1 = get_intersection_of_lists(job_profile_list_1, job_profile_list_2)
                final_job_profile_list_2 = job_profile_list_3
                final_job_profile_list = get_intersection_of_lists(final_job_profile_list_1, final_job_profile_list_2)
                if final_job_profile_list:
                    final_job_profile_list = final_job_profile_list
                    queryset = UserJobProfile.objects.filter(id__in=final_job_profile_list)
                    return queryset
                else:
                    queryset = UserJobProfile.objects.none()
                    return queryset
                # else:
                #     pass

            else:
                logger.exception("invalid search_slug value")
                raise ICFException(_("Something went wrong, Please contact admin."))
        except CandidateSearch.DoesNotExist as cse:
            logger.exception("CandidateSearch object does not exist")
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except EducationLevel.DoesNotExist as ele:
            logger.exception("Education level object does not exist")
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.exception("value of type is not matching {reason}".format(reason=str(ve)))
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # queryset = self.queryset
        # return queryset
        # do some filtering

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CandidateSearchObjectAPIView(RetrieveAPIView):
    queryset = CandidateSearch.objects.all()
    serializer_class = CandidateSearchListSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        try:
            search_slug = self.kwargs.get('search_slug', None)
            if search_slug:
                candidate_search_obj = CandidateSearch.objects.get(slug=search_slug)
                return candidate_search_obj
        except CandidateSearch.DoesNotExist as ce:
            logger.info("CandidateSearch object not found.")
            raise ICFException(_("Object not found."), status_code=status.HTTP_404_NOT_FOUND)

