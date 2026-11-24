#!/usr/bin/env bash
# =============================================================================
# VERITAS AI — Local Services Orchestrator
# Agent :8001 <-> Harness :8002 <-> Frontend :3000 (deterministic, no LLM key)
# Usage: ./start_local.sh            # foreground, Ctrl+C stops everything
#        SKIP_SEED=1 ./start_local.sh
# Preflight: .venv/bin/python scripts/demo_preflight.py
# =============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export VERITAS_DB="${VERITAS_DB:-$DIR/veritas.db}"
export VERITAS_AGENT_URL="${VERITAS_AGENT_URL:-http://127.0.0.1:8001}"
export VERITAS_AGENT_TOKEN="${VERITAS_AGENT_TOKEN:-dev-agent-token}"
export VERITAS_CORS_ORIGINS="${VERITAS_CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}"
export VERITAS_INTERNAL_TOKEN="${VERITAS_INTERNAL_TOKEN:-dev-internal}"
export HARNESS_URL="${HARNESS_URL:-http://127.0.0.1:8002}"
export NEXT_PUBLIC_HARNESS_URL="${NEXT_PUBLIC_HARNESS_URL:-http://127.0.0.1:8002}"

# The demo planner is deterministic by default. Never inherit an LLM key.
unset VERITAS_LLM_BASE_URL VERITAS_LLM_API_KEY VERITAS_LLM_MODEL || true

PYTHON_BIN="$DIR/.venv/bin/python"
[ -f "$PYTHON_BIN" ] || PYTHON_BIN="python3"
UVICORN_BIN="$DIR/.venv/bin/uvicorn"
[ -f "$UVICORN_BIN" ] || UVICORN_BIN="uvicorn"

echo "================================================================================"
echo "  VERITAS AI — Local Demo"
echo "  Agent :8001 (proposal only) | Harness :8002 | Frontend :3000"
echo "================================================================================"

if [ "${SKIP_SEED:-0}" != "1" ]; then
  echo "-> Seeding/refreshing synthetic Nexora dataset (idempotent)..."
  "$PYTHON_BIN" seed_demo.py >/dev/null
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

echo "-> [1/3] Agent Service on 127.0.0.1:8001..."
VERITAS_AGENT_TOKEN="$VERITAS_AGENT_TOKEN" \
  "$UVICORN_BIN" agent_service:app --host 127.0.0.1 --port 8001 --log-level warning &
PIDS+=($!)

echo "-> [2/3] Harness Gateway on 127.0.0.1:8002..."
VERITAS_DB="$VERITAS_DB" \
  VERITAS_AGENT_URL="$VERITAS_AGENT_URL" \
  VERITAS_AGENT_TOKEN="$VERITAS_AGENT_TOKEN" \
  VERITAS_CORS_ORIGINS="$VERITAS_CORS_ORIGINS" \
  VERITAS_INTERNAL_TOKEN="$VERITAS_INTERNAL_TOKEN" \
  "$UVICORN_BIN" veritas_harness:app --host 127.0.0.1 --port 8002 --log-level warning &
PIDS+=($!)

echo "-> Waiting for backend health (max 20s)..."
AGENT_OK=0
HARNESS_OK=0
for _ in $(seq 1 20); do
  sleep 1
  curl -fsS http://127.0.0.1:8001/health/live >/dev/null 2>&1 && AGENT_OK=1
  curl -fsS http://127.0.0.1:8002/health/ready >/dev/null 2>&1 && HARNESS_OK=1
  if [ "$AGENT_OK" = "1" ] && [ "$HARNESS_OK" = "1" ]; then break; fi
done
if [ "$AGENT_OK" != "1" ] || [ "$HARNESS_OK" != "1" ]; then
  echo "ERROR: backend did not become healthy (agent=$AGENT_OK harness=$HARNESS_OK)." >&2
  exit 1
fi
echo "   agent :8001 LIVE | harness :8002 READY"

if curl -fsS http://127.0.0.1:3000/ -o /dev/null 2>&1; then
  echo "-> [3/3] Frontend already responding on :3000; reusing it (no duplicate process)."
else
  echo "-> [3/3] Frontend on http://localhost:3000..."
  (cd frontend && pnpm dev --port 3000) &
  PIDS+=($!)
fi

echo "================================================================================"
echo "  Ready:  http://localhost:3000  |  console: http://localhost:3000/dashboard"
echo "  Preflight: .venv/bin/python scripts/demo_preflight.py"
echo "  Ctrl+C to stop services started here."
echo "================================================================================"

wait
