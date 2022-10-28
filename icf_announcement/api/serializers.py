from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.utils import model_meta
from rest_framework import serializers
from rest_framework import status
from django.utils.translation import ugettext_lazy as _

from icf_announcement.models import Announcement
from icf_auth.models import User
from icf_generic.api.serializers import CountrySerializer, LanguageSerializer, TypeSerializer
from icf_generic.models import Country, Language, Type

import logging
logger = logging.getLogger(__name__)


class AnnouncementSerializer(ModelSerializer):
    language_name = serializers.SerializerMethodField(read_only=True)
    id = serializers.ReadOnlyField()
    country_name = serializers.SerializerMethodField(read_only=True)
    item_type_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Announcement
        fields = [
                    "id",
                    "title",
                    "description",
                    "url",
                    "button_text",
                    "status",
                    "language",
                    "language_name",
                    "country",
                    "country_name",
                    "item_type",
                    "item_type_name",
                    "start_date",
                    "end_date",
                 ]

    def get_language_name(self, obj):
        try:
            serializer = LanguageSerializer(Language.objects.filter(id=obj.language_id).first())
            return serializer.data['name']
        except Exception as e:
            logger.exception('Could not get Language name, reason: {reason}.\n'.format(reason=str(e)))
            return None

    def get_country_name(self, obj):
        if obj.country:
            serializer = CountrySerializer(Country.objects.filter(id=obj.country_id).first())
            return serializer.data['country']
        else:
            return None

    def get_item_type_name(self, obj):
        if obj.item_type:
            serializer = TypeSerializer(Type.objects.filter(id=obj.item_type_id).first())
            return serializer.data['name']
        else:
            return None

    def validate(self, data):
        """
        Check that the start date is before the end date.
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start Date must be after End date")
        return data

    def create(self, validated_data):
        """
        Create and return a new 'User Education'.
        """
        # try:
        #     user = User.objects.get(user=user)
        return Announcement.objects.create( **validated_data)
        # except User.DoesNotExist as e:
        #     logger.exception(e)
        #     raise

