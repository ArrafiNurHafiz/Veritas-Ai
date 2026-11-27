#!/usr/bin/env bash
# =============================================================================
# VERITAS AI — Enterprise Local Services Orchestrator
# Agent :8001 <-> Enterprise Harness :8002 <-> Frontend :3000
# Usage: ./start_local.sh            # foreground, Ctrl+C stops everything
#        SKIP_MIGRATE=1 ./start_local.sh
# =============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:///$DIR/enterprise.db}"
export VERITAS_AGENT_URL="${VERITAS_AGENT_URL:-http://127.0.0.1:8001}"
export VERITAS_AGENT_TOKEN="${VERITAS_AGENT_TOKEN:-dev-agent-token}"
export VERITAS_CORS_ORIGINS="${VERITAS_CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}"
export VERITAS_INTERNAL_TOKEN="${VERITAS_INTERNAL_TOKEN:-dev-internal}"
export VERITAS_SSO_BYPASS="${VERITAS_SSO_BYPASS:-1}"
export VERITAS_KMS_BYPASS="${VERITAS_KMS_BYPASS:-1}"
export VERITAS_AUTH_TEST_MODE="${VERITAS_AUTH_TEST_MODE:-1}"
export HARNESS_URL="${HARNESS_URL:-http://127.0.0.1:8002}"
export NEXT_PUBLIC_HARNESS_URL="${NEXT_PUBLIC_HARNESS_URL:-http://127.0.0.1:8002}"
export NEXT_PUBLIC_VERITAS_MODE="${NEXT_PUBLIC_VERITAS_MODE:-enterprise}"
export NEXT_PUBLIC_VERITAS_TEST_MODE="${NEXT_PUBLIC_VERITAS_TEST_MODE:-1}"
export VERITAS_ERP_ADAPTER="${VERITAS_ERP_ADAPTER:-webhook}"
export VERITAS_ERP_WEBHOOK_URL="${VERITAS_ERP_WEBHOOK_URL:-http://127.0.0.1:8003/api/erp/webhook}"
export VERITAS_ALLOW_INSECURE_WEBHOOKS="${VERITAS_ALLOW_INSECURE_WEBHOOKS:-1}"
export ERP_SANDBOX_DB="${ERP_SANDBOX_DB:-$DIR/erp_sandbox/erp_sandbox.db}"
export ERP_SANDBOX_API_KEY="${ERP_SANDBOX_API_KEY:-${VERITAS_ERP_API_KEY:-}}"
export ERP_SANDBOX_HMAC_SECRET="${ERP_SANDBOX_HMAC_SECRET:-${VERITAS_ERP_HMAC_SECRET:-}}"
export VERITAS_PUBLIC_URL="${VERITAS_PUBLIC_URL:-http://localhost:3000}"
export MAIL_SANDBOX_DB="${MAIL_SANDBOX_DB:-$DIR/mail_sandbox/mail_sandbox.db}"
export SMTP_HOST="${SMTP_HOST:-127.0.0.1}"
export SMTP_PORT="${SMTP_PORT:-1025}"
export SMTP_USE_TLS="${SMTP_USE_TLS:-0}"
export SMTP_FROM="${SMTP_FROM:-noreply@veritas.local}"
export VERITAS_APPROVAL_NOTIFY_EMAILS="${VERITAS_APPROVAL_NOTIFY_EMAILS:-approver@veritas.local,admin@veritas.local}"

PYTHON_BIN="$DIR/.venv/bin/python"
[ -f "$PYTHON_BIN" ] || PYTHON_BIN="python3"
UVICORN_BIN="$DIR/.venv/bin/uvicorn"
[ -f "$UVICORN_BIN" ] || UVICORN_BIN="uvicorn"
ALEMBIC_BIN="$DIR/.venv/bin/alembic"
[ -f "$ALEMBIC_BIN" ] || ALEMBIC_BIN="alembic"

echo "================================================================================"
echo "  VERITAS AI — Enterprise Console"
echo "  Agent :8001 | Enterprise Harness :8002 | Frontend :3000"
echo "================================================================================"

if [ "${SKIP_MIGRATE:-0}" != "1" ]; then
  echo "-> Running Alembic migrations (enterprise/alembic.ini)..."
  DATABASE_URL="$DATABASE_URL" "$ALEMBIC_BIN" -c enterprise/alembic.ini upgrade head >/dev/null
fi

PIDS=()
cleanup() {
  echo ""
  echo "-> Stopping services started by this script..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null || true; fi
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Start local 9router LLM gateway if VERITAS_LLM_BASE_URL targets localhost:20128
ROUTER_BIN="$(command -v 9router 2>/dev/null || true)"
[ -n "$ROUTER_BIN" ] || [ ! -x "$HOME/.bun/bin/9router" ] || ROUTER_BIN="$HOME/.bun/bin/9router"
case "${VERITAS_LLM_BASE_URL:-}" in
  http://127.0.0.1:20128*|http://localhost:20128*)
    if "$PYTHON_BIN" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(s.connect_ex(('127.0.0.1',20128)))" 2>/dev/null; then
      echo "-> [0/5] 9router already listening on 127.0.0.1:20128; reusing it."
    elif [ -n "$ROUTER_BIN" ]; then
      echo "-> [0/5] Starting 9router LLM gateway on 127.0.0.1:20128..."
      "$ROUTER_BIN" -n --skip-update -H 127.0.0.1 -p 20128 >/dev/null 2>&1 &
      PIDS+=($!)
      for _ in $(seq 1 20); do
        sleep 1
        if "$PYTHON_BIN" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(s.connect_ex(('127.0.0.1',20128)))" 2>/dev/null; then
          echo "   9router :20128 READY"
          break
        fi
      done
    else
      echo "WARN: VERITAS_LLM_BASE_URL targets :20128 but 9router binary was not found." >&2
    fi
    ;;
esac

echo "-> [1/5] Agent Service on 127.0.0.1:8001..."
VERITAS_AGENT_TOKEN="$VERITAS_AGENT_TOKEN" \
  VERITAS_LLM_BASE_URL="${VERITAS_LLM_BASE_URL:-}" \
  VERITAS_LLM_API_KEY="${VERITAS_LLM_API_KEY:-}" \
  VERITAS_LLM_MODEL="${VERITAS_LLM_MODEL:-}" \
  OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}" \
  OPENROUTER_MODEL="${OPENROUTER_MODEL:-}" \
  VERITAS_PUBLIC_URL="$VERITAS_PUBLIC_URL" \
  "$UVICORN_BIN" agent_service:app --host 127.0.0.1 --port 8001 --log-level warning &
PIDS+=($!)

NEED_ERP_SANDBOX=0
if [ "${VERITAS_ERP_ADAPTER}" != "odoo" ]; then
  NEED_ERP_SANDBOX=1
  echo "-> [2/5] ERP Sandbox Service on 127.0.0.1:8003..."
  ERP_SANDBOX_DB="$ERP_SANDBOX_DB" \
    VERITAS_HARNESS_URL="$HARNESS_URL" \
    ERP_SANDBOX_API_KEY="$ERP_SANDBOX_API_KEY" \
    ERP_SANDBOX_HMAC_SECRET="$ERP_SANDBOX_HMAC_SECRET" \
    "$UVICORN_BIN" erp_sandbox.main:app --host 127.0.0.1 --port 8003 --log-level warning &
  PIDS+=($!)
else
  echo "-> [2/5] ERP Sandbox skipped (using real Odoo adapter: ${VERITAS_ERP_WEBHOOK_URL})."
fi

NEED_MAIL_SANDBOX=0
if [ "${SMTP_HOST}" = "127.0.0.1" ] || [ "${SMTP_HOST}" = "localhost" ]; then
  NEED_MAIL_SANDBOX=1
  echo "-> [3/5] Mail Sandbox (SMTP :1025 | Inbox :8025)..."
  MAIL_SANDBOX_DB="$MAIL_SANDBOX_DB" \
    "$UVICORN_BIN" mail_sandbox.server:app --host 127.0.0.1 --port 8025 --log-level warning &
  PIDS+=($!)
else
  echo "-> [3/5] Mail Sandbox skipped (using real SMTP: ${SMTP_HOST}:${SMTP_PORT})."
fi

echo "-> [4/5] Enterprise Harness Gateway on 127.0.0.1:8002..."
DATABASE_URL="$DATABASE_URL" \
  VERITAS_AGENT_URL="$VERITAS_AGENT_URL" \
  VERITAS_AGENT_TOKEN="$VERITAS_AGENT_TOKEN" \
  VERITAS_CORS_ORIGINS="$VERITAS_CORS_ORIGINS" \
  VERITAS_INTERNAL_TOKEN="$VERITAS_INTERNAL_TOKEN" \
  VERITAS_SSO_BYPASS="$VERITAS_SSO_BYPASS" \
  VERITAS_KMS_BYPASS="$VERITAS_KMS_BYPASS" \
  VERITAS_AUTH_TEST_MODE="$VERITAS_AUTH_TEST_MODE" \
  VERITAS_ERP_ADAPTER="$VERITAS_ERP_ADAPTER" \
  VERITAS_ERP_WEBHOOK_URL="$VERITAS_ERP_WEBHOOK_URL" \
  VERITAS_ALLOW_INSECURE_WEBHOOKS="$VERITAS_ALLOW_INSECURE_WEBHOOKS" \
  SMTP_HOST="$SMTP_HOST" \
  SMTP_PORT="$SMTP_PORT" \
  SMTP_USE_TLS="$SMTP_USE_TLS" \
  SMTP_FROM="$SMTP_FROM" \
  VERITAS_APPROVAL_NOTIFY_EMAILS="$VERITAS_APPROVAL_NOTIFY_EMAILS" \
  "$UVICORN_BIN" enterprise.main:app --host 127.0.0.1 --port 8002 --log-level warning &
PIDS+=($!)

echo "-> Waiting for backend health (max 20s)..."
AGENT_OK=0
ERP_OK=1; [ "$NEED_ERP_SANDBOX" = "1" ] && ERP_OK=0
MAIL_OK=1; [ "$NEED_MAIL_SANDBOX" = "1" ] && MAIL_OK=0
HARNESS_OK=0
for _ in $(seq 1 20); do
  sleep 1
  curl -fsS http://127.0.0.1:8001/health/live >/dev/null 2>&1 && AGENT_OK=1
  if [ "$NEED_ERP_SANDBOX" = "1" ]; then curl -fsS http://127.0.0.1:8003/health/live >/dev/null 2>&1 && ERP_OK=1; fi
  if [ "$NEED_MAIL_SANDBOX" = "1" ]; then curl -fsS http://127.0.0.1:8025/health/live >/dev/null 2>&1 && MAIL_OK=1; fi
  curl -fsS http://127.0.0.1:8002/health/ready >/dev/null 2>&1 && HARNESS_OK=1
  if [ "$AGENT_OK" = "1" ] && [ "$ERP_OK" = "1" ] && [ "$MAIL_OK" = "1" ] && [ "$HARNESS_OK" = "1" ]; then break; fi
done
if [ "$AGENT_OK" != "1" ] || [ "$ERP_OK" != "1" ] || [ "$MAIL_OK" != "1" ] || [ "$HARNESS_OK" != "1" ]; then
  echo "ERROR: backend did not become healthy (agent=$AGENT_OK erp=$ERP_OK mail=$MAIL_OK harness=$HARNESS_OK)." >&2
  exit 1
fi
echo "   agent :8001 LIVE | enterprise harness :8002 READY (erp_sandbox=$NEED_ERP_SANDBOX mail_sandbox=$NEED_MAIL_SANDBOX)"

if curl -fsS http://127.0.0.1:3000/ -o /dev/null 2>/dev/null; then
  echo "-> [5/5] Frontend already responding on :3000; reusing it (no duplicate process)."
else
  echo "-> [5/5] Frontend on http://localhost:3000..."
  if command -v pnpm >/dev/null 2>&1; then
    (cd frontend && pnpm dev --port 3000) &
  else
    (cd frontend && ./node_modules/.bin/next dev --port 3000) &
  fi
  PIDS+=($!)
fi

echo "================================================================================"
echo "  Ready:  http://localhost:3000  |  console: http://localhost:3000/dashboard"
echo "================================================================================"
echo "  Ctrl+C to stop services started here."
echo "================================================================================"

wait
