from django.urls import path, include, re_path
from django.contrib import admin

from rest_framework.routers import DefaultRouter

from icf_events.api.views import EventCreateApiView, GeneralEventListView, EntityEventList, \
    EventMarkForDeleteCreateView, \
    RejectEventMarkedForDeleteRequestView, EventMarkedForDeleteListView, EventDeleteView, EventCloseView, \
    EventDetailView, EventUpdateView, EventDraftPreviewView, EventDraftCreateApiView, EntityEventDraftList, \
    EventDraftDetailView, EventDraftUpdateView, EventGalleryViewSet, StatsEventListView, UpcomingEventsListView, \
    PastEventsListView, \
    EventDraftGalleryViewSet, EventDraftCloneCreateApiView, EntityEventListCountView, SaveParticipantSearchAPIView, \
    ParticipantSearchUpdateApiView, DeleteParticipantSearchAPIView, ParticipantSearchListAPIView, \
    ParticipantSearchBySearchSlugAPIView, ParticipantSearchObjectAPIView

router = DefaultRouter()

router.register(r'gallery-images', EventGalleryViewSet, basename='event-gallery')
router.register(r'gallery-images-draft', EventDraftGalleryViewSet, basename='event-draft-gallery')


urlpatterns = [
    re_path(r'^', include(router.urls)),
    # re_path(r'^event-categories/list/$', EventCategoryListView.as_view(), name="event-category-list"),
    re_path(r'^upcoming-events/list/$', UpcomingEventsListView.as_view(), name='upcoming-events'),
    re_path(r'^past-events/list/$', PastEventsListView.as_view(), name='past-events'),
    re_path(r'^(?P<entity_slug>[\w-]+)/create/$', EventCreateApiView.as_view(), name='create'),
    re_path(r'^list/$', GeneralEventListView.as_view(), name='list'),
    re_path(r'^list/(?P<entity_slug>[\w-]+)/$', EntityEventList.as_view(), name='entity-event-list'),
    re_path(r'^event-list-count/(?P<entity_slug>[\w-]+)/$', EntityEventListCountView.as_view(),
        name='entity-event-list-count'),
    re_path(r'^(?P<slug>[\w-]+)/mark-for-delete/$', EventMarkForDeleteCreateView.as_view(),
        name='mark-for-delete-event'),
    re_path(r'^(?P<entity_slug>[\w-]+)/events-marked-for-delete/$', EventMarkedForDeleteListView.as_view(),
        name='events-marked-for-delete-list'),
    re_path(r'^(?P<slug>[\w-]+)/reject-event-marked-for-delete-request/$', RejectEventMarkedForDeleteRequestView.as_view(),
        name='reject-event-marked-for-delete-request'),
    re_path(r'^(?P<slug>[\w-]+)/delete/$', EventDeleteView.as_view(), name='delete-event'),
    re_path(r'^(?P<slug>[\w-]+)/close/$', EventCloseView.as_view(), name='close-event'),
    re_path(r'^detail/(?P<slug>[\w-]+)/$', EventDetailView.as_view(), name='event-detail'),
    re_path(r'^(?P<slug>[\w-]+)/edit/$', EventUpdateView.as_view(), name='update-event'),
    re_path(r'^(?P<entity_slug>[\w-]+)/(?P<event_slug>[\w-]+)/preview/$', EventDraftPreviewView.as_view(), name='event-preview'),
    # re_path(r'^(?P<entity_slug>[\w-]+)/draft/', include(draft_router.urls)),
    re_path(r'^(?P<entity_slug>[\w-]+)/(?P<slug>[\w-]+)/', include(router.urls)),
    re_path(r'^(?P<entity_slug>[\w-]+)/(?P<slug>[\w-]+)/', include(router.urls)),
    re_path(r'^create/clone/(?P<entity_slug>[\w-]+)/(?P<event_slug>[\w-]+)/$', EventDraftCloneCreateApiView.as_view(),
        name='draft-create-clone'),
    re_path(r'^(?P<entity_slug>[\w-]+)/create/draft/$', EventDraftCreateApiView.as_view(), name='draft-create'),
    re_path(r'^draft/list/(?P<slug>[\w-]+)/$', EntityEventDraftList.as_view(), name='entity-draft-event-list'),
    re_path(r'^detail/(?P<slug>[\w-]+)/draft/$', EventDraftDetailView.as_view(), name='draft-event-detail'),
    re_path(r'^draft/(?P<slug>[\w-]+)/edit/$', EventDraftUpdateView.as_view(), name='draft-update-event'),

    re_path(r'^save-search/(?P<entity_slug>[\w-]+)/$', SaveParticipantSearchAPIView.as_view(),
            name='save-participant-search'),
    re_path(r'^update-search/(?P<search_slug>[\w-]+)/$', ParticipantSearchUpdateApiView.as_view(),
            name='update-participant-search'),
    re_path(r'^delete-participant-search/(?P<search_slug>[\w-]+)/$', DeleteParticipantSearchAPIView.as_view(),
            name='delete-participant-search'),
    re_path(r'^participant-search-list/(?P<entity_slug>[\w-]+)/$', ParticipantSearchListAPIView.as_view(),
            name='participant-search-list'),
    re_path(r'^participant-search/(?P<search_slug>[\w-]+)/$', ParticipantSearchBySearchSlugAPIView.as_view(),
            name='participant-search-by-search-slug'),
    re_path(r'^get-participant-search-object/(?P<search_slug>[\w-]+)/$', ParticipantSearchObjectAPIView.as_view(),
            name='search-obj-by-search-slug'),
]