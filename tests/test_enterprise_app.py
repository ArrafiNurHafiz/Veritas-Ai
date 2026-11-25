"""End-to-end checks for the enterprise FastAPI app. No external provider calls."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="veritas-enterprise-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/enterprise.db"
os.environ["VERITAS_BOOTSTRAP_TENANT_ID"] = "tenant-a"
os.environ["VERITAS_BOOTSTRAP_TENANT_NAME"] = "Tenant A"
os.environ["VERITAS_SIGNING_SEED"] = "11" * 32
os.environ["VERITAS_AUTH_TEST_MODE"] = "true"
os.environ["VERITAS_SESSION_STORE"] = "memory"
os.environ["VERITAS_LLM_BASE_URL"] = ""
os.environ["VERITAS_COOKIE_SECURE"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from enterprise.config import init_db  # noqa: E402
from enterprise.main import app  # noqa: E402


class EnterpriseAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def identity(self, user_id: str, role: str, tenant_id: str = "tenant-a") -> None:
        os.environ["VERITAS_TEST_IDENTITY_JSON"] = json.dumps(
            {"user_id": user_id, "tenant_id": tenant_id, "roles": [role], "email": f"{user_id}@test.local"}
        )
        self.client.cookies.set("vt_csrf", "csrf-test")
        self.client.headers.update({"X-CSRF-Token": "csrf-test"})

    def submit(self, invoice_id: str, amount: int, vendor: str = "ABC") -> dict:
        self.identity("operator-1", "operator")
        response = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": f"key-{invoice_id}"},
            json={"task_type": "invoice_review", "payload": {
                "invoice_id": invoice_id, "amount_idr": amount, "vendor": vendor,
            }},
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_01_auto_execution_and_receipt(self):
        result = self.submit("INV-AUTO-1", 3_200_000)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["tool_calls"], 1)
        receipt_id = result["receipt_id"]
        self.assertTrue(receipt_id)

        self.identity("auditor-1", "auditor")
        receipt = self.client.get(f"/api/v1/receipts/{receipt_id}").json()
        self.assertTrue(receipt["digest"])
        self.assertTrue(receipt["signature"])

        verify = self.client.post(f"/api/v1/receipts/{receipt_id}/verify").json()
        self.assertTrue(verify["hash_matches"])
        self.assertTrue(verify["signature_valid"])
        self.assertTrue(verify["trusted_key"])
        self.assertFalse(verify["verified"])  # mock anchor still pending

        self.identity("admin-1", "admin")
        anchor_id = receipt["anchor"]["id"]
        confirmed = self.client.post(f"/api/v1/anchors/{anchor_id}/confirm")
        self.assertEqual(confirmed.status_code, 200, confirmed.text)

        self.identity("auditor-1", "auditor")
        verify = self.client.post(f"/api/v1/receipts/{receipt_id}/verify").json()
        self.assertTrue(verify["verified"])

    def test_02_approval_gate_and_separation_of_duties(self):
        result = self.submit("INV-GATE-1", 8_500_000)
        self.assertEqual(result["status"], "WAITING_APPROVAL")
        self.assertEqual(result["tool_calls"], 0)
        approval_id = result["approval_id"]

        self.identity("operator-1", "operator")
        denied = self.client.post(
            f"/api/v1/approvals/{approval_id}/decisions",
            json={"decision": "approve", "reason": "self", "expected_version": 1},
        )
        self.assertEqual(denied.status_code, 403, denied.text)

        self.identity("approver-1", "approver")
        approved = self.client.post(
            f"/api/v1/approvals/{approval_id}/decisions",
            json={"decision": "approve", "reason": "Verified against purchase order", "expected_version": 1},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertTrue(approved.json()["execution"]["receipt_id"])

        stale = self.client.post(
            f"/api/v1/approvals/{approval_id}/decisions",
            json={"decision": "approve", "reason": "again", "expected_version": 1},
        )
        self.assertEqual(stale.status_code, 409, stale.text)

    def test_03_rbac_and_tenant_isolation(self):
        self.identity("auditor-2", "auditor")
        denied = self.client.post(
            "/api/v1/tasks",
            json={"task_type": "invoice_review", "payload": {
                "invoice_id": "INV-AUDITOR", "amount_idr": 1000, "vendor": "ABC",
            }},
        )
        self.assertEqual(denied.status_code, 403, denied.text)

        self.identity("intruder", "admin", tenant_id="tenant-b")
        executions = self.client.get("/api/v1/executions").json()
        self.assertEqual(executions["total"], 0)

    def test_04_audit_chain(self):
        self.identity("auditor-1", "auditor")
        result = self.client.get("/api/v1/audit-events?verify=true").json()
        self.assertTrue(result["chain"]["ok"], result["chain"])
        self.assertGreater(result["chain"]["count"], 0)

    def test_05_agents_and_verify_supplied(self):
        self.identity("auditor-1", "auditor")
        agents_res = self.client.get("/api/v1/agents")
        self.assertEqual(agents_res.status_code, 200, agents_res.text)
        agents = agents_res.json()["agents"]
        self.assertEqual(agents[0]["agent_id"], "procurement-agent")
        self.assertGreater(agents[0]["executions"], 0)

        exec_id = self.client.get("/api/v1/executions").json()["executions"][0]["id"]
        exec_detail = self.client.get(f"/api/v1/executions/{exec_id}").json()
        receipt_id = exec_detail["receipt_id"]
        receipt_res = self.client.get(f"/api/v1/receipts/{receipt_id}").json()

        valid_res = self.client.post(
            "/api/v1/verify",
            json={
                **receipt_res["receipt"],
                "signature": receipt_res["signature"],
                "key_id": receipt_res["key_id"],
            },
        )
        self.assertEqual(valid_res.status_code, 200, valid_res.text)
        self.assertTrue(valid_res.json()["signature_valid"])
        self.assertTrue(valid_res.json()["hash_matches"])

        tampered_receipt = dict(receipt_res["receipt"])
        tampered_receipt["agent_id"] = "procurement-agent-TAMPERED"
        tampered_res = self.client.post(
            "/api/v1/verify",
            json={
                **tampered_receipt,
                "signature": receipt_res["signature"],
                "key_id": receipt_res["key_id"],
            },
        )
        self.assertEqual(tampered_res.status_code, 200)
        self.assertFalse(tampered_res.json()["signature_valid"])
        self.assertFalse(tampered_res.json()["hash_matches"])
        self.assertFalse(tampered_res.json()["verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
