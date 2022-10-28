from django.urls import path, include, re_path
from django.contrib import admin
from rest_framework.routers import DefaultRouter, SimpleRouter

from icf_announcement.api.views import AnnouncementViewSet


router = DefaultRouter()
draft_router = DefaultRouter()

router.register(r'announcement', AnnouncementViewSet, basename='announcements')

urlpatterns = [
    re_path(r'^', include(router.urls)),
]