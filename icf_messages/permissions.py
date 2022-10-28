from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models
from guardian.shortcuts import get_perms
from guardian.conf import settings
from rest_framework import permissions
from django.utils.translation import ugettext_lazy as _
from rest_framework.permissions import SAFE_METHODS

from icf_entity.api.mixins import ICFEntityMixin
from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import EntityPerms, Entity
from icf_jobs.models import JobPerms, Job
from icf_messages.models import AppMessagePerm, ICFMessage


class EntityMessagePermission(ICFEntityMixin, permissions.BasePermission):

    message = _("You do not have the permissions to compose a message")
    allowed_read_perms = [EntityPerms.ENTITY_USER, ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('entity_slug')

        if entity_slug:
            entity = self.get_entity(entity_slug)
            if request.method in SAFE_METHODS:
                return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
            else:
                return any(perm in get_perms(request.user, entity) for perm in self.allowed_write_perms)
        else:
            return False

    def has_object_permission(self, request, view, obj):

        if request.method in SAFE_METHODS:
            return any(perm in get_perms(request.user, obj) for perm in self.allowed_read_perms)
        else:
            return any(perm in get_perms(request.user, obj) for perm in self.allowed_write_perms)


class CanReplyForEntity(ICFEntityMixin, permissions.BasePermission):
    message = _("You do not have the permissions to reply to this message")

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('entity_slug')
        entity = self.get_entity(entity_slug)

        message_id = view.kwargs.get('message_id')
        message = ICFMessage.objects.get(id=message_id)
        message_type = message.app_type

        app_perm_reqd = AppMessagePerm.objects.get_perm_for_app(message_type.slug)

        if app_perm_reqd in get_perms(request.user, entity):
            return True


class UserCanReply(ICFEntityMixin, permissions.BasePermission):
    message = _("You do not have the permissions to reply to this message")

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        message_id = view.kwargs.get('message_id')
        message = ICFMessage.objects.get(id=message_id)

        if message.recipient_type == ContentType.objects.get_for_model(request.user) and \
                message.recipient_id == request.user.id:
            return True

        if message.sender_type == ContentType.objects.get_for_model(request.user) and \
                message.sender_id == request.user.id:
            return True


class CanViewConversation(ICFEntityMixin, permissions.BasePermission):
    message = _("You do not have the permissions to reply to this message")

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('entity_slug')
        entity = self.get_entity(entity_slug)

        thread_id = view.kwargs.get('thread_id')
        message = ICFMessage.objects.filter(thread_id=thread_id).first()
        message_type = message.app_type

        app_perm_reqd = AppMessagePerm.objects.get_perm_for_app(message_type.slug)

        if app_perm_reqd in get_perms(request.user, entity):
            return True


class CanViewForEntity(ICFEntityMixin, permissions.BasePermission):
    message = _("You do not have the permissions to read entity messages")

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('entity_slug')

        entity = self.get_entity(entity_slug)

        perm_filter=None
        all_msg_perms = AppMessagePerm.objects.get_all_perms()

        return any(perm in get_perms(user, entity) for perm in all_msg_perms.keys())

        # for perm, app_slug in all_msg_perms.items():
        #     if perm in get_perms(user, entity):
        #         if not perm_filter:
        #             perm_filter = models.Q()
        #         perm_filter.add(app_type__slug=app_slug)
        # if perm_filter is not None:
        #     view.perm_filter = perm_filter
        #     return True
        #


