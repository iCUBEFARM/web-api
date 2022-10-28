#
# The below method is a signal receiver for pre_save called just before the Entity model is saved
#
import datetime
import itertools

from django.contrib.auth.models import Group
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.utils.text import slugify
from guardian.shortcuts import assign_perm

from icf_entity.models import Entity, EntityPerms

import logging

from icf_orders.models import ICFPaymentTransaction

logger = logging.getLogger(__name__)



"""
Create a unique slug for the Entity
"""
MAX_SLUG_LENGTH = 60


def create_icf_payment_transaction_slug(instance):

    if not instance.order_no:
        order_no_str = 'ICF'+datetime.datetime.strptime(str(datetime.datetime.today().date()), '%Y-%m-%d').strftime('%Y%m%d')
        instance.order_no = orig = slugify(order_no_str)[:MAX_SLUG_LENGTH]

        for x in itertools.count(1):
            if not ICFPaymentTransaction.objects.filter(order_no=instance.order_no).exists():
                break

            # Truncate the original order_no dynamically. Minus 1 for the hyphen.
            instance.order_no = "%s%d" % (orig[:MAX_SLUG_LENGTH - len(str(x)) - 1], x)
            logger.info("Created order_no for ICFPaymentTransaction {0}".format(instance.order_no))


@receiver(pre_save, sender=ICFPaymentTransaction)
def icf_payment_transaction_pre_save_receiver(sender, instance, *args, **kwargs):
    logger.info("Pre save receiver to create slug called")
    create_icf_payment_transaction_slug(instance)


# @receiver(post_save, sender=Entity)
# def entity_post_save_receiver(sender, instance, *args, **kwargs):
#     logger.info("Entity post save receiver called to create groups")
#
#     # Create groups for entity created for every permission.
#     # content_type = ContentType.objects.get_for_model(instance)
#
#     entity_permissions = EntityPerms.get_icf_permissions()
#
#     # Create groups for all entity permissions
#     for perm in entity_permissions:
#         #group_name = "{}_{}".format(instance.slug, perm.codename)
#         group_name = EntityPerms.get_entity_group(instance, perm.codename)
#         entity_group, created = Group.objects.get_or_create(name=group_name)
#         assign_perm(perm.codename, entity_group, instance)


# entity_add_permission = Signal(providing_args=["entity", "user", "perm", ])
# entity_remove_permission = Signal(providing_args=["entity", "user", "perm", ])
