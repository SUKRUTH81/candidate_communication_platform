import re

from django.apps import apps
from django.db.models import F, OuterRef, Q, Subquery
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Candidate
from .serializers import BulkDeleteSerializer, CandidateSerializer

PHONE_LIKE = re.compile(r"[+\d\s().-]{2,}")
ORDERING = {
    "name": F("name"), "-name": F("name").desc(),
    "code": F("code"), "-code": F("code").desc(),
    "created_at": F("created_at"), "-created_at": F("created_at").desc(),
    "last_message_at": F("last_message_at").asc(nulls_last=True),
    "-last_message_at": F("last_message_at").desc(nulls_last=True),
}


class CandidateViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CandidateSerializer
    lookup_value_regex = "[0-9a-fA-F-]{36}"

    def get_queryset(self):
        Message = apps.get_model("messaging", "Message")
        latest = (Message.objects.filter(candidate=OuterRef("pk"))
                  .exclude(status__in=["scheduled", "cancelled"]).order_by("-created_at"))
        qs = Candidate.objects.annotate(
            last_message_at=Subquery(latest.values("created_at")[:1]),
            last_message_status=Subquery(latest.values("status")[:1]),
        )
        q = (self.request.query_params.get("search") or "").strip()
        if q:
            cond = Q(name__icontains=q) | Q(code__icontains=q) | Q(email__icontains=q)
            # only treat the query as a phone number if it looks like one (not an ID such as "A2B3C4")
            if PHONE_LIKE.fullmatch(q):
                cond |= Q(phone__contains="".join(ch for ch in q if ch.isdigit()))
            qs = qs.filter(cond)
        ordering = ORDERING.get(self.request.query_params.get("ordering", "name"), ORDERING["name"])
        return qs.order_by(ordering, "id")

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qs = Candidate.objects.filter(id__in=ser.validated_data["ids"])
        count = qs.count()
        qs.delete()
        return Response({"deleted": count})
