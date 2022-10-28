from django.urls import path

# from icf_item.api.views import GlobalSearchList
from icf_item.api.views import GlobalSearchList, stats

urlpatterns = [

    path('search/', GlobalSearchList.as_view(), name="global-search"),
    path('stats/', stats, name='Stats'),

]