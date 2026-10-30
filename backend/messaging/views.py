import hashlib
import hmac
import json
import logging
from collections import Counter

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status as http, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from candidates.models import Candidate

from . import services
from .models import Batch, Message, MessageTemplate, Status
from .serializers import MessageSerializer, SendMessageSerializer, TemplateSerializer

log = logging.getLogger(__name__)
UUID_RE = "[0-9a-fA-F-]{36}"
VALID_STATUSES = {s.value for s in Status}


def _summary(messages):
    c = Counter(m.status for m in messages)
    return {"total": len(messages), "by_status": dict(c),
            "failed": c[Status.FAILED], "scheduled": c[Status.SCHEDULED],
            "in_progress": c[Status.QUEUED] + c[Status.SENDING] + c[Status.SENT],
            "succeeded": c[Status.DELIVERED] + c[Status.READ]}


class MessageViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = MessageSerializer
    lookup_value_regex = UUID_RE

    def get_queryset(self):
        qs = Message.objects.select_related("candidate").order_by("-created_at", "id")
        p = self.request.query_params
        if p.get("status"):
            statuses = [s for s in p["status"].split(",") if s in VALID_STATUSES]
            qs = qs.filter(status__in=statuses)
        if p.get("candidate"):
            qs = qs.filter(candidate_id=p["candidate"])
        if p.get("batch"):
            qs = qs.filter(batch_id=p["batch"])
        if p.get("ids"):
            qs = qs.filter(id__in=[i for i in p["ids"].split(",") if i])
        if p.get("channel"):
            qs = qs.filter(channel=p["channel"])
        if p.get("search"):
            s = p["search"].strip()
            qs = qs.filter(Q(candidate__name__icontains=s) | Q(body__icontains=s))
        if p.get("ordering") == "scheduled_at":
            qs = qs.order_by("scheduled_at", "id")
        return qs

    def create(self, request):
        ser = SendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        batch, messages = services.create_messages(candidates=d["candidates"], body=d["body"], channel=d["channel"],
                                                   scheduled_at=d.get("scheduled_at"), template=d["template"])
        for m in messages:      # bulk_create doesn't populate relations for serialization
            m.candidate = next(c for c in d["candidates"] if c.pk == m.candidate_id)
        return Response({"batch_id": batch.id, "summary": _summary(messages),
                         "results": MessageSerializer(messages, many=True).data}, status=http.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        return Response(MessageSerializer(services.retry_message(get_object_or_404(Message, pk=pk).pk)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return Response(MessageSerializer(services.cancel_message(get_object_or_404(Message, pk=pk).pk)).data)

    @action(detail=False, methods=["post"], url_path="retry")
    def retry_many(self, request):
        ids = request.data.get("message_ids")
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"message_ids": "Select at least one message."})
        out = []
        for mid in ids:
            try:
                m = services.retry_message(mid)
                out.append({"id": str(m.id), "ok": True, "status": m.status})
            except Exception as e:   # per-item result; one failure must not abort the rest
                out.append({"id": str(mid), "ok": False, "error": str(getattr(e, "detail", e))})
        return Response({"results": out, "retried": sum(r["ok"] for r in out)})


class BatchView(APIView):
    """Polled by the UI after a bulk send to show per-candidate results."""

    def get(self, request, pk):
        if not Batch.objects.filter(pk=pk).exists():
            raise NotFound("Batch not found.")
        messages = list(Message.objects.filter(batch_id=pk).select_related("candidate").order_by("candidate__name"))
        return Response({"batch_id": pk, "summary": _summary(messages),
                         "results": MessageSerializer(messages, many=True).data})


class CandidateHistoryView(ListAPIView):
    """Communication history, most recent first."""
    serializer_class = MessageSerializer

    def get_queryset(self):
        get_object_or_404(Candidate, pk=self.kwargs["pk"])
        return Message.objects.filter(candidate_id=self.kwargs["pk"]).exclude(status=Status.CANCELLED) \
            .select_related("candidate").order_by("-created_at", "id")


class TemplateViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateSerializer
    queryset = MessageTemplate.objects.all()
    lookup_value_regex = UUID_RE
    pagination_class = None


class MetaView(APIView):
    def get(self, request):
        cfg = settings.MESSAGING
        return Response({
            "channels": [{"id": k, "label": v["label"], "recipient": v["recipient"]} for k, v in cfg["CHANNELS"].items()],
            "default_channel": cfg["DEFAULT_CHANNEL"],
            "max_body_length": cfg["MAX_BODY_LENGTH"],
            "max_bulk_recipients": cfg["MAX_BULK_RECIPIENTS"],
            "placeholders": [{"key": k, "label": v[0]} for k, v in services.PLACEHOLDERS.items()],
        })


class HealthView(APIView):
    def get(self, request):
        return Response(services.health_summary())


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def provider_webhook(request):
    """Provider -> platform status updates. Signed, idempotent, tolerant of reordering."""
    raw = request.body
    expected = "sha256=" + hmac.new(settings.WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Provider-Signature", "")):
        return Response({"error": {"code": "bad_signature", "message": "Invalid signature."}}, status=http.HTTP_401_UNAUTHORIZED)
    try:
        data = json.loads(raw)
        event_id, status, mid = data["event_id"], data["status"], data.get("message_id")
    except (ValueError, KeyError, TypeError):
        return Response({"error": {"code": "bad_payload", "message": "event_id and status are required."}}, status=http.HTTP_400_BAD_REQUEST)
    ref = data.get("reference")
    result = services.apply_provider_event(event_id=event_id, status=status, provider_message_id=mid, reference=ref,
                                           error=data.get("error"), payload=data,
                                           when=parse_datetime(data.get("timestamp") or "") or None)
    if result == "unknown":
        log.warning("Webhook for unknown message %s / %s", mid, ref)
    # 200 for everything we understood so the provider stops retrying duplicates / unknown ids
    return Response({"result": result})
