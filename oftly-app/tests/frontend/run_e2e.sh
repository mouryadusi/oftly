#!/usr/bin/env bash
# Runs the real-browser suite against a throw-away data folder and a fake weather service (no internet needed).
# Usage: tests/frontend/run_e2e.sh [STEP_NAME_REGEX]      e.g. tests/frontend/run_e2e.sh "axe WCAG"
# Needs: Node 18+, `npm install` in tests/frontend, and Chrome (CHROME_PATH=...) or Linux @sparticuz/chromium. Python: PYTHON=.venv/bin/python
set -euo pipefail
cd "$(dirname "$0")/../.."
PY="${PYTHON:-.venv/bin/python}"; PORT="${E2E_PORT:-8011}"; D="$(mktemp -d)"
OFTLY_DATA="$D" "$PY" tests/frontend/seed_e2e.py >/dev/null 2>&1
OFTLY_DATA="$D" OFTLY_PORT="$PORT" "$PY" tests/frontend/serve_fake_weather.py >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV 2>/dev/null || true; rm -rf "$D"' EXIT
for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null && break; sleep 1; done
cd tests/frontend && ONLY="${1:-}" node e2e.mjs "http://127.0.0.1:$PORT"
