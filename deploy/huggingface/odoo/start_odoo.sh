#!/usr/bin/env bash
set -euo pipefail

export PGSSLMODE="${PGSSLMODE:-require}"

exec odoo \
  --db_host="${ODOO_DB_HOST:?Set ODOO_DB_HOST (e.g. Neon host)}" \
  --db_port="${ODOO_DB_PORT:-5432}" \
  --db_user="${ODOO_DB_USER:?Set ODOO_DB_USER}" \
  --db_password="${ODOO_DB_PASSWORD:?Set ODOO_DB_PASSWORD}" \
  --http-port=7860 \
  --proxy-mode \
  --workers=0 \
  --without-demo=all
