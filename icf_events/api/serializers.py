from datetime import datetime

import pytz
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.utils import model_meta

from icf_auth.api.serializers import UserFirstAndLastNameSerializer, UserProfileRetrieveSerializerForList
from icf_auth.models import UserProfile
from icf_events.api.mixins import ICFEntityMixin, ICFEventDraftMixin
from icf_entity.models import Logo
from icf_events.api.mixins import ICFEventMixin
from icf_events.models import Event, EventDraft, EventGallery, EventGalleryOptional, ParticipantSearch
from icf_generic.Exceptions import ICFException
from icf_generic.api.serializers import AddressRetrieveSerializer, AddressOptionalSerializer, \
    AddressOptionalRetrieveSerializer
from icf_generic.models import Address, Sponsored, Category, Type, AddressOptional
from django.utils.translation import ugettext_lazy as _

import logging

from icf_item.api.serializers import ItemCreateUpdateSerializer, ItemListSerializer, EntitySerializer, \
    ItemCreateUpdateDraftSerializer, ItemDraftListSerializer
from icf_item.models import Item, ItemUserView, ItemDraft
from icf_jobs.JobHelper import get_user_work_experience_in_seconds
from icf_jobs.api.serializers import UserJobProfileRetrieveSerializer, UserEducationRetrieveSerializer, \
    UserWorkExperienceListSerializer, UserReferenceSerializerForList, UserSkillSerializer
from icf_jobs.models import UserJobProfile, UserResume, JobProfileFileUpload, UserEducation, UserWorkExperience, \
    UserReference, UserSkill
from icf_messages.models import ICFMessage
from icf_orders.api.mixins import ICFCreditManager
from icf_orders.app_settings import CREATE_EVENT, SPONSORED_EVENT

logger = logging.getLogger(__name__)


class CategoryListSerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class EventCreateSerializer(ItemCreateUpdateSerializer):
    item_type = serializers.SerializerMethodField()
    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = Event
        exclude = ['owner']
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(EventCreateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    @transaction.atomic
    def create(self, validated_data):

        location_data = validated_data.pop("location")
        location = Address.objects.create(**location_data)

        entity = validated_data.get("entity")

        sponsored_start_dt = validated_data.pop('sponsored_start_dt')
        sponsored_end_dt = validated_data.pop('sponsored_end_dt')
        is_sponsored = validated_data.pop('is_sponsored')

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create event.\n")
            raise ICFException(_("You do not have the permissions to create events for {}".format(entity)),
                               status_code=status.HTTP_400_BAD_REQUEST)

        if request.data.get('event_draft_slug'):
            event_draft_slug = request.data.get('event_draft_slug').lstrip().rstrip()
        else:
            logger.exception("event_draft_slug not there, cannot create event.")
            raise ICFException(_("could not create event. for {}".format(entity)),
                               status_code=status.HTTP_400_BAD_REQUEST)

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('expiry')
        category = validated_data.get('category')
        try:
            type_obj = Type.objects.get(slug='event')
            category_obj = Category.objects.get(name=category.name, type=type_obj)
        except Type.DoesNotExist as tdn:
            logger.exception("Invalid category type for event.\n")
            raise ICFException(_("Invalid category type for event, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except Category.DoesNotExist as tdn:
            logger.exception("category object not found for event.\n")
            raise ICFException(_("Invalid category type for event, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        is_allowed_interval = ICFCreditManager.is_allowed_interval(start_date, end_date)
        if not is_allowed_interval:
            logger.exception("Invalid duration for posting the event."
                             "The event's start date should be between {X} and {Y}.\n".format(X=str(datetime.now(pytz.utc).date()), Y=str(end_date.date())))
            raise ICFException(_("The event's start date should be between {X} and {Y}.".format(X=str(datetime.now(pytz.utc).date()), Y=str(end_date.date()))),
                               status_code=status.HTTP_400_BAD_REQUEST)

        event = Event.objects.create(owner=user, location=location, **validated_data)

        # get the event draft object using 'event_draft_slug'
        # get the Gallery for draft event (EventGalleryOptional)
        # create the EventGallery(main Event)  for the created event by using EventGalleryOptional fields
        # finally delete the EventDraft object

        try:
            event_draft_obj = ItemDraft.objects.get(slug=event_draft_slug)
        except ItemDraft.DoesNotExist as edne:
            logger.exception(str(edne))
            raise
        try:
            event_draft_gallery_list = EventGalleryOptional.objects.filter(event=event_draft_obj, entity=entity)
            for event_draft_gallery_obj in event_draft_gallery_list:
                EventGallery.objects.create(event=event, entity=entity, event_slug=event.slug,
                                        image=event_draft_gallery_obj.image,
                                        image_type=event_draft_gallery_obj.image_type)
            event_draft_obj.delete()
        # except EventGalleryOptional.DoesNotExist as edne:
        #     event_draft_obj.delete()
        except Exception as e:
            logger.exception(str(e))
            raise

        # event_model = ContentType.objects.get_for_model(event)

        # if event.status == Item.ITEM_ACTIVE:
        #     ICFCreditManager.manage_entity_subscription(entity=entity, action=CREATE_EVENT, item_start_date=start_date,
        #                                                 item_end_date=end_date,
        #                                                 user=user, app=event_model)
        #
        #     if is_sponsored:
        #
        #         if not sponsored_start_dt or not sponsored_end_dt:
        #             logger.exception("Invalid duration for sponsoring the event")
        #             raise ICFException(_(
        #                 "The minimum duration for sponsoring a event is X days and "
        #                 "the maximum duration of sponsoring a event is Y days. Please check and try again."),
        #                                status_code=status.HTTP_400_BAD_REQUEST)
        #
        #         # A event can be sponsored anywhere during the period when the event is active.
        #         if sponsored_start_dt >= event.start_date and sponsored_end_dt <= event.expiry:
        #             intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
        #                                                               SPONSORED_EVENT)
        #             Sponsored.objects.create(content_object=event, start_date=sponsored_start_dt,
        #                                      end_date=sponsored_end_dt)
        #             ICFCreditManager.charge_for_action(user=user, entity=entity, app=event_model, action=SPONSORED_EVENT,
        #                                                intervals=intervals)
        #             event.is_sponsored = True
        #             event.sponsored_start_dt = sponsored_start_dt
        #             event.sponsored_end_dt = sponsored_end_dt
        #         else:
        #             logger.exception("Invalid duration for sponsoring the event.")
        #             raise ICFException(_(
        #                 "The minimum duration for sponsoring a event is X days and"
        #                 " the maximum duration of sponsoring a event is Y days. Please check and try again."),
        #                                status_code=status.HTTP_400_BAD_REQUEST)
        #
        #     #
        #     # Add teh sponsored information to tbe event object to be serialized.
        #     # The sponsored information is added to the event object even though the information
        #     # is not part of the Event model.
        #     #

        logger.info("Event created {}.".format(event))
        return event

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None


class EventListSerializer(ItemListSerializer):

    class Meta(ItemListSerializer.Meta):
        model = Event
        fields = ItemListSerializer.Meta.fields + ('registration_website', 'contact_email', 'contact_no',)


class EntityEventListSerializer(ItemListSerializer):
    is_sponsored_event = serializers.SerializerMethodField()
    no_of_views = serializers.SerializerMethodField()
    # no_of_applied_user = serializers.SerializerMethodField()

    class Meta(ItemListSerializer.Meta):
        model = Event
        fields = ItemListSerializer.Meta.fields + ('registration_website', 'contact_email', 'contact_no', 'entity',  'is_sponsored_event', 'no_of_views')

    def get_is_sponsored_event(self, obj):
        try:
            content_type = ContentType.objects.get(model='event')
            sponsored_event = Sponsored.objects.get(object_id=obj.id, content_type=content_type.id, status=Sponsored.SPONSORED_ACTIVE)
            if sponsored_event:
                return True
            else:
                return False
        except Sponsored.DoesNotExist as e:
            logger.debug(e)
            return False

    def get_no_of_views(self,obj):
        # number of user viewed
        view_count = ItemUserView.objects.filter(item=obj)
        return view_count.count()


class EventRetrieveSerializer(ModelSerializer):
    location = AddressRetrieveSerializer()
    item_type = serializers.SerializerMethodField()
    entity = EntitySerializer()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry = serializers.DateTimeField(format='%B %d, %Y')
    category = serializers.StringRelatedField()
    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = Event
        # exclude = ['owner', ]
        fields = (
            'id',
            'title',
            'entity',
            'category',
            'item_type',
            'description',
            'location',
            'status',
            'expiry',
            'slug',
            'start_date',
            'registration_website',
            'contact_email',
            'contact_no',
            'daily_start_time',
            'daily_end_time',
            'hero_image',
            'gallery_images',
            'created',
            'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None

    def get_hero_image(self, obj):
        try:
            return EventGallery.objects.get(event=obj, image_type=EventGallery.HERO).image.url
        except ObjectDoesNotExist:
            return None

    def get_gallery_images(self, obj):
        gallery_image_list = []
        gallery_image_dict = {}
        event_gallery_list = EventGallery.objects.filter(event=obj, image_type=EventGallery.GALLERY).order_by('created')
        index = 0
        for event_gallery in event_gallery_list:
            key_index = 'gallery_image_'+str(index)
            gallery_image_dict[key_index] = event_gallery.image.url
            gallery_image_list.append(gallery_image_dict)
            index = index + 1
        return gallery_image_list


class EventRetrieveUpdateSerializer(ItemCreateUpdateSerializer):
    item_type = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    entity = serializers.StringRelatedField()

    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = Event
        exclude = ['owner', ]
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(EventRetrieveUpdateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    @transaction.atomic
    def update(self, instance, validated_data):

        event_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create event.\n")
            raise ICFException("Unknown user, cannot create event.", status_code=status.HTTP_400_BAD_REQUEST)

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            location, address_created = Address.objects.update_or_create(userprofile=instance, **location_data)
            instance.location = location

        prev_event_status = instance.status
        prev_start_date = instance.start_date
        prev_end_date = instance.expiry

        current_status = validated_data.get('status')
        curr_start_date = validated_data.get('start_date')
        curr_end_date = validated_data.get('expiry')

        is_sponsored = validated_data.get('is_sponsored')
        sponsored_start_dt = validated_data.get('sponsored_start_dt')
        sponsored_end_dt = validated_data.get('sponsored_end_dt')

        ########################################
        # Getting published for the first time
        ########################################
        if prev_event_status != current_status and current_status == Item.ITEM_ACTIVE:
            logger.info("Publishing the event first time : {}".format(instance.slug))
            is_allowed_interval = ICFCreditManager.is_allowed_interval(curr_start_date, curr_end_date)
            if not is_allowed_interval:
                logger.exception("Invalid duration for posting the event."
                                 "The event's start date should be between {X} and {Y}.\n".
                                 format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                raise ICFException(_("The event's start date should be between {X} and {Y}.".format(X=str(datetime.now(pytz.utc).date()),
                                                                                   Y=str(curr_end_date.date()))),
                                   status_code=status.HTTP_400_BAD_REQUEST)
            # intervals = ICFCreditManager.get_num_of_intervals(curr_start_date, curr_end_date, 'create_event')
            # ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=event_model,
            # action='create_event', intervals=intervals)

            ICFCreditManager.manage_entity_subscription(entity=instance.entity, action=CREATE_EVENT,
                                                        item_start_date=curr_start_date, item_end_date=curr_end_date,
                                                        user=user, app=event_model)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid duration for sponsoring the event.\n")
                    raise ICFException(_("Please provide the event's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # A event can be sponsored anywhere during the period when the event is active.
                if sponsored_start_dt >= curr_start_date and sponsored_end_dt <= curr_end_date:
                    intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt, SPONSORED_EVENT)
                    Sponsored.objects.create(content_object=instance,
                                             start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                    ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=event_model,
                                                       action=SPONSORED_EVENT, intervals=intervals)
                    instance.is_sponsored = True
                    instance.sponsored_start_dt = sponsored_start_dt
                    instance.sponsored_end_dt = sponsored_end_dt
                else:
                    logger.exception("Duration for sponsoring event not within the event posting duration.\n")
                    raise ICFException(_("Event can be sponsored from {X} till {Y}. "
                                         "Choose valid sponsored start date and end date.".
                                         format(X=str(curr_start_date.date()), Y=str(curr_end_date.date()))),
                        status_code=status.HTTP_400_BAD_REQUEST)

        ######################################
        # Updating an already published event
        ######################################
        if prev_event_status == current_status and current_status == Item.ITEM_ACTIVE:
            logger.info("Updating a published event : {}".format(instance.slug))

            if prev_start_date != curr_start_date:
                if prev_start_date.date() < datetime.now(pytz.utc).date():
                    logger.exception("Cannot change start date for an active and published event.\n")
                    raise ICFException(_("You cannot change the start date for an active and published event."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                elif curr_start_date.date() < datetime.now(pytz.utc).date():
                    logger.exception("Invalid start date. The start date cannot be before {X}.\n"
                                     .format(X=datetime.now(pytz.utc).date()))
                    raise ICFException(_("The start date cannot be before {X}.".format(X=str(datetime.now(pytz.utc).date()))),
                                       status_code=status.HTTP_400_BAD_REQUEST)

            if curr_end_date.date() < datetime.now(pytz.utc).date():
                logger.exception("Invalid end date. The end date cannot be before {X}.\n"
                                 .format(X=datetime.now(pytz.utc).date()))
                raise ICFException(_("The end date cannot be before {X}.".format(X=str(datetime.now(pytz.utc).date()))),
                                   status_code=status.HTTP_400_BAD_REQUEST)

            # Charge for the difference in duration.
            intervals = ICFCreditManager.change_to_interval(prev_start_date, prev_end_date, curr_start_date,
                                                            curr_end_date, action=CREATE_EVENT)
            if intervals:
                # ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=event_model,
                #                                    action=CREATE_EVENT, intervals=intervals)

                ICFCreditManager.manage_entity_subscription(entity=instance.entity, action=CREATE_EVENT,
                                                            item_start_date=curr_start_date,
                                                            item_end_date=curr_end_date,
                                                            user=user, app=event_model)

            if is_sponsored:

                if not sponsored_start_dt or not sponsored_end_dt:
                    logger.exception("Invalid values for sponsoring the event.\n")
                    raise ICFException(_("Please provide event's sponsored start date and sponsored end date."),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                # Check if the event was already sponsored before
                try:

                    # The event was already sponsored. Charge for the difference if any in the duration.
                    sponsored = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_ACTIVE)

                    prev_sponsored_start_date = sponsored.start_date
                    prev_sponsored_end_date = sponsored.end_date

                    if prev_sponsored_start_date != sponsored_start_dt:
                        if prev_sponsored_start_date < datetime.now(pytz.utc):
                            logger.exception("Cannot change start date of an already sponsored event.\n")
                            raise ICFException(
                                _("You cannot change the start date of an ongoing sponsored event campaign."),
                                status_code=status.HTTP_400_BAD_REQUEST)
                        elif sponsored_start_dt < datetime.now(pytz.utc) or \
                                sponsored_start_dt > curr_end_date:
                            logger.exception("Invalid start date for sponsoring the event."
                                             "The Sponsored event start date should be between {X} and {Y}.\n".
                                             format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                            raise ICFException(_("The Sponsored event start date should be between {X} and {Y}".
                                             format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date()))),
                                status_code=status.HTTP_400_BAD_REQUEST)

                    if sponsored_end_dt < datetime.now(pytz.utc) or \
                            sponsored_end_dt > curr_end_date:
                        logger.exception("Invalid end date for sponsoring the event."
                                         "The Sponsored event end date should be between {X} and {Y}.\n".
                                         format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date())))
                        raise ICFException(_("The Sponsored event end date should be between {X} and {Y}".
                                             format(X=str(datetime.now(pytz.utc).date()), Y=str(curr_end_date.date()))),
                                           status_code=status.HTTP_400_BAD_REQUEST)

                    sponsored.start_date = sponsored_start_dt
                    sponsored.end_date = sponsored_end_dt
                    sponsored.status = Sponsored.SPONSORED_ACTIVE
                    sponsored.save(update_fields=['start_date', 'end_date', 'status'])
                    # Charge for the difference in duration.
                    intervals = ICFCreditManager.change_to_interval(prev_sponsored_start_date,
                                                                    prev_sponsored_end_date, sponsored_start_dt,
                                                                    sponsored_end_dt, action=SPONSORED_EVENT)
                    if intervals:
                        ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=event_model,
                                                           action=SPONSORED_EVENT, intervals=intervals)

                except Sponsored.DoesNotExist:
                    #to check whether event is alredy sponsored and inactive
                    try:
                        pre_sponsored = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_INACTIVE)
                        #delete to avoid redudant row in table
                        pre_sponsored.delete()
                    except ObjectDoesNotExist:
                        pass

                    # Event sponsored first time during this update, did not exist earlier

                    if sponsored_start_dt >= curr_start_date and sponsored_end_dt <= curr_end_date:
                        intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
                                                                          SPONSORED_EVENT)
                        Sponsored.objects.create(content_object=instance,
                                                 start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                        ICFCreditManager.charge_for_action(user=user, entity=instance.entity, app=event_model,
                                                           action='SPONSORED_EVENT',
                                                           intervals=intervals)
                        instance.is_sponsored = True
                        instance.sponsored_start_dt = sponsored_start_dt
                        instance.sponsored_end_dt = sponsored_end_dt
                    else:
                        logger.exception("Duration for sponsoring event not within the event posting duration.\n")
                        raise ICFException(_("The start date of your sponsored event campaign cannot be before {X} "
                                             "and the end date cannot be after {Y}."
                                             .format(X=str(curr_start_date.date()), Y=str(curr_end_date.date()))),
                            status_code=status.HTTP_400_BAD_REQUEST)

            else:
                # Check if an earlier sponsored event has been removed
                try:
                    sponsored = Sponsored.objects.get(object_id=instance.id)
                    sponsored.status = Sponsored.SPONSORED_INACTIVE
                    sponsored.save(update_fields=["status"])
                except Sponsored.DoesNotExist:
                    pass

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None


class EventDraftRetrieveSerializer(ModelSerializer):
    location = AddressOptionalSerializer()
    item_type = serializers.SerializerMethodField()
    entity = EntitySerializer()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry = serializers.DateTimeField(format='%B %d, %Y')
    category = serializers.StringRelatedField()
    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = EventDraft
        fields = (
            'id',
            'title',
            'entity',
            'category',
            'item_type',
            'description',
            'location',
            'status',
            'expiry',
            'slug',
            'start_date',
            'registration_website',
            'contact_email',
            'contact_no',
            'daily_start_time',
            'daily_end_time',
            'hero_image',
            'gallery_images',
            'created',
            'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None

    def get_hero_image(self, obj):
        try:
            return EventGalleryOptional.objects.get(event=obj, image_type=EventGalleryOptional.HERO).image.url
        except ObjectDoesNotExist:
            return None

    def get_gallery_images(self, obj):
        gallery_image_list = []
        gallery_image_dict = {}
        event_gallery_list = EventGalleryOptional.objects.filter(event=obj,
                             image_type=EventGalleryOptional.GALLERY).order_by('created')
        index = 0
        for event_gallery in event_gallery_list:
            key_index = 'gallery_image_' + str(index)
            gallery_image_dict[key_index] = event_gallery.image.url
            gallery_image_list.append(gallery_image_dict)
            index = index + 1
        return gallery_image_list


class EventCreateDraftSerializer(ItemCreateUpdateDraftSerializer):
    item_type = serializers.SerializerMethodField()
    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = EventDraft
        exclude = ['owner', ]

    def create(self, validated_data):

        location_data = validated_data.pop("location")
        location = AddressOptional.objects.create(**location_data)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create event.\n")
            raise ICFException(_("Unknown user, cannot create event."), status_code=status.HTTP_400_BAD_REQUEST)

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('expiry')

        category = validated_data.get('category')
        if category:
            try:
                type_obj = Type.objects.get(slug='event')
                category_obj = Category.objects.get(name=category.name, type=type_obj)
            except Type.DoesNotExist as tdn:
                logger.exception("Invalid category type for event.\n")
                raise ICFException(_("Invalid category type for event, please check and try again."),
                                   status_code=status.HTTP_400_BAD_REQUEST)
            except Category.DoesNotExist as tdn:
                logger.exception("category object not found for event.\n")
                raise ICFException(_("Invalid category type for event, please check and try again."),
                                   status_code=status.HTTP_400_BAD_REQUEST)
        else:
            category = None

        event = EventDraft.objects.create(owner=user, location=location, **validated_data)

        event_model = ContentType.objects.get_for_model(event)

        logger.info("Event created {}.".format(event))
        return event

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None


class EventCreateDraftCloneSerializer(ItemCreateUpdateDraftSerializer):
    slug = serializers.CharField(read_only=True)

    # is_sponsored = serializers.BooleanField(default=False)
    # sponsored_start_dt = serializers.DateTimeField(default=None)
    # sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = EventDraft
        fields = ['slug', ]

    def create(self, validated_data):

        logger.info("Create event draft for event clone \n")
        event_slug = self.context['event_slug']

        if not event_slug:
            logger.exception("Cannot clone event because invalid event slug.\n")
            raise ICFException(_("Cannot clone event, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        try:
            event = Event.objects.get(slug=event_slug)
        except Event.DoesNotExist as edne:
            logger.exception("Cannot clone event because Event not found.\n")
            raise ICFException(_("Cannot clone event, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        # location_data = validated_data.pop("location")
        # location = AddressOptional.objects.create(**location_data)

        location_obj = event.location
        location = AddressOptional.objects.create(address_1=location_obj.address_1,
                                                  address_2=location_obj.address_2, city=location_obj.city)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create event.\n")
            raise ICFException(_("Unknown user, cannot create event."), status_code=status.HTTP_400_BAD_REQUEST)

        category = event.category
        if category:
            try:
                type_obj = Type.objects.get(slug='event')
                category_obj = Category.objects.get(name=category.name, type=type_obj)
            except Type.DoesNotExist as tdn:
                logger.exception("Invalid category type for event.\n")
                raise ICFException(_("Invalid category type for event, please check and try again."),
                                   status_code=status.HTTP_400_BAD_REQUEST)
            except Category.DoesNotExist as tdn:
                logger.exception("category object not found for event.\n")
                raise ICFException(_("Invalid category type for event, please check and try again."),
                                   status_code=status.HTTP_400_BAD_REQUEST)
        else:
            category = None

        event_draft = EventDraft.objects.create(owner=user, location=location, title=event.title,
                                                entity=event.entity, category=event.category,
                                                start_date=event.start_date, expiry=event.expiry,
                                                item_type=event.item_type, description=event.description,
                                                registration_website=event.registration_website,
                                                contact_email=event.contact_email, contact_no=event.contact_no,
                                                daily_start_time=event.daily_start_time,
                                                daily_end_time=event.daily_end_time,
                                                status=EventDraft.ITEM_DRAFT
                                                )

        event_gallery_list = EventGallery.objects.filter(event=event, entity=event.entity)
        for event_gallery_obj in event_gallery_list:
            EventGalleryOptional.objects.create(event=event_draft, entity=event_draft.entity, event_slug=event_draft.slug,
                                        image=event_gallery_obj.image,
                                        image_type=event_gallery_obj.image_type)

        # event_model = ContentType.objects.get_for_model(event)

        logger.info("Event created {}.".format(event_draft))
        return event_draft

    # def get_item_type(self, obj):
    #     try:
    #         item_type = obj.item_type
    #         return item_type.id
    #     except Exception as e:
    #         logger.exception(e)
    #         return None


class EventDraftListSerializer(ItemDraftListSerializer):

    class Meta(ItemDraftListSerializer.Meta):
        model = EventDraft
        fields = ItemDraftListSerializer.Meta.fields + ('registration_website', 'contact_email',
            'entity', 'contact_no')


class EventDraftRetrieveUpdateSerializer(ItemCreateUpdateDraftSerializer):
    item_type = serializers.SerializerMethodField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    entity = serializers.StringRelatedField()

    class Meta:
        model = EventDraft
        exclude = ['owner', ]

    def update(self, instance, validated_data):
        event_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            logger.exception("Unknown user, cannot create draft event.\n")
            raise ICFException(_("Unknown user, cannot create draft event."), status_code=status.HTTP_400_BAD_REQUEST)

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            location, address_created = AddressOptional.objects.update_or_create(**location_data)
            instance.location = location

        info = model_meta.get_field_info(instance)
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        return instance

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.debug(e)
            return None

    def get_entity_logo(self, obj):
        try:
            return Logo.objects.get(entity=obj.entity).image.url
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None


class EventGallerySerializer(ICFEntityMixin, ICFEventMixin, ModelSerializer):
    image_type_name = serializers.SerializerMethodField()

    class Meta:
        model = EventGallery
        # fields = '__all__'
        exclude = ['event_slug', 'event', 'entity']

    def create(self, validated_data):
        logger.info("Upload image for the event")
        entity = self.get_entity(self.context['entity_slug'])
        event = self.get_event(self.context['slug'])

        try:
            image_type = validated_data.get('image_type')
            if image_type == EventGallery.HERO:
                obj = EventGallery.objects.get(entity=entity, event=event, event_slug=event.slug, image_type=image_type)
                obj.image = validated_data.get('image')
                obj.save(update_fields=['image'])
                return obj
            else:
                image = validated_data.pop('image')
                image_type = validated_data.pop('image_type')
                obj = EventGallery.objects.create(entity=entity, event=event, event_slug=event.slug,
                                                  image=image, image_type=image_type)
                return obj
        except ObjectDoesNotExist:
            image = validated_data.pop('image')
            image_type = validated_data.pop('image_type')
            obj = EventGallery.objects.create(entity=entity, event=event, event_slug=event.slug,
                                              image=image, image_type=image_type)
            return obj

    def get_image_type_name(self, obj):
        return EventGallery.get_image_types().get(obj.image_type)

    # def update(self, instance, validated_data):
    #     logger.info("Update event gallery for the event.")
    #     instance.image = validated_data.get('image')
    #     instance.image_type = validated_data.get('image_type')
    #     instance.save()
    #     return instance


class EventDraftGallerySerializer(ICFEntityMixin, ICFEventDraftMixin, ModelSerializer):

    class Meta:
        model = EventGalleryOptional
        # fields = '__all__'
        exclude = ['event_slug', 'event', 'entity']

    def create(self, validated_data):
        logger.info("Upload image for the event draft")
        entity = self.get_entity(self.context['entity_slug'])
        event = self.get_draft_event(self.context['slug'])

        try:
            image_type = validated_data.get('image_type')
            if image_type == EventGalleryOptional.HERO:
                obj = EventGalleryOptional.objects.get(entity=entity, event=event, event_slug=event.slug, image_type=image_type)
                obj.image = validated_data.get('image')
                obj.save(update_fields=['image'])
                return obj
            else:
                image = validated_data.pop('image')
                image_type = validated_data.pop('image_type')
                obj = EventGalleryOptional.objects.create(entity=entity, event=event, event_slug=event.slug,
                                                  image=image, image_type=image_type)
                return obj
        except ObjectDoesNotExist:
            image = validated_data.pop('image')
            image_type = validated_data.pop('image_type')
            obj = EventGalleryOptional.objects.create(entity=entity, event=event, event_slug=event.slug,
                                              image=image, image_type=image_type)
            return obj

    def get_image_type_name(self, obj):
        return EventGalleryOptional.get_image_types().get(obj.image_type)

    # def update(self, instance, validated_data):
    #     logger.info("Update event gallery for the event.")
    #     instance.image = validated_data.get('image')
    #     instance.image_type = validated_data.get('image_type')
    #     instance.save()
    #     return instance


class UpcomingOrPastEventSerializer(ModelSerializer):
    location = AddressRetrieveSerializer()
    item_type = serializers.SerializerMethodField()
    entity = EntitySerializer()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry = serializers.DateTimeField(format='%B %d, %Y')
    category = serializers.StringRelatedField()
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Event
        # fields = '__all__'
        fields = (
                'id',
                'title',
                'entity',
                'category',
                'item_type',
                'description',
                'location',
                'status',
                'expiry',
                'slug',
                'start_date',
                'registration_website',
                'contact_email',
                'contact_no',
                'daily_start_time',
                'daily_end_time',
                'hero_image',
                'created',
                'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except Exception as e:
            logger.exception(e)
            return None

    def get_hero_image(self, obj):
        try:
            return EventGallery.objects.filter(event=obj, image_type=EventGallery.HERO).last().image.url
        except EventGallery.DoesNotExist:
            return None
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            logger.exception(e)
            return None


class EventDraftPreviewRetrieveSerializer(ModelSerializer):
    location = AddressOptionalRetrieveSerializer()
    item_type = serializers.SerializerMethodField()
    entity = EntitySerializer()
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    # expiry = serializers.DateTimeField(format='%B %d, %Y')
    category = serializers.StringRelatedField()
    hero_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = EventDraft
        fields = (
            'id',
            'title',
            'entity',
            'category',
            'item_type',
            'description',
            'location',
            'status',
            'expiry',
            'slug',
            'start_date',
            'registration_website',
            'contact_email',
            'contact_no',
            'daily_start_time',
            'daily_end_time',
            'hero_image',
            'gallery_images',
            'created',
            'updated')

    def get_item_type(self, obj):
        try:
            item_type = obj.item_type
            return item_type.id
        except:
            return None

    def get_hero_image(self, obj):
        try:
            return EventGalleryOptional.objects.get(event=obj, image_type=EventGalleryOptional.HERO).image.url
        except ObjectDoesNotExist:
            return None

    def get_gallery_images(self, obj):
        gallery_image_list = []
        gallery_image_dict = {}
        event_gallery_list = EventGalleryOptional.objects.filter(event=obj,
                                                                 image_type=EventGalleryOptional.GALLERY).order_by(
            'created')
        index = 0
        for event_gallery in event_gallery_list:
            key_index = 'gallery_image_' + str(index)
            gallery_image_dict[key_index] = event_gallery.image.url
            gallery_image_list.append(gallery_image_dict)
            index = index + 1
        return gallery_image_list



class ParticipantSearchCreateSerializer(ModelSerializer):
    location = serializers.ListField(allow_null=True)
    education_level = serializers.ListField(allow_null=True)
    key_skill = serializers.ListField(allow_null=True)
    computer_skill = serializers.ListField(allow_null=True)
    language_skill = serializers.ListField(allow_null=True)
    recruiter = serializers.SerializerMethodField(read_only=True)
    slug = serializers.CharField(read_only=True)
    entity_slug = serializers.CharField(read_only=True)

    class Meta:
        model = ParticipantSearch
        fields = '__all__'

    def create(self, validated_data):
        try:
            entity_slug = self.context.get('entity_slug')
            user = self.context.get("user")
            name = self.validated_data.pop('name')
            job_title = self.validated_data.pop('job_title', None)
            work_experience = self.validated_data.get('work_experience', None)
            work_experience = self.validated_data.pop('work_experience')

            if work_experience:
                work_experience = int(work_experience)
            location_id_list = validated_data.get('location', None)
            validated_data.pop('location')
            education_level_id_list = validated_data.get('education_level', None)
            validated_data.pop('education_level')
            key_skill_id_list = validated_data.get('key_skill', None)
            validated_data.pop('key_skill')
            computer_skill_id_list = validated_data.get('computer_skill', None)
            validated_data.pop('computer_skill')
            language_skill_id_list = validated_data.get('language_skill', None)
            validated_data.pop('language_skill')

            location_id_string = ''
            if location_id_list:
                location_converted_list = [str(element) for element in location_id_list]
                location_id_string = ",".join(location_converted_list)
            # print(location_id_string)

            education_level_id_string = ''
            if education_level_id_list:
                education_converted_list = [str(element) for element in education_level_id_list]
                education_level_id_string = ",".join(education_converted_list)
            # print(education_level_id_string)

            key_skill_id_string = ''
            if key_skill_id_list:
                key_skill_converted_list = [str(element) for element in key_skill_id_list]
                key_skill_id_string = ",".join(key_skill_converted_list)
            # print(key_skill_id_string)

            computer_skill_id_string = ''
            if computer_skill_id_list:
                computer_skill_converted_list = [str(element) for element in computer_skill_id_list]
                computer_skill_id_string = ",".join(computer_skill_converted_list)
            # print(computer_skill_id_string)

            language_skill_id_string = ''
            if language_skill_id_list:
                language_skill_converted_list = [str(element) for element in language_skill_id_list]
                language_skill_id_string = ",".join(language_skill_converted_list)
            # print(language_skill_id_string)

            candidate_search_obj = ParticipantSearch.objects.create(name=name, entity_slug=entity_slug, recruiter=user, location=location_id_string,
                                                                  work_experience=work_experience, education_level=education_level_id_string,
                                                                  key_skill=key_skill_id_string, computer_skill=computer_skill_id_string,
                                                                  language_skill=language_skill_id_string, job_title=job_title
                                                                  )
            return candidate_search_obj

        except ValueError as ve:
            logger.exception("Cannot cast the value to integer.")
            raise ICFException(_("Something went wrong.Please contact administrator."), status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(_("Something went wrong.Please contact administrator.", status_code=status.HTTP_400_BAD_REQUEST))

    def get_recruiter(self, obj):
        if obj.recruiter:
            return UserFirstAndLastNameSerializer(obj.recruiter).data
        else:
            return None


class ParticipantSearchListSerializer(ModelSerializer):
    recruiter = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ParticipantSearch
        fields = '__all__'

    def get_recruiter(self, obj):
        if obj.recruiter:
            return UserFirstAndLastNameSerializer(obj.recruiter).data
        else:
            return None


class ParticipantSearchRetrieveUpdateSerializer(ModelSerializer):
    location = serializers.ListField(allow_null=True)
    education_level = serializers.ListField(allow_null=True)
    key_skill = serializers.ListField(allow_null=True)
    computer_skill = serializers.ListField(allow_null=True)
    language_skill = serializers.ListField(allow_null=True)
    recruiter = serializers.SerializerMethodField(read_only=True)
    # entity_slug = serializers.CharField(read_only=True)

    class Meta:
        model = ParticipantSearch
        exclude = ['slug', 'entity_slug']

    def update(self, instance, validated_data):
        try:
            search_slug = self.context.get('view').kwargs.get('search_slug')
            user = self.context.get("request").user
            # name = self.validated_data.pop('name')
            name = instance.name
            job_title = self.validated_data.pop('job_title', None)
            # entity_slug = self.validated_data.get('entity_slug', None)
            # entity_slug = self.validated_data.pop('entity_slug')
            work_experience = self.validated_data.get('work_experience', None)
            work_experience = self.validated_data.pop('work_experience')

            if work_experience:
                work_experience = int(work_experience)
            location_id_list = validated_data.get('location', None)
            validated_data.pop('location')
            education_level_id_list = validated_data.get('education_level', None)
            validated_data.pop('education_level')
            key_skill_id_list = validated_data.get('key_skill', None)
            validated_data.pop('key_skill')
            computer_skill_id_list = validated_data.get('computer_skill', None)
            validated_data.pop('computer_skill')
            language_skill_id_list = validated_data.get('language_skill', None)
            validated_data.pop('language_skill')

            location_id_string = ''
            if location_id_list:
                location_converted_list = [str(element) for element in location_id_list]
                location_id_string = ",".join(location_converted_list)
            # print(location_id_string)

            education_level_id_string = ''
            if education_level_id_list:
                education_converted_list = [str(element) for element in education_level_id_list]
                education_level_id_string = ",".join(education_converted_list)
            # print(education_level_id_string)

            key_skill_id_string = ''
            if key_skill_id_list:
                key_skill_converted_list = [str(element) for element in key_skill_id_list]
                key_skill_id_string = ",".join(key_skill_converted_list)
            # print(key_skill_id_string)

            computer_skill_id_string = ''
            if computer_skill_id_list:
                computer_skill_converted_list = [str(element) for element in computer_skill_id_list]
                computer_skill_id_string = ",".join(computer_skill_converted_list)
            # print(computer_skill_id_string)

            language_skill_id_string = ''
            if language_skill_id_list:
                language_skill_converted_list = [str(element) for element in language_skill_id_list]
                language_skill_id_string = ",".join(language_skill_converted_list)
            # print(language_skill_id_string)

            # candidate_search_obj = ParticipantSearch.objects.get(slug=search_slug)
            instance.name = name
            # instance.entity_slug = entity_slug
            instance.recruiter = user
            instance.location=location_id_string
            instance.work_experience = work_experience
            instance.education_level = education_level_id_string
            instance.key_skill = key_skill_id_string
            instance.computer_skill = computer_skill_id_string
            instance.language_skill = language_skill_id_string
            instance.job_title = job_title
            instance.save(update_fields=['name', 'recruiter', 'location',
                                                                  'work_experience','education_level',
                                                                  'key_skill', 'computer_skill',
                                                                  'language_skill', 'job_title'])
            return instance
        except ParticipantSearch.DoesNotExist as e:
            logger.exception("ParticipantSearch object not found.")
            raise ICFException(_("Something went wrong.Please contact administrator."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.exception("Cannot cast the value to integer.")
            raise ICFException(_("Something went wrong.Please contact administrator."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Something went wrong, reason:{reason}".format(reason=str(e)))
            raise ICFException(
                _("Something went wrong.Please contact administrator.", status_code=status.HTTP_400_BAD_REQUEST))

    def get_recruiter(self, obj):
        if obj.recruiter:
            return UserFirstAndLastNameSerializer(obj.recruiter).data
        else:
            return None


class ParticipantSearchUserJobProfileSerializer(ModelSerializer):
    resume_url = serializers.SerializerMethodField()
    user_profile = serializers.SerializerMethodField()
    job_profile = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    user_slug = serializers.SerializerMethodField()
    user_last_work_experience = serializers.SerializerMethodField()
    user_total_experience = serializers.SerializerMethodField()
    is_job_invitation_sent = serializers.SerializerMethodField()

    class Meta:
        model = UserJobProfile
        fields = '__all__'

    def get_user_profile(self, obj):
        try:
            # message = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION')
            # details_msg = settings.ICF_NOTIFICATION_SETTINGS.get('JOB_SEEKER_NOTIFICATION_DETAIL')
            # details = details_msg.format(obj.job.entity)
            # try:
            #     ICFNotificationManager.objects.get(user=obj.user, details=details)
            # except Exception:
            #     ICFNotificationManager.add_notification(user=obj.user, message=message, details=details)

            return UserProfileRetrieveSerializerForList(UserProfile.objects.get(user=obj.user)).data
        except UserProfile.DoesNotExist:
            logger.exception("User profile does not exist for {}".format(obj.user.email))
            return None

    def get_user_slug(self, obj):
        return obj.user.slug

    def get_resume_url(self, obj):
        try:
            if obj.resume:
                try:
                    user_resume = UserResume.objects.get(id=obj.resume.id)
                    if user_resume.resume:
                        return user_resume.resume.url
                    else:
                        try:
                            job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                            if job_profile_file_upload:
                                if job_profile_file_upload.resume_src:
                                    return job_profile_file_upload.resume_src.url
                                else:
                                    return None
                            else:
                                return None

                        except JobProfileFileUpload.DoesNotExist as jpfe:
                            logger.debug(str(jpfe))
                            return None
                except UserResume.DoesNotExist as urdne:
                    logger.debug(str(urdne))
                    try:
                        job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                        if job_profile_file_upload:
                            if job_profile_file_upload.resume_src:
                                return job_profile_file_upload.resume_src.url
                            else:
                                return None
                        else:
                            return None

                    except JobProfileFileUpload.DoesNotExist as jpfe:
                        logger.debug(str(jpfe))
                        return None
                except Exception as e:
                    logger.exception(str(e))
                    raise ICFException(_("Something went wrong, please contact admin."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
        except AttributeError as ae:
            # checks if user has default resume that is in JobProfileFileUpload table
            # if user did not upload default resume it returns None
            try:
                job_profile_file_upload = JobProfileFileUpload.objects.get(user=obj.user)
                if job_profile_file_upload:
                    if job_profile_file_upload.resume_src:
                        return job_profile_file_upload.resume_src.url
                    else:
                        return None
                else:
                    return None
            except JobProfileFileUpload.DoesNotExist as jpfe:
                logger.debug(str(jpfe))
                return None
        except Exception as e:
            logger.exception(str(e))
            raise ICFException(_("Something went wrong, please contact admin."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    def get_job_profile(self, obj):
        try:
            return UserJobProfileRetrieveSerializer(UserJobProfile.objects.get(user=obj.user)).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None

    def get_education(self, obj):
        try:
            return UserEducationRetrieveSerializer(UserEducation.objects.filter(job_profile__user=obj.user),
                                                   many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for education")
            return None

    def get_experience(self, obj):
        try:
            return UserWorkExperienceListSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),
                                                    many=True).data
            # return UserWorkExperienceSerializer(UserWorkExperience.objects.filter(job_profile__user=obj.user),
            #                                     many=True).data
        except ValueError as ve:
            logger.exception("Error in getting a value for experience")
            return None
        except ObjectDoesNotExist:
            return None

    def get_reference(self, obj):
        try:
            return UserReferenceSerializerForList(UserReference.objects.filter(job_profile__user=obj.user),
                                                  many=True).data
        except ObjectDoesNotExist:
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for reference")
            return None

    def get_skills(self, obj):
        try:
            return UserSkillSerializer(UserSkill.objects.filter(job_profile__user=obj.user), many=True).data
        except ObjectDoesNotExist as e:
            logger.debug(e)
            return None
        except ValueError as ve:
            logger.exception("Error in getting a value for skill")
            return None

    def get_user_last_work_experience(self, obj):
        user_work_experience_last_obj = UserWorkExperience.objects.filter(job_profile=obj).last()
        if user_work_experience_last_obj:
            work_experience_serializer = UserWorkExperienceListSerializer(user_work_experience_last_obj)
            return work_experience_serializer.data
        else:
            return None

    def get_user_total_experience(self, obj):
        try:
            work_exp_qs = UserWorkExperience.objects.filter(job_profile=obj)
            user_total_work_exp_in_seconds = 0
            for exp in work_exp_qs:
                # print("exp_from: {d}".format(d=exp.worked_from))
                # print("exp_till: {till}".format(till=exp.worked_till))
                user_single_exp_in_seconds = get_user_work_experience_in_seconds(exp.worked_from, exp.worked_till)
                # print("Single work experience: ", single_exp_in_seconds)
                user_total_work_exp_in_seconds = user_total_work_exp_in_seconds + user_single_exp_in_seconds
            if user_total_work_exp_in_seconds > 0:
                user_total_work_exp_in_years = user_total_work_exp_in_seconds/60/60/24/365
                return round(user_total_work_exp_in_years, 1)
            else:
                return 0
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            # raise ICFException(_("Something went wrong. reason:{reason}").format(reason=str(e)))
            return 0

    def get_is_job_invitation_sent(self, obj):
        try:
            jobseeker_user = obj.user
            to_user_type = ContentType.objects.get_for_model(jobseeker_user)

            app_type_slug = 'job'
            app_type = Type.objects.get(slug=app_type_slug)

            icf_user_messages_list = ICFMessage.objects.filter(topic_slug=self.context.get('view').kwargs.get('slug'),
                                           recipient_type =to_user_type,
                                           recipient_id=jobseeker_user.id, app_type=app_type, sent_at__isnull=False)
            if icf_user_messages_list:
                return True
            else:
                return False
        except Exception as e:
            pass

# class EventOverviewSerializer(Serializer):
#     number_of_jobs = serializers.SerializerMethodField()
#     number_of_events = serializers.SerializerMethodField()
#     available_credit = serializers.SerializerMethodField()
#
#     def get_number_of_jobs(self,obj):
#         return Job.objects.filter(entity=obj).filter(status=Item.ITEM_ACTIVE).count()
#
#     def get_number_of_events(self,obj):
#         return Event.objects.filter(entity=obj).filter(status=Item.ITEM_ACTIVE).count()
#
#     def get_available_credit(self,obj):
#         try:
#             return ICFCreditManager.get_available_credit(entity=obj)
#         except Exception as e:
#             logger.exception(e)
#             return 0

