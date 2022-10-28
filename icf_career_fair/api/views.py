# Create your views here.
import os
import ssl
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.template.loader import get_template, render_to_string
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
# from weasyprint import HTML
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer

from icf.settings import MEDIA_ROOT
from icf_auth.models import UserProfile, UserProfileImage
from icf_career_fair.api.filters import CareerFairFilters, StatusEntityCareerFairFilter
from icf_career_fair.api.serializers import CareerFairCreateSerializer, CareerFairForUserSerializer, CareerFairListSerializer, \
    CareerFairDraftCreateSerializer, CareerFairDraftRetrieveUpdateSerializer, \
    CareerFairRetrieveSerializer, CareerFairRetrieveUpdateSerializer, CareerFairDraftListSerializer, \
    CareerFairDraftRetrieveSerializer, EntityCareerFairListSerializer, SpeakerProfileImageSerializer, \
    SpeakerProfileImageOptionalSerializer, CareerFairGallerySerializer, CareerFairDraftGallerySerializer, \
    UpcomingOrPastCareerFairSerializer, CareerFairProductSerializer, CareerFairSalesSerializer, \
    SessionOptionalSerializer, SupportOptionalSerializer, SpeakerOptionalSerializer, SessionSerializer, \
    SupportSerializer, SpeakerSerializer, SupportLogoSerializer, SupportOptionalLogoSerializer, \
    CareerFairTestSpeakerSerializer, CareerFairDraftRetrieveTestSerializer, \
    CandidateSearchCareerFairUserJobProfileSerializer, CareerFairRetrieveTestSerializer, \
    CareerFairOptionalImageSerializer, CareerFairImageSerializer, CareerFairAdvertisementListSerializer, \
    EntityHasCareerFairAdvertisementSerializer
from icf_career_fair.models import CareerFairImageType, CareerFair, CareerFairDraft, SpeakerProfileImage, \
    SpeakerProfileImageOptional, \
    CareerFairGallery, CareerFairGalleryOptional, CareerFairMarkedForDelete, CareerFairProductSubType, \
    CareerFairAndProduct, CareerFairAndProductOptional, ParticipantAndProduct, SessionOptional, SupportOptional, \
    SpeakerOptional, Session, Support, Speaker, SupportLogo, SupportLogoOptional, CareerFairParticipant, \
    CareerFairImagesOptional, CareerFairImages, CareerFairAdvertisement, CareerFairAdvertisementViews
from icf_career_fair.permissions import CanCreateCareerFair, CanEditCareerFair, CanSeeCareerFairsMarkedForDelete, \
    CanRejectMarkedForDeleteCareerFair, CanDeleteCareerFair, CanPublishCareerFair, CanMarkCareerFairDelete
from icf_entity.models import Entity
from icf_entity.permissions import IsEntityUser
from icf_generic.Exceptions import ICFException

from icf_generic.mixins import ICFListMixin
from icf_generic.models import Sponsored, Country, City, Address
from icf_item.api.serializers import EntitySerializer
from icf_item.models import Item
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, DestroyAPIView, \
    RetrieveUpdateDestroyAPIView, UpdateAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q, Count, Sum, F, FloatField

import logging

from icf_jobs.models import UserJobProfile, UserSkill
from icf_messages.manager import ICFNotificationManager
from icf_orders.models import Product, ProductDraft

logger = logging.getLogger(__name__)


class CareerFairCreateApiView(CreateAPIView):
    queryset = CareerFair.objects.all()
    serializer_class = CareerFairCreateSerializer
    permission_classes = (IsAuthenticated, CanCreateCareerFair)

    def perform_create(self, serializer):
        instance = serializer.save()
        return instance

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            output_serializer = CareerFairRetrieveTestSerializer(instance)
            output_data = output_serializer.data
            headers = self.get_success_headers(output_serializer.data)
            return Response(output_data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.exception("something went wrong.")
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class GeneralCareerFairListView(ListAPIView):
    queryset = CareerFair.objects.all()
    serializer_class = CareerFairListSerializer
    filter_class = CareerFairFilters

    def get_queryset(self):
        queryset = CareerFair.objects.all().filter(status=Item.ITEM_ACTIVE, start_date__lte=now(),
                                                   expiry__gte=now()).order_by("-created")
        try:
            entity = self.request.query_params.get('entity', None)
            if entity:
                queryset = queryset.filter(entity__slug=entity)

            entity_related_career_fairs = self.request.query_params.get('entity_related_career_fairs', None)
            if entity_related_career_fairs:
                career_fair = CareerFair.objects.get(slug=entity_related_career_fairs)
                queryset = queryset.filter(entity=CareerFair.entity).exclude(pk=career_fair.pk)

            location = self.request.query_params.get('location')
            if location:
                career_fair = CareerFair.objects.get(slug=location)
                queryset = queryset.filter(location__city__city=career_fair.location.city.city).exclude(
                    pk=career_fair.pk)

            return queryset

        except Exception as e:
            logger.debug(e)
            return CareerFair.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EntityCareerFairListApiView(ICFListMixin, ListAPIView):
    queryset = CareerFair.objects.all()
    serializer_class = EntityCareerFairListSerializer
    filter_class = StatusEntityCareerFairFilter
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(entity__slug=self.kwargs.get('slug'))
            # update the cf status for the cf which is
            # continues to be active even if it expired
            status = self.request.query_params.get('status', None)
            if status and int(status) == Item.ITEM_ACTIVE:
                queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the career fair list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class EntityCareerFairCountApiView(APIView):
    queryset = CareerFair.objects.all()
    permission_classes = (IsAuthenticated, IsEntityUser)

    def list(self):
        try:
            queryset = self.queryset.filter(entity__slug=self.kwargs.get('entity_slug'), status=Item.ITEM_ACTIVE,
                                            start_date__lte=now(), expiry__gte=now()).order_by("-created")
            queryset_count = queryset.count()
            return Response({'active_career_fair_count': queryset_count}, status=status.HTTP_200_OK)

        except Exception as e:
            pass


class CareerFairSpeakerListApiView(ListAPIView):
    pass


class CareerFairMarkForDeleteCreateApiView(APIView):
    queryset = CareerFair.objects.all()
    permission_classes = (IsAuthenticated, CanMarkCareerFairDelete)
    lookup_field = "slug"

    def post(self, request, *args, **kwargs):
        user = self.request.user
        career_fair_slug = kwargs.get('slug')
        if career_fair_slug is not None:
            try:
                career_fair = CareerFair.objects.get(slug=career_fair_slug)
                if career_fair.status is not CareerFair.ITEM_ACTIVE:
                    return Response({'detail': 'Career fair is not active ,cannot mark the career fair for delete '},
                                    status=status.HTTP_403_FORBIDDEN)

            except CareerFair.DoesNotExist as jdn:
                logger.debug(jdn)
                return Response({'detail': 'Career fair not found'}, status=status.HTTP_404_NOT_FOUND)
            try:
                career_fair_marked_for_delete = CareerFairMarkedForDelete.objects.get(career_fair=career_fair)
                if career_fair_marked_for_delete.approval_status == CareerFairMarkedForDelete.REJECTED:
                    career_fair_marked_for_delete.approval_status = CareerFairMarkedForDelete.NEW
                    career_fair_marked_for_delete.user = user
                    career_fair_marked_for_delete.save(update_fields=['approval_status', 'user'])
                    return Response({'detail': 'Career fair marked for delete'}, status=status.HTTP_201_CREATED)
                elif career_fair_marked_for_delete.approval_status == CareerFairMarkedForDelete.NEW:
                    return Response({'detail': 'Career fair has already been marked for delete'},
                                    status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'Career fair cannot be marked for delete because '
                                               'career fair has been deleted'},
                                    status=status.HTTP_400_BAD_REQUEST)

            except CareerFairMarkedForDelete.DoesNotExist as e:
                CareerFairMarkedForDelete.objects.create(user=user, career_fair=career_fair)
                return Response({'detail': 'Career fair marked for delete.'}, status=status.HTTP_201_CREATED)
        else:
            return Response("Bad Request", status=status.HTTP_400_BAD_REQUEST)


class CareerFairMarkedForDeleteListView(ListAPIView):
    permission_classes = (IsAuthenticated, CanSeeCareerFairsMarkedForDelete)
    queryset = CareerFair.objects.all()
    serializer_class = CareerFairListSerializer

    def list(self, request, *args, **kwargs):
        career_fairs_list = []
        career_fair_marked_for_delete_list = CareerFairMarkedForDelete.objects.all()
        entity_slug = self.kwargs['entity_slug']
        if entity_slug:
            for career_fair in self.get_queryset():
                for emd in career_fair_marked_for_delete_list:
                    if career_fair == emd.career_fair and emd.approval_status == CareerFairMarkedForDelete.NEW and career_fair.entity.slug == entity_slug:
                        career_fairs_list.append(career_fair)
            serializer = CareerFairListSerializer(career_fairs_list, many=True)
            return Response(serializer.data)

        else:
            logger.info("entity slug not passed.")
            raise ICFException(_("Something went wrong, please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)


class RejectCareerFairMarkedForDeleteRequestView(APIView):
    queryset = CareerFair.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated, CanRejectMarkedForDeleteCareerFair)
    lookup_field = "slug"

    def put(self, request, *args, **kwargs):
        user = self.request.user
        career_fair_slug = kwargs.get('slug')
        if career_fair_slug is not None:
            try:
                career_fair = CareerFair.objects.get(slug=career_fair_slug)
                career_fair_marked_for_delete = CareerFairMarkedForDelete.objects.get(career_fair=career_fair)
                if career_fair_marked_for_delete.approval_status == CareerFairMarkedForDelete.NEW:
                    #  if the career_fair_marked_for_delete status is New, Change the career_fair_marked_for_delete
                    #  status to Rejected
                    career_fair_marked_for_delete.approval_status = CareerFairMarkedForDelete.REJECTED
                    career_fair_marked_for_delete.save(update_fields=['approval_status'])
                    return Response({'detail': 'delete request for the career fair is rejected.'},
                                    status=status.HTTP_200_OK)

                elif career_fair_marked_for_delete.approval_status == CareerFairMarkedForDelete.REJECTED:
                    #  if the career_fair_marked_for_delete status is Rejected, send message as it has been already rejected
                    return Response({'detail': 'the career fair delete request has been already rejected.'},
                                    status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'CareerFair has been deleted'},
                                    status=status.HTTP_400_BAD_REQUEST)

            except CareerFair.DoesNotExist as edn:
                logger.exception(edn)
                return Response({'detail': 'CareerFair not found'}, status=status.HTTP_404_NOT_FOUND)
            except CareerFairMarkedForDelete.DoesNotExist as emdn:
                logger.debug(emdn)
                return Response({'detail': 'CareerFairMarkedForDelete does not found.'},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            return Response("Bad Request", status=status.HTTP_400_BAD_REQUEST)


class CareerFairDeleteApiView(DestroyAPIView):
    queryset = CareerFair.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated, CanDeleteCareerFair)
    lookup_field = "slug"

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({'detail': 'Career fair not found'}, status=status.HTTP_404_NOT_FOUND)
        if instance.status == CareerFair.ITEM_DRAFT:
            self.perform_destroy(instance)
            return Response({'detail': 'Career fair has been deleted permanently'}, status=status.HTTP_200_OK)

        elif instance.status == CareerFair.ITEM_ACTIVE:
            try:
                career_fair_marked_for_delete = CareerFairMarkedForDelete.objects.get(career_faor=instance)

                if career_fair_marked_for_delete.approval_status is not CareerFairMarkedForDelete.NEW:
                    return Response({'detail': 'Career fair cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)

                # Delete the career fair if CareerFairMarkedForDelete is NEW
                instance.status = CareerFair.ITEM_DELETED
                instance.save(update_fields=['status'])

                # Delete the career fair if CareerFairMarkedForDelete is NEW
                career_fair_marked_for_delete.approval_status = CareerFairMarkedForDelete.DELETED
                career_fair_marked_for_delete.save(update_fields=['approval_status'])
                return Response({'detail': 'Career fair has been deleted'}, status=status.HTTP_200_OK)
            except CareerFairMarkedForDelete.DoesNotExist as jmdn:
                logger.debug(jmdn)
                return Response(
                    {'detail': 'Career fair cannot be deleted,because career fair is not marked for delete'},
                    status=status.HTTP_400_BAD_REQUEST)
        else:

            if instance.status == CareerFair.ITEM_DELETED:
                return Response({'detail': 'Career fair has been already deleted.'}, status=status.HTTP_400_BAD_REQUEST)
            instance.status = CareerFair.ITEM_DELETED
            instance.save(update_fields=['status'])
            return Response({'detail': 'Career fair has been deleted'}, status=status.HTTP_200_OK)


class CareerFairCloseView(APIView):
    queryset = CareerFair.objects.all()
    serializer_class = None
    lookup_field = "slug"
    permission_classes = (IsAuthenticated, CanPublishCareerFair)

    def put(self, request, *args, **kwargs):
        career_fair_slug = kwargs.get('slug')
        try:
            career_fair = CareerFair.objects.get(slug=career_fair_slug)
            if career_fair.status == CareerFair.ITEM_CLOSED:
                return Response({'detail': 'Career fair has been already closed.'}, status=status.HTTP_400_BAD_REQUEST)
            career_fair.status = CareerFair.ITEM_CLOSED
            career_fair.save(update_fields=['status'])
            return Response({'detail': 'Career fair has been closed.'}, status=status.HTTP_200_OK)

        except CareerFair.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Career fair Not found.'}, status=status.HTTP_404_NOT_FOUND)


class CareerFairDirectUpdateApiView(UpdateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        try:
            career_fair_obj = CareerFair.objects.get(slug=self.kwargs.get('slug'))
            return career_fair_obj
        except CareerFair.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Career Fair object Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Product object Not found.'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            instance.status = Item.ITEM_DELETED
            return Response({'detail': 'Career Fair updated successfully.'}, status=status.HTTP_200_OK)
        except CareerFair.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Career Fair object Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Product object Not found.'}, status=status.HTTP_404_NOT_FOUND)


class CareerFairUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = CareerFair.objects.all()
    serializer_class = CareerFairRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, CanEditCareerFair)
    lookup_field = "slug"

    def get_object(self, slug=None):
        try:
            instance = CareerFair.objects.get(slug=self.kwargs.get('slug'))
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object(*args, **kwargs)

        # Check if career fair is sponsored
        try:
            sp_obj = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_ACTIVE)
            instance.sponsored_start_dt = sp_obj.start_date
            instance.sponsored_end_dt = sp_obj.end_date
            instance.is_sponsored = True
            # serializer = self.get_serializer(instance)
            serializer = CareerFairRetrieveTestSerializer(instance)
        except Exception as e:
            serializer = CareerFairRetrieveTestSerializer(instance)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object(*args, **kwargs)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        output_serializer = CareerFairRetrieveTestSerializer(instance)
        output_data = output_serializer.data
        return Response(output_data)

    # def get(self, request, *args, **kwargs):
    #     return self.retrieve(request, *args, **kwargs)
    #
    # def retrieve(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #
    #     # Check if career fair is sponsored
    #     try:
    #         sp_obj = Sponsored.objects.get(object_id=instance.id,status=Sponsored.SPONSORED_ACTIVE)
    #         instance.sponsored_start_dt = sp_obj.start_date
    #         instance.sponsored_end_dt = sp_obj.end_date
    #         instance.is_sponsored = True
    #         serializer = self.get_serializer(instance)
    #     except Exception as e:
    #         serializer = self.get_serializer(instance)
    #
    #     return Response(serializer.data)
    #
    # def perform_update(self, serializer):
    #     serializer.save()


class CareerFairDetailView(RetrieveAPIView):
    queryset = CareerFair.objects.all()
    serializer_class = CareerFairRetrieveTestSerializer
    # permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class CareerFairOptionalImageViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CareerFairOptionalImageSerializer
    # permission_classes = (IsAuthenticated, CanCreateCareerFair,)
    queryset = CareerFairImagesOptional.objects.all()

    def get_serializer(self, *args, **kwargs):
        return CareerFairOptionalImageSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = CareerFairImagesOptional.objects.get(career_fair__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(career_fair__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add draft career fair image"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve draft career fair image"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update draft career fair image"}, status=status.HTTP_400_BAD_REQUEST)


class CareerFairImageViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CareerFairImageSerializer
    # permission_classes = (IsAuthenticated, CanCreateCareerFair,)
    queryset = CareerFairImages.objects.all()

    def get_serializer(self, *args, **kwargs):
        return CareerFairImageSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = CareerFairImages.objects.get(career_fair__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(career_fair__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add career fair image"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve career fair image"},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update career fair image"}, status=status.HTTP_400_BAD_REQUEST)


class SpeakerProfileImageViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = SpeakerProfileImageSerializer
    permission_classes = (IsAuthenticated, CanCreateCareerFair,)
    queryset = SpeakerProfileImage.objects.all()

    def get_serializer(self, *args, **kwargs):
        return SpeakerProfileImageSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = SpeakerProfileImage.objects.get(speaker__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(speaker__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add profile image"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve profile image"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update profile image"}, status=status.HTTP_400_BAD_REQUEST)


class SpeakerProfileImageOptionalViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = SpeakerProfileImageOptionalSerializer
    permission_classes = (IsAuthenticated, CanCreateCareerFair,)
    queryset = SpeakerProfileImageOptional.objects.all()

    def get_serializer(self, *args, **kwargs):
        return SpeakerProfileImageOptionalSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = SpeakerProfileImageOptional.objects.get(speaker__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(speaker__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add profile image"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve profile image"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update profile image"}, status=status.HTTP_400_BAD_REQUEST)


class SupportLogoViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = SupportLogoSerializer
    permission_classes = (IsAuthenticated, CanCreateCareerFair,)
    queryset = SupportLogo.objects.all()

    def get_serializer(self, *args, **kwargs):
        return SupportLogoSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = SupportLogoSerializer.objects.get(support__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(support__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add support logo"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve logo"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update logo"}, status=status.HTTP_400_BAD_REQUEST)


class SupportOptionalLogoViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = SupportOptionalLogoSerializer

    permission_classes = (IsAuthenticated, CanCreateCareerFair,)
    queryset = SupportLogoOptional.objects.all()

    def get_serializer(self, *args, **kwargs):
        return SupportOptionalLogoSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = SupportLogoOptional.objects.get(support__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(support__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add support logo"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve logo"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update logo"}, status=status.HTTP_400_BAD_REQUEST)


class CareerFairDraftPreviewView(RetrieveAPIView):
    serializer_class = CareerFairDraftRetrieveSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_object(self):
        try:
            return CareerFairDraft.objects.get(slug=self.kwargs.get('career_fair_slug'))
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise


class EntityCareerFairDraftList(ICFListMixin, ListAPIView):
    queryset = CareerFairDraft.objects.all()
    serializer_class = CareerFairDraftListSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_queryset(self):
        queryset = self.queryset.filter(entity__slug=self.kwargs.get('slug'), status=Item.ITEM_DRAFT).order_by(
            '-updated')
        return queryset


class CareerFairDraftCreateApiView(CreateAPIView):
    queryset = CareerFairDraft.objects.all()
    serializer_class = CareerFairDraftCreateSerializer
    permission_classes = (IsAuthenticated, CanCreateCareerFair)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CareerFairDraftDetailView(RetrieveAPIView):
    queryset = CareerFairDraft.objects.all()
    serializer_class = CareerFairDraftRetrieveTestSerializer
    # permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class CareerFairDraftUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = CareerFairDraft.objects.all()
    serializer_class = CareerFairDraftRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"

    def get_object(self, slug=None):
        try:
            instance = CareerFairDraft.objects.get(slug=self.kwargs.get('slug'))
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object(*args, **kwargs)
        serializer = CareerFairDraftRetrieveTestSerializer(instance)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object(*args, **kwargs)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        output_serializer = CareerFairDraftRetrieveTestSerializer(instance)
        output_data = output_serializer.data
        return Response(output_data)


class CareerFairGalleryViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CareerFairGallerySerializer
    permission_classes = (IsAuthenticated,)
    queryset = CareerFairGallery.objects.all()

    def get_serializer(self, *args, **kwargs):
        return CareerFairGallerySerializer(*args, **kwargs)

    def get_object(self, slug=None, entity_slug=None, pk=None):
        try:
            instance = CareerFairGallery.objects.get(pk=self.kwargs.get('pk'))
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, entity_slug=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        qs = self.queryset.filter(entity__slug=entity_slug, career_fair__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, entity_slug=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add image for career fair."}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve image."}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        try:
            instance = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update Logo"}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, args, slug=None, entity_slug=None, pk=None, *kwargs):
        try:
            obj = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            obj.delete()
            return Response({"detail: image deleted"}, status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve image."}, status=status.HTTP_400_BAD_REQUEST)


class CareerFairDraftGalleryViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CareerFairDraftGallerySerializer
    permission_classes = (IsAuthenticated,)
    queryset = CareerFairGalleryOptional.objects.all()

    def get_serializer(self, *args, **kwargs):
        return CareerFairDraftGallerySerializer(*args, **kwargs)

    def get_object(self, slug=None, entity_slug=None, pk=None):
        try:
            instance = CareerFairGalleryOptional.objects.get(pk=self.kwargs.get('pk'))
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, entity_slug=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        qs = self.queryset.filter(entity__slug=entity_slug, career_fair__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, entity_slug=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add image for career fair."}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve image."}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        try:
            instance = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update image."}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        try:
            instance = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            self.perform_destroy(instance)
            return Response({"detail": "image got deleted successfully."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("image not found, cannot delete.")
            return Response({'detail': "image not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)


class UpcomingCareerFairsListApiView(ListAPIView):
    serializer_class = UpcomingOrPastCareerFairSerializer

    def get_queryset(self):

        now = datetime.now()
        queryset = CareerFair.objects.filter(status=CareerFair.ITEM_ACTIVE). \
            filter(expiry__gte=now).order_by('-updated')
        qp_slug = self.request.query_params.get('exclude_career_fair_slug', None)
        qp_career_fair_title = self.request.query_params.get('search_text', None)
        qp_country_name = self.request.query_params.get('country_name', None)

        if qp_slug is not None:
            queryset = queryset.exclude(slug=qp_slug)

        if qp_career_fair_title is not None:
            queryset = queryset.filter(title__icontains=qp_career_fair_title)

        if qp_country_name is not None:
            qp_city_name_str = qp_country_name.split(', ')
            queryset = queryset.filter(location__city__city__icontains=qp_city_name_str[0])

        return queryset


class PastCareerFairsListApiView(ListAPIView):
    serializer_class = UpcomingOrPastCareerFairSerializer

    def get_queryset(self):

        # slug = self.kwargs.get('slug')
        queryset = CareerFair.objects.filter(status=CareerFair.ITEM_ACTIVE). \
            filter(expiry__lt=datetime.now()).order_by('-updated')
        qp_slug = self.request.query_params.get('exclude_career_fair_slug', None)
        qp_career_fair_title = self.request.query_params.get('search_text', None)
        qp_country_name = self.request.query_params.get('country_name', None)

        if qp_slug is not None:
            queryset = queryset.exclude(slug=qp_slug)

        if qp_career_fair_title is not None:
            queryset = queryset.filter(title__icontains=qp_career_fair_title)

        if qp_country_name is not None:
            qp_city_name_str = qp_country_name.split(', ')
            queryset = queryset.filter(location__city__city__icontains=qp_city_name_str[0])

        return queryset


class UpcomingCareerFairsByEntityListApiView(ICFListMixin, ListAPIView):
    serializer_class = UpcomingOrPastCareerFairSerializer

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        try:
            entity = Entity.objects.get(slug=entity_slug)
        except Entity.DoesNotExist as cde:
            logger.exception("Entity object not found.\n")
            raise ICFException(_("Invalid entity slug, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        # entity = Entity.objects.get(slug=entity_slug)
        now = datetime.now()
        queryset = CareerFair.objects.filter(expiry__gte=now).filter(entity=entity).order_by('-updated')
        return queryset


class ActiveCareerFairsByEntityListApiView(ICFListMixin, ListAPIView):
    serializer_class = UpcomingOrPastCareerFairSerializer

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        try:
            entity = Entity.objects.get(slug=entity_slug)
        except Entity.DoesNotExist as cde:
            logger.exception("Entity object not found.\n")
            raise ICFException(_("Invalid entity slug, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        # entity = Entity.objects.get(slug=entity_slug)
        queryset = CareerFair.objects.filter(status=CareerFair.ITEM_ACTIVE).filter(entity=entity).order_by('-updated')

        return queryset


class PastCareerFairsByEntityListApiView(ICFListMixin, ListAPIView):
    serializer_class = UpcomingOrPastCareerFairSerializer

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        try:
            entity = Entity.objects.get(slug=entity_slug)
        except Entity.DoesNotExist as cde:
            logger.exception("Entity object not found.\n")
            raise ICFException(_("Invalid entity slug, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        # entity = Entity.objects.get(slug=entity_slug)
        queryset = CareerFair.objects.filter(entity=entity). \
            filter(expiry__lt=datetime.now()).order_by('-updated')

        return queryset


class CareerFairProductsByBuyerTypeListApiView(ICFListMixin, ListAPIView):
    serializer_class = CareerFairProductSerializer

    def get_queryset(self):
        career_fair_slug = self.kwargs.get('slug')
        buyer_type_id = self.kwargs.get('buyer_type_id')
        try:
            career_fair = CareerFair.objects.get(slug=career_fair_slug)
        except CareerFair.DoesNotExist as cde:
            logger.exception("CareerFair object not found.\n")
            raise ICFException(_("Invalid career fair slug, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        # entity = Entity.objects.get(slug=entity_slug)
        career_fair_and_products_id_list = CareerFairAndProduct.objects.filter(career_fair=career_fair). \
            values_list('product_id', flat=True)
        queryset = Product.objects.filter(id__in=career_fair_and_products_id_list).filter(
            buyer_type=buyer_type_id).order_by('-updated')

        return queryset

    # def list(self, request, *args, **kwargs):
    #
    #     queryset = self.get_queryset()
    #     page = self.paginate_queryset(queryset)
    #
    #     serializer = self.get_serializer(queryset, many=True)
    #
    #     product_sub_type = None
    #
    #
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response({'results': serializer.data,
    #                                             'search_filter_list': search_criteria_list, 'job_filters': job_filters})
    #     else:
    #         return Response(
    #             {'results': serializer.data, 'search_filter_list': search_criteria_list, 'job_filters': job_filters},
    #             status=status.HTTP_200_OK)


class IsUserCareerFairParticipantView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = CareerFairParticipant.objects.all()

    def retrieve(self, request, *args, **kwargs):
        career_fair_slug = kwargs.get('career_fair_slug')
        if career_fair_slug:
            """
            Is the user a participant
            """
            if CareerFairParticipant.objects.filter(career_fair__slug=career_fair_slug,
                                                    user=self.request.user).exists():
                """
                Also check if the user is a entity participant
                """

                return Response({'is_participant': True}, status=status.HTTP_200_OK)

        return Response({'is_participant': False}, status=status.HTTP_200_OK)


class CareerFairSalesReportView(ListAPIView):
    permission_classes = (IsAuthenticated, CanEditCareerFair)
    queryset = ParticipantAndProduct.objects.all()
    serializer_class = CareerFairSalesSerializer

    def get_queryset(self):

        try:
            career_fair_slug = self.kwargs.get('career_fair_slug')
            entity_slug = self.kwargs.get('slug')
            career_fair_products = None

            """
            Filter only for sale products
            """
            if career_fair_slug:
                career_fair_products = CareerFairAndProduct.objects.filter(career_fair__slug=career_fair_slug,
                                                                           career_fair__entity__slug=entity_slug, ).values_list(
                    'product')

            """
            If the career fair has product
            """  # career_fair_product_status=CareerFairAndProduct.FOR_SALE)
            if career_fair_products:
                # queryset = ParticipantAndProduct.objects.filter(product__id__in=career_fair_products).values(
                #     'participant', 'product__name', 'product__cost', 'product__currency__name').annotate(item_quantity=Sum('quantity')).annotate(
                #     item_cost=Sum(F('quantity') * F('product__cost')))

                """
                Check if any of the products of career fair is purchased by any participant
                """
                purchased_products = None
                purchased_products = ParticipantAndProduct.objects.filter(product__id__in=career_fair_products)

                if purchased_products:
                    queryset = ParticipantAndProduct.objects.annotate(
                        product_cost=F('product__cost'),
                        product_name=F('product__name'),
                        currency=F('product__currency__name')).filter(
                        product__id__in=career_fair_products).values(
                        'product_name', 'product_cost', 'currency').annotate(
                        item_quantity=Sum('quantity')).annotate(
                        item_cost=Sum(F('quantity') * F('product__cost'), output_field=FloatField()))

                    total_cost = ParticipantAndProduct.objects.filter(product__in=career_fair_products).aggregate(
                        total_cost=Sum(F('quantity') * F('product__cost'), output_field=FloatField()))

                    total_quantity = ParticipantAndProduct.objects.filter(product__in=career_fair_products).aggregate(
                        total_quantity=Sum('quantity'))

                    return queryset, total_cost, total_quantity
                else:
                    return ParticipantAndProduct.objects.none(), {'total_cost': 0}, {'total_quantity': 0}

            else:
                return ParticipantAndProduct.objects.none(), {'total_cost': 0}, {'total_quantity': 0}

        except Exception as e:
            logger.exception(e)
            return ParticipantAndProduct.objects.none(), {'total_cost': 0}, {'total_quantity': 0}

    def list(self, request, *args, **kwargs):
        querset = None
        total_cost = None
        total_quantity = None
        queryset, cost, quantity = self.get_queryset()
        if queryset:
            # page = self.paginate_queryset(queryset)
            # if page is not None:
            #     serializer = self.get_serializer(page, many=True)
            #     return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response({'total_cost': cost.get('total_cost'), 'total_quantity': quantity.get('total_quantity'),
                             'products': serializer.data})
        else:
            return Response({'total_cost': cost.get('total_cost'), 'total_quantity': quantity.get('total_quantity'),
                             'products': None})


class CareerFairDraftDirectDeleteApiView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        try:
            career_fair_draft_obj = CareerFairDraft.objects.get(slug=self.kwargs.get('slug'))
            career_fair_and_products = CareerFairAndProductOptional.objects.filter(career_fair=career_fair_draft_obj)
            for career_fair_and_product in career_fair_and_products:
                product_obj = ProductDraft.objects.get(pk=career_fair_and_product.product_id)
                product_obj.delete()
            return career_fair_draft_obj
        except CareerFairDraft.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Career Fair Draft object Not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ProductDraft.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Product Draft object Not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(('GET',))
def get_career_fair_product_types(request):
    if request.method == 'GET':
        product_types_dict = Product.get_product_types()
        return Response({'product_types_dict': product_types_dict}, status=status.HTTP_200_OK)
    else:
        logger.exception("Invalid  request.")
        raise ICFException(_("Invalid  request"),
                           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(('GET',))
def get_career_fair_product_buyer_types(request):
    if request.method == 'GET':
        product_buyer_types_dict = Product.get_buyer_types()
        return Response({'product_buyer_types_dict': product_buyer_types_dict}, status=status.HTTP_200_OK)
    else:
        logger.exception("Invalid  request.")
        raise ICFException(_("Invalid  request"),
                           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(('GET',))
def get_career_fair_sub_types(request):
    if request.method == 'GET':
        career_fair_product_sub_types_dict = CareerFairProductSubType.get_career_fair_product_sub_types()
        return Response({'career_fair_product_sub_types_dict': career_fair_product_sub_types_dict},
                        status=status.HTTP_200_OK)
    else:
        logger.exception("Invalid  request.")
        raise ICFException(_("Invalid  request"),
                           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionDraftDetailView(RetrieveAPIView):
    queryset = SessionOptional.objects.all()
    serializer_class = SessionOptionalSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class SupportDraftDetailView(RetrieveAPIView):
    queryset = SupportOptional.objects.all()
    serializer_class = SupportOptionalSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class SpeakerDraftDetailView(RetrieveAPIView):
    queryset = SpeakerOptional.objects.all()
    serializer_class = SpeakerOptionalSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class SessionDetailView(RetrieveAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class SupportDetailView(RetrieveAPIView):
    queryset = Support.objects.all()
    serializer_class = SupportSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class SpeakerDetailView(RetrieveAPIView):
    queryset = Speaker.objects.all()
    serializer_class = SpeakerSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class SessionListByCareerFairView(ICFListMixin, ListAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(career_fair__slug=self.kwargs.get('career_fair_slug'))
            # update the session status for the job which is
            # continues to be active even if it expired
            # status = self.request.query_params.get('status', None)
            # if status and int(status) == Item.ITEM_ACTIVE:
            #     queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class SupportListByCareerFairView(ICFListMixin, ListAPIView):
    queryset = Support.objects.all()
    serializer_class = SupportSerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(career_fair__slug=self.kwargs.get('career_fair_slug'))
            # update the session status for the job which is
            # continues to be active even if it expired
            # status = self.request.query_params.get('status', None)
            # if status and int(status) == Item.ITEM_ACTIVE:
            #     queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class SpeakerListByCareerFairView(ICFListMixin, ListAPIView):
    queryset = Speaker.objects.all()
    serializer_class = SpeakerSerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(career_fair__slug=self.kwargs.get('career_fair_slug'))
            # update the session status for the job which is
            # continues to be active even if it expired
            # status = self.request.query_params.get('status', None)
            # if status and int(status) == Item.ITEM_ACTIVE:
            #     queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class SessionDraftListByCareerFairView(ICFListMixin, ListAPIView):
    queryset = SessionOptional.objects.all()
    serializer_class = SessionOptionalSerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(career_fair__slug=self.kwargs.get('career_fair_slug'))
            # update the session status for the job which is
            # continues to be active even if it expired
            # status = self.request.query_params.get('status', None)
            # if status and int(status) == Item.ITEM_ACTIVE:
            #     queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class SupportDraftListByCareerFairView(ICFListMixin, ListAPIView):
    queryset = SupportOptional.objects.all()
    serializer_class = SupportOptionalSerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(career_fair__slug=self.kwargs.get('career_fair_slug'))
            # update the session status for the job which is
            # continues to be active even if it expired
            # status = self.request.query_params.get('status', None)
            # if status and int(status) == Item.ITEM_ACTIVE:
            #     queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class SpeakerDraftListByCareerFairView(ICFListMixin, ListAPIView):
    queryset = SpeakerOptional.objects.all()
    serializer_class = SpeakerOptionalSerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            queryset = self.queryset.filter(career_fair__slug=self.kwargs.get('career_fair_slug'))
            # update the session status for the job which is
            # continues to be active even if it expired
            # status = self.request.query_params.get('status', None)
            # if status and int(status) == Item.ITEM_ACTIVE:
            #     queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


# class Sa(CreateAPIView):
#     queryset = CareerFairDraft.objects.all()
#     serializer_class = SD
#     # permission_classes = (IsAuthenticated, CanCreateCareerFair)
#
#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         headers = self.get_success_headers(serializer.data)
#         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CareerFairTestSpeakerView(RetrieveUpdateDestroyAPIView):
    queryset = SpeakerOptional.objects.all()
    # serializer_class = CareerFairDraftRetrieveUpdateSerializer
    serializer_class = CareerFairTestSpeakerSerializer

    # permission_classes = (IsAuthenticated, )
    # lookup_field = "slug"

    def get_queryset(self):
        return SpeakerOptional.objects.filter(id=60)

    def get_object(self):
        return SpeakerOptional.objects.get(id=60)

    def get(self, request, *args, **kwargs):
        # return self.retrieve(request, *args, **kwargs)
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class SearchCandidatesForCareerFairAPIView(ListAPIView):
    queryset = UserJobProfile.objects.all()
    serializer_class = CandidateSearchCareerFairUserJobProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:

            career_fair_slug = self.kwargs.get('slug')  # career_fair slug
            entity_slug = self.kwargs.get('entity_slug')
            career_fair_user_id_list = None
            if career_fair_slug:
                career_fair_user_id_list = CareerFairParticipant.objects.filter(career_fair__slug=career_fair_slug,
                                                                                participant_type=CareerFairParticipant.INDIVIDUAL).values_list(
                    'user_id', flat=True)

            user_job_profile_id_list = UserJobProfile.objects.filter(user__id__in=career_fair_user_id_list).values_list(
                "id", flat=True).order_by()

            logger.info("Key skills: {}".format(self.request.data.get('key_skills_id_list', None)))
            logger.info("Computer skills: {}".format(self.request.data.get('computer_skills_id_list', None)))
            logger.info("Language skills: {}".format(self.request.data.get('language_skills_id_list', None)))

            key_skills_id_list = self.request.data.get('key_skills_id_list', [])
            computer_skills_id_list = self.request.data.get('computer_skills_id_list', [])
            language_skills_id_list = self.request.data.get('language_skills_id_list', [])
            is_empty = False

            if len(key_skills_id_list) == 0 and len(computer_skills_id_list) == 0 and len(language_skills_id_list) == 0:
                is_empty = True

            skill_matching_user_profile_id_list = None
            # skills_list = key_skills_id_list + computer_skills_id_list + language_skills_id_list

            profile_id_list = None
            temp_id_list = None

            # Get users with key skills
            # profile_id_list = user_job_profile_id_list
            if not is_empty:
                profile_id_list = user_job_profile_id_list
                if key_skills_id_list and len(key_skills_id_list) > 0:
                    key_skill_ids = [s for s in key_skills_id_list if isinstance(s, int)]
                    temp_id_list = UserSkill.objects.filter(skill_id__in=key_skill_ids,
                                                            job_profile__id__in=profile_id_list).values_list(
                        "job_profile__id", flat=True).order_by()
                    # Update profile id list with users matching key skills
                    profile_id_list = temp_id_list

                # Get intersection of users matching key skills and computer skills
                if computer_skills_id_list and len(computer_skills_id_list) > 0:
                    computer_skill_ids = [s for s in computer_skills_id_list if isinstance(s, int)]
                    temp_id_list = None
                    if profile_id_list:
                        temp_id_list = UserSkill.objects.filter(skill_id__in=computer_skill_ids,
                                                                job_profile__id__in=profile_id_list).values_list(
                            "job_profile__id",
                            flat=True).order_by()

                    # Update profile id list with users matching computer skills
                    profile_id_list = temp_id_list

                # Get intersection of users matching key, computer and language skills
                if language_skills_id_list and len(language_skills_id_list) > 0:
                    language_skill_ids = [s for s in language_skills_id_list if isinstance(s, int)]
                    temp_id_list = None
                    if profile_id_list:
                        temp_id_list = UserSkill.objects.filter(skill_id__in=language_skill_ids,
                                                                job_profile__id__in=profile_id_list).values_list(
                            "job_profile__id",
                            flat=True).order_by()

                    # Update profile id list with users matching language skills
                    profile_id_list = temp_id_list

            if is_empty:
                final_job_profile_list = user_job_profile_id_list
            else:
                final_job_profile_list = profile_id_list

            if final_job_profile_list and len(final_job_profile_list) > 0:
                # print(final_job_profile_list)
                queryset = UserJobProfile.objects.filter(id__in=final_job_profile_list)
                return queryset
            else:
                queryset = UserJobProfile.objects.none()
                return queryset
        except UserJobProfile.DoesNotExist as jpe:
            # logger.exception("UserJobProfile object does not exist")
            # raise ICFException(_("Something went wrong, Please contact admin."),
            # status_code=status.HTTP_400_BAD_REQUEST)
            # user does not have UserJobProfile so will ignore the user
            pass

        except ValueError as ve:
            logger.exception("value of type is not matching {reason}".format(reason=str(ve)))
            raise ICFException(_("Something went wrong, Please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong, Please contact admin."),
                               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # queryset = self.queryset
        # return queryset
        # do some filtering

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        if page is not None:
            # return self.get_paginated_response({'results': serializer.data})
            return self.get_paginated_response(serializer.data)
        else:
            # return Response({'results': serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.data, status=status.HTTP_200_OK)


class CareerFairEntityListApiView(ListAPIView):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    # filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            # queryset = Entity.objects.all()
            career_fair_slug = self.kwargs.get('career_fair_slug', None)
            if career_fair_slug:
                career_fair = CareerFair.objects.get(slug=career_fair_slug)
                # career_fair_products_id_list = CareerFairAndProduct.objects.filter(career_fair=career_fair, product_sub_type=CareerFairProductSubType.TICKET). \
                #     values_list('product_id', flat=True)
                # product_entity_id_list = Product.objects.filter(id__in=career_fair_products_id_list).filter(
                #     buyer_type=Product.ENTITY, product_type=Product.CAREER_FAIR_PRODUCT).values_list('entity_id', flat=True).order_by('-created')
                entity_id_list = CareerFairParticipant.objects.filter(career_fair=career_fair,
                                                                      participant_type=CareerFairParticipant.ENTITY).values_list(
                    'entity_id', flat=True).order_by('-created')
                city_str = self.request.query_params.get('city', None)
                qp_fun_area = self.request.query_params.get('functional-area', None)

                # product_entity_id_list_with_city_filter = None
                if city_str is not None:
                    city_rpr = city_str.split(',')
                    city = city_rpr[0].strip()  # gives the city name
                    # queryset = queryset.filter(address__city__city__icontains=city).order_by('created')
                    entity_id_list = Entity.objects.filter(id__in=entity_id_list, address__city__city__icontains=city). \
                        values_list('id', flat=True).order_by('created')
                if qp_fun_area is not None:
                    entity_id_list = Entity.objects.filter(id__in=entity_id_list,
                                                           industry__industry__icontains=qp_fun_area). \
                        values_list('id', flat=True).order_by('created')

                if entity_id_list:
                    queryset = Entity.objects.filter(id__in=entity_id_list, status=Item.ITEM_ACTIVE).order_by('created')
                else:
                    queryset = Entity.objects.none()
                return queryset
            else:
                logger.exception("Career fair slug not provided.\n")
                return Response(
                    {"detail": "Something went wrong.Please contact admin."},
                    status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add Career Fair Object."}, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the session list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class EntityHasCareerfairAd(CreateAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = CareerFairAdvertisement.objects.all()
    serializer_class = EntityHasCareerFairAdvertisementSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        queryset = self.queryset.filter(entity__id=serializer.validated_data.get("entity"),
                                        career_fair__id=serializer.validated_data.get("career_fair"))
        return Response({"count": queryset.count()}, status=status.HTTP_200_OK)


class EntityCareerFairAdvertisementListApiView(ICFListMixin, ListAPIView):
    queryset = CareerFairAdvertisement.objects.all()
    serializer_class = CareerFairAdvertisementListSerializer

    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_queryset(self):
        try:

            queryset = self.queryset.filter(entity__slug=self.kwargs.get('slug'), )
            return queryset
        except ValueError as ve:
            logger.exception("improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the career fair list for the entity."},
                status=status.HTTP_400_BAD_REQUEST)


class CareerFairSubmitAdvertisementApiView(APIView):
    permission_classes = (IsAuthenticated, IsEntityUser)
    serializer_class = CareerFairAdvertisementListSerializer

    def get_queryset(self):
        return CareerFairAdvertisement.objects.all()

    def get(self, request, **kwargs):
        serialized = self.serializer_class(self.get_queryset(), many=True)
        return Response(serialized.data)

    def _perform_update(self, ad):
        pk = CareerFairAdvertisement.objects.filter(id=ad.get('id')).update(**ad)

    def put(self, request, **kwargs):
        data = request.data
        entity_slug = self.kwargs.get('slug')
        serializer = self.serializer_class(data=data, many=isinstance(data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(data, list):  # Update multiple elements
            for ad in serializer.validated_data:
                self._perform_update(ad)
        else:  # Update one element
            self._perform_update(serializer.validated_data)

        return_queryset = CareerFairAdvertisement.objects.filter(entity__slug=entity_slug)
        output_serializer = self.serializer_class(return_queryset, many=True)
        output_data = output_serializer.data
        if output_data:
            # headers = self.get_success_headers(output_serializer.data)
            return Response(output_data, status=status.HTTP_200_OK, )
        else:
            return Response({'detail': 'No advertisement found for entity'}, status=status.HTTP_200_OK)


class CareerFairAdvertisementListApiView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = CareerFairAdvertisement.objects.all()
    serializer_class = CareerFairAdvertisementListSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, args, kwargs)
        ad_type=None
        if self.request.user_agent.is_mobile:
            ad_type = CareerFairImageType.MOBILE_IMAGE
        elif self.request.user_agent.is_pc:
            ad_type = CareerFairImageType.DESKTOP_IMAGE
        response.data['device_type'] =ad_type
        return  response

    def get_queryset(self):
        ads_to_view = None
        if self.request.user_agent.is_mobile:
            ad_type = CareerFairImageType.MOBILE_IMAGE
            ads_to_view = 1
        elif self.request.user_agent.is_pc:
            ad_type = CareerFairImageType.DESKTOP_IMAGE
            ads_to_view = 4

        try:
            views_queryset = CareerFairAdvertisementViews.objects.filter(career_fair_advertisement__career_fair__slug=self.kwargs.get('slug'),
                                                                         ad_image_type=ad_type,
                                                                         career_fair_advertisement__ad_status=CareerFairAdvertisement.APPROVED).order_by(
                'number_of_views')[:ads_to_view]

            queryset = self.queryset.filter(id__in=[cad.career_fair_advertisement.id for cad in views_queryset])

            # Update the views count
            for view_record in views_queryset:
                view_record.number_of_views = view_record.number_of_views + 1
                view_record.save()

            # CareerFairAdvertisementViews.objects.bulk_update(views_queryset, ['number_of_views'])
            #print(queryset)
            return queryset
        except ValueError as ve:
            logger.exception("Get ad views: improper query parameter.reason:{reason}\n".format(reason=str(ve)))
            return Response(
                {"detail": "Could not get the career fair ad list."},
                status=status.HTTP_400_BAD_REQUEST)


class CareerFairForUserApiView(ListAPIView):
    serializer_class = CareerFairForUserSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = None
        user = self.request.user
        if user:
            qs = CareerFairParticipant.objects.filter(user=user,)
        return qs

# class CareerFairForUserApiView (ListAPIView):
#     permission_classes = (IsAuthenticated,)
#     queryset = CareerFairParticipant.objects.all()
#     serializer_class = CareerFairForUserSerializer

#     def list(self, request):
#         print('---------', request)
#         # Note the use of `get_queryset()` instead of `self.queryset`
#         queryset = self.get_queryset()
#         serializer = CareerFairForUserSerializer(queryset, many=True)
#         return Response(serializer.data)


