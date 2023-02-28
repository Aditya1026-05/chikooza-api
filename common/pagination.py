from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):
    """
    CustomPagination class is used to pagination.
    """

    page_size_query_param = "size"

    def get_paginated_response(self, data):
        return Response(data)
