"""Paginacja publicznego API bloga."""

from rest_framework.pagination import PageNumberPagination


class PostPagination(PageNumberPagination):
    """5 postów na stronę — kontrakt `docs/tasks/8-publiczne-api.md`."""

    page_size = 5
