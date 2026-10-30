import requests
from django.conf import settings

from .base import BaseProvider, Health, ProviderError, RemoteStatus, SendResult


class DummyProvider(BaseProvider):
    """Client for the standalone dummy provider service in /provider."""

    name = "PingHub (dummy)"

    def __init__(self):
        self.base = settings.PROVIDER_BASE_URL.rstrip("/")
        self.timeout = settings.PROVIDER_TIMEOUT_SECONDS
        self.headers = {"Authorization": f"Bearer {settings.PROVIDER_API_KEY}"}

    def _request(self, method, path, **kw):
        try:
            return requests.request(method, self.base + path, headers={**self.headers, **kw.pop("headers", {})},
                                    timeout=self.timeout, **kw)
        except requests.Timeout:
            raise ProviderError("TIMEOUT", "request timed out")
        except requests.RequestException as e:
            raise ProviderError("SERVICE_UNAVAILABLE", str(e))

    @staticmethod
    def _error(resp) -> ProviderError:
        try:
            err = resp.json().get("error", {})
        except ValueError:
            err = {}
        code = err.get("code") or ("SERVICE_UNAVAILABLE" if resp.status_code >= 500 else "UNKNOWN")
        if resp.status_code == 429:
            code = "RATE_LIMITED"
        elif resp.status_code >= 500 and code not in ("SERVICE_UNAVAILABLE", "TEMPORARY_FAILURE"):
            code = "TEMPORARY_FAILURE"
        retry_after = resp.headers.get("Retry-After")
        return ProviderError(code, err.get("message", resp.text[:200]),
                             retry_after=float(retry_after) if retry_after and retry_after.isdigit() else None)

    def send(self, *, to, body, channel, reference, idempotency_key):
        resp = self._request("POST", "/v1/messages", json={"to": to, "body": body, "channel": channel, "reference": reference},
                             headers={"Idempotency-Key": idempotency_key})
        if resp.status_code in (200, 202):
            data = resp.json()
            return SendResult(provider_message_id=data["id"], status=data.get("status", "accepted"))
        raise self._error(resp)

    def fetch_status(self, provider_message_id):
        resp = self._request("GET", f"/v1/messages/{provider_message_id}")
        if resp.status_code != 200:
            raise self._error(resp)
        data = resp.json()
        err = data.get("error") or {}
        return RemoteStatus(status=data["status"], error_code=err.get("code", ""), error_message=err.get("message", ""))

    def health(self):
        try:
            resp = requests.get(self.base + "/health", timeout=2)
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            return Health(ok=False, detail=str(e))
        if data.get("status") != "operational":
            return Health(ok=False, detail=data.get("status", "unknown"))
        try:
            stats = self._request("GET", "/v1/stats").json()
            return Health(ok=True, counters=stats.get("counters", {}))
        except (ProviderError, ValueError):
            return Health(ok=True)
