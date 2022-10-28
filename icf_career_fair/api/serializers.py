import json
from datetime import datetime

import pytz
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import transaction
from django.db.models import Count

from icf import settings
from icf_auth.api.serializers import UserProfileRetrieveSerializerForList
from icf_auth.models import User, UserProfile
from icf_career_fair.api.mixins import ICFSpeakerMixin, ICFSpeakerOptionalMixin, ICFCareerFairMixin, \
    ICFCareerFairDraftMixin, ICFSupportMixin, ICFSupportOptionalMixin
from icf_career_fair.models import CareerFairImageType, CareerFairProductSubType, CareerFair, Session, Speaker, \
    CareerFairDraft, \
    SessionOptional, SupportOptional, \
    SpeakerOptional, Support, SpeakerProfileImage, SpeakerProfileImageOptional, CareerFairGallery, \
    CareerFairGalleryOptional, SpeakerAndSession, SpeakerAndSessionOptional, CareerFairAndProduct, \
    CareerFairAndProductOptional, SupportLogo, SupportLogoOptional, ParticipantAndProduct, CareerFairAndProductOptional, \
    ParticipantAndProduct, CareerFairParticipant, CareerFairImages, CareerFairImagesOptional, CareerFairAdvertisement
from icf_career_fair.util import CareerFairUtil
from icf_entity.api.mixins import ICFEntityMixin
from icf_jobs.JobHelper import get_user_work_experience_in_seconds
from icf_jobs.api.serializers import UserJobProfileRetrieveSerializer, UserEducationRetrieveSerializer, \
    UserWorkExperienceListSerializer, UserReferenceSerializerForList, UserSkillSerializer
from icf_jobs.models import UserJobProfile, UserResume, JobProfileFileUpload, UserEducation, UserWorkExperience, \
    UserReference, UserSkill
from icf_messages.models import ICFMessage
from icf_orders.app_settings import CREATE_CAREER_FAIR, SPONSORED_CAREER_FAIR
from icf_orders.models import CreditAction, Subscription, Product, ProductDraft
from icf_entity.models import Logo, Entity
from icf_orders.api.mixins import ICFCreditManager
from icf_generic.Exceptions import ICFException
from icf_generic.api.serializers import AddressSerializer, AddressRetrieveSerializer, AddressOptionalSerializer, \
    CitySerializer
from icf_item.api.serializers import ItemCreateUpdateSerializer, ItemListSerializer, EntitySerializer, \
    ItemCreateUpdateDraftSerializer, ItemDraftListSerializer
from icf_generic.models import Address, Sponsored, AddressOptional, City, Type, Category, Currency
from icf_item.models import Item, ItemUserView, FavoriteItem, ItemDraft
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.utils import model_meta
from rest_framework import serializers
from rest_framework import status
from django.utils.translation import ugettext_lazy as _

import logging

from icf_messages.manager import ICFNotificationManager

logger = logging.getLogger(__name__)


class SessionRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Session
        exclude = ['career_fair', 'slug']
        # exclude = ['career_fair']


class SupportLogoSerializer(ICFSupportMixin, ModelSerializer):
    class Meta:
        model = SupportLogo
        fields = ['logo', 'id']

    def get_logo(self, obj):
        return obj.logo.url

    def create(self, validated_data):
        logger.info("Upload logo for the support.")
        support = self.get_support(self.context['slug'])
        try:
            obj = SupportLogo.objects.get(support=support)
            obj.logo = validated_data.get('logo')
            obj.save()
        except ObjectDoesNotExist:
            obj = SupportLogo.objects.create(support=support, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update logo for the support")
        instance.logo = validated_data.get('logo')
        instance.save()
        return instance


class SupportOptionalLogoSerializer(ICFSupportOptionalMixin, ModelSerializer):
    class Meta:
        model = SupportLogoOptional
        fields = ['logo', 'id']

    def get_logo(self, obj):
        return obj.logo.url

    def create(self, validated_data):
        logger.info("Update logo for the support optional.")
        support = self.get_support(self.context['slug'])
        try:
            obj = SupportLogoOptional.objects.get(support=support)
            obj.logo = validated_data.get('logo')
            obj.save()
        except ObjectDoesNotExist:
            obj = SupportLogoOptional.objects.create(support=support, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update logo for the support optional.")
        instance.logo = validated_data.get('logo')
        instance.save()
        return instance


class SupportRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Support
        exclude = ['career_fair', 'slug']

    # def get_logo(self, obj):
    #     return obj.logo.url


class SpeakerProfileImageOptionalSerializer(ICFSpeakerOptionalMixin, ModelSerializer):
    class Meta:
        model = SpeakerProfileImageOptional
        fields = ['image_url', 'id']

    def get_image(self, obj):
        return obj.image.url

    def create(self, validated_data):
        logger.info("Upload image for the speaker.")
        speaker = self.get_speaker(self.context['slug'])
        try:
            obj = SpeakerProfileImageOptional.objects.get(speaker=speaker)
            obj.image = validated_data.get('image')
            obj.save()
        except ObjectDoesNotExist:
            obj = SpeakerProfileImageOptional.objects.create(speaker=speaker, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update speaker image for the career fair")
        instance.image = validated_data.get('image')
        instance.save()
        return instance


class SpeakerAndSessionSerializer(ModelSerializer):
    class Meta:
        model = SpeakerAndSessionOptional
        fields = '__all__'


class CareerFairImageSerializer(ICFCareerFairMixin, ModelSerializer):
    class Meta:
        model = CareerFairImages
        fields = ['image', 'id']

    def get_image(self, obj):
        return obj.image.url

    def create(self, validated_data):
        logger.info("Upload image for career fair image.")
        career_fair = self.get_career_fair(self.context['slug'])
        try:
            obj = CareerFairImages.objects.get(career_fair=career_fair)
            obj.image = validated_data.get('image')
            obj.save()
        except ObjectDoesNotExist:
            obj = CareerFairImages.objects.create(career_fair=career_fair, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update image for the career fair")
        instance.image = validated_data.get('image')
        instance.save()
        return instance


class CareerFairOptionalImageSerializer(ICFCareerFairDraftMixin, ModelSerializer):
    career_fair_slug = serializers.SerializerMethodField()

    class Meta:
        model = CareerFairImagesOptional
        fields = ['image', 'id', 'career_fair_slug']

    def get_career_fair_slug(self, obj):
        return obj.career_fair.slug

    def get_image(self, obj):
        return obj.image.url

    def create(self, validated_data):
        logger.info("Upload image for the career fair optional.")
        career_fair_draft = self.get_draft_career_fair(self.context['slug'])
        try:
            obj = CareerFairImagesOptional.objects.get(career_fair=career_fair_draft)
            obj.image = validated_data.get('image')
            obj.save()
        except ObjectDoesNotExist:
            obj = CareerFairImagesOptional.objects.create(career_fair=career_fair_draft, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update image for the career fair draft")
        instance.image = validated_data.get('image')
        instance.save()
        return instance


class CareerFairImageSerializer(ICFCareerFairMixin, ModelSerializer):
    career_fair_slug = serializers.SerializerMethodField()

    class Meta:
        model = CareerFairImages
        fields = ['image', 'id', 'career_fair_slug']

    def get_career_fair_slug(self, obj):
        return obj.career_fair.slug

    def get_image(self, obj):
        return obj.image.url

    def create(self, validated_data):
        logger.info("Upload image for the career fair optional.")
        career_fair = self.get_career_fair(self.context['slug'])
        try:
            obj = CareerFairImages.objects.get(career_fair=career_fair)
            obj.image = validated_data.get('image')
            obj.save()
        except ObjectDoesNotExist:
            obj = CareerFairImages.objects.create(career_fair=career_fair, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update image for the career fair ")
        instance.image = validated_data.get('image')
        instance.save()
        return instance


class SpeakerProfileImageSerializer(ICFSpeakerMixin, ModelSerializer):
    class Meta:
        model = SpeakerProfileImage
        fields = ['image', 'id']

    def get_image(self, obj):
        return obj.image.url

    def create(self, validated_data):
        logger.info("Upload image for the speaker.")
        speaker = self.get_speaker(self.context['slug'])
        try:
            obj = SpeakerProfileImage.objects.get(speaker=speaker)
            obj.image = validated_data.get('image')
            obj.save()
        except ObjectDoesNotExist:
            obj = SpeakerProfileImage.objects.create(speaker=speaker, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update speaker image for the career fair")
        instance.image = validated_data.get('image')
        instance.save()
        return instance


class SpeakerRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    # image = serializers.SerializerMethodField(read_only=True)
    speaker_sessions = SessionRetrieveSerializer(many=True)

    class Meta:
        model = Speaker
        fields = [
            'id',
            'name',
            'entity_name',
            'position',
            'speaker_sessions',
            'image_url'
        ]

    # def get_image(self, object):
    #     serializer = SpeakerProfileImageSerializer(
    #         SpeakerProfileImage.objects.filter(speaker=object).first())
    #     return serializer.data

    def get_speaker_sessions(self, object):
        speaker_session_serializer_list = []
        speaker_sessions_objects_list = SpeakerAndSession.objects.filter(speaker=object)
        for speaker_session in speaker_sessions_objects_list:
            session_serializer = SpeakerAndSessionSerializer(speaker_session)
            speaker_session_serializer_list.append(session_serializer.data)
        return speaker_session_serializer_list


class SessionSerializer(ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'


class SupportSerializer(ModelSerializer):
    class Meta:
        model = Support
        fields = '__all__'


class SpeakerSerializer(ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)
    # speaker_type_name = serializers.SerializerMethodField(read_only=True)
    speaker_sessions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Speaker
        fields = [
            'name',
            'entity_name',
            'position',
            # 'speaker_type',
            # 'speaker_type_name',
            'speaker_sessions',
            'image_url',
            'image'
        ]

    def get_image(self, object):
        serializer = SpeakerProfileImageSerializer(
            SpeakerProfileImage.objects.filter(speaker=object).first())
        return serializer.data

    # def get_speaker_type(self, object):
    #     return object.speaker_type

    # def get_speaker_type_name(self, object):
    #     return Speaker.get_speaker_types().get(object.speaker_type)

    def get_speaker_sessions(self, object):
        speaker_session_serializer_list = []
        speaker_sessions_objects_list = SpeakerAndSession.objects.filter(speaker=object)
        for speaker_session in speaker_sessions_objects_list:
            session_serializer = SpeakerAndSessionSerializer(speaker_session)
            speaker_session_serializer_list.append(session_serializer.data)
        return speaker_session_serializer_list


class SessionOptionalSerializer(ModelSerializer):
    class Meta:
        model = SessionOptional
        # exclude = ['career_fair', 'slug']
        fields = '__all__'


class SupportOptionalSerializer(ModelSerializer):
    class Meta:
        model = SupportOptional
        fields = '__all__'


class SpeakerOptionalSerializer(ModelSerializer):
    # image = serializers.SerializerMethodField(read_only=True)
    # speaker_type_name = serializers.SerializerMethodField(read_only=True)
    speaker_sessions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SpeakerOptional
        fields = [
            'name',
            'entity_name',
            'position',
            # 'speaker_type',
            # 'speaker_type_name',
            'speaker_sessions',
            'image_url'
        ]

    # def get_image(self, object):
    #     serializer = SpeakerProfileImageOptionalSerializer(
    #         SpeakerProfileImageOptional.objects.filter(speaker=object).first())
    #     return serializer.data

    # def get_speaker_type(self, object):
    #     return object.speaker_type

    # def get_speaker_type_name(self, object):
    #     return SpeakerOptional.get_speaker_types().get(object.speaker_type)

    def get_speaker_sessions(self, object):
        speaker_session_serializer_list = []
        speaker_sessions_optional_objects_list = SpeakerAndSessionOptional.objects.filter(speaker=object)
        for speaker_session in speaker_sessions_optional_objects_list:
            session_serializer = SpeakerAndSessionOptionalSerializer(speaker_session)
            speaker_session_serializer_list.append(session_serializer.data)
        return speaker_session_serializer_list


class SessionOptionalRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = SessionOptional
        # fields = ['id', 'title', 'description', 'start_date', 'start_time', 'end_time', 'session_link', ]
        exclude = ['career_fair', 'slug']
        # exclude = ['career_fair']


class SupportOptionalRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = SupportOptional
        exclude = ['career_fair', 'slug']


class SpeakerAndSessionOptionalSerializer(ModelSerializer):
    class Meta:
        model = SpeakerAndSessionOptional
        fields = '__all__'


class SpeakerOptionalRetrieveTestSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    # image = serializers.SerializerMethodField(read_only=True)
    speaker_sessions = serializers.SerializerMethodField()

    class Meta:
        model = SpeakerOptional
        fields = [
            'id',
            'name',
            'entity_name',
            'position',
            'image_url',
            'speaker_sessions'
        ]

    def get_speaker_sessions(self, obj):
        session_ids = SpeakerAndSessionOptional.objects.filter(speaker=obj).values_list('session__id')
        queryset = SessionOptional.objects.filter(id__in=session_ids)
        return SessionOptionalRetrieveSerializer(queryset, many=True).data

    # def get_image(self, object):
    #     serializer = SpeakerProfileImageOptionalSerializer(SpeakerProfileImageOptional.objects.filter(speaker=object).first())
    #     return serializer.data


class SpeakerOptionalRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    # image = serializers.SerializerMethodField(read_only=True)
    speaker_sessions = SessionOptionalRetrieveSerializer(many=True)

    class Meta:
        model = SpeakerOptional
        fields = [
            'id',
            'name',
            'entity_name',
            'position',
            'image_url',
            'speaker_sessions'
        ]
        # extra_fields = ['speaker_sessions']
        # fields = fields + extra_fields

    # def get_image(self, object):
    #     serializer = SpeakerProfileImageOptionalSerializer(SpeakerProfileImageOptional.objects.filter(speaker=object).first())
    #     return serializer.data

    # def get_speaker_sessions(self, object):
    #     speaker_session_serializer_list = []
    #     queryset = SpeakerAndSessionOptional.objects.filter(speaker=object)
    #     return SpeakerAndSessionOptionalSerializer(queryset, many=True)
    #     # for speaker_session in speaker_sessions_optional_objects_list:
    #     #     session_serializer = SpeakerAndSessionOptionalSerializer(speaker_session)
    #     #     # return session_serializer.data
    #     #     speaker_session_serializer_list.append(session_serializer.data)
    #     # return speaker_session_serializer_list


# class SpeakerOptionalRetrieveTestSerializer(ModelSerializer):
#     image = serializers.SerializerMethodField(read_only=True)
#     # image = serializers.ImageField(use_url=True, max_length=None, write_only=True)
#     # speaker_and_sessions = serializers.ListField(write_only=True)
#     # speaker_and_sessions = serializers.ListField(write_only=True)
#     # speaker_sessions = SessionOptionalRetrieveSerializer(many=True)
#     session_speakers_optional = SessionOptionalRetrieveSerializer(many=True)
#
#     class Meta:
#         model = SpeakerOptional
#         fields = [
#             'name',
#             'entity_name',
#             'position',
#             'session_speakers_optional',
#             'image'
#         ]
# extra_fields = ['speaker_sessions']
# fields = fields + extra_fields

# def get_image(self, object):
#     serializer = SpeakerProfileImageOptionalSerializer(SpeakerProfileImageOptional.objects.filter(speaker=object).first())
#     return serializer.data

# def get_speaker_sessions(self, object):
#     speaker_session_serializer_list = []
#     queryset = SpeakerAndSessionOptional.objects.filter(speaker=object)
#     return SpeakerAndSessionOptionalSerializer(queryset, many=True)
#     # for speaker_session in speaker_sessions_optional_objects_list:
#     #     session_serializer = SpeakerAndSessionOptionalSerializer(speaker_session)
#     #     # return session_serializer.data
#     #     speaker_session_serializer_list.append(session_serializer.data)
#     # return speaker_session_serializer_list


class CareerFairProductSerializer(ModelSerializer):
    currency = serializers.CharField(max_length=20)
    product_sub_type = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_product_sub_type(self, obj):
        try:
            # id = obj.id
            # test = CareerFairAndProduct.objects.filter(product=obj)
            # count = test.count()
            career_fair_and_product_obj = CareerFairAndProduct.objects.get(product=obj)

            return career_fair_and_product_obj.product_sub_type
        except Exception as e:
            raise


class CareerFairSalesSerializer(ModelSerializer):
    currency = serializers.CharField()
    product_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    product_name = serializers.CharField()
    item_quantity = serializers.IntegerField()
    item_cost = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = ParticipantAndProduct
        fields = ['product_name', 'product_cost', 'item_quantity', 'item_cost', 'currency']


class ProductDraftRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    currency = serializers.CharField(max_length=20)

    class Meta:
        model = ProductDraft
        exclude = ['entity', 'parent_product']


class CareerFairAndProductOptionalRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    product = ProductDraftRetrieveSerializer()

    class Meta:
        model = CareerFairAndProductOptional
        fields = [
            'id',
            'product',
            'product_sub_type',
        ]


class ProductRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    currency = serializers.CharField(max_length=20)

    class Meta:
        model = Product
        exclude = ['entity', 'parent_product']


class CareerFairAndProductRetrieveSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    product = ProductRetrieveSerializer()

    class Meta:
        model = CareerFairAndProduct
        fields = [
            'id',
            'product',
            'product_sub_type',
        ]


class SponsoredSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(default=None)
    end_date = serializers.DateTimeField(default=None)

    class Meta:
        model = Sponsored
        fields = ['start_date', 'end_date']


class CareerFairCreateSerializer(ItemCreateUpdateSerializer):
    career_fair_sessions = SessionRetrieveSerializer(many=True)
    career_fair_supports = SupportRetrieveSerializer(many=True)
    career_fair_speakers = SpeakerRetrieveSerializer(many=True)
    career_fair_products = CareerFairAndProductRetrieveSerializer(many=True)

    slug = serializers.ReadOnlyField()
    item_type = serializers.SerializerMethodField()
    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = CareerFair
        exclude = ['owner', 'category']
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(CareerFairCreateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    @transaction.atomic
    def create(self, validated_data):
        location_data = validated_data.pop("location")
        location = Address.objects.create(**location_data)

        entity = validated_data.get("entity")

        sponsored_start_dt = validated_data.pop('sponsored_start_dt')
        sponsored_end_dt = validated_data.pop('sponsored_end_dt')
        is_sponsored = validated_data.pop('is_sponsored')

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create career fair.")
            raise ICFException(_("You do not have the permissions to create fairs for {}".format(entity)),
                               status_code=status.HTTP_400_BAD_REQUEST)

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('expiry')

        if request.data.get('career_fair_draft_slug'):
            career_fair_draft_slug = request.data.get('career_fair_draft_slug').lstrip().rstrip()
        else:
            logger.exception("career_fair_draft_slug not there, cannot create career fair.")
            raise ICFException(_("could not create career fair for {}".format(entity)),
                               status_code=status.HTTP_400_BAD_REQUEST)

        try:
            type_obj = Type.objects.get(slug='career fair')
            category_name = 'career fair category'
            try:
                category_obj = Category.objects.get(name=category_name, type=type_obj)
            except Category.DoesNotExist as tdn:
                category_obj = Category.objects.create(name=category_name,
                                                       description='career fair category description', type=type_obj)
        except Type.DoesNotExist as tdn:
            logger.exception("Invalid category type for career fair.\n")
            raise ICFException(_("Invalid category type for career fair, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Category.DoesNotExist as tdn:
            logger.exception("category object not found for career fair.\n")
            raise ICFException(_("Invalid category type for career fair, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        is_allowed_interval = ICFCreditManager.is_allowed_interval(start_date, end_date)
        if not is_allowed_interval:
            logger.exception("Invalid duration for posting the career fair. "
                             "The career fair's start date should be between {X} and {Y}.\n"
                             .format(X=str(datetime.now(pytz.utc).date()), Y=str(end_date)))
            raise ICFException(_("The career fair's start date should be between {X} and {Y}."
                                 .format(X=str(datetime.now(pytz.utc).date()), Y=str(end_date))))

        cf_session_data = validated_data.get('career_fair_sessions', None)
        cf_support_data = validated_data.get('career_fair_supports', None)
        cf_speaker_data = validated_data.get('career_fair_speakers', None)
        cf_product_data = validated_data.get('career_fair_products', None)

        cf_session_data = validated_data.pop('career_fair_sessions')
        cf_support_data = validated_data.pop('career_fair_supports')
        cf_speaker_data = validated_data.pop('career_fair_speakers')
        cf_product_data = validated_data.pop('career_fair_products')

        title = validated_data.pop('title')
        title_en = validated_data.pop('title_en')
        title_fr = validated_data.pop('title_fr')
        title_es = validated_data.pop('title_es')

        description = validated_data.pop('description')
        description_en = validated_data.pop('description_en')
        description_fr = validated_data.pop('description_fr')
        description_es = validated_data.pop('description_es')

        career_fair = CareerFair.objects.create(owner=user, location=location, item_type=type_obj,
                                                category=category_obj,
                                                title=title, title_en=title, title_fr=title, title_es=title,
                                                description=description, description_en=description,
                                                description_es=description,
                                                description_fr=description, **validated_data)

        career_fair_model = ContentType.objects.get_for_model(career_fair)

        if cf_session_data:
            # to avoid redundancy of Session
            for session_d in cf_session_data:
                session_dict = session_d
                if session_dict.get('id'):
                    session_dict.pop('id')

                session_obj = Session.objects.create(career_fair=career_fair, **session_dict)

        if cf_support_data:
            # # # cf_support_data  is a list of dictionaries
            for support_d in cf_support_data:
                support_dict = support_d
                if support_dict.get('id'):
                    support_dict.pop('id')
                support_obj = Support.objects.create(career_fair=career_fair, **support_dict)

        if cf_speaker_data:
            for speaker_d in cf_speaker_data:
                speaker_dict = speaker_d

                if speaker_dict.get('id'):
                    speaker_dict.pop('id')

                speaker_sessions = speaker_dict.pop('speaker_sessions')

                speaker_obj = Speaker.objects.create(career_fair=career_fair, **speaker_dict)

                if speaker_sessions:
                    # each item in the list is session id
                    for session_obj in speaker_sessions:
                        try:

                            if session_obj.get('id'):
                                session_obj.pop('id')

                            session_obj_db = None
                            if isinstance(session_obj, Session):
                                session_obj_db = session_obj
                            else:
                                session_obj_db = Session.objects.get(**session_obj)
                            if session_obj_db.pk:
                                speaker_session, speaker_session_created = SpeakerAndSession.objects.update_or_create(
                                    speaker=speaker_obj,
                                    session=session_obj_db)

                        except Session.DoesNotExist as s:
                            logger.exception("Session object not found.\n")
                            raise ICFException(_("Could not create career fair, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        except ObjectDoesNotExist as obe:
                            logger.exception("Object does not exist")

        if cf_product_data:

            # # # cf_product_data  is a list of dictionaries
            for career_fair_and_product_dict in cf_product_data:
                product_dict = career_fair_and_product_dict.pop('product')
                product_sub_type = career_fair_and_product_dict.pop('product_sub_type')
                if product_sub_type == CareerFairProductSubType.ADVERTISEMENT:
                    #     career_fair_and_product_obj = CareerFairAndProduct.objects.filter(career_fair=instance,
                    #                                                                       product_sub_type=product_sub_type)
                    is_advertisement_already_exist = CareerFairAdvertisement.objects.filter(career_fair=career_fair,
                                                                                            entity=career_fair.entity)
                    if is_advertisement_already_exist.count() == 0:
                        is_ad_already_exist = 1
                        link = "no link now"
                        CareerFairUtil.send_add_advertisement_link_to_owner(career_fair.entity, user, link)

                career_fair_and_product_id = None
                is_ad_already_exist = None
                if career_fair_and_product_dict.get('id'):
                    career_fair_and_product_id = career_fair_and_product_dict.pop('id')

                currency_code = product_dict.pop('currency')
                currency_obj = Currency.objects.get(code=currency_code.upper())

                if product_dict.get('id'):
                    product_id = product_dict.pop('id')

                product_obj = Product.objects.create(currency=currency_obj, entity=career_fair.entity, **product_dict)
                if is_ad_already_exist == 1:
                    CareerFairAdvertisement.objects.create(
                        user=user,
                        career_fair=career_fair,
                        entity=career_fair.entity,
                        product=product_obj,
                        ad_image_type=CareerFairImageType.DESKTOP_IMAGE

                    )
                    CareerFairAdvertisement.objects.create(
                        user=user,
                        career_fair=career_fair,
                        entity=career_fair.entity,
                        product=product_obj,
                        ad_image_type=CareerFairImageType.MOBILE_IMAGE

                    )

                # product_obj, product_obj_created = Product.objects.update_or_create(currency=currency_obj,
                #                                                                     entity=career_fair.entity, **product_dict)

                # if career_fair_and_product_id:
                #     career_fair_product_obj = CareerFairAndProduct.objects.get(
                #         id=career_fair_and_product_id)
                #     career_fair_product_obj.product = product_obj
                #     career_fair_product_obj.career_fair = career_fair
                #     career_fair_product_obj.product_sub_type = product_sub_type
                #     career_fair_product_obj.save()
                # else:

                career_fair_and_product = CareerFairAndProduct.objects.create(
                    career_fair=career_fair,
                    product=product_obj,
                    product_sub_type=product_sub_type)

        if career_fair.status == Item.ITEM_UNDER_REVIEW:
            ICFCreditManager.manage_entity_subscription(entity=entity, action=CREATE_CAREER_FAIR,
                                                        item_start_date=start_date,
                                                        item_end_date=end_date, user=user, app=career_fair_model)

            # if is_sponsored:
            #
            #     if not sponsored_start_dt or not sponsored_end_dt:
            #         logger.exception("Invalid values for sponsored start date and sponsored end date.\n")
            #         raise ICFException(_("Please provide career fair's sponsored start date and sponsored end date."),
            #                            status_code=status.HTTP_400_BAD_REQUEST)
            #
            #     # A career fair can be sponsored anywhere during the period when the cf is active.
            #     if sponsored_start_dt >= career_fair.start_date and sponsored_end_dt <= career_fair.expiry:
            #         intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
            #                                                           SPONSORED_CAREER_FAIR)
            #         Sponsored.objects.create(content_object=career_fair, start_date=sponsored_start_dt,
            #                                  end_date=sponsored_end_dt)
            #         ICFCreditManager.charge_for_action(user=user, entity=entity, app=career_fair_model,
            #                                            action=SPONSORED_CAREER_FAIR,
            #                                            intervals=intervals)
            #         career_fair.is_sponsored = True
            #         career_fair.sponsored_start_dt = sponsored_start_dt
            #         career_fair.sponsored_end_dt = sponsored_end_dt
            #         career_fair.save()
            #     else:
            #         logger.exception("A career fair can be sponsored from {X} till {Y}. "
            #                          "Choose valid sponsored start date and end date.\n".
            #                          format(X=str(career_fair.start_date), Y=str(career_fair.expiry)))
            #         raise ICFException(_("A career fair can be sponsored from {X} till {Y}. "
            #                              "Choose valid sponsored start date and end date.".
            #                              format(X=str(career_fair.start_date), Y=str(career_fair.expiry))),
            #                            status_code=status.HTTP_400_BAD_REQUEST)
            #
            # #
            # Add teh sponsored information to the career fair object to be serialized.
            # The sponsored information is added to the career fair object even though the information
            # is not part of the CareerFair model.
            #

        try:
            career_fair_draft_obj = ItemDraft.objects.get(slug=career_fair_draft_slug)
        except ItemDraft.DoesNotExist as edne:
            logger.exception(str(edne))
            raise
        try:
            career_fair_draft_gallery_list = CareerFairGalleryOptional.objects.filter(career_fair=career_fair_draft_obj,
                                                                                      entity=entity)
            for career_fair_draft_gallery_obj in career_fair_draft_gallery_list:
                CareerFairGallery.objects.create(career_fair=career_fair, entity=entity,
                                                 career_fair_slug=career_fair.slug,
                                                 image=career_fair_draft_gallery_obj.image,
                                                 image_type=career_fair_draft_gallery_obj.image_type)
            career_fair_draft_obj.delete()

        except Exception as e:
            logger.exception(str(e))
            raise

        logger.info("Career fair created {}".format(career_fair))

        """
        Send career fair for approval to the admin
        """
        if career_fair.status == Item.ITEM_UNDER_REVIEW:
            CareerFairUtil.send_career_fair_review_email(request, career_fair)

        return career_fair

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None


class SpeakerRetrieveTestSerializer(ModelSerializer):
    id = serializers.IntegerField(required=False)
    # image = serializers.SerializerMethodField(read_only=True)
    # image = serializers.ImageField(use_url=True, max_length=None, write_only=True)
    speaker_sessions = serializers.SerializerMethodField()

    class Meta:
        model = Speaker
        fields = [
            'id',
            'name',
            'entity_name',
            'position',
            'image_url',
            'speaker_sessions'
        ]

    def get_speaker_sessions(self, obj):
        session_ids = SpeakerAndSession.objects.filter(speaker=obj).values_list('session__id')
        queryset = Session.objects.filter(id__in=session_ids)
        return SessionRetrieveSerializer(queryset, many=True).data

    # def get_image(self, object):
    #     serializer = SpeakerProfileImageSerializer(SpeakerProfileImage.objects.filter(speaker=object).first())
    #     return serializer.data


class CareerFairRetrieveTestSerializer(ItemCreateUpdateSerializer):
    career_fair_sessions = SessionRetrieveSerializer(many=True)
    career_fair_supports = SupportRetrieveSerializer(many=True)
    career_fair_speakers = SpeakerRetrieveTestSerializer(many=True)
    slug = serializers.ReadOnlyField()
    item_type = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    # entity = serializers.StringRelatedField()
    entity = EntitySerializer()
    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)
    career_fair_products = CareerFairAndProductRetrieveSerializer(many=True, )
    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = CareerFair
        exclude = ['owner', 'category']
        extra_fields = ['entity', 'item_type', 'entity_logo', 'hero_image', 'gallery_images', 'career_fair_sessions',
                        'career_fair_supports', 'career_fair_speakers', 'career_fair_products']
        # fields = (
        #     'id',
        #     'title',
        #     'entity',
        #     'item_type',
        #     'entity_logo',
        #     'description',
        #     'location',
        #     'status',
        #     'expiry',
        #     'slug',
        #     'start_date',
        #     'start_time',
        #     'end_time',
        #     'organiser_contact_email',
        #     'organiser_contact_phone',
        #     'hero_image',
        #     'gallery_images',
        #     'career_fair_sessions',
        #     'career_fair_supports',
        #     'career_fair_speakers',
        #     'career_fair_products',
        #     'created',
        #     'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None

    def get_hero_image(self, obj):
        try:
            career_fair_galley_obj = CareerFairGallery.objects.filter(career_fair=obj,
                                                                      image_type=CareerFairGallery.HERO).last()
            if career_fair_galley_obj:
                return CareerFairGallery.objects.filter(career_fair=obj,
                                                        image_type=CareerFairGallery.HERO).last().image.url
            else:
                return None
        except CareerFairGallery.DoesNotExist:
            return None

    def get_gallery_images(self, obj):
        career_fair_gallery_list = CareerFairGallery.objects.filter(career_fair=obj,
                                                                    image_type=CareerFairGallery.GALLERY).order_by(
            'created')
        return CareerFairGallerySerializer(career_fair_gallery_list, many=True).data


class CareerFairRetrieveUpdateSerializer(ItemCreateUpdateSerializer):
    career_fair_sessions = SessionRetrieveSerializer(many=True)
    career_fair_supports = SupportRetrieveSerializer(many=True)
    career_fair_speakers = SpeakerRetrieveSerializer(many=True)
    career_fair_products = CareerFairAndProductRetrieveSerializer(many=True)

    item_type = serializers.SerializerMethodField()
    # is_fav_item = serializers.SerializerMethodField()
    # is_applied_by_user = serializers.SerializerMethodField()
    slug = serializers.ReadOnlyField()
    # entity_logo = serializers.SerializerMethodField(read_only=True)
    entity = serializers.StringRelatedField()
    # entity = EntitySerializer()

    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = CareerFair
        exclude = ['owner', 'category']
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(CareerFairRetrieveUpdateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    @transaction.atomic
    def update(self, instance, validated_data):

        career_fair_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create career fair.")
            raise ICFException("Unknown user, cannot create career fair.", status_code=status.HTTP_400_BAD_REQUEST)

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            # location, address_created = Address.objects.update_or_create(userprofile=instance, **location_data)
            location, address_created = Address.objects.update_or_create(**location_data)
            instance.location = location

        cf_session_data = validated_data.get('career_fair_sessions', None)
        cf_support_data = validated_data.get('career_fair_supports', None)
        cf_speaker_data = validated_data.get('career_fair_speakers', None)

        cf_session_data = validated_data.pop('career_fair_sessions')
        cf_support_data = validated_data.pop('career_fair_supports')
        cf_speaker_data = validated_data.pop('career_fair_speakers')
        cf_product_data = validated_data.pop('career_fair_products')

        prev_career_fair_status = instance.status
        prev_start_date = instance.start_date
        prev_end_date = instance.expiry

        current_status = validated_data.get('status')
        curr_start_date = validated_data.get('start_date')
        curr_end_date = validated_data.get('expiry')

        is_sponsored = validated_data.get('is_sponsored')
        sponsored_start_dt = validated_data.get('sponsored_start_dt')
        sponsored_end_dt = validated_data.get('sponsored_end_dt')

        ########################################
        # Getting published for the first time
        ########################################
        if prev_career_fair_status != current_status and current_status == Item.ITEM_UNDER_REVIEW:
            logger.info("Publishing the career fair first time : {}.\n".format(instance.slug))
            is_allowed_interval = ICFCreditManager.is_allowed_interval(curr_start_date, curr_end_date)
            if not is_allowed_interval:
                logger.exception("Invalid duration for posting the career fair. "
                                 "The career fair's start date should be between {X} and {Y}.\n"
                                 .format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date)))
                raise ICFException(_("The career fair's start date should be between {X} and {Y}."
                                     .format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date))))
            # intervals = ICFCreditManager.get_num_of_intervals(curr_start_date, curr_end_date, 'create_job')
            # ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model, action='create_job',
            #                                    intervals=intervals)

            ICFCreditManager.manage_entity_subscription(entity=instance.entity, action=CREATE_CAREER_FAIR,
                                                        item_start_date=curr_start_date,
                                                        item_end_date=curr_end_date,
                                                        user=user, app=career_fair_model)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid values for sponsored start date and sponsored end date.\n")
                    raise ICFException(_("Please provide career fair's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # A career fair can be sponsored anywhere during the period when the career fair is active.
                if sponsored_start_dt >= curr_start_date and sponsored_end_dt <= curr_end_date:
                    intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
                                                                      SPONSORED_CAREER_FAIR)
                    Sponsored.objects.create(content_object=instance,
                                             start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                    ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=career_fair_model,
                                                       action=SPONSORED_CAREER_FAIR,
                                                       intervals=intervals)
                    instance.is_sponsored = True
                    instance.sponsored_start_dt = sponsored_start_dt
                    instance.sponsored_end_dt = sponsored_end_dt
                else:
                    logger.exception(
                        "Duration for sponsoring career fair not within the career fair posting duration.\n")
                    raise ICFException(_("The start date of your sponsored career fair campaign cannot be before {X} "
                                         "and the end date cannot be after {Y}.".format(X=str(curr_start_date.date()),
                                                                                        Y=str(curr_end_date.date()))),
                                       status_code=status.HTTP_400_BAD_REQUEST)

        ######################################
        # Updating an already published career fair
        ######################################
        if prev_career_fair_status == current_status and current_status == Item.ITEM_UNDER_REVIEW:
            logger.info("Updating a published career fair : {}.\n".format(instance.slug))

            if prev_start_date != curr_start_date:
                if prev_start_date.date() < datetime.now(pytz.utc).date():
                    logger.exception("Cannot change start date for an active and published career fair.\n")
                    raise ICFException(_("You cannot change the start date for an active and published career fair."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                elif curr_start_date.date() < datetime.now(pytz.utc).date():
                    logger.exception(
                        "The start date cannot be before {X}.\n".format(X=str(datetime.now(pytz.utc).date())))
                    raise ICFException(
                        _("The start date cannot be before {X}.".format(X=str(datetime.now(pytz.utc).date()))),
                        status_code=status.HTTP_400_BAD_REQUEST)

            if curr_end_date.date() < datetime.now(pytz.utc).date():
                logger.exception("The end date cannot be before {X}.\n".format(X=str(datetime.now(pytz.utc).date())))
                raise ICFException(_("The end date cannot be before {X}.".format(X=str(datetime.now(pytz.utc).date()))),
                                   status_code=status.HTTP_400_BAD_REQUEST)

            # Charge for the difference in duration.
            intervals = ICFCreditManager.change_to_interval(prev_start_date, prev_end_date, curr_start_date,
                                                            curr_end_date, action=CREATE_CAREER_FAIR)
            if intervals:
                # ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=job_model,
                #                                    action=CREATE_JOB, intervals=intervals)

                ICFCreditManager.manage_entity_subscription(entity=instance.entity, action=CREATE_CAREER_FAIR,
                                                            item_start_date=curr_start_date,
                                                            item_end_date=curr_end_date,
                                                            user=user, app=career_fair_model)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid values for sponsored start date and sponsored end date.\n")
                    raise ICFException(_("Please provide career fair's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # Check if the career fair was already sponsored before
                try:

                    # The career fair was already sponsored. Charge for the difference if any in the duration.
                    sponsored = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_ACTIVE)

                    prev_sponsored_start_date = sponsored.start_date
                    prev_sponsored_end_date = sponsored.end_date

                    if prev_sponsored_start_date != sponsored_start_dt:
                        if prev_sponsored_start_date < datetime.now(pytz.utc):
                            logger.exception("Cannot change start date of an already sponsored career fair.\n")
                            raise ICFException(
                                _("You cannot change the start date of an ongoing sponsored career fair campaign."),
                                status_code=status.HTTP_400_BAD_REQUEST)
                        elif sponsored_start_dt < datetime.now(pytz.utc) or \
                                sponsored_start_dt > curr_end_date:
                            logger.exception(
                                "Invalid start date for sponsoring the career fair. The Sponsored career fair start date "
                                "should be between {X} and {Y}.\n".
                                    format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                            raise ICFException(_("The Sponsored career fair start date should be between "
                                                 "{X} and {Y}.".format(X=str(datetime.now(pytz.utc).date()),
                                                                       Y=str(curr_end_date.date()))),
                                               status_code=status.HTTP_400_BAD_REQUEST)

                    if sponsored_end_dt < datetime.now(pytz.utc) or \
                            sponsored_end_dt > curr_end_date:
                        logger.exception(
                            "Invalid end date for sponsoring the career fair. The Sponsored career fair end date "
                            "should be between {X} and {Y}.\n".
                                format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                        raise ICFException(_("The Sponsored career fair end date should be between "
                                             "{X} and {Y}.".format(X=str(datetime.now(pytz.utc).date()),
                                                                   Y=str(curr_end_date.date()))),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                    sponsored.start_date = sponsored_start_dt
                    sponsored.end_date = sponsored_end_dt
                    sponsored.status = Sponsored.SPONSORED_ACTIVE
                    sponsored.save(update_fields=['start_date', 'end_date', 'status'])
                    # Charge for the difference in duration.
                    intervals = ICFCreditManager.change_to_interval(prev_sponsored_start_date,
                                                                    prev_sponsored_end_date, sponsored_start_dt,
                                                                    sponsored_end_dt, action=SPONSORED_CAREER_FAIR)
                    if intervals:
                        ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=career_fair_model,
                                                           action=SPONSORED_CAREER_FAIR, intervals=intervals)

                except Sponsored.DoesNotExist:
                    # to check whether career fair is already sponsored and inactive
                    try:
                        pre_sponsored = Sponsored.objects.get(object_id=instance.id,
                                                              status=Sponsored.SPONSORED_INACTIVE)
                        # delete to avoid redundant row in table
                        pre_sponsored.delete()
                    except ObjectDoesNotExist:
                        pass

                    # Career Fair sponsored first time during this update, did not exist earlier

                    if sponsored_start_dt >= curr_start_date and sponsored_end_dt <= curr_end_date:
                        intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
                                                                          SPONSORED_CAREER_FAIR)
                        Sponsored.objects.create(content_object=instance,
                                                 start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                        ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=career_fair_model,
                                                           action=SPONSORED_CAREER_FAIR,
                                                           intervals=intervals)
                        instance.is_sponsored = True
                        instance.sponsored_start_dt = sponsored_start_dt
                        instance.sponsored_end_dt = sponsored_end_dt
                    else:
                        logger.exception(
                            "Duration for sponsoring career fair not within the career fair posting duration.\n")
                        raise ICFException(_("The start date of your sponsored career fair campaign cannot "
                                             "be before {X} and the end date cannot be after {Y}."
                                             .format(X=str(curr_start_date.date()), Y=str(curr_end_date.date()))),
                                           status_code=status.HTTP_400_BAD_REQUEST)

            else:
                # Check if an earlier sponsored career fair has been removed
                try:
                    sponsored = Sponsored.objects.get(object_id=instance.id)
                    sponsored.status = Sponsored.SPONSORED_INACTIVE
                    sponsored.save(update_fields=["status"])
                except Sponsored.DoesNotExist:
                    pass

        """
        PROCESS SESSION
        """
        # career fair session, support, speaker and products
        old_session_ids = Session.objects.filter(career_fair=instance).values_list('id', flat=True)

        # To force django to execute the query and not do lazy load
        old_session_count = len(old_session_ids)
        logger.debug("Sessions already existing - {}".format(len(old_session_ids)))

        # If there are new sessions, create. They will come from the UI without id field
        if cf_session_data:
            new_sessions = [session for session in cf_session_data if session.get('id') == None]
            for session_d in new_sessions:
                session_dict = session_d
                session_obj, session_created = Session.objects.update_or_create(career_fair=instance, **session_dict)

        # Find existing sessions from UI
        session_data_ids = [ui_session.get('id') for ui_session in cf_session_data if ui_session.get('id')]

        # Remove the sessions in the DB that are not present in the list from UI.
        sessions_to_remove = set(old_session_ids) - set(session_data_ids)

        logger.debug("Sessions to remove - {}".format(sessions_to_remove))
        for remove_session in sessions_to_remove:
            """
            Before removing session, the speaker session and the speakers associated with the session should be removed.
            """
            speaker_ids_for_session = SpeakerAndSession.objects.filter(session__id=remove_session).values_list(
                'speaker', flat=True)
            SpeakerAndSession.objects.filter(session__id=remove_session).delete()
            Speaker.objects.filter(id__in=speaker_ids_for_session).delete()
            logger.debug("Removing Session - {}".format(remove_session))
            Session.objects.filter(id=remove_session).delete()

            """
            The speaker information should also be removed from the list of speakers coming from UI. This should be done before
            processing the speaker data.
            """
            if cf_speaker_data:
                for speaker_id in speaker_ids_for_session:
                    remaining_speakers = [speaker for speaker in cf_speaker_data if
                                          not (speaker.get('id') == speaker_id)]
                    cf_speaker_data = remaining_speakers

        """
        PROCESS SUPPORT
        """
        # career fair session, support, speaker and products
        old_support_ids = Support.objects.filter(career_fair=instance).values_list('id', flat=True)
        old_support_count = len(old_support_ids)
        logger.debug("Support already existing - {}".format(old_support_count))
        if cf_support_data:
            # # # cf_support_data  is a list of dictionaries
            new_supports = [support for support in cf_support_data if support.get('id') == None]
            for support_d in new_supports:
                support_dict = support_d
                support_obj, support_created = Support.objects.update_or_create(career_fair=instance, **support_dict)

        # Find existing supports from UI
        support_data_ids = [support.get('id') for support in cf_support_data if support.get('id')]

        # Remove the supports in the DB that are not present in the list from UI.
        supports_to_remove = set(old_support_ids) - set(support_data_ids)
        logger.debug("Supports to remove - {}".format(supports_to_remove))

        for remove_support in supports_to_remove:
            Support.objects.filter(id=remove_support).delete()

        # """
        # PROCESS SPEAKER
        # """
        old_speaker_ids = Speaker.objects.filter(career_fair=instance).values_list('id', flat=True)
        old_speaker_count = len(old_speaker_ids)
        logger.debug("Speakers already existing - {}".format(old_speaker_count))

        if cf_speaker_data:
            new_speakers = [speaker for speaker in cf_speaker_data if speaker.get('id') == None]
            for speaker_d in new_speakers:
                speaker_dict = speaker_d
                # image = speaker_dict.pop('image')
                speaker_sessions = speaker_dict.pop('speaker_sessions')
                speaker_obj, speaker_created = Speaker.objects.update_or_create(career_fair=instance, **speaker_dict)

                # if image:
                #     SpeakerProfileImage.objects.update_or_create(speaker=speaker_obj, image=image)

                if speaker_sessions:
                    # each item in the list is session id
                    for session_obj in speaker_sessions:
                        try:

                            session_obj_id = session_obj.get('id')
                            session_obj_db = None
                            if isinstance(session_obj, Session):
                                session_obj_db = session_obj
                            else:
                                session_obj_db = Session.objects.get(**session_obj)
                            if session_obj_db.pk:
                                speaker_session, speaker_session_created = SpeakerAndSession.objects.update_or_create(
                                    speaker=speaker_obj,
                                    session=session_obj_db)

                        except Session.DoesNotExist as s:
                            logger.exception("Session object not found.\n")
                            raise ICFException(_("Could not create career fair, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        except ObjectDoesNotExist as obe:
                            logger.exception("Object does not exist")

        # Find existing speakers from UI
        speaker_data_ids = [speaker.get('id') for speaker in cf_speaker_data if speaker.get('id')]

        # Remove the speaker sessions and speakers in the DB that are not present in the list from UI.
        speakers_to_remove = set(old_speaker_ids) - set(speaker_data_ids)
        logger.debug("Speakers to remove - {}".format(speakers_to_remove))

        if speakers_to_remove:
            SpeakerAndSession.objects.filter(speaker__id__in=speakers_to_remove).delete()
            Speaker.objects.filter(id__in=speakers_to_remove).delete()
        is_ad_already_exist = 0
        if cf_product_data:
            # # # cf_product_data  is a list of dictionaries
            for career_fair_and_product_dict in cf_product_data:
                product_dict = career_fair_and_product_dict.pop('product')
                product_sub_type = career_fair_and_product_dict.pop('product_sub_type')
                if product_sub_type == CareerFairProductSubType.ADVERTISEMENT:
                    #     career_fair_and_product_obj = CareerFairAndProduct.objects.filter(career_fair=instance,
                    #                                                                       product_sub_type=product_sub_type)
                    is_advertisement_already_exist = CareerFairAdvertisement.objects.filter(career_fair=instance,
                                                                                            entity=instance.entity)
                    if is_advertisement_already_exist.count() == 0:
                        is_ad_already_exist = 1
                        link = "no link now"
                        CareerFairUtil.send_add_advertisement_link_to_owner(instance.entity, user, link)

                career_fair_and_product_id = None
                if career_fair_and_product_dict.get('id'):
                    career_fair_and_product_id = career_fair_and_product_dict.pop('id')

                currency_code = product_dict.pop('currency')
                currency_obj = Currency.objects.get(code=currency_code.upper())
                if product_dict.get('id'):
                    product_obj = Product.objects.get(id=product_dict.get('id'))
                    product_obj.is_active = product_dict.get('is_active')
                    product_obj.save()

                else:
                    product_obj = Product.objects.create(currency=currency_obj,
                                                         entity=instance.entity,
                                                         **product_dict)
                    if is_ad_already_exist == 1:
                        CareerFairAdvertisement.objects.create(
                            user=user,
                            career_fair=instance,
                            entity=instance.entity,
                            product=product_obj,
                            ad_image_type=CareerFairImageType.DESKTOP_IMAGE

                        )
                        CareerFairAdvertisement.objects.create(
                            user=user,
                            career_fair=instance,
                            entity=instance.entity,
                            product=product_obj,
                            ad_image_type=CareerFairImageType.MOBILE_IMAGE

                        )

                if career_fair_and_product_id:
                    career_fair_product_obj = CareerFairAndProduct.objects.get(
                        id=career_fair_and_product_id)
                    career_fair_product_obj.product = product_obj
                    career_fair_product_obj.career_fair = instance
                    career_fair_product_obj.product_sub_type = product_sub_type
                    career_fair_product_obj.save()
                else:
                    career_fair_and_product = CareerFairAndProduct.objects.create(
                        career_fair=instance,
                        product=product_obj,
                        product_sub_type=product_sub_type)
                    # to do anoop

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    # def get_is_fav_item(self, obj):
    #     request = self.context.get("request")
    #
    #     try:
    #         fav = FavoriteItem.objects.get(user=request.user,item=obj)
    #         if fav is not None:
    #             return True
    #         else:
    #             return False
    #     except ObjectDoesNotExist as e:
    #         logger.debug(e)
    #         return False

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    # def get_entity_logo(self, obj):
    #     try:
    #         return Logo.objects.get(entity=obj.entity).image.url
    #     except ObjectDoesNotExist as e:
    #         logger.debug(e)
    #         return None


class SessionObjectOptionalRetrieveSerializer(ModelSerializer):
    class Meta:
        model = SessionOptional
        exclude = ['career_fair', 'slug']


class CareerFairDraftRetrieveTestSerializer(ItemCreateUpdateDraftSerializer):
    career_fair_optional_sessions = SessionOptionalRetrieveSerializer(many=True)
    career_fair_optional_supports = SupportOptionalRetrieveSerializer(many=True)
    career_fair_optional_speakers = SpeakerOptionalRetrieveTestSerializer(many=True)
    slug = serializers.ReadOnlyField()
    item_type = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    # entity = serializers.StringRelatedField()
    entity = EntitySerializer()
    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)
    career_fair_draft_products = CareerFairAndProductOptionalRetrieveSerializer(many=True, )
    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = CareerFairDraft
        exclude = ['owner', 'category']
        extra_fields = ['entity', 'item_type', 'entity_logo', 'hero_image', 'gallery_images',
                        'career_fair_optional_sessions',
                        'career_fair_optional_supports', 'career_fair_optional_speakers', 'career_fair_draft_products']
        # fields = (
        #     'id',
        #     'title',
        #     'entity',
        #     'item_type',
        #     'entity_logo',
        #     'description',
        #     'location',
        #     'status',
        #     'expiry',
        #     'slug',
        #     'start_date',
        #     'start_time',
        #     'end_time',
        #     'organiser_contact_email',
        #     'organiser_contact_phone',
        #     'hero_image',
        #     'gallery_images',
        #     'career_fair_draft_products',
        #     'career_fair_optional_sessions',
        #     'career_fair_optional_supports',
        #     'career_fair_optional_speakers',
        #     'created',
        #     'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None

    def get_hero_image(self, obj):
        try:
            career_fair_galley_obj = CareerFairGalleryOptional.objects.filter(career_fair=obj,
                                                                              image_type=CareerFairGalleryOptional.HERO).last()
            if career_fair_galley_obj:
                return CareerFairGalleryOptional.objects.filter(career_fair=obj,
                                                                image_type=CareerFairGalleryOptional.HERO).last().image.url
            else:
                return None
        except CareerFairGalleryOptional.DoesNotExist:
            return None

    def get_gallery_images(self, obj):
        career_fair_gallery_list = CareerFairGalleryOptional.objects.filter(career_fair=obj,
                                                                            image_type=CareerFairGalleryOptional.GALLERY).order_by(
            'created')

        return CareerFairDraftGallerySerializer(career_fair_gallery_list, many=True).data


class CareerFairDraftRetrieveUpdateSerializer(ItemCreateUpdateDraftSerializer):
    career_fair_optional_sessions = SessionOptionalRetrieveSerializer(many=True)
    career_fair_optional_supports = SupportOptionalRetrieveSerializer(many=True)
    career_fair_optional_speakers = SpeakerOptionalRetrieveSerializer(many=True)
    slug = serializers.ReadOnlyField()
    item_type = serializers.SerializerMethodField()
    # entity_logo = serializers.SerializerMethodField(read_only=True)
    entity = serializers.StringRelatedField()
    # entity = EntitySerializer()
    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)
    career_fair_draft_products = CareerFairAndProductOptionalRetrieveSerializer(many=True)

    class Meta:
        model = CareerFairDraft
        exclude = ['owner', 'category']
        # extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    # def get_field_names(self, declared_fields, info):
    #     expanded_fields = super(CareerFairDraftRetrieveUpdateSerializer, self).get_field_names(declared_fields, info)
    #
    #     if getattr(self.Meta, 'extra_fields', None):
    #         return expanded_fields + self.Meta.extra_fields
    #     else:
    #         return expanded_fields

    @transaction.atomic
    def update(self, instance, validated_data):

        career_fair_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create draft career fair")
            raise ICFException("Unknown user, cannot create draft career fair", status_code=status.HTTP_400_BAD_REQUEST)

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            location, address_created = AddressOptional.objects.update_or_create(userprofile=instance, **location_data)
            instance.location = location

        cf_session_optional_data = validated_data.get('career_fair_optional_sessions', None)
        cf_support_optional_data = validated_data.get('career_fair_optional_supports', None)
        cf_speaker_optional_data = validated_data.get('career_fair_optional_speakers', None)
        #
        # # if cf_session_optional_data:
        cf_session_optional_data = validated_data.pop('career_fair_optional_sessions')
        #
        # # if cf_support_optional_data:
        cf_support_optional_data = validated_data.pop('career_fair_optional_supports')
        #
        # # if cf_speaker_optional_data:
        cf_speaker_optional_data = validated_data.pop('career_fair_optional_speakers')
        ############################################ SESSION #############################################################
        old_session_ids = SessionOptional.objects.filter(career_fair=instance).values_list('id', flat=True)
        # To force django to execute the query and not do lazy load
        old_session_count = len(old_session_ids)
        logger.debug("Sessions already existing - {}".format(len(old_session_ids)))

        # If there are new sessions, create. They will come from the UI without id field
        if cf_session_optional_data:
            # to avoid redundancy of SessionOptional
            new_sessions = [session for session in cf_session_optional_data if session.get('id') == None]
            for session_d in cf_session_optional_data:
                session_dict = session_d
                session_optional_obj, session_created = SessionOptional.objects.update_or_create(career_fair=instance,
                                                                                                 **session_dict)
        # Find existing sessions from UI
        session_data_ids = [ui_session.get('id') for ui_session in cf_session_optional_data if ui_session.get('id')]

        # Remove the sessions in the DB that are not present in the list from UI.
        sessions_to_remove = set(old_session_ids) - set(session_data_ids)

        logger.debug("Sessions to remove - {}".format(sessions_to_remove))
        for remove_session in sessions_to_remove:
            """
            Before removing session, the speaker session and the speakers associated with the session should be removed.
            """
            speaker_ids_for_session = SpeakerAndSessionOptional.objects.filter(session__id=remove_session).values_list(
                'speaker', flat=True)
            SpeakerAndSessionOptional.objects.filter(session__id=remove_session).delete()
            SpeakerOptional.objects.filter(id__in=speaker_ids_for_session).delete()
            logger.debug("Removing Session - {}".format(remove_session))
            SessionOptional.objects.filter(id=remove_session).delete()

            """
            The speaker information should also be removed from the list of speakers coming from UI. This should be done before
            processing the speaker data.
            """
            if cf_speaker_optional_data:
                for speaker_id in speaker_ids_for_session:
                    remaining_speakers = [speaker for speaker in speaker_ids_for_session if
                                          not (speaker.get('id') == speaker_id)]
                    speaker_ids_for_session = remaining_speakers
        ######################################### SUPPORT #################################################################
        old_support_ids = SupportOptional.objects.filter(career_fair=instance).values_list('id', flat=True)
        old_support_count = len(old_support_ids)
        logger.debug("Support already existing - {}".format(old_support_count))
        if cf_support_optional_data:
            # # # cf_support_optional_data  is a list of dictionaries
            new_supports = [support for support in cf_support_optional_data if support.get('id') == None]
            for support_d in cf_support_optional_data:
                support_dict = support_d
                support_optional_obj, support_created = SupportOptional.objects.update_or_create(career_fair=instance,
                                                                                                 **support_dict)
                # Find existing supports from UI
        support_data_ids = [support.get('id') for support in cf_support_optional_data if support.get('id')]

        # Remove the supports in the DB that are not present in the list from UI.
        supports_to_remove = set(old_support_ids) - set(support_data_ids)
        logger.debug("Supports to remove - {}".format(supports_to_remove))

        for remove_support in supports_to_remove:
            SupportOptional.objects.filter(id=remove_support).delete()
        ##################################### SPEAKER ##########################################################################
        old_speaker_ids = SpeakerOptional.objects.filter(career_fair=instance).values_list('id', flat=True)
        old_speaker_count = len(old_speaker_ids)
        logger.debug("Speakers already existing - {}".format(old_speaker_count))
        if cf_speaker_optional_data:
            # SpeakerOptional.objects.filter(career_fair=instance).delete()
            new_speakers = [speaker for speaker in cf_speaker_optional_data if speaker.get('id') == None]
            for speaker_d in cf_speaker_optional_data:
                speaker_dict = speaker_d

                speaker_sessions = speaker_dict.pop('speaker_sessions')
                speaker_optional_obj, speaker_created = SpeakerOptional.objects.update_or_create(career_fair=instance,
                                                                                                 **speaker_dict)
                if speaker_sessions:
                    # each item in the list is session id
                    for session_obj in speaker_sessions:
                        try:

                            session_obj_id = session_obj.get('id')
                            if isinstance(session_obj, SessionOptional):
                                session_optional_obj = session_obj
                            else:
                                session_optional_obj = SessionOptional.objects.get(**session_obj)
                            if session_optional_obj.pk:
                                speaker_session, speaker_session_created = SpeakerAndSessionOptional.objects.update_or_create(
                                    speaker=speaker_optional_obj,
                                    session=session_optional_obj)
                        except SessionOptional.DoesNotExist as s:
                            logger.exception("SessionOptional object not found.\n")
                            raise ICFException(_("Could not create career fair, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        except ObjectDoesNotExist as obe:
                            logger.exception("Object does not exist")

        # Find existing speakers from UI
        speaker_data_ids = [speaker.get('id') for speaker in cf_speaker_optional_data if speaker.get('id')]

        # Remove the speaker sessions and speakers in the DB that are not present in the list from UI.
        speakers_to_remove = set(old_speaker_ids) - set(speaker_data_ids)
        logger.debug("Speakers to remove - {}".format(speakers_to_remove))

        if speakers_to_remove:
            SpeakerAndSessionOptional.objects.filter(speaker__id__in=speakers_to_remove).delete()
            SpeakerOptional.objects.filter(id__in=speakers_to_remove).delete()
        ####################################### PRODUCT #############################################################
        cf_product_optional_data = validated_data.pop("career_fair_draft_products")

        if cf_product_optional_data:

            # # # cf_product_data  is a list of dictionaries
            for career_fair_and_product_dict in cf_product_optional_data:
                product_dict = career_fair_and_product_dict.pop('product')
                product_sub_type = career_fair_and_product_dict.pop('product_sub_type')
                career_fair_and_product_optional_id = None
                if career_fair_and_product_dict.get('id'):
                    career_fair_and_product_optional_id = career_fair_and_product_dict.pop('id')

                currency_code = product_dict.pop('currency')
                currency_obj = Currency.objects.get(code=currency_code.upper())
                if product_dict.get('id'):
                    product_obj = ProductDraft.objects.get(id=product_dict.get('id'))
                    product_obj.is_active = product_dict.get('is_active')
                    product_obj.save()

                else:
                    product_obj = ProductDraft.objects.create(currency=currency_obj,
                                                              entity=instance.entity,
                                                              **product_dict)

                # product_obj, product_obj_created = ProductDraft.objects.update_or_create(currency=currency_obj,
                #                                                                          entity=instance.entity,
                #                                                                          **product_dict)

                if career_fair_and_product_optional_id:
                    career_fair_product_optional_obj = CareerFairAndProductOptional.objects.get(
                        id=career_fair_and_product_optional_id)
                    career_fair_product_optional_obj.product = product_obj
                    career_fair_product_optional_obj.career_fair = instance
                    career_fair_product_optional_obj.product_sub_type = product_sub_type
                    career_fair_product_optional_obj.save()
                else:
                    career_fair_and_product_optional = CareerFairAndProductOptional.objects.create(
                        career_fair=instance,
                        product=product_obj,
                        product_sub_type=product_sub_type)

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    # def get_entity_logo(self, obj):
    #     try:
    #         return Logo.objects.get(entity=obj.entity).image.url
    #     except ObjectDoesNotExist as e:
    #         logger.debug(e)
    #         return None


class CareerFairRetrieveSerializer(ModelSerializer):
    location = AddressRetrieveSerializer()
    item_type = serializers.SerializerMethodField()

    entity = EntitySerializer()

    career_fair_sessions = SessionRetrieveSerializer(many=True)
    career_fair_supports = SupportRetrieveSerializer(many=True)
    career_fair_speakers = SpeakerRetrieveSerializer(many=True)
    career_fair_products = CareerFairAndProductRetrieveSerializer(many=True)

    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = CareerFair
        fields = (
            'id',
            'title',
            'entity',
            'item_type',
            'description',
            'location',
            'status',
            'expiry',
            'slug',
            'start_date',
            'start_time',
            'end_time',
            'organiser_contact_email',
            'organiser_contact_phone',
            'hero_image',
            'gallery_images',
            'career_fair_sessions',
            'career_fair_supports',
            'career_fair_speakers',
            'career_fair_products',
            'created',
            'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None

    def get_hero_image(self, obj):
        try:
            career_fair_galley_obj = CareerFairGallery.objects.filter(career_fair=obj,
                                                                      image_type=CareerFairGallery.HERO).last()
            if career_fair_galley_obj:
                return CareerFairGallery.objects.filter(career_fair=obj,
                                                        image_type=CareerFairGallery.HERO).last().image.url
            else:
                return None
        except CareerFairGallery.DoesNotExist:
            return None

    def get_gallery_images(self, obj):
        career_fair_gallery_list = CareerFairGallery.objects.filter(career_fair=obj,
                                                                    image_type=CareerFairGallery.GALLERY).order_by(
            'created')
        return CareerFairGallerySerializer(career_fair_gallery_list, many=True).data


class CareerFairDraftRetrieveSerializer(ModelSerializer):
    location = AddressOptionalSerializer()
    career_fair_optional_sessions = SessionOptionalRetrieveSerializer(many=True)
    career_fair_optional_supports = SupportOptionalRetrieveSerializer(many=True)
    career_fair_optional_speakers = SpeakerOptionalRetrieveSerializer(many=True)
    career_fair_draft_products = CareerFairAndProductOptionalRetrieveSerializer(many=True)
    item_type = serializers.SerializerMethodField()

    entity = EntitySerializer()
    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = CareerFairDraft
        fields = (
            'id',
            'title',
            'entity',
            'item_type',
            'description',
            'location',
            'status',
            'expiry',
            'slug',
            'start_date',
            'start_time',
            'end_time',
            'organiser_contact_email',
            'organiser_contact_phone',
            'hero_image',
            'gallery_images',
            'career_fair_draft_products',
            'career_fair_optional_sessions',
            'career_fair_optional_supports',
            'career_fair_optional_speakers',
            'created',
            'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None

    def get_hero_image(self, obj):
        try:
            career_fair_galley_obj = CareerFairGalleryOptional.objects.filter(career_fair=obj,
                                                                              image_type=CareerFairGalleryOptional.HERO).last()
            if career_fair_galley_obj:
                return CareerFairGalleryOptional.objects.filter(career_fair=obj,
                                                                image_type=CareerFairGalleryOptional.HERO).last().image.url
            else:
                return None
        except CareerFairGalleryOptional.DoesNotExist:
            return None

    def get_gallery_images(self, obj):
        career_fair_gallery_list = CareerFairGalleryOptional.objects.filter(career_fair=obj,
                                                                            image_type=CareerFairGalleryOptional.GALLERY).order_by(
            'created')

        return CareerFairDraftGallerySerializer(career_fair_gallery_list, many=True).data


class CareerFairListSerializer(ItemListSerializer):
    class Meta(ItemListSerializer.Meta):
        model = CareerFair
        fields = ItemListSerializer.Meta.fields + ('organiser_contact_email', 'organiser_contact_phone',
                                                   'entity')


class CareerFairDraftListSerializer(ItemDraftListSerializer):
    class Meta(ItemDraftListSerializer.Meta):
        model = CareerFairDraft
        fields = ItemDraftListSerializer.Meta.fields + ('organiser_contact_email', 'organiser_contact_phone',
                                                        'entity', 'mode_of_cf')


class EntityCareerFairListSerializer(ItemListSerializer):
    is_sponsored_career_fair = serializers.SerializerMethodField()

    # no_of_views = serializers.SerializerMethodField()
    # no_of_participants = serializers.SerializerMethodField()

    class Meta(ItemListSerializer.Meta):
        model = CareerFair
        fields = ItemListSerializer.Meta.fields + ('organiser_contact_email', 'organiser_contact_phone',
                                                   'entity', 'is_sponsored_career_fair', 'mode_of_cf')

    def get_is_sponsored_career_fair(self, obj):
        try:

            content_type = ContentType.objects.get(model='careerfair')
            sponsored_career_fair = Sponsored.objects.filter(object_id=obj.id, content_type=content_type.id,
                                                             status=Sponsored.SPONSORED_ACTIVE).last()

            if sponsored_career_fair:
                if sponsored_career_fair.start_date <= datetime.now(pytz.utc) < sponsored_career_fair.end_date:
                    return True
                else:
                    return False
            else:
                return False
        except Sponsored.DoesNotExist as e:
            logger.debug(e)
            return False

    # def get_no_of_participants(self, obj):
    #     return CareerFairParticipant.objects.filter(career_fair=obj,
    #                                                 participant_type=CareerFairParticipant.INDIVIDUAL).count()


# class ProductDraftRetrieveSerializer(ModelSerializer):
#
#     class Meta:
#         model = ProductDraft
#         fields = '__all__'


# class CareerFairAndProductOptionalRetrieveSerializer(ModelSerializer):
#
#     product = ProductDraftRetrieveSerializer()
#
#     class Meta:
#         model = CareerFairAndProductOptional
#         fields = '__all__'
#

class CareerFairDraftCreateSerializer(ItemCreateUpdateDraftSerializer):
    career_fair_optional_sessions = SessionOptionalRetrieveSerializer(many=True)
    career_fair_optional_supports = SupportOptionalRetrieveSerializer(many=True)
    career_fair_optional_speakers = SpeakerOptionalRetrieveSerializer(many=True)
    slug = serializers.ReadOnlyField()
    item_type = serializers.SerializerMethodField()
    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)
    career_fair_draft_products = CareerFairAndProductOptionalRetrieveSerializer(many=True)

    class Meta:
        model = CareerFairDraft
        exclude = ['owner', 'category']
        # extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    # def get_field_names(self, declared_fields, info):
    #     expanded_fields = super(CareerFairDraftCreateSerializer, self).get_field_names(declared_fields, info)
    #
    #     if getattr(self.Meta, 'extra_fields', None):
    #         return expanded_fields + self.Meta.extra_fields
    #     else:
    #         return expanded_fields

    def create(self, validated_data):

        cf_session_optional_data = validated_data.get('career_fair_optional_sessions', None)
        cf_support_optional_data = validated_data.get('career_fair_optional_supports', None)
        cf_speaker_optional_data = validated_data.get('career_fair_optional_speakers', None)
        cf_draft_optional_data = validated_data.get('career_fair_draft_products', None)

        location_data = validated_data.pop("location")
        location = AddressOptional.objects.create(**location_data)

        # sponsored_start_dt = validated_data.pop('sponsored_start_dt')
        # sponsored_end_dt = validated_data.pop('sponsored_end_dt')
        # is_sponsored = validated_data.pop('is_sponsored')

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create career fair.")
            raise ICFException(_("Unknown user, cannot create career fair."), status_code=status.HTTP_400_BAD_REQUEST)

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('expiry')
        entity = validated_data.get("entity")

        try:
            type_obj = Type.objects.get(slug='career fair')
            category_name = 'career fair category'
            try:
                category_obj = Category.objects.get(name=category_name, type=type_obj)
            except Category.DoesNotExist as tdn:
                category_obj = Category.objects.create(name=category_name,
                                                       description='career fair category description', type=type_obj)
        except Type.DoesNotExist as tdn:
            logger.exception("Invalid category type for career fair.\n")
            raise ICFException(_("Invalid category type for career fair, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Category.DoesNotExist as tdn:
            logger.exception("category object not found for career fair.\n")
            raise ICFException(_("Invalid category type for career fair, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        # if cf_session_optional_data:
        cf_session_optional_data = validated_data.pop('career_fair_optional_sessions')

        # if cf_support_optional_data:
        cf_support_optional_data = validated_data.pop('career_fair_optional_supports')

        # if cf_speaker_optional_data:
        cf_speaker_optional_data = validated_data.pop('career_fair_optional_speakers')

        # currency = Currency.objects.get(code='USD')
        cf_product_optional_data = validated_data.pop('career_fair_draft_products')
        # cf_product_optional_data = [{'name': 'Free Participation Ticket', 'entity': entity, 'unit': 1, 'cost': 10, 'currency': currency, 'is_active': True, 'description': 'Individual Participation Ticket  Description', 'product_type': 4, 'buyer_type': 1, 'product_sub_type': 1}]

        title = validated_data.pop('title')
        title_en = validated_data.pop('title_en')
        title_fr = validated_data.pop('title_fr')
        title_es = validated_data.pop('title_es')

        description = validated_data.pop('description')
        description_en = validated_data.pop('description_en')
        description_fr = validated_data.pop('description_fr')
        description_es = validated_data.pop('description_es')

        # career_fair_draft = CareerFairDraft.objects.create(owner=user, location=location, item_type=type_obj, category=category_obj,
        #                         title=title, title_en=title, title_fr=title, title_es=title,
        #                          description=description, description_en=description, description_es=description,
        #                          description_fr=description, **validated_data)

        career_fair_draft = CareerFairDraft.objects.create(owner=user, location=location, item_type=type_obj,
                                                           category=category_obj,
                                                           title=title, title_en=title, title_fr=title_fr,
                                                           title_es=title_es,
                                                           description=description, description_en=description,
                                                           description_es=description_es,
                                                           description_fr=description_fr, **validated_data)

        career_fair_model = ContentType.objects.get_for_model(career_fair_draft)

        if cf_session_optional_data:
            for session_d in cf_session_optional_data:
                session_dict = session_d
                SessionOptional.objects.create(career_fair=career_fair_draft, **session_dict)

        if cf_support_optional_data:
            # # # cf_support_optional_data  is a list of dictionaries
            for support_d in cf_support_optional_data:
                support_dict = support_d
                SupportOptional.objects.create(career_fair=career_fair_draft, **support_dict)

        if cf_speaker_optional_data:
            for speaker_d in cf_speaker_optional_data:
                speaker_dict = speaker_d

                # image = speaker_dict.pop('image')
                speaker_sessions = speaker_dict.pop('speaker_sessions')

                speaker_optional_obj = SpeakerOptional.objects.create(career_fair=career_fair_draft, **speaker_dict)

                # if image:
                #     SpeakerProfileImageOptional.objects.update_or_create(speaker=speaker_optional_obj, image=image)

                if speaker_sessions:
                    # each item in the list is session id
                    for session_obj_dict in speaker_sessions:
                        try:

                            # session_obj_id = session_obj_dict.get('id')
                            if isinstance(session_obj_dict, SessionOptional):
                                session_optional_obj = session_obj_dict
                            else:
                                session_optional_obj = SessionOptional.objects.get(**session_obj_dict)
                            speaker_session = SpeakerAndSessionOptional.objects.create(
                                speaker=speaker_optional_obj,
                                session=session_optional_obj)

                        except SessionOptional.DoesNotExist as s:
                            logger.exception("SessionOptional object not found.\n")
                            raise ICFException(_("Could not create career fair, please check and try again."),
                                               status_code=status.HTTP_400_BAD_REQUEST)
                        except ObjectDoesNotExist as obe:
                            logger.exception("Object does not exist")

        if cf_product_optional_data:

            # # # cf_product_data  is a list of dictionaries
            for career_fair_and_product_dict in cf_product_optional_data:
                product_dict = career_fair_and_product_dict.pop('product')
                product_sub_type = career_fair_and_product_dict.pop('product_sub_type')
                # product_dict = product_d.pop('product')
                # cf_product_sub_type = product_d.pop('product_sub_type')

                # entity = validated_data.pop('entity')
                currency_code = product_dict.pop('currency')
                try:
                    currency_obj = Currency.objects.get(code=currency_code.upper())
                except Currency.DoesNotExist as cde:
                    logger.exception("Currency object not found.\n")
                    raise ICFException(_("Invalid currency code, please check and try again."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                name = product_dict.pop('name')

                name_en = product_dict.pop('name_en')
                name_fr = product_dict.pop('name_fr')
                name_es = product_dict.pop('name_es')
                description = product_dict.pop('description')
                description_en = product_dict.pop('description_en')
                description_fr = product_dict.pop('description_fr')
                description_es = product_dict.pop('description_es')

                career_fair_draft_product = ProductDraft.objects.create(name=name, name_en=name_en, name_fr=name_fr,
                                                                        name_es=name_es,
                                                                        description=description,
                                                                        description_en=description_en,
                                                                        description_es=description_es,
                                                                        description_fr=description_fr,
                                                                        entity=entity, currency=currency_obj,
                                                                        **product_dict)

                career_fair_and_product_optional = CareerFairAndProductOptional.objects.update_or_create(
                    career_fair=career_fair_draft,
                    product=career_fair_draft_product,
                    product_sub_type=product_sub_type)

        logger.info("Career Fair Draft created {}".format(career_fair_draft))
        return career_fair_draft

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None


class CareerFairGallerySerializer(ICFEntityMixin, ICFCareerFairMixin, ModelSerializer):
    image_type_name = serializers.SerializerMethodField()

    class Meta:
        model = CareerFairGallery
        exclude = ['career_fair_slug', 'career_fair', 'entity']

    def create(self, validated_data):
        logger.info("Upload image for the career fair")
        entity = self.get_entity(self.context['entity_slug'])
        career_fair = self.get_career_fair(self.context['slug'])

        try:
            image_type = validated_data.get('image_type')
            if image_type == CareerFairGallery.HERO:
                obj = CareerFairGallery.objects.get(entity=entity, career_fair=career_fair,
                                                    career_fair_slug=career_fair.slug, image_type=image_type)
                obj.image = validated_data.get('image')
                obj.save(update_fields=['image'])
                return obj
            else:
                # Check Limit
                if CareerFairGallery.objects.filter(entity=entity, career_fair=career_fair).count() >= 12:
                    raise ICFException(_("You have reached the max number of images"),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                image = validated_data.pop('image')
                image_type = validated_data.pop('image_type')
                obj = CareerFairGallery.objects.create(entity=entity, career_fair=career_fair,
                                                       career_fair_slug=career_fair.slug,
                                                       image=image, image_type=image_type)
                return obj
        except ObjectDoesNotExist:
            image = validated_data.pop('image')
            image_type = validated_data.pop('image_type')
            obj = CareerFairGallery.objects.create(entity=entity, career_fair=career_fair,
                                                   career_fair_slug=career_fair.slug,
                                                   image=image, image_type=image_type)
            return obj

    def get_image_type_name(self, obj):
        return CareerFairGallery.get_image_types().get(obj.image_type)


class CareerFairDraftGallerySerializer(ICFEntityMixin, ICFCareerFairDraftMixin, ModelSerializer):
    class Meta:
        model = CareerFairGalleryOptional
        exclude = ['career_fair_slug', 'career_fair', 'entity']

    def create(self, validated_data):
        logger.info("Upload image for the career fair draft")
        entity = self.get_entity(self.context['entity_slug'])
        career_fair = self.get_draft_career_fair(self.context['slug'])

        try:
            image_type = validated_data.get('image_type')
            if image_type == CareerFairGalleryOptional.HERO:
                obj = CareerFairGalleryOptional.objects.get(entity=entity, career_fair=career_fair,
                                                            career_fair_slug=career_fair.slug, image_type=image_type)
                obj.image = validated_data.get('image')
                obj.save(update_fields=['image'])
                return obj
            else:

                # Check Limit
                if CareerFairGalleryOptional.objects.filter(entity=entity, career_fair=career_fair).count() >= 12:
                    raise ICFException(_("You have reached the max number of images"),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                image = validated_data.pop('image')
                image_type = validated_data.pop('image_type')
                obj = CareerFairGalleryOptional.objects.create(entity=entity, career_fair=career_fair,
                                                               career_fair_slug=career_fair.slug, image=image,
                                                               image_type=image_type)
                return obj
        except ObjectDoesNotExist:
            image = validated_data.pop('image')
            image_type = validated_data.pop('image_type')
            obj = CareerFairGalleryOptional.objects.create(entity=entity, career_fair=career_fair,
                                                           career_fair_slug=career_fair.slug,
                                                           image=image, image_type=image_type)
            return obj

    def get_image_type_name(self, obj):
        return CareerFairGalleryOptional.get_image_types().get(obj.image_type)


class UpcomingOrPastCareerFairSerializer(ModelSerializer):
    location = AddressRetrieveSerializer()
    item_type = serializers.SerializerMethodField()
    entity = EntitySerializer()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry = serializers.DateTimeField(format='%B %d, %Y')
    # category = serializers.StringRelatedField()
    hero_image = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()
    no_of_participants = serializers.SerializerMethodField()

    class Meta:
        model = CareerFair
        fields = (
            'id',
            'title',
            'title_en',
            'title_fr',
            'title_es',
            'entity',
            # 'category',
            'item_type',
            'description',
            'description_en',
            'description_fr',
            'description_es',
            'location',
            'status',
            'expiry',
            'slug',
            'start_date',
            'organiser_contact_email',
            'organiser_contact_phone',
            'hero_image',
            'gallery_images',
            'user_info',
            'no_of_participants',
            'created',
            'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None

    def get_hero_image(self, obj):
        try:
            career_fair_galley_obj = CareerFairGallery.objects.filter(career_fair=obj,
                                                                      image_type=CareerFairGallery.HERO).last()
            if career_fair_galley_obj:
                return CareerFairGallery.objects.filter(career_fair=obj,
                                                        image_type=CareerFairGallery.HERO).last().image.url
            else:
                return None
        except CareerFairGallery.DoesNotExist:
            return None

    def get_gallery_images(self, obj):
        career_fair_gallery_list = CareerFairGallery.objects.filter(career_fair=obj,
                                                                    image_type=CareerFairGallery.GALLERY).order_by(
            'created')

        return CareerFairGallerySerializer(career_fair_gallery_list, many=True).data

    def get_user_info(self, obj):
        try:
            owner = UserProfile.objects.get(user=obj.owner)
            return UserProfileRetrieveSerializerForList(owner).data
        except UserProfile.DoesNotExist as e:
            return None

    def get_no_of_participants(self, obj):
        # return CareerFairParticipant.objects.filter(career_fair=obj,
        #                                             participant_type=CareerFairParticipant.INDIVIDUAL).count()
        return CareerFairParticipant.objects.filter(career_fair=obj,
                                                    participant_type=CareerFairParticipant.INDIVIDUAL).values(
            'user__id').annotate(Count('user__id')).order_by().count()


# class SD(Serializer):
#     image = serializers.ImageField(max_length=None, use_url=True)


class CareerFairTestSpeakerSerializer(ModelSerializer):
    session_speakers = SessionOptionalRetrieveSerializer(many=True, source='speakerandsessionoptional_set')

    class Meta:
        model = SpeakerOptional
        fields = [
            'name',
            'entity_name',
            'position',
            'speaker_email',
            'session_speakers',
        ]


class CandidateSearchCareerFairUserJobProfileSerializer(ModelSerializer):
    resume_url = serializers.SerializerMethodField()
    user_profile = serializers.SerializerMethodField()
    job_profile = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    user_slug = serializers.SerializerMethodField()
    user_last_work_experience = serializers.SerializerMethodField()
    user_total_experience = serializers.SerializerMethodField()
    is_job_invitation_sent = serializers.SerializerMethodField()

    class Meta:
        model = UserJobProfile
        fields = '__all__'

    def get_user_profile(self, obj):
        try:
            # message = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION')
            # details_msg = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION_DETAIL')
            # details = details_msg.format(obj.job.entity)
            # try:
            #     ICFNotificationManager.objects.get(user=obj.user, details=details)
            # except Exception:
            #     ICFNotificationManager.add_notification(user=obj.user, message=message, details=details)

            return UserProfileRetrieveSerializerForList(UserProfile.objects.get(user=obj.user)).data
        except UserProfile.DoesNotExist:
            logger.exception("User profile does not exist for {}".format(obj.user.email))
            return None

    def get_user_slug(self, obj):
        return obj.user.slug

    def get_resume_url(self, obj):
        try:
            if obj.resume:
                try:
                    user_resume = UserResume.objects.get(id=obj.resume.id)
                    if user_resume.resume:
                        return user_resume.resume.url
                    else:
                        try:
                            job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                            if job_profile_file_upload:
                                if job_profile_file_upload.resume_src:
                                    return job_profile_file_upload.resume_src.url
                                else:
                                    return None
                            else:
                                return None

                        except JobProfileFileUpload.DoesNotExist as jpfe:
                            logger.debug(str(jpfe))
                            return None
                except UserResume.DoesNotExist as urdne:
                    logger.debug(str(urdne))
                    try:
                        job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                        if job_profile_file_upload:
                            if job_profile_file_upload.resume_src:
                                return job_profile_file_upload.resume_src.url
                            else:
                                return None
                        else:
                            return None

                    except JobProfileFileUpload.DoesNotExist as jpfe:
                        logger.debug(str(jpfe))
                        return None
                except Exception as e:
                    logger.exception(str(e))
                    raise ICFException(_("Something went wrong, please contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
        except AttributeError as ae:
            # checks if user has default resume that is in JobProfileFileUpload table
            # if user did not upload default resume it returns None
            try:
                job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                if job_profile_file_upload:
                    if job_profile_file_upload.resume_src:
                        return job_profile_file_upload.resume_src.url
                    else:
                        return None
                else:
                    return None
            except JobProfileFileUpload.DoesNotExist as jpfe:
                logger.debug(str(jpfe))
                return None
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_job_profile(self, obj):
        try:
            return UserJobProfileRetrieveSerializer(UserJobProfile.objects.get(user=obj.user)).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None

    def get_education(self, obj):
        try:
            return UserEducationRetrieveSerializer(UserEducation.objects.filter(job_profile__user=obj.user),
                                                   many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for education")
            return None

    def get_experience(self, obj):
        try:
            return UserWorkExperienceListSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),
                                                    many=True).data
            # return UserWorkExperienceSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),
            #                                     many=True).data
        except ValueError as ve:
            logger.exception("Error in getting a value for experience")
            return None
        except ObjectDoesNotExist:
            return None

    def get_reference(self, obj):
        try:
            return UserReferenceSerializerForList(UserReference.objects.filter(job_profile__user=obj.user),
                                                  many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for reference")
            return None

    def get_skills(self, obj):
        try:
            return UserSkillSerializer(UserSkill.objects.filter(job_profile__user=obj.user), many=True).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for skill")
            return None

    def get_user_last_work_experience(self, obj):
        user_work_experience_last_obj = UserWorkExperience.objects.filter(job_profile=obj).last()
        if user_work_experience_last_obj:
            work_experience_serializer = UserWorkExperienceListSerializer(user_work_experience_last_obj)
            return work_experience_serializer.data
        else:
            return None

    def get_user_total_experience(self, obj):
        try:
            work_exp_qs = UserWorkExperience.objects.filter(job_profile=obj)
            user_total_work_exp_in_seconds = 0
            for exp in work_exp_qs:
                # print("exp_from: {d}".format(d=exp.worked_from))
                # print("exp_till: {till}".format(till=exp.worked_till))
                user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from, exp.worked_till)
                # print("Single work experience: ", single_exp_in_seconds)
                user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
            if user_total_work_exp_in_seconds > 0:
                user_total_work_exp_in_years = user_total_work_exp_in_seconds / 60 / 60 / 24 / 365
                return round(user_total_work_exp_in_years, 1)
            else:
                return 0
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            # raise ICFException(_("Something went wrong. reason:{reason}").format(reason=str(e)))
            return 0

    def get_is_job_invitation_sent(self, obj):
        try:
            jobseeker_user = obj.user
            to_user_type = ContentType.objects.get_for_model(jobseeker_user)

            app_type_slug = 'job'
            app_type = Type.objects.get(slug=app_type_slug)

            icf_user_messages_list = ICFMessage.objects.filter(topic_slug=self.context.get('view').kwargs.get('slug'),
                                                               recipient_type=to_user_type,
                                                               recipient_id=jobseeker_user.id, app_type=app_type,
                                                               sent_at__isnull=False)
            if icf_user_messages_list:
                return True
            else:
                return False
        except Exception as e:
            pass


class EntityHasCareerFairAdvertisementSerializer(serializers.Serializer):
    entity = serializers.IntegerField(required=True)
    career_fair = serializers.IntegerField(required=True)


class CareerFairAdvertisementListSerializer(ModelSerializer):
    id = serializers.IntegerField()
    career_fair_name = serializers.SerializerMethodField()
    career_fair_entity = serializers.SerializerMethodField()
    career_fair_slug = serializers.SerializerMethodField()
    career_fair_start_date = serializers.SerializerMethodField()
    career_fair_timezone = serializers.SerializerMethodField()
    buyer_entity = serializers.SerializerMethodField()

    class Meta:
        model = CareerFairAdvertisement
        fields = ['id', 'ad_image_url', 'ad_image_type', 'ad_redirect_url', 'ad_status', 'admin_comments',
                  'career_fair', 'career_fair_name', 'product', 'career_fair_entity', 'career_fair_slug',
                  'career_fair_start_date', 'career_fair_timezone', 'buyer_entity']

    def get_career_fair_name(self, obj):
        return obj.career_fair.title

    def get_career_fair_entity(self, obj):
        return obj.career_fair.entity.name

    def get_career_fair_slug(self, obj):
        return obj.career_fair.slug

    def get_career_fair_start_date(self, obj):
        return obj.career_fair.start_date

    def get_career_fair_timezone(self, obj):
        return obj.career_fair.timezone

    def get_buyer_entity(self, obj):
        return obj.entity.name


class CareerFairForUserSerializer(ModelSerializer):
    class Meta:
        model = CareerFairParticipant
        fields = ['id', 'career_fair', 'name_of_representative', 'participant_type', 'is_active', 'total_cost', 'is_payment_successful']