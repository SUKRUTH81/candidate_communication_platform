#!/usr/bin/env bash
# One command to run everything locally: provider, API, worker, frontend.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r backend/requirements.txt -r provider/requirements.txt
fi
[ -d frontend/node_modules ] || (cd frontend && npm install)

PY="$ROOT/.venv/bin/python"
(cd backend && "$PY" manage.py migrate -v0)

pids=()
cleanup() { echo; echo "Stopping..."; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd backend && "$PY" manage.py runserver 8000 --noreload) & pids+=($!)
(cd backend && "$PY" manage.py run_worker) & pids+=($!)
(cd frontend && npm run dev) & pids+=($!)

echo "Frontend  http://localhost:5173"
echo "API       http://localhost:8000/api/"
wait
