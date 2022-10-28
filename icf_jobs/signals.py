import itertools
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from icf_entity import signals
from icf_item.models import Type
from icf_jobs.permissions import ICFJobsUserPermManager
from icf_jobs.models import Job, JobDraft, UserResume, CandidateSearch

import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


MAX_JOB_SLUG_LENGTH = 70
MAX_CANDIDATE_SEARCH_SLUG_LENGTH = 70


def create_job_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_JOB_SLUG_LENGTH]

        for x in itertools.count(1):
            if not Job.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_JOB_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Job {0}".format(instance.slug))


@receiver(pre_save, sender=Job)
def job_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the job")
        instance_type = ContentType.objects.get_for_model(instance)
        item_type = Type.objects.get(content_type__id=instance_type.id)
        instance.item_type = item_type
        create_job_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save job"}, status=status.HTTP_400_BAD_REQUEST)


def create_job_draft_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.title)[:MAX_JOB_SLUG_LENGTH]

        for x in itertools.count(1):
            if not JobDraft.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_JOB_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Draft Job {0}".format(instance.slug))


@receiver(pre_save, sender=JobDraft)
def job_draft_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the job")
        instance_type = ContentType.objects.get_for_model(Job)
        item_type = Type.objects.get(content_type__id=instance_type.id)
        instance.item_type = item_type
        create_job_draft_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save jobdraft"}, status=status.HTTP_400_BAD_REQUEST)


def create_user_resume_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.job_profile.user.username+"_resume")[:MAX_JOB_SLUG_LENGTH]

        for x in itertools.count(1):
            if not UserResume.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_JOB_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for User resume {0}".format(instance.slug))


def create_candidate_search_slug(instance):
    if not instance.slug:
        instance.slug = orig = slugify(instance.name)[:MAX_CANDIDATE_SEARCH_SLUG_LENGTH]

        for x in itertools.count(1):
            if not CandidateSearch.objects.filter(slug=instance.slug).exists():
                break

            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_CANDIDATE_SEARCH_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Candidate Search {0}".format(instance.slug))


@receiver(pre_save, sender=UserResume)
def user_resume_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set item type before saving the user resume")
        # instance_type = ContentType.objects.get_for_model(Job)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_user_resume_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save user resume"}, status=status.HTTP_400_BAD_REQUEST)


@receiver(pre_save, sender=CandidateSearch)
def candidate_search_pre_save_receiver(sender, instance, *args, **kwargs):
    try:
        logger.info("Set slug  before saving the candidate search")
        # instance_type = ContentType.objects.get_for_model(Job)
        # item_type = Type.objects.get(content_type__id=instance_type.id)
        # instance.item_type = item_type
        create_candidate_search_slug(instance)
    except ObjectDoesNotExist:
        return Response({"detail": "object not found while pre_save user resume"}, status=status.HTTP_400_BAD_REQUEST)


signals.entity_add_permission.connect(ICFJobsUserPermManager.add_user_perm)

signals.entity_remove_permission.connect(ICFJobsUserPermManager.remove_user_perm)