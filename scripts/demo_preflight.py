#!/usr/bin/env python3
"""Preflight checks for the VERITAS local demo.

Run after ./start_local.sh:
    .venv/bin/python scripts/demo_preflight.py

Exits non-zero on the first failed check. Mutates only synthetic demo data.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

BACKEND = os.environ.get("VERITAS_BASE", "http://127.0.0.1:8002")
FRONTEND = os.environ.get("VERITAS_FRONTEND", "http://localhost:3000")
TOKENS = {
    "operator": "tok-operator",
    "approver": "tok-approver",
    "admin": "tok-admin",
}


def call(path, method="GET", body=None, role="admin", base=BACKEND, extra=None):
    headers = {"Authorization": f"Bearer {TOKENS[role]}", "Content-Type": "application/json"}
    headers.update(extra or {})
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def check(label, condition, detail=""):
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        sys.exit(1)


def wait_for_backend():
    for _ in range(20):
        try:
            status, body = call("/health/ready")
            if status == 200 and body.get("database") == "ok":
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    check("Harness backend becomes ready", wait_for_backend())

    try:
        with urllib.request.urlopen(FRONTEND + "/", timeout=10) as response:
            frontend_status = response.status
    except Exception:
        frontend_status = 0
    check("Frontend responds", frontend_status == 200, f"HTTP {frontend_status}")

    status, summary = call("/api/v1/dashboard/summary")
    check("Dashboard summary available", status == 200, f"HTTP {status}")
    check("Seeded executions present", summary.get("executions", {}).get("total", 0) >= 5)
    check("Seeded receipts present", summary.get("receipts", 0) >= 2)
    check("Pending approval present", summary.get("approvals_pending", 0) >= 1)

    status, policy = call("/api/v1/policies")
    check("Policy endpoint available", status == 200)
    check("Auto ceiling is Rp 5,000,000",
          policy.get("source", {}).get("auto_approve_limit_idr") == 5_000_000)

    key = "preflight-" + uuid.uuid4().hex[:12]
    status, created = call(
        "/api/v1/tasks",
        method="POST",
        role="operator",
        body={"task_type": "invoice_review", "payload": {
            "invoice_id": "INV-PREFLIGHT-001",
            "amount_idr": 8_500_000,
            "vendor": "V-ABC",
        }},
        extra={"Idempotency-Key": key},
    )
    check("Over-limit task accepted", status == 202, f"HTTP {status}")
    check("Task held before tool execution",
          created.get("status") == "WAITING_APPROVAL" and created.get("tool_calls", 1) == 0,
          str(created.get("status")))

    approval_id = created.get("approval_id")
    check("Approval record created", bool(approval_id))
    status, decided = call(
        f"/api/v1/approvals/{approval_id}/decisions",
        method="POST",
        role="approver",
        body={"decision": "approve", "reason": "Preflight deterministic check", "expected_version": 1},
    )
    check("Approver can sign", status == 200, f"HTTP {status}")
    execution = decided.get("execution", {})
    check("Execution succeeded after sign-off", execution.get("status") == "SUCCEEDED",
          str(execution.get("status")))
    receipt_id = execution.get("receipt_id")
    check("Signed receipt issued", bool(receipt_id))

    status, verified = call(f"/api/v1/receipts/{receipt_id}/verify", method="POST", body={})
    check("Receipt verification endpoint works", status == 200, f"HTTP {status}")
    check("Signature valid", verified.get("signature_valid") is True)
    check("Canonical hash matches", verified.get("hash_matches") is True)
    check("Pending mock anchor is not verified", verified.get("verified") is False,
          str(verified.get("anchor_status")))

    print("\nAll demo preflight checks passed.")


if __name__ == "__main__":
    main()
