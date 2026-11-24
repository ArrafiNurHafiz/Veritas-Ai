"""Runtime checks for the VERITAS demo services.

Run against a live local stack:
    .venv/bin/python tests/test_demo_runtime.py

These checks complement the pure unit/E2E suites by exercising the exact
surfaces the browser demo depends on. They mutate only demo data.
"""

import json
import os
import unittest
import urllib.error
import urllib.request

BASE = os.environ.get("VERITAS_BASE", "http://127.0.0.1:8002")
ADMIN = {"Authorization": "Bearer tok-admin", "Content-Type": "application/json"}


def call(method: str, path: str, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={**ADMIN, **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


class DemoRuntimeTests(unittest.TestCase):
    def test_health(self):
        status, body = call("GET", "/health/ready")
        self.assertEqual(status, 200, body)
        self.assertEqual(body.get("database"), "ok")

    def test_seeded_demo_data(self):
        status, body = call("GET", "/api/v1/executions?limit=50")
        self.assertEqual(status, 200, body)
        self.assertGreaterEqual(body["total"], 5)
        receipts = [e for e in body["executions"] if e.get("receipt_id")]
        self.assertGreaterEqual(len(receipts), 2)

    def test_stored_receipt_verifies(self):
        status, body = call("GET", "/api/v1/executions?limit=50")
        self.assertEqual(status, 200, body)
        confirmed = None
        for item in body["executions"]:
            if not item.get("receipt_id"):
                continue
            anchor = item.get("anchor") or {}
            if anchor.get("status") == "confirmed":
                confirmed = item["receipt_id"]
                break
        self.assertIsNotNone(confirmed, "no confirmed seeded receipt")
        status, result = call("POST", f"/api/v1/receipts/{confirmed}/verify", {})
        self.assertEqual(status, 200, result)
        self.assertTrue(result["signature_valid"], result)
        self.assertTrue(result["hash_matches"], result)
        self.assertTrue(result["verified"], result)

    def test_policy_can_be_published(self):
        status, before = call("GET", "/api/v1/policies")
        self.assertEqual(status, 200, before)
        original = before["source"]["auto_approve_limit_idr"]
        try:
            status, updated = call(
                "PUT",
                "/api/v1/policies",
                {"auto_approve_limit_idr": 7_500_000},
            )
            self.assertEqual(status, 200, updated)
            status, after = call("GET", "/api/v1/policies")
            self.assertEqual(after["source"]["auto_approve_limit_idr"], 7_500_000)
            self.assertNotEqual(after["digest"], before["digest"])
        finally:
            call("PUT", "/api/v1/policies", {"auto_approve_limit_idr": original})

    def test_demo_reset_endpoint_exists(self):
        status, body = call("POST", "/api/v1/demo/reset", {})
        self.assertEqual(status, 200, body)
        status, after = call("GET", "/api/v1/executions?limit=50")
        self.assertGreaterEqual(after["total"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
