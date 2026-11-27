#!/usr/bin/env python3
"""Preflight for the enterprise stack through its public entrypoint.

Run after:
    docker compose -f docker-compose.enterprise.yml up -d --build

Uses only the gated test-login route, so no OIDC credentials are needed.
"""

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("ENTERPRISE_BASE", "http://localhost:8090").rstrip("/")
TENANT = os.environ.get("ENTERPRISE_TENANT", "default")


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        sys.exit(1)


class Session:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def login(self, user: str, role: str, tenant: str = TENANT) -> None:
        query = urllib.parse.urlencode({"user_id": user, "role": role, "tenant_id": tenant})
        response = self.opener.open(f"{BASE}/api/v1/auth/test-login?{query}", timeout=15)
        check(f"test-login {role}", response.status == 200)
        response.read()

    @property
    def csrf(self) -> str:
        for cookie in self.jar:
            if cookie.name == "vt_csrf":
                return cookie.value or ""
        return ""

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        headers: dict[str, str] = {}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        if method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            headers["X-CSRF-Token"] = self.csrf
        request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=20) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")


def main() -> None:
    status, health = Session().call("GET", "/health/ready")
    check("backend ready", status == 200 and health.get("database") == "ok")

    operator = Session()
    operator.login("preflight-operator", "operator")
    status, policy = operator.call("GET", "/api/v1/policies")
    check("policy readable", status == 200)
    check("auto ceiling is Rp 5,000,000",
          policy.get("source", {}).get("auto_approve_limit_idr") == 5_000_000)

    status, identity = operator.call("GET", "/api/v1/me")
    check("identity resolves from session", status == 200 and identity.get("role") == "operator")

    status, agents_body = operator.call("GET", "/api/v1/agents")
    agent_ids = [a.get("agent_id") for a in agents_body.get("agents", [])]
    check("four operational agents registered", status == 200 and len(agent_ids) == 4 and "procurement-agent" in agent_ids)

    key = "enterprise-" + uuid.uuid4().hex[:10]
    request = urllib.request.Request(
        BASE + "/api/v1/tasks",
        data=json.dumps({"task_type": "invoice_review", "payload": {
            "invoice_id": "INV-ENT-AUTO", "amount_idr": 3_200_000, "vendor": "ABC",
        }}).encode(),
        headers={"Content-Type": "application/json", "X-CSRF-Token": operator.csrf,
                 "Idempotency-Key": key},
        method="POST",
    )
    with operator.opener.open(request, timeout=20) as response:
        auto = json.loads(response.read())
        status = response.status
    check("auto task accepted", status in (200, 202))
    check("auto task succeeded before tool release", auto.get("status") == "SUCCEEDED", str(auto.get("status")))
    check("exactly one simulated tool call", auto.get("tool_calls") == 1)
    receipt_id = auto.get("receipt_id")
    check("receipt issued", bool(receipt_id))

    auditor = Session()
    auditor.login("preflight-auditor", "auditor")
    status, receipt = auditor.call("GET", f"/api/v1/receipts/{receipt_id}")
    check("receipt readable by auditor", status == 200)
    verify = auditor.call("POST", f"/api/v1/receipts/{receipt_id}/verify", {})[1]
    check("signature valid", verify.get("signature_valid") is True)
    check("canonical hash matches", verify.get("hash_matches") is True)
    check("pending anchor is not verified", verify.get("verified") is False)

    admin = Session()
    admin.login("preflight-admin", "admin")
    anchor_id = (receipt.get("anchor") or {}).get("id")
    check("anchor present", bool(anchor_id))
    status, _ = admin.call("POST", f"/api/v1/anchors/{anchor_id}/confirm", {})
    check("admin confirms local mock anchor", status == 200)
    verify = auditor.call("POST", f"/api/v1/receipts/{receipt_id}/verify", {})[1]
    check("verified after mock anchor confirm", verify.get("verified") is True)

    status, gated = operator.call("POST", "/api/v1/tasks", {
        "task_type": "invoice_review",
        "payload": {"invoice_id": "INV-ENT-GATE", "amount_idr": 8_500_000, "vendor": "ABC"},
    })
    check("gate task held", gated.get("status") == "WAITING_APPROVAL", str(gated.get("status")))
    check("zero tool calls while held", gated.get("tool_calls") == 0)
    approval_id = gated.get("approval_id")
    check("approval created", bool(approval_id))

    status, self_decision = operator.call(
        "POST", f"/api/v1/approvals/{approval_id}/decisions",
        {"decision": "approve", "reason": "self", "expected_version": 1},
    )
    check("requester cannot self-approve", status == 403)

    approver = Session()
    approver.login("preflight-approver", "approver")
    status, decided = approver.call(
        "POST", f"/api/v1/approvals/{approval_id}/decisions",
        {"decision": "approve", "reason": "Verified against purchase order", "expected_version": 1},
    )
    check("approver signs", status == 200, f"HTTP {status}")
    check("execution succeeded after sign-off",
          (decided.get("execution") or {}).get("status") == "SUCCEEDED")

    status, audit = auditor.call("GET", "/api/v1/audit-events?verify=true")
    check("audit chain valid", status == 200 and audit.get("chain", {}).get("ok") is True)

    outsider = Session()
    outsider.login("preflight-outsider", "admin", tenant="tenant-b")
    status, foreign = outsider.call("GET", "/api/v1/executions")
    check("cross-tenant list is empty", status == 200 and foreign.get("total") == 0)

    print("\nEnterprise preflight passed.")


if __name__ == "__main__":
    main()
