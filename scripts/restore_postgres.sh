#!/usr/bin/env bash
# Restore PostgreSQL dump (.sql.gz) into docker-compose.enterprise.yml and run Alembic head
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <path-to-backup.sql.gz>" >&2
  exit 1
fi

DUMP_FILE="$1"
if [ ! -f "$DUMP_FILE" ]; then
  echo "Backup file not found: $DUMP_FILE" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
COMPOSE_FILE="${VERITAS_COMPOSE_FILE:-docker-compose.enterprise.yml}"
POSTGRES_USER="${POSTGRES_USER:-veritas}"
POSTGRES_DB="${POSTGRES_DB:-veritas}"

if [ -f "${DUMP_FILE}.sha256" ]; then
  echo "Verifying checksum ${DUMP_FILE}.sha256..."
  sha256sum -c "${DUMP_FILE}.sha256"
fi

if command -v docker >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v podman-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(podman-compose)
else
  echo "Neither docker nor podman-compose found in PATH." >&2
  exit 1
fi

echo "Restoring $DUMP_FILE into '$POSTGRES_DB'..."
gunzip -c "$DUMP_FILE" | "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Ensuring migrations are at head..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T enterprise \
  alembic -c enterprise/alembic.ini upgrade head

echo "Restore complete. Verify audit hash chain via GET /api/v1/audit-events?verify=true"
