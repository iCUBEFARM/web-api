from icf import settings


class AutosuggestionMixin(object):
    def get_default_queryset(self, queryset):
        # return queryset[:getattr(settings, 'ICF_DEFAULT_AUTOSUGGESTION_LIMIT', 10)]
        return queryset
