"""Tests for the standalone Mail Sandbox SMTP catcher and Web Inbox UI."""
from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from mail_sandbox.server import app, init_db, save_captured_email


class MailSandboxTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        os.environ["MAIL_SANDBOX_DB"] = self._tmp.name
        init_db(self._tmp.name)
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("MAIL_SANDBOX_DB", None)
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_capture_and_list_approval_email(self):
        raw_email = (
            b"From: noreply@veritas.local\r\n"
            b"To: approver@veritas.local\r\n"
            b"Subject: [VERITAS AI] Approval Required: INV-MAIL-1\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"Please review INV-MAIL-1 at http://localhost:3000/dashboard/approvals\r\n"
        )
        saved = save_captured_email(
            mail_from="noreply@veritas.local",
            rcpt_to=["approver@veritas.local"],
            raw_bytes=raw_email,
            db_path=self._tmp.name,
        )
        self.assertEqual(saved["subject"], "[VERITAS AI] Approval Required: INV-MAIL-1")

        res = self.client.get("/api/messages")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total_count"], 1)

        html_res = self.client.get("/")
        self.assertEqual(html_res.status_code, 200)
        self.assertIn("INV-MAIL-1", html_res.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
