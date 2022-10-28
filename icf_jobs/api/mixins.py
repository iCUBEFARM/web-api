from icf_auth.models import UserProfile
from icf_generic.Exceptions import ICFException
from icf_jobs.JobHelper import get_user_work_experience_in_seconds, get_intersection_of_lists
from icf_jobs.models import Job, CandidateSearchForJobMaster, CandidateSearchForJobMasterChoice, JobSkill, UserSkill, \
    UserWorkExperience, UserJobProfile, UserEducation
from rest_framework import status
from django.utils.translation import ugettext_lazy as _

import logging

logger = logging.getLogger(__name__)


class SearchCandidateListMixin(object):
    def get_queryset(self):
        try:
            job_slug = self.kwargs.get('slug', None)
            if job_slug:
                job = Job.objects.get(slug=job_slug)
                cs_for_job_parameters = CandidateSearchForJobMaster.objects.all()

                skill_matching_user_profile_id_list = []
                experience_matching_user_profile_id_list = []
                education_level_matching_user_profile_id_list = []
                location_matching_user_profile_id_list = []
                for cs in cs_for_job_parameters:
                    if cs.search_criteria == CandidateSearchForJobMasterChoice.SKILL:
                        job_skill_id_qs = JobSkill.objects.filter(job=job).values_list('skill', flat=True)
                        for skill_id in job_skill_id_qs:
                            skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id).values_list(
                                'job_profile',
                                flat=True)
                            for job_profile_id in skill_job_profile_id_qs:
                                skill_matching_user_profile_id_list.append(job_profile_id)

                    elif cs.search_criteria == CandidateSearchForJobMasterChoice.WORK_EXPERIENCE:
                        job_required_experience_in_months = 0
                        if job.experience_years:
                            job_required_experience_in_months = job.experience_years * 12
                        if job.experience_months:
                            job_required_experience_in_months = job_required_experience_in_months + job.experience_months
                        total_required_work_experience_in_seconds = (job_required_experience_in_months // 12) * (
                                    365 * 24 * 60 * 60)
                        work_exp_job_profile_id_qs = UserWorkExperience.objects.values_list('job_profile_id',
                                                                                            flat=True).distinct()
                        for job_profile_id in work_exp_job_profile_id_qs:
                            job_profile_obj = UserJobProfile.objects.get(id=job_profile_id)
                            work_exp_qs = UserWorkExperience.objects.filter(job_profile=job_profile_obj)
                            user_total_work_exp_in_seconds = 0
                            for exp in work_exp_qs:
                                # print("exp_from: {d}".format(d=exp.worked_from))
                                # print("exp_till: {till}".format(till=exp.worked_till))
                                user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from,
                                                                                                 exp.worked_till)
                                # print("Single work experience: ", single_exp_in_seconds)
                                user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
                            if user_total_work_exp_in_seconds >= total_required_work_experience_in_seconds:
                                experience_matching_user_profile_id_list.append(job_profile_id)

                    elif cs.search_criteria == CandidateSearchForJobMasterChoice.EDUCATION:
                        user_education_qs = UserEducation.objects.filter(education_level=job.education_level)
                        for user_education in user_education_qs:
                            education_level_matching_user_profile_id_list.append(user_education.job_profile_id)

                    elif cs.search_criteria == CandidateSearchForJobMasterChoice.LOCATION:
                        job_location = job.location.city.city
                        user_profile_qs = UserProfile.objects.filter(location__city__city__iexact=job_location)
                        for user_profile in user_profile_qs:
                            user_job_profile_obj = UserJobProfile.objects.get(user=user_profile.user)
                            location_matching_user_profile_id_list.append(user_job_profile_obj.pk)

                    else:
                        logger.exception("Job object not found.")
                        raise ICFException(_("Could not find matching jobs. Please contact admin."),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                job_profile_list_1 = get_intersection_of_lists(skill_matching_user_profile_id_list,
                                                               experience_matching_user_profile_id_list)
                job_profile_list_2 = get_intersection_of_lists(education_level_matching_user_profile_id_list,
                                                               location_matching_user_profile_id_list)
                final_job_profile_list = get_intersection_of_lists(job_profile_list_1, job_profile_list_2)
                if final_job_profile_list:
                    final_job_profile_list = final_job_profile_list
                    queryset = UserJobProfile.objects.filter(id__in=final_job_profile_list)
                    return queryset
                else:
                    queryset = UserJobProfile.objects.none()
                    return queryset

        except Job.DoesNotExist as je:
            logger.exception("Job object not found.")
            raise ICFException(_("Something went wrong. Please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except UserJobProfile.DoesNotExist as je:
            logger.exception("UserJobProfile object not found.")
            raise ICFException(_("Something went wrong. Please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.debug(e)
            return Job.objects.none()


class SearchCandidateListMixinForNotification(object):
    def get_queryset(self):
        try:
            # job_slug = self.kwargs.get('slug', None)
            job_slug = self.slug
            if job_slug:
                job = Job.objects.get(slug=job_slug)
                cs_for_job_parameters = CandidateSearchForJobMaster.objects.all()

                skill_matching_user_profile_id_list = []
                education_level_matching_user_profile_id_list = []
                location_matching_user_profile_id_list = []
                for cs in cs_for_job_parameters:
                    if cs.search_criteria == CandidateSearchForJobMasterChoice.SKILL:
                        job_skill_id_qs = JobSkill.objects.filter(job=job).values_list('skill', flat=True)
                        for skill_id in job_skill_id_qs:
                            skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id).values_list(
                                'job_profile',
                                flat=True)
                            for job_profile_id in skill_job_profile_id_qs:
                                skill_matching_user_profile_id_list.append(job_profile_id)

                    elif cs.search_criteria == CandidateSearchForJobMasterChoice.EDUCATION:
                        user_education_qs = UserEducation.objects.filter(education_level=job.education_level)
                        for user_education in user_education_qs:
                            education_level_matching_user_profile_id_list.append(user_education.job_profile_id)

                    elif cs.search_criteria == CandidateSearchForJobMasterChoice.LOCATION:
                        # job_location = job.location.city.city
                        job_country_location = job.location.city.state.country.country
                        user_profile_qs = UserProfile.objects.filter(location__city__state__country__country__iexact=job_country_location)
                        for user_profile in user_profile_qs:
                            user_job_profile_obj = UserJobProfile.objects.get(user=user_profile.user)
                            location_matching_user_profile_id_list.append(user_job_profile_obj.pk)

                    else:
                        logger.exception("Job object not found.")
                        raise ICFException(_("Could not find matching jobs. Please contact admin."),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                union_list = skill_matching_user_profile_id_list + \
                             education_level_matching_user_profile_id_list + \
                             location_matching_user_profile_id_list

                unique_user_profiles = None
                #
                # A set does not contain duplication. The list is converted to a set to remove duplicates
                #
                unique_user_profiles = set(union_list)
                if unique_user_profiles:
                    queryset = UserJobProfile.objects.filter(id__in=unique_user_profiles)
                    return queryset
                else:
                    queryset = UserJobProfile.objects.none()
                    return queryset

            else:
                queryset = UserJobProfile.objects.none()
                return queryset

        except Job.DoesNotExist as je:
            logger.exception("Job object not found.")
            raise ICFException(_("Something went wrong. Please contact admin."),
                       status_code=status.HTTP_400_BAD_REQUEST)

        except UserJobProfile.DoesNotExist as je:
            logger.exception("UserJobProfile object not found.")
            raise ICFException(_("Something went wrong. Please contact admin."),
                       status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.debug(e)
            return Job.objects.none()
