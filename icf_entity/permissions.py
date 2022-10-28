from django.contrib.auth.models import Group, _user_has_perm, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import Signal
from guardian.shortcuts import get_perms
from rest_framework import permissions
from guardian.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework.permissions import SAFE_METHODS

from icf_auth.models import User
from icf_entity.api.mixins import ICFEntityPermissionMixin, ICFEntityMixin
from icf_entity.models import EntityPerms, EntityUser, Entity
from icf_entity.signals import entity_add_permission, entity_remove_permission

import logging

logger = logging.getLogger(__name__)

# class CanAddEntityUser(ICFEntityPermissionMixin, permissions.BasePermission):
#     message = _("Do not have permissions to add user to entity")
#     allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_ADD_USER, ]
#     allowed_write_perms = allowed_read_perms


class IsEntityAdmin(ICFEntityPermissionMixin, permissions.BasePermission):
    message = _("You do not have the permissions of an entity admin")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, ]
    allowed_write_perms = allowed_read_perms


class CanEditEntity(ICFEntityPermissionMixin, permissions.BasePermission):
    message = _("You do not have the permissions to edit this entity")
    allowed_read_perms = allowed_write_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, ]
    allowed_write_perms = allowed_read_perms


class IsEntityUser(ICFEntityPermissionMixin, permissions.BasePermission):
    message = _("You do not have the permissions to view users of this entity")
    allowed_read_perms = [EntityPerms.ENTITY_USER, ]
    allowed_write_perms = allowed_read_perms


class CanAddEntityUser(ICFEntityPermissionMixin, permissions.BasePermission):
    message = _("You do not have the permissions to view users of this entity")
    allowed_read_perms = [EntityPerms.ENTITY_USER, ]
    allowed_write_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, EntityPerms.ENTITY_ADD_USER ]


class CanViewEntityPerm(ICFEntityPermissionMixin, permissions.BasePermission):
    message = _("You do not have the permissions to view users of this entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, EntityPerms.ENTITY_ADD_USER ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        if request.method in SAFE_METHODS:
            try:
                user = request.user
                other_user_param = request.query_params.get('other', None)
                entity_slug = view.kwargs.get('slug')

                entity = self.get_entity(entity_slug)

                if not user.has_perm(EntityPerms.ENTITY_USER, entity):
                    return False

                # If the call is to get permissions for current logged in user
                if not other_user_param:
                    return True

                # If the call is to get permissions of another user
                other_user = User.objects.get(slug=other_user_param)

                if not other_user.has_perm(EntityPerms.ENTITY_USER, entity):
                    return False

                return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)

            except ObjectDoesNotExist:
                return False

        return False


class EntityLogoPerm(ICFEntityPermissionMixin, permissions.BasePermission):
    message = _("You do not have the permissions to view users of this entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, EntityPerms.ENTITY_USER, ]
    allowed_write_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, EntityPerms.ENTITY_ADD_USER ]


class ICFEntityUserPermManager:

    @classmethod
    def get_user_permissions(cls, user, entity):
        entity_perms = EntityPerms.get_icf_permissions()
        user_perms = get_perms(user, entity)
        response = dict()
        for perm in entity_perms:
            response[perm.codename] = False
            if perm.codename in user_perms:
                response[perm.codename] = True

        return response

    #
    # If the permission is one of the Entity permissions, set it
    # else, send entity_set_permission signal that can be processed
    # by other apps that have included permissions on the entity
    #
    @classmethod
    def add_user_perm(cls, user, entity, perm):

        entity_perms = EntityPerms.get_entity_perms()

        #
        # If not a basic entity permission, send a signal
        # Other applications to handle
        #
        if perm not in entity_perms.values():
            response = entity_add_permission.send_robust(sender=cls.__class__, entity=entity, user=user, perm=perm)
            logger.info("Add permission signal response : {} ".format(response))
            return user

        perms_for_user = []
        if perm == EntityPerms.get_admin_perm():
            # Icf permissions provide all possible permissions on the Entity object ( which could have been created by
            # other apps also )
            for perm_obj in EntityPerms.get_icf_permissions():
                perms_for_user.append(perm_obj.codename)
        else:
            perms_for_user.append(perm)

        for user_perm in perms_for_user:
            group_name = EntityPerms.get_entity_group(entity, user_perm)
            group = Group.objects.get(name=group_name)
            user.groups.add(group)

        return user

    @classmethod
    def remove_user_perm(cls, user, entity, perm):
        entity_perms = EntityPerms.get_entity_perms()

        #
        # If not a basic entity permission, send a signal
        # Other applications to handle
        #
        if perm not in entity_perms.values():
            response = entity_remove_permission.send_robust(sender=cls.__class__, entity=entity, user=user, perm=perm)
            logger.info("Remove permission signal response : {} ".format(response))
            return user

        perms_for_user = []
        if perm == EntityPerms.get_admin_perm():

            for perm_obj in EntityPerms.get_icf_permissions():
                # When admin permission is removed the Entity user permission should not be removed
                if perm_obj.codename == EntityPerms.get_entity_user_perm():
                    continue

                perms_for_user.append(perm_obj.codename)
        else:
            perms_for_user.append(perm)

        for user_perm in perms_for_user:
            group_name = EntityPerms.get_entity_group(entity, user_perm)
            group = Group.objects.get(name=group_name)
            user.groups.remove(group)

        return user

    @classmethod
    def has_entity_perm(cls, user, entity, perm):
        return user.has_perm(perm, entity)

