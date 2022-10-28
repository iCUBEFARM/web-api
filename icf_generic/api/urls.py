from django.urls import path, include, re_path
from icf_generic.api.views import SponsoredListView, GetFeaturedVideosListView, GetFeaturedEventsListView, \
    FeaturedEventDetailAPIView, GetSearchFeaturedVideosListView, GetCityAPIView, AboutUsCreateAPIView, \
    CountryAutocomplete, LanguageAutocomplete, GetFAQsView, GetFAQDetailView, GetRelevantFAQListView, \
    FaqCategoryAutocomplete, GetFAQListByCategoryView, GetFAQListByCategorySlugView
from icf_item.api.views import CategoryListView, ItemList

from .views import (
        LanguageList,AddressList,
        CityList,StateList,
        CountryList,CurrencyList
)
urlpatterns = [

    re_path(r'^category/$', CategoryListView.as_view(), name='list'),

    re_path(r'^currencies/$', CurrencyList.as_view(), name="currency-list"),
    re_path(r'^languages/$', LanguageList.as_view(), name="language-list"),
    re_path(r'^addresses/$', AddressList.as_view(), name="address-list"),
    re_path(r'^cities/$', CityList.as_view(), name="city-list"),
    re_path(r'^states/$', StateList.as_view(), name="state-list"),
    re_path(r'^countries/$', CountryList.as_view(), name="country-list"),
    re_path(r'^items/$', ItemList.as_view(),name="item-list"),
    re_path(r'^sponsored/$', SponsoredListView.as_view(),name="sponsored-list"),
    re_path(r'^featured-videos/$', GetFeaturedVideosListView.as_view(), name='featured-videos'),
    re_path(r'^featured-search-videos/$', GetSearchFeaturedVideosListView.as_view(), name='featured-search-videos'),
    re_path(r'^featured-events/$', GetFeaturedEventsListView.as_view(), name='featured-events'),
    re_path(r'^featured-events/(?P<slug>[\w-]+)/$', FeaturedEventDetailAPIView.as_view(), name='featured-event-detail'),
    re_path(r'^faqs/(?P<category_id>\d+)/$', GetFAQListByCategoryView.as_view(), name='FAQ-list'),
    re_path(r'^faqs/(?P<category_slug>[\w-]+)/$', GetFAQListByCategorySlugView.as_view(), name='FAQ-list-by-category-slug'),
    re_path(r'^faqs/$', GetFAQsView.as_view(), name='FAQ-search-list'),
    # re_path(r'^get-relevant-faqs/(?P<faq_slug>[\w-]+)/(?P<faq_category_slug>[\w-]+)/$', GetRelevantFAQListView.as_view(),
    #     name='relevant-faqs'),
    re_path(r'^get-relevant-faqs/(?P<faq_slug>[\w-]+)/$', GetRelevantFAQListView.as_view(),
        name='relevant-faqs'),
    re_path(r'^faq-detail/(?P<slug>[\w-]+)/$', GetFAQDetailView.as_view(), name='faq-detail'),
    re_path(r'^get-city/(?P<pk>\d+)/$', GetCityAPIView.as_view(), name="get-city"),
    re_path(r'^about-us/create/$', AboutUsCreateAPIView.as_view(), name="about-us-create"),
    re_path(r'^country-autocomplete/$', CountryAutocomplete.as_view(), name="country-autocomplete-list"),
    re_path(r'^language-autocomplete/$', LanguageAutocomplete.as_view(), name="language-autocomplete-list"),
    re_path(r'^faq-category-autocomplete/$', FaqCategoryAutocomplete.as_view(), name="faq-category-autocomplete-list"),

]