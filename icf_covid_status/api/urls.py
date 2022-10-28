from django.urls import path, include, re_path
from django.contrib import admin

from icf_entity.api.views import EntityLogoViewSet

from .views import EGSectorListAPIView, CurrentWorkStatusListAPIView, CurrentCompensationListAPIView, \
    UserWorkStatusCreateAPIView, CheckIfUserHasWorkStatusAPIView

urlpatterns = [

    re_path(r'^eg-sectors/$', EGSectorListAPIView.as_view(), name="currency-list"),
    re_path(r'^current-work-statuses/$', CurrentWorkStatusListAPIView.as_view(), name="language-list"),
    re_path(r'^current-compensation-statuses/$', CurrentCompensationListAPIView.as_view(), name="language-list"),
    re_path(r'^check_user-work-status/$', CheckIfUserHasWorkStatusAPIView.as_view(), name='check_user-work-status'),
    re_path(r'^user-work-status/create/$', UserWorkStatusCreateAPIView.as_view(), name='create-user-resume'),


]
