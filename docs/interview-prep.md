# Interview preparation

## 60-second project summary

“I built a candidate communication workspace with a Next.js, TypeScript, and MUI frontend backed by Django REST Framework. Recruiters can manage candidates, send individual or bulk messages, and inspect independent delivery outcomes. I isolated the communication provider behind an adapter and made a dummy provider the default so the full lifecycle can be demonstrated without real credentials. Every message has attempt history; provider status events are deduplicated, legal transitions are enforced, and late events cannot regress an advanced message. I added candidate history, retry rules, reusable message templates, and provider health reporting. The README documents the security limitations and how I would move dispatch to a durable worker for a real provider.”

## Honest resume bullets

- Built a full-stack candidate communication platform using Next.js, TypeScript, Material UI, Django, and Django REST Framework, including candidate CRUD/search, individual messaging, bulk campaigns, and communication history.
- Designed a provider adapter and message lifecycle model with independent per-recipient records, provider references, status events, attempt history, and idempotent callback processing.
- Implemented failure classification, retry eligibility, maximum-attempt limits, and handling for duplicate/out-of-order status callbacks; added deterministic failure scenarios for end-to-end demos.
- Added candidate-specific message templates, provider health and aggregate metrics, and responsive recruiter workflows with explicit loading, empty, validation, and error states.
- Added Django API tests for candidate validation/search, message lifecycle, bulk partial outcomes, idempotency, webhook deduplication, out-of-order events, and retry behavior.

Do not add performance or business-impact numbers unless you measure them yourself. Do not state that this is a production deployment or a real messaging integration.

## Recommended live demo (4–6 minutes)

1. Open Dashboard and explain the metrics are database aggregates and the provider status is labeled as simulation.
2. Create “Demo Candidate” with a valid `@demo.test` email and phone; show server-side validation by attempting to submit with both fields blank.
3. Open the profile and send a short interview reminder. Explain that `sent` means provider acceptance, not delivery.
4. Open message details and simulate delivery, then read. Point out the persisted status-event timeline.
5. Return to Candidates and select Rahul, Priya, Amit, and Neha. Choose the “mixed outcome” scenario for a bulk message. Open the batch page and show one row per recipient with independent references/failure reasons.
6. Open a retryable failed message. Explain the retry-after delay and why permanent recipient failures / uncertain timeouts are not blindly retried.
7. Open Templates and Provider health. Conclude by describing how a real provider adapter, signed webhooks, auth, and Celery/Redis would be added.

## Likely interview questions and sample answers

### Why keep a provider abstraction instead of calling a service from a view?
The provider boundary prevents external-provider payload formats and error types from leaking into API views or message state. It provides one place to normalize provider references, errors, retryability, and status behavior. A real adapter can replace the dummy adapter while the candidate/message APIs remain stable.

### Why are `sent` and `delivered` different?
A provider may accept a send request without successfully delivering it. `sent` records provider acceptance; `delivered` requires a provider callback. Conflating the states would present false certainty to recruiters.

### How does bulk messaging handle partial success?
The batch is a grouping record, not a single provider send. Each candidate has an independent Message plus MessageAttempt record. The service catches provider-specific failures per recipient, persists them safely, and continues with remaining recipients. The batch status derives from the final per-recipient states.

### How do you avoid duplicate processing of webhooks?
Every provider event has a unique `provider_event_id` stored in `MessageStatusEvent`. Database uniqueness provides the deduplication guard. Processing is done in a transaction, and a duplicate event is ignored rather than applied twice.

### What happens if callbacks arrive out of order?
The message service has a transition map and state rank for the forward delivery lifecycle. A lower-ranked `sent` event cannot roll a `delivered` message backward. The event is retained with an ignored processing result so the event can be inspected without corrupting current state.

### How do retries work, and what are the trade-offs?
Permanent recipient errors are not retryable; temporary provider outages and rate limiting are retryable after a delay; provider timeouts are treated as uncertain acceptance and are not blindly retried. Attempts are capped and historical attempt rows remain. A production provider should use provider idempotency keys and reconciliation for ambiguous outcomes.

### What would you change before production?
Add authentication and per-team authorization, audit controls, signed webhook validation, secret management, HTTPS, data-retention rules, stricter logging/redaction, PostgreSQL, a transactional outbox, and Celery/Redis workers with bounded concurrency and provider-aware rate limits. Add end-to-end tests and load tests. Scheduled messages should rely on durable jobs, not process memory.

### Why aren't scheduled messages implemented?
Scheduling was optional. An in-memory timer can lose work on restarts and is not appropriate for a communication platform. I prioritized the core send/status/failure/history workflows; a correct implementation should use a persistent queue or scheduler with locking and cancellation semantics.

## Important module map

- `backend/communication/models.py`: relational schema and database constraints.
- `backend/communication/providers.py`: provider contract, dummy sender, typed provider exceptions, health.
- `backend/communication/services.py`: dispatch, attempt creation, retry policy, legal status transitions, webhook deduplication, template rendering.
- `backend/communication/views.py`: REST request/response layer and validation of user operations.
- `backend/communication/serializers.py`: server-facing validation and output representation.
- `frontend/lib/api.ts`: typed API client, safe error normalization, shared domain types.
- `frontend/components/AppShell.tsx`: navigation and responsive SaaS workspace shell.
- `frontend/app/candidates`: candidate management and contact-specific composer.
- `frontend/app/messages`: message table and lifecycle inspector.
- `frontend/app/batches`: campaign overview and per-recipient outcomes.

## Trade-offs to acknowledge

- Bulk dispatch currently runs synchronously for small demo batches, with a 500-recipient cap. A real provider should use asynchronous workers.
- The local dummy webhook is not signed and is blocked when `DEBUG=False`; real adapters require provider-specific signatures and timestamp validation.
- Authentication is intentionally not included for the evaluator-friendly local demo, so this build must not be made public as-is.
- Automated backend and frontend tests are written but must be run in an environment where the dependencies can be installed. Do not claim they passed until you run them.
