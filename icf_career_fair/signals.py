import itertools
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.text import slugify

from icf_career_fair.models import CareerFairDraft, CareerFair, Speaker, SpeakerOptional, Session, Support, \
    SupportOptional, SessionOptional, CareerFairAdvertisement, CareerFairAdvertisementViews
from icf_career_fair.permissions import ICFCareerFairsUserPermManager
from icf_entity import signals
from icf_item.models import Type
from icf_jobs.permissions import ICFJobsUserPermManager
from icf_jobs.models import Job, JobDraft, UserResume, CandidateSearch

import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

MAX_CAREER_FAIR_SLUG_LENGTH = 70
MAX_CAREER_FAIR_SESSION_LENGTH = 70
MAX_CAREER_FAIR_SUPPORT_LENGTH = 70
MAX_CAREER_FAIR_SPEAKER_LENGTH = 70


# MAX_CANDIDATE_SEARCH_SLUG_LENGTH = 70


def create_career_fair_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_CAREER_FAIR_SLUG_LENGTH]

        for x in itertools.count(1):
            if not CareerFair.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Career Fair {0}".format(instance.slug))


@receiver(pre_save, sender=CareerFair)
def career_fair_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair")
        instance_type = ContentType.objects.get_for_model(instance)
        item_type = Type.objects.get(content_type__id=instance_type.id)
        instance.item_type = item_type
        create_career_fair_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair"}, status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_draft_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_CAREER_FAIR_SLUG_LENGTH]

        for x in itertools.count(1):
            if not CareerFairDraft.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Draft Career Fair {0}".format(instance.slug))


@receiver(pre_save, sender=CareerFairDraft)
def career_fair_draft_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair")
        instance_type = ContentType.objects.get_for_model(CareerFair)
        item_type = Type.objects.get(content_type__id=instance_type.id)
        instance.item_type = item_type
        create_career_fair_draft_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair draft"},
                        status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_session_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_CAREER_FAIR_SESSION_LENGTH]

        for x in itertools.count(1):
            if not Session.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SESSION_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Session {0}".format(instance.slug))


@receiver(pre_save, sender=Session)
def career_fair_session_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair Speaker")
        instance_type = ContentType.objects.get_for_model(instance)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_career_fair_session_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair session"},
                        status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_session_optional_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_CAREER_FAIR_SESSION_LENGTH]

        for x in itertools.count(1):
            if not SessionOptional.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SESSION_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Session Optional {0}".format(instance.slug))


@receiver(pre_save, sender=SessionOptional)
def career_fair_session_optional_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair Session Optional")
        instance_type = ContentType.objects.get_for_model(instance)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_career_fair_session_optional_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair session optional"},
                        status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_support_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.brand_name)[:MAX_CAREER_FAIR_SUPPORT_LENGTH]

        for x in itertools.count(1):
            if not Support.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SUPPORT_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Support {0}".format(instance.slug))


@receiver(pre_save, sender=Support)
def career_fair_support_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair Speaker")
        instance_type = ContentType.objects.get_for_model(instance)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_career_fair_support_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair Support"},
                        status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_support_optional_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.brand_name)[:MAX_CAREER_FAIR_SUPPORT_LENGTH]

        for x in itertools.count(1):
            if not SupportOptional.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SUPPORT_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Support {0}".format(instance.slug))


@receiver(pre_save, sender=SupportOptional)
def career_fair_support_optional_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair Support Optional")
        instance_type = ContentType.objects.get_for_model(instance)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_career_fair_support_optional_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair Support Optional"},
                        status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_speaker_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.name)[:MAX_CAREER_FAIR_SPEAKER_LENGTH]

        for x in itertools.count(1):
            if not Speaker.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Speaker {0}".format(instance.slug))


@receiver(pre_save, sender=Speaker)
def career_fair_speaker_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair Speaker")
        instance_type = ContentType.objects.get_for_model(instance)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_career_fair_speaker_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair speaker"},
                        status=status.HTTP_400_BAD_REQUEST)


def create_career_fair_speaker_optional_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.name)[:MAX_CAREER_FAIR_SPEAKER_LENGTH]

        for x in itertools.count(1):
            if not SpeakerOptional.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CAREER_FAIR_SPEAKER_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for SpeakerOptional {0}".format(instance.slug))


@receiver(pre_save, sender=SpeakerOptional)
def career_fair_speaker_optional_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the career fair Speaker")
        instance_type = ContentType.objects.get_for_model(instance)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_career_fair_speaker_optional_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save career fair speaker Optional"},
                        status=status.HTTP_400_BAD_REQUEST)


# def create_user_resume_slug(instance):
#
#     if not instance.slug:
#         instance.slug = orig = slugify(instance.job_profile.user.username+"_resume")[:MAX_JOB_SLUG_LENGTH]
#
#         for x in itertools.count(1):
#             if not UserResume.objects.filter(slug=instance.slug).exists():
#                 break
#
#             # Truncate the original slug dynamically. Minus 1 for the hyphen.
#             instance.slug = "%s-%d" % (orig[:MAX_JOB_SLUG_LENGTH - len(str(x)) - 1], x)
#             logger.info("Created slug for User resume {0}".format(instance.slug))
#
#
# def create_candidate_search_slug(instance):
#     if not instance.slug:
#         instance.slug = orig = slugify(instance.name)[:MAX_CANDIDATE_SEARCH_SLUG_LENGTH]
#
#         for x in itertools.count(1):
#             if not CandidateSearch.objects.filter(slug=instance.slug).exists():
#                 break
#
#             # Truncate the original slug dynamically. Minus 1 for the hyphen.
#             instance.slug = "%s-%d" % (orig[:MAX_CANDIDATE_SEARCH_SLUG_LENGTH - len(str(x)) - 1], x)
#             logger.info("Created slug for Candidate Search {0}".format(instance.slug))
#
#
# @receiver(pre_save, sender=UserResume)
# def user_resume_pre_save_receiver(sender, instance, *args, **kwargs):
#     try:
#         logger.info("Set item type before saving the user resume")
#         # instance_type = ContentType.objects.get_for_model(Job)
#         # item_type = Type.objects.get(content_type__id=instance_type.id)
#         # instance.item_type = item_type
#         create_user_resume_slug(instance)
#     except ObjectDoesNotExist:
#         return Response({"detail": "object not found while pre_save user resume"}, status=status.HTTP_400_BAD_REQUEST)
#
#
# @receiver(pre_save, sender=CandidateSearch)
# def candidate_search_pre_save_receiver(sender, instance, *args, **kwargs):
#     try:
#         logger.info("Set slug  before saving the candidate search")
#         # instance_type = ContentType.objects.get_for_model(Job)
#         # item_type = Type.objects.get(content_type__id=instance_type.id)
#         # instance.item_type = item_type
#         create_candidate_search_slug(instance)
#     except ObjectDoesNotExist:
#         return Response({"detail": "object not found while pre_save user resume"}, status=status.HTTP_400_BAD_REQUEST)

@receiver(post_save, sender=CareerFairAdvertisement)
def career_fair_advertisement_create_views_receiver(sender, instance, created, *args, **kwargs):
    if created:
        logger.info("Creating an Advertisement view record")
        CareerFairAdvertisementViews.objects.create(career_fair_advertisement=instance,
                                                    ad_image_type=instance.ad_image_type, number_of_views=0)


signals.entity_add_permission.connect(ICFCareerFairsUserPermManager.add_user_perm)

signals.entity_remove_permission.connect(ICFCareerFairsUserPermManager.remove_user_perm)
