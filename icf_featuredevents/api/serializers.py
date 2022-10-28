from django.utils import timezone
from rest_framework import status, serializers
from rest_framework.serializers import ModelSerializer, Serializer
from icf import settings
from datetime import datetime

from icf_orders.api.serializers import ProductListSerializer
from icf_orders.models import CountryTax
from icf_featuredevents.models import FeaturedEvent, FeaturedEventGallery, TermsAndConditions, EventProduct, \
    Participant
import logging

from icf_generic.Exceptions import ICFException

from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class TermsAndConditionsSerializer(ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = ['name', 'description']


# class FeaturedEventsCategorySerializer(ModelSerializer):
#
#     class Meta:
#         model = FeaturedEventCategory
#         fields = ['id', 'name', 'description', 'slug', 'is_active']
#
#
# class FeaturedEventAndCategorySerializer(ModelSerializer):
#
#     class Meta:
#         model = FeaturedEventAndCategory
#         fields = ['id', 'featured_event', 'category', 'product']


class FeaturedEventsListSerializer(ModelSerializer):
    terms_and_conditions = TermsAndConditionsSerializer()

    class Meta:
        model = FeaturedEvent
        fields = ['title', 'sub_title', 'image', 'description', 'slug', 'status', 'location', 'start_date',
                  'end_date', 'start_date_timing', 'end_date_timing', 'contact_email', 'contact_no',
                  'is_featured_event', 'terms_and_conditions']


class LatestFeaturedEventSerializer(ModelSerializer):
    class Meta:
        model = FeaturedEvent
        fields = ['id', 'slug', 'title']


class FeaturedEventsRetrieveSerializer(ModelSerializer):
    tax = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedEvent
        fields = ['title', 'sub_title', 'image', 'description', 'slug', 'status', 'location', 'start_date',
                  'end_date', 'start_date_timing', 'end_date_timing', 'contact_email', 'contact_no',
                  'is_featured_event', 'terms_and_conditions', 'tax']

    def get_tax(self, obj):
        country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
        return country_tax.percentage


class FeaturedEventGalleryDetailSerializer(ModelSerializer):
    class Meta:
        model = FeaturedEventGallery
        fields = ['title', 'image_1', 'image_2', 'image_3', 'image_4', 'gallery_url']


class FeaturedEventsUpcomingOrPastSerializer(ModelSerializer):

    class Meta:
        model = FeaturedEvent
        fields = ['title', 'sub_title', 'image', 'description', 'slug', 'status', 'location', 'start_date',
                  'end_date', 'start_date_timing', 'end_date_timing', 'contact_email', 'contact_no',
                  'is_featured_event', 'terms_and_conditions']


class FeaturedEventsProductSerializer(ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    product = ProductListSerializer()

    class Meta:
        model = EventProduct
        fields = ['id', 'product',  'expiry_date', 'does_have_extra_participants', 'is_expired', 'no_of_tickets_allowed']

    def get_is_expired(self, obj):
        if obj.expiry_date < timezone.now():
            return True
        else:
            return False


class ParticipantCreateSerializer(ModelSerializer):
    class Meta:
        model = Participant
        fields = "__all__"


# class FeaturedEventsCategoryListSerializer(ModelSerializer):
#
#     class Meta:
#         model = FeaturedEventCategory
#         fields = '__all__'


# class FeaturedEventAndCategoryListSerializer(ModelSerializer):
#     category = FeaturedEventsCategoryListSerializer()
#
#     class Meta:
#         model = FeaturedEventAndCategory
#         fields = ['id', 'category', ]
#
#     def get_category(self, obj):
#         serializer = FeaturedEventsCategoryListSerializer(obj.category)
#         return serializer.data

class ProductSerializer(ModelSerializer):
    product_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EventProduct
        fields = ['id', 'product_name']

    def get_product_name(self, obj):
        return obj.product.name


class PurchaseTicketsByStripePaymentSerializer(Serializer):

    entityName = serializers.CharField()
    entityEmail = serializers.CharField()
    entityPhone = serializers.CharField()
    name_of_representative = serializers.CharField()
    address = serializers.CharField()
    participants = serializers.CharField()
    totalCost = serializers.DecimalField(max_digits=8, decimal_places=2)
    productList = serializers.ListField()
    stripeToken = serializers.CharField()
    event_slug = serializers.CharField()
    currency = serializers.CharField()
    VAT = serializers.CharField()


class PurchaseTicketsByPayPalPaymentSerializer(Serializer):

    entityName = serializers.CharField()
    entityEmail = serializers.CharField()
    entityPhone = serializers.CharField()
    name_of_representative = serializers.CharField()
    address = serializers.CharField()
    participants = serializers.CharField()
    totalCost = serializers.DecimalField(max_digits=8, decimal_places=2)
    productList = serializers.ListField()
    paymentToken = serializers.CharField()
    paymentID = serializers.CharField()
    event_slug = serializers.CharField()
    currency = serializers.CharField()
    VAT = serializers.CharField()


class OfflinePaymentInvoiceForTicketSerializer(Serializer):

    entityName = serializers.CharField()
    entityEmail = serializers.CharField()
    entityPhone = serializers.CharField()
    name_of_representative = serializers.CharField()
    address = serializers.CharField()
    participants = serializers.CharField()
    totalCost = serializers.DecimalField(max_digits=8, decimal_places=2)
    productList = serializers.ListField()
    event_slug = serializers.CharField()
    currency = serializers.CharField()
    VAT = serializers.CharField()




