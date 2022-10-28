import itertools
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from icf_entity import signals
from icf_events.models import Event, EventDraft
from icf_events.permissions import ICFEventsUserPermManager
from icf_item.models import Type

import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


MAX_EVENT_SLUG_LENGTH = 70


def create_event_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_EVENT_SLUG_LENGTH]

        for x in itertools.count(1):
            if not Event.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_EVENT_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Event {0}".format(instance.slug))


def create_event_draft_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_EVENT_SLUG_LENGTH]

        for x in itertools.count(1):
            if not EventDraft.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_EVENT_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for EventDraft {0}".format(instance.slug))


@receiver(pre_save, sender=EventDraft)
def event_draft_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the event draft")
        instance_type = ContentType.objects.get_for_model(Event)
        item_type = Type.objects.get(content_type__id=instance_type.id)
        instance.item_type = item_type
        create_event_draft_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save eventdraft"}, status=status.HTTP_400_BAD_REQUEST)


@receiver(pre_save, sender=Event)
def event_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the event")
        instance_type = ContentType.objects.get_for_model(instance)
        item_type = Type.objects.get(content_type__id=instance_type.id)
        instance.item_type = item_type
        create_event_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save event"}, status=status.HTTP_400_BAD_REQUEST)


signals.entity_add_permission.connect(ICFEventsUserPermManager.add_user_perm)

signals.entity_remove_permission.connect(ICFEventsUserPermManager.remove_user_perm)
