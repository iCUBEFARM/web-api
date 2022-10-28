#
# The below method is a signal receiver for pre_save called just before the Entity model is saved
#
import itertools

from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from guardian.shortcuts import assign_perm

from icf_entity.models import Entity

import logging

from icf_generic.models import Sponsored, FeaturedEvent, FAQ, FAQCategory

logger = logging.getLogger(__name__)


"""
Create a unique slug for the Entity
"""
MAX_SLUG_LENGTH = 60
FAQ_MAX_SLUG_LENGTH = 200


def create_faq_category_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.name)[:MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not FAQCategory.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for FAQCategory {0}".format(instance.slug))


def create_faq_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.question)[:FAQ_MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not FAQ.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:FAQ_MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for FAQ {0}".format(instance.slug))


def create_featured_event_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not FeaturedEvent.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for FeaturedEvent {0}".format(instance.slug))


@receiver(pre_save, sender=FeaturedEvent)
def featured_event_pre_save_receiver(sender, instance, *args, **kwargs):
    logger.info("Pre save receiver to create slug  for FeaturedEvent.")
    create_featured_event_slug(instance)


@receiver(pre_save, sender=FAQ)
def faq_pre_save_receiver(sender, instance, *args, **kwargs):
    logger.info("Pre save receiver to create slug  for faq.")
    create_faq_slug(instance)


@receiver(pre_save, sender=FAQCategory)
def faq_category_pre_save_receiver(sender, instance, *args, **kwargs):
    logger.info("Pre save receiver to create slug  for FAQCategory.")
    create_faq_category_slug(instance)


# pre_save.connect(sponsored_pre_save_receiver,Sponsored)
pre_save.connect(featured_event_pre_save_receiver, FeaturedEvent)
pre_save.connect(faq_pre_save_receiver, FAQ)
pre_save.connect(faq_category_pre_save_receiver, FAQCategory)



