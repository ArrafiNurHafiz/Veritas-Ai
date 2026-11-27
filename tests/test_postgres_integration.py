"""PostgreSQL 16 integration smoke test (enabled when VERITAS_PG_TEST_URL is set)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PG_URL = os.environ.get("VERITAS_PG_TEST_URL", "").strip()


@unittest.skipUnless(PG_URL, "VERITAS_PG_TEST_URL is not set; skipping live Postgres integration test")
class PostgresIntegrationTests(unittest.TestCase):
    def test_alembic_schema_api_and_append_only_trigger(self):
        os.environ["DATABASE_URL"] = PG_URL
        os.environ["VERITAS_BOOTSTRAP_TENANT_ID"] = "pg-tenant-a"
        os.environ["VERITAS_BOOTSTRAP_TENANT_NAME"] = "PG Tenant A"
        os.environ["VERITAS_SIGNING_SEED"] = "33" * 32
        os.environ["VERITAS_AUTH_TEST_MODE"] = "true"
        os.environ["VERITAS_SESSION_STORE"] = "postgres"
        os.environ["VERITAS_LLM_BASE_URL"] = ""
        os.environ["VERITAS_COOKIE_SECURE"] = "0"

        from fastapi.testclient import TestClient
        import json
        from sqlalchemy import text

        from enterprise.config import get_engine, reset_engine, session_scope
        from enterprise.main import app

        reset_engine()
        with TestClient(app) as client:
            client.cookies.set("vt_csrf", "csrf-pg")
            client.headers.update({"X-CSRF-Token": "csrf-pg"})
            os.environ["VERITAS_TEST_IDENTITY_JSON"] = json.dumps(
                {"user_id": "pg-op", "tenant_id": "pg-tenant-a", "roles": ["operator"]}
            )
            res = client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "pg-auto-1"},
                json={"task_type": "invoice_review", "payload": {"invoice_id": "INV-PG-1", "amount_idr": 1_000_000, "vendor": "ABC"}},
            )
            self.assertEqual(res.status_code, 202, res.text)
            body = res.json()
            self.assertEqual(body["status"], "SUCCEEDED")
            self.assertTrue(body["receipt_id"])

            os.environ["VERITAS_TEST_IDENTITY_JSON"] = json.dumps(
                {"user_id": "pg-auditor", "tenant_id": "pg-tenant-a", "roles": ["auditor"]}
            )
            audit = client.get("/api/v1/audit-events?verify=true").json()
            self.assertTrue(audit["chain"]["ok"])

        with session_scope() as session:
            with self.assertRaises(Exception):
                session.execute(text("UPDATE audit_events SET action = 'tampered' WHERE seq = 1"))
        get_engine().dispose()


if __name__ == "__main__":
    unittest.main(verbosity=2)
