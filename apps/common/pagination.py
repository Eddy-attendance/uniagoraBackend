from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination

from .response import success_response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Default `DEFAULT_PAGINATION_CLASS`. `page_size` defaults to 20 as a
    sensible marketplace-browse default; clients may request up to
    `max_page_size` via `?page_size=`.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return success_response(
            data=OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
