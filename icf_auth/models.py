import itertools
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _


# Create your models here.
from icf_generic.models import Address, Language, Country


PROFILE_IMAGE_DIR = "userprofile/images"


def upload_userprofile_media_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=PROFILE_IMAGE_DIR, file=instance.user_profile.user.slug, ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=PROFILE_IMAGE_DIR, file=filename)


class User(AbstractUser):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                       message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")

    mobile = models.CharField(validators=[PHONE_REGEX], max_length=20, blank=True)  # validators should be a list
    slug = models.SlugField(blank=True)

    def get_mobile(self):
        return self.mobile

    @property
    def display_name(self):
        return "{} {}".format(self.first_name, self.last_name)


class RegistrationOTP(models.Model):
    REG_OTP_CREATED = 1
    REG_OTP_SENT = 2
    REG_OTP_VERIFIED = 3
    REG_OTP_FAILED = 4
    REG_OTP_STATUS_CHOICES = ((REG_OTP_CREATED, 'Created'), (REG_OTP_SENT, 'Sent'), (REG_OTP_VERIFIED, 'Verified'), (REG_OTP_FAILED, 'Failed'),)

    mobile = models.CharField(validators=[User.PHONE_REGEX], max_length=17, blank=True) # validators should be a list
    key = models.CharField(max_length=16, blank=False, null=False)
    updated = models.DateTimeField(auto_now=True)
    status = models.SmallIntegerField(choices=REG_OTP_STATUS_CHOICES)

    def __str__(self):
        return self.mobile


class RegistrationEmailOTP(models.Model):
    REG_OTP_CREATED = 1
    REG_OTP_SENT = 2
    REG_OTP_VERIFIED = 3
    REG_OTP_FAILED = 4
    REG_OTP_STATUS_CHOICES = ((REG_OTP_CREATED, 'Created'), (REG_OTP_SENT, 'Sent'), (REG_OTP_VERIFIED, 'Verified'), (REG_OTP_FAILED, 'Failed'),)

    email = models.EmailField(_('email address'), blank=True) # validators should be a list
    mobile = models.CharField(validators=[User.PHONE_REGEX], max_length=17, blank=True) # validators should be a list
    key = models.CharField(max_length=16, blank=False, null=False)
    updated = models.DateTimeField(auto_now=True)
    status = models.SmallIntegerField(choices=REG_OTP_STATUS_CHOICES)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    GENDER_CHOICES = (
        ('M', _('Male')),
        ('F', _('Female')),
    )
    NOT_UPDATED=1
    UPDATED=2

    user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True)
    location = models.ForeignKey(Address, on_delete=models.CASCADE, null=True, blank=True)
    biography = models.CharField(_("biography"), max_length=250, null=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True)
    nationality = models.ForeignKey(Country, on_delete=models.CASCADE, null=True)
   # slug = models.SlugField(blank=True)
    status = models.SmallIntegerField(default=NOT_UPDATED)
    is_profile_private = models.BooleanField(default=False)
    professional_pronoun = models.CharField(_("professional_pronoun"), max_length=250, null=True)
    professional_title = models.CharField(_("professional_title"), max_length=250, null=True)

    def __str__(self):
        return self.user.username


MAX_SLUG_LENGTH = 60


def create_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.username)[:MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not User.objects.filter(slug=instance.slug).exists():
                break
            # Truncate the original slug dynamically. Minus 1 for the hyphen.
            instance.slug = "%s-%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            # logger.info("Created slug for UserProfile {0}".format(instance.slug))


@receiver(pre_save, sender=User)
def user_profile_pre_save_receiver(sender, instance, *args, **kwargs):
    # logger.info("Pre save receiver to create slug called")
    create_slug(instance)


class UserProfileImage(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=upload_userprofile_media_location, width_field="width", height_field="height")
    height = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)

    def __str__(self):
        return self.image.url


class UserBrowserInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    os = models.CharField(max_length=200)
    device_type = models.CharField(max_length=300)
    device_info = models.CharField(max_length=300)
    browser = models.CharField(max_length=300)
