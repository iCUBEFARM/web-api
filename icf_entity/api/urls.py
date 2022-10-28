from django.urls import path, include, re_path
from django.contrib import admin
from rest_framework import routers
from rest_framework.routers import DefaultRouter, SimpleRouter

from icf_entity.api.views import (
    EntityDetailAPIView,
    EntityUpdateAPIView,
    IndustryList,
    SectorList,
    CompanySizeList,
    IsRegisteredUserView,
    EntityUserListCreateView, EntityUserRetrieveDestroyAPIView, EntityLogoViewSet, EntityListView, UserEntityList,
    GetFeaturedEntity, EntityPermRetrieveUpdateDestroyAPIView, EntityPermListView, EntitySetPermView,
    EntityRemovePermView, GeneralEntityListView, EntityDashboardRetrieveView, EntitySearchList, GetIndustryAPIView,
    EntityUserAcceptCreateView, EntityUserRejectView, UserWithCreateJobPermissionEntityList, MarkEntityInactiveAPIView,
    NewEntityCreateAPIView, EntityBrochureViewSet, EntityPromoVideoViewSet)
from .views import EnergyEGEntityList, EntityCreateAPIView, StatsEntityListView

router = DefaultRouter()
router.register(r'', EntityLogoViewSet, basename='logo')

brochure_router = DefaultRouter()
brochure_router.register(r'', EntityBrochureViewSet, basename='entity-brochure' )

promotional_video_router = DefaultRouter()
promotional_video_router.register(r'', EntityPromoVideoViewSet, basename='entity-promotional-video')

urlpatterns = [
    re_path(r'^create/$', EntityCreateAPIView.as_view(), name='entity-create'),
    re_path(r'^new-create/$', NewEntityCreateAPIView.as_view(), name='new-entity-create'),
    re_path(r'^list/$', GeneralEntityListView.as_view(), name='list'),
    re_path(r'^energy-sector-equatorial-guinea/$', EnergyEGEntityList.as_view(), name='list'),
    re_path(r'^search-entity-list/$', EntitySearchList.as_view(), name="entity-search-list"),
    re_path(r'^industries/$', IndustryList.as_view(), name="industry-list"),
    re_path(r'^sectors/$', SectorList.as_view(), name="sector-list"),
    re_path(r'^company-sizes/$', CompanySizeList.as_view(), name="companysize-list"),
    re_path(r'^my-entities/$', UserEntityList.as_view(), name='my-entity'),
    re_path(r'^my-entities-create-job-permission/$', UserWithCreateJobPermissionEntityList.as_view(), name='my-entity-with-create-job-permission'),
    re_path(r'^featured-entity/$', GetFeaturedEntity.as_view(), name='featured-entity'),
    re_path(r'^list/(?P<slug>[\w-]+)/$', EntityListView.as_view(), name='entity-list'),
    re_path(r'^mark-entity-inactive/(?P<slug>[\w-]+)/$', MarkEntityInactiveAPIView.as_view(), name='mark-entity-inactive'),
    re_path(r'^(?P<slug>[\w-]+)/perms/$', EntityPermListView.as_view(), name='all_entity_permissions'),
    re_path(r'^(?P<slug>[\w-]+)/set-perm/$', EntitySetPermView.as_view(), name='set_permissions'),
    re_path(r'^(?P<slug>[\w-]+)/remove-perm/$', EntityRemovePermView.as_view(), name='remove_permissions'),
    re_path(r'^(?P<slug>[\w-]+)/$', EntityDetailAPIView.as_view(), name='entity-detail'),
    re_path(r'^(?P<slug>[\w-]+)/edit/$', EntityUpdateAPIView.as_view(), name='entity-update'),
    re_path(r'^(?P<slug>[\w-]+)/check-user/$', IsRegisteredUserView.as_view(), name='check_user'),
    re_path(r'^(?P<slug>[\w-]+)/users/$', EntityUserListCreateView.as_view(), name='entity_user_list_create'),
    re_path(r'^(?P<slug>[\w-]+)/accept-add-user/(?P<user_slug>[\w-]+)/$', EntityUserAcceptCreateView.as_view(), name='entity_user_accept_create'),
    re_path(r'^(?P<slug>[\w-]+)/reject-add-user/(?P<user_slug>[\w-]+)/$', EntityUserRejectView.as_view(), name='entity_user_reject_create'),
    re_path(r'^(?P<slug>[\w-]+)/users/(?P<user_slug>[\w-]+)/$',
        EntityUserRetrieveDestroyAPIView.as_view(), name='entity_user_retrieve_update'),
    re_path(r'^(?P<slug>[\w-]+)/logos/', include(router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/brochure/', include(brochure_router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/promotional-video/', include(promotional_video_router.urls)),
    re_path(r'^(?P<slug>[\w-]+)/dashboard/$', EntityDashboardRetrieveView.as_view(), name='entity-dashboard'),
    re_path(r'^get-industry/(?P<pk>\d+)/$', GetIndustryAPIView.as_view(), name="get-industry"),
    # re_path(r'^get-industry-sector-by-ministry/(?P<ministry>[\w\s]+)/(?P<country>[\w\s]+)/$',
    #     GetIndustrySectorsByMinistryAndCountryAPIView.as_view(), name="get-industry-sector-by-ministry-country"),
    # re_path(r'^(?P<slug>[\w-]+)/add-user/$', EntityAddUserAPIView.as_view(), name='add_user'),
]


