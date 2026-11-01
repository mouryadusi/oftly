#!/usr/bin/env bash
# Creates the virtual environment on first run, installs dependencies, starts OFTLY. Stop with Ctrl+C.
set -e
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
PORT="${OFTLY_PORT:-8000}"
echo "OFTLY is starting at http://127.0.0.1:$PORT  (Ctrl+C to stop)"
if command -v open >/dev/null; then (sleep 2 && open "http://127.0.0.1:$PORT") & fi
cd backend && exec ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
