import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings

from .base import BaseProvider, Health, ProviderError, RemoteStatus, SendResult

log = logging.getLogger(__name__)


class SmtpEmailProvider(BaseProvider):
    """
    Standard SMTP provider (RFC 5321).
    Works with Gmail, Outlook, AWS SES, Mailpit, MailHog, etc.
    """

    name = "Gmail SMTP"

    def __init__(self):
        self.host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        self.port = int(getattr(settings, "SMTP_PORT", 587))
        self.user = getattr(settings, "SMTP_USER", "")
        self.password = getattr(settings, "SMTP_PASSWORD", "")
        self.use_tls = getattr(settings, "SMTP_USE_TLS", True)
        self.from_email = getattr(settings, "SMTP_FROM_EMAIL", self.user or "recruitment@hunar.ai")

    def send(self, *, to: str, body: str, channel: str, reference: str, idempotency_key: str) -> SendResult:
        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = to
        msg["Subject"] = "Update regarding your application at Hunar.ai"
        msg["X-Reference-ID"] = reference
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)

            provider_msg_id = f"smtp-{uuid.uuid4()}"
            return SendResult(provider_message_id=provider_msg_id, status="sent")
        except smtplib.SMTPRecipientsRefused:
            raise ProviderError("INVALID_RECIPIENT", f"Recipient email {to} was refused by SMTP.")
        except smtplib.SMTPAuthenticationError:
            raise ProviderError("UNAUTHORISED", "SMTP authentication failed.")
        except smtplib.SMTPConnectError:
            raise ProviderError("SERVICE_UNAVAILABLE", f"Could not connect to SMTP server {self.host}:{self.port}.")
        except (smtplib.SMTPException, OSError) as e:
            raise ProviderError("TEMPORARY_FAILURE", f"SMTP delivery error: {str(e)}")

    def fetch_status(self, provider_message_id: str) -> RemoteStatus:
        return RemoteStatus(status="delivered")

    def health(self) -> Health:
        try:
            with smtplib.SMTP(self.host, self.port, timeout=5) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                code, _ = server.noop()
                return Health(ok=(code == 250), detail=f"Connected to {self.host}:{self.port}")
        except Exception as e:
            return Health(ok=False, detail=f"SMTP offline ({self.host}:{self.port}): {e}")

