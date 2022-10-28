from django.core.exceptions import ObjectDoesNotExist

from icf_auth.api.serializers import UserProfileImageSerializer
from icf_auth.models import UserProfile, UserProfileImage
from icf_entity.models import Logo, Entity
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from icf_generic.api.serializers import AddressSerializer, AddressOptionalSerializer
from icf_item.models import Item, Category, ItemDraft
import logging

logger = logging.getLogger(__name__)


class ItemCreateUpdateSerializer(ModelSerializer):

    location = AddressSerializer()

    class Meta:
        model = Item
        fields = '__all__'


class EntitySerializer(ModelSerializer):
    entity_logo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Entity
        fields = ['name', 'slug', 'entity_logo', 'description']

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj).image.url
        except ObjectDoesNotExist as e:
            return None


class ItemListSerializer(ModelSerializer):
    category = serializers.StringRelatedField()
    location = serializers.StringRelatedField()
    item_type = serializers.StringRelatedField()
    entity = serializers.StringRelatedField()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry =  serializers.DateTimeField(format='%B %d, %Y')
    entity_slug = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    title = serializers.SerializerMethodField(read_only=True)
    owner_profile_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Item
        fields = ('title', 'category', 'description', 'location', 'created', 'slug', 'updated', 'item_type',
                  'expiry', 'entity', 'entity_logo', 'start_date', 'entity_slug', 'owner', 'owner_profile_image')

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            return None

    def get_entity_slug(self, obj):
        try:
            return obj.entity.slug
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return None

    def get_title(self, obj):
        if obj.title_en:
            return obj.title_en
        elif obj.title_fr:
            return obj.title_fr
        else:
            return obj.title_es

    def get_owner_profile_image(self, obj):
        try:
            if obj.owner:
                user_profile = UserProfile.objects.get(user=obj.owner)
                user_profile_image = UserProfileImage.objects.get(user_profile=user_profile)
                if user_profile_image.image:
                    return user_profile_image.image.url
                else:
                    return None
            else:
                return None
        except UserProfile.DoesNotExist as ue:
            return None
        except UserProfileImage.DoesNotExist as upe:
            return None


class ItemDraftListSerializer(ModelSerializer):
    category = serializers.StringRelatedField()
    location = serializers.StringRelatedField()
    type = serializers.StringRelatedField()
    entity = serializers.StringRelatedField()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry =  serializers.DateTimeField(format='%B %d, %Y')
    entity_slug = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ItemDraft
        fields = ('title', 'category', 'description', 'location', 'created', 'slug', 'updated', 'type', 'expiry','entity','entity_logo','start_date','entity_slug')

    def get_entity_logo(self,obj):
        try:
            return Logo.objects.get(entity = obj.entity).image.url
        except ObjectDoesNotExist as e:
            return None

    def get_entity_slug(self,obj):
        try:
            return obj.entity.slug
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return None

class CategorySerializer(ModelSerializer):

    class Meta:
        model = Category
        fields = '__all__'

class ItemSearchListSerializer(ItemListSerializer):
    type = serializers.SerializerMethodField(read_only=True)

    class Meta(ItemListSerializer.Meta):
        model = Item
        fields = ItemListSerializer.Meta.fields + ('type',)

    def get_type(self,obj):
        try:
            return obj.item_type.content_type.model
        except Exception as e:
            logger.exception("Error in getting a type of the item")
            return None


class ItemCreateUpdateDraftSerializer(ModelSerializer):

    location = AddressOptionalSerializer()

    class Meta:
        model = ItemDraft
        fields = '__all__'