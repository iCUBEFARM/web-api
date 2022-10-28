from django_filters.filters import NumberFilter, ModelChoiceFilter, ModelMultipleChoiceFilter, CharFilter, ChoiceFilter, \
    BooleanFilter
from django_filters.filterset import FilterSet

from icf_career_fair.models import CareerFair
from icf_item.models import FavoriteItem, Category, Item
from django.utils.translation import ugettext_lazy as _


class StatusEntityCareerFairFilter(FilterSet):
    status = ChoiceFilter(choices=Item.ITEM_STATUS_CHOICES)

    class Meta:
        model = CareerFair
        fields = ['status']


class CareerFairFilters(FilterSet):
    company = CharFilter(field_name='entity__slug')
    location = CharFilter(field_name='location__city__city')
    # location = ModelChoiceFilter(queryset=Address.objects.all())
    # job_skill = ModelMultipleChoiceFilter(field_name='job_skills__skill', queryset=Skill.objects.all())
    title = CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = CareerFair
        fields = ['company', 'location', 'title']

