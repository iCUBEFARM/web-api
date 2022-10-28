import itertools
import os

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import RegexValidator
from django.db import models


# Create your models here.
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from icf_generic.api.serializers import SponsoredListSerializer

from icf_generic.models import Address, Sponsored, Category, Country
from icf_auth.models import User
from django.utils.translation import ugettext_lazy as _
import logging

logger = logging.getLogger(__name__)

LOGOS_DIR = "entity/logos"


def upload_entity_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=LOGOS_DIR, file=instance.entity.slug, ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=LOGOS_DIR, file=filename)


ENTITY_BROCHURE_FILE_DIR = "entity/brochures"


def upload_entity_brochure_media_location(instance, filename):
    try:
        # print(instance.job_profile.user.slug)
        return "{dir1}/{dir2}/{file}{ext}".format(dir1=ENTITY_BROCHURE_FILE_DIR,
                                                  dir2=instance.entity.slug,
                                                  file=instance.entity.slug,
                                                  ext=os.path.splitext(filename)[1])
    except:
        print(instance.entity.slug)
        return "{dir1}/{dir2}/{file}".format(dir1=ENTITY_BROCHURE_FILE_DIR,
                                                  dir2=instance.entity.slug,
                                                  file=instance.entity.slug)


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.png', '.jpg', '.jpeg', '.txt', '.gif']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u' Unsupported file extension.')


class Sector(models.Model):
    sector = models.CharField(max_length=80, unique=True, blank=True)
    description = models.CharField(max_length=500, blank=True)  # not unique as there are duplicates (IT)

    class Meta:
        verbose_name_plural = 'Sectors'
        ordering = ('sector',)

    def __str__(self):
        return self.sector


class Industry(models.Model):
    industry = models.CharField(max_length=200, unique=True, blank=True)
    description = models.CharField(max_length=500, blank=True)  # not unique as there are duplicates (IT)

    class Meta:
        verbose_name_plural = 'Industries'
        ordering = ('industry',)

    def __str__(self):
        return self.industry


class CompanySize(models.Model):
    ENTITY_SIZE_SMALL = 1
    ENTITY_SIZE_MEDIUM = 2
    ENTITY_SIZE_LARGE = 3

    ENITIY_SIZE_CHOICES = (
        (ENTITY_SIZE_SMALL, _('Small')),
        (ENTITY_SIZE_MEDIUM, _('Medium')),
        (ENTITY_SIZE_LARGE, _('Large')),
    )

    size = models.CharField(max_length=40, unique=True, blank=True)
    description = models.CharField(max_length=80, blank=True)  # not unique as there are duplicates (IT)

    class Meta:
        verbose_name_plural = 'CompanySizes'
        ordering = ('size',)

    def __str__(self):
        return self.size


class EntityPerms():
    ENTITY_CREATE = 'icf_ent_cr'
    ENTITY_EDIT = 'icf_ent_ed'
    ENTITY_ADMIN = 'icf_ent_adm'
    ENTITY_ADD_USER = 'icf_ent_add_usr'
    ENTITY_USER = 'icf_ent_usr'

    ENTITY_PERM_CHOICES = (("ENTITY_CREATE", ENTITY_CREATE),
                            ("ENTITY_EDIT", ENTITY_EDIT ),
                            ("ENTITY_ADMIN", ENTITY_ADMIN),
                            ("ENTITY_ADD_USER", ENTITY_ADD_USER),
                            ("ENTITY_USER", ENTITY_USER),)

    # This provides all possible icf permissions on the Entity object. This includes permissions created by different
    # apps on the Entity model
    @classmethod
    def get_icf_permissions(cls):
        content_type = ContentType.objects.get_for_model(Entity)
        entity_permissions = Permission.objects.filter(content_type=content_type, codename__istartswith='icf_')
        return entity_permissions

    @classmethod
    def get_entity_perms(cls):
        return dict(cls.ENTITY_PERM_CHOICES)

    @classmethod
    def get_admin_perm(cls):
        return cls.ENTITY_ADMIN

    @classmethod
    def get_entity_user_perm(cls):
        return cls.ENTITY_USER

    @classmethod
    def get_entity_group(cls, entity, perm):
        return "{}_{}".format(entity.slug, perm)


class Entity(models.Model):

    ENTITY_CREATED = 1
    ENTITY_ACTIVE = 2
    ENTITY_INACTIVE = 3

    ENTITY_STATUS_CHOICES = (
        (ENTITY_ACTIVE, _('Active')),
        (ENTITY_INACTIVE, _('Inactive')),
    )


    LOGO_WIDTH = 300
    LOGO_HEIGHT = 300

    name = models.CharField(_("name"), max_length=200, blank=False, null=False)
    #logo = models.ForeignKey(Logo, on_delete=models.CASCADE, null=True, blank=True)
    # logo = models.ImageField(upload_to=upload_entity_media_location, width_field="width", height_field="height")

    email = models.EmailField(blank=False)
    phone = models.CharField(validators=[User.PHONE_REGEX], max_length=25, blank=False)  # validators should be a list
    alternate_phone = models.CharField(validators=[User.PHONE_REGEX], max_length=25, blank=True)  # validators should be a list
    website = models.URLField(blank=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, null=True)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name="entity", null=True)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="entity", null=True)
    company_size = models.ForeignKey(CompanySize, on_delete=models.CASCADE, related_name="entity", null=True)
    description = models.CharField(_("description"), max_length=1000, blank=False, null=False )
    status = models.SmallIntegerField(choices=ENTITY_STATUS_CHOICES, default=ENTITY_ACTIVE)
    slug = models.SlugField(blank=True, max_length=200)
    sponsored = GenericRelation(Sponsored, related_query_name="job", null=True)

    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)
    category = models.ForeignKey(Category,on_delete=models.CASCADE, related_name="entity", null=True)
    linked_in = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    schedule_appointment = models.URLField(blank=True)

    class Meta:
        ordering = ['-created', ]

        # Create permission codename with max
        permissions = (
            (EntityPerms.ENTITY_CREATE, 'entity create'),
            (EntityPerms.ENTITY_EDIT, 'ability to change entity'),
            (EntityPerms.ENTITY_ADMIN, 'act as admin of entity'),
            (EntityPerms.ENTITY_ADD_USER, 'ability to add entity user'),
            (EntityPerms.ENTITY_USER, 'ability to view entity'),
        )

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return self.name

    def get_sponsored_info(self):
        if self.status == Entity.ENTITY_ACTIVE:
            serializer = SponsoredListSerializer()
            serializer.title = self.name
            serializer.description = self.description
            serializer.entity_name = self.name
            serializer.location = self.address
            serializer.slug = self.slug
            serializer.content_type = self.__class__.__name__
            serializer.published_date = ""
            serializer.expiry_date = ""
            serializer.logo = self.get_entity_logo()
            return serializer
        else:
            return None

    def get_entity_logo(self):
        try:
            return Logo.objects.get(entity=self).image.url
        except ObjectDoesNotExist:
            return ""

    # def get_entity_user(self):
    #     user = User.objects.filter(email=self.email).first()
    #     print('----------', user)

    @staticmethod
    def get_icf_permissions():
        content_type = ContentType.objects.get_for_model(Entity)
        entity_permissions = Permission.objects.filter(content_type=content_type, codename__istartswith='icf_')
        return entity_permissions


class Logo(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='logo', null=True, blank=True)
    image = models.ImageField(upload_to=upload_entity_media_location, width_field="width", height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)

    def __str__(self):
        return self.image.url


class EntityUser(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return "{} : {}".format(self.entity, self.user)


class FeaturedEntity(models.Model):
    FEATURED_ENTITY_ACTIVE = 1
    FEATURED_ENTITY_INACTIVE = 2

    FEATTURED_ENITIY_STATUS_CHOICES = (
        (FEATURED_ENTITY_ACTIVE, _('Active')),
        (FEATURED_ENTITY_INACTIVE, _('Inactive')),
    )

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    # banner_image = models.ImageField(upload_to=upload_entity_media_location, width_field="width", height_field="height")
    # height = models.PositiveIntegerField(null=True)
    # width = models.PositiveIntegerField(null=True)
    title = models.CharField(_("title"), max_length=150)
    description = models.CharField(_("description"), max_length=150, blank=False, null=False)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.SmallIntegerField(choices=FEATTURED_ENITIY_STATUS_CHOICES, default=FEATURED_ENTITY_INACTIVE)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __str__(self):
        return self.entity.name


class TeamMember(models.Model):
    name = models.CharField(_("name"), max_length=50, blank=False, null=False )
    position = models.CharField(_("position"), max_length=50, blank=False, null=False )
    image = models.ImageField(upload_to=upload_entity_media_location, width_field="width", height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    featured_entity = models.ForeignKey(FeaturedEntity, on_delete=models.CASCADE)
    is_incharge = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class PendingEntityUser(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user_to_add = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=False, auto_now=True)
    entity_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pending_entity_user')

    def __str__(self):
        return "{} : {} : {}".format(self.entity, self.user_to_add, self.entity_user)


class MinistryMasterConfig(models.Model):
    ministry_type = models.CharField(_("ministry_type"), max_length=500, blank=False, null=False)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    industries = models.CharField(_("industries"), max_length=500, blank=True, null=True)
    sectors = models.CharField(_("sectors"), max_length=500, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)

    class Meta:
        verbose_name_plural = 'MinistryMasterConfig'
        unique_together = ('ministry_type', 'country',)

    def __str__(self):
        return self.ministry_type + " " + self.country


class EntityBrochure(models.Model):
    brochure_name = models.CharField(max_length=150)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    brochure = models.FileField(upload_to=upload_entity_brochure_media_location,
                              validators=[validate_file_extension], max_length=200, null=True, blank=True)
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
        return self.brochure_name


class EntityPromotionalVideo(models.Model):
    promotional_video_name = models.CharField(max_length=150)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    promotional_video_url = models.URLField(blank=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.promotional_video_name



