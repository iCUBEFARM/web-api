from django.db.models.query_utils import Q
from django.utils.timezone import now
from icf_career_fair.models import CareerFair
from icf_entity.models import Entity
from icf_events.models import Event
from icf_auth.models import User
from icf_jobs.models import Job, JobUserApplied, UserJobProfile
from rest_framework.permissions import IsAdminUser

from icf_generic.api.filters import CategoryTypeFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from icf_item.api.serializers import CategorySerializer, ItemListSerializer, ItemSearchListSerializer
from icf_item.models import Category, Item
from datetime import date , datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

class CategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_class = CategoryTypeFilter
    pagination_class = None


class ItemList(ListAPIView):
    serializer_class = ItemListSerializer

    def get_queryset(self):
        # queryset = Item.objects.filter(status=Item.ITEM_ACTIVE, start_date__lte=now(), expiry__gte=now()).order_by("-created")
        """
        For jobs, and item is visible in the website starting from start date while creating a job.
         the active items should be live now ( i.e. start date should be less than or equal to now)
        For events and career fair, the item should be visible even if the start date is in the future as users will
        want to purchase ticket etc. for an upcoming event.
        :return:
        """
        queryset = (Item.objects.filter(status=Item.ITEM_ACTIVE, start_date__lte=now(), expiry__gte=now(),
                                        item_type__name='job') | Item.objects.filter(status=Item.ITEM_ACTIVE,
                                                                                     expiry__gte=now(),
                                                                                     item_type__name__in=['event',
                                                                                                          'career fair'])).order_by(
            "-updated")

        return queryset

    permission_classes = (IsAuthenticated,)


class GlobalSearchList(ListAPIView):
    serializer_class = ItemSearchListSerializer

    def get_queryset(self):
        queryset = Item.objects.all().filter(status=Item.ITEM_ACTIVE).order_by('created')
        query = self.request.query_params.get('query', None)
        city_str = self.request.query_params.get('city', None)

        if query is not None:
            queryset = queryset.filter(Q(title__icontains=query) | Q(location__city__city__icontains=query))

        if city_str is not None:
                # city = City.objects.get(id=city_id)
                city_rpr = city_str.split(',')
                city = city_rpr[0].strip()
                queryset = queryset.filter(location__city__city__icontains=city)
        return queryset

# Entity Stats list for ICF Admins stats table.
# Only visible ot admins aka user.is_staff is True
# @swagger_auto_schema(
#     operation_summary="Admin stats overview."
# )
@api_view(["GET"])
@permission_classes([IsAdminUser])
def stats(request, *args, **kwargs):

    # 1. creat a dict to carry all the stats
    entity_data = {}
    # 2. Pull in all data
    total = Entity.objects.all().count()
    # Last year
    last_yr = Entity.objects.filter(created__range=["2021-01-01", "2021-12-31"]).count()

    # last Month
    startdate = datetime.today()
    enddate = startdate - timedelta(days=30)
    last_month = Entity.objects.filter(created__range=[enddate, startdate]).count()

    # Last week data
    startdate = datetime.today()
    enddate = startdate - timedelta(days=6)
    this_week = Entity.objects.filter(created__range=[enddate, startdate ]).count()
    # 3. store total count in the dict
    entity_data["all_time"] = total
    entity_data["last_yr"] = last_yr
    entity_data["last_month"] = last_month
    entity_data["this_week"] = this_week

# Entity Data
    event_data = {}
    # 2. Pull in all data
    total = Event.objects.all().count()
    event_data["all_time"] = total

# UserJobProfile Data
    userJobProfile_data = {}
    # 2. Pull in all data
    total = UserJobProfile.objects.all().count()
    userJobProfile_data["all_time"] = total

# JobUserApplied Data
    jobUserApplied_data = {}
    # 2. Pull in all data
    total = JobUserApplied.objects.all().count()
    jobUserApplied_data["all_time"] = total

# Job Data
    job_data = {}
    # 2. Pull in all data
    total = Job.objects.all().count()
    job_data["all_time"] = total

# CareerFair Data
    careerFair_data = {}
    # 2. Pull in all data
    total = CareerFair.objects.all().count()
    careerFair_data["all_time"] = total


# User Data
    user_data = {}
    # 2. Pull in all data
    total = User.objects.all().count()
    # Last year
    last_yr = User.objects.filter(date_joined__range=["2021-01-01", "2021-12-31"]).count()

    # last Month
    startdate = datetime.today()
    enddate = startdate - timedelta(days=30)
    last_month = User.objects.filter(date_joined__range=[enddate, startdate]).count()

    # Last week data
    startdate = datetime.today()
    enddate = startdate - timedelta(days=6)
    this_week = User.objects.filter(date_joined__range=[enddate, startdate ]).count()
    # 3. store total count in the dict
    user_data["all_time"] = total
    user_data["last_yr"] = last_yr
    user_data["last_month"] = last_month
    user_data["this_week"] = this_week



    data = {
        "entity" : entity_data,
        "user" : user_data,
        "events": event_data,
        "job_posted": job_data,
        "job_applications": jobUserApplied_data,
        "job_profile": userJobProfile_data,
        "careerFair_listed": careerFair_data,
    }
    return Response(data)