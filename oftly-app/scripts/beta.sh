#!/usr/bin/env bash
# PRIVATE BETA ON YOUR MAC, reachable from your iPhone over HTTPS (Cloudflare "quick tunnel": free, no account, URL changes every run).
# UNTESTED in the build sandbox (no network access to Cloudflare there): run it once yourself and follow docs/IPHONE_TESTING.md.
# Requires:  brew install cloudflared      Stop with Ctrl+C. Your Mac must stay awake while friends test.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v cloudflared >/dev/null || { echo "Install the tunnel tool first:  brew install cloudflared"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
PORT="${OFTLY_PORT:-8000}"
export OFTLY_DATA="${OFTLY_DATA:-$PWD/data-beta}"                       # beta data is kept apart from any other data
INVITE="${OFTLY_INVITE_CODES:-$(.venv/bin/python -c 'import secrets;print(secrets.token_urlsafe(9))')}"
LOG="$(mktemp)"
cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate >"$LOG" 2>&1 &
TUN=$!; SRV=""
trap 'kill $TUN $SRV 2>/dev/null || true' EXIT
URL=""
for _ in $(seq 1 40); do URL="$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" | head -1 || true)"; [ -n "$URL" ] && break; sleep 1; done
[ -n "$URL" ] || { echo "The tunnel did not start. Details: $LOG"; exit 1; }
export OFTLY_ALLOWED_HOSTS="${URL#https://}" OFTLY_PUBLIC_URL="$URL" OFTLY_COOKIE_SECURE=1 OFTLY_INVITE_CODES="$INVITE"
echo; echo "============================================================"
echo " OFTLY private beta is LIVE (while this window stays open)"
echo "   Open on iPhone (Safari):  $URL"
echo "   Invite code for friends:  $INVITE"
echo "   Data folder:              $OFTLY_DATA"
echo "============================================================"; echo
cd backend && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --proxy-headers --forwarded-allow-ips=127.0.0.1 &
SRV=$!
wait $SRV
