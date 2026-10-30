"""Unit tests for the PingHub standalone provider service."""
import pytest
from app import app, MESSAGES, BY_IDEMPOTENCY

@pytest.fixture
def client():
    app.config["TESTING"] = True
    from app import CHAOS
    orig_chaos = dict(CHAOS)
    CHAOS["temporary_failure_rate"] = 0
    CHAOS["rate_limit_rate"] = 0
    CHAOS["delivery_failure_rate"] = 0
    CHAOS["outage"] = False
    with app.test_client() as c:
        MESSAGES.clear()
        BY_IDEMPOTENCY.clear()
        yield c
    CHAOS.update(orig_chaos)

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "operational"

def test_send_success(client):
    r = client.post(
        "/v1/messages",
        headers={"Authorization": "Bearer dev-provider-key", "X-Idempotency-Key": "test-key-1"},
        json={"to": "+919876543210", "body": "Hello Rahul", "channel": "whatsapp", "reference": "msg-123"},
    )
    assert r.status_code == 202
    data = r.get_json()
    assert "id" in data
    assert data["status"] == "accepted"

def test_send_invalid_recipient(client):
    r = client.post(
        "/v1/messages",
        headers={"Authorization": "Bearer dev-provider-key", "X-Idempotency-Key": "test-key-2"},
        json={"to": "+919876500000", "body": "Hello", "channel": "whatsapp"},
    )
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "INVALID_RECIPIENT"

def test_send_opted_out(client):
    r = client.post(
        "/v1/messages",
        headers={"Authorization": "Bearer dev-provider-key"},
        json={"to": "+919876501111", "body": "Hello", "channel": "whatsapp"},
    )
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "RECIPIENT_BLOCKED"

def test_send_rate_limited(client):
    r = client.post(
        "/v1/messages",
        headers={"Authorization": "Bearer dev-provider-key"},
        json={"to": "+919876502222", "body": "Hello", "channel": "whatsapp"},
    )
    assert r.status_code == 429
    assert r.get_json()["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in r.headers

def test_stats(client):
    r = client.get("/v1/stats", headers={"Authorization": "Bearer dev-provider-key"})
    assert r.status_code == 200
    data = r.get_json()
    assert "counters" in data
    assert "status" in data
