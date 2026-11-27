"""Tests for the standalone ERP Sandbox service (erp_sandbox/)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from erp_sandbox.db import init_db
from erp_sandbox.main import app


class ErpSandboxTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        os.environ["ERP_SANDBOX_DB"] = self._tmp.name
        init_db(self._tmp.name)
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("ERP_SANDBOX_DB", None)
        os.environ.pop("ERP_SANDBOX_HMAC_SECRET", None)
        os.environ.pop("ERP_SANDBOX_API_KEY", None)
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_seed_transactions_and_console_html(self):
        res = self.client.get("/api/erp/transactions")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_count"], 3)
        self.assertEqual(data["total_posted_idr"], 23_250_000)

        html_res = self.client.get("/")
        self.assertEqual(html_res.status_code, 200)
        self.assertIn("ERP-JRN-2026-0001", html_res.text)

    def test_webhook_hmac_idempotency_and_reverse(self):
        os.environ["ERP_SANDBOX_HMAC_SECRET"] = "test-erp-hmac"
        os.environ["ERP_SANDBOX_API_KEY"] = "test-erp-key"
        payload = {
            "execution_id": "exec_test_100",
            "tenant_id": "tenant-a",
            "tool": "approve_invoice",
            "arguments": {
                "invoice_id": "INV-LIVE-999",
                "vendor_id": "V-ABC",
                "amount_idr": 1_500_000,
                "currency": "IDR",
                "description": "Cloud GPU cluster",
            },
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        sig = hmac.new(b"test-erp-hmac", raw, hashlib.sha256).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-erp-key",
            "Idempotency-Key": "tool-exec_test_100",
            "X-Veritas-Signature": f"sha256={sig}",
            "X-Veritas-ERP-Adapter": "webhook",
        }
        first = self.client.post("/api/erp/webhook", content=raw, headers=headers)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["idempotent_replay"])
        self.assertEqual(first.json()["journal_number"], "ERP-JRN-2026-0004")

        replay = self.client.post("/api/erp/webhook", content=raw, headers=headers)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["idempotent_replay"])

        tx_id = first.json()["transaction_id"]
        rev = self.client.post(f"/api/erp/transactions/{tx_id}/reverse")
        self.assertEqual(rev.status_code, 200)
        self.assertEqual(rev.json()["status"], "REVERSED")

    def test_odoo_and_sap_payload_mapping(self):
        odoo_res = self.client.post(
            "/api/erp/webhook",
            headers={"Idempotency-Key": "odoo-1", "X-Veritas-ERP-Adapter": "odoo"},
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "account.move",
                    "veritas_execution_id": "exec-odoo-1",
                    "tenant_id": "tenant-a",
                    "tool": "approve_invoice",
                    "vals": {"ref": "INV-ODOO-1", "partner_code": "V-XYZ", "amount_total": 750_000, "currency": "IDR"},
                },
            },
        )
        self.assertEqual(odoo_res.status_code, 200, odoo_res.text)
        self.assertEqual(odoo_res.json()["amount_idr"], 750_000)

        sap_res = self.client.post(
            "/api/erp/webhook",
            headers={"Idempotency-Key": "sap-1", "X-Veritas-ERP-Adapter": "sap"},
            json={
                "DocumentType": "RE",
                "CompanyCode": "tenant-a",
                "ReferenceDocument": "INV-SAP-1",
                "VendorAccount": "V-ABC",
                "AmountInTransactionCurrency": 900_000,
                "Currency": "IDR",
                "VeritasExecutionId": "exec-sap-1",
                "Tool": "approve_invoice",
            },
        )
        self.assertEqual(sap_res.status_code, 200, sap_res.text)
        self.assertEqual(sap_res.json()["amount_idr"], 900_000)

    def test_submit_to_veritas_and_webhook_status_promotion(self):
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.cookies = {"veritas_csrf": "csrf-tok-1"}
        mock_client.get.return_value = MagicMock(status_code=200, text="{}")
        mock_client.post.return_value = MagicMock(
            status_code=202,
            json=lambda: {
                "id": "exec_erp_wait_1",
                "tenant_id": "default",
                "status": "WAITING_APPROVAL",
                "decision": "REQUIRE_APPROVAL",
                "reason_code": "AMOUNT_LIMIT",
                "approval_id": "aprv_123",
                "payload_json": json.dumps({"amount_idr": 12_000_000}),
            },
        )
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_client

        with patch("erp_sandbox.main.httpx.Client", return_value=mock_cm):
            sub_res = self.client.post(
                "/api/erp/submit-to-veritas",
                json={
                    "invoice_id": "INV-ERP-WAIT-1",
                    "vendor_code": "ABC",
                    "amount": 12_000_000,
                    "currency": "IDR",
                    "description": "Server rack from ERP",
                },
            )
        self.assertEqual(sub_res.status_code, 200, sub_res.text)
        self.assertEqual(sub_res.json()["transaction"]["status"], "WAITING_APPROVAL")

        # When VERITAS later approves and posts webhook with the same execution_id,
        # the existing ERP row promotes to POSTED without duplication.
        wh_res = self.client.post(
            "/api/erp/webhook",
            headers={"Idempotency-Key": "tool-exec_erp_wait_1"},
            json={
                "execution_id": "exec_erp_wait_1",
                "tenant_id": "default",
                "tool": "approve_invoice",
                "arguments": {
                    "invoice_id": "INV-ERP-WAIT-1",
                    "vendor_id": "V-ABC",
                    "amount_idr": 12_000_000,
                },
            },
        )
        self.assertEqual(wh_res.status_code, 200, wh_res.text)
        self.assertEqual(wh_res.json()["status"], "POSTED")
        txs = self.client.get("/api/erp/transactions").json()["transactions"]
        matching = [t for t in txs if t["execution_id"] == "exec_erp_wait_1"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["status"], "POSTED")

        # Rejection webhook syncs a pending ERP row to REJECTED
        with patch("erp_sandbox.main.httpx.Client", return_value=mock_cm):
            mock_client.post.return_value = MagicMock(
                status_code=202,
                json=lambda: {
                    "id": "exec_erp_rej_1",
                    "tenant_id": "default",
                    "status": "WAITING_APPROVAL",
                    "decision": "APPROVAL_REQUIRED",
                    "reason_code": "AMOUNT_LIMIT",
                    "approval_id": "aprv_rej",
                    "payload_json": json.dumps({"amount_idr": 15_000_000}),
                },
            )
            rej_sub = self.client.post(
                "/api/erp/submit-to-veritas",
                json={"invoice_id": "INV-ERP-REJ-1", "vendor_code": "ABC", "amount": 15_000_000, "currency": "IDR"},
            )
        self.assertEqual(rej_sub.status_code, 200)
        rej_wh = self.client.post(
            "/api/erp/webhook",
            headers={"Idempotency-Key": "status-exec_erp_rej_1-rejected"},
            json={"execution_id": "exec_erp_rej_1", "tenant_id": "default", "tool": "approve_invoice", "status": "REJECTED"},
        )
        self.assertEqual(rej_wh.status_code, 200)
        self.assertEqual(rej_wh.json()["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
