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
        self.client.cookies.clear()
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

    def test_06_password_auth_users_and_production_guards(self):
        from enterprise.passwords import hash_password, verify_password

        encoded = hash_password("S3cur3P@ssword!")
        self.assertTrue(encoded.startswith("scrypt$"))
        self.assertTrue(verify_password("S3cur3P@ssword!", encoded))
        self.assertFalse(verify_password("wrong-pass", encoded))

        # Admin creates an operator user
        self.identity("admin-1", "admin")
        created = self.client.post(
            "/api/v1/users",
            json={
                "email": "operator.real@company.com",
                "display_name": "Real Operator",
                "role": "operator",
                "password": "StrongPassword123!",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        user_id = created.json()["user_id"]

        listed = self.client.get("/api/v1/users")
        self.assertEqual(listed.status_code, 200, listed.text)
        users = listed.json()["users"]
        self.assertTrue(any(u["email"] == "operator.real@company.com" for u in users))
        self.assertFalse(any("password_hash" in u for u in users))

        # Non-admin cannot list or create users
        self.identity("op-1", "operator")
        self.assertEqual(self.client.get("/api/v1/users").status_code, 403)

        # Admin updates user role
        self.identity("admin-1", "admin")
        patched = self.client.patch(
            f"/api/v1/users/{user_id}/role",
            json={"role": "approver", "status": "active"},
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        self.assertEqual(patched.json()["role"], "approver")

        # Real password login creates an authenticated session cookie + CSRF token
        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "operator.real@company.com", "password": "StrongPassword123!"},
        )
        self.assertEqual(login_res.status_code, 200, login_res.text)
        self.assertEqual(login_res.json()["role"], "approver")
        self.assertTrue(login_res.json()["csrf_token"])

        # Wrong password fails with 401 and triggers rate limit after 5 attempts
        for _ in range(5):
            bad = self.client.post(
                "/api/v1/auth/login",
                json={"email": "operator.real@company.com", "password": "WrongPassword!"},
            )
            self.assertEqual(bad.status_code, 401)
        limited = self.client.post(
            "/api/v1/auth/login",
            json={"email": "operator.real@company.com", "password": "StrongPassword123!"},
        )
        self.assertEqual(limited.status_code, 429)

        # Production guard disables test-login even if VERITAS_AUTH_TEST_MODE=true
        prev_env = os.environ.get("VERITAS_ENV")
        os.environ["VERITAS_ENV"] = "production"
        try:
            blocked_test_login = self.client.get("/api/v1/auth/test-login?role=admin")
            self.assertEqual(blocked_test_login.status_code, 404)
        finally:
            if prev_env is None:
                os.environ.pop("VERITAS_ENV", None)
            else:
                os.environ["VERITAS_ENV"] = prev_env

    def test_07_tool_registry_and_persistent_policy(self):
        self.identity("admin-1", "admin")
        tools_res = self.client.get("/api/v1/tools")
        self.assertEqual(tools_res.status_code, 200, tools_res.text)
        tool_names = {t["tool_name"] for t in tools_res.json()["tools"]}
        self.assertIn("approve_invoice", tool_names)
        self.assertIn("check_vendor_status", tool_names)

        # Toggle check_vendor_status off and verify /api/v1/agents updates dynamically
        toggled = self.client.patch(
            "/api/v1/tools/check_vendor_status",
            json={"enabled": False},
        )
        self.assertEqual(toggled.status_code, 200, toggled.text)
        self.assertFalse(toggled.json()["enabled"])

        agents_res = self.client.get("/api/v1/agents").json()
        self.assertNotIn("check_vendor_status", agents_res["agents"][0]["allowed_tools"])

        # Non-admin cannot toggle tools
        self.identity("op-1", "operator")
        self.assertEqual(
            self.client.patch("/api/v1/tools/check_vendor_status", json={"enabled": True}).status_code,
            403,
        )

        # Re-enable as admin and bump policy version
        self.identity("admin-1", "admin")
        self.assertEqual(
            self.client.patch("/api/v1/tools/check_vendor_status", json={"enabled": True}).status_code,
            200,
        )
        pol = self.client.put(
            "/api/v1/policies",
            json={"auto_approve_limit_idr": 6_000_000, "vendors": ["V-ABC", "V-XYZ", "V-NEW"]},
        )
        self.assertEqual(pol.status_code, 200, pol.text)
        self.assertGreaterEqual(pol.json()["version"], 2)
        self.assertEqual(pol.json()["source"]["auto_approve_limit_idr"], 6_000_000)

    def test_08_ssrf_guard_webhook_egress_and_erp_adapter(self):
        import http.server
        import threading
        from enterprise.adapters import SsrfBlockedError, sign_webhook_payload, validate_outbound_url

        # SSRF blocks non-HTTPS, loopback, and cloud metadata IPs
        prev_insecure = os.environ.pop("VERITAS_ALLOW_INSECURE_WEBHOOKS", None)
        try:
            with self.assertRaises(SsrfBlockedError):
                validate_outbound_url("http://example.com/hook")
            with self.assertRaises(SsrfBlockedError):
                validate_outbound_url("https://169.254.169.254/latest/meta-data")
            with self.assertRaises(SsrfBlockedError):
                validate_outbound_url("https://127.0.0.1:8100/hook")
        finally:
            if prev_insecure is not None:
                os.environ["VERITAS_ALLOW_INSECURE_WEBHOOKS"] = prev_insecure

        received: list[dict] = []

        class _HookHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                received.append({
                    "path": self.path,
                    "body": body,
                    "sig": self.headers.get("X-Veritas-Signature", ""),
                    "idemp": self.headers.get("Idempotency-Key", ""),
                })
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *_args):
                return

        server = http.server.HTTPServer(("127.0.0.1", 0), _HookHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        hook_url = f"http://127.0.0.1:{server.server_port}/webhook"

        self.identity("op-1", "operator")
        try:
            # 1. Sensitive field blocked before any network call
            blocked = self.client.post(
                "/api/v1/egress/send",
                headers={"Idempotency-Key": "egress-sens-1"},
                json={"destination": "mock://crm", "payload": {"customer": "Acme", "api_key": "secret"}},
            )
            self.assertEqual(blocked.status_code, 403, blocked.text)
            self.assertEqual(blocked.json()["reason_code"], "SENSITIVE_FIELD")
            self.assertEqual(len(received), 0)

            # 2. Unlisted destination blocked
            unlisted = self.client.post(
                "/api/v1/egress/send",
                headers={"Idempotency-Key": "egress-off-1"},
                json={"destination": "https://evil.example/drop", "payload": {"ok": True}},
            )
            self.assertEqual(unlisted.status_code, 403)
            self.assertEqual(unlisted.json()["reason_code"], "DESTINATION_NOT_ALLOWED")

            # 3. Allowlisted webhook receives HMAC-signed payload; replay does not duplicate
            os.environ["VERITAS_ALLOW_INSECURE_WEBHOOKS"] = "1"
            os.environ["VERITAS_EGRESS_DESTINATIONS"] = hook_url
            os.environ["VERITAS_EGRESS_HMAC_SECRET"] = "test-hmac-secret"
            ok = self.client.post(
                "/api/v1/egress/send",
                headers={"Idempotency-Key": "egress-hook-1"},
                json={"destination": hook_url, "payload": {"invoice_id": "INV-9", "status": "ok"}},
            )
            self.assertEqual(ok.status_code, 200, ok.text)
            self.assertEqual(ok.json()["delivery_status"], "DELIVERED")
            self.assertEqual(len(received), 1)
            expected_sig = "sha256=" + sign_webhook_payload(received[0]["body"], "test-hmac-secret")
            self.assertEqual(received[0]["sig"], expected_sig)

            replay = self.client.post(
                "/api/v1/egress/send",
                headers={"Idempotency-Key": "egress-hook-1"},
                json={"destination": hook_url, "payload": {"invoice_id": "INV-9", "status": "ok"}},
            )
            self.assertEqual(replay.status_code, 200)
            self.assertTrue(replay.json()["replayed"])
            self.assertEqual(len(received), 1)

            # 4. ERP tool adapter executes real HTTP POST on auto-approved task
            os.environ["VERITAS_ERP_WEBHOOK_URL"] = hook_url
            os.environ["VERITAS_ERP_HMAC_SECRET"] = "erp-secret"
            task_res = self.client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "erp-task-1"},
                json={"task_type": "invoice_review", "payload": {
                    "invoice_id": "INV-ERP-1", "amount_idr": 1_000_000, "vendor": "ABC",
                }},
            )
            self.assertEqual(task_res.status_code, 202, task_res.text)
            self.assertEqual(task_res.json()["status"], "SUCCEEDED")
            self.assertEqual(len(received), 2)
        finally:
            server.shutdown()
            server.server_close()
            for key in ("VERITAS_ALLOW_INSECURE_WEBHOOKS", "VERITAS_EGRESS_DESTINATIONS",
                        "VERITAS_EGRESS_HMAC_SECRET", "VERITAS_ERP_WEBHOOK_URL", "VERITAS_ERP_HMAC_SECRET"):
                os.environ.pop(key, None)

    def test_09_evm_anchor_outbox_and_sweep(self):
        import http.server
        import threading

        txs: dict[str, dict] = {}

        class _RpcHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                req = json.loads(self.rfile.read(length))
                method = req.get("method")
                params = req.get("params", [])
                if method == "eth_sendTransaction":
                    tx_hash = "0x" + "ab" * 32
                    txs[tx_hash] = {"blockNumber": "0x1", "input": params[0]["data"]}
                    result = tx_hash
                elif method == "eth_getTransactionByHash":
                    result = txs.get(params[0])
                else:
                    result = None
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"jsonrpc": "2.0", "id": req.get("id"), "result": result}).encode())

            def log_message(self, *_args):
                return

        # 1. Simulate RPC outage (unreachable port) -> receipt stays durable, anchor pending
        os.environ["VERITAS_ANCHOR_RPC_URL"] = "http://127.0.0.1:1"
        os.environ["VERITAS_ANCHOR_FROM"] = "0x" + "11" * 20
        self.identity("op-1", "operator")
        try:
            task_res = self.client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "chain-outage-1"},
                json={"task_type": "invoice_review", "payload": {
                    "invoice_id": "INV-CHAIN-1", "amount_idr": 1_000_000, "vendor": "ABC",
                }},
            )
            self.assertEqual(task_res.status_code, 202, task_res.text)
            receipt_id = task_res.json()["receipt_id"]
            self.assertTrue(receipt_id)

            receipt = self.client.get(f"/api/v1/receipts/{receipt_id}").json()
            self.assertEqual(receipt["anchor"]["status"], "pending")
            self.assertTrue(receipt["anchor"]["last_error"])

            # Manual mock confirm is disabled in RPC mode
            self.identity("admin-1", "admin")
            manual = self.client.post(f"/api/v1/anchors/{receipt['anchor']['id']}/confirm")
            self.assertEqual(manual.status_code, 409, manual.text)

            # 2. Bring up mock EVM node and run outbox sweep -> anchor confirmed & verified
            server = http.server.HTTPServer(("127.0.0.1", 0), _RpcHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                os.environ["VERITAS_ANCHOR_RPC_URL"] = f"http://127.0.0.1:{server.server_port}"
                sweep = self.client.post("/api/v1/anchors/sweep")
                self.assertEqual(sweep.status_code, 200, sweep.text)
                self.assertGreaterEqual(sweep.json()["confirmed"], 1)

                verified = self.client.post(f"/api/v1/receipts/{receipt_id}/verify").json()
                self.assertTrue(verified["verified"], verified)
                self.assertEqual(verified["anchor_status"], "confirmed")
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.environ.pop("VERITAS_ANCHOR_RPC_URL", None)
            os.environ.pop("VERITAS_ANCHOR_FROM", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
