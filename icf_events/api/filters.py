from django_filters.filters import NumberFilter, ModelChoiceFilter, ModelMultipleChoiceFilter, CharFilter, ChoiceFilter, \
    BooleanFilter
from django_filters.filterset import FilterSet
from icf_entity.models import Entity
from icf_events.models import Event
from icf_generic.models import Address, City
from icf_item.models import FavoriteItem, Category, Item
from icf_jobs.models import Job, JobUserApplied, Skill
from django.utils.translation import ugettext_lazy as _


class StatusEntityFilter(FilterSet):
    status = ChoiceFilter(choices=Item.ITEM_STATUS_CHOICES)

    class Meta:
        model = Event
        fields = ['status']


class EventFilters(FilterSet):
    category = CharFilter(field_name='category__slug')
    company = CharFilter(field_name='entity__slug')
    location = CharFilter(field_name='location__city__city')
    title = CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = Event
        fields = ['category', 'company', 'location', 'title']


# class AppliedUserStatusFilter(FilterSet):
#     NEW = 1
#     MAY_BE = 2
#     YES = 3
#     NO = 4
#     USER_STATUS_CHOICES = ((NEW, _('NEW')),(MAY_BE, _('Maybe')), (YES, _('Yes')), (NO, _('NO')))
#     status = ChoiceFilter(choices=USER_STATUS_CHOICES)
#
#     class Meta:
#         model = JobUserApplied
#         fields = ['status']



