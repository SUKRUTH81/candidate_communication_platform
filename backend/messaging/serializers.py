from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from candidates.models import Candidate

from . import services
from .models import Message, MessageTemplate, Status


class CandidateBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ["id", "code", "name", "phone", "email"]


class MessageSerializer(serializers.ModelSerializer):
    candidate = CandidateBriefSerializer(read_only=True)
    channel_label = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    max_attempts = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "candidate", "batch_id", "body", "channel", "channel_label", "status", "failure_code",
                  "failure_message", "retryable", "can_retry", "can_cancel", "attempts", "max_attempts",
                  "scheduled_at", "next_attempt_at", "sent_at", "delivered_at", "read_at", "created_at", "updated_at"]

    def get_channel_label(self, m):
        return settings.MESSAGING["CHANNELS"].get(m.channel, {}).get("label", m.channel)

    def get_can_retry(self, m):
        return m.status == Status.FAILED and m.retryable

    def get_can_cancel(self, m):
        return m.status == Status.SCHEDULED

    def get_max_attempts(self, m):
        return settings.MESSAGING["MAX_AUTO_ATTEMPTS"]


class SendMessageSerializer(serializers.Serializer):
    candidate_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    body = serializers.CharField(allow_blank=True, required=False, trim_whitespace=True)
    template_id = serializers.UUIDField(required=False, allow_null=True)
    channel = serializers.CharField(required=False)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_candidate_ids(self, ids):
        cfg = settings.MESSAGING
        ids = list(dict.fromkeys(ids))      # de-duplicate, keep order
        if len(ids) > cfg["MAX_BULK_RECIPIENTS"]:
            raise serializers.ValidationError(f"You can message at most {cfg['MAX_BULK_RECIPIENTS']} candidates at once.")
        return ids

    def validate_channel(self, value):
        if value not in settings.MESSAGING["CHANNELS"]:
            raise serializers.ValidationError("Choose one of: " + ", ".join(settings.MESSAGING["CHANNELS"]))
        return value

    def validate_scheduled_at(self, value):
        if value is None:
            return value
        lead = settings.MESSAGING["MIN_SCHEDULE_LEAD_SECONDS"]
        if value < timezone.now() + timedelta(seconds=lead):
            raise serializers.ValidationError("Pick a time at least a minute from now.")
        if value > timezone.now() + timedelta(days=365):
            raise serializers.ValidationError("Messages can be scheduled up to a year ahead.")
        return value

    def validate(self, attrs):
        template = None
        if attrs.get("template_id"):
            template = MessageTemplate.objects.filter(pk=attrs["template_id"]).first()
            if not template:
                raise serializers.ValidationError({"template_id": "This template no longer exists."})
        body = (attrs.get("body") or (template.body if template else "")).strip()
        if not body:
            raise serializers.ValidationError({"body": "Write a message before sending."})
        if len(body) > settings.MESSAGING["MAX_BODY_LENGTH"]:
            raise serializers.ValidationError({"body": f"Messages can be at most {settings.MESSAGING['MAX_BODY_LENGTH']} characters."})
        services.validate_body(body)
        found = Candidate.objects.in_bulk(attrs["candidate_ids"])
        missing = [str(i) for i in attrs["candidate_ids"] if i not in found]
        if missing:
            raise serializers.ValidationError({"candidate_ids": f"{len(missing)} selected candidate(s) no longer exist. Refresh the list and try again."})
        attrs.update(body=body, template=template, candidates=[found[i] for i in attrs["candidate_ids"]],
                     channel=attrs.get("channel") or settings.MESSAGING["DEFAULT_CHANNEL"])
        return attrs


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = ["id", "name", "body", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = " ".join(value.split())
        qs = MessageTemplate.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a template with this name.")
        return value

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Template text can't be empty.")
        if len(value) > settings.MESSAGING["MAX_BODY_LENGTH"]:
            raise serializers.ValidationError(f"Keep templates under {settings.MESSAGING['MAX_BODY_LENGTH']} characters.")
        bad = services.unknown_placeholders(value)
        if bad:
            raise serializers.ValidationError(f"Unknown placeholder(s): {', '.join('{{' + b + '}}' for b in bad)}.")
        return value
