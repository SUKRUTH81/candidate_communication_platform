"""
Messaging domain logic. Views and the worker stay thin and call into here.

Lifecycle:
  scheduled -> queued -> sending -> sent -> delivered -> read
                 ^          |  \\-> failed (retryable / permanent)
                 \\_ auto-retry with backoff for temporary provider failures
"""
import logging
import re
import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from config.api import Conflict

from .models import IN_FLIGHT, PROGRESS_RANK, Batch, Message, MessageEvent, Status, WorkerHeartbeat
from .providers.base import ProviderError
from .providers.registry import all_providers, channels, get_provider

log = logging.getLogger(__name__)
CFG = lambda: settings.MESSAGING  # noqa: E731  (read lazily so tests can override settings)

# ---- Failure catalogue: code -> (what the recruiter sees, can it be retried?) -------------
FAILURES = {
    "INVALID_RECIPIENT": ("The candidate's phone number or email isn't valid, so nothing could be sent. Fix their contact details and send a new message.", False),
    "RECIPIENT_BLOCKED": ("This candidate has opted out of receiving messages.", False),
    "NO_EMAIL": ("This candidate has no email address on file. Add one or choose another channel.", False),
    "EMPTY_BODY": ("The message was empty after filling in the candidate's details.", False),
    "BODY_TOO_LONG": ("The message is too long for this channel.", False),
    "INVALID_CHANNEL": ("This communication channel isn't supported.", False),
    "UNAUTHORISED": ("The messaging service rejected our credentials. Please contact your administrator.", False),
    "RATE_LIMITED": ("The messaging service is busy right now (rate limit reached).", True),
    "TEMPORARY_FAILURE": ("The messaging service had a temporary problem.", True),
    "SERVICE_UNAVAILABLE": ("The messaging service is currently unavailable.", True),
    "TIMEOUT": ("The messaging service took too long to respond.", True),
    "UNREACHABLE": ("Delivery failed: the candidate's phone couldn't be reached (it may be switched off or out of coverage).", True),
    "UNKNOWN": ("Something went wrong while sending this message.", True),
}
AUTO_RETRY_CODES = {"RATE_LIMITED", "TEMPORARY_FAILURE", "SERVICE_UNAVAILABLE", "TIMEOUT"}
OUR_SIDE_CODES = {"SERVICE_UNAVAILABLE", "TIMEOUT"}   # we gave up, but the provider may still have accepted it


def describe_failure(code):
    return FAILURES.get(code, FAILURES["UNKNOWN"])


# ---- Templates / placeholders ----------------------------------------------------------------
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_]+)\s*\}\}")
PLACEHOLDERS = {
    "name": ("Full name", lambda c: c.name),
    "first_name": ("First name", lambda c: c.name.split()[0]),
    "phone": ("Phone number", lambda c: c.phone),
    "email": ("Email", lambda c: c.email),
    "candidate_id": ("Candidate ID", lambda c: c.code),
}


def unknown_placeholders(body):
    return sorted({m for m in PLACEHOLDER_RE.findall(body) if m not in PLACEHOLDERS})


def render_body(body, candidate):
    return PLACEHOLDER_RE.sub(lambda m: PLACEHOLDERS[m.group(1)][1](candidate), body)


def validate_body(body):
    bad = unknown_placeholders(body)
    if bad:
        raise ValidationError({"body": f"Unknown placeholder(s): {', '.join('{{' + b + '}}' for b in bad)}. "
                                       f"Available: {', '.join('{{' + k + '}}' for k in PLACEHOLDERS)}."})


# ---- Creating messages -------------------------------------------------------------------------
def recipient_for(candidate, channel):
    return getattr(candidate, channels()[channel]["recipient"])


def _precheck(candidate, channel, rendered):
    if not recipient_for(candidate, channel):
        return "NO_EMAIL" if channels()[channel]["recipient"] == "email" else "INVALID_RECIPIENT"
    if not rendered.strip():
        return "EMPTY_BODY"
    if len(rendered) > CFG()["MAX_BODY_LENGTH"]:
        return "BODY_TOO_LONG"
    return None


@transaction.atomic
def create_messages(*, candidates, body, channel, scheduled_at=None, template=None):
    """Persist one Message per candidate. Nothing is sent here; the worker does that, so a slow or
    broken provider can never fail (or slow down) the HTTP request, and one candidate's problem
    never affects the others."""
    batch = Batch.objects.create()
    now = timezone.now()
    messages = []
    for c in candidates:
        rendered = render_body(body, c)
        m = Message(candidate=c, batch=batch, template=template, body=rendered, channel=channel, scheduled_at=scheduled_at)
        problem = _precheck(c, channel, rendered)
        if problem:
            m.status, m.failure_code = Status.FAILED, problem
            m.failure_message, m.retryable = describe_failure(problem)[0], False
        elif scheduled_at:
            m.status, m.next_attempt_at = Status.SCHEDULED, scheduled_at
        else:
            m.status, m.next_attempt_at = Status.QUEUED, now
        messages.append(m)
    Message.objects.bulk_create(messages)
    return batch, messages


# ---- Sending (called by the worker) --------------------------------------------------------------
def claim(message_id):
    now = timezone.now()
    return Message.objects.filter(
        id=message_id, status__in=[Status.QUEUED, Status.SCHEDULED], next_attempt_at__lte=now
    ).update(status=Status.SENDING, locked_at=now, attempts=F("attempts") + 1) == 1


def process_message(message_id):
    """Send one message. Returns (outcome, error_code). Never raises for provider problems."""
    if not claim(message_id):
        return "skipped", None
    m = Message.objects.select_related("candidate").get(pk=message_id)
    now = timezone.now()
    try:
        provider = get_provider(m.channel)
        result = provider.send(to=recipient_for(m.candidate, m.channel), body=m.body, channel=m.channel,
                               reference=str(m.id), idempotency_key=f"{m.id}:{m.send_round}")
    except ProviderError as e:
        _handle_send_error(m, e, now)
        return ("retry" if m.status == Status.QUEUED else "failed"), e.code
    except Exception:  # a bug or surprise must not wedge the message in 'sending'
        log.exception("Unexpected error sending message %s", m.id)
        _handle_send_error(m, ProviderError("UNKNOWN", "unexpected error"), now)
        return "failed", "UNKNOWN"

    with transaction.atomic():
        m = Message.objects.select_for_update().get(pk=message_id)
        if m.provider_message_id is None:
            m.provider_message_id = result.provider_message_id
        if m.status == Status.SENDING:      # a webhook may already have advanced it; never move backwards
            m.status, m.sent_at = Status.SENT, m.sent_at or now
        m.failure_code, m.failure_message, m.retryable, m.locked_at = "", "", False, None
        m.save()
    return "sent", None


def _handle_send_error(m, e, now):
    friendly, retryable = describe_failure(e.code)
    cfg = CFG()
    with transaction.atomic():
        m = Message.objects.select_for_update().get(pk=m.pk)
        if m.status != Status.SENDING:
            return
        m.failure_code, m.locked_at = e.code, None
        if e.code in AUTO_RETRY_CODES and m.attempts < cfg["MAX_AUTO_ATTEMPTS"]:
            delay = max(e.retry_after or 0, cfg["BACKOFF_BASE_SECONDS"] * 2 ** (m.attempts - 1))
            m.status, m.next_attempt_at, m.retryable = Status.QUEUED, now + timedelta(seconds=delay), True
            m.failure_message = f"{friendly} Retrying automatically (attempt {m.attempts} of {cfg['MAX_AUTO_ATTEMPTS']})."
        else:
            m.status, m.retryable = Status.FAILED, retryable
            m.failure_message = friendly + (" We stopped retrying automatically; you can retry it manually." if retryable else "")
        m.save()
    log.warning("Message %s: %s (%s) -> %s", m.pk, e.code, e.detail, m.status)


class CircuitBreaker:
    """If the provider is clearly down, stop hammering it and don't burn retry attempts."""

    def __init__(self, threshold=3, cooldown=10):
        self.threshold, self.cooldown, self.failures, self.open_until = threshold, cooldown, 0, 0.0

    @property
    def is_open(self):
        return time.monotonic() < self.open_until

    def record(self, code):
        if code in OUR_SIDE_CODES:
            self.failures += 1
            if self.failures >= self.threshold:
                self.open_until = time.monotonic() + self.cooldown
                log.error("Provider looks down; pausing sends for %ss", self.cooldown)
        else:
            self.failures = 0


def run_due_messages(breaker=None, limit=50):
    breaker = breaker or CircuitBreaker()
    ids = list(Message.objects.filter(status__in=[Status.QUEUED, Status.SCHEDULED], next_attempt_at__lte=timezone.now())
               .order_by("next_attempt_at").values_list("id", flat=True)[:limit])
    done = 0
    for mid in ids:
        if breaker.is_open:
            break
        outcome, code = process_message(mid)
        if outcome != "skipped":
            breaker.record(code if outcome != "sent" else None)
            done += 1
    return done


def recover_stale():
    cutoff = timezone.now() - timedelta(seconds=CFG()["STALE_SENDING_SECONDS"])
    return Message.objects.filter(status=Status.SENDING, locked_at__lt=cutoff).update(
        status=Status.QUEUED, next_attempt_at=timezone.now(), locked_at=None)


def beat():
    WorkerHeartbeat.objects.update_or_create(id=1, defaults={"seen_at": timezone.now()})


def worker_alive(max_age=15):
    hb = WorkerHeartbeat.objects.filter(id=1).first()
    return bool(hb and (timezone.now() - hb.seen_at).total_seconds() < max_age)


# ---- Status updates (webhooks + reconciliation) ----------------------------------------------------
def _transition(m, new, error, when):
    """Apply a provider status to a message. Returns True if the message changed.
    Rules make updates idempotent and order-independent: progress only moves forward, and a
    message that was delivered/read can't later 'fail'."""
    cur = m.status
    if new == Status.FAILED:
        if cur not in IN_FLIGHT:
            return False
        code = (error or {}).get("code") or "UNKNOWN"
        friendly, retryable = describe_failure(code)
        m.status, m.failure_code, m.failure_message, m.retryable, m.locked_at = Status.FAILED, code, friendly, retryable, None
        return True
    if new not in PROGRESS_RANK:
        return False
    revive = cur == Status.FAILED and m.failure_code in OUR_SIDE_CODES   # we gave up too early; provider did accept it
    if not (cur in (Status.QUEUED, Status.SENDING) or revive or (cur in PROGRESS_RANK and PROGRESS_RANK[new] > PROGRESS_RANK[cur])):
        return False
    rank = PROGRESS_RANK[new]
    m.status = new
    m.sent_at = m.sent_at or when
    if rank >= 2:
        m.delivered_at = m.delivered_at or when
    if rank >= 3:
        m.read_at = m.read_at or when
    m.failure_code, m.failure_message, m.retryable, m.locked_at = "", "", False, None
    return True


def apply_provider_event(*, event_id, status, provider_message_id=None, reference=None, error=None, payload=None, when=None):
    """Idempotent. Returns 'applied' | 'ignored' | 'duplicate' | 'unknown'."""
    when = when or timezone.now()
    with transaction.atomic():
        qs = Message.objects.select_for_update()
        m = None
        if provider_message_id:
            m = qs.filter(provider_message_id=provider_message_id).first()
        if m is None and reference:
            # webhook can beat our own "save provider id" step; our id travels as the reference
            try:
                m = qs.filter(pk=uuid.UUID(str(reference))).first()
            except ValueError:
                m = None
        if m is None:
            return "unknown"
        event, created = MessageEvent.objects.get_or_create(
            provider_event_id=event_id, defaults={"message": m, "status": status, "payload": payload or {}})
        if not created:
            return "duplicate"
        changed = _transition(m, status, error, when)
        if changed:
            if m.provider_message_id is None and provider_message_id:
                m.provider_message_id = provider_message_id
            m.save()
        event.applied = changed
        event.save(update_fields=["applied"])
    return "applied" if changed else "ignored"


def reconcile(limit=50):
    """Safety net for lost webhooks: ask the provider about messages that look stuck."""
    cfg = CFG()
    cutoff = timezone.now() - timedelta(seconds=cfg["RECONCILE_AFTER_SECONDS"])
    due = (Message.objects.filter(status__in=[Status.SENT, Status.DELIVERED], provider_message_id__isnull=False,
                                  updated_at__lt=cutoff, created_at__gt=timezone.now() - timedelta(hours=24))
           .exclude(last_reconciled_at__gt=cutoff).order_by("updated_at")[:limit])
    n = 0
    for m in due:
        Message.objects.filter(pk=m.pk).update(last_reconciled_at=timezone.now())
        try:
            remote = get_provider(m.channel).fetch_status(m.provider_message_id)
        except ProviderError:
            continue
        err = {"code": remote.error_code, "message": remote.error_message} if remote.error_code else None
        if apply_provider_event(event_id=f"recon:{m.provider_message_id}:{remote.status}", status=remote.status,
                                provider_message_id=m.provider_message_id, error=err) == "applied":
            n += 1
    return n


# ---- Retry / cancel -----------------------------------------------------------------------------------
def retry_message(message_id):
    with transaction.atomic():
        m = Message.objects.select_for_update().select_related("candidate").get(pk=message_id)
        if m.status != Status.FAILED:
            raise Conflict("Only failed messages can be retried.")
        if not m.retryable:
            raise Conflict(f"This message can't be retried: {m.failure_message} Send a new message instead.")
        problem = _precheck(m.candidate, m.channel, m.body)
        if problem:
            raise Conflict(describe_failure(problem)[0])
        m.status, m.attempts, m.send_round = Status.QUEUED, 0, m.send_round + 1
        m.next_attempt_at, m.provider_message_id = timezone.now(), None
        m.failure_code = m.failure_message = ""
        m.retryable = False
        m.save()
    return m


def cancel_message(message_id):
    with transaction.atomic():
        m = Message.objects.select_for_update().get(pk=message_id)
        if m.status != Status.SCHEDULED:
            raise Conflict("Only scheduled messages can be cancelled. This one has already been picked up for sending.")
        m.status, m.next_attempt_at = Status.CANCELLED, None
        m.save()
    return m


# ---- Provider health ------------------------------------------------------------------------------------
def health_summary():
    now = timezone.now()
    counts = {}
    for row in Message.objects.values("status").annotate(n=Count("id")):
        counts[row["status"]] = row["n"]
    g = lambda *s: sum(counts.get(x, 0) for x in s)  # noqa: E731
    providers = []
    for provider, chans in all_providers():
        h = provider.health()
        providers.append({"name": provider.name, "channels": chans, "operational": h.ok, "detail": h.detail})
    recent = Message.objects.filter(created_at__gt=now - timedelta(hours=1))
    recent_failed = recent.filter(status=Status.FAILED).count()
    recent_total = recent.exclude(status__in=[Status.SCHEDULED, Status.CANCELLED]).count()
    if any(not p["operational"] for p in providers):
        status = "outage"
    elif recent_total >= 5 and recent_failed / recent_total > 0.25:
        status = "degraded"
    else:
        status = "operational"
    return {
        "status": status,
        "checked_at": now,
        "worker_running": worker_alive(),
        "providers": providers,
        "totals": {
            "sent": g("sent", "delivered", "read"),
            "delivered": g("delivered", "read"),
            "read": g("read"),
            "failed": g("failed"),
            "pending": g("queued", "sending"),
            "scheduled": g("scheduled"),
        },
    }
