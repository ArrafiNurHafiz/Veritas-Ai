#!/usr/bin/env sh
set -e
# Idempotent synthetic dataset. Re-running only replays fixed idempotency keys.
python seed_demo.py >/dev/null
exec uvicorn veritas_harness:app --host 0.0.0.0 --port 8002
