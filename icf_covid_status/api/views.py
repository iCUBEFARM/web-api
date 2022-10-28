# Create your views here.

from icf_covid_status.api.serializers import CurrentWorkStatusSerializer, CurrentCompensationStatusSerializer, \
    EGSectorSerializer, UserWorkStatusCreateSerializer
from icf_covid_status.models import EGSector, CurrentWorkStatus, CurrentCompensationStatus, UserWorkStatus
from icf_generic.Exceptions import ICFException

from icf_jobs.permissions import CanCreateJob
from rest_framework.generics import CreateAPIView, ListAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.utils.translation import ugettext_lazy as _

import logging

from icf_messages.manager import ICFNotificationManager

logger = logging.getLogger(__name__)


class EGSectorListAPIView(ListAPIView):
    serializer_class = EGSectorSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = EGSector.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(name__istartswith=qp)
        return queryset


class CurrentWorkStatusListAPIView(ListAPIView):
    serializer_class = CurrentWorkStatusSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = CurrentWorkStatus.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(name__istartswith=qp)
        return queryset


class CurrentCompensationListAPIView(ListAPIView):
    serializer_class = CurrentCompensationStatusSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = CurrentCompensationStatus.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(name__istartswith=qp)
        return queryset


class CheckIfUserHasWorkStatusAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        try:
            user = self.request.user
            if user:
                try:
                    user_work_status = UserWorkStatus.objects.get(user=user)
                    return Response({"user_has_work_status": True}, status=status.HTTP_200_OK)
                except UserWorkStatus.DoesNotExist as ue:
                    return Response({"user_has_work_status": False}, status=status.HTTP_200_OK)
            else:
                logger.info('User is not logged in.')
                return Response({"detail": "Please login."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.info('something went wrong reason: {reason}.'.format(reason=str(e)))
            return Response({"detail": "something went wrong, Please contact admin."}, status=status.HTTP_400_BAD_REQUEST)


class UserWorkStatusCreateAPIView(CreateAPIView):
    queryset = UserWorkStatus.objects.all()
    serializer_class = UserWorkStatusCreateSerializer
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        context = {'user': self.request.user}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

