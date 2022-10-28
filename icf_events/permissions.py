from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms
from guardian.conf import settings
from rest_framework import permissions
from django.utils.translation import ugettext_lazy as _
from rest_framework.permissions import SAFE_METHODS

from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import EntityPerms, Entity
from icf_events.models import EventPerms, Event


class CanCreateEvent(permissions.BasePermission):
    message = _("You do not have the permissions to create a Event for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, EventPerms.EVENT_ADMIN, EventPerms.EVENT_CREATE, ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('entity_slug')

        entity = Entity.objects.get(slug=entity_slug)

        if entity:
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_write_perms)

        return False


class CanEditEvent(permissions.BasePermission):
    message = _("You do not have the permissions to create a event for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT,
                          EventPerms.EVENT_ADMIN, EventPerms.EVENT_CREATE, ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):

        entity = obj.entity

        if request.user == obj.owner:
            return True

        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanPublishEvent(permissions.BasePermission):
    message = _("You do not have the permissions to publish a event for entity.")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT,
                          EventPerms.EVENT_ADMIN, EventPerms.EVENT_PUBLISH]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):
        entity = obj.entity
        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanMarkEventDelete(permissions.BasePermission):
    message = _("You do not have the permissions to mark a event as Delete for entity.")
    allowed_read_perms = [EventPerms.EVENT_PUBLISH]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        slug = view.kwargs.get('slug')
        try:
            event = Event.objects.get(slug=slug)
            entity = event.entity
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Event.DoesNotExist as dne:
            return False
        except Entity.DoesNotExist as dne:
            return False


class CanSeeEventsMarkedForDelete(permissions.BasePermission):
    message = _("You do not have permissions to see the events marked for Delete.")
    allowed_read_perms = [EventPerms.EVENT_ADMIN]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        entity_slug = view.kwargs.get('entity_slug')
        try:
            entity = Entity.objects.get(slug=entity_slug)
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Entity.DoesNotExist as dne:
            return False


class CanRejectMarkedForDeleteEvent(permissions.BasePermission):
    message = _("You do not have the permissions to reject a event delete request for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EventPerms.EVENT_ADMIN, ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        slug = view.kwargs.get('slug')
        try:
            event = Event.objects.get(slug=slug)
            entity = event.entity
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Event.DoesNotExist as edne:
            return False


class CanDeleteEvent(permissions.BasePermission):
    message = _("You do not have the permissions to delete events for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EventPerms.EVENT_ADMIN, ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):

        entity = obj.entity
        # Any user with create permission can delete a draft
        if request.user.has_perm(EventPerms.EVENT_CREATE, entity) and obj.status == Event.ITEM_DRAFT:
            return True

        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class ICFEventsUserPermManager:
    ADD_PERM = 1
    REMOVE_PERM = 2

    #
    # If the permission is one of the Entity permissions, set it
    # else, send entity_set_permission signal that can be processed
    # by other apps that have included permissions on the entity
    #
    @classmethod
    def set_user_perm(cls, action, user, entity, perm):

        event_perms = EventPerms.get_event_perms()

        #
        # If not a basic entity permission, send a signal
        # Other applications to handle
        #
        if perm not in event_perms.values():
            return None

        perms_for_user = []
        if perm == EventPerms.get_admin_perm():
            for value in event_perms.values():
                perms_for_user.append(value)
        else:
            perms_for_user.append(perm)

        for user_perm in perms_for_user:
            group_name = EventPerms.get_entity_group(entity, user_perm)
            group = Group.objects.get(name=group_name)

            if action == cls.ADD_PERM:
                user.groups.add(group)
            elif action == cls.REMOVE_PERM:
                user.groups.remove(group)

        return user

    @classmethod
    def add_user_perm(cls, sender, user=None, entity=None, perm=None, **kwargs):
        return cls.set_user_perm(cls.ADD_PERM, user, entity, perm)

    @classmethod
    def remove_user_perm(cls, sender, user=None, entity=None, perm=None, **kwargs):
        return cls.set_user_perm(cls.REMOVE_PERM, user, entity, perm)



