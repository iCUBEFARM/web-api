from django.urls import path, include, re_path

from icf_orders.api import views
from icf_orders.api.views import CreditForAction, EntityCreditSummaryView, SalesHistoryForEntity, TransactionHistory, \
    AssignCreditView, GetCreditForActionView, GenerateInvoice, GetEntityUserForAdminList, \
    CreditHistoryListView, SubscriptionCreateUsingStripeApiView, \
    SubscriptionPlanListApiView, SubscriptionCreateUsingPaypalApiView, SubscriptionCreateOfflineApiView, \
    CheckSubscriptionApiView, PurchaseHistoryListApiView, ProductListApiView, \
    PurchaseCreditsByStripePaymentApiView, PurchaseCreditsByPayPalPaymentApiView, CheckEntitySubscriptionApiView, \
    GetProductsByProductTypeApiView, PurchaseProductsUsingStripePaymentApiView, CartCreateListView, CartDeleteView, \
    GetCartCount, CartDetailView, CartUpdateView, PurchaseProductsUsingPaypalPaymentApiView, \
    GenerateInvoiceForProductsApiView, GetBillingAddressForUserApiView, PurchaseHistoryForUserListApiView, \
    GetBuyerInformationForUserApiView, PurchaseDetailsListView, GenerateInvoiceForProductsByFreeCheckoutApiView, WalletDetailApiView, WithdrawalTransactionViewSet
from icf_entity.api.views import EntityAutocomplete
from rest_framework.routers import DefaultRouter, SimpleRouter

router = DefaultRouter()
router.register(r'withdrawal-transaction', WithdrawalTransactionViewSet, basename='withdrawal-transaction')

urlpatterns = [
    re_path(r'^', include(router.urls)),
    # re_path(r'^credit-for-action/$', CreditForAction.as_view(), name='credit-action'),
    re_path(r'^(?P<entity_slug>[\w-]+)/credit-summary/$', EntityCreditSummaryView.as_view(), name='credit-summary'),
    re_path(r'^(?P<entity_slug>[\w-]+)/credit-history/$', CreditHistoryListView.as_view(), name='credit-history'),
    # re_path(r'^transaction-history/$',TransactionHistory.as_view(),name='transaction-history'),
    # re_path(r'^(?P<entity_slug>[\w-]+)/product-create/$', ProductCreateApiView.as_view(), name='create-product'),
    # re_path(r'^(?P<id>[\d]+)/(?P<entity_slug>[\w-]+)$', ProductDetailApiView.as_view(), name='product-detail'),
    # re_path(r'^(?P<slug>[\w-]+)/product/edit/$', ProductUpdateApiView.as_view(), name='product-update'),
    # re_path(r'^(?P<id>[\d]+)/entity_slug/$', ProductDeleteView.as_view(), name='product-delete'),

    re_path(r'^(?P<entity_slug>[\w-]+)/wallet-details/$', WalletDetailApiView.as_view(), name='wallet-details'),


    re_path(r'^(?P<entity_slug>[\w-]+)/assign-credits/$', AssignCreditView.as_view(), name='assign-credit'),
    re_path(r'^(?P<action>[\w-]+)/get-credits/$', GetCreditForActionView.as_view(), name='get-credit'),
    re_path(r'^(?P<entity_slug>[\w-]+)/generate-invoice/$', GenerateInvoice.as_view(), name="generate-invoice"),
    re_path(r'^get-user-entity/', GetEntityUserForAdminList.as_view()),
    re_path(r'^entity-autocomplete/$', EntityAutocomplete.as_view(), name='entity-autocomplete'),
    re_path(r"^payment-form/$", views.payment_form, name="payment_form"),
    re_path(r'^(?P<entity_slug>[\w-]+)/purchase-credits-by-stripe_payment/$', PurchaseCreditsByStripePaymentApiView.as_view(), name='purchase-credits-by-stripe'),
    re_path(r'^(?P<entity_slug>[\w-]+)/purchase-credits-by-paypal_payment/$', PurchaseCreditsByPayPalPaymentApiView.as_view(), name='purchase-credits-by-paypal'),
    # re_path(r'^get-subscription-plan-list/$', SubscriptionPlanListApiView.as_view(), name='subscription-plan-list'),
    re_path(r'^get-product-list/(?P<product_type>\d+)/$', ProductListApiView.as_view(), name='subscription-plan-detail'),
    re_path(r'^check-subscription/(?P<entity_slug>[\w-]+)/(?P<subscription_id>\d+)/$', CheckSubscriptionApiView.as_view(), name='check-subscription'),
    re_path(r'^check-entity-subscription/(?P<entity_slug>[\w-]+)/$', CheckEntitySubscriptionApiView.as_view(), name='check-subscription'),
    re_path(r'^(?P<entity_slug>[\w-]+)/purchase-subscription-stripe/$', SubscriptionCreateUsingStripeApiView.as_view(), name='purchase-subscription-stripe'),
    re_path(r'^(?P<entity_slug>[\w-]+)/purchase-subscription-paypal/$', SubscriptionCreateUsingPaypalApiView.as_view(), name='purchase-subscription-paypal'),
    re_path(r'^(?P<entity_slug>[\w-]+)/generate-invoice-subscription-offline-payment/$', SubscriptionCreateOfflineApiView.as_view(), name='generate-invoice-purchase-subscription-offline'),
    re_path(r'^(?P<entity_slug>[\w-]+)/get-purchase-history/$', PurchaseHistoryListApiView.as_view(), name='purchase-history-entity'),
    re_path(r'^get-purchase-history-for-user/$', PurchaseHistoryForUserListApiView.as_view(), name='purchase-history-user'),
    re_path(r'^get-subscription-plan-list/$', SubscriptionPlanListApiView.as_view(), name='subscription-plan-list'),
    # re_path(r'^get-products-by-type/(?P<product_type>[\w-]+)/$', GetProductsByProductTypeApiView.as_view(), name='products-by-type'),
    re_path(r'^purchase-products-by-stripe-payment/$', PurchaseProductsUsingStripePaymentApiView.as_view(), name='purchase-products-by-stripe'),
    re_path(r'^purchase-products-by-paypal-payment/$', PurchaseProductsUsingPaypalPaymentApiView.as_view(), name='purchase-products-by-paypal'),
    re_path(r'^generate-invoice-for-products/$', GenerateInvoiceForProductsApiView.as_view(), name='generate-invoice-for-products'),
    re_path(r'^generate-invoice-for-products-free-checkout/$', GenerateInvoiceForProductsByFreeCheckoutApiView.as_view(), name='generate-invoice-for-products-free-checkout'),
    re_path(r'^add-to-cart/$', CartCreateListView.as_view(), name='cart-create'),
    re_path(r'^(?P<id>[\d]+)/remove-cart/$', CartDeleteView.as_view(), name='cart-delete'),
    re_path(r'^get-cart-count/$', GetCartCount.as_view(), name='cart-count'),
    re_path(r'^purchase-details/(?P<order_no>[\w-]+)/$', PurchaseDetailsListView.as_view(), name='purchase-detail'),
    re_path(r'^(?P<id>[\d]+)/cart-details/$', CartDetailView.as_view(), name='cart-details'),
    re_path(r'^(?P<id>[\d]+)/cart-update/$', CartUpdateView.as_view(), name='cart-update'),
    re_path(r'^get-billing-address-details/$', GetBillingAddressForUserApiView.as_view(),
        name='user-billing-address-details'),
    re_path(r'^get-buyer-information-for-user/$', GetBuyerInformationForUserApiView.as_view(),
        name='buyer-information-for-user'),
    re_path(r'^get-sales-history-for-entity/(?P<slug>[\w-]+)/$', SalesHistoryForEntity.as_view(), name='entity-sales-history'),


]


