from django.conf import settings


class ICFListMixin(object):

    def get_queryset(self):
        queryset = self.queryset

        # If the user is not logged in, return one page, otherwise all pages
        if not self.request.user.is_authenticated:
            page_size = settings.REST_FRAMEWORK.get('PAGE_SIZE', 15)
            queryset = queryset.filter()[:page_size]

        return queryset
