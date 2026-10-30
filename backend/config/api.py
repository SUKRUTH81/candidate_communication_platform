"""Shared API plumbing: one consistent error envelope and one pagination shape."""
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "results": data,
        })


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "This action conflicts with the current state."


def _flatten(detail):
    """DRF error detail -> {field: first message}."""
    if isinstance(detail, dict):
        return {k: _flatten(v) for k, v in detail.items()}
    if isinstance(detail, list):
        return _flatten(detail[0]) if detail and not isinstance(detail[0], (dict, list)) else [_flatten(d) for d in detail]
    return str(detail)


def exception_handler(exc, context):
    """{"error": {"code", "message", "fields"?}} for every failure the client can see."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        fields = _flatten(exc.detail) if isinstance(exc.detail, dict) else {}
        non_field = fields.pop("non_field_errors", None) if isinstance(fields, dict) else None
        message = non_field or ("Please fix the highlighted fields." if fields else _flatten(exc.detail))
        if isinstance(message, list):
            message = message[0]
        body = {"code": "validation_error", "message": message}
        if fields:
            body["fields"] = fields
    else:
        detail = response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data
        body = {"code": getattr(exc, "default_code", "error"), "message": str(detail)}
    response.data = {"error": body}
    return response
