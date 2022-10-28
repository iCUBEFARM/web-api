import os
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.exceptions import ValidationError, ObjectDoesNotExist

# Create your models here.
from icf import settings
from icf_auth.models import User
from icf_entity.models import Entity
from icf_generic.models import Type

MESSAGE_ATTACHMENT_DIR = "jobs/messages"

# Function to validate upload before upload
def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xlsx', '.xls']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u' Unsupported file extension.')

class ICFMessageManager(models.Manager):

    def _folder(self, filters, app_filter=None, order_by=None):
        qs = self.all()

        # if related:
        #     qs = qs.select_related(*related)
        if order_by:
            qs = qs.order_by(order_by)

        if isinstance(filters, (list, tuple)):
            lookups = models.Q()
            for filter_dict in filters:
                lookups |= models.Q(**filter_dict)
        else:
            lookups = models.Q(**filters)
        qs = qs.filter(lookups)
        if app_filter:
            qs = qs.filter(app_filter)
        return qs

    # def inbox(self, user, related=True, **kwargs):
    #     """
    #     Return accepted messages received by a user but not marked as archived or deleted.
    #     """
    #     related = ('sender',) if related else None
    #     filters = {
    #         'recipient': user,
    #         'recipient_archived': False,
    #         'recipient_deleted_at__isnull': True,
    #     }
    #     return self._folder(related, filters, **kwargs)

    def inbox(self, subscriber, **kwargs):
        """
        Return accepted messages received by a user/entity but not marked as archived or deleted.
        """
        #app_filter = kwargs.get('app_filter')

        filters = {
            'recipient_type': ContentType.objects.get_for_model(subscriber),
            'recipient_id': subscriber.id,
            'recipient_archived': False,
            'recipient_deleted_at__isnull': True,
        }
        return self._folder(filters, **kwargs)

    def inbox_unread_count(self, subscriber):
        """
        Return the number of unread messages for a user/entity.

        """
        return self.inbox(subscriber).filter(read_at__isnull=True).count()

    def sent(self, subscriber, **kwargs):
        """
        Return all messages sent by a user/entity but not marked as archived or deleted.
        """
        filters = {
            'sender_type': ContentType.objects.get_for_model(subscriber),
            'sender_id': subscriber.id,
            'sender_archived': False,
            'sender_deleted_at__isnull': True,
        }
        return self._folder(filters, **kwargs)

    def archives(self, subscriber, **kwargs):
        """
        Return messages belonging to a user and marked as archived.
        """
        #related = ('sender', 'recipient')
        filters = ({
            'recipient_type': ContentType.objects.get_for_model(subscriber),
            'recipient_id': subscriber.id,
            'recipient_archived': True,
            'recipient_deleted_at__isnull': True,
        }, {
            'sender_type': ContentType.objects.get_for_model(subscriber),
            'sender_id': subscriber.id,
            'sender_archived': True,
            'sender_deleted_at__isnull': True,
        })
        return self._folder(filters, **kwargs)

    def trash(self, subscriber, **kwargs):
        """
        Return messages belonging to a user and marked as deleted.
        """
        filters = ({
            'recipient_type': ContentType.objects.get_for_model(subscriber),
            'recipient_id': subscriber.id,
            'recipient_deleted_at__isnull': False,
        }, {
            'sender_type': ContentType.objects.get_for_model(subscriber),
            'sender_id': subscriber.id,
            'sender_deleted_at__isnull': False,
        })
        return self._folder(filters, **kwargs)

    def thread(self, subscriber, query_filter):
        """
        Return message/conversation for display.
        """
        subscriber_type = ContentType.objects.get_for_model(subscriber)
        return self.filter(
            query_filter,
            (models.Q(recipient_type=subscriber_type, recipient_id=subscriber.id) |
             models.Q(sender_type=subscriber_type, sender_id=subscriber.id)
             )).order_by('sent_at')

    def set_read(self, subscriber, query_filter):
        """
        Set messages as read.
        """
        return self.filter(
            query_filter,
            recipient_type=ContentType.objects.get_for_model(subscriber),
            recipient_id=subscriber.id,
            read_at__isnull=True,
        ).update(read_at=now())

    def set_archive(self, subscriber, query_filter):
        """
        Set messages in a thread as archived.
        """

        recipeient_rows = self.filter(
            query_filter,
            recipient_type=ContentType.objects.get_for_model(subscriber),
            recipient_id=subscriber.id,
        ).update(recipient_archived=True)

        sender_rows = self.filter(
            query_filter,
            sender_type=ContentType.objects.get_for_model(subscriber),
            sender_id=subscriber.id,
        ).update(sender_archived=True)

        return

    def set_delete(self, subscriber, query_filter):
        """
        Set messages as deleted.
        """
        self.filter(
            query_filter,
            recipient_type=ContentType.objects.get_for_model(subscriber),
            recipient_id=subscriber.id,
        ).update(recipient_deleted_at=now())

        self.filter(
            query_filter,
            sender_type=ContentType.objects.get_for_model(subscriber),
            sender_id=subscriber.id,
        ).update(sender_deleted_at=now())

    def restore_deleted(self, subscriber, query_filter):
        """
        Restore messaged deleted.
        """
        self.filter(
            query_filter,
            recipient_type=ContentType.objects.get_for_model(subscriber),
            recipient_id=subscriber.id,
        ).update(recipient_deleted_at=None,recipient_archived=False)

        self.filter(
            query_filter,
            sender_type=ContentType.objects.get_for_model(subscriber),
            sender_id=subscriber.id,
        ).update(sender_deleted_at=None,sender_archived=False)

    def restore_archived(self, subscriber, query_filter):
        """
        Restore messaged archived.
        """
        self.filter(
            query_filter,
            recipient_type=ContentType.objects.get_for_model(subscriber),
            recipient_id=subscriber.id,
        ).update(recipient_archived=False)

        self.filter(
            query_filter,
            sender_type=ContentType.objects.get_for_model(subscriber),
            sender_id=subscriber.id,
        ).update(sender_archived=False)


class ICFMessagePermManager(models.Manager):

    def get_perm_for_app(self, app_slug):
        """
        Get the permission required for sending messages in the app.
        """
        return self.get(app_type__slug=app_slug).perm_reqd.codename

    def get_all_perms(self):
        return {i[0]: i[1] for i in self.values_list('perm_reqd__codename', 'app_type__slug')}


class AppMessagePerm(models.Model):
    app_type = models.ForeignKey(Type, on_delete=models.CASCADE)
    perm_reqd = models.ForeignKey(Permission, on_delete=models.CASCADE)

    objects = ICFMessagePermManager()

    class Meta:
        verbose_name = _("Messaging Permissions")
        verbose_name_plural = _("Messaging Permissions")


class ICFMessage(models.Model):

    SUBJECT_MAX_LENGTH = 120

    subject = models.CharField(_("subject"), max_length=SUBJECT_MAX_LENGTH)
    topic_slug = models.SlugField()
    body = models.TextField(_("body"), blank=True)

    sender_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="sender_type")
    sender_id = models.PositiveIntegerField(verbose_name="sender_id")
    sender = GenericForeignKey('sender_type', 'sender_id')
    sender_name = models.CharField(max_length=80)

    recipient_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="recipient_type")
    recipient_id = models.PositiveIntegerField()
    recipient = GenericForeignKey('recipient_type', 'recipient_id')
    recipient_name = models.CharField(max_length=80)


    app_type = models.ForeignKey(Type, on_delete=models.CASCADE)
    entity_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    parent = models.ForeignKey('self', related_name='next_messages', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("parent message"))
    thread = models.ForeignKey('self', related_name='child_messages', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("root message"))
    sent_at = models.DateTimeField(_("sent at"), default=now)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    sender_archived = models.BooleanField(_("archived by sender"), default=False)
    recipient_archived = models.BooleanField(_("archived by recipient"), default=False)

    sender_deleted_at = models.DateTimeField(_("deleted by sender at"), null=True, blank=True)
    recipient_deleted_at = models.DateTimeField(_("deleted by recipient at"), null=True, blank=True)


    objects = ICFMessageManager()

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ['-sent_at', '-id']

    def __str__(self):
        return self.sender_name + " " + self.recipient_name

    @property
    def is_new(self):
        """Tell if the recipient has not yet read the message."""
        return self.read_at is None

    @property
    def is_replied(self):
        """Tell if the recipient has written a reply to the message."""
        return self.replied_at is not None

    def admin_sender(self):
        """
        Return the sender either as a username or as entity name.
        Designed for the Admin site.

        """
        if self.sender:
            return str(self.sender)
        else:
            return '<{0}>'.format(self.entity.name)
    admin_sender.short_description = _("sender")
    admin_sender.admin_order_field = 'sender'

    # Give the sender either as a username or as a plain email.
    clear_sender = property(admin_sender)

    def admin_recipient(self):
        """
        Return the recipient either as a username or or as entity name.
        Designed for the Admin site.

        """
        if self.recipient:
            return str(self.recipient)
        else:
            return '<{0}>'.format(self.entity.name)
    admin_recipient.short_description = _("recipient")
    admin_recipient.admin_order_field = 'recipient'

    # Give the recipient either as a username or as a plain email.
    clear_recipient = property(admin_recipient)

    def get_replies_count(self):
        """Return the number of accepted responses."""
        return self.next_messages.count()


class ICFNotification(models.Model):
    SUBJECT_MAX_LENGTH = 200
    message = models.CharField(_('message'), max_length=SUBJECT_MAX_LENGTH)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    sent_at = models.DateTimeField(_("sent at"), default=now)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    deleted_at =models.DateTimeField(_("deleted_at"),null=True,blank=True)
    details = models.CharField(_('details'), max_length=SUBJECT_MAX_LENGTH,null=True, blank=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ['-sent_at', '-id']


def upload_message_attachment_location(instance, filename):
    try:
        return "{dir}/{file}{ext}".format(dir=MESSAGE_ATTACHMENT_DIR, file=instance.user.slug, ext=os.path.splitext(filename)[1])
    except:
        return "{dir}/{file}".format(dir=MESSAGE_ATTACHMENT_DIR, file=filename)

#  MOdel for Message attachments.
class MessageAttachmentUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    attachment_src = models.FileField(upload_to=upload_message_attachment_location,
                                  validators=[validate_file_extension],max_length=200)

    def __str__(self):
        return self.attachment_src.url
