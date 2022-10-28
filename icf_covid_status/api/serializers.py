from rest_framework import status
from rest_framework.serializers import ModelSerializer

from icf_covid_status.models import CurrentWorkStatus, EGSector, CurrentCompensationStatus, UserWorkStatus
import logging

from icf_generic.Exceptions import ICFException
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class EGSectorSerializer(ModelSerializer):

    class Meta:
        model = EGSector
        fields = ["id", "name", "description", ]


class CurrentWorkStatusSerializer(ModelSerializer):

    class Meta:
        model = CurrentWorkStatus
        fields = ["id", "name", "description", ]


class CurrentCompensationStatusSerializer(ModelSerializer):

    class Meta:
        model = CurrentCompensationStatus
        fields = ["id", "name", "description", ]


class UserWorkStatusCreateSerializer(ModelSerializer):

    class Meta:
        model = UserWorkStatus
        exclude = ['user']

    def create(self, validated_data):
        user = self.context['request'].user
        try:
            user_work_status = UserWorkStatus.objects.get(user=user)
            logger.exception("User has already provided work status.\n")
            raise ICFException(_("You have already provided your work status."), status_code=status.HTTP_400_BAD_REQUEST)
        except UserWorkStatus.DoesNotExist as ue:
            user_work_status = UserWorkStatus.objects.create(user=user, **validated_data)
        return user_work_status



