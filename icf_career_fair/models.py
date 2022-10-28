import logging
import os
from datetime import datetime, timezone
from enum import Enum

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models

# Create your models here.

from icf_auth.models import User
from icf_entity.models import Entity, Logo, EntityPerms
from icf_generic.api.serializers import SponsoredListSerializer
from icf_generic.models import Sponsored, Address, Category, Currency
from icf_item.models import Item, ItemDraft
from django.utils.translation import ugettext_lazy as _

from icf_orders.models import Product, ProductDraft

logger = logging.getLogger(__name__)


def get_career_fair_directory(instance):
    career_fair_image_dir = "career_fair/{dir_1}/images".format(dir_1=instance.career_fair.slug)
    return career_fair_image_dir


def get_career_fair_drafts_directory(instance):
    career_fair_draft_image_dir = "career_fair/drafts/{dir_1}/images".format(dir_1=instance.career_fair_slug)
    return career_fair_draft_image_dir


def upload_career_fair_media_location(instance, filename):
    try:
        career_fair_directory = get_career_fair_directory(instance)
        return "{dir}/{file}{ext}".format(dir=career_fair_directory, file=instance.career_fair.slug, ext=
        os.path.splitext(filename)[1])
    except:
        career_fair_directory = get_career_fair_directory(instance)
        return "{dir}/{file}".format(dir=career_fair_directory, file=instance.career_fair_slug)


def upload_career_fair_draft_media_location(instance, filename):
    try:
        career_fair_draft_directory = get_career_fair_drafts_directory(instance)
        return "{dir}/{file}{ext}".format(dir=career_fair_draft_directory, file=instance.career_fair_slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        career_fair_draft_directory = get_career_fair_drafts_directory(instance)
        return "{dir}/{file}".format(dir=career_fair_draft_directory, file=instance.career_fair_slug)


SPEAKER_PROFILE_IMAGE_DIR = "speaker_profile/images"


def upload_speaker_profile_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=SPEAKER_PROFILE_IMAGE_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=SPEAKER_PROFILE_IMAGE_DIR, file=filename)


CAREER_FAIR_SPEAKER_PROFILE_IMAGE_DIR = "CareerFairSpeakerProfile/images"


def upload_career_fair_speaker_profile_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=CAREER_FAIR_SPEAKER_PROFILE_IMAGE_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=CAREER_FAIR_SPEAKER_PROFILE_IMAGE_DIR, file=filename)


CAREER_FAIR_SPEAKER_DRAFT_PROFILE_IMAGE_DIR = "CareerFairSpeakerDraftProfile/images"


def upload_career_fair_speaker_draft_profile_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=CAREER_FAIR_SPEAKER_DRAFT_PROFILE_IMAGE_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=CAREER_FAIR_SPEAKER_DRAFT_PROFILE_IMAGE_DIR, file=filename)


SPEAKER_OPTIONAL_PROFILE_IMAGE_DIR = "speaker_optional_profile/images"


def upload_speaker_optional_profile_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=SPEAKER_OPTIONAL_PROFILE_IMAGE_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=SPEAKER_OPTIONAL_PROFILE_IMAGE_DIR, file=filename)


SUPPORT_LOGO_DIR = "support/logos"


def upload_career_fair_image_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=SUPPORT_LOGO_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=SUPPORT_LOGO_DIR, file=filename)


SUPPORT_OPTIONAL_LOGO_DIR = "supportOptional/logos"

def upload_support_logo_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=SUPPORT_LOGO_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=SUPPORT_LOGO_DIR, file=filename)


def upload_support_optional_logo_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=SUPPORT_OPTIONAL_LOGO_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=SUPPORT_OPTIONAL_LOGO_DIR, file=filename)


CAREER_FAIR_SUPPORT_OPTIONAL_LOGO_DIR = "CareerFairSupportDraft/logos"


def upload_career_fair_support_optional_logo_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=CAREER_FAIR_SUPPORT_OPTIONAL_LOGO_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=CAREER_FAIR_SUPPORT_OPTIONAL_LOGO_DIR, file=filename)


CAREER_FAIR_SUPPORT_LOGO_DIR = "CareerFairSupport/logos"


def upload_career_fair_support_logo_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=CAREER_FAIR_SUPPORT_LOGO_DIR, file=instance.slug,
                                          ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=CAREER_FAIR_SUPPORT_LOGO_DIR, file=filename)


class CareerFairPerms():
    CAREER_FAIR_CREATE = 'icf_cf_cr'
    CAREER_FAIR_PUBLISH = 'icf_cf_pub'
    CAREER_FAIR_ADMIN = 'icf_cf_adm'

    CAREER_FAIR_PERM_CHOICES = (("CAREER_FAIR_CREATE", CAREER_FAIR_CREATE),
                         ("CAREER_FAIR_PUBLISH", CAREER_FAIR_PUBLISH),
                         ("CAREER_FAIR_ADMIN", CAREER_FAIR_ADMIN), )

    @classmethod
    def get_career_fair_perms(cls):
        return dict(cls.CAREER_FAIR_PERM_CHOICES)

    @classmethod
    def get_admin_perm(cls):
        return cls.CAREER_FAIR_ADMIN

    @classmethod
    def get_entity_group(cls, entity, perm):
        return EntityPerms.get_entity_group(entity, perm)


class ModeOfCareerFair:
    PRESENTIAL = 1
    VIRTUAL_CAREER_FAIR = 2
    HYBRID_CAREER_FAIR = 3

    CAREER_MODE_CHOICES = (
        (PRESENTIAL, "PRESENTIAL"), (VIRTUAL_CAREER_FAIR, "VIRTUAL_CAREER_FAIR"),
        (HYBRID_CAREER_FAIR, "HYBRID_CAREER_FAIR"))


class CareerFair(Item):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. "
                                         "Up to 15 digits allowed.")

    sponsored = GenericRelation(Sponsored, related_query_name="career_fairs")
    organiser_contact_email = models.EmailField(blank=True, null=True)
    organiser_contact_phone = models.CharField(validators=[PHONE_REGEX], max_length=17,
                                               blank=True)  # validators should be a list
    # mode_of_cf = models.CharField(max_length=2, choices=ModeOfCareerFair.CAREER_MODE_CHOICES)  # Choices is a list of Tuple
    mode_of_cf = models.SmallIntegerField(choices=ModeOfCareerFair.CAREER_MODE_CHOICES,
                                          default=ModeOfCareerFair.PRESENTIAL)

    start_time = models.CharField(max_length=50, blank=True, null=True)
    end_time = models.CharField(max_length=50, blank=True, null=True)
    timezone = models.CharField(max_length=50,default='nill')

    class Meta:
        verbose_name_plural = 'Career Fairs'
        ordering = ['-created', ]

    def get_sponsored_info(self):
        if self.status == CareerFair.ITEM_ACTIVE and self.expiry >= datetime.now(timezone.utc):
            serializer = SponsoredListSerializer()
            serializer.title = self.title
            serializer.description = self.entity.description
            serializer.entity_name = self.entity.name
            serializer.location = self.location
            serializer.slug = self.slug
            serializer.content_type = self.__class__.__name__
            # right now published date is created date itself
            # (published date field  is not present in Job model)
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


class CareerFairGallery(models.Model):
    HERO = 1
    GALLERY = 2

    IMAGE_TYPE_CHOICES = (
        (HERO, _('Hero')), (GALLERY, _('Gallery')))

    career_fair = models.ForeignKey(CareerFair, models.CASCADE)
    entity = models.ForeignKey(Entity, models.CASCADE)
    career_fair_slug = models.CharField(max_length=150)
    image = models.ImageField(upload_to=upload_career_fair_media_location)
    image_type = models.SmallIntegerField(choices=IMAGE_TYPE_CHOICES, default=GALLERY)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.career_fair.title

    @classmethod
    def get_image_types(cls):
        return dict(cls.IMAGE_TYPE_CHOICES)


class CareerFairMarkedForDelete(models.Model):
    NEW = 1
    DELETED = 2
    REJECTED = 3

    APPROVAL_STATUS_CHOICES = (
        (NEW, _('New')), (DELETED, _('Deleted')), (REJECTED, _('Rejected')))

    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE, related_name='marked_delete')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    approval_status = models.SmallIntegerField(choices=APPROVAL_STATUS_CHOICES, default=NEW)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{} : {}".format(self.user.username, self.career_fair.slug)

    @classmethod
    def get_career_fair_marked_for_delete_approval_statuses(cls):
        return dict(cls.APPROVAL_STATUS_CHOICES)


class CareerFairDraft(ItemDraft):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. "
                                         "Up to 15 digits allowed.")

    organiser_contact_email = models.EmailField(blank=True, null=True)
    organiser_contact_phone = models.CharField(validators=[PHONE_REGEX], max_length=17,
                                               blank=True, null=True)  # validators should be a list
    mode_of_cf = models.SmallIntegerField(choices=ModeOfCareerFair.CAREER_MODE_CHOICES,
                                          default=ModeOfCareerFair.PRESENTIAL, blank=True, null=True)
    start_time = models.CharField(max_length=50, blank=True, null=True)
    end_time = models.CharField(max_length=50, blank=True, null=True)
    timezone = models.CharField(max_length=50, default='nill')

    class Meta:
        verbose_name_plural = 'Career Fair Drafts'
        ordering = ['-created', ]

    def get_entity_logo(self):
        try:
            return Logo.objects.get(entity=self.entity).image.url
        except ObjectDoesNotExist:
            return ""


class CareerFairImagesOptional(models.Model):
    career_fair = models.ForeignKey(CareerFairDraft, models.CASCADE)
    image = models.ImageField(upload_to=upload_career_fair_media_location, width_field="width",
                             height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.image.url


class CareerFairImages(models.Model):
    career_fair = models.ForeignKey(CareerFair, models.CASCADE)
    image = models.ImageField(upload_to=upload_career_fair_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.image.url


class CareerFairGalleryOptional(models.Model):
    HERO = 1
    GALLERY = 2

    IMAGE_TYPE_CHOICES = (
        (HERO, _('Hero')), (GALLERY, _('Gallery')))

    career_fair = models.ForeignKey(CareerFairDraft, models.CASCADE)
    entity = models.ForeignKey(Entity, models.CASCADE)
    career_fair_slug = models.CharField(max_length=150)
    image = models.ImageField(upload_to=upload_career_fair_media_location)
    image_type = models.SmallIntegerField(choices=IMAGE_TYPE_CHOICES, default=GALLERY)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.career_fair.title

    @classmethod
    def get_image_types(cls):
        return dict(cls.IMAGE_TYPE_CHOICES)


class SessionOptional(models.Model):
    career_fair = models.ForeignKey(CareerFairDraft, on_delete=models.CASCADE,
                                    related_name='career_fair_optional_sessions')
    title = models.CharField(_("title"), max_length=80, blank=False, null=False)
    description = models.TextField(_("description"), blank=False, null=False)
    # expiry = models.DateTimeField()
    start_date = models.DateTimeField()
    start_date_string = models.CharField(max_length=50, blank=True, null=True)
    start_time = models.CharField(max_length=50, blank=False, null=False)
    end_time = models.CharField(max_length=50, blank=False, null=False)
    session_link = models.URLField(blank=True)
    slug = models.SlugField(blank=True, unique=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.slug)

    class Meta:
        verbose_name_plural = 'Draft Sessions'
        ordering = ['-created', ]


class SupportOptional(models.Model):
    # PARTNER = 1
    # SPONSOR = 2
    # GOLD_SPONSOR = 3
    # MAIN_PARTNER = 4
    #
    # SUPPORT_TYPE_CHOICES = (
    #     (PARTNER, _('Partner')), (SPONSOR, _('Sponsor')), (GOLD_SPONSOR, _('Gold Sponsor')),
    #     (MAIN_PARTNER, _('Main Partner')))

    career_fair = models.ForeignKey(CareerFairDraft, on_delete=models.CASCADE,
                                    related_name='career_fair_optional_supports')
    brand_name = models.CharField(_("brand_name"), max_length=80, blank=False, null=False)
    # support_type = models.SmallIntegerField(choices=SUPPORT_TYPE_CHOICES, default=PARTNER)
    support_type = models.CharField(_("support_type"), max_length=80, blank=False, null=False)
    image_url = models.CharField(_("image"), max_length=300, blank=True, null=True)
    slug = models.SlugField(blank=True, unique=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.slug)

    class Meta:
        verbose_name_plural = 'Draft Supports'
        ordering = ['-created', ]

    # @classmethod
    # def get_support_types(cls):
    #     return dict(cls.SUPPORT_TYPE_CHOICES)


class SupportLogoOptional(models.Model):
    support = models.OneToOneField(SupportOptional, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to=upload_support_optional_logo_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


class SpeakerOptional(models.Model):
    # SPEAKER = 1
    # KEYNOTE_SPEAKER = 2
    # PANELIST = 3
    # HOST = 4
    # PRESENTER = 5

    # SPEAKER_TYPE_CHOICES = (
    #     (SPEAKER, _('Speaker')), (KEYNOTE_SPEAKER, _('Keynote_speaker')), (PANELIST, _('Panelist')),
    #     (HOST, _('Host')), (PRESENTER, _('Presenter')))

    career_fair = models.ForeignKey(CareerFairDraft, on_delete=models.CASCADE,
                                    related_name='career_fair_optional_speakers')
    name = models.CharField(_("name"), max_length=80, blank=False, null=False)
    entity_name = models.CharField(_("entity_name"), max_length=80, blank=False, null=False)
    position = models.CharField(_("position"), max_length=80, blank=False, null=False)
    # speaker_type = models.SmallIntegerField(choices=SPEAKER_TYPE_CHOICES, default=SPEAKER)
    speaker_email = models.EmailField(null=True, blank=True)
    slug = models.SlugField(blank=True, unique=True)
    image_url = models.CharField(_("image"), max_length=300, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Draft Speakers'
        ordering = ['-created', ]

    # @classmethod
    # def get_speaker_types(cls):
    #     return dict(cls.SPEAKER_TYPE_CHOICES)


class SpeakerProfileImageOptional(models.Model):
    speaker = models.OneToOneField(SpeakerOptional, on_delete=models.CASCADE)
    image_url = models.ImageField(upload_to=upload_speaker_optional_profile_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.image.url


class SpeakerAndSessionOptional(models.Model):
    speaker = models.ForeignKey(SpeakerOptional, on_delete=models.CASCADE, related_name='session_speakers_optional')
    # speaker = models.ForeignKey(SpeakerOptional, on_delete=models.CASCADE)
    session = models.ForeignKey(SessionOptional, on_delete=models.CASCADE, related_name='speaker_sessions_optional')
    # session = models.ForeignKey(SessionOptional, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.speaker.name


class CareerFairProductSubType:
    TICKET = 1
    ITEM_FOR_SALE = 2
    ADVERTISEMENT = 3
    OTHER = 4

    CAREER_FAIR_PRODUCT_SUB_TYPE_CHOICES = (
        (TICKET, "Ticket"), (ITEM_FOR_SALE, "Item For Sale"), (ADVERTISEMENT, "Advertisement"), (OTHER, "Other"))

    @classmethod
    def get_career_fair_product_sub_types(cls):
        return dict(cls.CAREER_FAIR_PRODUCT_SUB_TYPE_CHOICES)


class Session(models.Model):
    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE, related_name='career_fair_sessions')
    title = models.CharField(_("title"), max_length=80, blank=False, null=False)
    description = models.TextField(_("description"), blank=False, null=False)
    # expiry = models.DateTimeField()
    start_date = models.DateTimeField()
    start_date_string=models.CharField(max_length=50, blank=True, null=True)
    start_time = models.CharField(max_length=50, blank=False, null=False)
    end_time = models.CharField(max_length=50, blank=False, null=False)
    session_link = models.URLField(blank=True)
    slug = models.SlugField(blank=True, unique=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.title)

    class Meta:
        verbose_name_plural = 'Sessions'
        ordering = ['start_date', ]


class Support(models.Model):
    # PARTNER = 1
    # SPONSOR = 2
    # GOLD_SPONSOR = 3
    # MAIN_PARTNER = 4
    # PLATINUM_SPONSOR = 5
    #
    # SUPPORT_TYPE_CHOICES = (
    #     (PARTNER, _('Partner')), (SPONSOR, _('Sponsor')), (GOLD_SPONSOR, _('Gold Sponsor')),
    #     (MAIN_PARTNER, _('Main Partner')), (PLATINUM_SPONSOR, _('Platinum Sponsor')))

    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE, related_name='career_fair_supports')
    brand_name = models.CharField(_("brand_name"), max_length=80, blank=False, null=False)
    # support_type = models.SmallIntegerField(choices=SUPPORT_TYPE_CHOICES, default=PARTNER)
    support_type = models.CharField(_("support_type"), max_length=80, blank=False, null=False)
    slug = models.SlugField(blank=True, unique=True)
    image_url = models.CharField(_("image"), max_length=300, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.brand_name)

    class Meta:
        verbose_name_plural = 'Supports'
        ordering = ['-created', ]

    # @classmethod
    # def get_support_types(cls):
    #     return dict(cls.SUPPORT_TYPE_CHOICES)


class SupportLogo(models.Model):
    support = models.OneToOneField(Support, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to=upload_career_fair_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.logo.url


class Speaker(models.Model):
    # SPEAKER = 1
    # KEYNOTE_SPEAKER = 2
    # PANELIST = 3
    # HOST = 4
    # PRESENTER = 5
    #
    # SPEAKER_TYPE_CHOICES = (
    #     (SPEAKER, _('Speaker')), (KEYNOTE_SPEAKER, _('Keynote_speaker')), (PANELIST, _('Panelist')),
    #     (HOST, _('Host')), (PRESENTER, _('Presenter')))

    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE, related_name='career_fair_speakers')
    name = models.CharField(_("name"), max_length=80, blank=False, null=False)
    entity_name = models.CharField(_("entity_name"), max_length=80, blank=False, null=False)
    position = models.CharField(_("position"), max_length=80, blank=False, null=False)
    # speaker_type = models.SmallIntegerField(choices=SPEAKER_TYPE_CHOICES, default=SPEAKER)
    speaker_email = models.EmailField(null=True, blank=True)
    slug = models.SlugField(blank=True, unique=True)
    image_url = models.CharField(_("image"), max_length=300, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Speakers'
        ordering = ['-created', ]

    # @classmethod
    # def get_speaker_types(cls):
    #     return dict(cls.SPEAKER_TYPE_CHOICES)


class SpeakerProfileImage(models.Model):
    speaker = models.OneToOneField(Speaker, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=upload_speaker_profile_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.image.url


class SpeakerAndSession(models.Model):
    speaker = models.ForeignKey(Speaker, on_delete=models.CASCADE, related_name='speaker_sessions')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='speaker_sessions')
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.speaker.name


class CareerFairAndProduct(models.Model):
    # RESERVED = 1
    # FOR_SALE = 0
    #
    # CAREERFAIR_PRODUCT_RESERVE_STATUS_CHOICES = ((RESERVED, _('Reserved')), (FOR_SALE, _('For Sale')),)

    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE, related_name='career_fair_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='career_fair_products')
    product_sub_type = models.SmallIntegerField(choices=CareerFairProductSubType.CAREER_FAIR_PRODUCT_SUB_TYPE_CHOICES, default=CareerFairProductSubType.TICKET)
    """
    In case of advertisements etc. the product can be reserved for own use or sell it to other entities
    """
    # career_fair_product_status = models.SmallIntegerField(choices=CAREERFAIR_PRODUCT_RESERVE_STATUS_CHOICES, default=RESERVED)
    # """
    # Add the upload function and other details
    # """
    # ad_image = models.ImageField()

    def __str__(self):
        return "{0},{1}".format(self.career_fair.title, self.product.name)


class CareerFairAndProductOptional(models.Model):
    career_fair = models.ForeignKey(CareerFairDraft, on_delete=models.CASCADE, related_name='career_fair_draft_products')
    product = models.ForeignKey(ProductDraft, on_delete=models.CASCADE, related_name='career_fair_draft_products')
    product_sub_type = models.SmallIntegerField(choices=CareerFairProductSubType.CAREER_FAIR_PRODUCT_SUB_TYPE_CHOICES, default=CareerFairProductSubType.TICKET)

    # def __str__(self):
    #     return "{0},{1}".format(self.career_fair.title, self.product.name)


class CareerFairParticipant(models.Model):

    INDIVIDUAL = 1
    ENTITY = 2
    SPONSOR = 3

    PARTICIPATION_TYPE_CHOICES = (
        (INDIVIDUAL, _('Individual')), (ENTITY, _('Entity')), (SPONSOR, _('Sponsor')))

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='career_fair_participant')
    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE)
    entity_id = models.IntegerField(blank=True, null=True)
    participant_type = models.SmallIntegerField(choices=PARTICIPATION_TYPE_CHOICES, default=INDIVIDUAL)
    name_of_representative = models.CharField(_("name_of_representative"), max_length=100, null=True, blank=True)
    representative_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    is_payment_successful = models.BooleanField(default=False)
    address = models.CharField(_("address"), max_length=500, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.user.name


class ParticipantAndProduct(models.Model):
    participant = models.ForeignKey(CareerFairParticipant, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{0},{1}".format(self.product.name, self.participant.user.display_name)


class CareerFairSpeakerProfileImage(models.Model):
    speaker = models.OneToOneField(Speaker, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=upload_career_fair_speaker_profile_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.image.url


class CareerFairSpeakerDraftProfileImage(models.Model):
    speaker = models.OneToOneField(Speaker, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=upload_career_fair_speaker_draft_profile_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.image.url


class CareerFairSupportLogo(models.Model):
    support = models.OneToOneField(SupportOptional, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to=upload_career_fair_support_logo_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


class CareerFairSupportDraftLogo(models.Model):
    support = models.OneToOneField(SupportOptional, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to=upload_career_fair_support_optional_logo_media_location, width_field="width",
                              height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


class CareerFairImageType:
    MOBILE_IMAGE = 1
    DESKTOP_IMAGE = 2

    IMAGE_TYPE_CHOICES = (
        (MOBILE_IMAGE, _('Mobile Image')), (DESKTOP_IMAGE, _('Desktop Image')), )


class CareerFairAdvertisement(models.Model):

    NEW = 1
    APPROVED = 2
    PENDING = 3
    REJECTED = 4
    OTHER = 5

    AD_IMAGE_STATUS_CHOICES = (
        (NEW, _('New')), (APPROVED, _('Approved')), (PENDING, _('Pending')), (REJECTED, _('Rejected')),)

    career_fair = models.ForeignKey(CareerFair, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,)
    entity = models.ForeignKey(Entity, models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE,)

    ad_image_url = models.CharField(_("ad_image"), max_length=300, blank=True, null=True)
    ad_image_type = models.SmallIntegerField(choices=CareerFairImageType.IMAGE_TYPE_CHOICES, default=CareerFairImageType.DESKTOP_IMAGE)
    ad_redirect_url = models.CharField(_("ad_redirect"), max_length=300, blank=True, null=True)
    ad_status = models.SmallIntegerField(choices=AD_IMAGE_STATUS_CHOICES, default=PENDING)
    admin_comments = models.CharField(_("admin comments"), max_length=1000, blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    class Meta:
        verbose_name_plural = 'Career Fair Advertisements'
        ordering = ['-created', 'career_fair']

    def __str__(self):
        return self.entity.name


class CareerFairAdvertisementViews(models.Model):
    career_fair_advertisement = models.ForeignKey(CareerFairAdvertisement, on_delete=models.CASCADE)
    ad_image_type = models.SmallIntegerField(choices=CareerFairImageType.IMAGE_TYPE_CHOICES, default=CareerFairImageType.DESKTOP_IMAGE)
    number_of_views = models.PositiveIntegerField(null=True)

    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.career_fair_advertisement.product.name
