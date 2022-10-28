from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import ugettext_lazy as _

# Create your models here.


class Country(models.Model):
    country = models.CharField(max_length=40, unique=True, blank=True)
    code = models.CharField(max_length=2, blank=True)  # not unique as there are duplicates (IT)

    class Meta:
        verbose_name_plural = 'Countries'
        ordering = ('country',)

    def __str__(self):
        return '%s' % (self.country or self.code)


class State(models.Model):
    state = models.CharField(max_length=165, blank=True)
    code = models.CharField(max_length=3, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')

    class Meta:
        unique_together = ('state', 'country')
        ordering = ('country', 'state')

    def __str__(self):
        txt = self.to_str()
        country = '%s' % self.country
        if country and txt:
            txt += ', '
        txt += country
        return txt

    def to_str(self):
        return '%s' % (self.state or self.code)


class City(models.Model):
    city = models.CharField(max_length=165, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')

    class Meta:
        verbose_name_plural = 'Cities'
        unique_together = ('city', 'state')
        ordering = ('city', 'state')

    def __str__(self):
        txt = '%s' % self.city
        state = self.state.to_str() if self.state else ''
        if txt and state:
            txt += ', '
        txt += state
        cntry = '%s' % (self.state.country if self.state and self.state.country else '')
        if cntry:
            txt += ', %s' % cntry
        return txt


class Address(models.Model):
    """
    Address model.

    """
    HOME_OR_WORK = 1
    BILLING = 2

    ADDRESS_TYPE_CHOICES = (
        (HOME_OR_WORK, "HOME_OR_WORK"), (BILLING, "BILLING"))

    address_1 = models.CharField(_("address"), max_length=300)
    address_2 = models.CharField(_("address continued"), max_length=300,
                                 blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="addresses")
    address_type = models.SmallIntegerField(choices=ADDRESS_TYPE_CHOICES, default=HOME_OR_WORK)

    def __str__(self):
        if not self.address_2:
            return "%s, %s" % (self.address_1, self.city)
        return "%s, %s, %s" % (self.address_1, self.address_2, self.city)

    class Meta:
        verbose_name_plural = 'Addresses'


class Language(models.Model):
    name = models.CharField(_("language"), max_length=20)
    code = models.CharField(_("code"), max_length=3)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Languages'
        ordering = ('name',)


class Currency(models.Model):
    name = models.CharField(_("currency"), max_length=20)
    code = models.CharField(_("currency code"), max_length=4)

    def __str__(self):
        return self.code

    class Meta:
        verbose_name_plural = 'Currencies'
        ordering = ('name',)


"""
Create a unique slug for the UserProfile
"""

#
# The below method is a signal receiver for pre_save called just before the UserProfile model is saved
#


class Sponsored(models.Model):
    """
    Sponsored can have any kind of object
    https://docs.djangoproject.com/en/dev/ref/contrib/contenttypes/#generic-relations
    Create a reverse relation in the object using this.
    """


    SPONSORED_ACTIVE = 1
    SPONSORED_INACTIVE = 2

    SPONSORED_STATUS = (
        (SPONSORED_ACTIVE, _('Active')),
        (SPONSORED_INACTIVE, _('Inactive'))
    )

    slug = models.SlugField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    start_date = models.DateTimeField(_("valid from"))
    end_date = models.DateTimeField(_("valid till"))
    count = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    status = models.SmallIntegerField(choices=SPONSORED_STATUS, default=SPONSORED_ACTIVE)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}: {}".format(self.content_type, self.object_id)


class FeaturedVideo(models.Model):
    FEATURED_VIDEO_ACTIVE = 1
    FEATURED_VIDEO_INACTIVE = 2

    FEATTURED_VIDEO_STATUS_CHOICES = (
        (FEATURED_VIDEO_ACTIVE, _('Active')),
        (FEATURED_VIDEO_INACTIVE, _('Inactive')),
    )

    title = models.CharField(_("title"), max_length=150)
    video_url = models.URLField()
    description = models.CharField(_("description"), max_length=150, blank=False, null=False)
    status = models.SmallIntegerField(choices=FEATTURED_VIDEO_STATUS_CHOICES, default=FEATURED_VIDEO_INACTIVE)
    is_main_video = models.BooleanField(default=False)
    show_in_dashboard = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.title


class Type(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(_("Description of type of item"), max_length=100)
    slug = models.SlugField(blank=True)

    def __str__(self):
        return "{}".format(self.name)


class Category(models.Model):
    name = models.CharField(_("category"), max_length=200)
    description = models.CharField(_("Description of category"), max_length=500)
    slug = models.SlugField(blank=True,max_length=200)
    type = models.ForeignKey(Type, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class FeaturedEvent(models.Model):
    PHONE_REGEX = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")

    FEATURED_EVENT_ACTIVE = 1
    FEATURED_EVENT_INACTIVE = 2

    FEATTURED_EVENT_STATUS_CHOICES = (
        (FEATURED_EVENT_ACTIVE, _('Active')),
        (FEATURED_EVENT_INACTIVE, _('Inactive')),
    )

    title = models.CharField(_("title"), max_length=150)
    image = models.ImageField(upload_to='featured-event-images')
    description = models.CharField(_("description"), max_length=150, blank=False, null=False)
    status = models.SmallIntegerField(choices=FEATTURED_EVENT_STATUS_CHOICES, default=FEATURED_EVENT_INACTIVE)
    location = models.CharField(_("location"), max_length=70, blank=False, null=False)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    start_date_timing = models.CharField(_("start date timing"), max_length=50, blank=True)
    end_date_timing = models.CharField(_("end date timing"), max_length=50, blank=True)
    contact_email = models.EmailField()
    slug = models.SlugField(blank=True)
    contact_no = models.CharField(validators=[PHONE_REGEX], max_length=17, blank=True)  # validators should be a list
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(_("question"), max_length=10000, blank=False, null=False)
    answer = models.TextField(_("answer"), blank=False, null=False)
    slug = models.SlugField(blank=True)
    video_url = models.URLField(_("video_url"), blank=True, null=True)

    def __str__(self):
        return self.question


class FAQCategory(models.Model):
    name = models.CharField(_("name"), max_length=150, blank=False, null=False)
    description = models.CharField(_("description"), max_length=500, blank=True, null=True)
    slug = models.SlugField(blank=True)

    def __str__(self):
        return self.name


class QuestionCategory(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, blank=False, null=False)
    faq = models.ForeignKey(FAQ, on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = ('category', 'faq')

    def __str__(self):
        return self.category.name


class AboutUs(models.Model):
    first_name = models.CharField(_("first name"), max_length=150, blank=False, null=False)
    second_name = models.CharField(_("second name"), max_length=150, blank=False, null=False)
    email = models.EmailField(blank=False, null=False)
    subject = models.CharField(_("subject"), max_length=150, blank=False, null=False)
    message = models.CharField(_("message"), max_length=3000, blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __str__(self):
        return self.email


class AdminEmail(models.Model):
    support = models.EmailField()

    def __str__(self):
        return self.support


def create_type_slug(instance):
        try:
            if not instance.slug:
                instance_str = str(instance).replace(' ', '')
                instance.slug = ContentType.objects.get(model = instance_str)
        except AttributeError:
            instance.slug = ContentType.objects.get(model=instance_str)


@receiver(pre_save, sender=Type)
def type_pre_save_receiver(sender, instance, *args, **kwargs):
    create_type_slug(instance)


class AddressOptional(models.Model):
    """
    Address model.

    """
    address_1 = models.CharField(_("address"), max_length=300,blank=True,null=True)
    address_2 = models.CharField(_("address continued"), max_length=300,
                                 blank=True,null=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE,blank=True,null=True)

    def __str__(self):
        if not self.address_2:
            return "%s, %s" % (self.address_1, self.city)
        return "%s, %s, %s" % (self.address_1, self.address_2, self.city)


