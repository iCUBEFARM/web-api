import os

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _


# Create your models here.
from icf_auth.models import User
from icf_orders.models import Product

FEATURED_EVENT_IMAGE_DIR = "featured_events/images"


def upload_featured_event_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=FEATURED_EVENT_IMAGE_DIR, file=instance.slug, ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=FEATURED_EVENT_IMAGE_DIR, file=filename)


class TermsAndConditions(models.Model):
    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=False, null=False)

    def __str__(self):
        return self.name


# class FeaturedEventCategory(models.Model):
#     name = models.CharField(_("name"), max_length=100)
#     description = models.TextField(_("description"), blank=False, null=False)
#     slug = models.SlugField(blank=True)
#     is_active = models.BooleanField(default=False)
#
#     def __str__(self):
#         return self.name


class EventProduct(models.Model):
    product = models.OneToOneField(Product, unique=True, on_delete=models.CASCADE)
    expiry_date = models.DateTimeField(_("expiry date"))
    does_have_extra_participants = models.BooleanField(default=False)
    no_of_tickets_allowed = models.IntegerField(default=1)

    def __str__(self):
        return self.product.name


class FeaturedEventGallery(models.Model):
    title = models.CharField(_("title"), max_length=150)
    image_1 = models.ImageField(upload_to=upload_featured_event_media_location)
    image_2 = models.ImageField(upload_to=upload_featured_event_media_location)
    image_3 = models.ImageField(upload_to=upload_featured_event_media_location)
    image_4 = models.ImageField(upload_to=upload_featured_event_media_location)
    gallery_url = models.URLField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class ParticipationType(models.Model):
    participation_type = models.CharField(_("participation type"), max_length=150)

    def __str__(self):
        return self.participation_type


class FeaturedEvent(models.Model):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")

    FEATURED_EVENT_ACTIVE = 1
    FEATURED_EVENT_INACTIVE = 2

    FEATURED_EVENT_STATUS_CHOICES = (
        (FEATURED_EVENT_ACTIVE, _('Active')),
        (FEATURED_EVENT_INACTIVE, _('Inactive')),
    )

    title = models.CharField(_("title"), max_length=150)
    sub_title = models.CharField(_("sub_title"), max_length=250)
    image = models.ImageField(upload_to=upload_featured_event_media_location)
    description = models.TextField(_("description"), blank=False, null=False)
    email_content = models.TextField(_("email_content"), blank=False, null=False, default='')
    status = models.SmallIntegerField(choices=FEATURED_EVENT_STATUS_CHOICES, default=FEATURED_EVENT_INACTIVE)
    location = models.CharField(_("location"), max_length=70, blank=False, null=False)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    start_date_timing = models.CharField(_("start date timing"), max_length=50, blank=True)
    end_date_timing = models.CharField(_("end date timing"), max_length=50, blank=True)
    contact_email = models.EmailField()
    terms_and_conditions = models.ForeignKey(TermsAndConditions, on_delete=models.CASCADE)
    is_featured_event = models.BooleanField(default=False)
    slug = models.SlugField(blank=True)
    contact_no = models.CharField(validators=[PHONE_REGEX], max_length=17, blank=True)  # validators should be a list
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.title


class FeaturedEventAndProduct(models.Model):
    featured_event = models.ForeignKey(FeaturedEvent, on_delete=models.CASCADE)
    product = models.ForeignKey(EventProduct, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.featured_event.title


# class FeaturedEventAndCategory(models.Model):
#     featured_event = models.ForeignKey(FeaturedEvent, on_delete=models.CASCADE)
#     category = models.ForeignKey(FeaturedEventCategory, on_delete=models.CASCADE)
#     product = models.ForeignKey(EventProduct, on_delete=models.CASCADE, null=True, blank=True)
#     created = models.DateTimeField(auto_now_add=True, auto_now=False)
#     updated = models.DateTimeField(auto_now_add=False, auto_now=True)
#
#     def __str__(self):
#         return self.featured_event.title


class Participant(models.Model):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    featured_event = models.ForeignKey(FeaturedEvent, on_delete=models.CASCADE)
    product = models.ForeignKey(EventProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    entity_name = models.CharField(_("entity name"), max_length=100, null=True, blank=True)
    entity_email = models.EmailField(null=True, blank=True)
    phone_no = models.CharField(validators=[PHONE_REGEX], max_length=17, null=True, blank=True)  # validators should be a list
    name_of_representative = models.CharField(_("name_of_representative"), max_length=100, null=True, blank=True)
    address = models.CharField(_("address"), max_length=500, null=True, blank=True)
    participants = models.CharField(_("participants"), max_length=10000, null=True, blank=True)
    is_payment_successful = models.BooleanField(default=False)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    is_active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


    def __str__(self):
        return self.entity_name




