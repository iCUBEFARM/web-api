import itertools
from django.contrib.contenttypes.models import ContentType
from django.db import models

# Create your models here.
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from icf_auth.models import User
from icf_entity.models import Entity
from icf_generic.models import Address, Category, Type, AddressOptional
import logging
logger = logging.getLogger(__name__)


class Item(models.Model):

    ITEM_DRAFT= 1
    ITEM_ACTIVE = 2
    ITEM_EXPIRED = 3
    ITEM_CLOSED = 4
    ITEM_MARK_DELETE = 5
    ITEM_DELETED = 6
    ITEM_UNDER_REVIEW = 7
    ITEM_REJECTED = 8

    ITEM_STATUS_CHOICES = (
        (ITEM_DRAFT, _('Draft')), (ITEM_ACTIVE, _('Active')), (ITEM_EXPIRED, _('Expired')),
        (ITEM_CLOSED, _('Closed')), (ITEM_MARK_DELETE, _('Marked for delete')), (ITEM_DELETED, _('Deleted')),
        (ITEM_UNDER_REVIEW, _('Item Under Review')), (ITEM_REJECTED, _('Item Rejected')))

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=80, blank=False, null=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="item")
    item_type = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="item")
    description = models.TextField(_("description"), blank=False, null=False)
    location = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='item')
    status = models.SmallIntegerField(choices=ITEM_STATUS_CHOICES, default=ITEM_DRAFT)
    # expiry = models.DateTimeField(_("valid till"))

    # for testing purpose
    expiry = models.DateTimeField()

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='item')
    slug = models.SlugField(blank=True, unique=True)
    start_date = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.slug)

    class Meta:
        verbose_name_plural = 'Items'
        ordering = ['-created', ]


class FavoriteItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='fav_item')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fav_item")

    def __str__(self):
        return "{0}".format(self.item)


class ItemUserView(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="user_view")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="item_view")

    def __str__(self):
        return "{0},{1}".format(self.item.title, self.user.username)




MAX_SLUG_LENGTH = 200

def create_category_slug(instance):

    if not instance.slug:
        instance.slug = orig = slugify(instance.name)[:MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not Category.objects.filter(slug=instance.slug).exists():
                break

            instance.slug = "%s-%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created slug for Category {0}".format(instance.slug))


@receiver(pre_save, sender=Category)
def category_pre_save_receiver(sender, instance, *args, **kwargs):
    logger.info("Pre save receiver to create slug  for category")
    create_category_slug(instance)


class ItemDraft(models.Model):

    ITEM_DRAFT= 1
    ITEM_ACTIVE = 2
    ITEM_EXPIRED = 3
    ITEM_CLOSED = 4
    ITEM_MARK_DELETE = 5
    ITEM_DELETED = 6
    ITEM_UNDER_REVIEW = 7
    ITEM_REJECTED = 8

    ITEM_STATUS_CHOICES = (
        (ITEM_DRAFT, _('Draft')), (ITEM_ACTIVE, _('Active')), (ITEM_EXPIRED, _('Expired')),
        (ITEM_CLOSED, _('Closed')), (ITEM_MARK_DELETE, _('Marked for delete')), (ITEM_DELETED, _('Deleted')),
        (ITEM_UNDER_REVIEW, _('Item Under Review')), (ITEM_REJECTED, _('Item Rejected')))

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    title = models.CharField(_("title"), max_length=80, blank=False, null=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True)
    item_type = models.ForeignKey(Type, on_delete=models.CASCADE, blank=True, null=True)
    description = models.TextField(_("description"), blank=True, null=True)
    location = models.ForeignKey(AddressOptional, on_delete=models.CASCADE,blank=True, null=True)
    status = models.SmallIntegerField(choices=ITEM_STATUS_CHOICES, blank=True, null=True)
    # expiry = models.DateTimeField(_("valid till"))

    # for testing purpose
    expiry = models.DateTimeField(blank=True,null=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE,blank=True, null=True)
    slug = models.SlugField(blank=True,unique=True)
    start_date = models.DateTimeField(blank=True,null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.slug)

    class Meta:
        verbose_name_plural = 'Items'
        ordering = ['-created', ]
