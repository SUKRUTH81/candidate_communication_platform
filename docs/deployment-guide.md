# Deployment Guide: Hunar.ai Candidate Communication Platform

This guide outlines multiple deployment options for taking the Candidate Communication Platform live, ranging from containerized Docker deployments to free-tier cloud hosting on Render, Railway, or Vercel.

---

## 📋 Architecture & Ports Overview

The platform consists of three coordinated services:

```
[ Next.js 15 Frontend ]  (Port 5173 / 3000)
         │  HTTP / JSON
         ▼
[ Django 5 REST API ]     (Port 8000)
         ▲
         │ Shared Database (SQLite WAL / PostgreSQL)
         ▼
[ Background Worker ]     (manage.py run_worker)
         │
         ├──► Twilio WhatsApp Sandbox (+17372508034)
         ├──► Twilio SMS REST API
         └──► Gmail SMTP Server (smtp.gmail.com:587)
```

---

## Option 1: Docker Compose (Recommended for Any Cloud VM)

The repository includes complete Docker configurations for production.

### 1. Build and Start All Containers
```bash
docker compose up -d --build
```

### 2. Verify Container Health
```bash
docker compose ps
```
Services running:
- `backend`: Django API on port `8000`
- `worker`: Background dispatch worker
- `frontend`: Next.js web application on port `5173`

### 3. Run Migrations & Seed Data (First Time Only)
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python scripts/seed.py
```

Access the application at `http://YOUR_SERVER_IP:5173`.

---

## Option 2: Render.com (Free Cloud Hosting)

Render offers free web services and background workers with zero server maintenance.

### Step 1: Create a GitHub Repository
1. Initialize git (if not already done) and push to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: complete candidate communication platform with real messaging"
   git remote add origin https://github.com/YOUR_USERNAME/hunar-candidate-platform.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy Backend API on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) ➔ **New Web Service**.
2. Connect your GitHub repository.
3. Configure settings:
   - **Name:** `hunar-platform-api`
   - **Root Directory:** `anti gravity/backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate`
   - **Start Command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Add Environment Variables:
   ```env
   DJANGO_SECRET_KEY=production-secret-key-change-me
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=*
   CORS_ALLOW_ALL_ORIGINS=True
   ```
5. Click **Create Web Service**. Note your backend URL (e.g. `https://hunar-api.onrender.com`).

### Step 3: Deploy Background Worker on Render
1. In Render ➔ **New Background Worker**.
2. Connect the same repository.
3. Configure settings:
   - **Name:** `hunar-platform-worker`
   - **Root Directory:** `anti gravity/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python manage.py run_worker`
4. Add the exact same environment variables as Step 2.
5. Click **Create Background Worker**.

### Step 4: Deploy Frontend on Vercel or Render
1. Go to [Vercel](https://vercel.com/) ➔ **Add New Project**.
2. Connect your GitHub repository.
3. Set **Root Directory:** `anti gravity/frontend`.
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_BASE_URL=https://hunar-api.onrender.com/api`
5. Click **Deploy**. Your live frontend is now connected to your cloud backend!

---

## Option 3: Railway.app (Easiest All-in-One Deployment)

Railway supports Docker Compose directly:
1. Push your repository to GitHub.
2. In Railway, click **New Project ➔ Deploy from GitHub Repo**.
3. Railway automatically detects `docker-compose.yml` and launches all 3 services together.
4. Add your Twilio and SMTP environment variables in the Railway dashboard.

---

## Option 4: Local Evaluation / Interview Presentation (Zero Cloud Setup)

If you are presenting locally during the interview or sharing a screen:

1. Clone repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/hunar-candidate-platform.git
   cd hunar-candidate-platform
   ```
2. Run one-click startup:
   ```powershell
   .\run.bat
   ```
3. Open **[http://localhost:5173](http://localhost:5173)**.
4. Seed demo data (optional):
   ```bash
   python scripts/seed.py
   ```

All real services (Twilio WhatsApp, Gmail SMTP, Background Worker, Next.js UI) run immediately out of the box.

---

## 🔑 Environment Variables Reference

| Variable | Default Value | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | `dev-insecure-key` | Django cryptographic secret |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | Allows frontend origin communication |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000/api` | Backend API URL for Frontend |

