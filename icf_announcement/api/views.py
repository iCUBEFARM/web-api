from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from icf import settings
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from icf_announcement.api.serializers import AnnouncementSerializer

from icf_announcement.models import Announcement

import logging
logger = logging.getLogger(__name__)


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Announcement.objects.all()

    def get_serializer(self, *args, **kwargs):
        return AnnouncementSerializer(*args, **kwargs)

    def get_object(self):
        try:
            return Announcement.objects.get( pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist as e:
            logger.debug(e)
            raise

    def list(self, request, *args, **kwargs):
        queryset = Announcement.objects.filter()
        serializer = AnnouncementSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = AnnouncementSerializer(data=request.data,)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug("Cannot create Announcement ")
            return Response({"detail": "Cannot create Announcement"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            obj = Announcement.objects.get(pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Announcement.DoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Announcement object not found"}, status=status.HTTP_400_BAD_REQUEST)

    # def update(self, request, pk=None, *args, **kwargs):
    #     try:
    #         instance = Announcement.objects.get(job_profile__user=self.request.user, pk=pk)
    #         serializer = self.get_serializer(instance, data=request.data)
    #         serializer.is_valid(raise_exception=True)
    #     except ObjectDoesNotExist as e:
    #         logger.debug("Cannot update User Education")
    #         return Response({"detail": "Cannot update User Education"}, status=status.HTTP_400_BAD_REQUEST)

    #     try:
    #         self.perform_update(serializer)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     except ObjectDoesNotExist as e:
    #         logger.debug("Cannot  update User Education")
    #         return Response({"detail": "Cannot  update User Education"}, status=status.HTTP_400_BAD_REQUEST)

    # def destroy(self, request, *args, pk=None, **kwargs):
    #     try:
    #         instance = self.get_object()
    #         self.perform_destroy(instance)
    #         return Response({"detail": "User Education got deleted successfully "}, status=status.HTTP_200_OK)
    #     except ObjectDoesNotExist as e:
    #         logger.debug("User Education not found, cannot delete")
    #         return Response({'detail': "User Education not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)
