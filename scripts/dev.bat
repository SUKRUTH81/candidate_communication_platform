@echo off
setlocal enabledelayedexpansion

REM One-click local startup script for Windows: provider, backend API, background worker, and frontend.
cd /d "%~dp0\.."

echo ===============================================================
echo Starting Hunar Candidate Communication Platform
echo ===============================================================

REM Find Python executable
set "PY=python"
if exist "..\hunar-candidate-communication-platform\.venv\Scripts\python.exe" (
  for %%F in ("..\hunar-candidate-communication-platform\.venv\Scripts\python.exe") do set "PY=%%~fF"
) else if exist ".venv\Scripts\python.exe" (
  for %%F in (".venv\Scripts\python.exe") do set "PY=%%~fF"
)

echo Using Python: %PY%

REM Run database migrations
cd backend
"%PY%" manage.py migrate --noinput
cd ..

REM Start services in separate command windows
echo Starting Django API server (port 8000)...
start "Backend API (8000)" cmd /k "cd backend && "%PY%" manage.py runserver 0.0.0.0:8000"

echo Starting Background Queue Worker...
start "Worker" cmd /k "cd backend && "%PY%" manage.py run_worker"

echo Starting Next.js Frontend (port 5173)...
start "Frontend (5173)" cmd /k ""%PY%" scripts\run_frontend.py"

echo.
echo ===============================================================
echo All services launched! (No mock provider needed - using real Twilio & Gmail)
echo Frontend: http://localhost:5173
echo API:      http://localhost:8000/api/
echo ===============================================================
echo Optional: run "python scripts/seed.py" to populate demo candidates.

