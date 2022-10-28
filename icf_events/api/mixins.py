from icf_entity.models import Entity
from rest_framework import status

from icf_events.models import Event, EventDraft
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


class ICFEventMixin(object):
    def get_event(self, event_slug):
        event = None
        try:
            event = Event.objects.get(slug=event_slug)
            return event
        except Event.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find event."), status_code=status.HTTP_400_BAD_REQUEST)


class ICFEventDraftMixin(object):

    def get_draft_event(self, event_slug):
        event = None
        try:
            event = EventDraft.objects.get(slug=event_slug)
            return event
        except EventDraft.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Unable to find event draft."), status_code=status.HTTP_400_BAD_REQUEST)