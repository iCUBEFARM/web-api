import base64
import os
import random
import smtplib
import threading
from decimal import Decimal
from email.encoders import encode_base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from allauth.account.adapter import get_adapter
from allauth.account.utils import send_email_confirmation, user_email
from anymail.utils import EmailAddress
from dal import autocomplete
from django.contrib.sessions.backends import file
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail, EmailMessage
from django.shortcuts import render
from django.utils.timezone import now
from django.views.generic import FormView
from rest_framework.generics import CreateAPIView, GenericAPIView

from django.conf import Settings, settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework.views import APIView

from icf.settings import BASE_DIR, SERVER_ROOT, STATIC_ROOT, MEDIA_ROOT, DEFAULT_FROM_EMAIL
from icf_entity.models import Entity, Logo
from icf_generic.Exceptions import ICFException
from icf_generic.api.mixins import AutosuggestionMixin
from icf_generic.api.serializers import (
    CountrySerializer, FeaturedEventsRetrieveSerializer2, StateSerializer,
    CitySerializer, AddressSerializer,
    LanguageSerializer, CurrencySerializer, SponsoredListSerializer, GetFeaturedVideosListSerializer,
    GetFeaturedEventsListSerializer, FAQListSerializer, AboutUsCreateSerializer,
    FAQRetrieveSerializer, FAQWithCategoryListSerializer, RelevantFAQListSerializer, FAQListByCategorySerializer,
    FAQListByCategorySlugSerializer, FAQDetailSerializer)
from icf_generic.forms import CreateFAQForm

from icf_generic.models import Country, State, City, Address, Language, Currency, Sponsored, FeaturedVideo, \
    FeaturedEvent, FAQ, AboutUs, QuestionCategory, FAQCategory
from rest_framework import generics, status
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema

import logging

logger = logging.getLogger(__name__)

@swagger_auto_schema(
    operation_summary="Return marching Adress",
)
class AddressList(generics.ListAPIView):
    serializer_class = AddressSerializer
    # pagination_class = None

    @swagger_auto_schema(
        operation_summary="Return marching Address",
    )
    def get_queryset(self):
        queryset = Address.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(address_1__istartswith=qp)
        return queryset


class CityList(AutosuggestionMixin, generics.ListAPIView):
    serializer_class = CitySerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="Return City List",
    )
    def get_queryset(self):
        queryset = City.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp:
            queryset = queryset.filter(city__istartswith=qp)
        else:
            # queryset = self.get_default_queryset(queryset)
            queryset = None               # queryset is made empty if no query parameter is passed
        return queryset


class StateList(generics.ListAPIView):

    serializer_class = StateSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="List States",
    )
    def get_queryset(self):
        queryset = State.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(state__istartswith=qp)
        return queryset


class CountryList(generics.ListAPIView):
    serializer_class = CountrySerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="List country",
    )
    def get_queryset(self):
        queryset = Country.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(country__istartswith=qp)
        return queryset


class LanguageList(generics.ListAPIView):
    serializer_class = LanguageSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="List Language",
    )
    def get_queryset(self):
        queryset = Language.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(name__istartswith=qp)
        return queryset


class CurrencyList(generics.ListAPIView):
    serializer_class = CurrencySerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="Return marching currency",
    )
    def get_queryset(self):
        queryset = Currency.objects.all()

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(name__istartswith=qp)
        return queryset


class SponsoredListView(generics.ListAPIView, generics.UpdateAPIView):
    serializer_class = SponsoredListSerializer

    @swagger_auto_schema(
        operation_summary="Sponsored List",
    )
    def get_queryset(self):
        queryset = Sponsored.objects.filter(status=Sponsored.SPONSORED_ACTIVE).order_by('last_seen')

        qp_type = self.request.query_params.get('type', None)

        if qp_type is not None:
            qp_type = qp_type.strip().lower()
            queryset = queryset.filter(content_type__model=qp_type).filter(start_date__lte=timezone.now(),
                                                                               end_date__gt=timezone.now())
            # print(queryset)
        else:
            queryset = queryset.filter(start_date__lte=timezone.now(), end_date__gt=timezone.now())
            # print(queryset)
        return queryset

    @swagger_auto_schema(
        operation_summary="Sponsored List",
    )
    def list(self, request, *args, **kwargs):
        response_list =[]
        sponsored_objects_to_update = []
        queryset = self.get_queryset()

        qp_no = self.request.query_params.get('limit', None)
        if qp_no is None:
            qp_no = 3
        else:
            try:
                qp_no = int(qp_no)
            except  ValueError as ve:
                logger.exception(ve)
                return Response({"detail": _("Provide a valid limit")}, status=status.HTTP_400_BAD_REQUEST)

        for sp_obj in queryset:
            content_type_obj = ContentType.objects.get_for_id(sp_obj.content_type_id)
            model = content_type_obj.model_class()
            instance_obj = model.objects.get(id=sp_obj.object_id)
            sponsored_info = instance_obj.get_sponsored_info()
            if sponsored_info is not None:
                response_list.append(sponsored_info)
                sponsored_objects_to_update.append(sp_obj)
            else:
                continue

        # if the Count (no objects present) in the queryset() is greater than or equal to qp_no(no of objects we want to retrieve(limit) )
        # then filter that many objects otherwise  get the objects present in the queryset()
        if len(response_list) >= qp_no:
            response_list_limited = response_list[:qp_no]
        else:
            response_list_limited = response_list

        if len(sponsored_objects_to_update)>=qp_no:
            sponsored_objects_to_update_limited = sponsored_objects_to_update[:qp_no]
        else:
            sponsored_objects_to_update_limited = sponsored_objects_to_update

        for sp_obj in sponsored_objects_to_update_limited:
            sp_obj.count = sp_obj.count+1
            sp_obj.save()

        serializer = SponsoredListSerializer(response_list_limited, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class GetFeaturedVideosListView(generics.ListAPIView):
    serializer_class = GetFeaturedVideosListSerializer

    def get_queryset(self):
        queryset = FeaturedVideo.objects.all()

        qp = self.request.query_params.get('type', None)
        if qp is not None:
            if qp == 'dashboard':
                queryset = FeaturedVideo.objects.filter(status=FeaturedVideo.FEATURED_VIDEO_ACTIVE).filter(show_in_dashboard=True).order_by('-updated')
            if qp == 'landing':
                queryset = FeaturedVideo.objects.filter(status=FeaturedVideo.FEATURED_VIDEO_ACTIVE).filter(is_main_video=True).order_by('-updated')
            return queryset
        else:
            queryset = FeaturedVideo.objects.filter(status=FeaturedVideo.FEATURED_VIDEO_ACTIVE).order_by('-updated')
            return queryset


class GetSearchFeaturedVideosListView(generics.ListAPIView):
    serializer_class = GetFeaturedVideosListSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = FeaturedVideo.objects.filter(status=FeaturedVideo.FEATURED_VIDEO_ACTIVE).order_by('id')

        qp = self.request.query_params.get('q', None)
        if qp is not None:
            queryset = queryset.filter(Q(title__contains=qp) | Q(description__contains=qp))
        return queryset


class GetFeaturedEventsListView(generics.ListAPIView):
    serializer_class = GetFeaturedEventsListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = FeaturedEvent.objects.filter(status=FeaturedEvent.FEATURED_EVENT_ACTIVE).\
            filter(start_date__lte = timezone.now(), end_date__gt = timezone.now()).order_by('-updated')
        return queryset


class FeaturedEventDetailAPIView(generics.RetrieveAPIView):
    queryset = FeaturedEvent.objects.all()
    serializer_class = FeaturedEventsRetrieveSerializer2
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"


# class GetFAQListView(generics.ListAPIView):
#     serializer_class = FAQListSerializer
#
#     def get_queryset(self):
#         queryset = FAQ.objects.all()
#         category_id = self.kwargs.get('category_id')
#         if category_id:
#             queryset = queryset.filter(category=category_id)
#         q = self.request.query_params.get('q',None)
#         if q is not None:
#             queryset = queryset.filter(Q(question__contains=q) | Q(answer__contains=q))
#         return queryset
#


class GetFAQListByCategoryView(generics.ListAPIView):
    serializer_class = FAQListByCategorySerializer

    @swagger_auto_schema(
        operation_summary="FAQ List",
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            category_id = int(self.kwargs.get('category_id'))
            if category_id:
                faq_category = FAQCategory.objects.get(id=category_id)
                return Response({'results': serializer.data, 'faq_category_name': faq_category.name,
                             'faq_category_slug': faq_category.slug})
            else:
                return Response({'detail': 'Something went wrong.'}, status=status.HTTP_400_BAD_REQUEST)
        except FAQCategory.DoesNotExist as tdne:
            logger.exception("FAQCategory object not found. {reason} ".format(reason=str(tdne)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        queryset = QuestionCategory.objects.all()
        category_id = int(self.kwargs.get('category_id'))
        if category_id:
            queryset = queryset.filter(category__id=category_id)
        q = self.request.query_params.get('q', None)
        if q is not None:
            queryset = queryset.filter(Q(faq__question__contains=q))
        return queryset


class GetFAQListByCategorySlugView(generics.ListAPIView):
    serializer_class = FAQListByCategorySlugSerializer

    @swagger_auto_schema(
        operation_summary="FAQ List by category",
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            category_slug = self.kwargs.get('category_slug')
            if category_slug:
                faq_category = FAQCategory.objects.get(slug=category_slug)
                return Response({'results': serializer.data, 'faq_category_name': faq_category.name,
                             'faq_category_slug': faq_category.slug})
            else:
                return Response({'detail': 'Something went wrong.'}, status=status.HTTP_400_BAD_REQUEST)
        except FAQCategory.DoesNotExist as tdne:
            logger.exception("FAQCategory object not found. {reason} ".format(reason=str(tdne)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
            return Response({"detail": _("Something went wrong.")}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        queryset = QuestionCategory.objects.all()
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        q = self.request.query_params.get('q', None)
        if q is not None:
            queryset = queryset.filter(Q(faq__question__contains=q) | Q(faq__answer__contains=q))
        return queryset


class GetFAQsView(generics.ListAPIView):
    serializer_class = FAQWithCategoryListSerializer

    def get_queryset(self):
        queryset = QuestionCategory.objects.all()
        q = self.request.query_params.get('q', None)
        if q is not None:
            queryset = queryset.filter(Q(faq__question__icontains=q) | Q(faq__answer__icontains=q))
        return queryset


class GetFAQDetailView(generics.RetrieveAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQDetailSerializer
    lookup_field = "slug"


class GetRelevantFAQListView(generics.ListAPIView):
    queryset = QuestionCategory.objects.all()
    serializer_class = RelevantFAQListSerializer

    def get_queryset(self):
        queryset = QuestionCategory.objects.all()
        faq_obj_list = []
        faq_slug = self.kwargs.get('faq_slug')
        # faq_category_slug = self.kwargs.get('faq_category_slug')
        # if faq_category_slug and faq_slug:
        if faq_slug:
            # queryset = queryset.filter(category__slug=faq_category_slug)
            queryset = queryset.exclude(faq__slug=faq_slug)
            queryset_faq_id_list = queryset.values('faq_id')
            if len(queryset_faq_id_list) == 0:
                return None
            elif len(queryset_faq_id_list) == 1:
                faq_id_dict = queryset_faq_id_list[0]
                faq_id = faq_id_dict.get('faq_id')
                FAQ_obj = FAQ.objects.get(id=faq_id)
                faq_obj_list.append(FAQ_obj)
                return faq_obj_list
            else:
                queryset_faq_id_list = list(queryset_faq_id_list)
                faq_random_list = random.sample(queryset_faq_id_list, len(queryset_faq_id_list))
                # faq_random_list = list(faq_random_list)
                for faq_id_dict in faq_random_list:
                    faq_id = faq_id_dict.get('faq_id')
                    FAQ_obj = FAQ.objects.get(id=faq_id)
                    faq_obj_list.append(FAQ_obj)
                return faq_obj_list

        else:
            raise Exception


@swagger_auto_schema(
    operation_summary="Retrieve city List",
)
class GetCityAPIView(generics.RetrieveAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class AboutUsCreateAPIView(generics.CreateAPIView):
    serializer_class = AboutUsCreateSerializer
    queryset = AboutUs.objects.all()


class CountryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Country.objects.all()

        if self.q:
            qs = qs.filter(country__istartswith=self.q)

        return qs


class LanguageAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Language.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class FaqCategoryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = FAQCategory.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AddQuestionCategoryView(FormView):

    template_name = 'admin/question_category.html'
    form_class = CreateFAQForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        # qs = User.objects.all()
        form = self.form_class(request.POST)
        if form.is_valid():
            faq_category_obj_list = form.cleaned_data.get('category')
            faq = form.cleaned_data.get('faq')
            if faq_category_obj_list and faq:
                for faq_category_obj in faq_category_obj_list:
                    try:
                        question_category = QuestionCategory.objects.get(category=faq_category_obj, faq=faq)
                        logger.exception("QuestionCategory  already exists.\n")
                        pass
                        # raise form.ValidationError(u"You haven't set a valid department. Do you want to continue?")
                        # raise form.error_class.

                    except QuestionCategory.DoesNotExist as qe:
                        question_category = QuestionCategory.objects.create(category=faq_category_obj, faq=faq)

            logger.info("Returning to UI at {}".format(now(), threading.get_ident()))

            return HttpResponseRedirect('/icube-admin/icf_generic/questioncategory/')

        return render(request, self.template_name, {'form': form, 'title': 'Question Category Form'})