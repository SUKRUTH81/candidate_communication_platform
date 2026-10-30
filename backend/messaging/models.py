import uuid

from django.db import models
from django.utils import timezone


class Status(models.TextChoices):
    SCHEDULED = "scheduled"   # waiting for its send time
    QUEUED = "queued"         # waiting for the worker (or waiting to be retried)
    SENDING = "sending"       # claimed by the worker, request to provider in flight
    SENT = "sent"             # accepted by provider / handed to the network
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Forward-only progress of a message that the provider has accepted.
PROGRESS_RANK = {Status.SENT: 1, Status.DELIVERED: 2, Status.READ: 3}
IN_FLIGHT = (Status.QUEUED, Status.SENDING, Status.SENT)


class Batch(models.Model):
    """One user action 'send this to N candidates'."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)


class MessageTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="messages")
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")
    template = models.ForeignKey(MessageTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    body = models.TextField()                      # already rendered for this candidate
    channel = models.CharField(max_length=20)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED, db_index=True)

    provider_message_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    failure_code = models.CharField(max_length=40, blank=True, default="")
    failure_message = models.CharField(max_length=300, blank=True, default="")   # recruiter-friendly
    retryable = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)      # automatic attempts in the current round
    send_round = models.PositiveSmallIntegerField(default=0)    # bumped by manual retries; part of the idempotency key

    scheduled_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)   # when the worker may pick it up
    locked_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    last_reconciled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "next_attempt_at"]),
                   models.Index(fields=["candidate", "-created_at"])]


class MessageEvent(models.Model):
    """Every status notification we received. The unique event id makes webhooks idempotent."""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="events")
    provider_event_id = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=12)
    applied = models.BooleanField(default=False)    # False = duplicate / out-of-order, kept for audit
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)


class WorkerHeartbeat(models.Model):
    """Single row so the API can tell whether the background worker is alive."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    seen_at = models.DateTimeField(default=timezone.now)
