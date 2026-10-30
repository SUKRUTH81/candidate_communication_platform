# Requirements traceability matrix

| Requirement | UI / route | Frontend implementation | API / service | Data model | Verification |
|---|---|---|---|---|---|
| Candidate create/list/search/details | `/candidates`, `/candidates/[id]` | Candidate table, form dialog, profile | `GET/POST /candidates/`, `GET/PATCH /candidates/{id}/` | `Candidate` | `test_candidate_validation_requires_contact`, `test_search_candidates` |
| Individual message send | Candidate profile | Compose panel, provider scenario selector | `POST /messages/send/`, `create_and_dispatch()` | `Message`, `MessageAttempt` | `test_individual_send_then_delivery_and_read` |
| Bulk messaging | Candidate table, `/batches/[id]` | Selection, recipient review, per-recipient outcome table | `POST /batches/`, `dispatch_message()` per message | `MessageBatch`, `Message` | `test_bulk_mixed_results_process_every_candidate` |
| Current message status | `/messages`, `/messages/[id]` | Status chips and live polling | `GET /messages/`, `GET /messages/{id}/` | `Message` | status lifecycle tests |
| Provider abstraction and references | Provider diagnostics, message inspector | Simulation disclosures and status controls | `providers.py`, health endpoint | `Message.provider_reference` | success / failure tests |
| Callback status updates | Message inspector | Explicit simulated events | `POST /webhooks/dummy/`, `process_status_event()` | `MessageStatusEvent` | duplicate/out-of-order tests |
| Failure classification | Message inspector, batch results | Safe failure message and retry reason | `ProviderError`, `dispatch_message()` | `Message`, `MessageAttempt` | permanent failure test |
| Safe retries | `/messages/[id]`, `/batches/[id]` | Individual / batch retry buttons | `POST /messages/{id}/retry/`, `POST /batches/{id}/retry-failed/` | `MessageAttempt` | retry policy is implemented; see known test limitations |
| Candidate history | Candidate profile | Reverse-chronological history | `GET /candidates/{id}/messages/` | `Message`, attempts, events | history ordering test |
| Loading / empty / error states | All major screens | Shared `StateBlocks` + page-level alerts | API errors normalized in `lib/api.ts` | N/A | frontend typecheck and tests |
| Message templates (bonus) | `/templates`, compose template selector | CRUD cards/dialog, variable insertion | `GET/POST /templates/`, `GET/PATCH/DELETE /templates/{id}/` | `MessageTemplate` | basic API integration available; UI test not yet exhaustive |
| Provider health (bonus) | `/settings/providers`, dashboard | Health badge, aggregates, recent errors | `GET /health/`, `GET /dashboard/` | Aggregate queries over messages | API smoke tests can be run locally |
| Live status updates (bonus) | Dashboard, message detail, batches | 8–12 second polling and query invalidation | Read APIs + status event APIs | Persisted status | manually verify in local browser |

## Assumptions and scope

- The default channel is a simulated email adapter; an SMS channel is also supported by the same dummy adapter.
- `Sent` means the provider accepted the send request. It does **not** mean delivered.
- Delivery/read states only change after a provider status event or a clearly labeled local simulation.
- A bulk batch contains one `Message` record per candidate; each provider call is handled independently.
- Templates support `candidate_name`, `candidate_email`, and `candidate_phone` variables.
- Scheduled messages and a real external provider adapter are intentionally not included in this version. A persistent scheduler is preferable to an in-memory timer and should only be added with a queue/worker.
- This is an assessment/demo project. Authentication is intentionally not implemented; do not expose the unauthenticated API publicly without adding authentication and authorization first.


## Separate provider service clarification

The dummy provider is implemented as an independent Python HTTP service in `provider_service/`, with its own Dockerfile and Compose service (`dummy-provider`). Django calls it through `backend/communication/providers.py`; provider status simulations call back to Django at `/api/v1/webhooks/dummy/`. This is a simulated provider, not a real third-party messaging integration.
