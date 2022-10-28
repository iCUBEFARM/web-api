from django.db.models import Q
from django.utils.timezone import now
from guardian.shortcuts import get_perms
from rest_framework import status
from rest_framework import filters
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser
from django.core.exceptions import ObjectDoesNotExist

from icf_entity.api.mixins import ICFEntityMixin
from icf_entity.models import Entity
from icf_entity.permissions import IsEntityUser
from icf_jobs.permissions import CanCreateJob
from icf_messages.api.serializers import ComposeSerializer, InboxSerializer, MessageAttachmentSerializer, UserReplySerializer, EntityReplySerializer, \
    MessageThreadSerializer, ICFNotificationSerializer, ComposeAndEmailSerializer
from icf_messages.manager import ICFNotificationManager
from icf_messages.models import ICFMessage, AppMessagePerm, ICFNotification, MessageAttachmentUpload
from icf_messages.permissions import EntityMessagePermission, CanReplyForEntity, CanViewForEntity, CanViewConversation, \
    UserCanReply
import logging
logger = logging.getLogger(__name__)


class ComposeApiView(CreateAPIView):
    """
    Compose of message thread is always done by the entity
    """
    queryset = ICFMessage.objects.all()
    serializer_class = ComposeSerializer
    permission_classes = (IsAuthenticated, EntityMessagePermission)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        entity_slug = self.kwargs['entity_slug']
        context = {'entity_slug': entity_slug, 'user': request.user}

        serializer = ComposeSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ComposeMessageAndEmailApiView(CreateAPIView):
    """
        Compose of message thread is always done by the entity
        """
    queryset = ICFMessage.objects.all()
    serializer_class = ComposeAndEmailSerializer
    permission_classes = (IsAuthenticated, EntityMessagePermission)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        entity_slug = self.kwargs['entity_slug']
        context = {'entity_slug': entity_slug, 'user': request.user}

        serializer = ComposeAndEmailSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserReplyApiView(CreateAPIView):
    """
    Reply message
    """
    queryset = ICFMessage.objects.all()
    serializer_class = UserReplySerializer
    permission_classes = (IsAuthenticated, UserCanReply )

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):

        message_id = self.kwargs['message_id']
        context = {'message_id': message_id, 'user': request.user}

        serializer = UserReplySerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class EntityReplyApiView(CreateAPIView):
    """
    Reply message
    """
    queryset = ICFMessage.objects.all()
    serializer_class = EntityReplySerializer
    permission_classes = (IsAuthenticated, CanReplyForEntity)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):

        message_id = self.kwargs['message_id']
        entity_slug = self.kwargs['entity_slug']
        context = {'message_id': message_id, 'entity_slug': entity_slug, 'user': request.user}

        serializer = EntityReplySerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class MessageListMixin(object):
    queryset = ICFMessage.objects.all().order_by('-sent_at')
    serializer_class = InboxSerializer

    def message_list(self):
        page = self.paginate_queryset(self.queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data)

    def get_app_filter(self, user, entity):
        """
        Only for Entity user. Need to check which app messages the user can view
        :return:
        """
        perm_filter=None
        all_msg_perms = AppMessagePerm.objects.get_all_perms()
        for perm, app_slug in all_msg_perms.items():
            if perm in get_perms(user, entity):
                if not perm_filter:
                    perm_filter = Q()
                perm_filter.add(Q(app_type__slug=app_slug), Q.OR)

        if perm_filter is not None:
            return perm_filter

        return None

    def get_filter(self,q):
        query = self.queryset
        query = query.filter(recipient_name__icontains=q) | \
                        query.filter(sender_name__icontains=q) | \
                        query.filter(subject__icontains=q) | \
                        query.filter(body__icontains=q)
        return query


class UserInboxApiView(MessageListMixin, ListAPIView):
    """
    Inbox for the user
    """
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        q = self.request.query_params.get('q')
        self.queryset = ICFMessage.objects.inbox(request.user)

        unique_thread_id_list = []
        thread_id_list = list([i.thread.pk for i in self.queryset])

        # add only unique thread pk to unique_thread_id_list
        for id in thread_id_list:
            if id not in unique_thread_id_list:
                unique_thread_id_list.append(id)

        queryset = []
        for i in unique_thread_id_list:
            queryset.append(self.queryset.filter(thread=i).order_by('-id').first())
        self.queryset = queryset

        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class EntityInboxApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Inbox of the company
    """
    permission_classes = (IsAuthenticated, CanViewForEntity)
    app_filter = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        app_filter = self.get_app_filter(request.user, entity)
        self.queryset = ICFMessage.objects.inbox(entity, app_filter=app_filter)

        thread_id = set([i.thread.pk for i in self.queryset])
        queryset = []
        for i in thread_id:
            queryset.append(self.queryset.filter(thread=i).order_by('-id').first())
        self.queryset = queryset

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class EntityInboxCountApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Inbox of the company
    """
    permission_classes = (IsAuthenticated, CanViewForEntity)
    app_filter = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        app_filter = self.get_app_filter(request.user, entity)
        self.queryset = ICFMessage.objects.inbox(entity, app_filter=app_filter)

        thread_id = set([i.thread.pk for i in self.queryset])
        queryset = []
        for i in thread_id:
            queryset.append(self.queryset.filter(thread=i).order_by('-id').first())
        self.queryset = queryset

        queryset_count = self.queryset.count()

        return Response({'entity_inbox_count': queryset_count}, status=status.HTTP_200_OK)


class UserConversationApiView(MessageListMixin, ListAPIView):
    """
    View the conversation thread by user
    """
    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        self.queryset = ICFMessage.objects.thread(request.user, query_filter)

        for m in self.queryset:
            if m.recipient_id == request.user.id and m.read_at is None:
                ICFMessage.objects.set_read(request.user, query_filter)
                break

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class EntityConversationApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    View the conversation thread by Entity
    """
    permission_classes = (IsAuthenticated, CanViewConversation)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        self.queryset = ICFMessage.objects.thread(entity, query_filter)

        for m in self.queryset:
            if m.recipient_id == entity.id and m.read_at is None:
                ICFMessage.objects.set_read(entity, query_filter)
                break

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class UserSentApiView(MessageListMixin, ListAPIView):
    """
    Sent items for the user
    """
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        self.queryset = ICFMessage.objects.sent(request.user)

        thread_id = set([i.thread.pk for i in self.queryset])
        queryset = []
        for i in thread_id:
            queryset.append(self.queryset.filter(thread=i).order_by('-id').first())
        self.queryset = queryset

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class EntitySentApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Sent items of the company
    """
    permission_classes = (IsAuthenticated, CanCreateJob)

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        app_filter = self.get_app_filter(request.user, entity)
        self.queryset = ICFMessage.objects.sent(entity, app_filter=app_filter)

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class UserArchiveApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Archived items for the user
    """
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        self.queryset = ICFMessage.objects.archives(request.user)

        thread_id = set([i.thread.pk for i in self.queryset])
        queryset = []
        for i in thread_id:
            queryset.append(self.queryset.filter(thread=i).order_by('-id').first())
        self.queryset = queryset

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class EntityArchiveApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Archived items of the company
    """
    permission_classes = (IsAuthenticated, CanCreateJob)

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        app_filter = self.get_app_filter(request.user, entity)
        self.queryset = ICFMessage.objects.archives(entity, app_filter=app_filter)

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class UserTrashApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Deleted items for the user
    """
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        self.queryset = ICFMessage.objects.trash(request.user)

        thread_id = set([i.thread.pk for i in self.queryset])
        queryset = []
        for i in thread_id:
            queryset.append(self.queryset.filter(thread=i).order_by('-id').first())
        self.queryset = queryset

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


class EntityTrashApiView(MessageListMixin, ICFEntityMixin, ListAPIView):
    """
    Deleted items of the company
    """
    permission_classes = (IsAuthenticated, CanCreateJob)

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        app_filter = self.get_app_filter(request.user, entity)
        self.queryset = ICFMessage.objects.trash(entity, app_filter=app_filter)

        q = self.request.query_params.get('q')
        if q:
            self.queryset = self.get_filter(q)

        return self.message_list()


# class ReplyApiView(CreateAPIView):
#     """
#     Compose of message thread is always done by the entity
#     """
#     queryset = ICFMessage.objects.all()
#     serializer_class = ReplySerializer
#     permission_classes = (IsAuthenticated, CanCreateJob)
#
#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         entity_slug = self.kwargs['entity_slug']
#         context = {'entity_slug': entity_slug}
#
#         serializer = ComposeSerializer(data=request.data, context=context)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         headers = self.get_success_headers(serializer.data)
#         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# class UserArchiveApiView(UpdateAPIView):
#     for skills in job_skills_data:
#         skill = skills.pop('skill')
#         JobSkill.objects.update_or_create(skill=skill, job=job)

class SetUserArchiveApiView(MessageListMixin, ListAPIView):

    permission_classes = (IsAuthenticated, )
    serializer_class = None

    def list(self, request, *args, **kwargs):
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        ICFMessage.objects.set_archive(request.user, query_filter)

        return Response({"detail": "Archived the messages of thread"}, status=status.HTTP_200_OK)
()


class SetEntityArchiveApiView(MessageListMixin, ICFEntityMixin, ListAPIView):

    permission_classes = (IsAuthenticated, CanViewConversation)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        ICFMessage.objects.set_archive(entity, query_filter)

        return Response({"detail": "Archived the messages of thread"}, status=status.HTTP_200_OK)


class SetUserRestoreArchivedApiView(MessageListMixin, ListAPIView):

    permission_classes = (IsAuthenticated, )
    serializer_class = None

    def list(self, request, *args, **kwargs):
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        ICFMessage.objects.restore_archived(request.user, query_filter)

        return Response({"detail": "Restored Archived messages of thread"}, status=status.HTTP_200_OK)


class SetEntityRestoreArchivedApiView(MessageListMixin, ICFEntityMixin, ListAPIView):

    permission_classes = (IsAuthenticated, CanViewConversation)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        ICFMessage.objects.restore_archived(entity, query_filter)

        return Response({"detail": "Restored Archived messages of thread"}, status=status.HTTP_200_OK)


class SetUserDeleteApiView(MessageListMixin, ListAPIView):

    permission_classes = (IsAuthenticated, )
    serializer_class = None


    def list(self, request, *args, **kwargs):
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)

        ICFMessage.objects.set_delete(request.user, query_filter)

        return Response({"detail": "Deleted the messages of thread"}, status=status.HTTP_200_OK)



class SetEntityDeleteApiView(MessageListMixin, ICFEntityMixin, ListAPIView):

    permission_classes = (IsAuthenticated, CanViewConversation)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)

        ICFMessage.objects.set_delete(entity, query_filter)

        return Response({"detail": "Deleted the messages of thread"}, status=status.HTTP_200_OK)


class SetUserRestoreDeletedApiView(MessageListMixin, ListAPIView):

    permission_classes = (IsAuthenticated,)
    serializer_class = None


    def list(self, request, *args, **kwargs):
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        ICFMessage.objects.restore_deleted(request.user, query_filter)

        return Response({"detail": " Restored Deleted messages of thread"}, status=status.HTTP_200_OK)



class SetEntityRestoreDeletedApiView(MessageListMixin, ICFEntityMixin, ListAPIView):

    permission_classes = (IsAuthenticated, CanViewConversation)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        thread_id = self.kwargs['thread_id']
        query_filter = Q(thread=thread_id)
        ICFMessage.objects.restore_deleted(entity, query_filter)

        return Response({"detail": "Restored Deleted messages of thread"}, status=status.HTTP_200_OK)


class InboxUnreadCount(APIView):

    def get(self, request, *args, **kwargs):
        inbox_unread_count = ICFMessage.objects.inbox_unread_count(request.user)
        return Response({"inbox_unread_count": inbox_unread_count}, status=status.HTTP_200_OK)

class EntityInboxUnreadCount(APIView, ICFEntityMixin):

    def get(self, request, *args, **kwargs):
        entity = self.get_entity(self.kwargs['entity_slug'])
        inbox_unread_count = ICFMessage.objects.inbox_unread_count(entity)
        return Response({"inbox_unread_count": inbox_unread_count}, status=status.HTTP_200_OK)

class NotificationListMixin(object):
    queryset = ICFNotification.objects.all()
    serializer_class = ICFNotificationSerializer

    def message_list(self):
        page = self.paginate_queryset(self.queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data)


class IcfNotificationList(ListAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = ICFNotification.objects.all()
    serializer_class = ICFNotificationSerializer

    def list(self, request, *args, **kwargs):

        user = self.request.user
        self.queryset = ICFNotificationManager.get_notication_list(user)
        serializer = self.get_serializer(self.queryset, many=True)
        ICFNotification.objects.filter(user=user,read_at=None,deleted_at=None).update(read_at=now())

        page = self.paginate_queryset(self.queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            print('--------', serializer.data)
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data)

    # def list(self, request, *args, **kwargs):
    #     user = self.request.user
    #     self.queryset = ICFNotificationManager.get_notication_list(user)
    #
    #     for notification in self.queryset:
    #         if notification.user_id == request.user.id and notification.read_at is None:
    #             notification.read_at = now()
    #             notification.save()
    #             break
    #
    #     return self.message_list()


class NotificationListCount(APIView):

    def get(self, request, *args, **kwargs):
        notification_unread_count = ICFNotification.objects.filter(user=request.user,read_at=None,deleted_at=None).count()
        return Response({"notification_unread_count": notification_unread_count}, status=status.HTTP_200_OK)


class SetNotificationDeleteApiView(MessageListMixin, ListAPIView):
    permission_classes = (IsAuthenticated, )
    serializer_class = None

    def list(self, request, *args, **kwargs):
        id = self.kwargs['id']
        ICFNotification.objects.filter(id=id,user=request.user).update(deleted_at=now())
        return Response({"detail": "Deleted the notification"}, status=status.HTTP_200_OK)


class NotificationDeleteApiView(ListAPIView):
    permission_classes = (IsAuthenticated, )
    serializer_class = ICFNotificationSerializer
    queryset = ICFNotification.objects.all()

    def list(self, request, *args, **kwargs):
        user = self.request.user
        self.queryset = self.queryset.filter(user=user,deleted_at__isnull=False)

        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data)

#  Viwe for attaching a file on messages
class MessageAttachmentViewSet(ModelViewSet):
    parser_classes = (MultiPartParser, FormParser, FileUploadParser)
    serializer_class = MessageAttachmentSerializer
    permission_classes = (IsAuthenticated,)
    queryset = MessageAttachmentUpload.objects.all()

    def get_serializer(self, *args, **kwargs):
        return MessageAttachmentSerializer(*args, **kwargs)

    def get_object(self, queryset=None):
        instance = MessageAttachmentSerializer.objects.filter(pk=self.kwargs['pk']).first()
        return instance

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = MessageAttachmentSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return Response({"detail": "Cannot add job profile files"}, status=status.HTTP_400_BAD_REQUEST)
