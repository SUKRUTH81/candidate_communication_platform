# Hunar.ai Candidate Communication Platform 

> **Enterprise-grade recruiter communication platform** built for Hunar.ai. Manage candidates, send individual and bulk messages across channels, track real-time delivery journeys (`Sent → Delivered → Read`), handle transient and permanent provider failures with intelligent retries, and inspect the complete candidate communication history.

---

## 🌟 Executive Summary & Highlights

This implementation brings together the best engineering patterns, combining:
- **Full-Stack Type Safety:** Next.js 15 App Router, React 19, TypeScript (`.tsx`), Material UI v7, and TanStack Query.
- **Robust Relational Backend:** Python with Django 5/6 and Django REST Framework.
- **Pluggable Architecture:** Multi-channel provider registry (WhatsApp, SMS, Email) with abstract interfaces.
- **Asynchronous Background Processing:** Dedicated Django management worker command (`run_worker`) executing queued and scheduled messages with exponential backoff.
- **Real Communication Providers:** Twilio WhatsApp + SMS, Gmail SMTP Email — live message delivery with actual provider webhooks and status callbacks.
- **Security & Integrity:** Cryptographic HMAC-SHA256 signature verification on webhooks (`X-Provider-Signature`), idempotent processing, and monotonic progression protections.
- **100% Core & Bonus Features Implemented:** Candidate Management, Single & Bulk Messaging, Status Journey, Standalone Provider, History Drawer, Templates (Bonus A), Scheduled Messages (Bonus B), Multi-Provider (Bonus C), Provider Health (Bonus D), and Smart Retries (Bonus E).

---

## 🛠 Tech Stack Overview

| Tier | Technology | Description / Port |
|---|---|---|
| **Frontend** | Next.js 15, React 19, **TypeScript (`.tsx`)**, Material UI v7, TanStack Query | `http://localhost:5173` |
| **Backend API** | Python 3.13, Django 5.2 / 6, Django REST Framework, SQLite | `http://localhost:8000/api/` |
| **Background Worker** | Django Management Command (`python manage.py run_worker`) | Asynchronous queue & schedule worker |
| **Real Providers** | Twilio WhatsApp, Twilio SMS, Gmail SMTP Email | Live message delivery with webhook callbacks |
| **Testing** | `pytest` + `pytest-django` (Backend: 40 tests) & `vitest` (Frontend: 14 tests) | 100% passing test suites |

---

## 🚀 Quickstart & Setup Instructions

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** (v22.17.0 tested)
- **Docker & Docker Compose** (optional for containerized deployment)

### Option 1: One-Click Local Startup (Recommended)

#### On Windows:
Run the pre-configured batch script:
```bat
.\scripts\dev.bat
```

#### On Linux / macOS:
```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

#### Optional: Seed Realistic Demo Candidates & Templates
In another terminal:
```bash
python scripts/seed.py
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

### Option 2: Docker Compose (All Services Containerized)

```bash
docker compose up --build
```
This launches 3 isolated services:
1. `api`: Django backend API on port `8000`
2. `worker`: Background dispatch and retry worker
3. `web`: Next.js production frontend on port `5173`

---

## 🧪 Automated Test Verification

### Backend Tests (40 Tests Passing)
Run backend tests with pytest:
```bash
cd backend
python -m pytest
```
*Result:* **40 passed in 1.59s** (covering phone normalization, validation envelopes, candidate search, bulk message isolation, rate limit backoff, HMAC webhooks, monotonic progress, and scheduling).

### Frontend Tests (14 Tests Passing)
Run frontend tests with Vitest:
```bash
cd frontend
npm test
```
*Result:* **14 passed** (covering phone formatting, timestamp formatting, status mappings, template rendering with placeholders, and recipient chip packing).

### TypeScript Typecheck & Production Build
```bash
cd frontend
npm run typecheck    # 0 errors
npm run build        # Clean Next.js production build
```

---

## 📋 Feature Completeness & Architecture Traceability

### 1. Candidate Management (Spec §2)
- **Add Candidate:** Dialog with client and server validations, phone formatting, and email validation.
- **List & Search:** Paginated candidate table with instant debounced search matching by name, mobile digits, email, or candidate reference code.
- **Candidate Details:** Click candidate name anywhere to open the slide-over history drawer showing candidate ID, phone, email, and activity timeline.
- **Bulk Selection & Deletion:** Multi-page selection preserving across search queries with confirmation modal.

### 2. Individual & Bulk Messaging (Spec §3 & §4)
- **Individual Send:** Click the send icon on any candidate row or in their profile drawer.
- **Bulk Send:** Select multiple candidates across pages; the Send panel displays recipient chips, automatically collapsing beyond two lines into a `+N` badge (matching Figma specifications).
- **Independent Outcomes:** Each message is tracked as an isolated record in the database. If one recipient fails (e.g., invalid phone or rate limit), other messages continue and succeed without hindrance.

### 3. Message Status & Status Updates (Spec §5 & §7)
- **Status Journey:** Supports `Scheduled → Queued → Sending → Sent → Delivered → Read`, plus `Failed` and `Cancelled`.
- **HMAC-Secured Webhooks:** Provider sends cryptographically signed webhooks (`X-Provider-Signature: sha256=...`) to `/api/webhooks/provider/`.
- **Monotonic Guarding & Idempotency:** Duplicate provider callbacks are ignored idempotently. Lower-ranked out-of-order callbacks (e.g. `delivered` arriving after `read`) are rejected to prevent state regression.

### 4. Real Communication Providers (Spec §6)
- **Twilio WhatsApp** (default channel): Messages sent via Twilio sandbox to `whatsapp:+17372508034`.
- **Twilio SMS**: Configurable with your Twilio phone number via `TWILIO_SMS_FROM`.
- **Gmail SMTP Email**: Working email delivery via Gmail App Password (or any SMTP server).
- **Dummy/Simulation mode**: If real provider credentials are missing, the system gracefully degrades to logged delivery — useful for local development without third-party accounts.
- **Multi-provider architecture**: Adding a new channel requires only a single Python class inheriting `BaseProvider`.

### 5. Failure Handling & Intelligence (Spec §8)
- Distinguishes **Permanent Failures** (invalid phone, opted out, missing email) from **Temporary Failures** (rate limit 429, service 503, network timeout).
- Converts raw technical error codes into empathetic, actionable recruiter messages.
- For retryable failures, respects `Retry-After` headers and calculates exponential backoff with jitter.

### 6. Communication History (Spec §10)
- Reverse-chronological drawer matching the exact assignment specification:
  ```yaml
  Candidate: Rahul Sharma
  Phone: +91 9876543210
  --------------------------------------------------
  08 Oct 2026, 10:30 AM
  Hello Rahul, your interview is scheduled for tomorrow at 11:00 AM.
  Status: ✓ Delivered
  --------------------------------------------------
  07 Oct 2026, 09:15 AM
  Welcome to our hiring process.
  Status: ✓ Read
  ```
- Shows sent, delivered, and read timestamps, safe failure explanations, a manual "Retry" button for eligible failures, and a "Cancel" button for scheduled messages.

---

## 🎁 Bonus Features Included

### A. Message Templates (Bonus A)
- Full CRUD for reusable recruiter templates at `/templates`.
- Variable placeholders: `{{first_name}}`, `{{name}}`, `{{phone}}`, `{{email}}`, and `{{candidate_id}}`.
- Live preview showing how candidate tags resolve before sending.

### B. Scheduled Messages (Bonus B)
- Recruiters can check "Schedule for later" and pick a future date & time.
- Status displays as `Scheduled` with a clock icon.
- Background worker automatically triggers and dispatches messages when their due time arrives.
- Recruiters can cancel scheduled messages at any time before dispatch.

### C. Multiple Communication Providers & Channels (Bonus C)
- Channel selector: **WhatsApp**, **SMS**, and **Email**.
- Pluggable provider registry in `messaging/providers/` allowing new providers (Twilio, SendGrid, Meta WhatsApp Cloud API) to be added with a single subclass.

### D. Provider Health Monitoring (Bonus D)
- Real-time indicator chip in the top navigation bar:
  - 🟢 **Operational**
  - 🟡 **Degraded**
  - 🔴 **Unavailable**
- Clickable popover displaying live counters:
  ```
  Communication Service
  ● Operational
  ----------------------------------
  Messages Sent        127
  Messages Delivered   118
  Messages Read        95
  Messages Failed      9
  In Queue             0
  Scheduled            2
  ----------------------------------
  WhatsApp (Twilio)    ●
  SMS (Twilio)         ●
  Email (Gmail SMTP)   ●
  Background Worker    Running
  ```

### E. Smart Retries (Bonus E)
- Automatic background worker retries for transient errors.
- Manual one-click retry in the Bulk Result modal and Candidate History drawer.
- Disables retry for permanent errors with clear explanations (e.g. *"This failure is permanent. Fix candidate contact details and send a new message."*).

---

## 🧪 Interactive Failure Test Matrix

All failure scenarios are handled gracefully with user-friendly messages:

| Scenario | Provider Behavior | Platform Behavior | Recruiter UI |
|---|---|---|---|
| Invalid phone number | Provider 422 | Marked **Failed** (Permanent) | *"The candidate's phone number isn't valid."* Retry disabled. |
| Candidate opted out | Provider 422 | Marked **Failed** (Permanent) | *"This candidate has opted out of receiving messages."* Retry disabled. |
| Rate limited | Provider 429 + `Retry-After` | Queued for auto-retry | Honors `Retry-After` header and retries automatically. |
| Service temporarily unavailable | Provider 503 | Auto-retry with backoff | Worker retries with exponential backoff. |
| Missing email address | Pre-send validation | Send blocked | *"N recipient(s) have no email address, so those messages will fail."* |
| No candidates selected | Pre-send validation | Send blocked | *"Write a message before sending."* |
| Future send time in past | Pre-send validation | Send blocked | *"Pick a time at least a minute from now."* |
| Non-sandbox WhatsApp number | Twilio 572002 | Marked **Failed** | Clear error: "Add 'to' number as a verified recipient." Retry enabled. |

---

## 🏛 Architecture & Engineering Decisions

1. **Monorepo / Clean Separation:** Frontend, backend, and background worker each have well-defined boundaries and contracts.
2. **Worker vs Synchronous Dispatch:** In high-volume recruitment, external HTTP providers can have network latency or rate limits. Dispatch is handled via a dedicated background worker with database row locking (`select_for_update`), ensuring zero UI lag and no duplicate dispatches.
3. **Idempotency Keys:** Every send attempt generates a deterministic idempotency key (`{message_id}:{attempt}`). Even in network reconnects or timeouts, external providers will not duplicate messages.
4. **Real Provider Integration:** Three live channels — Twilio WhatsApp (sandbox), Twilio SMS, Gmail SMTP — are registered in a pluggable provider registry. Switching providers requires only changing an environment variable.
5. **Figma Design Fidelity:** The theme, typography, MUI table structure, status badges, two-line recipient chip packing, and drawer panels were crafted to match the provided Figma specification.

---

Built with ❤️ for **Hunar.ai** by K Sukruth.

