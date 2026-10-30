import json
import logging
import requests
from django.conf import settings

from .base import BaseProvider, Health, ProviderError, RemoteStatus, SendResult

log = logging.getLogger(__name__)


class TwilioWhatsAppProvider(BaseProvider):
    """
    Real Twilio WhatsApp Provider.

    Dispatches outbound WhatsApp messages through Twilio's WhatsApp Sandbox.

    IMPORTANT — Twilio trial sandbox policy:
      - Requires a 24-hour session window: the recipient must first send ANY message
        from their WhatsApp to the sandbox number (+17372508034) within the last 24h.
      - OR a pre-approved ContentSid (HX...) must be supplied in TWILIO_WHATSAPP_CONTENT_SID.
      - Without either, Twilio returns error 21654 (ContentSid Required).
    """

    name = "Twilio WhatsApp"

    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self.api_key = getattr(settings, "TWILIO_API_KEY", "")
        self.api_secret = getattr(settings, "TWILIO_API_SECRET", "")
        self.from_number = getattr(settings, "TWILIO_WHATSAPP_FROM", "whatsapp:+17372508034")
        self.content_sid = getattr(settings, "TWILIO_WHATSAPP_CONTENT_SID", "")
        self.url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        # Use API key credentials if available, otherwise Account SID + Auth Token
        if self.api_key and self.api_secret:
            self.auth = (self.api_key, self.api_secret)
        else:
            self.auth = (self.account_sid, self.auth_token)

    def _build_payload(self, to_wa: str, from_wa: str, body: str) -> dict:
        data: dict = {"From": from_wa, "To": to_wa}
        if self.content_sid:
            # Template-based send (works 24/7 without session window constraints)
            data["ContentSid"] = self.content_sid
            # Safely serialize variables for Twilio template
            var1 = body[:40] if body else "Interview"
            var2 = "Hunar.ai"
            data["ContentVariables"] = json.dumps({"1": var1, "2": var2})
        else:
            # Session-based send (requires 24h open session window)
            data["Body"] = body
        return data

    def send(self, *, to: str, body: str, channel: str, reference: str, idempotency_key: str) -> SendResult:
        to_wa = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        from_wa = self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}"

        data = self._build_payload(to_wa, from_wa, body)

        try:
            resp = requests.post(
                self.url,
                data=data,
                auth=self.auth,
                timeout=10,
            )
        except requests.RequestException as e:
            raise ProviderError("SERVICE_UNAVAILABLE", f"Twilio connection error: {e}")

        if resp.status_code in (200, 201):
            res_json = resp.json()
            return SendResult(
                provider_message_id=res_json.get("sid", ""),
                status=res_json.get("status", "accepted"),
            )

        err_data = {}
        try:
            err_data = resp.json()
        except Exception:
            pass

        code = err_data.get("code") or "PROVIDER_ERROR"
        msg = err_data.get("message") or resp.text[:200]
        log.error("Twilio WhatsApp error %s: %s (HTTP %s)", code, msg, resp.status_code)

        if resp.status_code == 429:
            raise ProviderError("RATE_LIMITED", msg)
        if resp.status_code == 401:
            raise ProviderError("UNAUTHORISED", msg)
        if code == 21654:
            # ContentSid required — session window not open; user must text the sandbox number first
            raise ProviderError(
                "TEMPORARY_FAILURE",
                "WhatsApp session window closed. Ask the recipient to send any message "
                f"to {self.from_number.replace('whatsapp:', '')} on WhatsApp first, then retry."
            )
        if code == 21655:
            raise ProviderError("UNAUTHORISED", f"Invalid WhatsApp ContentSid. Check TWILIO_WHATSAPP_CONTENT_SID setting. {msg}")
        if resp.status_code in (400, 422):
            raise ProviderError("INVALID_RECIPIENT" if code in (21211, 21614) else "TEMPORARY_FAILURE", msg)

        raise ProviderError("TEMPORARY_FAILURE", msg)

    def fetch_status(self, provider_message_id: str) -> RemoteStatus:
        try:
            r = requests.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages/{provider_message_id}.json",
                auth=self.auth,
                timeout=5,
            )
            if r.status_code == 200:
                s = r.json().get("status", "sent")
                mapped = (
                    "delivered" if s in ("delivered",)
                    else "sent" if s in ("sent", "queued", "sending")
                    else "failed" if s in ("failed", "undelivered")
                    else s
                )
                return RemoteStatus(status=mapped)
        except Exception:
            pass
        return RemoteStatus(status="delivered")

    def health(self) -> Health:
        try:
            r = requests.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}.json",
                auth=self.auth,
                timeout=5,
            )
            if r.status_code == 200:
                mode = "template" if self.content_sid else "session (24h window)"
                return Health(ok=True, detail=f"Twilio WhatsApp active — send mode: {mode}")
            return Health(ok=False, detail=f"Twilio error: HTTP {r.status_code}")
        except Exception as e:
            return Health(ok=False, detail=f"Twilio offline: {e}")
