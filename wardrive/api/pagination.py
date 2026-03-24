from rest_framework import pagination


class CustomPagination(pagination.PageNumberPagination):
    """
    REST API pagination parameter configuration.
    Default and field names:
    * search = text for search
    * page = page number
    * page_size = page size
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"


class MapPlacesPagination(pagination.PageNumberPagination):
    """
    Pagination for map point listings (WiFi/LTE).
    Allows large page sizes without changing defaults for the rest of the API.
    """

    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 2000
    page_query_param = "page"
