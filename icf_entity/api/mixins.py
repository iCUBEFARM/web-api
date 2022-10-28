from guardian.conf import settings
from guardian.shortcuts import get_perms
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS

from icf_entity.models import Entity, EntityUser, EntityPerms
from icf_generic.Exceptions import ICFException
from django.utils.translation import ugettext_lazy as _
import logging
logger = logging.getLogger(__name__)

class ICFEntityMixin(object):
    def get_entity(self, entity_slug):
        entity = None
        try:
            entity = Entity.objects.get(slug=entity_slug)
            return entity
        except Entity.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find entity"), status_code=status.HTTP_400_BAD_REQUEST)


class ICFEntityPermissionMixin(ICFEntityMixin, object):

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('slug')
        if not entity_slug:
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

