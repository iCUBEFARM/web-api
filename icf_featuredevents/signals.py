import itertools

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.utils.text import slugify

from icf_featuredevents.models import FeaturedEvent

import logging


logger = logging.getLogger(__name__)



"""
Create a unique slug for the FeaturedEvent
"""
MAX_SLUG_LENGTH = 60


def create_featured_event_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not FeaturedEvent.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for FeaturedEvent {0}".format(instance.slug))


# def create_featured_event_category_slug(instance):
#     if not instance.slug:
#         instance.slug = orig = slugify(instance.name)[:MAX_SLUG_LENGTH]
#
#         for x in itertools.count(1):
#             if not FeaturedEvent.objects.filter(slug=instance.slug).exists():
#                 break
#
#             # Truncate the original slug dynamically. Minus 1 for the hyphen.
#             instance.slug = "%s-%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
#             logger.info("Created slug for FeaturedEventCategory {0}".format(instance.slug))


@receiver(pre_save, sender=FeaturedEvent)
def featured_event_pre_save_receiver(sender, instance, *args, **kwargs):
    logger.info("Pre save receiver to create slug called")
    create_featured_event_slug(instance)


# @receiver(pre_save, sender=FeaturedEvent)
# def featured_event_category_pre_save_receiver(sender, instance, *args, **kwargs):
#     logger.info("Pre save receiver to create slug called")
#     create_featured_event_category_slug(instance)


pre_save.connect(featured_event_pre_save_receiver, FeaturedEvent)
# pre_save.connect(featured_event_category_pre_save_receiver, FeaturedEventCategory)
