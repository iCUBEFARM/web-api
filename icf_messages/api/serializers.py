from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from guardian.shortcuts import get_perms
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import StringRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers, status
from django.core import serializers as core_serializers

from icf_auth.models import User, UserProfileImage
from icf_entity.api.mixins import ICFEntityMixin
from icf_entity.api.serializers import EntityLogoSerializer
from icf_entity.models import Logo
from icf_generic.Exceptions import ICFException
from icf_generic.models import Type
from icf_messages import app_settings
from icf_messages.app_settings import message_user_name_part, message_text_body_part
from icf_messages.message_helper import send_email_notification_to_job_seeker
from icf_messages.models import ICFMessage, AppMessagePerm, ICFNotification, MessageAttachmentUpload
from django.utils.translation import ugettext_lazy as _

import logging

logger = logging.getLogger(__name__)


class InboxSerializer(ModelSerializer):
    #sender_name = SerializerMethodField()
    # sender_type = SerializerMethodField()
    sender_slug = SerializerMethodField()
    entity_user = StringRelatedField()
    entity_user_name = SerializerMethodField()

    #recipient_name = SerializerMethodField()
    # recipient_type = SerializerMethodField()
    recipient_slug = SerializerMethodField()
    sender_image = SerializerMethodField()
    recipient_image = SerializerMethodField()

    class Meta:
        model = ICFMessage
        exclude = ['sender_id', 'recipient_id','sender_type','recipient_type','parent','replied_at',
                   'sender_archived','recipient_archived','sender_deleted_at','recipient_deleted_at','app_type']

    # def get_sender_name(self, obj):
    #     return obj.sender.display_name

    def get_sender_type(self, obj):
        return obj.sender.__class__.__name__.lower()

    def get_sender_slug(self, obj):
        return obj.sender.slug

    def get_sender_image(self,obj):
        sender_class = self.get_sender_type(obj)
        if sender_class == "entity":
            logo = Logo.objects.filter(entity__slug=obj.sender.slug).first()
            if logo:
                return logo.image.url
            else:
                return None

        if sender_class == "user":
            try:
                request = self.context.get('request')
                user = request.user
                return UserProfileImage.objects.get(user_profile__user=obj.sender).image.url
            except ObjectDoesNotExist as e:
                logger.debug(e)
                return None

    def get_recipient_image(self,obj):
        sender_class = self.get_recipient_type(obj)
        if sender_class == "entity":
            logo =  Logo.objects.filter(entity__slug=obj.recipient.slug).first()
            if logo:
                return logo.image.url
            else:
                return None

        if sender_class == "user":
            try:
                return UserProfileImage.objects.get(user_profile__user=obj.recipient).image.url
            except ObjectDoesNotExist as e:
                logger.debug(e)
                return None


    # def get_recipient_name(self, obj):
    #     return obj.recipient.display_name

    def get_recipient_type(self, obj):
        return obj.recipient.__class__.__name__.lower()

    def get_recipient_slug(self, obj):
        return obj.recipient.slug

    def get_entity_user_name(self,obj):
        try:
            return User.objects.get(username=obj.entity_user).display_name
        except User.DoesNotExist as e:
            logger.debug(e)
            return None


class ComposeSerializer(ICFEntityMixin, ModelSerializer):
    to_user = serializers.SlugField()
    app_type_slug = serializers.SlugField()

    class Meta:
        model = ICFMessage
        fields = ['subject', 'body', 'topic_slug', 'to_user', 'app_type_slug']
        extra_fields = ['to_user', 'app_type_slug']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(ComposeSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def create(self, validated_data):
        logger.info("Create a new message")
        entity = self.get_entity(self.context.get('entity_slug'))
        entity_type = ContentType.objects.get_for_model(entity)

        entity_user = self.context.get('user')

        to_user = User.objects.get(slug=validated_data.pop('to_user'))
        to_user_type = ContentType.objects.get_for_model(to_user)

        app_type_slug = validated_data.pop('app_type_slug')
        #type_obj = AppMessagePerm.objects.get(app_type__slug=app_type_slug)

        required_perm = AppMessagePerm.objects.get_perm_for_app(app_type_slug)

        if required_perm in get_perms(entity_user, entity):
            obj = ICFMessage.objects.create(sender_type=entity_type, sender_id=entity.id,
                                            sender_name=entity.display_name, recipient_type=to_user_type,
                                            recipient_id=to_user.id, recipient_name=to_user.display_name,
                                            entity_user=entity_user,
                                            app_type=Type.objects.get(slug=app_type_slug),
                                            **validated_data)
            obj.save()
            obj.thread_id = obj.id
            obj.save()
            obj.to_user = to_user
            obj.app_type_slug = app_type_slug
            return obj
        else:
            logger.exception("Does not have permission to compose message for entity")
            raise ICFException(_("You do not have the permissions to compose messages for this entity"), status_code=status.HTTP_403_FORBIDDEN)


class UserReplySerializer(ICFEntityMixin, ModelSerializer):
    """
    User replies to entity
    """
    recipient_slug = serializers.SlugField()

    class Meta:
        model = ICFMessage
        fields = ['body', 'recipient_slug']
        extra_fields = ['recipient_slug']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(UserReplySerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def create(self, validated_data):
        logger.info("Reply to a message")
        message_id = self.context.get('message_id')
        entity_slug = validated_data.pop('recipient_slug')
        recipient_entity = self.get_entity(entity_slug)
        entity_type = ContentType.objects.get_for_model(recipient_entity)

        sender_user = self.context.get('user')
        sender_user_type = ContentType.objects.get_for_model(sender_user)

        parent = ICFMessage.objects.get(id=message_id)

        if parent and not parent.thread_id:  # at the very first reply, make it a conversation
            parent.thread = parent
            parent.save()

        obj = ICFMessage.objects.create(sender_type=sender_user_type, sender_id=sender_user.id,
                                        sender_name=sender_user.display_name,
                                        recipient_type=entity_type, recipient_id=recipient_entity.id,
                                        recipient_name=recipient_entity.display_name,
                                        parent=parent, thread_id=parent.thread_id, subject=parent.subject,
                                        app_type=parent.app_type, **validated_data)
        obj.save()
        obj.recipient_slug = entity_slug
        return obj


class EntityReplySerializer(ICFEntityMixin, ModelSerializer):
    """
    User replies to entity
    """
    recipient_slug = serializers.SlugField()

    class Meta:
        model = ICFMessage
        fields = ['body', 'recipient_slug']
        extra_fields = ['recipient_slug']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(EntityReplySerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def create(self, validated_data):
        logger.info("Reply to a message")
        message_id = self.context.get('message_id')
        user_slug = validated_data.pop('recipient_slug')
        recipient_user = User.objects.get(slug=user_slug)
        user_type = ContentType.objects.get_for_model(recipient_user)

        sender_entity = self.get_entity(self.context.get('entity_slug'))
        entity_type = ContentType.objects.get_for_model(sender_entity)

        parent = ICFMessage.objects.get(id=message_id)

        if parent and not parent.thread_id:  # at the very first reply, make it a conversation
            parent.thread = parent
            parent.save()

        obj = ICFMessage.objects.create(sender_type=entity_type, sender_id=sender_entity.id,
                                        sender_name=sender_entity.display_name,
                                        recipient_type=user_type, recipient_id=recipient_user.id,
                                        recipient_name=recipient_user.display_name,
                                        parent=parent, thread_id=parent.thread_id, subject=parent.subject,
                                        app_type=parent.app_type, entity_user=self.context.get('user'),
                                        **validated_data)
        obj.save()
        obj.recipient_slug = user_slug
        return obj


class MessageSerializer(ModelSerializer):
    class Meta:
        model = ICFMessage
        fields = ['id']


class MessageThreadSerializer(ModelSerializer):
    class Meta:
        model = ICFMessage
        fields = ['thread_id']


class UserMessageUpdateSerializer(serializers.Serializer):
    messages = MessageSerializer(many=True)
    threads = MessageThreadSerializer(many=True)

class ICFNotificationSerializer(ModelSerializer):
    class Meta:
        model = ICFNotification
        fields = '__all__'


class ComposeAndEmailSerializer(ICFEntityMixin, ModelSerializer):
    to_user = serializers.SlugField()
    app_type_slug = serializers.SlugField()
    other_jobs = serializers.ListField(default=None)

    class Meta:
        model = ICFMessage
        fields = ['subject', 'body', 'topic_slug', 'to_user', 'app_type_slug', 'other_jobs']
        extra_fields = ['to_user', 'app_type_slug']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(ComposeAndEmailSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def create(self, validated_data):
        logger.info("Create a new message")
        entity = self.get_entity(self.context.get('entity_slug'))
        entity_type = ContentType.objects.get_for_model(entity)

        entity_user = self.context.get('user')

        to_user = User.objects.get(slug=validated_data.pop('to_user'))
        to_user_type = ContentType.objects.get_for_model(to_user)
        app_type_slug = validated_data.pop('app_type_slug')

        other_jobs = validated_data.get('other_jobs', None)   # list of job slugs
        job_slug_list = []
        if other_jobs and app_type_slug.lower() == 'job':
            job_slug_list = other_jobs
        validated_data.pop('other_jobs')   # list of job slugs

        body = validated_data.pop('body')
        protocol = 'https'

        try:
            current_site = Site.objects.get_current()
        except Exception as ex:
            logger.error("Failed to get site information: {e}".format(e=str(ex)))
            current_site = None

        body = str(app_settings.common_body).format(job_seeker_user_name=to_user.display_name, entity_name=entity.name)
        body = body + "<ul style=\"list-style: none;\">"
        job_links_str = ''
        for job_slug in job_slug_list:
            # single_job_link_str = "<li>" + protocol + "://" + current_site.domain + "/api/jobs/" + job_slug + "</li><br>"
            single_job_link_str = "<li><a href=" + protocol + "://" + current_site.domain + "/api/jobs/" + job_slug + ">" + protocol + "://" + current_site.domain + "/api/jobs/" + job_slug + "</a></li><br>"
            job_links_str = job_links_str + single_job_link_str
        email_body = body + job_links_str + "</ul>"

        message_user_name_part_1 = str(message_user_name_part).format(job_seeker_user_name=to_user.display_name)
        message_text_body_2 = str(message_text_body_part).format(entity_name=entity.name) + job_links_str + "</ul>"
        message_body = "<!DOCTYPE html><html><head><title></title></head><body>"+message_user_name_part_1+message_text_body_2+"</body></html>"

        required_perm = AppMessagePerm.objects.get_perm_for_app(app_type_slug)

        if required_perm in get_perms(entity_user, entity):
            obj = ICFMessage.objects.create(sender_type=entity_type, sender_id=entity.id,
                                            sender_name=entity.display_name, recipient_type=to_user_type,
                                            recipient_id=to_user.id, recipient_name=to_user.display_name,
                                            entity_user=entity_user,
                                            app_type=Type.objects.get(slug=app_type_slug), body=message_body,
                                            **validated_data)
            obj.save()
            obj.thread_id = obj.id
            obj.save()
            obj.to_user = to_user
            obj.app_type_slug = app_type_slug

            # send email to user
            entity_email = entity.email
            email_context = {
                'job_seeker_user_name': to_user.display_name,  # not used in template , directly coming from backend
                'job_seeker_email': to_user.email,
                'entity_email': entity_email,
                'body': email_body,
            }
            send_email_notification_to_job_seeker(email_context)

            return obj
        else:
            logger.exception("Does not have permission to compose message for entity")
            raise ICFException(_("You do not have the permissions to compose messages for this entity"), status_code=status.HTTP_403_FORBIDDEN)

#  Serializser for message attachements.
class MessageAttachmentSerializer(ModelSerializer):

    class Meta:
        model = MessageAttachmentUpload
        fields = ['attachment_src', 'id']

    def create(self, validated_data):
        user = self.context['user']
        try:
            obj = MessageAttachmentUpload.objects.get(user=user)
            obj.attachment_src = validated_data.get('attachment_src')
            obj.save()
        except ObjectDoesNotExist:
            obj = MessageAttachmentUpload.objects.create(user=user, **validated_data)
        return obj

    def update(self, instance, validated_data):
        file = validated_data.get('attachment_src')
        instance.attachment_src = file
        instance.save()
        return instance
