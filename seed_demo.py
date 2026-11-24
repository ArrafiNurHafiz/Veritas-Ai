"""Seed the Nexora demo dataset through the real API.

Run once, then start uvicorn against the same database (default veritas.db):

    .venv/bin/python seed_demo.py
    .venv/bin/uvicorn veritas_harness:app --port 8002

Idempotent by fixed Idempotency-Key values: re-running prints current state.
"""
import os

from fastapi.testclient import TestClient

import veritas_harness as harness

OP = {"Authorization": "Bearer tok-operator"}
APPROVER = {"Authorization": "Bearer tok-approver"}
INTERNAL = {"X-Internal-Token": harness.INTERNAL_TOKEN}

INVOICES = [
    {"key": "nexora-inv-001", "invoice_id": "INV-2036-001", "amount_idr": 3_000_000, "vendor": "ABC"},
    {"key": "nexora-inv-002", "invoice_id": "INV-2036-002", "amount_idr": 8_500_000, "vendor": "ABC"},
    {"key": "nexora-inv-003", "invoice_id": "INV-2036-003", "amount_idr": 8_500_000, "vendor": "XYZ"},
    {"key": "nexora-inv-004", "invoice_id": "INV-2036-004", "amount_idr": 30_000_000, "vendor": "ABC"},
    {"key": "nexora-inv-005", "invoice_id": "INV-2036-005", "amount_idr": 1_000_000, "vendor": "EVIL"},
]


def seed() -> dict:
    client = TestClient(harness.app, follow_redirects=False)
    summary = {"executions": [], "receipts": [], "pending_approvals": [], "egress": []}

    def submit(item: dict) -> dict:
        response = client.post("/api/v1/tasks", headers={**OP, "Idempotency-Key": item["key"]},
                               json={"task_type": "invoice_review", "payload": {
                                   "invoice_id": item["invoice_id"], "amount_idr": item["amount_idr"],
                                   "vendor": item["vendor"]}})
        assert response.status_code == 202, response.text
        return response.json()

    # 1-2: allowed invoice executed + receipt, anchor confirmed
    view = submit(INVOICES[0])
    if view.get("anchor", {}).get("status") == "pending":
        anchor = client.get(f"/internal/v1/latest-anchor/{view['receipt_id']}", headers=INTERNAL).json()
        client.post(f"/internal/v1/anchors/{anchor['anchor_id']}/confirm", headers=INTERNAL)
    summary["executions"].append(view)

    # 3: over-limit invoice approved -> executed, anchor left pending for the live demo
    view = submit(INVOICES[1])
    if view["status"] == "WAITING_APPROVAL":
        decided = client.post(f"/api/v1/approvals/{view['approval_id']}/decisions", headers=APPROVER,
                              json={"decision": "approve", "reason": "Seed: reviewed", "expected_version": 1})
        assert decided.status_code == 200, decided.text
        view = decided.json()["execution"]
    summary["executions"].append(view)

    # 4: over-limit invoice left waiting for the live approval decision
    view = submit(INVOICES[2])
    summary["executions"].append(view)
    if view["status"] == "WAITING_APPROVAL":
        summary["pending_approvals"].append(view["approval_id"])

    # 5-6: denied by hard cap and by unknown vendor
    summary["executions"].append(submit(INVOICES[3]))
    summary["executions"].append(submit(INVOICES[4]))

    # 7-8: outbound data blocked, then redacted payload delivered once
    blocked = client.post("/api/v1/egress/send", headers={**OP, "Idempotency-Key": "nexora-egress-001"},
                          json={"destination": "mock://crm",
                                "payload": {"customer": "Nexora", "api_key": "sk-live-demo-secret"}})
    summary["egress"].append(blocked.json())
    allowed = client.post("/api/v1/egress/send", headers={**OP, "Idempotency-Key": "nexora-egress-002"},
                          json={"destination": "mock://ledger",
                                "payload": {"customer": "Nexora", "invoice_id": "INV-2036-002", "amount_idr": 8_500_000}})
    summary["egress"].append(allowed.json())
    return summary


def main() -> None:
    summary = seed()
    print(f"database: {os.path.abspath(harness.DB_PATH)}")
    print(f"{'execution':22} {'status':18} {'decision':17} reason")
    for view in summary["executions"]:
        print(f"{view['execution_id']:22} {view['status']:18} {str(view['decision']):17} {view['reason_code']}")
    for view in summary["executions"]:
        if view.get("receipt_id"):
            print(f"receipt {view['receipt_id']}  ->  http://localhost:8002/trust?receipt_id={view['receipt_id']}")
    for delivery in summary["egress"]:
        print(f"egress {delivery['delivery_id']:20} {delivery['decision']:5} {delivery['reason_code']}")
    if summary["pending_approvals"]:
        print(f"pending approval: {summary['pending_approvals'][0]}  (decide it live in /ui)")
    print("demo UI: http://localhost:8002/ui")


if __name__ == "__main__":
    main()