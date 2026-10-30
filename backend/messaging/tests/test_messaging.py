import hashlib
import hmac
import json
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from messaging import services
from messaging.models import Message, MessageEvent, Status
from messaging.providers.base import Health, ProviderError, RemoteStatus, SendResult


class FakeProvider:
    """Scriptable provider. `script` maps recipient -> list of outcomes (exceptions are raised)."""
    name = "fake"

    def __init__(self):
        self.script, self.sent, self.remote = {}, [], {}

    def send(self, *, to, body, channel, reference, idempotency_key):
        steps = self.script.get(to)
        if steps:
            step = steps.pop(0) if len(steps) > 1 else steps[0]
            if isinstance(step, Exception):
                raise step
        self.sent.append({"to": to, "body": body, "key": idempotency_key, "reference": reference})
        return SendResult(provider_message_id=f"pm_{len(self.sent)}")

    def fetch_status(self, pid):
        return self.remote.get(pid, RemoteStatus("sent"))

    def health(self):
        return Health(ok=True)


@pytest.fixture
def fake(monkeypatch):
    f = FakeProvider()
    monkeypatch.setattr(services, "get_provider", lambda channel: f)
    monkeypatch.setattr(services, "all_providers", lambda: [(f, ["whatsapp", "sms", "email"])])
    return f


def send_payload(cands, **kw):
    return {"candidate_ids": [str(c.id) for c in cands], "body": "Hi {{first_name}}, interview tomorrow.", **kw}


def webhook(api, payload, secret=None):
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new((secret or settings.WEBHOOK_SECRET).encode(), raw, hashlib.sha256).hexdigest()
    return api.post("/api/webhooks/provider/", data=raw, content_type="application/json", HTTP_X_PROVIDER_SIGNATURE=sig)


def run_all():
    while services.run_due_messages():
        pass


@pytest.mark.django_db
class TestSending:
    def test_single_send_personalises_and_goes_through_provider(self, api, make_candidate, fake):
        c = make_candidate("Rahul Sharma")
        r = api.post("/api/messages/", send_payload([c]), format="json")
        assert r.status_code == 201
        assert r.data["results"][0]["status"] == "queued"
        run_all()
        m = Message.objects.get()
        assert m.status == Status.SENT and m.provider_message_id == "pm_1"
        assert fake.sent[0]["body"] == "Hi Rahul, interview tomorrow."
        assert fake.sent[0]["reference"] == str(m.id)

    def test_bulk_failure_is_isolated_per_candidate(self, api, make_candidate, fake):
        a, b, c = make_candidate("A One"), make_candidate("B Two"), make_candidate("C Three")
        fake.script[b.phone] = [ProviderError("INVALID_RECIPIENT")]
        r = api.post("/api/messages/", send_payload([a, b, c]), format="json")
        assert r.data["summary"]["total"] == 3
        run_all()
        st = {m.candidate.name: m.status for m in Message.objects.select_related("candidate")}
        assert st == {"A One": "sent", "B Two": "failed", "C Three": "sent"}
        failed = Message.objects.get(candidate=b)
        assert failed.retryable is False and "isn't valid" in failed.failure_message

    def test_channel_without_recipient_fails_only_that_candidate(self, api, make_candidate, fake):
        with_mail, without = make_candidate("Has Mail"), make_candidate("No Mail", email="")
        r = api.post("/api/messages/", send_payload([with_mail, without], channel="email"), format="json")
        by = {x["candidate"]["name"]: x for x in r.data["results"]}
        assert by["Has Mail"]["status"] == "queued"
        assert by["No Mail"]["status"] == "failed" and by["No Mail"]["failure_code"] == "NO_EMAIL"
        assert by["No Mail"]["can_retry"] is False

    def test_validation(self, api, make_candidate, fake):
        c = make_candidate()
        assert api.post("/api/messages/", {"candidate_ids": [], "body": "x"}, format="json").status_code == 400
        r = api.post("/api/messages/", {"candidate_ids": [str(c.id)], "body": "   "}, format="json")
        assert r.data["error"]["fields"]["body"]
        r = api.post("/api/messages/", {"candidate_ids": [str(c.id)], "body": "Hi {{nope}}"}, format="json")
        assert "nope" in r.data["error"]["fields"]["body"]
        r = api.post("/api/messages/", {"candidate_ids": [str(c.id)], "body": "x" * 1601}, format="json")
        assert r.status_code == 400
        r = api.post("/api/messages/", {"candidate_ids": [str(c.id)], "body": "x", "channel": "pigeon"}, format="json")
        assert r.data["error"]["fields"]["channel"]
        r = api.post("/api/messages/", {"candidate_ids": ["00000000-0000-0000-0000-000000000001"], "body": "x"}, format="json")
        assert "no longer exist" in r.data["error"]["fields"]["candidate_ids"]
        assert Message.objects.count() == 0

    def test_duplicate_candidate_ids_send_once(self, api, make_candidate, fake):
        c = make_candidate()
        api.post("/api/messages/", {"candidate_ids": [str(c.id)] * 3, "body": "x"}, format="json")
        assert Message.objects.count() == 1


@pytest.mark.django_db
class TestRetries:
    def test_temporary_failure_backs_off_then_succeeds(self, api, make_candidate, fake):
        c = make_candidate()
        fake.script[c.phone] = [ProviderError("TEMPORARY_FAILURE"), SendResult("ok")]
        api.post("/api/messages/", send_payload([c]), format="json")
        run_all()
        m = Message.objects.get()
        assert m.status == Status.QUEUED and m.attempts == 1 and m.next_attempt_at > timezone.now()
        assert "Retrying automatically" in m.failure_message
        assert services.run_due_messages() == 0               # not due yet
        Message.objects.update(next_attempt_at=timezone.now())
        run_all()
        m.refresh_from_db()
        assert m.status == Status.SENT and m.failure_message == ""

    def test_gives_up_after_max_attempts_and_allows_manual_retry(self, api, make_candidate, fake):
        c = make_candidate()
        fake.script[c.phone] = [ProviderError("SERVICE_UNAVAILABLE")]
        api.post("/api/messages/", send_payload([c]), format="json")
        for _ in range(settings.MESSAGING["MAX_AUTO_ATTEMPTS"]):
            Message.objects.update(next_attempt_at=timezone.now())
            services.run_due_messages()
        m = Message.objects.get()
        assert m.status == Status.FAILED and m.retryable and m.attempts == 4
        fake.script[c.phone] = [SendResult("ok")]
        r = api.post(f"/api/messages/{m.id}/retry/")
        assert r.status_code == 200 and r.data["status"] == "queued"
        run_all()
        m.refresh_from_db()
        assert m.status == Status.SENT
        assert fake.sent[-1]["key"].endswith(":1")   # new idempotency key -> provider really re-sends

    def test_rate_limit_honours_retry_after(self, api, make_candidate, fake):
        c = make_candidate()
        fake.script[c.phone] = [ProviderError("RATE_LIMITED", retry_after=120)]
        api.post("/api/messages/", send_payload([c]), format="json")
        services.run_due_messages()
        m = Message.objects.get()
        assert m.next_attempt_at > timezone.now() + timedelta(seconds=100)

    def test_permanent_failure_cannot_be_retried(self, api, make_candidate, fake):
        c = make_candidate()
        fake.script[c.phone] = [ProviderError("INVALID_RECIPIENT")]
        api.post("/api/messages/", send_payload([c]), format="json")
        run_all()
        m = Message.objects.get()
        assert m.status == Status.FAILED and m.attempts == 1 and not m.retryable
        r = api.post(f"/api/messages/{m.id}/retry/")
        assert r.status_code == 409 and "can't be retried" in r.data["error"]["message"]

    def test_only_failed_can_be_retried(self, api, make_candidate, fake):
        m = Message.objects.create(candidate=make_candidate(), body="x", channel="sms", status=Status.DELIVERED)
        assert api.post(f"/api/messages/{m.id}/retry/").status_code == 409

    def test_retry_many_reports_each(self, api, make_candidate, fake):
        a, b = make_candidate("A"), make_candidate("B")
        ok = Message.objects.create(candidate=a, body="x", channel="sms", status=Status.FAILED, retryable=True, failure_code="TIMEOUT")
        no = Message.objects.create(candidate=b, body="x", channel="sms", status=Status.FAILED, retryable=False, failure_code="INVALID_RECIPIENT")
        r = api.post("/api/messages/retry/", {"message_ids": [str(ok.id), str(no.id)]}, format="json")
        assert [x["ok"] for x in r.data["results"]] == [True, False] and r.data["retried"] == 1

    def test_circuit_breaker_pauses_without_burning_attempts(self, api, make_candidate, fake):
        cs = [make_candidate(f"P{i}") for i in range(6)]
        for c in cs:
            fake.script[c.phone] = [ProviderError("SERVICE_UNAVAILABLE")]
        api.post("/api/messages/", send_payload(cs), format="json")
        breaker = services.CircuitBreaker(threshold=3, cooldown=60)
        services.run_due_messages(breaker)
        assert breaker.is_open
        assert Message.objects.filter(attempts=0).count() == 3     # untouched, will be sent once the provider is back

    def test_stale_sending_is_recovered(self, make_candidate, fake):
        m = Message.objects.create(candidate=make_candidate(), body="x", channel="sms", status=Status.SENDING,
                                   locked_at=timezone.now() - timedelta(minutes=5))
        assert services.recover_stale() == 1
        m.refresh_from_db()
        assert m.status == Status.QUEUED


@pytest.mark.django_db
class TestScheduling:
    def test_past_or_too_soon_rejected(self, api, make_candidate, fake):
        c = make_candidate()
        soon = (timezone.now() + timedelta(seconds=5)).isoformat()
        r = api.post("/api/messages/", send_payload([c], scheduled_at=soon), format="json")
        assert r.status_code == 400 and "scheduled_at" in r.data["error"]["fields"]

    def test_scheduled_waits_then_sends_and_can_be_cancelled(self, api, make_candidate, fake):
        c = make_candidate()
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = api.post("/api/messages/", send_payload([c], scheduled_at=when), format="json")
        assert r.data["results"][0]["status"] == "scheduled"
        assert services.run_due_messages() == 0 and fake.sent == []
        mid = r.data["results"][0]["id"]
        Message.objects.update(next_attempt_at=timezone.now() - timedelta(seconds=1))
        run_all()
        assert Message.objects.get(pk=mid).status == Status.SENT
        assert api.post(f"/api/messages/{mid}/cancel/").status_code == 409

    def test_cancel(self, api, make_candidate, fake):
        c = make_candidate()
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        mid = api.post("/api/messages/", send_payload([c], scheduled_at=when), format="json").data["results"][0]["id"]
        assert api.post(f"/api/messages/{mid}/cancel/").data["status"] == "cancelled"
        Message.objects.update(next_attempt_at=timezone.now())
        assert services.run_due_messages() == 0


@pytest.mark.django_db
class TestWebhooks:
    def make(self, make_candidate, status=Status.SENT, pid="pm_x"):
        return Message.objects.create(candidate=make_candidate(), body="x", channel="sms", status=status, provider_message_id=pid)

    def test_rejects_bad_signature(self, api):
        r = webhook(api, {"event_id": "e1", "status": "delivered", "message_id": "pm_x"}, secret="wrong")
        assert r.status_code == 401

    def test_rejects_malformed(self, api):
        assert webhook(api, {"nope": 1}).status_code == 400

    def test_progress_and_duplicate_delivery_is_idempotent(self, api, make_candidate):
        m = self.make(make_candidate)
        p = {"event_id": "e1", "status": "delivered", "message_id": "pm_x"}
        assert webhook(api, p).data["result"] == "applied"
        assert webhook(api, p).data["result"] == "duplicate"
        assert webhook(api, {**p, "event_id": "e2"}).data["result"] == "ignored"   # same status, new event id
        m.refresh_from_db()
        assert m.status == Status.DELIVERED and m.delivered_at
        assert MessageEvent.objects.count() == 2

    def test_out_of_order_never_moves_backwards(self, api, make_candidate):
        m = self.make(make_candidate)
        webhook(api, {"event_id": "e1", "status": "read", "message_id": "pm_x"})
        assert webhook(api, {"event_id": "e2", "status": "delivered", "message_id": "pm_x"}).data["result"] == "ignored"
        assert webhook(api, {"event_id": "e3", "status": "sent", "message_id": "pm_x"}).data["result"] == "ignored"
        m.refresh_from_db()
        assert m.status == Status.READ and m.delivered_at and m.read_at   # skipped step is backfilled

    def test_failed_after_delivered_is_ignored_but_failed_after_sent_applies(self, api, make_candidate):
        d = self.make(make_candidate, Status.DELIVERED, "pm_d")
        s = self.make(make_candidate, Status.SENT, "pm_s")
        err = {"code": "UNREACHABLE", "message": "x"}
        assert webhook(api, {"event_id": "a", "status": "failed", "message_id": "pm_d", "error": err}).data["result"] == "ignored"
        assert webhook(api, {"event_id": "b", "status": "failed", "message_id": "pm_s", "error": err}).data["result"] == "applied"
        s.refresh_from_db()
        assert s.status == Status.FAILED and s.retryable and "switched off" in s.failure_message

    def test_webhook_arriving_before_provider_id_is_saved_matches_by_reference(self, api, make_candidate):
        m = Message.objects.create(candidate=make_candidate(), body="x", channel="sms", status=Status.SENDING)
        r = webhook(api, {"event_id": "e1", "status": "sent", "message_id": "pm_new", "reference": str(m.id)})
        assert r.data["result"] == "applied"
        m.refresh_from_db()
        assert m.status == Status.SENT and m.provider_message_id == "pm_new"

    def test_unknown_message_is_acknowledged(self, api):
        r = webhook(api, {"event_id": "e1", "status": "sent", "message_id": "pm_ghost", "reference": "not-a-uuid"})
        assert r.status_code == 200 and r.data["result"] == "unknown"

    def test_late_webhook_revives_message_we_gave_up_on(self, api, make_candidate):
        m = self.make(make_candidate, Status.FAILED, None)
        m.failure_code, m.retryable = "TIMEOUT", True
        m.save()
        r = webhook(api, {"event_id": "e1", "status": "delivered", "message_id": "pm_late", "reference": str(m.id)})
        m.refresh_from_db()
        assert r.data["result"] == "applied" and m.status == Status.DELIVERED and m.failure_message == ""

    def test_reconcile_recovers_lost_webhooks(self, make_candidate, fake):
        m = self.make(make_candidate)
        Message.objects.filter(pk=m.pk).update(updated_at=timezone.now() - timedelta(minutes=5))
        fake.remote["pm_x"] = RemoteStatus("delivered")
        assert services.reconcile() == 1
        m.refresh_from_db()
        assert m.status == Status.DELIVERED


@pytest.mark.django_db
class TestHistoryTemplatesHealth:
    def test_history_most_recent_first_and_hides_cancelled(self, api, make_candidate):
        c = make_candidate()
        now = timezone.now()
        Message.objects.create(candidate=c, body="old", channel="sms", status="read", created_at=now - timedelta(days=2))
        Message.objects.create(candidate=c, body="new", channel="sms", status="failed", created_at=now)
        Message.objects.create(candidate=c, body="gone", channel="sms", status="cancelled")
        r = api.get(f"/api/candidates/{c.id}/messages/")
        assert [m["body"] for m in r.data["results"]] == ["new", "old"]

    def test_empty_history(self, api, make_candidate):
        assert api.get(f"/api/candidates/{make_candidate().id}/messages/").data["count"] == 0

    def test_template_crud_and_validation(self, api, make_candidate, fake):
        r = api.post("/api/templates/", {"name": "Interview", "body": "Hi {{first_name}}!"}, format="json")
        assert r.status_code == 201
        assert api.post("/api/templates/", {"name": "interview", "body": "x"}, format="json").status_code == 400
        assert api.post("/api/templates/", {"name": "Bad", "body": "{{wat}}"}, format="json").status_code == 400
        c = make_candidate("Neha Patel")
        r = api.post("/api/messages/", {"candidate_ids": [str(c.id)], "template_id": r.data["id"]}, format="json")
        assert r.status_code == 201 and r.data["results"][0]["body"] == "Hi Neha!"

    def test_health_counts_and_outage(self, api, make_candidate, monkeypatch):
        c = make_candidate()
        for s in ["sent", "delivered", "read", "failed", "queued"]:
            Message.objects.create(candidate=c, body="x", channel="sms", status=s)
        down = type("P", (), {"name": "down", "health": lambda self: Health(ok=False, detail="refused")})()
        monkeypatch.setattr(services, "all_providers", lambda: [(down, ["sms"])])
        d = api.get("/api/provider/health/").data
        assert d["status"] == "outage"
        assert d["totals"] == {"sent": 3, "delivered": 2, "read": 1, "failed": 1, "pending": 1, "scheduled": 0}

    def test_meta(self, api):
        d = api.get("/api/meta/").data
        assert {c["id"] for c in d["channels"]} == {"whatsapp", "sms", "email"}
