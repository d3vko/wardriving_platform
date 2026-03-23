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
    Paginación para listados de puntos en mapa (WiFi/LTE).
    Permite pedir muchos marcadores por página sin afectar al resto de la API.
    """

    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 2000
    page_query_param = "page"
