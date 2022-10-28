from django.core.mail import send_mail
from django.core.mail.message import BadHeaderError
from django.http.response import HttpResponse
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.conf import settings

from icf_generic.models import Address, City, Country, State, Language, Currency, Sponsored, FeaturedVideo, \
    FeaturedEvent, FAQ, AboutUs, AdminEmail, AddressOptional, QuestionCategory, FAQCategory, Type
from django.utils.translation import ugettext_lazy as _


import logging

logger = logging.getLogger(__name__)


class CountrySerializer(ModelSerializer):

    class Meta:
        model = Country
        fields = ["id", "country", ]


class StateSerializer(ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = State
        fields = [
            "id",
            "state",
            "country",
        ]


class CitySerializer(ModelSerializer):
    city = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = [
            "id",
            "city",
            "state",
        ]

    def get_city(self, obj):
        return "{}, {}, {}".format(obj.city, obj.state.state, obj.state.country.country)


class AddressSerializer(ModelSerializer):
    # city = serializers.StringRelatedField()
    class Meta:
        model = Address
        fields = "__all__"


class AddressRetrieveSerializer(ModelSerializer):
    city = serializers.StringRelatedField()

    class Meta:
        model = Address
        fields = "__all__"


class LanguageSerializer(ModelSerializer):

    class Meta:
        model = Language
        fields = ["id", "name", ]

class TypeSerializer(ModelSerializer):

    class Meta:
        model = Type
        fields = ["id", "name", ]



class CurrencySerializer(ModelSerializer):

    class Meta:
        model = Currency
        fields = ["id", "name", ]


class SponsoredListSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=200)
    entity_name = serializers.CharField(max_length=200)
    location = serializers.CharField(max_length=900)
    slug = serializers.CharField(max_length=200)
    content_type = serializers.CharField(max_length=200)
    published_date = serializers.DateTimeField(format='%B %d, %Y')
    expiry_date = serializers.DateTimeField(format='%B %d, %Y')
    logo = serializers.CharField(max_length=900)


class GetFeaturedVideosListSerializer(ModelSerializer):
    class Meta:
        model = FeaturedVideo
        fields = ['title','video_url','description','is_main_video','show_in_dashboard']


class GetFeaturedEventsListSerializer(ModelSerializer):
    class Meta:
        model = FeaturedEvent
        fields = ['title', 'image', 'description', 'slug', 'status', 'location', 'start_date',
                  'end_date', 'start_date_timing', 'end_date_timing', 'contact_email', 'contact_no']


class FeaturedEventsRetrieveSerializer2(ModelSerializer):
    class Meta:
        model = FeaturedEvent
        fields = ['title', 'image', 'description', 'status', 'location', 'start_date',
                  'end_date', 'start_date_timing', 'end_date_timing', 'contact_email', 'contact_no']


class FAQListSerializer(ModelSerializer):
    # category_name_list = serializers.SerializerMethodField()
    # category_name = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = [
            # 'category_name_list',
            'question',
            'answer',
            'slug',
            'video_url',
        ]

    # def get_category_name(self, obj):
    #     question_category_id_query_list = QuestionCategory.objects.filter(faq=obj).values('category_id')

    # def get_category_name_list(self, obj):
    #     category_name_list = []
    #     c_id_list = []
    #     question_category_id_query_list = QuestionCategory.objects.filter(faq=obj).values('category_id')
    #     for qc in question_category_id_query_list:
    #         qc_id = qc.get('category_id')
    #         c_id_list.append(qc_id)
    #     for c_id in c_id_list:
    #         faq_category_name = FAQCategory.objects.get(id=c_id).name
    #         category_name_list.append(faq_category_name)
    #     return category_name_list


class FAQRetrieveSerializer(ModelSerializer):

    class Meta:
        model = FAQ
        fields = [
            'question',
            'answer',
            'slug',
            # 'video_url',
        ]

    # def get_category_name_list(self, obj):
    #     category_name_list = []
    #     c_id_list = []
    #     question_category_id_query_list = QuestionCategory.objects.filter(faq=obj).values('category_id')
    #     for qc in question_category_id_query_list:
    #         qc_id = qc.get('category_id')
    #         c_id_list.append(qc_id)
    #     for c_id in c_id_list:
    #         faq_category_name = FAQCategory.objects.get(id=c_id).name
    #         category_name_list.append(faq_category_name)
    #     return category_name_list


class FAQSerializer(ModelSerializer):

    class Meta:
        model = FAQ
        fields = [
            'question',
            # 'answer',
            'slug',
            # 'video_url',
        ]


class AboutUsCreateSerializer(ModelSerializer):
    class Meta:
        model = AboutUs
        fields = "__all__"

    def create(self, validated_data):
        about_us = AboutUs.objects.create(**validated_data)
        try:
            send_mail(about_us.subject, about_us.message, about_us.email, [settings.CONTACT_US_TO_EMAIL],
                      fail_silently=False)
        except BadHeaderError:
            return HttpResponse(_('Invalid header found.'))
        return about_us

    # def create(self, validated_data):
    #     about_us = AboutUs.objects.create(**validated_data)
    #     try:
    #         admin_email = AdminEmail.objects.all().first()
    #         if admin_email is not None:
    #             # about_us = AboutUs.objects.create(**validated_data)
    #             send_mail(about_us.subject, about_us.message, about_us.email, [settings.CONTACT_US_TO_EMAIL], fail_silently=False)
    #         else:
    #             raise serializers.ValidationError({'detail' : 'Support email not configured by Admin'})
    #     except BadHeaderError:
    #         # return HttpResponse('Invalid header found.')
    #         raise serializers.ValidationError("Invalid header found.")
    #     return about_us


class AddressOptionalSerializer(ModelSerializer):
    # city = serializers.StringRelatedField()
    class Meta:
        model = AddressOptional
        fields = "__all__"


class AddressOptionalRetrieveSerializer(ModelSerializer):
    city = serializers.StringRelatedField()

    class Meta:
        model = AddressOptional
        fields = "__all__"


class FAQCategorySerializer(ModelSerializer):
    class Meta:
        model = FAQCategory
        fields = "__all__"


class FAQWithCategoryListSerializer(ModelSerializer):
    category = serializers.StringRelatedField()
    faq = FAQRetrieveSerializer()

    class Meta:
        model = QuestionCategory
        fields = '__all__'


class RelevantFAQListSerializer(ModelSerializer):
    # category_name_list = serializers.SerializerMethodField()
    class Meta:
        model = FAQ
        fields = "__all__"
        # fields = [
        #     'category_name_list',
        #     'question',
        #     'answer',
        #     'slug',
        #     'video_url',
        # ]

    # def get_category_name_list(self, obj):
    #     category_name_list = []
    #     c_id_list = []
    #     question_category_id_query_list = QuestionCategory.objects.filter(faq=obj).values('category_id')
    #     for qc in question_category_id_query_list:
    #         qc_id = qc.get('category_id')
    #         c_id_list.append(qc_id)
    #     for c_id in c_id_list:
    #         faq_category_name = FAQCategory.objects.get(id=c_id).name
    #         category_name_list.append(faq_category_name)
    #     return category_name_list


class FAQListByCategorySerializer(ModelSerializer):
    # category = serializers.StringRelatedField()
    # category_slug = serializers.SerializerMethodField()
    faq = FAQSerializer()

    class Meta:
        model = QuestionCategory
        # fields = '__all__'
        fields = [
            'faq',
            # 'category',
            # 'category_slug',
        ]

    # def get_category_slug(self, obj):
    #     return obj.category.slug


class FAQDetailSerializer(ModelSerializer):

    class Meta:
        model = FAQ
        fields = [
            'question',
            'answer',
            'slug',
            'video_url',
        ]


class FAQListByCategorySlugSerializer(ModelSerializer):
    faq = FAQDetailSerializer()

    class Meta:
        model = QuestionCategory
        fields = [
            'faq',
            # 'category',
            # 'category_slug',
        ]
