from django_filters import CharFilter
from django_filters.filters import ChoiceFilter
from django_filters.rest_framework import FilterSet
from icf_item.models import Item

from icf_entity.models import Entity
from icf_jobs.models import Job


class EntityListFilter(FilterSet):
    city = CharFilter(field_name='address__city__city')
    industry = CharFilter(field_name='industry__industry')
    sector = CharFilter(field_name='sector__sector')
    category = CharFilter(field_name='category__slug')

    class Meta:
        model = Entity
        fields = ['city','industry','sector','category']


