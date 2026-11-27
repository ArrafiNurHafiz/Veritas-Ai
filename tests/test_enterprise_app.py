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
            os.environ["VERITAS_ALLOW_INSECURE_WEBHOOKS"] = "1"
            os.environ["VERITAS_WEBHOOK_ALLOW_HOSTS"] = "erp_sandbox"
            with self.assertRaises(SsrfBlockedError):
                validate_outbound_url("http://10.10.10.10:8003/api/erp/webhook")
            with self.assertRaises(SsrfBlockedError):
                validate_outbound_url("http://169.254.169.254/latest/meta-data")
        finally:
            if prev_insecure is not None:
                os.environ["VERITAS_ALLOW_INSECURE_WEBHOOKS"] = prev_insecure
            else:
                os.environ.pop("VERITAS_ALLOW_INSECURE_WEBHOOKS", None)
            os.environ.pop("VERITAS_WEBHOOK_ALLOW_HOSTS", None)

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

    def test_10_observability_correlation_and_metrics(self):
        # Correlation ID echoed back on requests
        health = self.client.get("/health/live", headers={"X-Correlation-ID": "trace-12345"})
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.headers.get("X-Correlation-ID"), "trace-12345")

        # /metrics requires valid X-Internal-Token
        denied = self.client.get("/metrics")
        self.assertEqual(denied.status_code, 401)

        token = os.environ.get("VERITAS_INTERNAL_TOKEN", "dev-internal")
        metrics = self.client.get("/metrics", headers={"X-Internal-Token": token})
        self.assertEqual(metrics.status_code, 200, metrics.text)
        self.assertIn("veritas_executions_total", metrics.text)
        self.assertIn("veritas_approvals_pending", metrics.text)
        self.assertIn("veritas_anchors_pending", metrics.text)
        self.assertIn("veritas_http_requests_total", metrics.text)

    def test_11_vendor_master_sync_and_blocked_denial(self):
        self.identity("admin-1", "admin")
        listed = self.client.get("/api/v1/vendors")
        self.assertEqual(listed.status_code, 200, listed.text)
        codes = {v["vendor_code"] for v in listed.json()["vendors"]}
        self.assertIn("V-ABC", codes)

        created = self.client.post(
            "/api/v1/vendors",
            json={"vendor_code": "V-NEW", "name": "PT Mitra Baru", "tax_id": "01.234.567.8-000.000", "status": "active"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["status"], "active")

        blocked = self.client.patch("/api/v1/vendors/V-NEW", json={"status": "blocked"})
        self.assertEqual(blocked.status_code, 200, blocked.text)
        self.assertEqual(blocked.json()["status"], "blocked")

        self.identity("op-1", "operator")
        denied = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "vendor-blocked-1"},
            json={"task_type": "invoice_review", "payload": {
                "invoice_id": "INV-BLK-1", "amount_idr": 500_000, "vendor": "V-NEW",
            }},
        )
        self.assertEqual(denied.status_code, 202, denied.text)
        self.assertEqual(denied.json()["status"], "DENIED")
        self.assertEqual(denied.json()["decision"], "DENY")
        self.assertEqual(denied.json()["reason_code"], "VENDOR_BLOCKED")

    def test_12_multicurrency_normalization(self):
        import json
        self.identity("op-1", "operator")
        res = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "fx-usd-1"},
            json={"task_type": "invoice_review", "payload": {
                "invoice_id": "INV-USD-1", "amount": 100, "currency": "USD", "vendor": "ABC",
            }},
        )
        self.assertEqual(res.status_code, 202, res.text)
        normalized = json.loads(res.json()["payload_json"])
        self.assertEqual(normalized["amount_idr"], 1_600_000)
        self.assertEqual(normalized["currency"], "USD")
        self.assertEqual(normalized["original_amount"], 100)

    def test_13_sso_and_kms_bypass_in_production(self):
        from enterprise.kms import get_signing_key, reset_signing_key_cache
        prev_env = os.environ.get("VERITAS_ENV")
        prev_sso = os.environ.get("VERITAS_SSO_BYPASS")
        prev_kms = os.environ.get("VERITAS_KMS_BYPASS")
        prev_seed = os.environ.get("VERITAS_SIGNING_SEED")
        try:
            os.environ["VERITAS_ENV"] = "production"
            os.environ["VERITAS_SSO_BYPASS"] = "1"
            os.environ["VERITAS_KMS_BYPASS"] = "1"
            os.environ.pop("VERITAS_SIGNING_SEED", None)
            reset_signing_key_cache()
            key = get_signing_key()
            self.assertEqual(key.provider, "ephemeral_bypass")
            login_res = self.client.get(
                "/api/v1/auth/test-login?role=operator&email=demo-op@veritas.local",
                follow_redirects=False,
            )
            self.assertEqual(login_res.status_code, 200, login_res.text)
            self.assertEqual(login_res.json()["roles"], ["operator"])
        finally:
            reset_signing_key_cache()
            for key, val in [
                ("VERITAS_ENV", prev_env),
                ("VERITAS_SSO_BYPASS", prev_sso),
                ("VERITAS_KMS_BYPASS", prev_kms),
                ("VERITAS_SIGNING_SEED", prev_seed),
            ]:
                if val is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = val

    def test_14_approval_email_notification_and_erp_presets(self):
        from unittest.mock import MagicMock, patch
        from enterprise.adapters import execute_erp_tool

        mock_smtp_instance = MagicMock()
        mock_smtp_cls = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp_instance

        prev_host = os.environ.get("SMTP_HOST")
        prev_from = os.environ.get("SMTP_FROM")
        try:
            os.environ["SMTP_HOST"] = "smtp.test.local"
            os.environ["SMTP_FROM"] = "veritas@test.local"
            self.identity("op-1", "operator")
            with patch("enterprise.notifications.smtplib.SMTP", mock_smtp_cls):
                res = self.client.post(
                    "/api/v1/tasks",
                    headers={"Idempotency-Key": "smtp-wait-1"},
                    json={"task_type": "invoice_review", "payload": {
                        "invoice_id": "INV-WAIT-EMAIL-1", "amount_idr": 12_000_000, "vendor": "ABC",
                    }},
                )
            self.assertEqual(res.status_code, 202, res.text)
            self.assertEqual(res.json()["status"], "WAITING_APPROVAL")
            self.assertTrue(mock_smtp_instance.send_message.called)
        finally:
            if prev_host is None:
                os.environ.pop("SMTP_HOST", None)
            else:
                os.environ["SMTP_HOST"] = prev_host
            if prev_from is None:
                os.environ.pop("SMTP_FROM", None)
            else:
                os.environ["SMTP_FROM"] = prev_from

        prev_adapter = os.environ.get("VERITAS_ERP_ADAPTER")
        try:
            os.environ["VERITAS_ERP_ADAPTER"] = "odoo"
            odoo_out = execute_erp_tool(
                execution_id="exec-1", tenant_id="tenant-a", tool_name="approve_invoice",
                arguments={"invoice_id": "INV-1", "vendor_code": "V-ABC", "amount_idr": 1000},
            )
            self.assertEqual(odoo_out["mode"], "local_ledger")
            self.assertEqual(odoo_out["adapter"], "odoo")
            self.assertEqual(odoo_out["payload"]["params"]["model"], "account.move")

            os.environ["VERITAS_ERP_ADAPTER"] = "sap"
            sap_out = execute_erp_tool(
                execution_id="exec-2", tenant_id="tenant-a", tool_name="approve_invoice",
                arguments={"invoice_id": "INV-2", "vendor_code": "V-ABC", "amount_idr": 2000},
            )
            self.assertEqual(sap_out["adapter"], "sap")
            self.assertEqual(sap_out["payload"]["DocumentType"], "RE")
        finally:
            if prev_adapter is None:
                os.environ.pop("VERITAS_ERP_ADAPTER", None)
            else:
                os.environ["VERITAS_ERP_ADAPTER"] = prev_adapter

    def test_15_multi_agent_catalog_execution_and_boundaries(self):
        self.identity("auditor-1", "auditor")
        agents_res = self.client.get("/api/v1/agents")
        self.assertEqual(agents_res.status_code, 200, agents_res.text)
        agents = agents_res.json()["agents"]
        self.assertEqual(
            [a["agent_id"] for a in agents],
            [
                "procurement-agent",
                "finance-risk-agent",
                "hr-operations-agent",
                "security-audit-agent",
            ],
        )
        self.assertTrue(all(a["status"] == "OPERATIONAL" for a in agents))

        self.identity("op-1", "operator")
        # Unknown agent is rejected cleanly
        bad_agent = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "multi-bad-agent"},
            json={"agent_id": "nonexistent-agent", "payload": {"invoice_id": "X"}},
        )
        self.assertEqual(bad_agent.status_code, 422)

        # Finance Risk Agent: auto-allowed variance + receipt binds agent_id
        fin_auto = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "multi-fin-auto"},
            json={
                "agent_id": "finance-risk-agent",
                "task_type": "ledger_reconciliation",
                "payload": {"reference_id": "REC-101", "account_code": "GL-4100", "amount_idr": 1_200_000},
            },
        )
        self.assertEqual(fin_auto.status_code, 202, fin_auto.text)
        self.assertEqual(fin_auto.json()["status"], "SUCCEEDED")
        self.assertEqual(fin_auto.json()["agent_id"], "finance-risk-agent")
        fin_receipt = self.client.get(f"/api/v1/receipts/{fin_auto.json()['receipt_id']}").json()
        self.assertEqual(fin_receipt["receipt"]["agent_id"], "finance-risk-agent")

        # HR Operations Agent: elevated -> WAITING_APPROVAL -> approver approves -> SUCCEEDED; admin -> DENIED
        hr_gate = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "multi-hr-gate"},
            json={
                "agent_id": "hr-operations-agent",
                "task_type": "workspace_provisioning",
                "payload": {"employee_id": "EMP-501", "department": "Platform", "access_tier": "elevated"},
            },
        )
        self.assertEqual(hr_gate.status_code, 202, hr_gate.text)
        self.assertEqual(hr_gate.json()["status"], "WAITING_APPROVAL")
        self.assertEqual(hr_gate.json()["tool_calls"], 0)

        hr_deny = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "multi-hr-deny"},
            json={
                "agent_id": "hr-operations-agent",
                "task_type": "workspace_provisioning",
                "payload": {"employee_id": "EMP-502", "department": "Contractor", "access_tier": "admin"},
            },
        )
        self.assertEqual(hr_deny.status_code, 202, hr_deny.text)
        self.assertEqual(hr_deny.json()["status"], "DENIED")
        self.assertEqual(hr_deny.json()["reason_code"], "ADMIN_PROVISION_RESTRICTED")

        # Security Audit Agent: staging scan -> SUCCEEDED; root revocation -> DENIED
        sec_scan = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "multi-sec-scan"},
            json={
                "agent_id": "security-audit-agent",
                "task_type": "iam_posture_scan",
                "payload": {"account_id": "AWS-STG-1", "scope": "staging"},
            },
        )
        self.assertEqual(sec_scan.status_code, 202, sec_scan.text)
        self.assertEqual(sec_scan.json()["status"], "SUCCEEDED")

        sec_deny = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "multi-sec-root"},
            json={
                "agent_id": "security-audit-agent",
                "task_type": "token_revocation",
                "payload": {
                    "principal_id": "root-breakglass",
                    "token_id": "TOK-ROOT-1",
                    "reason": "Automated sweep",
                },
            },
        )
        self.assertEqual(sec_deny.status_code, 202, sec_deny.text)
        self.assertEqual(sec_deny.json()["status"], "DENIED")
        self.assertEqual(sec_deny.json()["reason_code"], "PROTECTED_ROOT_PRINCIPAL")

        # Approver signs off the HR elevated access task
        self.identity("approver-1", "approver")
        hr_approved = self.client.post(
            f"/api/v1/approvals/{hr_gate.json()['approval_id']}/decisions",
            json={"decision": "approve", "reason": "Manager approved elevated access", "expected_version": 1},
        )
        self.assertEqual(hr_approved.status_code, 200, hr_approved.text)
        self.assertEqual(hr_approved.json()["execution"]["status"], "SUCCEEDED")

        # /api/v1/agents reports per-agent execution totals
        self.identity("auditor-1", "auditor")
        by_id = {a["agent_id"]: a for a in self.client.get("/api/v1/agents").json()["agents"]}
        self.assertGreaterEqual(by_id["finance-risk-agent"]["executions"], 1)
        self.assertGreaterEqual(by_id["hr-operations-agent"]["executions"], 2)
        self.assertGreaterEqual(by_id["security-audit-agent"]["executions"], 2)

    def test_16_cross_service_agent_and_erp_webhook_sync(self):
        import socket
        import subprocess
        import time

        def _free_port() -> int:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                return int(sock.getsockname()[1])

        agent_port = _free_port()
        erp_port = _free_port()
        erp_db = os.path.join(_TMP, "sync_erp.db")

        agent_env = {**os.environ, "VERITAS_AGENT_TOKEN": "sync-agent-tok", "VERITAS_LLM_BASE_URL": "", "OPENROUTER_API_KEY": ""}
        erp_env = {**os.environ, "ERP_SANDBOX_DB": erp_db}
        agent_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "agent_service:app", "--host", "127.0.0.1", "--port", str(agent_port), "--log-level", "error"],
            cwd=ROOT, env=agent_env,
        )
        erp_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "erp_sandbox.main:app", "--host", "127.0.0.1", "--port", str(erp_port), "--log-level", "error"],
            cwd=ROOT, env=erp_env,
        )
        prev = {k: os.environ.get(k) for k in ("VERITAS_AGENT_URL", "VERITAS_AGENT_TOKEN", "VERITAS_ERP_ADAPTER", "VERITAS_ERP_WEBHOOK_URL", "VERITAS_ALLOW_INSECURE_WEBHOOKS")}
        try:
            import httpx
            for url in (f"http://127.0.0.1:{agent_port}/health/live", f"http://127.0.0.1:{erp_port}/health/live"):
                for _ in range(50):
                    try:
                        if httpx.get(url, timeout=1.0).status_code == 200:
                            break
                    except Exception:
                        time.sleep(0.1)

            os.environ["VERITAS_AGENT_URL"] = f"http://127.0.0.1:{agent_port}"
            os.environ["VERITAS_AGENT_TOKEN"] = "sync-agent-tok"
            os.environ["VERITAS_ERP_ADAPTER"] = "webhook"
            os.environ["VERITAS_ERP_WEBHOOK_URL"] = f"http://127.0.0.1:{erp_port}/api/erp/webhook"
            os.environ["VERITAS_ALLOW_INSECURE_WEBHOOKS"] = "1"

            # 1. Auto-approved task routes through agent_service -> enterprise -> erp_sandbox
            self.identity("op-sync", "operator")
            ok_res = self.client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "sync-auto-1"},
                json={"agent_id": "procurement-agent", "task_type": "invoice_review", "payload": {
                    "invoice_id": "INV-SYNC-1", "amount_idr": 2_000_000, "vendor": "ABC",
                }},
            )
            self.assertEqual(ok_res.status_code, 202, ok_res.text)
            self.assertEqual(ok_res.json()["status"], "SUCCEEDED")
            exec_id = ok_res.json()["id"]
            detail = self.client.get(f"/api/v1/executions/{exec_id}").json()
            self.assertIn("agent_service:deterministic", json.dumps(detail["events"]))

            txs = httpx.get(f"http://127.0.0.1:{erp_port}/api/erp/transactions", timeout=5.0).json()["transactions"]
            self.assertTrue(any(t["execution_id"] == exec_id and t["status"] == "POSTED" for t in txs))

            # 2. Gated execution rejected by approver syncs REJECTED back to erp_sandbox
            gated_res = self.client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "sync-gate-reject"},
                json={"agent_id": "procurement-agent", "task_type": "invoice_review", "payload": {
                    "invoice_id": "INV-SYNC-REJ", "amount_idr": 9_500_000, "vendor": "ABC",
                }},
            )
            self.assertEqual(gated_res.status_code, 202, gated_res.text)
            gate_exec_id = gated_res.json()["id"]
            gate_aprv_id = gated_res.json()["approval_id"]
            httpx.post(
                f"http://127.0.0.1:{erp_port}/api/erp/webhook",
                headers={"Idempotency-Key": f"pre-{gate_exec_id}"},
                json={"execution_id": gate_exec_id, "tenant_id": "tenant-a", "tool": "approve_invoice", "status": "POSTED", "arguments": {"invoice_id": "INV-SYNC-REJ", "vendor_id": "V-ABC", "amount_idr": 9_500_000}},
                timeout=5.0,
            )
            self.identity("approver-sync", "approver")
            rej_res = self.client.post(
                f"/api/v1/approvals/{gate_aprv_id}/decisions",
                json={"decision": "reject", "reason": "Over Q4 cap", "expected_version": 1},
            )
            self.assertEqual(rej_res.status_code, 200, rej_res.text)
            txs_after = httpx.get(f"http://127.0.0.1:{erp_port}/api/erp/transactions", timeout=5.0).json()["transactions"]
            self.assertTrue(any(t["execution_id"] == gate_exec_id and t["status"] == "REJECTED" for t in txs_after))
            self.identity("op-sync", "operator")

            # 3. Stop agent_service -> enterprise fails closed with AGENT_UNAVAILABLE
            agent_proc.terminate()
            agent_proc.wait(timeout=10)
            down_res = self.client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "sync-down-1"},
                json={"agent_id": "procurement-agent", "task_type": "invoice_review", "payload": {
                    "invoice_id": "INV-SYNC-DOWN", "amount_idr": 1_000_000, "vendor": "ABC",
                }},
            )
            self.assertEqual(down_res.status_code, 202, down_res.text)
            self.assertEqual(down_res.json()["status"], "DENIED")
            self.assertEqual(down_res.json()["reason_code"], "AGENT_UNAVAILABLE")
            self.assertEqual(down_res.json()["tool_calls"], 0)
        finally:
            for k, val in prev.items():
                if val is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = val
            for proc in (agent_proc, erp_proc):
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=10)

    def test_17_approval_expiry_and_resume_revalidation(self):
        from enterprise.config import session_scope
        from enterprise.models import Approval

        # 1. Expired pending approval transitions cleanly to EXPIRED (409 on decide, 0 tool calls)
        exp = self.submit("INV-EXP-1", 9_500_000)
        self.assertEqual(exp["status"], "WAITING_APPROVAL")
        exp_exec_id = exp["id"]
        exp_aprv_id = exp["approval_id"]
        with session_scope() as session:
            row = session.get(Approval, exp_aprv_id)
            self.assertIsNotNone(row)
            row.expires_at = "2020-01-01T00:00:00Z"

        self.identity("approver-exp", "approver")
        dec_exp = self.client.post(
            f"/api/v1/approvals/{exp_aprv_id}/decisions",
            json={"decision": "approve", "expected_version": 1},
        )
        self.assertEqual(dec_exp.status_code, 409, dec_exp.text)
        self.assertEqual(dec_exp.json()["error"]["code"], "APPROVAL_EXPIRED")

        exec_view = self.client.get(f"/api/v1/executions/{exp_exec_id}").json()
        self.assertEqual(exec_view["status"], "EXPIRED")
        self.assertEqual(exec_view["decision"], "DENY")
        self.assertEqual(exec_view["reason_code"], "APPROVAL_EXPIRED")
        self.assertEqual(exec_view["tool_calls"], 0)
        self.assertTrue(any(ev["type"] == "APPROVAL_EXPIRED" for ev in exec_view["events"]))

        self.identity("auditor-exp", "auditor")
        approvals = self.client.get("/api/v1/approvals").json()
        self.assertFalse(any(a["id"] == exp_aprv_id for a in approvals))
        with session_scope() as session:
            refreshed = session.get(Approval, exp_aprv_id)
            self.assertIsNotNone(refreshed)
            self.assertEqual(refreshed.status, "expired")
        audit = self.client.get("/api/v1/audit-events?verify=true").json()
        self.assertTrue(audit["chain"]["ok"])
        self.assertTrue(any(ev["action"] == "approval.expired" and ev["target_id"] == exp_aprv_id for ev in audit["events"]))

        # 2. Policy version change after approval request denies on resume (POLICY_CHANGED)
        pol_exec = self.submit("INV-POL-CHG", 9_500_000)
        self.assertEqual(pol_exec["status"], "WAITING_APPROVAL")
        pol_aprv_id = pol_exec["approval_id"]

        self.identity("admin-reval", "admin")
        pol_src = self.client.get("/api/v1/policies").json()["source"]
        new_limit = pol_src["auto_approve_limit_idr"] - 1000 if pol_src["auto_approve_limit_idr"] > 2000 else pol_src["auto_approve_limit_idr"] + 1000
        pol_put = self.client.put(
            "/api/v1/policies",
            json={
                "auto_approve_limit_idr": new_limit,
                "hard_cap_idr": pol_src["hard_cap_idr"],
                "vendors": pol_src["vendors"],
            },
        )
        self.assertEqual(pol_put.status_code, 200, pol_put.text)

        self.identity("approver-reval", "approver")
        res_pol = self.client.post(
            f"/api/v1/approvals/{pol_aprv_id}/decisions",
            json={"decision": "approve", "expected_version": 1},
        )
        self.assertEqual(res_pol.status_code, 200, res_pol.text)
        body_pol = res_pol.json()
        self.assertEqual(body_pol["approval"]["status"], "rejected")
        self.assertEqual(body_pol["execution"]["status"], "DENIED")
        self.assertEqual(body_pol["execution"]["reason_code"], "POLICY_CHANGED")
        self.assertEqual(body_pol["execution"]["tool_calls"], 0)

        # 3. Disabling tool before approval decision denies on resume (TOOL_NOT_ALLOWED_FOR_TENANT)
        tool_exec = self.submit("INV-TOOL-OFF", 9_500_000)
        self.assertEqual(tool_exec["status"], "WAITING_APPROVAL")
        tool_aprv_id = tool_exec["approval_id"]

        try:
            self.identity("admin-reval", "admin")
            dis = self.client.patch("/api/v1/tools/approve_invoice", json={"enabled": False})
            self.assertEqual(dis.status_code, 200, dis.text)

            self.identity("approver-reval", "approver")
            res_tool = self.client.post(
                f"/api/v1/approvals/{tool_aprv_id}/decisions",
                json={"decision": "approve", "expected_version": 1},
            )
            self.assertEqual(res_tool.status_code, 200, res_tool.text)
            body_tool = res_tool.json()
            self.assertEqual(body_tool["approval"]["status"], "rejected")
            self.assertEqual(body_tool["execution"]["status"], "DENIED")
            self.assertEqual(body_tool["execution"]["reason_code"], "TOOL_NOT_ALLOWED_FOR_TENANT")
            self.assertEqual(body_tool["execution"]["tool_calls"], 0)
        finally:
            self.identity("admin-reval", "admin")
            self.client.patch("/api/v1/tools/approve_invoice", json={"enabled": True})

    def test_18_agent_toggle_tenant_onboarding_and_metrics_pending(self):
        from enterprise.config import session_scope
        from enterprise.main import sweep_all_expired_approvals
        from enterprise.models import Approval

        # 1. Pending approval increments veritas_approvals_pending metric (>0) and background sweep clears it
        gated = self.submit("INV-METRIC-1", 9_500_000)
        self.assertEqual(gated["status"], "WAITING_APPROVAL")
        aprv_id = gated["approval_id"]
        token = os.environ.get("VERITAS_INTERNAL_TOKEN", "dev-internal")
        metrics_res = self.client.get("/metrics", headers={"X-Internal-Token": token})
        self.assertEqual(metrics_res.status_code, 200)
        self.assertRegex(metrics_res.text, r"veritas_approvals_pending [1-9]\d*")

        with session_scope() as session:
            ap = session.get(Approval, aprv_id)
            self.assertIsNotNone(ap)
            ap.expires_at = "2020-01-01T00:00:00Z"
        self.assertGreaterEqual(sweep_all_expired_approvals(), 1)
        expired_exec = self.client.get(f"/api/v1/executions/{gated['id']}").json()
        self.assertEqual(expired_exec["status"], "EXPIRED")

        # 2. Admin can toggle an agent off; pending approval & new tasks fail closed with AGENT_DISABLED
        held = self.submit("INV-AG-OFF", 9_500_000)
        self.assertEqual(held["status"], "WAITING_APPROVAL")
        held_aprv_id = held["approval_id"]

        self.identity("op-check", "operator")
        self.assertEqual(
            self.client.patch("/api/v1/agents/procurement-agent", json={"enabled": False}).status_code,
            403,
        )

        self.identity("admin-1", "admin")
        try:
            self.assertEqual(
                self.client.patch("/api/v1/agents/nonexistent-agent", json={"enabled": False}).status_code,
                404,
            )
            off = self.client.patch("/api/v1/agents/procurement-agent", json={"enabled": False})
            self.assertEqual(off.status_code, 200, off.text)
            self.assertEqual(off.json()["status"], "DISABLED")
            self.assertFalse(off.json()["enabled"])

            agents_view = self.client.get("/api/v1/agents").json()["agents"]
            proc = next(a for a in agents_view if a["agent_id"] == "procurement-agent")
            self.assertEqual(proc["status"], "DISABLED")

            # New task on disabled agent fails closed before planner invocation
            blocked = self.submit("INV-AG-BLOCKED", 1_000_000)
            self.assertEqual(blocked["status"], "DENIED")
            self.assertEqual(blocked["reason_code"], "AGENT_DISABLED")
            self.assertEqual(blocked["tool_calls"], 0)

            # Resuming held approval on disabled agent fails closed on resume
            self.identity("approver-1", "approver")
            resumed = self.client.post(
                f"/api/v1/approvals/{held_aprv_id}/decisions",
                json={"decision": "approve", "expected_version": 1},
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            self.assertEqual(resumed.json()["execution"]["status"], "DENIED")
            self.assertEqual(resumed.json()["execution"]["reason_code"], "AGENT_DISABLED")
            self.assertEqual(resumed.json()["execution"]["tool_calls"], 0)
        finally:
            self.identity("admin-1", "admin")
            on = self.client.patch("/api/v1/agents/procurement-agent", json={"enabled": True})
            self.assertEqual(on.status_code, 200, on.text)

        # 3. Admin tenant onboarding creates an isolated seeded tenant; duplicates rejected with 409
        self.identity("op-1", "operator")
        self.assertEqual(
            self.client.post("/api/v1/tenants", json={"id": "acme-demo", "name": "ACME Corp"}).status_code,
            403,
        )
        self.identity("admin-1", "admin")
        created = self.client.post(
            "/api/v1/tenants",
            json={"id": "acme-demo", "name": "ACME Corp"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertTrue(created.json()["seeded"])

        dup = self.client.post("/api/v1/tenants", json={"id": "acme-demo", "name": "ACME Corp"})
        self.assertEqual(dup.status_code, 409, dup.text)

        # New tenant can immediately serve policy, tools, agents, and task execution
        self.identity("op-acme", "operator", tenant_id="acme-demo")
        self.assertEqual(self.client.get("/api/v1/policies").status_code, 200)
        self.assertEqual(len(self.client.get("/api/v1/agents").json()["agents"]), 4)
        acme_exec = self.client.post(
            "/api/v1/tasks",
            headers={"Idempotency-Key": "acme-task-1"},
            json={"agent_id": "hr-operations-agent", "task_type": "badge_request", "payload": {"employee_id": "E-1", "zone": "office"}},
        )
        self.assertEqual(acme_exec.status_code, 202, acme_exec.text)
        self.assertEqual(acme_exec.json()["status"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
