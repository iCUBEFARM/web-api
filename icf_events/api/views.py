from datetime import datetime, timezone

from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.generics import CreateAPIView, ListAPIView, DestroyAPIView, RetrieveAPIView, \
    RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from icf_auth.models import UserProfile
from icf_entity.models import Entity
from icf_entity.permissions import IsEntityUser
from icf_events.api.filters import StatusEntityFilter, EventFilters
from icf_events.api.serializers import EventCreateSerializer, CategoryListSerializer, EventListSerializer, \
    EntityEventListSerializer, EventRetrieveSerializer, EventRetrieveUpdateSerializer, EventDraftRetrieveSerializer, \
    EventCreateDraftSerializer, EventDraftRetrieveUpdateSerializer, EventDraftListSerializer, EventGallerySerializer, \
    UpcomingOrPastEventSerializer, EventDraftGallerySerializer, EventCreateDraftCloneSerializer, \
    EventDraftPreviewRetrieveSerializer, ParticipantSearchCreateSerializer, ParticipantSearchListSerializer, \
    ParticipantSearchUserJobProfileSerializer, ParticipantSearchRetrieveUpdateSerializer
from django.utils.translation import ugettext_lazy as _
from icf_events.models import Event, EventMarkedForDelete, EventDraft, EventGallery, EventGalleryOptional, \
    ParticipantSearch
from icf_events.permissions import CanCreateEvent, CanSeeEventsMarkedForDelete, CanMarkEventDelete, \
    CanRejectMarkedForDeleteEvent, CanDeleteEvent, CanPublishEvent, CanEditEvent
from icf_generic.Exceptions import ICFException
from icf_generic.mixins import ICFListMixin
from icf_generic.models import Category, Type, Sponsored, City
from icf_item.models import Item
import logging
from rest_framework.permissions import IsAdminUser

from icf_jobs.JobHelper import get_user_work_experience_in_seconds, get_intersection_of_lists
from icf_jobs.models import UserJobProfile, UserWorkExperience, EducationLevel, UserEducation, UserSkill, Skill
from drf_yasg.utils import swagger_auto_schema

logger = logging.getLogger(__name__)


# class EventCategoryListView(ListAPIView):
#     serializer_class = CategoryListSerializer
#     try:
#         type_obj = Type.objects.get(slug='event')
#     except Type.DoesNotExist as tdn:
#         raise ICFException("Invalid type, please check and try again.",
#                            status_code=status.HTTP_400_BAD_REQUEST)
#     queryset = Category.objects.filter(type=type_obj).order_by('id')
#     pagination_class = None


class EventCreateApiView(CreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventCreateSerializer
    permission_classes = (IsAuthenticated, CanCreateEvent)

    @swagger_auto_schema(
        operation_summary="Create New Event"
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, entity_slug=None, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# Event Stats list for ICF Admins stats table.
# Only visible ot admins aka user.is_staff is True
class StatsEventListView(ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventListSerializer
    permission_classes = [IsAdminUser]

class GeneralEventListView(ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventListSerializer
    filter_class = EventFilters

    @swagger_auto_schema(
        operation_summary="General Event list"
    )
    def get_queryset(self):
        queryset = Event.objects.all().filter(status=Item.ITEM_ACTIVE,
                                              start_date__lte=now(), expiry__gte=now()).order_by("-created")
        try:
            entity = self.request.query_params.get('entity', None)
            if entity:
                queryset = queryset.filter(entity__slug=entity)

            category_name = self.request.query_params.get('category', None)
            if category_name:
                queryset = queryset.filter(category__slug=category_name)

            entity_related_events = self.request.query_params.get('entity_related_events', None)
            if entity_related_events:
                event = Event.objects.get(slug=entity_related_events)
                queryset = queryset.filter(entity=event.entity).exclude(pk=event.pk)

            location = self.request.query_params.get('location')
            if location:
                event = Event.objects.get(slug=location)
                queryset = queryset.filter(location__city__city=event.location.city.city).exclude(pk=event.pk)

            # related events based on education
            related = self.request.query_params.get('related', None)
            if related:
                event = Event.objects.get(slug=related)
                q1 = queryset.filter(category=event.category)
                queryset = q1.distinct().exclude(pk=event.pk)

            return queryset

        except Exception as e:
            logger.debug(e)
            return Event.objects.none()

    @swagger_auto_schema(
        operation_summary="List all Event"
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@swagger_auto_schema(
    operation_summary="List an Entiy's events"
)
class EntityEventList(ICFListMixin, ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EntityEventListSerializer
    filter_class = StatusEntityFilter
    permission_classes = (IsAuthenticated, IsEntityUser)

    @swagger_auto_schema(
        operation_summary="List an Entiy's events"
    )
    def get_queryset(self):
        queryset = self.queryset.filter(entity__slug=self.kwargs.get('entity_slug'))
        # update the event status for the event which is continues to be active even if it expired
        if self.request.query_params['status']:
            if int(self.request.query_params['status']) == Item.ITEM_ACTIVE:
                queryset.filter(expiry__lt=now(), status=Item.ITEM_ACTIVE).update(status=Item.ITEM_EXPIRED)

        return queryset


class EntityEventListCountView(APIView):
    queryset = Event.objects.all()

    @swagger_auto_schema(
        operation_summary="Count of Active Event"
    )
    def list(self, request, *args, **kwargs):
        queryset = self.queryset.filter(status=Item.ITEM_ACTIVE,
                                              start_date__lte=now(), expiry__gte=now()).order_by("-created")
        queryset_count = queryset.count()

        return Response({'active_event_count': queryset_count}, status=status.HTTP_200_OK)


class EventMarkForDeleteCreateView(APIView):
    queryset = Event.objects.all()
    permission_classes = (IsAuthenticated, CanMarkEventDelete)
    lookup_field = "slug"

    @swagger_auto_schema(
        operation_summary="Mark Event to be deleted"
    )
    def post(self, request, *args, **kwargs):
        user = self.request.user
        event_slug = kwargs.get('slug')
        if event_slug is not None:
            try:
                event = Event.objects.get(slug=event_slug)
                if event.status is not Event.ITEM_ACTIVE:
                    return Response({'detail': 'Event is not active ,cannot mark the event for delete '},
                                    status=status.HTTP_403_FORBIDDEN)

            except Event.DoesNotExist as jdn:
                logger.debug(jdn)
                return Response({'detail': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
            try:
                event_marked_for_delete = EventMarkedForDelete.objects.get(event=event)
                if event_marked_for_delete.approval_status == EventMarkedForDelete.REJECTED:
                    event_marked_for_delete.approval_status = EventMarkedForDelete.NEW
                    event_marked_for_delete.user = user
                    event_marked_for_delete.save(update_fields=['approval_status', 'user'])
                    return Response({'detail': 'Event marked for delete'}, status=status.HTTP_201_CREATED)
                elif event_marked_for_delete.approval_status == EventMarkedForDelete.NEW:
                    return Response({'detail': 'Event has already been marked for delete'},
                                    status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'Event cannot be marked for delete because event has been Deleted'},
                                    status=status.HTTP_400_BAD_REQUEST)

            except EventMarkedForDelete.DoesNotExist as e:
                EventMarkedForDelete.objects.create(user=user, event=event)
                return Response({'detail': 'Event marked for delete.'}, status=status.HTTP_201_CREATED)
        else:
            return Response("Bad Request", status=status.HTTP_400_BAD_REQUEST)


class EventMarkedForDeleteListView(ListAPIView):
    permission_classes = (IsAuthenticated, CanSeeEventsMarkedForDelete)
    queryset = Event.objects.all()
    serializer_class = EventListSerializer

    @swagger_auto_schema(
        operation_summary="List Events marked to be deleted"
    )
    def list(self, request, *args, **kwargs):
        events_list = []
        event_marked_for_delete_list = EventMarkedForDelete.objects.all()
        entity_slug = self.kwargs['entity_slug']
        if entity_slug:
            for event in self.get_queryset():
                for emd in event_marked_for_delete_list:
                    if event == emd.event and emd.approval_status == EventMarkedForDelete.NEW and event.entity.slug == entity_slug:
                        events_list.append(event)
            serializer = EventListSerializer(events_list, many=True)
            return Response(serializer.data)

        else:
            logger.info("entity slug not passed.")
            raise ICFException(_("Something went wrong. "), status_code=status.HTTP_400_BAD_REQUEST)


class RejectEventMarkedForDeleteRequestView(APIView):
    queryset = Event.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated, CanRejectMarkedForDeleteEvent)
    lookup_field = "slug"

    @swagger_auto_schema(
        operation_summary="Reject Event marked for deletion"
    )
    def put(self, request, *args, **kwargs):
        user = self.request.user
        event_slug = kwargs.get('slug')
        if event_slug is not None:
            try:
                event = Event.objects.get(slug=event_slug)
                event_marked_for_delete = EventMarkedForDelete.objects.get(event=event)
                if event_marked_for_delete.approval_status == EventMarkedForDelete.NEW:
                    #  if the event_marked_for_delete status is New, Change the event_marked_for_delete
                    #  status to Rejected
                    event_marked_for_delete.approval_status = EventMarkedForDelete.REJECTED
                    event_marked_for_delete.save(update_fields=['approval_status'])
                    return Response({'detail': 'delete request for the event is rejected.'}, status=status.HTTP_200_OK)

                elif event_marked_for_delete.approval_status == EventMarkedForDelete.REJECTED:
                    #  if the event_marked_for_delete status is Rejected, send message as it has been already rejected
                    return Response({'detail': 'the event delete request has been already rejected.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'Event has been deleted'},
                                    status=status.HTTP_400_BAD_REQUEST)

            except Event.DoesNotExist as edn:
                logger.exception(edn)
                return Response({'detail': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
            except EventMarkedForDelete.DoesNotExist as emdn:
                logger.debug(emdn)
                return Response({'detail': 'EventMarkedForDelete does not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response("Bad Request", status=status.HTTP_400_BAD_REQUEST)


class EventDeleteView(DestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = None
    permission_classes = (IsAuthenticated, CanDeleteEvent)
    lookup_field = "slug"

    @swagger_auto_schema(
        operation_summary="Delete Events"
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({'detail': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
        if instance.status == Event.ITEM_DRAFT:
            self.perform_destroy(instance)
            return Response({'detail': 'Draft event has been deleted permanently'}, status=status.HTTP_200_OK)

        elif instance.status == Event.ITEM_ACTIVE:
            try:
                event_marked_for_delete = EventMarkedForDelete.objects.get(event=instance)

                if event_marked_for_delete.approval_status is not EventMarkedForDelete.NEW:
                    return Response({'detail': 'Event cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)

                # Delete the event if EventMarkedForDelete is NEW
                instance.status = Event.ITEM_DELETED
                instance.save(update_fields=['status'])

                # Delete the event if EventMarkedForDelete is NEW
                event_marked_for_delete.approval_status = EventMarkedForDelete.DELETED
                event_marked_for_delete.save(update_fields=['approval_status'])
                return Response({'detail': 'Event has been deleted'}, status=status.HTTP_200_OK)
            except EventMarkedForDelete.DoesNotExist as jmdn:
                logger.debug(jmdn)
                return Response({'detail': 'Event cannot be deleted,because event is not marked for delete'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:

            if instance.status == Event.ITEM_DELETED:
                return Response({'detail': 'Event has been already deleted.'}, status=status.HTTP_400_BAD_REQUEST)
            instance.status = Event.ITEM_DELETED
            instance.save(update_fields=['status'])
            return Response({'detail': 'Event has been deleted'}, status=status.HTTP_200_OK)


class EventCloseView(APIView):
    queryset = Event.objects.all()
    serializer_class = None
    lookup_field = "slug"
    permission_classes = (IsAuthenticated, CanPublishEvent)

    @swagger_auto_schema(
        operation_summary="Mark Event closed"
    )
    def put(self, request, *args, **kwargs):
        event_slug = kwargs.get('slug')
        try:
            event = Event.objects.get(slug=event_slug)
            if event.status == Event.ITEM_CLOSED:
                return Response({'detail': 'Event has been already closed.'}, status=status.HTTP_400_BAD_REQUEST)
            event.status = Event.ITEM_CLOSED
            event.save(update_fields=['status'])
            return Response({'detail': 'Event has been closed.'}, status=status.HTTP_200_OK)

        except Event.DoesNotExist as e:
            logger.exception(e)
            return Response({'detail': 'Event Not found.'}, status=status.HTTP_404_NOT_FOUND)


class EventDetailView(RetrieveAPIView):
    '''
    Single details by slug
    '''
    queryset = Event.objects.all()
    serializer_class = EventRetrieveSerializer
    lookup_field = "slug"

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         event_gallery_images_list = get_event_gallery_images_list(instance)
#
#         serializer = self.get_serializer(instance)
#         # return Response(serializer.data, )
#         return Response({'results': serializer.data, 'event_gallery_images': event_gallery_images_list})
#
#
# def get_event_gallery_images_list(event):
#     gallery_image_list = []
#     gallery_image_dict = {}
#     event_gallery_list = EventGallery.objects.filter(event=event, image_type=EventGallery.GALLERY).order_by('created')
#     index = 0
#     for event_gallery in event_gallery_list:
#         key_index = 'gallery_image_' + str(index)
#         gallery_image_dict[key_index] = event_gallery.image.url
#         gallery_image_list.append(gallery_image_dict)
#         index = index + 1
#     return gallery_image_list


class EventUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = EventRetrieveUpdateSerializer

    permission_classes = (IsAuthenticated, CanEditEvent)

    lookup_field = "slug"

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Event details"
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if event is sponsored
        try:
            sp_obj = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_ACTIVE)
            instance.sponsored_start_dt = sp_obj.start_date
            instance.sponsored_end_dt = sp_obj.end_date
            instance.is_sponsored = True
            serializer = self.get_serializer(instance)
        except Exception as e:
            serializer = self.get_serializer(instance)

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class EventDraftPreviewView(RetrieveAPIView):
    # serializer_class = EventDraftRetrieveSerializer
    serializer_class = EventDraftPreviewRetrieveSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_object(self):
        try:
            return EventDraft.objects.get(slug=self.kwargs.get('event_slug'))
        except EventDraft.DoesNotExist as e:
            logger.exception(e)
            raise


# class DraftEventsViewSet(ModelViewSet):
#     serializer_class = DraftJobSerializer
#     permission_classes = (IsAuthenticated, CanCreateEvent,)
#     queryset = DraftEvent.objects.all()
#
#     def get_serializer(self, *args, **kwargs):
#         return DraftJobRetrieveSerializer(*args, **kwargs)
#
#     def get_object(self):
#         try:
#             return DraftJob.objects.get(pk=self.kwargs.get('pk'))
#         except ObjectDoesNotExist as e:
#             logger.exception(e)
#             raise
#
#     def list(self, request,entity_slug=None,pagination=None):
#         queryset = DraftJob.objects.filter(entity__slug=entity_slug)
#         serializer = DraftJobListSerializer(queryset, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
#
#     def create(self, request, *args, entity_slug=None, **kwargs):
#         entity = Entity.objects.get(slug=entity_slug)
#         context = {'entity': entity}
#
#         serializer = DraftJobSerializer(data=request.data,context=context)
#
#         serializer.is_valid(raise_exception=True)
#         serializer.validated_data['entity'] = entity
#         serializer.save()
#         try:
#             self.perform_create(serializer)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         except:
#             logger.exception("Cannot save job as draft")
#             raise
#
#     def retrieve(self, request, pk=None, *args, **kwargs):
#         try:
#             obj = self.get_object()
#             serializer = DraftJobRetrieveSerializer(obj)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except ObjectDoesNotExist as e:
#             logger.debug(e)
#             return Response({"detail": "Draft job not found"},
#                             status=status.HTTP_400_BAD_REQUEST)
#
#     def update(self, request,pk=None, *args, **kwargs):
#         try:
#             instance = self.get_object()
#             serializer = self.get_serializer(instance, data=request.data)
#             serializer.is_valid(raise_exception=True)
#         except ObjectDoesNotExist as e:
#             logger.debug(e)
#             return Response({"detail": "Draft job not found"}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             self.perform_update(serializer)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except ObjectDoesNotExist as e:
#             logger.debug(e)
#             return Response({"detail": "Draft job not found"}, status=status.HTTP_400_BAD_REQUEST)
#
#     def destroy(self, request, *args, pk=None, **kwargs):
#         try:
#             instance = self.get_object()
#             self.perform_destroy(instance)
#             return Response({"detail": "Draft job got deleted successfully "}, status=status.HTTP_200_OK)
#         except ObjectDoesNotExist as e:
#             logger.debug(e)
#             return Response({'detail': "Draft job not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


class EventDraftCreateApiView(CreateAPIView):
    queryset = EventDraft.objects.all()
    serializer_class = EventCreateDraftSerializer
    permission_classes = (IsAuthenticated, CanCreateEvent)

    @swagger_auto_schema(
        operation_summary="Create Event Draft"
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class EventDraftCloneCreateApiView(CreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventCreateDraftCloneSerializer
    permission_classes = (IsAuthenticated, CanCreateEvent)

    def get_serializer(self, *args, **kwargs):
        return EventCreateDraftCloneSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Clone Event draft"
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, event_slug=None, **kwargs):
        context = {'event_slug': event_slug,
                   'request': request
                   }
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class EntityEventDraftList(ICFListMixin, ListAPIView):
    queryset = EventDraft.objects.all()
    serializer_class = EventDraftListSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    @swagger_auto_schema(
        operation_summary="List Entity Event drafts"
    )
    def get_queryset(self):
        queryset = self.queryset.filter(entity__slug=self.kwargs.get('slug'))
        return queryset


@swagger_auto_schema(
    operation_summary="Entity Event draft detail"
)
class EventDraftDetailView(RetrieveAPIView):
    queryset = EventDraft.objects.all()
    serializer_class = EventDraftRetrieveSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


class EventDraftUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = EventDraft.objects.all()
    serializer_class = EventDraftRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, CanEditEvent)
    lookup_field = "slug"

    @swagger_auto_schema(
        operation_summary="Update Entity Event draft"
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()


class EventGalleryViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EventGallerySerializer
    permission_classes = (IsAuthenticated,)
    queryset = EventGallery.objects.all()

    def get_serializer(self, *args, **kwargs):
        return EventGallerySerializer(*args, **kwargs)

    def get_object(self, slug=None, entity_slug=None, pk=None):
        try:
            instance = EventGallery.objects.get(pk=self.kwargs.get('pk'))
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise
    @swagger_auto_schema(
        operation_summary="List Entity Event Gallery"
    )
    def list(self, request, *args, slug=None, entity_slug=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        qs = self.queryset.filter(entity__slug=entity_slug, event__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="create Entity Event Gallery"
    )
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
            return Response({"detail": "Cannot add image for event."}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="retrieve Entity Event Gallery"
    )
    def retrieve(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve image."}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="update Entity Event Gallery"
    )
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


class EventDraftGalleryViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EventDraftGallerySerializer
    permission_classes = (IsAuthenticated,)
    queryset = EventGalleryOptional.objects.all()

    def get_serializer(self, *args, **kwargs):
        return EventDraftGallerySerializer(*args, **kwargs)

    def get_object(self, slug=None, entity_slug=None, pk=None):
        try:
            instance = EventGalleryOptional.objects.get(pk=self.kwargs.get('pk'))
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    @swagger_auto_schema(
        operation_summary="List Entity Event Draft Gallery"
    )
    def list(self, request, *args, slug=None, entity_slug=None, **kwargs):
        context = {'slug': slug,
                   'entity_slug': entity_slug
                   }
        qs = self.queryset.filter(entity__slug=entity_slug, event__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create Entity Event Draft Gallery"
    )
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
            return Response({"detail": "Cannot add image for event."}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Retrieve Entity Event draft Gallery"
    )
    def retrieve(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve image."}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Update Entity Event draft Gallery"
    )
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

    @swagger_auto_schema(
        operation_summary="Delete Entity Event Draft Gallery"
    )
    def destroy(self, request, *args, slug=None, entity_slug=None, pk=None, **kwargs):
        try:
            instance = self.get_object(slug=slug, entity_slug=entity_slug, pk=pk)
            self.perform_destroy(instance)
            return Response({"detail": "image got deleted successfully."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.debug("image not found, cannot delete.")
            return Response({'detail': "image not found, cannot delete."}, status=status.HTTP_404_NOT_FOUND)


class UpcomingEventsListView(ListAPIView):
    serializer_class = UpcomingOrPastEventSerializer

    def get_queryset(self):

        # slug = self.kwargs.get('slug')
        now = datetime.now()
        queryset = Event.objects.filter(status=Event.ITEM_ACTIVE). \
            filter(expiry__gte=now).order_by('-updated')
        qp_slug = self.request.query_params.get('exclude_event_slug', None)
        qp_event_title = self.request.query_params.get('search_text', None)
        qp_country_name = self.request.query_params.get('country_name', None)

        if qp_slug is not None:
            queryset = queryset.exclude(slug=qp_slug)

        if qp_event_title is not None:
            queryset = queryset.filter(title__icontains=qp_event_title)

        if qp_country_name is not None:
            qp_city_name_str = qp_country_name.split(', ')
            queryset = queryset.filter(location__city__city__icontains=qp_city_name_str[0])

        return queryset


class PastEventsListView(ListAPIView):
    serializer_class = UpcomingOrPastEventSerializer

    def get_queryset(self):

        # slug = self.kwargs.get('slug')
        queryset = Event.objects.filter(status=Event.ITEM_ACTIVE). \
            filter(expiry__lt=datetime.now()).order_by('-updated')
        qp_slug = self.request.query_params.get('exclude_event_slug', None)
        qp_event_title = self.request.query_params.get('search_text', None)
        qp_country_name = self.request.query_params.get('country_name', None)

        if qp_slug is not None:
            queryset = queryset.exclude(slug=qp_slug)

        if qp_event_title is not None:
            queryset = queryset.filter(title__icontains=qp_event_title)

        if qp_country_name is not None:
            qp_city_name_str = qp_country_name.split(', ')
            queryset = queryset.filter(location__city__city__icontains=qp_city_name_str[0])

        return queryset

# Function for saving a search
class SaveParticipantSearchAPIView(CreateAPIView):
    serializer_class = ParticipantSearchCreateSerializer
    queryset = ParticipantSearch.objects.all()
    permission_classes = (IsAuthenticated, IsEntityUser)

    @swagger_auto_schema(
        operation_summary="Function for saving a search"
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            entity_slug = self.kwargs.get('entity_slug')
            entity = Entity.objects.get(slug=entity_slug)
            context = {'entity_slug': entity_slug, 'user': self.request.user}
            serializer = self.get_serializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Entity.DoesNotExist as ce:
            logger.exception("Entity object not found.")
            return Response({"detail": "Entity object not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong. reason:{reason}".format(reason=str(e))), status_code=status.HTTP_400_BAD_REQUEST)



class ParticipantSearchUpdateApiView(RetrieveUpdateAPIView):
    queryset = ParticipantSearch.objects.all()
    serializer_class = ParticipantSearchRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, )

    @swagger_auto_schema(
        operation_summary="Retrieve participant search"
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self):
        try:
            search_slug = self.kwargs.get('search_slug', None)
            if search_slug:
                candidate_search_obj = ParticipantSearch.objects.get(slug=search_slug)
                return candidate_search_obj
        except ParticipantSearch.DoesNotExist as ce:
            logger.info("ParticipantSearch object not found.")
            raise ICFException(_("Object not found."), status_code=status.HTTP_404_NOT_FOUND)


class DeleteParticipantSearchAPIView(DestroyAPIView):
    queryset = ParticipantSearch.objects.all()
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="Delete participant search"
    )
    def destroy(self, request, *args,  **kwargs):
        try:
            instance = ParticipantSearch.objects.get(slug=self.kwargs.get('search_slug'))
            self.perform_destroy(instance)
            return Response({"detail": "ParticipantSearch got deleted successfully."}, status=status.HTTP_200_OK)

        except ParticipantSearch.DoesNotExist as wdne:
            logger.debug("ParticipantSearch object not found, cannot delete")
            return Response({'detail': "ParticipantSearch object not found, cannot delete."},
                            status=status.HTTP_404_NOT_FOUND)


class ParticipantSearchListAPIView(ListAPIView):
    serializer_class = ParticipantSearchListSerializer
    permission_classes = (IsAuthenticated, IsEntityUser)

    @swagger_auto_schema(
        operation_summary="List participant search"
    )
    def get_queryset(self):
        print('-------', self)
        try:
            queryset = ParticipantSearch.objects.filter(entity_slug=self.kwargs.get('entity_slug')).order_by('-created')
            return queryset
        except Exception as cse:
            logger.exception("Something went wrong. reason:{reason}\n".format(reason=str(cse)))
            raise ICFException(_("Something went wrong. Please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)


class ParticipantSearchBySearchSlugAPIView(ListAPIView):
    #
    # api to get candidates(job seekers based on saved search slug)
    #
    queryset = UserJobProfile.objects.all()
    serializer_class = ParticipantSearchUserJobProfileSerializer
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="api to get candidates(job seekers based on saved search slug)"
    )
    def get_queryset(self):
        try:
            search_slug = self.kwargs.get('search_slug', None)
            if search_slug:
                search_obj = ParticipantSearch.objects.get(slug=search_slug)
                # if not search_obj.job_title:
                city_id_list = []
                city_id_str = search_obj.location
                if city_id_str:
                    city_id_list_str = city_id_str.split(",")
                    for i in city_id_list_str:
                        city_id_list.append(int(i))

                work_experience_in_years = search_obj.work_experience

                education_level_id_list = []
                education_level_id_str = search_obj.education_level
                if education_level_id_str:
                    education_level_id_list_str = education_level_id_str.split(",")
                    for i in education_level_id_list_str:
                        education_level_id_list.append(int(i))

                key_skills_id_list = []
                key_skills_id_str = search_obj.key_skill
                if key_skills_id_str:
                    key_skills_id_list_str = key_skills_id_str.split(",")
                    for i in key_skills_id_list_str:
                        key_skills_id_list.append(int(i))

                computer_skills_id_list = []
                computer_skills_id_str = search_obj.computer_skill
                if computer_skills_id_str:
                    computer_skills_id_list_str = computer_skills_id_str.split(",")
                    for i in computer_skills_id_list_str:
                        computer_skills_id_list.append(int(i))

                language_skills_id_list = []
                language_skills_id_str = search_obj.language_skill
                if language_skills_id_str:
                    language_skills_id_list_str = language_skills_id_str.split(",")
                    for i in language_skills_id_list_str:
                        language_skills_id_list.append(int(i))

                location_matching_user_profile_id_list = []
                experience_matching_user_profile_id_list = []
                education_level_matching_user_profile_id_list = []
                key_skill_matching_user_profile_id_list = []
                computer_skill_matching_user_profile_id_list = []
                language_skill_matching_user_profile_id_list = []

                if city_id_list:
                    for city_id in city_id_list:
                        city_obj = City.objects.get(pk=city_id)
                        user_profile_qs = UserProfile.objects.filter(location__city__city__iexact=city_obj.city)
                        for user_profile in user_profile_qs:
                            user_job_profile_obj = UserJobProfile.objects.get(user=user_profile.user)
                            location_matching_user_profile_id_list.append(user_job_profile_obj.pk)

                if work_experience_in_years:
                    work_experience_in_years = int(work_experience_in_years)
                    # convert experience in years to seconds
                    total_required_work_experience_in_seconds = work_experience_in_years * (365 * 24 * 60 * 60)
                    work_exp_job_profile_id_qs = UserWorkExperience.objects.values_list('job_profile_id', flat=True).distinct()
                    for job_profile_id in work_exp_job_profile_id_qs:
                        job_profile_obj = UserJobProfile.objects.get(id=job_profile_id)
                        work_exp_qs = UserWorkExperience.objects.filter(job_profile=job_profile_obj)
                        user_total_work_exp_in_seconds = 0
                        for exp in work_exp_qs:
                            user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from,
                                                                                             exp.worked_till)
                            user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
                        if user_total_work_exp_in_seconds >= total_required_work_experience_in_seconds:
                            experience_matching_user_profile_id_list.append(job_profile_id)

                if education_level_id_list:
                    for education_level_id in education_level_id_list:
                        education_level_obj = EducationLevel.objects.get(id=education_level_id)
                        education_job_profile_id_qs = UserEducation.objects.filter(
                            education_level=education_level_obj).values_list('job_profile', flat=True)
                        for job_profile_id in education_job_profile_id_qs:
                            education_level_matching_user_profile_id_list.append(job_profile_id)
                if key_skills_id_list:
                    for skill_id in key_skills_id_list:
                        key_skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
                                                                               skill__skill_type=Skill.KEY_SKILLS).values_list(
                            'job_profile', flat=True)
                        for job_profile_id in key_skill_job_profile_id_qs:
                            key_skill_matching_user_profile_id_list.append(job_profile_id)
                if computer_skills_id_list:
                    for skill_id in computer_skills_id_list:
                        computer_skill_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
                                                                                    skill__skill_type=Skill.COMPUTER_SKILLS).values_list(
                            'job_profile', flat=True)
                        for job_profile_id in computer_skill_job_profile_id_qs:
                            computer_skill_matching_user_profile_id_list.append(job_profile_id)
                if language_skills_id_list:
                    for skill_id in language_skills_id_list:
                        language_job_profile_id_qs = UserSkill.objects.filter(skill__id=skill_id,
                                                                              skill__skill_type=Skill.LANGUAGE).values_list(
                            'job_profile', flat=True)
                        for job_profile_id in language_job_profile_id_qs:
                            language_skill_matching_user_profile_id_list.append(job_profile_id)
                final_job_profile_list = []
                job_profile_list_1 = get_intersection_of_lists(location_matching_user_profile_id_list,
                                                               experience_matching_user_profile_id_list)
                job_profile_list_2 = get_intersection_of_lists(education_level_matching_user_profile_id_list,
                                                               key_skill_matching_user_profile_id_list)
                job_profile_list_3 = get_intersection_of_lists(computer_skill_matching_user_profile_id_list,
                                                               language_skill_matching_user_profile_id_list)
                final_job_profile_list_1 = get_intersection_of_lists(job_profile_list_1, job_profile_list_2)
                final_job_profile_list_2 = job_profile_list_3
                final_job_profile_list = get_intersection_of_lists(final_job_profile_list_1, final_job_profile_list_2)
                if final_job_profile_list:
                    final_job_profile_list = final_job_profile_list
                    queryset = UserJobProfile.objects.filter(id__in=final_job_profile_list)
                    return queryset
                else:
                    queryset = UserJobProfile.objects.none()
                    return queryset
                # else:
                #     pass

            else:
                logger.exception("invalid search_slug value")
                raise ICFException(_("Something went wrong, Please contact admin."))
        except ParticipantSearch.DoesNotExist as cse:
            logger.exception("ParticipantSearch object does not exist")
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except EducationLevel.DoesNotExist as ele:
            logger.exception("Education level object does not exist")
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.exception("value of type is not matching {reason}".format(reason=str(ve)))
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong, Please contact admin."), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # queryset = self.queryset
        # return queryset
        # do some filtering

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ParticipantSearchObjectAPIView(RetrieveAPIView):
    queryset = ParticipantSearch.objects.all()
    serializer_class = ParticipantSearchListSerializer
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="Retrieve participant search"
    )
    def get_object(self):
        try:
            search_slug = self.kwargs.get('search_slug', None)
            if search_slug:
                candidate_search_obj = ParticipantSearch.objects.get(slug=search_slug)
                return candidate_search_obj
        except ParticipantSearch.DoesNotExist as ce:
            logger.info("ParticipantSearch object not found.")
            raise ICFException(_("Object not found."), status_code=status.HTTP_404_NOT_FOUND)

# class EventOverviewRetrieveView(RetrieveAPIView):
#     serializer_class = EventOverviewSerializer
#     permission_classes = (IsAuthenticated,IsEntityUser)
#
#     def get_object(self):
#         return Entity.objects.filter(slug=self.kwargs.get('slug')).first()
