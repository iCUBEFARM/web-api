from icf_entity.models import Entity
from icf_career_fair.models import Speaker, SpeakerOptional, Support, SupportOptional

from rest_framework import status

from icf_career_fair.models import CareerFair, CareerFairDraft
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


class ICFCareerFairMixin(object):
    def get_career_fair(self, career_fair_slug):
        career_fair = None
        try:
            career_fair = CareerFair.objects.get(slug=career_fair_slug)
            return career_fair
        except CareerFair.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find career fair."), status_code=status.HTTP_400_BAD_REQUEST)


class ICFCareerFairDraftMixin(object):

    def get_draft_career_fair(self, career_fair_slug):
        career_fair = None
        try:
            career_fair = CareerFairDraft.objects.get(slug=career_fair_slug)
            return career_fair
        except CareerFairDraft.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find career fair draft."), status_code=status.HTTP_400_BAD_REQUEST)


class ICFSpeakerMixin(object):
    def get_speaker(self, speaker_slug):
        speaker = None
        try:
            speaker = Speaker.objects.get(slug=speaker_slug)
            return speaker
        except Speaker.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find Speaker"), status_code=status.HTTP_400_BAD_REQUEST)


class ICFSpeakerOptionalMixin(object):
    def get_speaker(self, speaker_slug):
        speaker = None
        try:
            speaker = SpeakerOptional.objects.get(slug=speaker_slug)
            return speaker
        except SpeakerOptional.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find SpeakerOptional"), status_code=status.HTTP_400_BAD_REQUEST)


class ICFSupportMixin(object):
    def get_support(self, support_slug):
        support = None
        try:
            support = Support.objects.get(slug=support_slug)
            return support
        except Support.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find Support"), status_code=status.HTTP_400_BAD_REQUEST)


class ICFSupportOptionalMixin(object):
    def get_support(self, support_slug):
        support = None
        try:
            support = SupportOptional.objects.get(slug=support_slug)
            return support
        except SupportOptional.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find SupportOptional"), status_code=status.HTTP_400_BAD_REQUEST)



# class ICFEntityPermissionMixin(ICFEntityMixin, object):
#
#     def has_permission(self, request, view):
#
#         user = request.user
#         if user.username == settings.ANONYMOUS_USER_NAME:
#             return False
#
#         entity_slug = view.kwargs.get('slug')
#         if not entity_slug:
#             entity_slug = view.kwargs.get('entity_slug')
#
#         if entity_slug:
#             entity = self.get_entity(entity_slug)
#             if request.method in SAFE_METHODS:
#                 return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
#             else:
#                 return any(perm in get_perms(request.user, entity) for perm in self.allowed_write_perms)
#         else:
#             return False
#
#     def has_object_permission(self, request, view, obj):
#
#         if request.method in SAFE_METHODS:
#             return any(perm in get_perms(request.user, obj) for perm in self.allowed_read_perms)
#         else:
#             return any(perm in get_perms(request.user, obj) for perm in self.allowed_write_perms)
#
