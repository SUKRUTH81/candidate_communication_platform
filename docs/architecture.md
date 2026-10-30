# Architecture and engineering decisions

## Components

- **Next.js App Router + React + TypeScript + MUI:** recruiter workspace and typed API boundary. Pages are client-rendered where interactive mutations/polling are needed. TanStack Query handles caching, mutation state, selective invalidation, and periodic refresh.
- **Django + Django REST Framework:** server-side validation, persistence, API pagination, provider orchestration, status transition rules, retries, and safe error messages.
- **Relational database:** SQLite by default for a frictionless local demo; PostgreSQL is supported through `DATABASE_URL` and used by Docker Compose.
- **Standalone dummy provider service:** `provider_service/app.py` runs in its own process/container and exposes HTTP endpoints for `/send/`, `/health/`, and `/simulate-status/`. It generates provider references, simulates failures, and sends status callbacks to Django. The Django-side HTTP adapter in `backend/communication/providers.py` translates provider responses/errors into domain-level types.

## Message lifecycle

A message is stored as `queued`, then one dispatch attempt changes it to `sending`. A successful dummy provider response stores a provider reference and sets `sent`. The provider event endpoint is the only normal path to `delivered` / `read`; a simulated failure event can transition `sent` to `failed`. Each attempt is recorded in `MessageAttempt`; status callback events are stored in `MessageStatusEvent`.

The domain service has a legal transition map. Statuses are monotonic for the ordered `queued → sending → sent → delivered → read` path. Lower-ranked late callbacks cannot regress an advanced state. The provider event ID is unique, making repeated events idempotent. Unknown provider references are accepted as non-applied results rather than creating orphan messages. Events with illegal transitions are retained for inspection with `invalid_transition` or ignored as out-of-order.

## Bulk processing

The batch row is created before recipient dispatch, and each candidate gets an independent message. A provider exception is mapped into that message's status and safe failure reason; the loop proceeds to other recipients. The batch status is then computed from persisted recipient statuses. The current implementation processes bounded demo sends synchronously (the dummy calls are local and fast) and imposes a 500-recipient API limit. A real provider should move dispatch into a persistent job queue such as Celery with Redis, bounded concurrency, a transactional outbox, and per-provider rate limits.

## Retry behavior

Permanent invalid-recipient errors are non-retryable. Temporary provider outage and rate-limit errors are marked retryable and carry a retry-after time. A timeout is considered acceptance-uncertain and is not blindly retried. Retry attempts preserve prior attempt rows and cap attempts at three. Retryable failures respect the provider's retry-after minimum and use capped exponential backoff with jitter; the UI blocks manual retry until the stored retry time. Each provider attempt receives a distinct idempotency key derived from the message ID and attempt number, while the API request idempotency key prevents duplicate message records. A production provider adapter must honor those keys where supported and reconcile uncertain timeouts rather than blindly resending.

## Data relationships

- `Candidate 1 ── * Message`
- `MessageBatch 1 ── * Message` (batch can be deleted without deleting message history)
- `Message 1 ── * MessageAttempt`
- `Message 1 ── * MessageStatusEvent`
- `MessageTemplate` is reusable content and is not a foreign-key dependency for historical messages.

## Security and production gaps

- Candidate and message API endpoints currently allow anonymous access for local evaluator convenience; add authentication and per-recruiter authorization before public deployment.
- The unsigned dummy webhook and status-simulation endpoint are explicitly limited to `DEBUG` mode. A real adapter must validate callback signatures and timestamps.
- Move secrets to a deployment secret manager, use HTTPS, tighten `ALLOWED_HOSTS` / CORS, configure rate limits, redact PII from logs, and review data retention/consent rules.
- Use PostgreSQL in shared environments. Add transactional outbox / Celery workers for asynchronous high-volume sends and scheduled work.
- Use provider-specific statuses. Read receipts are not generally reliable/available across all channels.
