from django.utils.encoding import force_text
from rest_framework.exceptions import APIException
from rest_framework import status


class ICFException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = {'detail': 'A server error occurred.'}

    def __init__(self, detail, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if detail is not None:
            self.detail = {'detail': force_text(detail)}
