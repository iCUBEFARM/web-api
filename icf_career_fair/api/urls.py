from django.urls import path, include, re_path

from django.contrib import admin

from rest_framework.routers import DefaultRouter

from .views import CareerFairCreateApiView, CareerFairDraftCreateApiView, CareerFairDraftUpdateView, \
    CareerFairDraftDetailView, CareerFairForUserApiView, EntityCareerFairDraftList, CareerFairDraftPreviewView, CareerFairDetailView, \
    GeneralCareerFairListView, EntityCareerFairListApiView, EntityCareerFairCountApiView, CareerFairUpdateView, \
    SpeakerProfileImageViewSet, SpeakerProfileImageOptionalViewSet, CareerFairDraftGalleryViewSet, \
    CareerFairGalleryViewSet, CareerFairMarkForDeleteCreateApiView, CareerFairDeleteApiView, CareerFairCloseView, \
    RejectCareerFairMarkedForDeleteRequestView, CareerFairMarkedForDeleteListView, get_career_fair_sub_types, \
    get_career_fair_product_types, get_career_fair_product_buyer_types, UpcomingCareerFairsByEntityListApiView, \
    PastCareerFairsByEntityListApiView, ActiveCareerFairsByEntityListApiView, UpcomingCareerFairsListApiView, \
    PastCareerFairsListApiView, CareerFairProductsByBuyerTypeListApiView, CareerFairDirectUpdateApiView, \
    CareerFairDraftDirectDeleteApiView, CareerFairSpeakerListApiView, SessionDraftDetailView, SupportDraftDetailView, \
    SpeakerDraftDetailView, SessionDetailView, SupportDetailView, SpeakerDetailView, SessionListByCareerFairView, \
    SupportListByCareerFairView, SpeakerListByCareerFairView, SessionDraftListByCareerFairView, \
    SupportDraftListByCareerFairView, SpeakerDraftListByCareerFairView, SupportLogoViewSet, SupportOptionalLogoViewSet, \
    CareerFairSalesReportView, CareerFairTestSpeakerView, SearchCandidatesForCareerFairAPIView, \
    CareerFairOptionalImageViewSet, CareerFairImageViewSet, CareerFairEntityListApiView, \
    IsUserCareerFairParticipantView, EntityHasCareerfairAd, EntityCareerFairAdvertisementListApiView, \
    CareerFairSubmitAdvertisementApiView, CareerFairAdvertisementListApiView

router = DefaultRouter()
draft_router = DefaultRouter()


support_logo_router = DefaultRouter()
support_logo_router.register(r'support-logo', SupportLogoViewSet, basename='support-logo')

support_logo_optional_router = DefaultRouter()
support_logo_optional_router.register(r'support-optional-logo', SupportOptionalLogoViewSet, basename='support-optional-logo')

career_fair_optional_images_router = DefaultRouter()
career_fair_optional_images_router.register(r'career-fair-optional-image', CareerFairOptionalImageViewSet, basename='career-fair-optional-image')

career_fair_images_router = DefaultRouter()
career_fair_images_router.register(r'career-fair-image', CareerFairImageViewSet, basename='career-fair-image')

speaker_profile_image_router = DefaultRouter()
speaker_profile_image_router.register(r'speaker-image', SpeakerProfileImageViewSet, basename='speaker-profile-Image')

speaker_profile_image_optional_router = DefaultRouter()
speaker_profile_image_optional_router.register(r'speaker-image-optional', SpeakerProfileImageOptionalViewSet, basename='speaker-profile-Image-optional')

career_fair_gallery_router = DefaultRouter()
career_fair_gallery_router.register(r'^gallery-images', CareerFairGalleryViewSet, basename='career-fair-gallery')

career_fair_draft_gallery_router = DefaultRouter()
career_fair_draft_gallery_router.register(r'^gallery-images-draft', CareerFairDraftGalleryViewSet, basename='career-fair-draft-gallery')


# router.register(r'education', UserEducationViewSet, basename='user-education')
# router.register(r'work-experience', UserWorkExperienceViewSet, basename='user-work-experience')
# router.register(r'user-reference', UserReferenceViewSet, basename='user-reference')
# router.register(r'user-skills', UserSkillsViewSet, basename='user-skills')
# router.register(r'user-relevant-links', UserRelevantLinksViewSet, basename='user-relevant-links')
# router.register(r'user-hobbies', UserHobbiesViewSet, basename='user-hobbies')
# # The Api for the project details
# router.register(r'user-projects', UserProjectsViewSet, basename='user-projects')
# router.register(r'upload-resume', FileUploadViewSet, basename='file-upload')
# router.register(r'unregistered-user-upload-resume', UnregisteredUploadViewSet, basename='unregistered-user-file-upload')
# draft_router.register(r'', DraftCareerFairsViewSet, basename='draft-career-fairs')


urlpatterns = [
    re_path(r'^', include(router.urls)),
    path('my-career-fair-events/', CareerFairForUserApiView.as_view(), name='career-events'),

    # re_path(r'^search-jobs-list/$', JobSearchList.as_view(), name="job-search-list"),
    # re_path(r'^user-resume/delete/(?P<id>\d+)/$', UserResumeDeleteAPIView.as_view(), name='delete-user-resume'),
    # re_path(r'^user-resume-component/delete/(?P<resume_id>\d+)/(?P<object_id>\d+)/(?P<type>[\w-]+)/$',
    #     UserResumeComponentDeleteAPIView.as_view(), name='delete-user-resume-component'),
    # re_path(r'^user-resume/edit/$', UserResumeEditAPIView.as_view(), name='edit-user-resume'),
    # re_path(r'^user-resume/detail/(?P<slug>[\w-]+)/$', UserResumeDetailAPIView.as_view(), name='user-resume-detail'),
    # re_path(r'^user-resume-component/create/$', UserResumeComponentCreateAPIView.as_view(),
    #     name='create-user-resume-component'),
    # re_path(r'^save-user-resume/(?P<resume_id>\d+)/$', UserResumeStatusUpdateAPIView.as_view(),
    #     name='update-user-resume-status'),
    # re_path(r'^task/create/$', TaskCreateAPIView.as_view(), name='add-task'),
    # re_path(r'^clone-user-resume/(?P<slug>[\w-]+)/$', UserResumeCloneCreateAPIView.as_view(),
    #     name='clone-user-resume'),
    # re_path(r'^get-user-resume-list/$', UserResumeListAPIView.as_view(), name='get-user-resume-list'),
    # re_path(r'^get-user-resume-count/$', UserResumeCountAPIView.as_view(), name='get-user-resume-count'),

    # re_path(r'^save-search/(?P<entity_slug>[\w-]+)/$', SaveCandidateSearchAPIView.as_view(),
    #     name='save-candidate-search'),
    # re_path(r'^update-search/(?P<search_slug>[\w-]+)/$', CandidateSearchUpdateApiView.as_view(),
    #     name='update-candidate-search'),
    # re_path(r'^delete-candidate-search/(?P<search_slug>[\w-]+)/$', DeleteCandidateSearchAPIView.as_view(),
    #     name='delete-candidate-search'),
    # re_path(r'^candidate-search-list/(?P<entity_slug>[\w-]+)/$', CandidateSearchListAPIView.as_view(),
    #     name='candidate-search-list'),
    # re_path(r'^candidate-search/(?P<search_slug>[\w-]+)/$', CandidateSearchBySearchSlugAPIView.as_view(),
    #     name='candidate-search-by-search-slug'),
    # re_path(r'^get-candidate-search-object/(?P<search_slug>[\w-]+)/$', CandidateSearchObjectAPIView.as_view(),
    #     name='search-obj-by-search-slug'),


    re_path(r'^upcoming-career-fairs/list/$', UpcomingCareerFairsListApiView.as_view(), name='upcoming-career-fairs'),
    re_path(r'^past-career-fairs/list/$', PastCareerFairsListApiView.as_view(), name='past-career-fairs'),
    re_path(r'^(?P<entity_slug>[\w-]+)/create/$', CareerFairCreateApiView.as_view(), name='create'),
    re_path(r'^upcoming-career-fairs/(?P<entity_slug>[\w-]+)/list/$', UpcomingCareerFairsByEntityListApiView.as_view(), name='upcoming-career-fairs-by-entity'),
    re_path(r'^past-career-fairs/(?P<entity_slug>[\w-]+)/list/$', PastCareerFairsByEntityListApiView.as_view(), name='past-career-fairs-by-entity'),
    re_path(r'^active-career-fairs/(?P<entity_slug>[\w-]+)/list/$', ActiveCareerFairsByEntityListApiView.as_view(), name='past-career-fairs-by-entity'),
    re_path(r'^list/$', GeneralCareerFairListView.as_view(), name='list'),
    re_path(r'^career-fair-products-by-buyer-type/(?P<slug>[\w-]+)/(?P<buyer_type_id>\d+)/$', CareerFairProductsByBuyerTypeListApiView.as_view(), name="career-fairs-products-by-buyer-type"),
    re_path(r'^entity-list/(?P<career_fair_slug>[\w-]+)/$', CareerFairEntityListApiView.as_view(), name="buyer-type-entity-list-career-fair"),
    re_path(r'^(?P<career_fair_slug>[\w-]+)/is-participant/$', IsUserCareerFairParticipantView.as_view(), name='is-career-fair-participant'),


    # re_path(r'^career-fair-product-types/$', get_career_fair_product_types, name="product-type-list"),
    # re_path(r'^career-fair-modes/$', get_mode_of_career_fair_types, name="product-type-list"),
    # re_path(r'^career-fair-product-buyer-types/$', get_career_fair_product_buyer_types, name="product-buyer-type-list"),
    # re_path(r'^career-fair-product-subtypes/$', get_career_fair_sub_types, name="product-sub-type-list"),
    re_path(r'^list/(?P<slug>[\w-]+)/$', EntityCareerFairListApiView.as_view(), name='entity-career-fair-list'),
    re_path(r'^entity-career-fair-count/(?P<entity_slug>[\w-]+)/$', EntityCareerFairCountApiView.as_view(), name='entity-career-fair-count'),

    #
    re_path(r'^(?P<slug>[\w-]+)/mark-for-delete/$', CareerFairMarkForDeleteCreateApiView.as_view(),
        name='mark-for-delete-carer-fair'),
    re_path(r'^(?P<slug>[\w-]+)/delete/$', CareerFairDeleteApiView.as_view(), name='delete-career-fair'),
    re_path(r'^(?P<slug>[\w-]+)/direct-delete/$', CareerFairDirectUpdateApiView.as_view(), name='delete-direct-career-fair'),
    re_path(r'^(?P<slug>[\w-]+)/close/$', CareerFairCloseView.as_view(), name='close-career-fair'),
    re_path(r'^(?P<entity_slug>[\w-]+)/career-fairs-marked-for-delete/$', CareerFairMarkedForDeleteListView.as_view(),
        name='career-fairs-marked-for-delete-list'),
    re_path(r'^(?P<slug>[\w-]+)/reject-career-fairs-marked-for-delete-request/$', RejectCareerFairMarkedForDeleteRequestView.as_view(),
        name='reject-career-fairs-marked-for-delete-request'),
    re_path(r'^session/(?P<slug>[\w-]+)/$', SessionDetailView.as_view(), name='session-detail'),
    re_path(r'^support/(?P<slug>[\w-]+)/$', SupportDetailView.as_view(), name='support-detail'),
    re_path(r'^speaker/(?P<slug>[\w-]+)/$', SpeakerDetailView.as_view(), name='speaker-detail'),

    re_path(r'^(?P<career_fair_slug>[\w-]+)/sessions/$', SessionListByCareerFairView.as_view(), name='career-fair-sessions'),
    re_path(r'^(?P<career_fair_slug>[\w-]+)/supports/$', SupportListByCareerFairView.as_view(), name='career-fair-supports'),
    re_path(r'^(?P<career_fair_slug>[\w-]+)/speakers/$', SpeakerListByCareerFairView.as_view(), name='career-fair-speakers'),

    re_path(r'^(?P<slug>[\w-]+)/career-fair-ads/$', EntityCareerFairAdvertisementListApiView.as_view(),
        name='entity-career-fair-ad-list'),
    re_path(r'^entity-has-career-fair-ad/$', EntityHasCareerfairAd.as_view(), name='entity-has-career-fair-advertisement'),
    re_path(r'^(?P<slug>[\w-]+)/submit-career-fair-ad/$', CareerFairSubmitAdvertisementApiView.as_view(),
        name='submit-career-fair-advertisement'),
    re_path(r'^(?P<slug>[\w-]+)/get-career-fair-ads/$', CareerFairAdvertisementListApiView.as_view(),
        name='career-fair-view-ad-list'),

    re_path(r'^draft/(?P<slug>[\w-]+)/$', CareerFairDraftDetailView.as_view(), name='draft-career-fair-detail'),
    re_path(r'^(?P<slug>[\w-]+)/$', CareerFairDetailView.as_view(), name='career-fair-detail'),
    re_path(r'^(?P<slug>[\w-]+)/edit/$', CareerFairUpdateView.as_view(), name='update-career-fair'),
    re_path(r'^(?P<slug>[\w-]+)/', include(speaker_profile_image_router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/', include(support_logo_router.urls)),
    re_path(r'^draft/(?P<slug>[\w-]+)/', include(career_fair_optional_images_router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/', include(career_fair_images_router.urls)),



    # re_path(r'^(?P<slug>[\w-]+)/applied-user/$', JobAppliedUserList.as_view(), name='applied-user-list'),
    # re_path(r'^user-status/(?P<job_slug>[\w-]+)/(?P<user_slug>[\w-]+)/$', JobAppliedUserStatus.as_view(),
    #     name='applied-user-status'),
    # re_path(r'^draft/speaker/$', CareerFairTestSpeakerView.as_view(), name='draft-update-career-fair-test'),
    # re_path(r'^draft/(?P<slug>[\w-]+)/$', CareerFairDraftDetailView.as_view(), name='draft-career-fair-detail'),
    re_path(r'^(?P<slug>[\w-]+)/(?P<career_fair_slug>[\w-]+)/preview/$', CareerFairDraftPreviewView.as_view(),
        name='career-fair-preview'),
    re_path(r'^(?P<slug>[\w-]+)/(?P<career_fair_slug>[\w-]+)/sales-report/$', CareerFairSalesReportView.as_view(),
        name='career-fair-sales-report'),
    # re_path(r'^(?P<slug>[\w-]+)/(?P<career_fair_slug>[\w-]+)/participants/$', CareerFairParticipantsView.as_view(),
    #     name='career-fair-sales-report'),
    re_path(r'^(?P<entity_slug>[\w-]+)/draft/', include(draft_router.urls)),
    re_path(r'^(?P<entity_slug>[\w-]+)/(?P<slug>[\w-]+)/', include(career_fair_gallery_router.urls)),
    re_path(r'^(?P<entity_slug>[\w-]+)/(?P<slug>[\w-]+)/', include(career_fair_draft_gallery_router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/draft/', include(speaker_profile_image_optional_router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/draft/', include(support_logo_optional_router.urls)),
    re_path(r'^draft/(?P<entity_slug>[\w-]+)/create/$', CareerFairDraftCreateApiView.as_view(), name='draft-create'),
    # re_path(r'^draft/(?P<slug>[\w-]+)/test-retrieve/$', CareerFairDraftRetrieveTestView.as_view(), name='draft-test-retrieve'),

    re_path(r'^draft/(?P<slug>[\w-]+)/edit/$', CareerFairDraftUpdateView.as_view(), name='draft-update-career-fair'),
    re_path(r'^draft/(?P<slug>[\w-]+)/direct-delete/$', CareerFairDraftDirectDeleteApiView.as_view(),
        name='delete-direct-career-fair'),
    re_path(r'^draft/list/(?P<slug>[\w-]+)/$', EntityCareerFairDraftList.as_view(), name='entity-draft-career-fair-list'),
    # re_path(r'^draft/(?P<slug>[\w-]+)/$', CareerFairDraftDetailView.as_view(), name='draft-career-fair-detail'),
    re_path(r'^draft/session/(?P<slug>[\w-]+)/$', SessionDraftDetailView.as_view(), name='draft-session-detail'),
    re_path(r'^draft/support/(?P<slug>[\w-]+)/$', SupportDraftDetailView.as_view(), name='draft-support-detail'),
    re_path(r'^draft/speaker/(?P<slug>[\w-]+)/$', SpeakerDraftDetailView.as_view(), name='draft-speaker-detail'),

    re_path(r'^(?P<career_fair_slug>[\w-]+)/draft/sessions/$', SessionDraftListByCareerFairView.as_view(), name='career-fair-draft-sessions'),
    re_path(r'^(?P<career_fair_slug>[\w-]+)/draft/supports/$', SupportDraftListByCareerFairView.as_view(), name='career-fair-draft-supports'),
    re_path(r'^(?P<career_fair_slug>[\w-]+)/draft/speakers/$', SpeakerDraftListByCareerFairView.as_view(), name='career-fair-draft-speakers'),
    re_path(r'^candidate-global-search/(?P<entity_slug>[\w-]+)/(?P<slug>[\w-]+)/$', SearchCandidatesForCareerFairAPIView.as_view(),
        name='candidate-global-search-career-fair'),


]
