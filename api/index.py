"""Vercel Serverless entrypoint combining Enterprise Harness, Agent Service, and ERP Sandbox."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure writable /tmp SQLite paths and demo-ready defaults on Vercel Serverless
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/enterprise.db")
os.environ.setdefault("VERITAS_DB", "/tmp/veritas_sessions.db")
os.environ.setdefault("VERITAS_SESSION_STORE", "jwt")
os.environ.setdefault("VERITAS_SESSION_SECRET", "veritas-vercel-stateless-session-2026")
os.environ.setdefault("ERP_SANDBOX_DB", "/tmp/erp_sandbox.db")
os.environ.setdefault("VERITAS_SSO_BYPASS", "1")
os.environ.setdefault("VERITAS_AUTH_TEST_MODE", "1")
os.environ.setdefault("VERITAS_KMS_BYPASS", "1")
os.environ.setdefault("VERITAS_EXPIRY_SWEEP_SECONDS", "0")
os.environ.setdefault("VERITAS_ERP_ADAPTER", "webhook")
os.environ.setdefault("VERITAS_ALLOW_INSECURE_WEBHOOKS", "1")
os.environ.setdefault("VERITAS_AGENT_TOKEN", "vercel-demo-agent-token")

_self_host = (
    os.environ.get("VERITAS_BACKEND_HOST")
    or os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
    or os.environ.get("VERCEL_URL")
    or ""
).strip()
if _self_host:
    _base = _self_host if _self_host.startswith("http") else f"https://{_self_host}"
    os.environ.setdefault("VERITAS_AGENT_URL", f"{_base}/_agent")
    os.environ.setdefault("VERITAS_ERP_WEBHOOK_URL", f"{_base}/_erp/api/erp/webhook")
    _host_only = _base.replace("https://", "").replace("http://", "").split("/")[0]
    os.environ.setdefault("VERITAS_WEBHOOK_ALLOW_HOSTS", _host_only)

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

def _ensure_migrated() -> None:
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("sqlite:////tmp/") and Path("/tmp/enterprise.db").exists():
        return
    cfg = AlembicConfig(str(ROOT / "enterprise" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "enterprise" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_command.upgrade(cfg, "head")

_ensure_migrated()

from fastapi import FastAPI
from agent_service import app as agent_app
from erp_sandbox.main import app as erp_app
from erp_sandbox.db import init_db as init_erp_db
from enterprise.main import app as enterprise_app, bootstrap

init_erp_db()
bootstrap()

app = enterprise_app
app.mount("/_agent", agent_app)
app.mount("/_erp", erp_app)
