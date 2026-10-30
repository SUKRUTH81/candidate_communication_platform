# Interview Demo Script: Hunar.ai Candidate Communication Platform

> **Target Duration:** 5 to 7 minutes  
> **Audience:** Technical Hiring Team / Interviewers at Hunar.ai  
> **Presenter:** K Sukruth  

---

## ⏱️ Timeline & Agenda

| Step | Topic | Duration | Key Feature Highlight |
|---|---|---|---|
| **1** | Introduction & Architectural Overview | 45 sec | Tech stack, 12-factor architecture, zero-loss worker |
| **2** | Candidate Management & Search | 45 sec | Real-time search, validations, add/delete flows |
| **3** | Individual Send & Lifecycle Tracking | 60 sec | `Queued → Sent → Delivered → Read` lifecycle |
| **4** | Real Delivery (Twilio WhatsApp + Gmail SMTP) | 60 sec | Live messages on real phone and Gmail inbox |
| **5** | Bulk Messaging with Independent Isolation | 60 sec | Partial failures don't block successes |
| **6** | All 5 Bonus Features (A to E) | 90 sec | Templates, Scheduling, Health, Multi-provider, Retries |
| **7** | Technical Deep Dive & Q&A | 60 sec | Idempotency, Concurrency, WAL transactions |

---

## Step 1: Opening & Architecture (45 seconds)

### 🎙️ Talking Points:
> *"Hello! Today I'm excited to present the Candidate Communication Platform I built for Hunar.ai.*  
> *The goal was to design an enterprise-grade recruiter workspace following the Figma specifications closely, while engineering an end-to-end reliable backend that guarantees zero message loss, handles provider failures, and supports real multi-channel delivery.*
>
> *On the frontend, I used **Next.js 15, React 19, TypeScript, and Material UI v6** with TanStack Query for optimistic updates and caching.*  
> *On the backend, I built a **Django 5 REST Framework** service paired with an asynchronous queue worker, supporting both simulated chaos testing and real production providers—including **Twilio WhatsApp** and **Gmail SMTP**."*

### 🖥️ Action:
- Open **[http://localhost:5173](http://localhost:5173)**.
- Point to the clean header, candidate table, and top-right **Platform Health Chip** (`Operational`).

---

## Step 2: Candidate Management & Validations (45 seconds)

### 🎙️ Talking Points:
> *"Recruiters need quick candidate search and safe validations. Let's look at the candidate table."*

### 🖥️ Actions:
1. **Search:** In the search bar, type `Aditya`. Notice instant filtering without page reloads. Clear it.
2. **Add Candidate:** Click **+ Add Candidate** (top right).
   - Enter invalid data (e.g. phone `123`, invalid email `abc`). Show field-level validation errors.
   - Enter valid data:
     - Name: `Demo Candidate`
     - Phone: `+919876543210`
     - Email: `demo.candidate@example.com`
   - Click **Create Candidate**.
   - Show toast notification and the candidate appearing at the top of the table.

---

## Step 3: Individual Messaging & Delivery Journey (60 seconds)

### 🎙️ Talking Points:
> *"Now let's examine message delivery. One of the core requirements is tracking the complete lifecycle: Queued, Sent, Delivered, and Read.*  
> *Notice that sending never blocks the recruiter. The API persists the message in an ACID transaction and returns immediately. A dedicated queue worker handles provider communication."*

### 🖥️ Actions:
1. Click on **sukruth** in the table.
2. Select **WhatsApp** in the channel dropdown.
3. Pick the template **Interview Invitation** (Bonus A).
4. Notice how `{{first_name}}` dynamically renders to `Hi sukruth...`.
5. Click **Send Message**.
6. Show the Drawer: The message status chips update smoothly:
   - `Queued` ➔ `Sent` ➔ `Delivered` ➔ `Read`.
7. Point out the timestamp, channel badge, and delivery details.

---

## Step 4: Real Delivery Showcase (Twilio WhatsApp + Gmail SMTP) (60 seconds)

### 🎙️ Talking Points:
> *"The assignment allowed using either a dummy service or real communication providers. I implemented BOTH.*  
> *Let me demonstrate real-world multi-channel delivery right now."*

### 🖥️ Actions:
1. **Real WhatsApp Delivery:**
   - Show your phone screen or WhatsApp: Point to the incoming message from **Twilio Sandbox (`+1 737-250-8034`)** received on `+919133923489`.
2. **1-Click Direct WhatsApp (wa.me):**
   - Click the green **⚡ WhatsApp (wa.me)** button under Real Message Sharing.
   - Show how WhatsApp Web opens with the candidate's phone number and the exact personalized interview invitation pre-filled ready to send without sandbox limitations.
3. **Real Email Delivery:**
   - Change channel to **Email**, click **Send Message**.
   - Open Gmail inbox (`sukruth1435@gmail.com`) and show the real email delivered via Gmail SMTP.

---

## Step 5: Bulk Messaging & Failure Isolation (60 seconds)

### 🎙️ Talking Points:
> *"A critical requirement is bulk messaging with independent recipient tracking: if one candidate fails, it must never fail or block the others."*

### 🖥️ Actions:
1. In the candidate table, select **3 checkboxes**:
   - `sukruth` (Valid number)
   - `Demo Invalid Number` (Seed candidate configured to fail)
   - `Demo Rate Limited` (Seed candidate configured for rate limiting)
2. The bottom bar appears: **3 Candidates Selected**. Click **Compose Bulk Message**.
3. Select template **Document Verification**, click **Send to 3 Candidates**.
4. The **Bulk Dispatch Dialog** appears showing per-recipient progress:
   - Candidate 1: `Succeeded / Sent`
   - Candidate 2: `Failed (Invalid Recipient)` — with friendly non-technical explanation
   - Candidate 3: `Queued / Retrying`
5. Emphasize: *"Notice each message is tracked independently with its own UUID and idempotency key."*

---

## Step 6: The 5 Bonus Features (90 seconds)

### 🎙️ Talking Points:
> *"I implemented all 5 bonus features requested in the assignment:"*

1. **Bonus A — Message Templates (`/templates`):**
   - Click **Templates** in the left navigation.
   - Show pre-seeded templates (*Interview Invitation, Document Verification, Offer Confirmation*).
   - Show placeholder tags: `{{first_name}}`, `{{candidate_id}}`, `{{email}}`.
   - Click **+ New Template**, enter a name and body, and save.

2. **Bonus B — Scheduled Messages:**
   - Go back to Candidates, select a candidate.
   - Toggle **Schedule for later**.
   - Pick a date/time 5 minutes in the future.
   - Click **Schedule Message**. Show badge: `Scheduled` with target dispatch time. Show the **Cancel** button.

3. **Bonus C — Multiple Providers:**
   - Highlight the Channel selector: **WhatsApp (Twilio)**, **SMS (Twilio SMS)**, and **Email (Gmail SMTP)**.
   - Show how the recipient field switches automatically from Phone to Email based on channel.

4. **Bonus D — Provider Health & Aggregated Metrics:**
   - Click the **Platform Health** chip in the top navbar.
   - The diagnostic modal opens:
     - Shows overall system status: `Operational`.
     - Worker heartbeat: `Active`.
     - Per-provider cards (Twilio WhatsApp, Twilio SMS, Gmail SMTP).
     - Aggregated live counters: *Sent, Delivered, Read, Failed, Pending*.

5. **Bonus E — Smart Retries & Exponential Backoff:**
   - Open a failed message in the candidate drawer.
   - Show how permanent errors (`INVALID_RECIPIENT`) disallow retry and display: *"Fix their contact details"*.
   - Show how transient errors (`TEMPORARY_FAILURE`, `RATE_LIMITED`) feature a **Retry Now** button.
   - Explain the backend circuit breaker and exponential backoff (`5s, 10s, 20s`).

---

## Step 7: Technical Highlights & Architecture Close (45 seconds)

### 🎙️ Talking Points:
> *"To ensure enterprise quality, I paid close attention to backend engineering details:*
> - * **Concurrency:** SQLite is configured with WAL (Write-Ahead Logging) and `IMMEDIATE` transaction locking to prevent write deadlocks between the API and the worker.*
> - * **Idempotency:** Webhook events use cryptographic signatures and unique event IDs (`event_id`) to prevent duplicate transitions.*
> - * **Monotonic State Machine:** Message status can only move forward (`Queued → Sent → Delivered → Read`), so out-of-order callbacks can never revert delivered messages.*
> - * **Automated Testing:** 40 backend pytest unit/contract tests and 14 frontend vitest component tests are 100% passing.*
>
> *Thank you! I'm happy to dive into any specific code or design decisions."*

---

## 💡 Anticipated Questions & Answers

| Question | Recommended Answer |
|---|---|
| **Why SQLite instead of PostgreSQL?** | SQLite with WAL mode and `IMMEDIATE` transactions provides zero-configuration local portability while supporting concurrent reads and non-blocking worker writes. For production, the Django ORM allows swapping to PostgreSQL with just `DATABASE_URL`. |
| **How do you handle worker crashes?** | Any message left in `sending` state longer than `STALE_SENDING_SECONDS` (60s) is automatically recovered and re-queued on worker startup. |
| **How did you avoid blocking HTTP threads during sends?** | The API endpoint strictly validates and writes to SQLite (`status=queued`), taking <10ms. The background worker asynchronously claims batches using row locks and dispatches them. |
| **What happens if Twilio/WhatsApp webhook is lost?** | The worker runs an automatic reconciliation loop every 45s (`reconcile()`) that queries the provider REST API for messages that haven't transitioned, acting as a safety net. |
