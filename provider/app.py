"""
Dummy communication provider ("PingHub").

An independent HTTP service that behaves like a real messaging provider
(Twilio / WhatsApp Cloud API style):

  POST /v1/messages             accept a message, return a provider message id
  GET  /v1/messages/<id>        current status (used for reconciliation)
  GET  /v1/stats                counters + health, used by the "provider health" widget
  GET  /health                  liveness
  GET/POST /v1/admin/chaos      change failure simulation at runtime (demo / tests)

Message lifecycle is simulated asynchronously and reported to the platform
through signed webhooks:  sent -> delivered -> read   (or -> failed)

Magic recipient numbers make failures reproducible (match on the last digits):
  ...0000  invalid recipient            (HTTP 422, permanent)
  ...1111  recipient blocked / opted out (HTTP 422, permanent)
  ...2222  rate limited                  (HTTP 429 + Retry-After, temporary)
  ...3333  temporary provider failure    (HTTP 503, temporary - fails the first 2 attempts)
  ...4444  accepted, then delivery fails (webhook: failed / handset unreachable; platform allows manual retry)
  ...5555  accepted, delivered, never read
Anything else is random according to the chaos configuration.
"""
import hashlib
import hmac
import json
import os
import random
import re
import threading
import time
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

API_KEY = os.environ.get("PROVIDER_API_KEY", "dev-provider-key")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://localhost:8000/api/webhooks/provider/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev-webhook-secret")
# Scale all simulated delays (1.0 = realistic demo pace, 0 = instant, handy for tests)
TIME_SCALE = float(os.environ.get("PROVIDER_TIME_SCALE", "1.0"))

app = Flask(__name__)
LOCK = threading.RLock()
MESSAGES = {}          # provider_message_id -> dict
BY_IDEMPOTENCY = {}    # idempotency key -> provider_message_id
ATTEMPTS = {}          # recipient -> attempts (for the "...3333" scenario)
CHAOS = {
    "outage": False,            # every request returns 503
    "latency_ms": 0,            # artificial latency on POST /v1/messages
    "temporary_failure_rate": 0.08,
    "rate_limit_rate": 0.03,
    "delivery_failure_rate": 0.06,
    "read_rate": 0.7,
    "duplicate_webhook_rate": 0.15,   # provider re-delivers some webhooks (at-least-once)
}
COUNTERS = {"accepted": 0, "rejected": 0, "sent": 0, "delivered": 0, "read": 0, "failed": 0}
CHANNELS = {"whatsapp", "sms", "email"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def err(status, code, message, **extra):
    body = {"error": {"code": code, "message": message}}
    resp = jsonify(body)
    resp.status_code = status
    for k, v in extra.items():
        resp.headers[k] = str(v)
    return resp


def authorised():
    return request.headers.get("Authorization", "") == f"Bearer {API_KEY}"


def sign(raw: bytes) -> str:
    return "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def deliver_webhook(payload: dict):
    """At-least-once delivery with retries; sometimes sends duplicates on purpose."""
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "X-Provider-Signature": sign(raw)}
    for attempt in range(4):
        try:
            r = requests.post(WEBHOOK_URL, data=raw, headers=headers, timeout=5)
            if r.status_code < 500:
                break
        except requests.RequestException:
            pass
        time.sleep(min(2 ** attempt, 8) * max(TIME_SCALE, 0.05))
    if random.random() < CHAOS["duplicate_webhook_rate"]:
        try:
            requests.post(WEBHOOK_URL, data=raw, headers=headers, timeout=5)
        except requests.RequestException:
            pass


def emit(msg, status, error=None):
    """Move a message to a new status and notify the platform."""
    with LOCK:
        msg["status"] = status
        msg["updated_at"] = now_iso()
        if status in COUNTERS:
            COUNTERS[status] += 1
        if error:
            msg["error"] = error
        payload = {
            "event_id": f"evt_{uuid.uuid4().hex}",
            "message_id": msg["id"],
            "reference": msg["reference"],
            "status": status,
            "timestamp": now_iso(),
        }
        if error:
            payload["error"] = error
    deliver_webhook(payload)


def sleep(seconds):
    time.sleep(seconds * TIME_SCALE)


def lifecycle(msg):
    """Background simulation of what happens after a provider accepts a message."""
    to = msg["to"]
    sleep(random.uniform(0.6, 1.5))
    emit(msg, "sent")
    if to.endswith("4444") or (not re.search(r"(5555)$", to) and random.random() < CHAOS["delivery_failure_rate"]):
        sleep(random.uniform(1, 2.5))
        emit(msg, "failed", {"code": "UNREACHABLE", "message": "Recipient handset unreachable or switched off."})
        return
    sleep(random.uniform(1.0, 3.0))
    emit(msg, "delivered")
    if to.endswith("5555") or random.random() > CHAOS["read_rate"]:
        return
    sleep(random.uniform(2.0, 6.0))
    emit(msg, "read")


@app.before_request
def gate():
    if request.path == "/health" or request.path.startswith("/v1/admin"):
        return None
    if CHAOS["outage"]:
        return err(503, "SERVICE_UNAVAILABLE", "Provider is temporarily unavailable.", **{"Retry-After": 30})
    if not authorised():
        return err(401, "UNAUTHORISED", "Invalid API key.")
    return None


@app.get("/health")
def health():
    return jsonify({"status": "outage" if CHAOS["outage"] else "operational", "time": now_iso()})


@app.post("/v1/messages")
def create_message():
    data = request.get_json(silent=True) or {}
    to, body = (data.get("to") or "").strip(), (data.get("body") or "").strip()
    channel = data.get("channel", "whatsapp")
    if channel not in CHANNELS:
        return err(400, "INVALID_CHANNEL", f"Unsupported channel '{channel}'.")
    if not body:
        return err(400, "EMPTY_BODY", "Message body is required.")
    if len(body) > 1600:
        return err(400, "BODY_TOO_LONG", "Message body exceeds 1600 characters.")
    key = request.headers.get("Idempotency-Key")
    if key:
        with LOCK:
            existing = BY_IDEMPOTENCY.get(key)
            if existing:  # replay -> same answer, no second message
                return jsonify(_public(MESSAGES[existing])), 200
    if CHAOS["latency_ms"]:
        time.sleep(CHAOS["latency_ms"] / 1000)

    valid = bool(re.fullmatch(r"\+[1-9]\d{7,14}", to)) if channel != "email" else bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to))
    if not valid or to.endswith("0000"):
        COUNTERS["rejected"] += 1
        return err(422, "INVALID_RECIPIENT", "The recipient address is not valid.")
    if to.endswith("1111"):
        COUNTERS["rejected"] += 1
        return err(422, "RECIPIENT_BLOCKED", "The recipient has opted out of messages.")
    if to.endswith("2222"):
        COUNTERS["rejected"] += 1
        return err(429, "RATE_LIMITED", "Too many requests, slow down.", **{"Retry-After": 5})
    if to.endswith("3333"):
        with LOCK:
            ATTEMPTS[to] = ATTEMPTS.get(to, 0) + 1
            n = ATTEMPTS[to]
        if n <= 2:
            COUNTERS["rejected"] += 1
            return err(503, "TEMPORARY_FAILURE", "Upstream carrier is temporarily unavailable.")
    elif not to.endswith(("4444", "5555")):
        roll = random.random()
        if roll < CHAOS["rate_limit_rate"]:
            COUNTERS["rejected"] += 1
            return err(429, "RATE_LIMITED", "Too many requests, slow down.", **{"Retry-After": 3})
        if roll < CHAOS["rate_limit_rate"] + CHAOS["temporary_failure_rate"]:
            COUNTERS["rejected"] += 1
            return err(503, "TEMPORARY_FAILURE", "Upstream carrier is temporarily unavailable.")

    msg = {
        "id": f"pm_{uuid.uuid4().hex[:24]}", "to": to, "body": body, "channel": channel,
        "reference": data.get("reference"), "status": "accepted",
        "created_at": now_iso(), "updated_at": now_iso(), "error": None,
    }
    with LOCK:
        MESSAGES[msg["id"]] = msg
        if key:
            BY_IDEMPOTENCY[key] = msg["id"]
        COUNTERS["accepted"] += 1
    threading.Thread(target=lifecycle, args=(msg,), daemon=True).start()
    return jsonify(_public(msg)), 202


def _public(m):
    return {k: m[k] for k in ("id", "to", "channel", "reference", "status", "created_at", "updated_at", "error")}


@app.get("/v1/messages/<mid>")
def get_message(mid):
    m = MESSAGES.get(mid)
    return (jsonify(_public(m)), 200) if m else err(404, "NOT_FOUND", "Unknown message id.")


@app.get("/v1/stats")
def stats():
    with LOCK:
        return jsonify({"status": "operational", "counters": dict(COUNTERS), "chaos": dict(CHAOS), "time": now_iso()})


@app.route("/v1/admin/chaos", methods=["GET", "POST"])
def chaos():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        for k, v in data.items():
            if k in CHAOS:
                CHAOS[k] = type(CHAOS[k])(v)
    return jsonify(CHAOS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 9000)), threaded=True)
