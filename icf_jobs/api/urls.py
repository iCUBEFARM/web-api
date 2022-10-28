from django.urls import path, include, re_path
from django.contrib import admin

from icf_entity.api.views import EntityLogoViewSet
from icf_jobs.api.views import (
    GeneralJobListView, JobUpdateView,
    EducationLevelList, OccupationList,
    SalaryFrequencyList, JobTypeList,
    SkillList,
    EntityJobList, JobDetailView,
    UserEducationViewSet, UserWorkExperienceViewSet,
    UserReferenceViewSet, UserSkillsViewSet, RelationShipList, FileUploadViewSet, JobSeekerProfileAPIView,
    FavoriteJobCreate, FavoriteJobDelete, JobApplyCreateView, CheckUserHasJobProfileView, JobAppliedUserList,
    JobAppliedUserStatus, JobMarkForDeleteCreateView, JobDeleteView, JobMarkedForDeleteListView,
    RejectJobMarkedForDeleteRequestView, JobSearchList, JobCloseView, JobDraftPreviewView, DraftJobsViewSet,
    EntityJobDraftList, JobDraftDetailView, JobDraftUpdateView, JobDraftCreateApiView, UnregisteredUploadViewSet,
    UserRelevantLinksViewSet, UserHobbiesViewSet, UserProjectsViewSet, DeleteTaskView, UserResumeCreateAPIView,
    UserResumeEditAPIView, UserResumeCountAPIView,
    UserResumeListAPIView, UserResumeDeleteAPIView, UserResumeComponentCreateAPIView,
    UserResumeDetailAPIView, UserResumeComponentDeleteAPIView, UserResumeStatusUpdateAPIView,
    UserResumeCloneCreateAPIView,
    TaskCreateAPIView, ModifyUserComponentSortOrderAPIView, CountryJobListAPIView, EntityJobCountApiView,
    SearchCandidatesAPIView, SearchCandidatesForJobAPIView, SaveCandidateSearchAPIView, DeleteCandidateSearchAPIView,
    CandidateSearchListAPIView, CandidateSearchBySearchSlugAPIView, CandidateSearchObjectAPIView,
    CandidateSearchUpdateApiView)
from rest_framework.routers import DefaultRouter, SimpleRouter

from .views import JobCreateApiView, UserAwardRecognitionViewSet, UserConferenceWorkshopViewSet, UserCourseViewSet, UserExtraCurricularActivitiesViewSet, UserFreelanceServiceViewSet, UserInfluencerViewSet, UserInterviewQuestionViewSet, UserLicenseCertificationViewSet, UserPreferedCountryViewSet, UserPreferedFunctionalAreaViewSet, UserPreferedIndustryViewSet, UserPreferedJobStaffLevelViewSet, UserPreferedJobTypeViewSet, UserPreferedWageViewSet, UserPreferedWorkSiteTypeViewSet, UserProfessionalMembershipViewSet, UserPublicationViewSet, UserRelevantLinkViewSet, UserVisionMissionViewSet, UserVolunteeringViewSet

router = DefaultRouter()
draft_router = DefaultRouter()
router.register(r'education', UserEducationViewSet, basename='user-education')
router.register(r'work-experience', UserWorkExperienceViewSet, basename='user-work-experience')
router.register(r'conference-workshop', UserConferenceWorkshopViewSet, basename='conference-workshop')
router.register(r'license-certification', UserLicenseCertificationViewSet, basename='license-certification')
router.register(r'courses', UserCourseViewSet, basename='courses')
router.register(r'freelance-Services', UserFreelanceServiceViewSet, basename='freelance-Services')
router.register(r'award-recognition', UserAwardRecognitionViewSet, basename='award-recognition')
router.register(r'interview-question', UserInterviewQuestionViewSet, basename='interview-question')
router.register(r'professional-membership', UserProfessionalMembershipViewSet, basename='professional-membership')
router.register(r'volunteering', UserVolunteeringViewSet, basename='volunteering')
router.register(r'vision-mission', UserVisionMissionViewSet, basename='vision-mission')
router.register(r'relevant-link', UserRelevantLinkViewSet, basename='relevant-link')
router.register(r'influencer', UserInfluencerViewSet, basename='influencer')
router.register(r'publication', UserPublicationViewSet, basename='publication')

router.register(r'prefered-job-type', UserPreferedJobTypeViewSet, basename='prefered-job-type')
router.register(r'prefered-job-staff-level', UserPreferedJobStaffLevelViewSet, basename='prefered-job-staff-level')
router.register(r'prefered-industry', UserPreferedIndustryViewSet, basename='prefered-industry')
router.register(r'prefered-functional-area', UserPreferedFunctionalAreaViewSet, basename='prefered-functional-area')
router.register(r'prefered-worksite-type', UserPreferedWorkSiteTypeViewSet, basename='prefered-worksite-type')
router.register(r'prefered-country', UserPreferedCountryViewSet, basename='prefered-country')
router.register(r'prefered-wage', UserPreferedWageViewSet, basename='prefered-wage')

router.register(r'user-reference', UserReferenceViewSet, basename='user-reference')
router.register(r'user-skills', UserSkillsViewSet, basename='user-skills')
router.register(r'user-relevant-links', UserRelevantLinksViewSet, basename='user-relevant-links')
router.register(r'user-extra-curricular-activities', UserExtraCurricularActivitiesViewSet, basename='user-extra-curricular-activities')
router.register(r'user-hobbies', UserHobbiesViewSet, basename='user-hobbies')
# The Api for the project details
router.register(r'user-projects', UserProjectsViewSet, basename='user-projects')
router.register(r'upload-resume', FileUploadViewSet, basename='file-upload')
router.register(r'unregistered-user-upload-resume', UnregisteredUploadViewSet, basename='unregistered-user-file-upload')
draft_router.register(r'', DraftJobsViewSet, basename='draft-job')


urlpatterns = [
    re_path(r'^', include(router.urls)),
    re_path(r'^search-jobs-list/$', JobSearchList.as_view(), name="job-search-list"),
    re_path(r'^user-resume/create/$', UserResumeCreateAPIView.as_view(), name='create-user-resume'),
    re_path(r'^user-resume/delete/(?P<id>\d+)/$', UserResumeDeleteAPIView.as_view(), name='delete-user-resume'),
    re_path(r'^user-resume-component/delete/(?P<resume_id>\d+)/(?P<object_id>\d+)/(?P<type>[\w-]+)/$',
        UserResumeComponentDeleteAPIView.as_view(), name='delete-user-resume-component'),
    re_path(r'^user-resume/edit/$', UserResumeEditAPIView.as_view(), name='edit-user-resume'),
    re_path(r'^user-resume/detail/(?P<slug>[\w-]+)/$', UserResumeDetailAPIView.as_view(), name='user-resume-detail'),
    re_path(r'^user-resume-component/create/$', UserResumeComponentCreateAPIView.as_view(),
        name='create-user-resume-component'),
    re_path(r'^save-user-resume/(?P<resume_id>\d+)/$', UserResumeStatusUpdateAPIView.as_view(),
        name='update-user-resume-status'),
    re_path(r'^task/create/$', TaskCreateAPIView.as_view(), name='add-task'),
    re_path(r'^clone-user-resume/(?P<slug>[\w-]+)/$', UserResumeCloneCreateAPIView.as_view(),
        name='clone-user-resume'),
    re_path(r'^get-user-resume-list/$', UserResumeListAPIView.as_view(), name='get-user-resume-list'),
    re_path(r'^get-user-resume-count/$', UserResumeCountAPIView.as_view(), name='get-user-resume-count'),

    re_path(r'^save-search/(?P<entity_slug>[\w-]+)/$', SaveCandidateSearchAPIView.as_view(),
        name='save-candidate-search'),
    re_path(r'^update-search/(?P<search_slug>[\w-]+)/$', CandidateSearchUpdateApiView.as_view(),
        name='update-candidate-search'),
    re_path(r'^delete-candidate-search/(?P<search_slug>[\w-]+)/$', DeleteCandidateSearchAPIView.as_view(),
        name='delete-candidate-search'),
    re_path(r'^candidate-search-list/(?P<entity_slug>[\w-]+)/$', CandidateSearchListAPIView.as_view(),
        name='candidate-search-list'),
    re_path(r'^candidate-search/(?P<search_slug>[\w-]+)/$', CandidateSearchBySearchSlugAPIView.as_view(),
        name='candidate-search-by-search-slug'),
    re_path(r'^get-candidate-search-object/(?P<search_slug>[\w-]+)/$', CandidateSearchObjectAPIView.as_view(),
        name='search-obj-by-search-slug'),

    re_path(r'^(?P<entity_slug>[\w-]+)/create/$', JobCreateApiView.as_view(), name='job-create'),
    re_path(r'^list/$', GeneralJobListView.as_view(), name='list'),
    re_path(r'^education-levels/$', EducationLevelList.as_view(), name="educationlevel-list"),
    re_path(r'^occupations/$', OccupationList.as_view(), name="occupation-list"),
    re_path(r'^salary-frequencies/$', SalaryFrequencyList.as_view(), name="salaryfrequency-list"),
    re_path(r'^job-types/$', JobTypeList.as_view(), name="jobtype-list"),
    re_path(r'^skills/$', SkillList.as_view(), name="skill-type-list"),
    re_path(r'^relationship/$', RelationShipList.as_view(), name='realtionship-list'),
    re_path(r'^jobseeker/profile/$', JobSeekerProfileAPIView.as_view(), name='jobseeker-profile'),
    re_path(r'^jobseeker/profile_exists/$', CheckUserHasJobProfileView.as_view(), name='jobseeker-profile-exists'),
    re_path(r'^favorite/$', FavoriteJobCreate.as_view(), name='favorite-job'),
    re_path(r'^favorite/(?P<id>\d+)/$', FavoriteJobDelete.as_view(), name='favorite-job-delete'),
    re_path(r'^apply/$', JobApplyCreateView.as_view(), name='apply-job'),
    re_path(r'^list/(?P<slug>[\w-]+)/$', EntityJobList.as_view(), name='entityjob-list'),
    re_path(r'^entity-job-count/(?P<entity_slug>[\w-]+)/$', EntityJobCountApiView.as_view(), name='entity-job-count'),
    re_path(r'^country-job-list/(?P<ministry>[\w\s]+)/(?P<country>[\w\s]+)/$', CountryJobListAPIView.as_view(),
        name='country-job-list'),

    re_path(r'^(?P<slug>[\w-]+)/mark-for-delete/$', JobMarkForDeleteCreateView.as_view(),
        name='mark-for-delete-job'),
    re_path(r'^(?P<slug>[\w-]+)/delete/$', JobDeleteView.as_view(), name='delete-job'),
    re_path(r'^(?P<slug>[\w-]+)/close/$', JobCloseView.as_view(), name='close-job'),
    re_path(r'^(?P<entity_slug>[\w-]+)/jobs-marked-for-delete/$', JobMarkedForDeleteListView.as_view(),
        name='jobs-marked-for-delete-list'),
    re_path(r'^(?P<slug>[\w-]+)/reject-job-marked-for-delete-request/$', RejectJobMarkedForDeleteRequestView.as_view(),
        name='reject-job-marked-for-delete-request'),
    re_path(r'^(?P<slug>[\w-]+)/$', JobDetailView.as_view(), name='job-detail'),
    re_path(r'^(?P<slug>[\w-]+)/edit/$', JobUpdateView.as_view(), name='update-job'),
    re_path(r'^(?P<slug>[\w-]+)/applied-user/$', JobAppliedUserList.as_view(), name='applied-user-list'),
    re_path(r'^user-status/(?P<job_slug>[\w-]+)/(?P<user_slug>[\w-]+)/$', JobAppliedUserStatus.as_view(),
        name='applied-user-status'),
    re_path(r'^(?P<slug>[\w-]+)/(?P<job_slug>[\w-]+)/preview/$', JobDraftPreviewView.as_view(), name='job-preview'),
    re_path(r'^(?P<entity_slug>[\w-]+)/draft/', include(draft_router.urls)),
    re_path(r'^draft/(?P<entity_slug>[\w-]+)/create/$', JobDraftCreateApiView.as_view(), name='draft-create'),
    re_path(r'^draft/list/(?P<slug>[\w-]+)/$', EntityJobDraftList.as_view(), name='entity-draft-job-list'),
    re_path(r'^draft/(?P<slug>[\w-]+)/$', JobDraftDetailView.as_view(), name='draft-job-detail'),
    re_path(r'^draft/(?P<slug>[\w-]+)/edit/$', JobDraftUpdateView.as_view(), name='draft-update-job'),
    re_path(r'^delete-task/(?P<work_exp_id>\d+)/(?P<task_id>\d+)/$', DeleteTaskView.as_view(),
        name='delete-project-task'),
    re_path(r'^user-component/sort-order/$', ModifyUserComponentSortOrderAPIView.as_view(),
        name='modify-user-component-order'),
    re_path(r'^candidate-global-search/(?P<entity_slug>[\w-]+)/(?P<slug>[\w-]+)/$', SearchCandidatesAPIView.as_view(),
        name='modify-user-component-order'),
    re_path(r'^candidate-job-search/(?P<slug>[\w-]+)/$', SearchCandidatesForJobAPIView.as_view(),
        name='candidate-search-job'),


]
