#!/usr/bin/env bash
# Stops a Veya server that is still running (e.g. in another terminal window).
PORT="${VEYA_PORT:-8000}"
PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
if [ -n "$PIDS" ]; then kill $PIDS && echo "Stopped Veya on port $PORT."; else echo "Nothing is running on port $PORT."; fi
