#!/usr/bin/env bash
# Backup PostgreSQL volume from docker-compose.enterprise.yml into ./backups/
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE_FILE="${VERITAS_COMPOSE_FILE:-docker-compose.enterprise.yml}"
BACKUP_DIR="${VERITAS_BACKUP_DIR:-./backups}"
POSTGRES_USER="${POSTGRES_USER:-veritas}"
POSTGRES_DB="${POSTGRES_DB:-veritas}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="${BACKUP_DIR}/veritas_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

if command -v docker >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v podman-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(podman-compose)
else
  echo "Neither docker nor podman-compose found in PATH." >&2
  exit 1
fi

echo "Dumping PostgreSQL database '$POSTGRES_DB' to $OUT_FILE..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges \
  | gzip -9 > "$OUT_FILE"

sha256sum "$OUT_FILE" > "${OUT_FILE}.sha256"
echo "Backup complete: $OUT_FILE"
