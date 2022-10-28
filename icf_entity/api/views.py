# Create your views here.
import datetime

from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils import timezone
from django.utils.timezone import now
from guardian.shortcuts import get_perms
from rest_framework.viewsets import GenericViewSet

from icf import settings
from icf_entity import app_settings
from icf_generic.api.mixins import AutosuggestionMixin
from icf_generic.models import Sponsored
from rest_framework import viewsets, status
from rest_framework.generics import (
    CreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView, RetrieveDestroyAPIView, UpdateAPIView)
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from django.forms.models import model_to_dict

from icf_auth.api.serializers import ICFEmailSerializer
from icf_auth.models import User, UserProfileImage, UserProfile
from icf_entity.api.filters import EntityListFilter
from icf_entity.api.mixins import ICFEntityMixin
from icf_entity.permissions import CanAddEntityUser, CanEditEntity, IsEntityUser, CanViewEntityPerm, \
    ICFEntityUserPermManager, IsEntityAdmin
from icf_entity.api.serializers import EntityCreateSerializer, EntityRetrieveSerializer, \
    EntityUserDetailSerializer, EntityLogoSerializer, \
    IndustrySerializer, SectorSerializer, CompanySizeSerializer, EntityListSerializer, StatsEntitySerializer, UsersEntityListSerializer, \
    FeaturedEntitySerializer, EntityUserPermListSerializer, EntitySetPermSerializer, EntityRetrieveUpdateSerializer, \
    EntityDashBoardSerializer, EntityUsersListSerializer, NewEntityCreateSerializer, EntityBrochureSerializer, \
    EntityPromotionalVideoSerializer
from rest_framework.permissions import IsAdminUser
from django.forms.models import model_to_dict
from icf_entity.models import Entity, EntityUser, Logo, Industry, Sector, CompanySize, FeaturedEntity, EntityPerms, \
    PendingEntityUser, MinistryMasterConfig, EntityBrochure, EntityPromotionalVideo
import logging

from icf_generic.Exceptions import ICFException
from icf_generic.mixins import ICFListMixin
from django.utils.translation import ugettext_lazy as _

#from icf_jobs.api.serializers import Pending_EntityUserSerializer
from icf_jobs.models import JobPerms
from icf_messages.manager import ICFNotificationManager
from drf_yasg.utils import swagger_auto_schema

logger = logging.getLogger(__name__)


class EntityCreateAPIView(CreateAPIView):
    permission_classes = (IsAuthenticated, )
    queryset = Entity.objects.all()
    serializer_class = EntityCreateSerializer

    @swagger_auto_schema(
        operation_summary="Create new Entity"
    )
    def post(self, request, *args, **kwargs):
        name = self.request.data.get("name").lstrip().rstrip()
        if name:
            # try:
            #     entity = Entity.objects.get(name__iexact=name)
            #     if entity:
            #         return Response({"detail": "Entity with this name already exist"}, status=status.HTTP_400_BAD_REQUEST)
            # except Entity.DoesNotExist:
            return self.create(request, *args, **kwargs)
        else:
            return Response({"detail": "Please provide proper entity name"}, status=status.HTTP_400_BAD_REQUEST)


class NewEntityCreateAPIView(CreateAPIView):
    # permission_classes = (IsAuthenticated,)
    queryset = Entity.objects.all()
    serializer_class = NewEntityCreateSerializer

    @swagger_auto_schema(
        operation_summary="Create new Entity"
    )
    def post(self, request, *args, **kwargs):
        name = self.request.data.get("name").lstrip().rstrip()
        if name:
            # try:
            #     entity = Entity.objects.get(name__iexact=name)
            #     if entity:
            #         return Response({"detail": "Entity with this name already exist"},
            #         status=status.HTTP_400_BAD_REQUEST)
            # except Entity.DoesNotExist:
            return self.create(request, *args, **kwargs)
        else:
            return Response({"detail": "Please provide proper entity name"}, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    operation_summary="Create new Entity"
)
class GeneralEntityListView(ListAPIView):
    queryset = Entity.objects.all().filter(status=Entity.ENTITY_ACTIVE)
    serializer_class = EntityListSerializer
    filter_class = EntityListFilter

# Entity Stats list for ICF Admins stats table.
# Only visible ot admins aka user.is_staff is True
class StatsEntityListView(ListAPIView):
    queryset = Entity.objects.all()
    serializer_class = EntityListSerializer
    permission_classes = [IsAdminUser]

class GeneralEntityListView(ListAPIView):
    queryset = Entity.objects.all().filter(status=Entity.ENTITY_ACTIVE)
    serializer_class = EntityListSerializer
    filter_class = EntityListFilter

class EntityListView(ICFListMixin, ListAPIView):
    queryset = Entity.objects.all()
    serializer_class = EntityListSerializer
    lookup_field = "sector"

    def get_queryset(self):
        queryset = self.queryset
        return queryset.filter(slug = self.kwargs.get('slug'))


class EntityDetailAPIView(RetrieveAPIView):
    queryset = Entity.objects.all()
    serializer_class = EntityRetrieveSerializer
    #permission_classes = (IsAuthenticated, )
    lookup_field = "slug"


class EntityUpdateAPIView(RetrieveUpdateAPIView):
    # parser_classes = (MultiPartParser, FormParser)
    queryset = Entity.objects.all()
    serializer_class = EntityRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, CanEditEntity)

    lookup_field = "slug"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if entity is sponsored
        try:
            sp_obj = Sponsored.objects.get(object_id=instance.id, status=Sponsored.SPONSORED_ACTIVE)
            instance.sponsored_start_dt = sp_obj.start_date
            instance.sponsored_end_dt = sp_obj.end_date
            instance.is_sponsored = True
            serializer = self.get_serializer(instance)
        except Exception as e:
            serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class IsRegisteredUserView(APIView):
    permission_classes = (IsAuthenticated, IsEntityUser)

    def get_serializer(self, *args, **kwargs):
        return ICFEmailSerializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        self.kwargs['email'] = email
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
            user_profile = UserProfile.objects.get(user=user)
            image_url = None
            try:
                profile_image = UserProfileImage.objects.get(user_profile=user_profile)
                image_url = profile_image.image.url
            except UserProfileImage.DoesNotExist as ue:
                pass

            return Response({"detail": _("user found"),
                             "username": user.first_name,
                             "email": user.email,
                             "user_slug": user.slug,
                             "profile_img": image_url,
                             },
                            status=status.HTTP_200_OK)
        except User.DoesNotExist as e:
            logger.exception(str(e))
            return Response({"detail": _("We could not find any user with the email {}".format(email))}, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist as ue:
            logger.exception(str(ue))
            return Response({"detail": _("We could not find any user with the email {}".format(email))}, status=status.HTTP_400_BAD_REQUEST)


class EntityUserListCreateView(ListCreateAPIView):
    queryset = EntityUser.objects.all()
    permission_classes = (IsAuthenticated, CanAddEntityUser,)

    def get_serializer(self, *args, **kwargs):
        return EntityUserDetailSerializer(*args, **kwargs)

    def get(self, request, slug=None):

        company_users = EntityUser.objects.filter(entity__slug=slug)
        serializer = EntityUserDetailSerializer(company_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, slug=None):
        user_to_add_slug = request.data['user_slug']
        user = get_user_model()
        try:
            user_to_add = user.objects.get(slug=user_to_add_slug)
        except User.DoesNotExist as e:
            logger.exception(e)
            return Response({"detail": _("user not found")}, status=status.HTTP_400_BAD_REQUEST)
        entity = Entity.objects.get(slug=slug)

        user_already_exits = EntityUser.objects.filter(entity = entity, user=user_to_add).exists()
        if user_already_exits:
            return Response({"detail": _("User already exits")}, status=status.HTTP_400_BAD_REQUEST)

        plaintext = get_template('../templates/account/email/entity_user_confirm_message.txt')
        current_site = Site.objects.get_current()
        base_url = current_site.domain
        accept_link = base_url + '/api/entity/{}/accept-add-user/{}/'.format(entity.slug, user_to_add.slug)
        reject_link = base_url + '/api/entity/{}/reject-add-user/{}/'.format(entity.slug, user_to_add.slug)
        current_site = get_current_site(request)
        d = {'entity_name': entity.display_name, 'accept_link': accept_link, 'reject_link': reject_link, 'current_site': current_site}
        text_content = plaintext.render(d)

        msg = EmailMultiAlternatives(subject=app_settings.ADD_USER_EMAIL_SUBJECT, body=text_content, to=[user_to_add.email])
        msg.send()
        message = settings.ICF_NOTIFICATION_SETTINGS.get('ADD_USER_NOTIFICATION')
        detail_msg = settings.ICF_NOTIFICATION_SETTINGS.get('ADD_USER_DETAIL_NOTIFICATION')
        details = "{}, {} {}".format(user_to_add.display_name,detail_msg, entity.display_name)
        ICFNotificationManager.add_notification(user=user_to_add, message=message,details=details)

        PendingEntityUser.objects.update_or_create(entity=entity, user_to_add=user_to_add, entity_user=request.user)

        return Response({"detail": _("An Email has been sent to the user for confirmation")}, status=status.HTTP_201_CREATED)


class EntityUserRetrieveDestroyAPIView(ICFEntityMixin, RetrieveDestroyAPIView):
    queryset = EntityUser.objects.all()
    serializer_class = EntityUserDetailSerializer
    permission_classes = (IsAuthenticated, CanAddEntityUser)

    def get_object(self, slug=None, user_slug=None):
        try:
            instance = EntityUser.objects.get(entity__slug=slug, user__slug=user_slug)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("We could not find any {} in {}".format(user_slug,slug)), status_code=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, slug=None, user_slug=None, **kwargs):

        obj = self.get_object(slug=slug, user_slug=user_slug)
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, slug=None, user_slug=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, user_slug=user_slug)

            # Current logged in user cannot remove him/her self from the entity
            if request.user == obj.user:
                return Response({"detail": _("Invalid request, cannot remove self")},
                                status=status.HTTP_400_BAD_REQUEST)

            # Only an admin can remove another admin.
            if obj.user.has_perm(EntityPerms.ENTITY_ADMIN, obj.entity):
                if not request.user.has_perm(EntityPerms.ENTITY_ADMIN, obj.entity):
                    return Response({"detail": _("You do not have permission to remove an admin")},
                                    status=status.HTTP_400_BAD_REQUEST)
            # delete permissions for the user
            deleted_user_perms = get_perms(obj.user, obj.entity)
            for perm in deleted_user_perms:
                ICFEntityUserPermManager.remove_user_perm(obj.user, obj.entity, perm)

            # Delete the user from entity
            obj.delete()
            return Response({"detail": _("{} has been successfully deleted from {}".format(obj.user,obj.entity))}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"detail": _("The delete action failed because the user was not found in {}".format(obj.entity))}, status=status.HTTP_400_BAD_REQUEST)


class EntityPermListView(ICFEntityMixin, ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = EntityUserPermListSerializer
    permission_classes = (IsAuthenticated, CanViewEntityPerm,)

    #
    # This method will give a list of user permissions for user in the query params. Without any parameter the
    # permissions on the entity for the currently logged in user will be provided
    #
    def list(self, request, *args, slug=None, **kwargs):
        other_user_param = self.request.query_params.get('other', None)

        if not other_user_param:
            user = request.user
        else:
            try:
                user = User.objects.get(slug=other_user_param)
            except User.DoesNotExist as e:
                logger.exception(e)
                raise ICFException(_("user not found, cannot get permissions"), status_code=status.HTTP_400_BAD_REQUEST)

        entity = self.get_entity(slug)

            # Is the user part of entity
        try:
            user_perms = ICFEntityUserPermManager.get_user_permissions(user, entity)
            return Response(user_perms, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": _("We could not retrieve the permissions for {}".format(user))}, status=status.HTTP_400_BAD_REQUEST)


class EntitySetPermView(ICFEntityMixin, CreateAPIView):
    queryset = EntityUser.objects.all()
    serializer_class = EntitySetPermSerializer
    permission_classes = (IsAuthenticated, CanAddEntityUser)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, slug=None, **kwargs):
        entity = self.get_entity(slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_data = serializer.validated_data.get('user')
        perm_data = serializer.validated_data.get('perm')
        try:
            user = User.objects.get(slug=user_data)
            resp_user = ICFEntityUserPermManager.add_user_perm(user, entity, perm_data)
            return Response({"detail": _("You have successfully added new permissions to {}".format(user.display_name)),
                             "user": user_data,
                             "perm": perm_data }, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist:
            Response({"detail": _("You cannot assign permissions to an invalid user. Recheck the user and try again.")}, status=status.HTTP_400_BAD_REQUEST)


class EntityRemovePermView(ICFEntityMixin, APIView):
    queryset = EntityUser.objects.all()
    serializer_class = EntitySetPermSerializer
    permission_classes = (IsAuthenticated, CanAddEntityUser)

    def get_serializer(self, *args, **kwargs):
        return EntitySetPermSerializer(*args, **kwargs)

    def post(self, request, *args, slug=None, **kwargs):
        entity = self.get_entity(slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_data = serializer.validated_data.get('user')
        perm_data = serializer.validated_data.get('perm')
        try:
            user = User.objects.get(slug=user_data)

            # If the user is an admin, he cannot remove admin permission for himself
            if perm_data == EntityPerms.get_admin_perm() and user == request.user:
                return Response({"detail": _("You cannot remove your own admin permissions. Please contact another entity admin")},
                                status=status.HTTP_400_BAD_REQUEST)

            resp_user = ICFEntityUserPermManager.remove_user_perm(user, entity, perm_data)
            return Response({"detail": _("You have successfully removed permissions from {}".format(user.display_name)),
                             "user": user_data,
                             "perm": perm_data }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response({"detail": _("You cannot remove permissions from an invalid user. Please recheck the user and try again.")}, status=status.HTTP_400_BAD_REQUEST)


class EntityPermRetrieveUpdateDestroyAPIView(ICFEntityMixin, RetrieveUpdateDestroyAPIView):
    queryset = EntityUser.objects.all()
    serializer_class = EntityUserPermListSerializer
    permission_classes = (IsAuthenticated, CanAddEntityUser)

    def get_object(self, slug=None, pk=None):
        try:
            instance = User.objects.get(id=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Invalid user"), status_code=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):

        if not pk:
            user = request.user
        else:
            user = self.get_object(pk=pk)

        entity = self.get_entity(slug)

        try:
            entity_perms = EntityPerms.get_icf_permissions()
            user_perms = get_perms(user, entity)

            for perm in entity_perms:
                perm.status = False
                if perm.codename in user_perms:
                    perm.status = True

            serializer = self.get_serializer(entity_perms, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"detail": _("User not found, cannot update")}, status=status.HTTP_400_BAD_REQUEST)
    # def update(self, request, *args, slug=None, pk=None, **kwargs):
    #
    #
    # def delete(self, request, *args, slug=None, pk=None, **kwargs):
    #
    #     try:
    #         obj = self.get_object(slug=slug, pk=pk)
    #         obj.delete()
    #         return Response({"detail": "user deleted"}, status=status.HTTP_200_OK)
    #     except ObjectDoesNotExist:
    #         return Response({"detail": "User not found, cannot delete"}, status=status.HTTP_404_NOT_FOUND)


# class EntityUserPermission(DestroyModelMixin, ListCreateAPIView):
#     queryset = Entity.objects.all()
#     serializer_class = EntityPermissionSerializer
#     permission_classes = (IsAuthenticated, CanAddEntityUser, )


class EntityLogoViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EntityLogoSerializer
    permission_classes = (IsAuthenticated, CanEditEntity,)
    queryset = Logo.objects.all()

    def get_serializer(self, *args, **kwargs):
        return EntityLogoSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = Logo.objects.get(entity__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(entity__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add Logo"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve logo"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, slug=None, pk=None, **kwargs):
        context = {'slug': slug}
        try:
            instance = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(instance, context=context, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot update Logo"}, status=status.HTTP_400_BAD_REQUEST)


class IndustryList(AutosuggestionMixin, ListAPIView):
    serializer_class = IndustrySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Industry.objects.all().order_by('industry')

        qp = self.request.query_params.get('q', None)
        if qp:
            queryset = queryset.filter(industry__istartswith=qp)
        else:
            queryset = self.get_default_queryset(queryset)
        return queryset


class SectorList(ListAPIView):
    serializer_class = SectorSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Sector.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(sector__istartswith=qp)
        return queryset


class CompanySizeList(ListAPIView):
    serializer_class = CompanySizeSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = CompanySize.objects.all().order_by('id')

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(size__istartswith=qp)
        return queryset


class UserEntityList(ListAPIView):
    serializer_class = UsersEntityListSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = None
        user = self.request.user
        if user:
            qs = EntityUser.objects.filter(user=user, entity__status=Entity.ENTITY_ACTIVE)
        return qs


class GetFeaturedEntity(RetrieveAPIView):
    serializer_class = FeaturedEntitySerializer

    def get_queryset(self):
        qs = FeaturedEntity.objects.filter(status=FeaturedEntity.FEATURED_ENTITY_ACTIVE).\
            filter(start_date__lte=timezone.now(), end_date__gt=timezone.now()).order_by("created")
        return qs

    def get_object(self, *args, **kwargs):
        if len(self.get_queryset()) > 0:
            return self.get_queryset()[:1].get()
        else:
            return None


class EntityDashboardRetrieveView(RetrieveAPIView):
    serializer_class = EntityDashBoardSerializer
    permission_classes = (IsAuthenticated,IsEntityUser)

    def get_object(self):
        return Entity.objects.filter(slug=self.kwargs.get('slug')).first()

# View for sector: Energy, country: Equatorial Guinea:
class EnergyEGEntityList(ListAPIView):
    queryset = Entity.objects.all().filter(status=Entity.ENTITY_ACTIVE)
    serializer_class = EntityListSerializer

    def get_queryset(self):
        queryset = self.queryset

        sector = 'energy'
        country = 'Equatorial Guinea'

        if sector and country is not None:
            queryset = queryset.filter(sector__sector__icontains=sector).filter(address__city__state__country__country__icontains=country).order_by('created')

        return queryset

class EntitySearchList(ListAPIView):
    queryset = Entity.objects.all().filter(status=Entity.ENTITY_ACTIVE)
    serializer_class = EntityListSerializer

    def get_queryset(self):
        queryset = self.queryset

        qp_name = self.request.query_params.get('name', None)
        city_str = self.request.query_params.get('city',None)
        qp_fun_area = self.request.query_params.get('functional-area', None)

        if qp_name is not None:
            queryset = queryset.filter(name__icontains=qp_name).order_by('created')
        if city_str is not None:
            city_rpr = city_str.split(',')
            city = city_rpr[0].strip()
            queryset = queryset.filter(address__city__city__icontains=city).order_by('created')
        if qp_fun_area is not None:
            queryset = queryset.filter(industry__industry__icontains=qp_fun_area).order_by('created')
        return queryset


class EntityUserAcceptCreateView(APIView):
    #queryset = PendingEntityUser.objects.all()
    serializer_class = None

    def get(self, request, slug=None, user_slug=None):
        return self.post(request, slug, user_slug)

    def post(self, request, slug=None, user_slug=None):
        print('--------Entity slug:', slug)
        print('--------User slug:', user_slug)
        try:
            entity = Entity.objects.get(slug=slug)
            user_to_add = User.objects.get(slug=user_slug)
            print('--------Entity:', entity)
            print('--------User:', user_to_add)

            pending_entity_user = PendingEntityUser.objects.get(entity=entity, user_to_add=user_to_add)
            print('--------', pending_entity_user)

            if pending_entity_user:
                link_expiry_date = pending_entity_user.created_date + datetime.timedelta(days=app_settings.ENTITY_USER_REQUEST_LINK_VALIDITY)
                if link_expiry_date > now():
                    obj, created = EntityUser.objects.get_or_create(entity=entity, user=user_to_add)
                    if created:
                        ICFEntityUserPermManager.add_user_perm(user_to_add, entity, EntityPerms.ENTITY_USER)
                    else:
                        raise ICFException(_("Already part of entity"),
                                           status_code=status.HTTP_403_FORBIDDEN)
                    current_site = get_current_site(request)
                    plaintext = get_template('../templates/account/email/entity_user_add_success.txt')
                    d = {'added_user': user_to_add.display_name, 'added_user_email': user_to_add.email,
                         'entity_name': entity.display_name, 'action_name': "accepted", 'current_site': current_site}
                    text_content = plaintext.render(d)
                    msg = EmailMultiAlternatives(subject=app_settings.ENTITY_USER_REQUEST,
                                                 body=text_content, to=[pending_entity_user.entity_user.email])
                    msg.send()
                    message = settings.ICF_NOTIFICATION_SETTINGS.get('ADD_USER_ACCEPT_NOTIFICATION')
                    details = "{} - {}".format(message, user_to_add.display_name)
                    ICFNotificationManager.add_notification(user=pending_entity_user.entity_user,message=message,details=details)
                    pending_entity_user.delete()
                    redirect_url = app_settings.ENTITY_USER_REQ_ACCEPT_REDIRECT_URL
                    return redirect(redirect_url)
                else:
                    redirect_url = app_settings.ENTITY_USER_REQ_LINK_EXPIRE_REDIRECT_URL
                    return redirect(redirect_url)

        except (User.DoesNotExist, Entity.DoesNotExist, PendingEntityUser.DoesNotExist) as e:
            logger.exception(e)
            raise ICFException(_("Invalid request"),
                               status_code=status.HTTP_403_FORBIDDEN)


class EntityUserRejectView(APIView):
    serializer_class = None

    def get(self, request, slug=None, user_slug=None):
        return self.post(request, slug, user_slug)

    def post(self, request, slug=None, user_slug=None):
        try:
            entity = Entity.objects.get(slug=slug)
            user_to_add = User.objects.get(slug=user_slug)
            pending_entity_user = PendingEntityUser.objects.get(entity=entity, user_to_add=user_to_add)
            if pending_entity_user:
                link_expiry_date = pending_entity_user.created_date + datetime.timedelta(
                    days=app_settings.ENTITY_USER_REQUEST_LINK_VALIDITY)
                if link_expiry_date > now():
                    current_site = get_current_site(request)
                    plaintext = get_template('../templates/account/email/entity_user_add_success.txt')
                    d = {'added_user': user_to_add.display_name, 'added_user_email': user_to_add.email,
                         'entity_name': entity.display_name, 'action_name': "rejected",  'current_site': current_site}
                    text_content = plaintext.render(d)
                    msg = EmailMultiAlternatives(subject=app_settings.ENTITY_USER_REQUEST, body=text_content,
                                         to=[pending_entity_user.entity_user.email])
                    msg.send()
                    message = settings.ICF_NOTIFICATION_SETTINGS.get('ADD_USER_REJECT_NOTIFICATION')
                    details = "{} - {}".format(message, user_to_add.display_name)
                    ICFNotificationManager.add_notification(user=pending_entity_user.entity_user, message=message,details=details)
                    pending_entity_user.delete()
                    redirect_url = app_settings.ENTITY_USER_REQ_REJECT_REDIRECT_URL
                    return redirect(redirect_url)
            else:
                redirect_url = app_settings.ENTITY_USER_REQ_LINK_EXPIRE_REDIRECT_URL
                return redirect(redirect_url)

        except (Entity.DoesNotExist, User.DoesNotExist, PendingEntityUser.DoesNotExist) as e:
            logger.exception(e)
            raise ICFException(_("Invalid request"),
                               status_code=status.HTTP_403_FORBIDDEN)


class GetIndustryAPIView(RetrieveAPIView):
        queryset = Industry.objects.all()
        serializer_class = IndustrySerializer
        permission_classes = (IsAuthenticated,)


class EntityAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Entity.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class UserWithCreateJobPermissionEntityList(ListAPIView):
    serializer_class = UsersEntityListSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        entity_users = None
        user = self.request.user
        if user:
            entity_users = EntityUser.objects.filter(user=user)
            perm = JobPerms.JOB_CREATE
            for entity_user in entity_users:
                if not ICFEntityUserPermManager.has_entity_perm(entity_user.user, entity_user.entity, perm):
                    entity_users.delete(entity_user)

        return entity_users


class MarkEntityInactiveAPIView(UpdateAPIView):
    queryset = Entity.objects.all()
    permission_classes = (IsAuthenticated, CanEditEntity)
    lookup_field = "slug"

    def update(self, request, *args, **kwargs):
        try:
            response_data = {}
            instance = self.get_object()

            if instance and instance.status != Entity.ENTITY_INACTIVE:
                instance.status = Entity.ENTITY_INACTIVE
                instance.save(update_fields=['status'])
                response_data.update({"detail": _("Entity marked as inactive successfully.")})
            else:
                response_data.update({"detail": _("Entity is already marked inactive.")})
            return Response(response_data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(str(e))
            return Response({"detail": _("Entity object not found.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(str(e))
            return Response({"detail": _("Could not mark entity inactive. Please contact admin.")},
                            status=status.HTTP_400_BAD_REQUEST)


class EntityBrochureViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EntityBrochureSerializer
    permission_classes = (IsAuthenticated, CanEditEntity,)
    queryset = EntityBrochure.objects.all()

    def get_serializer(self, *args, **kwargs):
        return EntityBrochureSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = EntityBrochure.objects.get(entity__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(entity__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add Brochure"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve Brochure"}, status=status.HTTP_400_BAD_REQUEST)


    def destroy(self, request, *args, slug=None, pk=None, **kwargs):
        instance = self.get_object(slug=slug, pk=pk)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EntityPromoVideoViewSet(viewsets.ModelViewSet):
  #  parser_classes = (MultiPartParser, FormParser)
    serializer_class = EntityPromotionalVideoSerializer
    permission_classes = (IsAuthenticated, CanEditEntity,)
    queryset = EntityPromotionalVideo.objects.all()

    def get_serializer(self, *args, **kwargs):
        return EntityPromotionalVideoSerializer(*args, **kwargs)

    def get_object(self, slug=None, pk=None):
        try:
            instance = EntityPromotionalVideo.objects.get(entity__slug=slug, pk=pk)
            return instance
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise

    def list(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        qs = self.queryset.filter(entity__slug=slug)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, slug=None, **kwargs):
        context = {'slug': slug}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Cannot add promotional video"}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, slug=None, pk=None, **kwargs):
        try:
            obj = self.get_object(slug=slug, pk=pk)
            serializer = self.get_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            return Response({"detail": "Not found, cannot retrieve promotional video"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, slug=None, pk=None, **kwargs):
        instance = self.get_object(slug=slug, pk=pk)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# class GetIndustrySectorsByMinistryAndCountryAPIView(APIView):
#     serializer_class = None
#
#     def get(self, request, ministry=None, country=None):
#         industry_list = []
#         sector_list = []
#
#         if ministry and country:
#             try:
#                 ministry_master_config = MinistryMasterConfig.objects.get(country__country__iexact=country,
#                                                                           ministry_type__iexact=ministry)
#                 industry_str = ministry_master_config.industries
#                 if industry_str and industry_str != '':
#                     industry_id_list = industry_str.split(',')
#                     for industry_id in industry_id_list:
#                         try:
#                             industry_id = int(industry_id.strip())
#                             industry = Industry.objects.get(id=industry_id)
#                             industry_list.append(industry.industry)
#                         except Industry.DoesNotExist as ie:
#                             logger.exception("Industry object not exist for id:{id}".format(id=industry_id))
#                             pass
#                         except ValueError as ve:
#                             logger.exception("Invalid parameter for industry id:{id}".format(id=industry_id))
#                             raise ICFException(_("Could not get industries and sectors for "
#                                                  "ministry:{ministry} and country: {country}."
#                                                  "Please contact administrator.)"
#                                                  .format(ministry=ministry, country=country),
#                                                  status=status.HTTP_400_BAD_REQUEST))
#
#                 sector_str = ministry_master_config.sectors
#                 if sector_str and sector_str != '':
#                     sector_id_list = sector_str.split(',')
#                     for sector_id in sector_id_list:
#                         try:
#                             sector_id = int(sector_id.strip())
#                             sector = Sector.objects.get(id=sector_id)
#                             sector_list.append(sector.sector)
#                         except Sector.DoesNotExist as se:
#                             logger.exception(
#                                 "Sector object not exist for id:{id}".format(id=sector_id))
#                             pass
#                         except ValueError as ve:
#                             logger.exception("Invalid parameter for sector id:{id}".format(id=sector_id))
#                             raise ICFException(_("Could not get industries and sectors for "
#                                                  "ministry:{ministry} and country: {country}."
#                                                  "Please contact administrator.)"
#                                                  .format(ministry=ministry, country=country),
#                                                  status=status.HTTP_400_BAD_REQUEST))
#
#                 return Response({
#                                  "ministry_type": ministry_master_config.ministry_type,
#                                  "country": ministry_master_config.country.country,
#                                  "industries": industry_list,
#                                  "sectors": sector_list
#                                  }, status=status.HTTP_400_BAD_REQUEST)
#             except MinistryMasterConfig.DoesNotExist as mde:
#                 logger.exception("Could not get industries and sectors for "
#                                  "ministry:{ministry} and country:{country}".format(ministry=ministry, country=country))
#                 raise ICFException(_("Could not get industries and sectors for "
#                                      "ministry:{ministry} and country:{country}.)"
#                                      .format(ministry=ministry, country=country), status=status.HTTP_400_BAD_REQUEST))
#
#         else:
#             logger.exception("Could not get industries and sectors for "
#                              "ministry:{ministry} and country:{country}".format(ministry=ministry, country=country))
#             raise ICFException(_("Could not get industries and sectors for "
#                                 "ministry:{ministry} and country:{country}. "
#                                 "Please provide valid ministry type and country.)"
#                                 .format(ministry=ministry, country=country), status=status.HTTP_400_BAD_REQUEST))
#

