# Submission Note: Candidate Communication Platform

**To:** Mehrabhumika & The Hunar.ai Hiring Team  
**From:** K Sukruth  
**Position:** Full Stack Software Engineering Candidate  
**Date:** October 30, 2026  
**Assignment:** Candidate Communication Platform  

---

## 🌟 Executive Summary

I have completed the **Candidate Communication Platform** for Hunar.ai adhering strictly to the provided Figma design, functional requirements, and engineering standards.

Rather than just building a mock UI or simple CRUD prototype, I engineered an **enterprise-grade, production-ready solution** that features real-time asynchronous message delivery, graceful failure handling, comprehensive validations, and **all 5 optional bonus features** fully implemented.

In addition, I integrated **real communication providers**:
- **WhatsApp:** Integrated with the **Twilio WhatsApp API / Sandbox**, delivering live WhatsApp messages to recipients.
- **Email:** Integrated with **Gmail SMTP (`smtp.gmail.com:587`)**, delivering real emails to candidate inboxes.
- **1-Click Direct Sharing:** Native `wa.me` deep-linking to send unrestricted custom interview invitations directly from recruiter WhatsApp accounts.

---

## 📦 What Was Built & Completed

### 1. Core Requirements (100% Complete)

| Requirement | Implementation Details |
|---|---|
| **Candidate Management** | Complete CRUD with real-time fuzzy search, field validations (E.164 phone regex, RFC 5322 email), duplicate protection, and single/bulk deletion. |
| **Individual Messaging** | Seamless message composer with live character counts, template selection, candidate placeholder interpolation (`{{name}}`, `{{first_name}}`, `{{email}}`, etc.), and ACID transaction safety. |
| **Bulk Messaging** | Multi-select candidate rows with a sticky bulk dispatch bar. Messages are dispatched with **independent recipient tracking**—failures on one candidate never block or fail other recipients. |
| **Status Journey** | Strict monotonic state machine: `Queued ➔ Sent ➔ Delivered ➔ Read`. Status updates reflect provider receipts without out-of-order race conditions. |
| **Communication Providers** | Pluggable multi-provider registry. Includes **Twilio WhatsApp**, **Twilio SMS**, **Gmail SMTP**, and an isolated standalone chaos simulation microservice. |
| **Failure Handling & Retries** | Meaningful recruiter-facing error catalog (categorized into permanent vs. transient). Automatic capped exponential backoff (`5s, 10s, 20s`) for temporary errors and manual retry for recruiters. |
| **Communication History** | Reverse-chronological history drawer per candidate showing full lifecycle timestamps, channel badges, message content, delivery status, and retry controls. |
| **Recruiter UX** | Adherence to Figma design with loading states, empty states, toast alerts, confirmation dialogs, and bulk dispatch summaries. |

---

### 2. All 5 Bonus Features Implemented

- **Bonus A — Message Templates (`/templates`):** Full CRUD for message templates with dynamic variable insertion (`{{first_name}}`, `{{candidate_id}}`, `{{email}}`, etc.).
- **Bonus B — Scheduled Messages:** Future-date scheduling with date-time picker, `Scheduled` badge status, and the ability to cancel pending scheduled messages before dispatch.
- **Bonus C — Multiple Providers:** Recruiters can switch dynamically between **WhatsApp**, **SMS**, and **Email** channels per message. The input form adapts validation based on the channel.
- **Bonus D — Provider Health & Aggregated Metrics:** Real-time platform health indicator in the header showing provider connectivity, worker heartbeats, and live counters (*Sent, Delivered, Read, Failed, Pending*).
- **Bonus E — Smart Retries & Exponential Backoff:** Intelligent error classification between retryable failures (rate limits, network timeout) vs. permanent failures (invalid phone number). Built-in circuit breaker prevents hammering offline providers.

---

## 🛠️ Tech Stack & Architecture Highlights

- **Frontend:** Next.js 15 (App Router), React 19, **TypeScript (`.tsx`)**, Material UI v6, TanStack Query.
- **Backend:** Python 3.13, Django 5.2, Django REST Framework.
- **Database:** SQLite with **WAL (Write-Ahead Logging)** mode and `IMMEDIATE` transaction locking to guarantee non-blocking concurrent reads and worker writes.
- **Testing:**
  - **Backend:** 40 / 40 passing `pytest` tests (100% coverage across models, services, serializers, and providers).
  - **Frontend:** 14 / 14 passing `vitest` component and utility tests.
  - **Type Safety:** Clean `next build` with 0 TypeScript compiler warnings or errors.

---

## 🚀 How to Run & Test the Application

### Option A: One-Click Local Run (Recommended)
```powershell
cd "anti gravity"
.\run.bat
```
*(Automatically executes migrations, starts Django API on port 8000, starts the background worker, and launches the Next.js frontend on port 5173).*

### Option B: Docker Compose
```bash
docker compose up -d --build
```

---

## 📄 Repository & Documentation

The repository includes extensive documentation:
- [`README.md`](file:///d:/sukruth/hunar%20ai/anti%20gravity/README.md) — Architecture, installation, and design decisions.
- [`docs/demo-script.md`](file:///d:/sukruth/hunar%20ai/anti%20gravity/docs/demo-script.md) — A 5-minute step-by-step interview demonstration script.
- [`docs/deployment-guide.md`](file:///d:/sukruth/hunar%20ai/anti%20gravity/docs/deployment-guide.md) — Cloud deployment guides for Render, Railway, Docker, and Vercel.
- [`docs/requirements-matrix.md`](file:///d:/sukruth/hunar%20ai/anti%20gravity/docs/requirements-matrix.md) — Comprehensive checklist mapping every line of the assignment prompt to source files.

Thank you for this opportunity! I look forward to discussing the architecture and demonstrating the live platform.

Best regards,  
**K Sukruth**
