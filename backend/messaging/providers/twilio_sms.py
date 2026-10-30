import logging
import requests
from django.conf import settings

from .base import BaseProvider, Health, ProviderError, RemoteStatus, SendResult

log = logging.getLogger(__name__)


class TwilioSmsProvider(BaseProvider):
    """
    Real Twilio SMS Provider.
    Sends outbound SMS messages through Twilio's REST API.
    Works on Twilio trial accounts for verified / TO numbers.
    """

    name = "Twilio SMS"

    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self.api_key = getattr(settings, "TWILIO_API_KEY", "")
        self.api_secret = getattr(settings, "TWILIO_API_SECRET", "")
        self.from_number = getattr(settings, "TWILIO_SMS_FROM", "")
        self.url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        )
        if self.api_key and self.api_secret:
            self.auth = (self.api_key, self.api_secret)
        else:
            self.auth = (self.account_sid, self.auth_token)

    def send(self, *, to: str, body: str, channel: str, reference: str, idempotency_key: str) -> SendResult:
        # Strip whatsapp: prefix if accidentally passed
        to_num = to.replace("whatsapp:", "").strip()

        data = {
            "From": self.from_number,
            "To": to_num,
            "Body": body[:1600],
        }

        try:
            resp = requests.post(
                self.url,
                data=data,
                auth=self.auth,
                timeout=10,
            )
        except requests.RequestException as e:
            raise ProviderError("SERVICE_UNAVAILABLE", f"Twilio SMS connection error: {e}")

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
        log.error("Twilio SMS error %s: %s (HTTP %s)", code, msg, resp.status_code)

        if resp.status_code == 429:
            raise ProviderError("RATE_LIMITED", msg)
        if resp.status_code == 401:
            raise ProviderError("UNAUTHORISED", msg)
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
        return RemoteStatus(status="sent")

    def health(self) -> Health:
        try:
            r = requests.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}.json",
                auth=self.auth,
                timeout=5,
            )
            if r.status_code == 200:
                return Health(ok=True, detail="Twilio SMS active & connected")
            return Health(ok=False, detail=f"Twilio SMS error: HTTP {r.status_code}")
        except Exception as e:
            return Health(ok=False, detail=f"Twilio SMS offline: {e}")

