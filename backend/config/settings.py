"""Django settings. Everything environment-specific comes from env vars (12-factor)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(int(default))).lower() in ("1", "true", "yes")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "candidates",
    "messaging",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SQLITE_PATH", BASE_DIR / "db.sqlite3"),
        "OPTIONS": {
            "timeout": 20,
            # The API process and the worker process write concurrently: WAL + IMMEDIATE
            # transactions avoid "database is locked" upgrade deadlocks.
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "config.api.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "config.api.Pagination",
    "PAGE_SIZE": 10,
}

# ---- Messaging -------------------------------------------------------------------
PROVIDER_BASE_URL = os.environ.get("PROVIDER_BASE_URL", "http://localhost:9000")
PROVIDER_API_KEY = os.environ.get("PROVIDER_API_KEY", "dev-provider-key")
PROVIDER_TIMEOUT_SECONDS = float(os.environ.get("PROVIDER_TIMEOUT_SECONDS", "5"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev-webhook-secret")

# Channel -> provider implementation.
# All real providers: Twilio (WhatsApp & SMS) and Gmail SMTP (Email).
MESSAGING = {
    "CHANNELS": {
        "whatsapp": {"label": "WhatsApp", "provider": "messaging.providers.twilio.TwilioWhatsAppProvider", "recipient": "phone"},
        "sms": {"label": "SMS", "provider": "messaging.providers.twilio_sms.TwilioSmsProvider", "recipient": "phone"},
        "email": {"label": "Email", "provider": "messaging.providers.smtp.SmtpEmailProvider", "recipient": "email"},
    },
    "DEFAULT_CHANNEL": "whatsapp",
    "MAX_BODY_LENGTH": 1600,
    "MAX_BULK_RECIPIENTS": 500,
    "MAX_AUTO_ATTEMPTS": 4,          # automatic attempts for temporary failures
    "BACKOFF_BASE_SECONDS": 5,       # 5s, 10s, 20s ...
    "MIN_SCHEDULE_LEAD_SECONDS": 30,
    "STALE_SENDING_SECONDS": 60,     # crash recovery: 'sending' longer than this goes back to queue
    "RECONCILE_AFTER_SECONDS": 45,   # poll the provider if no webhook arrived for this long
}

# Real Gmail SMTP Configuration
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL")

# Real Twilio Configuration (WhatsApp + SMS)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_API_KEY = os.environ.get("TWILIO_API_KEY")
TWILIO_API_SECRET = os.environ.get("TWILIO_API_SECRET")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
TWILIO_WHATSAPP_CONTENT_SID = os.environ.get("TWILIO_WHATSAPP_CONTENT_SID")
TWILIO_SMS_FROM = os.environ.get("TWILIO_SMS_FROM", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
