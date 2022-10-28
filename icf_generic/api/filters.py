from django_filters.filters import  CharFilter
from django_filters.filterset import FilterSet
from icf_item.models import Category, Type


class CategoryTypeFilter(FilterSet):
    type = CharFilter(field_name = 'type__slug')

    class Meta:
        model = Category
        fields = ['type']