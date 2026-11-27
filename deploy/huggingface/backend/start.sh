#!/usr/bin/env bash
set -euo pipefail

export VERITAS_AGENT_URL="${VERITAS_AGENT_URL:-http://127.0.0.1:8001}"
export VERITAS_AGENT_TOKEN="${VERITAS_AGENT_TOKEN:-hf-agent-token}"
export VERITAS_SSO_BYPASS="${VERITAS_SSO_BYPASS:-1}"
export VERITAS_AUTH_TEST_MODE="${VERITAS_AUTH_TEST_MODE:-1}"

echo "-> Running Alembic migrations..."
alembic -c enterprise/alembic.ini upgrade head

echo "-> Starting Agent Service on 127.0.0.1:8001..."
uvicorn agent_service:app --host 127.0.0.1 --port 8001 --log-level warning &

for _ in $(seq 1 20); do
  if python3 -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(s.connect_ex(('127.0.0.1', 8001)))" 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "-> Starting Enterprise Harness on 0.0.0.0:${PORT:-7860}..."
exec uvicorn enterprise.main:app --host 0.0.0.0 --port "${PORT:-7860}" --proxy-headers --forwarded-allow-ips="*"
