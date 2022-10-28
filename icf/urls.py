"""icf URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  re_path(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  re_path(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  re_path(r'^blog/', include('blog.urls'))
"""
from django.urls import path, re_path, include
from django.conf.urls import static

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.static import serve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions

from icf import settings
# from icf_generic.api.views import AddQuestionCategoryView
from icf_integrations import views
from drf_yasg.views import get_schema_view as swagger_get_schema_view
from drf_yasg import openapi

schema_view = swagger_get_schema_view(
   openapi.Info(
       title="Icubefarm API",
       default_version='v15.9.1',
       description="Upgrade",
   ),
    public=True,
)

urlpatterns = [
    re_path(r'^$', TemplateView.as_view(template_name="index.html")),
        # re_path(r'^icube-admin/icf_generic/questioncategory/add/$', AddQuestionCategoryView.as_view(), name='add-question-category'),
    re_path(r'^icube-admin/', admin.site.urls),
    path('',
        include([
            path('entity/', include('icf_entity.api.urls')),
            path('jobs/', include('icf_jobs.api.urls')),
            path('generic/', include('icf_generic.api.urls')),
            path('auth/', include('icf_auth.api.urls')),
            path('icube-admin/integrations/send-group-sms/', views.GroupSmsView.as_view(), name='send-group-sms'),

            path('orders/', include('icf_orders.api.urls')),
            path('item/', include('icf_item.api.urls')),
            path('messages/', include('icf_messages.api.urls')),
            path('featuredevents/', include('icf_featuredevents.api.urls')),
            path('events/', include('icf_events.api.urls')),
            path('career-fairs/', include('icf_career_fair.api.urls')),
            path('covid-status/', include('icf_covid_status.api.urls')),
            path('announcements/', include('icf_announcement.api.urls')),

            path('swagger/schema/', schema_view.with_ui('swagger', cache_timeout=0), name="swagger-schema-ui"),
            path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
            path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
        ])
    ),

    re_path(r'^summernote/', include('django_summernote.urls')),

    #re_path(r'^(?:.*)/?$', TemplateView.as_view(template_name="index.html")),
]


""" The urls from """
ui_urlpatterns = [

    re_path(r'^account/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^job/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^entity/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^home/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^info/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^search-result/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^events/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^error/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^featured-videos/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^faq/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^search-result/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^about-us/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^company-pages/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^help/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^cart/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^mmh-careers/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^career-fair/', TemplateView.as_view(template_name="index.html")),
    re_path(r'^career-fair-virtual/', TemplateView.as_view(template_name="index.html")),

]

@api_view(['GET'])
@permission_classes((IsAuthenticated, ))
def protected_serve(request, path, file, document_root=None, show_indexes=False):
    return serve(request, "{}{}".format(path, file), document_root, show_indexes)


urlpatterns += [
    re_path(r'^%s(?P<path>jobs/resumes/)(?P<file>.*)$' % settings.MEDIA_URL[1:], protected_serve, {'document_root': settings.MEDIA_ROOT}),
]


urlpatterns += ui_urlpatterns
urlpatterns += static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


admin.site.site_header = 'iCUBEFARM Administration'

def error404(request, exception):
    return redirect('/error/404');


handler404 = error404;