from django.urls import path, include, re_path

from icf_featuredevents.api.views import GetFeaturedEventsListView, FeaturedEventDetailAPIView, \
    FeaturedEventGalleryDetailAPIView, UpcomingFeaturedEventsListAPIView, PastFeaturedEventsListAPIView, \
    GetRelatedProductListView, \
    TermsAndConditionsByFeaturedEventAPIView, GetLatestFeaturedEventView, EmailFailedEventsPaypalTrasactionsAPIView, \
    GenerateInvoiceForPurchaseTicketsAPIView, FeaturedEventProductsListAPIView

urlpatterns = [

    re_path(r'^featured-events/$', GetFeaturedEventsListView.as_view(), name='featured-events'),
    re_path(r'^get-latest-featured-event/$', GetLatestFeaturedEventView.as_view(), name='get-latest-featured-event'),
    re_path(r'^featured-events/(?P<slug>[\w-]+)/$', FeaturedEventDetailAPIView.as_view(), name='featured-event-detail'),
    # re_path(r'^get-related-categories/(?P<slug>[\w-]+)/$', FeaturedEventRelatedCategoriesListAPIView.as_view(), name='featured-event-category-list'),
    re_path(r'^get_featured-events-gallery/$', FeaturedEventGalleryDetailAPIView.as_view(), name='featured-event-gallery-detail'),
    re_path(r'^upcoming-featured-events/$', UpcomingFeaturedEventsListAPIView.as_view(), name='upcoming-featured-events'),
    re_path(r'^past-featured-events/$', PastFeaturedEventsListAPIView.as_view(), name='past-featured-events'),
    # re_path(r'^featured-event-category-list/$', FeaturedEventCategoryListAPIView.as_view(), name='featured-event-category-list'),
    # re_path(r'^featured-event-products/(?P<category_slug>[\w-]+)/(?P<slug>[\w-]+)/$', ProductsByCategoryListAPIView.as_view(), name='category-product-list'),
    # re_path(r"^payment-form/$", views.payment_form, name="payment_form"),
    # re_path(r'^purchase-tickets-by-stripe_payment/$', PurchaseTicketsByStripePaymentAPIView.as_view(), name='purchase-tickets-stripe-payment'),
    # re_path(r'^purchase-tickets-by-paypal-payment/$', PurchaseTicketsByPayPalPaymentAPIView.as_view(), name='purchase-tickets-paypal-payment'),
    re_path(r'^generate-invoice-for-purchase-tickets/$', GenerateInvoiceForPurchaseTicketsAPIView.as_view(), name='generate-invoice-purchase-tickets'),
    re_path(r'^getRelatedProducts/$', GetRelatedProductListView.as_view(), name='get-products'),
    # re_path(r'^(?P<slug>[\w-]+)/$', GetCategoryDetailView.as_view(), name='get-category'),
    re_path(r'^terms-and-conditions/(?P<slug>[\w-]+)/$', TermsAndConditionsByFeaturedEventAPIView.as_view(), name='terms-and-conditions'),
    re_path(r'^paypal-failed-transaction-mail/$', EmailFailedEventsPaypalTrasactionsAPIView.as_view(), name='email-failed-event-paypal-payments'),
    re_path(r'^featured-event-products/(?P<slug>[\w-]+)/$', FeaturedEventProductsListAPIView.as_view(), name='featured-event-product-list'),

]
















