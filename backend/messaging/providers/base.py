from dataclasses import dataclass, field
from typing import Optional


class ProviderError(Exception):
    """Failure talking to a provider, already classified for the platform."""

    def __init__(self, code: str, detail: str = "", retry_after: Optional[float] = None):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.retry_after = code, detail, retry_after


@dataclass
class SendResult:
    provider_message_id: str
    status: str = "accepted"


@dataclass
class RemoteStatus:
    status: str
    error_code: str = ""
    error_message: str = ""


@dataclass
class Health:
    ok: bool
    detail: str = ""
    counters: dict = field(default_factory=dict)


class BaseProvider:
    """Interface every communication provider (dummy, Twilio, Resend, ...) implements."""

    name = "base"

    def send(self, *, to: str, body: str, channel: str, reference: str, idempotency_key: str) -> SendResult:
        raise NotImplementedError

    def fetch_status(self, provider_message_id: str) -> RemoteStatus:
        raise NotImplementedError

    def health(self) -> Health:
        raise NotImplementedError
