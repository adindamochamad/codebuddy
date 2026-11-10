#!/bin/sh
# Start the API, then Gradio. Used by the Hugging Face Space, not the laptop.
set -eu

mkdir -p /tmp/codebuddy-data

export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////tmp/codebuddy-data/codebuddy.db}"
export CODEBUDDY_API="${CODEBUDDY_API:-http://127.0.0.1:8000}"
export CODEBUDDY_SPACE_DEMO=1

cd /app/backend
uvicorn main:app --host 127.0.0.1 --port 8000 >/tmp/codebuddy-api.log 2>&1 &
pid_api=$!

if python - <<'PY'
import sys
import time
import urllib.request

url = "http://127.0.0.1:8000/health"
for _ in range(60):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            if resp.status == 200:
                sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
PY
then
    cd /app
    exec python /app/frontend/app.py
fi

kill "$pid_api" 2>/dev/null || true
exit 1
