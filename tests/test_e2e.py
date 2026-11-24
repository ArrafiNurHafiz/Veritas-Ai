"""End-to-end HTTP checks against a real uvicorn process. No test framework.

Run: .venv/bin/python tests/test_e2e.py

Covers the demo story over the wire: login, policy outcomes, approval with CSRF,
receipt verification, egress, logout. Uses a throwaway SQLite file.
"""
import http.cookiejar
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = os.path.join(tempfile.mkdtemp(), "veritas-e2e.db")
INTERNAL = "e2e-internal"

failures = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f" — {detail}"))
    if not ok:
        failures.append(name)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Client:
    def __init__(self, base):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = ""

    def request(self, method, path, body=None, headers=None, token=False):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if token and self.csrf:
            request.add_header("X-CSRF-Token", self.csrf)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with self.opener.open(request, timeout=10) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def login(self, email, password="demo123456"):
        status, body = self.request("POST", "/api/v1/auth/login", {"email": email, "password": password})
        self.csrf = body.get("csrf_token", "") if status == 200 else ""
        return status, body


def main():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "VERITAS_DB": DB,
        "VERITAS_INTERNAL_TOKEN": INTERNAL,
        "VERITAS_CORS_ORIGINS": "http://localhost:3000",
        "VERITAS_LOG_JSON": "0",
    }
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "veritas_harness:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env,
    )
    try:
        for _ in range(60):
            try:
                with urllib.request.urlopen(base + "/health/live", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.25)
        else:
            raise SystemExit("server did not start")

        operator, approver = Client(base), Client(base)
        check("unauthenticated read is rejected", operator.request("GET", "/api/v1/me")[0] == 401)
        check("wrong password is rejected", operator.login("marcus.vance@nexora.internal", "wrong")[0] == 401)

        status, body = operator.login("marcus.vance@nexora.internal")
        check("operator login returns identity", status == 200 and body["role"] == "operator")
        check("session cookie is opaque", any(
            cookie.name == "vt_session" and cookie.value != "tok-operator" for cookie in operator.jar))
        check("me resolves the session", operator.request("GET", "/api/v1/me")[1]["user"] == "marcus.vance")
        check("cookie mutation without CSRF is rejected",
              operator.request("POST", "/api/v1/tasks", {"payload": {"invoice_id": "INV-E2E-1"}})[0] == 403)

        def submit(invoice, amount, key):
            return operator.request("POST", "/api/v1/tasks", {
                "agent_id": "procurement-agent", "task_type": "invoice_review",
                "payload": {"invoice_id": invoice, "amount_idr": amount, "vendor": "ABC"},
            }, headers={"Idempotency-Key": key}, token=True)

        status, allowed = submit("INV-E2E-1", 3_000_000, "e2e-allow")
        check("auto-approved task succeeds", status == 202 and allowed["decision"] == "ALLOW", allowed)
        execution_id = allowed["execution_id"]
        detail = operator.request("GET", f"/api/v1/executions/{execution_id}")[1]
        check("execution reached SUCCEEDED", detail["status"] == "SUCCEEDED", detail)
        receipt_id = detail["receipt_id"]
        check("receipt was anchored", detail["anchor"]["status"] in {"pending", "confirmed"})

        status, stored = operator.request("GET", f"/api/v1/receipts/{receipt_id}")
        check("receipt is readable by the owning org", status == 200 and stored["receipt"]["receipt_id"] == receipt_id)
        pending_verify = operator.request("POST", f"/api/v1/receipts/{receipt_id}/verify", token=True)[1]
        check("pending anchor never counts as verified",
              pending_verify["verified"] is False and pending_verify["anchor_status"] == "pending", pending_verify)
        admin = Client(base)
        admin.login("alexa.chen@nexora.internal")
        check("admin confirms the anchor", admin.request(
              "POST", f"/api/v1/anchors/{stored['anchor']['id']}/confirm", token=True)[0] == 200)
        confirmed = operator.request("POST", f"/api/v1/receipts/{receipt_id}/verify", token=True)[1]
        check("confirmed receipt verifies", confirmed["verified"] is True, confirmed)
        check("anonymous trust page renders", urllib.request.urlopen(base + "/trust", timeout=10).status == 200)
        tampered = {**stored["receipt"], "signature": stored["signature"], "key_id": stored["key_id"],
                    "payload_hash": "0" * 64}
        check("tampered receipt fails", operator.request("POST", "/api/v1/verify", tampered, token=True)[1]["verified"] is False)

        status, awaiting = submit("INV-E2E-2", 12_000_000, "e2e-approval")
        check("over-limit task waits for approval",
              status == 202 and awaiting["decision"] == "APPROVAL_REQUIRED", awaiting)

        check("operator cannot approve", operator.request("POST",
              f"/api/v1/approvals/{awaiting['approval_id']}/decisions",
              {"decision": "approve"}, token=True)[0] == 403)
        approver.login("sarah.jenkins@nexora.internal")
        pending = approver.request("GET", "/api/v1/approvals")[1]["approvals"]
        check("approver sees the pending item", any(item["id"] == awaiting["approval_id"] for item in pending))
        check("approval requires CSRF", approver.request("POST",
              f"/api/v1/approvals/{awaiting['approval_id']}/decisions", {"decision": "approve"})[0] == 403)
        status, decided = approver.request("POST", f"/api/v1/approvals/{awaiting['approval_id']}/decisions",
                                           {"decision": "approve"}, token=True)
        check("approver decision is applied", status in (200, 202) and decided["status"] == "approved", decided)
        resumed = operator.request("GET", f"/api/v1/executions/{awaiting['execution_id']}")[1]
        check("approved execution succeeds", resumed["status"] == "SUCCEEDED", resumed)

        status, sent = operator.request("POST", "/api/v1/egress/send", {
            "destination": "mock://crm", "execution_id": execution_id,
            "payload": {"note": "e2e", "amount_idr": 1500},
        }, headers={"Idempotency-Key": "e2e-egress"}, token=True)
        check("egress gate delivers to an allowed destination",
              status == 202 and sent["decision"] == "ALLOW" and sent["delivered"], sent)
        calls = operator.request("GET", "/internal/mock/receiver/calls",
                                 headers={"X-Internal-Token": INTERNAL})[1]["calls"]
        check("delivered payload reaches the mock receiver", bool(calls) and calls[-1]["payload"]["note"] == "e2e")
        blocked = operator.request("POST", "/api/v1/egress/send", {
            "destination": "mock://crm", "payload": {"api_key": "sk-live-secret"},
        }, headers={"Idempotency-Key": "e2e-egress-secret"}, token=True)[1]
        check("sensitive field is blocked before egress",
              blocked["decision"] == "DENY" and blocked["reason_code"] == "SENSITIVE_FIELD", blocked)
        check("egress to an unknown destination is denied",
              operator.request("POST", "/api/v1/egress/send",
                               {"destination": "https://evil.example", "payload": {"note": "x"}},
                               headers={"Idempotency-Key": "e2e-egress-offlist"}, token=True)[1]["reason_code"]
              == "DESTINATION_NOT_ALLOWED")

        operator.request("POST", "/internal/mock/receiver/failures", {"remaining": 1},
                         headers={"X-Internal-Token": INTERNAL})
        outage = operator.request("POST", "/api/v1/egress/send", {
            "destination": "mock://crm", "payload": {"note": "outage"},
        }, headers={"Idempotency-Key": "e2e-outage"}, token=True)[1]
        check("receiver outage reports a failed delivery",
              outage["decision"] == "ALLOW" and outage["delivered"] is False
              and outage["delivery_status"] == "FAILED", outage)
        recovered = operator.request("POST", "/api/v1/egress/send", {
            "destination": "mock://crm", "payload": {"note": "outage"},
        }, headers={"Idempotency-Key": "e2e-outage"}, token=True)[1]
        check("replay after the outage delivers once",
              recovered["delivered"] and recovered["delivery_attempts"] == 2, recovered)

        summary = operator.request("GET", "/api/v1/dashboard/summary")[1]
        check("summary counts the E2E work", summary["executions"]["total"] >= 2, summary)

        check("logout succeeds", operator.request("POST", "/api/v1/auth/logout", token=True)[0] == 200)
        check("logout revokes the session", operator.request("GET", "/api/v1/me")[0] == 401)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    if failures:
        raise SystemExit(f"{len(failures)} failed: {', '.join(failures)}")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
