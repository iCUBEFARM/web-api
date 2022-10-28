from datetime import datetime

import pytz
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from icf_entity.app_settings import DEFAULT_CREDITS_FOR_ENTITY
from icf_entity.entity_credit_helper import EntityDefaultCreditManager
from icf_events.models import Event
from icf_orders.api.mixins import ICFCreditManager
from icf_item.models import Item
from icf_jobs.models import Job
from rest_framework import serializers, status
from rest_framework.serializers import ModelSerializer, Serializer

from rest_framework.utils import model_meta

from icf_entity.api.mixins import ICFEntityMixin
from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import Entity, Logo, EntityUser, Sector, CompanySize, Industry, FeaturedEntity, TeamMember, \
    EntityPerms, EntityBrochure, EntityPromotionalVideo
from icf_generic.Exceptions import ICFException
from icf_auth.models import User, UserProfileImage
from icf_generic.models import Address, Sponsored
from icf_generic.api.serializers import AddressSerializer
from django.utils.translation import ugettext_lazy as _

import logging

logger = logging.getLogger(__name__)


class EntityLogoSerializer(ICFEntityMixin, ModelSerializer):
   # image_url = serializers.SerializerMethodField()
    class Meta:
        model = Logo
        fields = ['image', 'id']

    def get_image_url(self, obj):
        return obj.image.url

    def create(self, validated_data):
        logger.info("Upload logo for the entity")
        entity = self.get_entity(self.context['slug'])
        try:
            obj = Logo.objects.get(entity=entity)
            obj.image = validated_data.get('image')
            obj.save()
        except ObjectDoesNotExist:
            obj = Logo.objects.create(entity=entity, **validated_data)
        return obj

    def update(self, instance, validated_data):
        logger.info("Update logo for the entity")
        instance.image = validated_data.get('image')
        instance.save()
        return instance


class EntityCreateSerializer(ModelSerializer):
    class Meta:
        model = Entity
        fields = ["name", "email", "phone", "slug", "address"]

    @transaction.atomic
    def create(self, validated_data):
        logger.info("Create entity")

        created_entity = super(EntityCreateSerializer, self).create(validated_data)

        logger.info("Entity created {}".format(created_entity))

        # Add the user to list of entity users
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            entity_creator = request.user
            EntityUser.objects.create(user=entity_creator, entity=created_entity)
        else:
            logger.exception("not an authenticated user, cannot create entity")
            raise ICFException(_("Please login and try again."), status_code=status.HTTP_400_BAD_REQUEST)

        # Add user to entity and admin group for entity created.
        ICFEntityUserPermManager.add_user_perm(entity_creator, created_entity, EntityPerms.ENTITY_ADMIN)
        ICFEntityUserPermManager.add_user_perm(entity_creator, created_entity, EntityPerms.ENTITY_USER)
        # admin_group_name = "{}_{}".format(created_entity.slug, EntityPerms.ENTITY_ADMIN)
        # admin_group = Group.objects.get(name=admin_group_name)
        # entity_creator.groups.add(admin_group)
        EntityDefaultCreditManager().assign_default_credits_to_entity(created_entity, entity_creator, DEFAULT_CREDITS_FOR_ENTITY)

        return created_entity


class NewEntityCreateSerializer(ModelSerializer):
    slug = serializers.ReadOnlyField()
    address = AddressSerializer()

    class Meta:
        model = Entity
        fields = ["name", "email", "phone", "alternate_phone", "website", "address", "industry",
                  "sector", "slug", ]

    @transaction.atomic
    def create(self, validated_data):
        logger.info("Create entity")

        address_data = None
        if validated_data.get('address'):
            address_data = validated_data.pop('address')
        created_entity = super(NewEntityCreateSerializer, self).create(validated_data)
        created_entity.status = Entity.ENTITY_ACTIVE
        created_entity.save(update_fields=['status'])

        if address_data:
            address, address_created = Address.objects.update_or_create(entity=created_entity, **address_data)
            created_entity.address = address
            created_entity.save(update_fields=['address'])

        logger.info("Entity created {}".format(created_entity))

        # Add the user to list of entity users
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            entity_creator = request.user
            EntityUser.objects.create(user=entity_creator, entity=created_entity)
        else:
            logger.exception("not an authenticated user, cannot create entity")
            raise ICFException(_("Please login and try again."), status_code=status.HTTP_400_BAD_REQUEST)

        # Add user to entity and admin group for entity created.
        ICFEntityUserPermManager.add_user_perm(entity_creator, created_entity, EntityPerms.ENTITY_ADMIN)
        ICFEntityUserPermManager.add_user_perm(entity_creator, created_entity, EntityPerms.ENTITY_USER)
        # admin_group_name = "{}_{}".format(created_entity.slug, EntityPerms.ENTITY_ADMIN)
        # admin_group = Group.objects.get(name=admin_group_name)
        # entity_creator.groups.add(admin_group)
        EntityDefaultCreditManager().assign_default_credits_to_entity(created_entity, entity_creator,
                                                                      DEFAULT_CREDITS_FOR_ENTITY)

        return created_entity


class EntityRetrieveUpdateSerializer(ModelSerializer):
    address = AddressSerializer()
    logo = serializers.SerializerMethodField(read_only=True)
    is_sponsored = serializers.BooleanField(default=False)
    sponsored_start_dt = serializers.DateTimeField(default=None)
    sponsored_end_dt = serializers.DateTimeField(default=None)

    class Meta:
        model = Entity
        exclude = [ 'created', 'updated', 'status']
        extra_fields = ['is_sponsored', 'sponsored_start_dt', 'sponsored_end_dt']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(EntityRetrieveUpdateSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def get_logo(self, obj):
        serializer = EntityLogoSerializer(Logo.objects.filter(entity=obj).first())
        return serializer.data

    @transaction.atomic
    def update(self, instance, validated_data):
        entity_model = ContentType.objects.get_for_model(instance)

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            raise ICFException(_("Unknown user, cannot create job"), status_code=status.HTTP_400_BAD_REQUEST)

        address_data = validated_data.pop('address')
        if instance.address:
            instance.address.address_1 = address_data.get('address_1')
            instance.address.address_2 = address_data.get('address_2')
            instance.address.city = address_data.get('city')
            instance.address.save()
        else:
            address, address_created = Address.objects.update_or_create(entity=instance, **address_data)
            instance.address = address

        is_sponsored = validated_data.get('is_sponsored')
        sponsored_start_dt = validated_data.get('sponsored_start_dt')
        sponsored_end_dt = validated_data.get('sponsored_end_dt')

        if is_sponsored:

            if not sponsored_start_dt or not sponsored_end_dt:
                logger.exception("Invalid duration for sponsoring the entity")
                raise ICFException(_("The minimum duration for sponsoring an entity is X days and the maximum duration of sponsoring an entity is Y days. Please check and try again."),
                                   status_code=status.HTTP_400_BAD_REQUEST)

            # Check if the entity was already sponsored before
            try:

                # The entity was already sponsored. Charge for the difference if any in the duration.
                sponsored = Sponsored.objects.get(object_id=instance.id,status=Sponsored.SPONSORED_ACTIVE)

                prev_sponsored_start_date = sponsored.start_date
                prev_sponsored_end_date = sponsored.end_date

                if prev_sponsored_start_date != sponsored_start_dt:
                    if prev_sponsored_start_date.date() < datetime.now(pytz.utc).date():
                        logger.exception("Cannot change start date of an already sponsored entity")
                        raise ICFException(
                            _("You cannot change the start date of an ongoing sponsored entity campaign."),
                            status_code=status.HTTP_400_BAD_REQUEST)
                    elif sponsored_start_dt.date() < datetime.now(pytz.utc).date():
                        logger.exception("Invalid start date for sponsoring the entity")
                        raise ICFException(
                            _("The start date of your sponsored entity campaign can only be between X and Y."),
                            status_code=status.HTTP_400_BAD_REQUEST)

                if sponsored_end_dt.date() < datetime.now(pytz.utc).date():
                    logger.exception("Invalid end date for sponsoring")
                    raise ICFException(_("The end date of your sponsored entity campaign can only be between X and Y"),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                sponsored.start_date = sponsored_start_dt
                sponsored.end_date = sponsored_end_dt
                sponsored.status = Sponsored.SPONSORED_ACTIVE
                sponsored.save(update_fields=['start_date', 'end_date', 'status'])
                # Charge for the difference in duration.
                intervals = ICFCreditManager.change_to_interval(prev_sponsored_start_date,
                                                                prev_sponsored_end_date, sponsored_start_dt,
                                                                sponsored_end_dt, action='sponsored_entity')
                if intervals:
                    ICFCreditManager.charge_for_action(user=user, entity=instance, app=entity_model,
                                                       action='sponsored_entity', intervals=intervals)

            except Sponsored.DoesNotExist:
                # entity sponsored first time during this update, did not exist earlier
                # to check whether job is alredy sponsored and inactive
                try:
                    pre_sponsored = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_INACTIVE)
                    # delete to avoid redudant row in table
                    pre_sponsored.delete()
                except ObjectDoesNotExist:
                    pass

                is_allowed_interval = ICFCreditManager.is_allowed_interval(sponsored_start_dt, sponsored_end_dt)
                if not is_allowed_interval:
                    logger.exception("Invalid duration for posting the job")
                    raise ICFException(_("Please review your start date and end date and try again. You can contact Customer Support to get help."),
                                       status_code=status.HTTP_400_BAD_REQUEST)
                intervals = ICFCreditManager.get_num_of_intervals(sponsored_start_dt, sponsored_end_dt,
                                                                  'sponsored_entity')
                Sponsored.objects.create(content_object=instance,
                                         start_date=sponsored_start_dt, end_date=sponsored_end_dt)
                ICFCreditManager.charge_for_action(user=user, entity=instance, app=entity_model,
                                                   action='sponsored_entity',
                                                   intervals=intervals)
                instance.is_sponsored = True
                instance.sponsored_start_dt = sponsored_start_dt
                instance.sponsored_end_dt = sponsored_end_dt

        else:
            # Check if an earlier sponsored job has been removed
            try:
                sponsored = Sponsored.objects.get(object_id=instance.id)
                sponsored.status = Sponsored.SPONSORED_INACTIVE
                sponsored.save(update_fields=["status"])
            except Sponsored.DoesNotExist:
                pass

        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)
        instance.status = Entity.ENTITY_ACTIVE
        instance.save()

        return instance


class EntityBrochureSerializer(ICFEntityMixin, ModelSerializer):
    class Meta:
        model = EntityBrochure
        ref_name = 'broshure'
        fields = ['brochure_name', 'brochure', 'pk']

    def create(self, validated_data):
        logger.info("Upload a Brochure for the entity")
        entity = self.get_entity(self.context['slug'])

        # Check Limit
        if EntityBrochure.objects.filter(entity=entity).count() >= 5:
            raise ICFException(_("You have reached the max number of brochures"), status_code=status.HTTP_400_BAD_REQUEST)

        obj = EntityBrochure.objects.create(entity=entity, **validated_data)

        return obj


class EntityPromotionalVideoSerializer(ICFEntityMixin, ModelSerializer):
    class Meta:
        model = EntityPromotionalVideo
        fields = ['promotional_video_name', 'promotional_video_url', 'pk']

    def create(self, validated_data):

        logger.info("Add a promotional video for the entity")
        entity = self.get_entity(self.context['slug'])

        # Check Limit
        if EntityPromotionalVideo.objects.filter(entity=entity).count() >= 5:
            raise ICFException(_("You have reached the max number of promotional videos"), status_code=status.HTTP_400_BAD_REQUEST)

        obj = EntityPromotionalVideo.objects.create(entity=entity, **validated_data)

        return obj


class EntityRetrieveSerializer(ModelSerializer):
    logo = serializers.SerializerMethodField(read_only=True)
    address =serializers.StringRelatedField()
    industry = serializers.StringRelatedField()
    sector = serializers.StringRelatedField()
    company_size = serializers.StringRelatedField()
    category = serializers.StringRelatedField()
    is_sponsored = serializers.SerializerMethodField()
    brochures = EntityBrochureSerializer(read_only=True, many=True, source='entitybrochure_set')
    promotional_videos = EntityPromotionalVideoSerializer(read_only=True, many=True, source='entitypromotionalvideo_set')


    class Meta:
        model = Entity
        exclude = ['created','updated',]

    def get_logo(self, obj):
        serializer = EntityLogoSerializer(Logo.objects.filter(entity=obj).first())
        return serializer.data

    def get_is_sponsored(self, obj):
        try:
            sp_obj = Sponsored.objects.get(object_id=obj.id, status=Sponsored.SPONSORED_ACTIVE)
            if sp_obj.end_date.date() >= datetime.now(pytz.utc).date():
                return True
            else:
                return False
        except ObjectDoesNotExist:
            return False


class EntityUsersListSerializer(ICFEntityMixin, serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    username = serializers.CharField(source='user.username', required=False)
    id = serializers.IntegerField(source='user.id', required=False)
    lookup_field = 'id'

    class Meta:
        model = EntityUser
        fields = ["id", "email", "first_name", "last_name", "username", "id"]

    def create(self, validated_data):
        entity = self.get_entity(self.context['slug'])

        try:
            user = validated_data.get("user")
            user = User.objects.get(slug=user.get('slug'))
        except User.DoesNotExist:
            raise

        if user and entity:
            obj = EntityUser.objects.get_or_create(entity=entity, user=user)
            ICFEntityUserPermManager.add_user_perm(user, entity, EntityPerms.ENTITY_USER)
            return obj


class EntityUserPermListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Permission
        fields = ['codename', 'status']

    def get_status(self, obj):
        return obj.status


class EntitySetPermSerializer(serializers.Serializer):
    perm = serializers.CharField()
    user = serializers.CharField()


class EntityUserDetailSerializer(ICFEntityMixin, serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', required=False)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    username = serializers.CharField(source='user.username', required=False)
    id = serializers.IntegerField(source='user.id', required=False, read_only=True)
    profile_image = serializers.SerializerMethodField()
    user_slug = serializers.CharField(source='user.slug', required=False)

    #lookup_field = 'username'

    class Meta:
        model = EntityUser
        fields = ["id", "email", "first_name", "last_name", "username", "profile_image", "user_slug"]

    def get_profile_image(self, object):
        try:
            return UserProfileImage.objects.get(user_profile__user=object.user).image.url
        except ObjectDoesNotExist:
            return None

    def create(self, validated_data):
        entity = self.get_entity(self.context['slug'])

        try:
            user_data = validated_data.get("user")
            user = User.objects.get(slug=user_data.get('slug'))

            obj, created = EntityUser.objects.get_or_create(entity=entity, user=user)
            if not created:
                logger.exception("user already exists with this entity")
                raise ICFException(_("{} is already a user with {}".format(user.display_name,entity.display_name)), status_code=status.HTTP_400_BAD_REQUEST)

            ICFEntityUserPermManager.add_user_perm(user, entity, EntityPerms.ENTITY_USER)
            return obj
        except User.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("The user was not added because we could not find any user with the email {}".format(user_data.get('email'))), status_code=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, validated_data):
        entity = self.get_entity(self.context['slug'])

        try:
            user_data = validated_data.get("user")
            user = User.objects.get(email=user_data.get('email'))
            obj = EntityUser.objects.get(entity=entity, user=user)
            return obj
        except User.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("We could not find any user with the email {}".format(user_data.get('email'))), status_code=status.HTTP_400_BAD_REQUEST)
        except EntityUser.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("This user is not part of {}".format(user.display_name)), status_code=status.HTTP_400_BAD_REQUEST)


class EntityUserEmailSerializer(ICFEntityMixin, serializers.Serializer):

    email = serializers.EmailField()

    def create(self, validated_data):
        entity = self.get_entity(self.context['slug'])

        try:
            user = User.objects.get(email=validated_data.get('email'))
            obj = EntityUser.objects.get_or_create(entity=entity, user=user)
            return obj
        except User.DoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("The user was not added because we could not find any user with the email {}".format(validated_data.get('email'))), status_code=status.HTTP_400_BAD_REQUEST)


class EntityListSerializer(ModelSerializer):
    address = serializers.StringRelatedField()
    website = serializers.StringRelatedField()
    sector = serializers.StringRelatedField()
    industry = serializers.StringRelatedField()
    slug = serializers.StringRelatedField()
    entity_logo = serializers.SerializerMethodField(read_only=True)
    # created = serializers.DateTimeField(format='%B %d, %Y')
    # updated = serializers.DateTimeField(format='%B %d, %Y')
    category = serializers.StringRelatedField()

    class Meta:
        model = Entity
        fields = '__all__'

    def get_entity_logo(self,obj):
        try:
            return Logo.objects.get(entity=obj).image.url
        except ObjectDoesNotExist:
            return None

class StatsEntitySerializer(serializers.Serializer):
    class Meta:
        model = Entity
        # fields =['name']
    # 1. creat a dict to carry all the stats
    # 2. Pull in all data
    # 3. store total count in the dict
    # 4. check by date how many in the last 12 months


class IndustrySerializer(ModelSerializer):

    class Meta:
        model = Industry
        fields = ["id", "industry", "description" ]


class SectorSerializer(ModelSerializer):

    class Meta:
        model = Sector
        fields = ["id", "sector", "description" ]


class CompanySizeSerializer(ModelSerializer):
    class Meta:
        model = CompanySize
        fields = ["id", "size", "description"]


class UsersEntityListSerializer(ICFEntityMixin, serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    entity_name = serializers.CharField(source='entity.name', required=False)
    entity_id = serializers.IntegerField(source='entity.id', required=False)
    slug = serializers.CharField(source='entity.slug', required=False)
    logo = serializers.SerializerMethodField(read_only=True)
    lookup_field = 'username'

    class Meta:
        model = EntityUser
        fields = ["username", "entity_name", "entity_id", "slug", "logo"]

    def get_logo(self, obj):
        serializer = EntityLogoSerializer(Logo.objects.filter(entity=obj.entity).first())
        return serializer.data

    # def create(self, validated_data):
    #     entity = self.get_entity(self.context['slug'])
    #
    #     try:
    #         user = validated_data.get("user")
    #         user = User.objects.get(email=user.get('email'))
    #
    #         obj = EntityUser.objects.get_or_create(entity=entity, user=user)
    #         return obj
    #     except User.DoesNotExist:
    #         raise


class TeamMemberSerializer(ModelSerializer):

    class Meta:
        model = TeamMember
        fields = ["name", "position", "featured_entity", "is_incharge", "image"]


class FeaturedEntitySerializer(ModelSerializer):
    team_members = serializers.SerializerMethodField()
    entity_name = serializers.CharField(source='entity.name', required=False)
    entity_description = serializers.CharField(source='entity.description', required=False)
    logo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FeaturedEntity
        # fields = ["team_members", "banner_image", "title", "description", "entity", "entity_name", "entity_description", "logo"]
        fields = ["team_members", "title", "description", "entity", "entity_name", "entity_description", "logo"]

    def get_team_members(self, obj):
        return TeamMemberSerializer(TeamMember.objects.filter(featured_entity=obj), many=True).data

    def get_logo(self, obj):
        serializer = EntityLogoSerializer(Logo.objects.filter(entity=obj.entity).first())
        return serializer.data


class EntityDashBoardSerializer(Serializer):
    number_of_jobs = serializers.SerializerMethodField()
    number_of_events = serializers.SerializerMethodField()
    available_credit = serializers.SerializerMethodField()

    def get_number_of_jobs(self,obj):
        return Job.objects.filter(entity=obj).filter(status=Item.ITEM_ACTIVE).count()

    def get_number_of_events(self,obj):
        return Event.objects.filter(entity=obj).filter(status=Item.ITEM_ACTIVE).count()

    def get_available_credit(self,obj):
        try:
            return ICFCreditManager.get_available_credit(entity=obj)
        except Exception as e:
            logger.exception(e)
            return 0


class EntityBrochureSerializer(ICFEntityMixin, ModelSerializer):
    class Meta:
        model = EntityBrochure
        fields = ['brochure_name', 'brochure', 'pk']

    def create(self, validated_data):
        logger.info("Upload a Brochure for the entity")
        entity = self.get_entity(self.context['slug'])

        # Check Limit
        if EntityBrochure.objects.filter(entity=entity).count() >= 5:
            raise ICFException(_("You have reached the max number of brochures"), status_code=status.HTTP_400_BAD_REQUEST)

        obj = EntityBrochure.objects.create(entity=entity, **validated_data)

        return obj


