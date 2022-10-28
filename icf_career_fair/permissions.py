from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms
from guardian.conf import settings
from rest_framework import permissions
from django.utils.translation import ugettext_lazy as _
from rest_framework.permissions import SAFE_METHODS

from icf_career_fair.models import CareerFairPerms, CareerFair
from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import EntityPerms, Entity


class CanCreateCareerFair(permissions.BasePermission):
    message = _("You do not have the permissions to create a career fair for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, CareerFairPerms.CAREER_FAIR_ADMIN, CareerFairPerms.CAREER_FAIR_CREATE, ]
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


class CanEditCareerFair(permissions.BasePermission):
    message = _("You do not have the permissions to create a career fair for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT,
                          CareerFairPerms.CAREER_FAIR_ADMIN, CareerFairPerms.CAREER_FAIR_CREATE, ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):

        entity = obj.entity

        if request.user == obj.owner:
            return True

        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanPublishCareerFair(permissions.BasePermission):
    message = _("You do not have the permissions to publish a career fair for entity.")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT,
                          CareerFairPerms.CAREER_FAIR_ADMIN, CareerFairPerms.CAREER_FAIR_PUBLISH]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):
        entity = obj.entity
        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanMarkCareerFairDelete(permissions.BasePermission):
    message = _("You do not have the permissions to mark a career fair as delete for entity.")
    allowed_read_perms = [CareerFairPerms.CAREER_FAIR_ADMIN]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        slug = view.kwargs.get('slug')
        try:
            career_fair = CareerFair.objects.get(slug=slug)
            entity = career_fair.entity
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except CareerFair.DoesNotExist as dne:
            return False
        except Entity.DoesNotExist as dne:
            return False


class CanSeeCareerFairsMarkedForDelete(permissions.BasePermission):
    message = _("You do not have permissions to see the career fairs marked for delete.")
    allowed_read_perms = [CareerFairPerms.CAREER_FAIR_ADMIN]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        entity_slug = view.kwargs.get('entity_slug')
        try:
            entity = Entity.objects.get(slug=entity_slug)
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Entity.DoesNotExist as dne:
            return False


class CanRejectMarkedForDeleteCareerFair(permissions.BasePermission):
    message = _("You do not have the permissions to reject a career fair delete request for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, CareerFairPerms.CAREER_FAIR_ADMIN, ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        slug = view.kwargs.get('slug')
        try:
            career_fair = CareerFair.objects.get(slug=slug)
            entity = career_fair.entity
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except CareerFair.DoesNotExist as edne:
            return False


class CanDeleteCareerFair(permissions.BasePermission):
    message = _("You do not have the permissions to delete career fair's for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, CareerFairPerms.CAREER_FAIR_ADMIN, ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):

        entity = obj.entity
        # Any user with create permission can delete a draft
        if request.user.has_perm(CareerFairPerms.CAREER_FAIR_CREATE, entity) and obj.status == CareerFair.ITEM_DRAFT:
            return True

        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class ICFCareerFairsUserPermManager:
    ADD_PERM = 1
    REMOVE_PERM = 2

    #
    # If the permission is one of the Entity permissions, set it
    # else, send entity_set_permission signal that can be processed
    # by other apps that have included permissions on the entity
    #
    @classmethod
    def set_user_perm(cls, action, user, entity, perm):

        career_fair_perms = CareerFairPerms.get_career_fair_perms()

        #
        # If not a basic entity permission, send a signal
        # Other applications to handle
        #
        if perm not in career_fair_perms.values():
            return None

        perms_for_user = []
        if perm == CareerFairPerms.get_admin_perm():
            for value in career_fair_perms.values():
                perms_for_user.append(value)
        else:
            perms_for_user.append(perm)

        for user_perm in perms_for_user:
            group_name = CareerFairPerms.get_entity_group(entity, user_perm)
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





