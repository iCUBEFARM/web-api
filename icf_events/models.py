from datetime import datetime, timezone

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models

# Create your models here.
from icf_auth.models import User
from icf_entity.models import Logo, EntityPerms, Entity
from icf_events.CreateThumbnailHelper import CreateThumbnail
from icf_events.app_settings import EVENT_GALLERY_IMAGE_THUMBNAIL_SIZE
from icf_generic.api.serializers import SponsoredListSerializer
from icf_generic.models import Sponsored
from icf_item.models import Item, ItemDraft
from django.utils.translation import ugettext_lazy as _
import logging
import os

logger = logging.getLogger(__name__)


def get_events_directory(instance):
    event_image_dir = "events/{dir_1}/images".format(dir_1=instance.event_slug)
    return event_image_dir


def get_event_drafts_directory(instance):
    event_draft_image_dir = "events/drafts/{dir_1}/images".format(dir_1=instance.slug)
    return event_draft_image_dir


def upload_event_media_location(instance, filename):
    try:
        event_directory = get_events_directory(instance)
        return "{dir}/{file}{ext}".format(dir=event_directory, file=instance.event_slug, ext=os.path.splitext(filename)[1])
    except:
        entity_directory = get_events_directory(instance)
        return "{dir}/{file}".format(dir=entity_directory, file=instance.event_slug)


def upload_event_draft_media_location(instance, filename):
    try:
        event_draft_directory = get_event_drafts_directory(instance)
        return "{dir}/{file}{ext}".format(dir=event_draft_directory, file=instance.slug, ext=os.path.splitext(filename)[1])
    except:
        event_draft_directory = get_event_drafts_directory(instance)
        return "{dir}/{file}".format(dir=event_draft_directory, file=instance.event_slug)


class EventPerms():
    EVENT_CREATE = 'icf_evt_cr'
    EVENT_PUBLISH = 'icf_evt_pub'
    EVENT_ADMIN = 'icf_evt_adm'

    EVENT_PERM_CHOICES = (("EVENT_CREATE", EVENT_CREATE),
                         ("EVENT_PUBLISH", EVENT_PUBLISH),
                         ("EVENT_ADMIN", EVENT_ADMIN), )

    @classmethod
    def get_event_perms(cls):
        return dict(cls.EVENT_PERM_CHOICES)

    @classmethod
    def get_admin_perm(cls):
        return cls.EVENT_ADMIN

    @classmethod
    def get_entity_group(cls, entity, perm):
        return EntityPerms.get_entity_group(entity, perm)


class Event(Item):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. "
                                         "Up to 15 digits allowed.")

    registration_website = models.URLField(blank=True, null=True)
    contact_email = models.EmailField()
    contact_no = models.CharField(validators=[PHONE_REGEX], max_length=17, blank=True)  # validators should be a list
    daily_start_time = models.CharField(max_length=16, blank=False, null=False)
    daily_end_time = models.CharField(max_length=16, blank=False, null=False)
    sponsored = GenericRelation(Sponsored, related_query_name="events")

    class Meta:
        verbose_name_plural = 'Events'
        ordering = ['-created', ]

    def get_sponsored_info(self):
        if self.status == Event.ITEM_ACTIVE and self.expiry >= datetime.now(timezone.utc):
            serializer = SponsoredListSerializer()
            serializer.title = self.title
            serializer.description = self.entity.description
            serializer.entity_name = self.entity.name
            serializer.location = self.location
            serializer.slug = self.slug
            serializer.content_type = self.__class__.__name__
            # right now published date is created date itself
            # (published date field is not present in Event model)
            serializer.published_date = self.created
            serializer.expiry_date = self.expiry
            serializer.logo = self.get_entity_logo()
            return serializer
        else:
            return None

    def get_entity_logo(self):
        try:
            return Logo.objects.get(entity=self.entity).image.url
        except ObjectDoesNotExist:
            return ""


class EventGallery(models.Model):
    HERO = 1
    GALLERY = 2

    IMAGE_TYPE_CHOICES = (
        (HERO, _('Hero')), (GALLERY, _('Gallery')))

    event = models.ForeignKey(Event, models.CASCADE)
    entity = models.ForeignKey(Entity, models.CASCADE)
    event_slug = models.CharField(max_length=150)
    image = models.ImageField(upload_to=upload_event_media_location)
    image_type = models.SmallIntegerField(choices=IMAGE_TYPE_CHOICES, default=GALLERY)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    # def save(self, *args, **kwargs):
    #     # save for image
    #     # super(EventGallery, self).save(*args, **kwargs)
    #
    #     CreateThumbnail().make_thumbnail(self.image, self.image, EVENT_GALLERY_IMAGE_THUMBNAIL_SIZE, 'image')
    #
    #     # save for thumbnail and icon
    #     super(EventGallery, self).save(*args, **kwargs)

    def __str__(self):
        return self.event.title

    @classmethod
    def get_image_types(cls):
        return dict(cls.IMAGE_TYPE_CHOICES)


class EventMarkedForDelete(models.Model):
    NEW = 1
    DELETED = 2
    REJECTED = 3

    APPROVAL_STATUS_CHOICES = (
        (NEW, _('New')), (DELETED, _('Deleted')), (REJECTED, _('Rejected')))

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='marked_delete')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    approval_status = models.SmallIntegerField(choices=APPROVAL_STATUS_CHOICES, default=NEW)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{} : {}".format(self.user.username, self.event.slug)

    @classmethod
    def get_event_marked_for_delete_approval_statuses(cls):
        return dict(cls.APPROVAL_STATUS_CHOICES)


class EventDraft(ItemDraft):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'."
                                         " Up to 15 digits allowed.")

    registration_website = models.URLField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_no = models.CharField(validators=[PHONE_REGEX], max_length=17, blank=True, null=True)  # validators should be a list
    daily_start_time = models.CharField(max_length=16, blank=True, null=True)
    daily_end_time = models.CharField(max_length=16, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'EventDrafts'
        ordering = ['-created', ]

    def get_entity_logo(self):
        try:
            return Logo.objects.get(entity=self.entity).image.url
        except ObjectDoesNotExist:
            return ""


class EventGalleryOptional(models.Model):
    HERO = 1
    GALLERY = 2

    IMAGE_TYPE_CHOICES = (
        (HERO, _('Hero')), (GALLERY, _('Gallery')))

    event = models.ForeignKey(EventDraft, models.CASCADE)
    entity = models.ForeignKey(Entity, models.CASCADE)
    event_slug = models.CharField(max_length=150)
    image = models.ImageField(upload_to=upload_event_media_location)
    image_type = models.SmallIntegerField(choices=IMAGE_TYPE_CHOICES, default=GALLERY)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    # def save(self, *args, **kwargs):
    #     # save for image
    #     # super(EventGalleryOptional, self).save(*args, **kwargs)
    #
    #     CreateThumbnail().make_thumbnail(self.image, self.image, EVENT_GALLERY_IMAGE_THUMBNAIL_SIZE, 'image')
    #
    #     # save for thumbnail and icon
    #     super(EventGalleryOptional, self).save(*args, **kwargs)

    def __str__(self):
        return self.event.title

    @classmethod
    def get_image_types(cls):
        return dict(cls.IMAGE_TYPE_CHOICES)



class ParticipantSearch(models.Model):
    name = models.CharField(_("name"), max_length=200, blank=False, null=False)
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE)
    entity_slug = models.CharField(max_length=500,  null=False, blank=False)
    location = models.CharField(max_length=500, null=True, blank=True)
    work_experience = models.PositiveIntegerField(null=True, blank=True)
    education_level = models.CharField(max_length=500, null=True, blank=True)
    key_skill = models.CharField(max_length=500, null=True, blank=True)
    computer_skill = models.CharField(max_length=500, null=True, blank=True)
    language_skill = models.CharField(max_length=500, null=True, blank=True)
    job_title = models.CharField(max_length=500, null=True, blank=True)
    slug = models.SlugField(blank=True, max_length=200)
    functional_area = models.CharField(max_length=500, null=True, blank=True)
    industries = models.CharField(max_length=500, null=True, blank=True)
    job_level = models.CharField(max_length=500, null=True, blank=True)
    worksite_type = models.CharField(max_length=500, null=True, blank=True)
    salary = models.CharField(max_length=500, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.name
