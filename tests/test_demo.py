"""Runnable acceptance checks for the Harness slice. No test framework.

Run: .venv/bin/python tests/test_demo.py
"""
import json
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

os.environ["VERITAS_DB"] = os.path.join(tempfile.mkdtemp(), "veritas-test.db")
os.environ["VERITAS_CORS_ORIGINS"] = "http://localhost:3000"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

import veritas_harness as harness  # noqa: E402

client = TestClient(harness.app)
OP = {"Authorization": "Bearer tok-operator"}
APPROVER = {"Authorization": "Bearer tok-approver"}
AUDITOR = {"Authorization": "Bearer tok-auditor"}
INTERNAL = {"X-Internal-Token": harness.INTERNAL_TOKEN}


def task(invoice_id, amount, vendor="ABC", key=None):
    key = key or f"idem-{invoice_id}"
    return client.post(
        "/api/v1/tasks",
        headers={**OP, "Idempotency-Key": key},
        json={"agent_id": "procurement-agent", "task_type": "invoice_review",
              "payload": {"invoice_id": invoice_id, "amount_idr": amount, "vendor": vendor}},
    )


def anchor_count():
    return client.get("/internal/mock/receiver/calls", headers=INTERNAL).json()["count"]


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"ok  {name}")


check("health live", client.get("/health/live").json()["status"] == "ok")
check("health ready", client.get("/health/ready").json()["database"] == "ok")

# AC-01 allowed invoice -> executed, signed receipt, anchor pending then confirmed
r = task("INV-2036-001", 3_000_000)
check("AC-01 status succeeded", r.status_code == 202 and r.json()["status"] == "SUCCEEDED")
check("AC-01 tool call exactly once", r.json()["tool_calls"] == 1)
exec_id = r.json()["execution_id"]
receipt_id = r.json()["receipt_id"]
v = client.post(f"/api/v1/receipts/{receipt_id}/verify", headers=AUDITOR).json()
check("AC-01 pending anchor is not verified", v["signature_valid"] and v["anchor_status"] == "pending" and not v["verified"])
anchor = client.get(f"/internal/v1/latest-anchor/{receipt_id}", headers=INTERNAL).json()
client.post(f"/internal/v1/anchors/{anchor['anchor_id']}/confirm", headers=INTERNAL)
v = client.post(f"/api/v1/receipts/{receipt_id}/verify", headers=AUDITOR).json()
check("AC-01 confirmed anchor verifies", v["verified"] and v["anchor_matches"])

# AC-02 over limit -> approval required, no tool call
r = task("INV-2036-002", 8_500_000)
check("AC-02 waits for approval", r.json()["status"] == "WAITING_APPROVAL")
check("AC-02 zero tool calls before approval", r.json()["tool_calls"] == 0)
approval_id = r.json()["approval_id"]

# AC-03 unauthorized approval -> 403, still pending with zero calls
r = client.post(f"/api/v1/approvals/{approval_id}/decisions", headers=OP, json={"decision": "approve", "reason": "self"})
check("AC-03 non-approver denied", r.status_code == 403)
state = client.get("/api/v1/approvals", headers=APPROVER).json()["approvals"]
pending = next(a for a in state if a["id"] == approval_id)
check("AC-03 approval still pending", pending["status"] == "pending")
check("AC-03 still zero tool calls", client.get(f"/api/v1/executions/{pending['execution_id']}", headers=AUDITOR).json()["tool_calls"] == 0)

# AC-04 unknown vendor / invalid amount / unknown tool surface -> denied without tool call
check("AC-04 unknown vendor denied", task("INV-2036-003", 1_000_000, vendor="EVIL").json()["decision"] == "DENY")
check("AC-04 invalid amount rejected", task("INV-2036-004", -5).status_code == 422)
check("AC-04 hard cap denied", task("INV-2036-005", 90_000_000).json()["decision"] == "DENY")
check("AC-04 boundary 5,000,000 auto-allowed", task("INV-BND-1", 5_000_000).json()["status"] == "SUCCEEDED")
check("AC-04 boundary 5,000,001 needs approval", task("INV-BND-2", 5_000_001).json()["status"] == "WAITING_APPROVAL")
check("AC-04 policy function denies unknown tool", harness.evaluate("wire_money", {}) == ("DENY", "UNKNOWN_TOOL"))

# AC-05 tampered receipt fails verification
receipt = client.get(f"/api/v1/receipts/{receipt_id}", headers=AUDITOR).json()
forged = dict(receipt["receipt"])
forged["outcome"] = "FAILED"
forged.update({"signature": receipt["signature"], "key_id": receipt["key_id"]})
v = client.post("/api/v1/verify", headers=AUDITOR, json=forged).json()
check("AC-05 tampered receipt fails", not v["verified"] and (not v["signature_valid"] or not v["hash_matches"]))

# AC-07 idempotency
again = task("INV-2036-001", 3_000_000)
check("AC-07 replay returns same execution", again.json()["execution_id"] == exec_id and again.json()["replayed"])
check("AC-07 replay does not duplicate tool call", again.json()["tool_calls"] == 1)
conflict = task("INV-2036-001", 7_000_000)
check("AC-07 conflicting reuse -> 409", conflict.status_code == 409)

# approval resume -> executes once
r = client.post(f"/api/v1/approvals/{approval_id}/decisions", headers=APPROVER,
                json={"decision": "approve", "reason": "Reviewed", "expected_version": 1})
check("AC-02 approved execution succeeds", r.status_code == 200 and r.json()["execution"]["status"] == "SUCCEEDED")
check("AC-02 approved tool call exactly once", r.json()["execution"]["tool_calls"] == 1)
second = client.post(f"/api/v1/approvals/{approval_id}/decisions", headers=APPROVER, json={"decision": "approve"})
check("AC-02 repeated decision -> 409", second.status_code == 409)

# rejection path never invokes the tool
r = task("INV-2036-006", 9_000_000)
aid = r.json()["approval_id"]
rej = client.post(f"/api/v1/approvals/{aid}/decisions", headers=APPROVER, json={"decision": "reject", "reason": "Duplicate"})
check("rejection sets REJECTED", rej.json()["execution"]["status"] == "REJECTED")
check("rejection zero tool calls", rej.json()["execution"]["tool_calls"] == 0)

# AC-08 / AC-09 outbound data
blocked = client.post("/api/v1/egress/send", headers={**OP, "Idempotency-Key": "egress-1"},
                      json={"destination": "mock://crm", "payload": {"name": "Nexora", "api_key": "sk-live-secret"}})
check("AC-08 sensitive field denied", blocked.json()["decision"] == "DENY" and blocked.json()["reason_code"] == "SENSITIVE_FIELD")
check("AC-08 receiver got zero calls", anchor_count() == 0)
offlist = client.post("/api/v1/egress/send", headers={**OP, "Idempotency-Key": "egress-2"},
                      json={"destination": "https://evil.example", "payload": {"name": "Nexora"}})
check("AC-08 off-list destination denied", offlist.json()["reason_code"] == "DESTINATION_NOT_ALLOWED")
allowed = client.post("/api/v1/egress/send", headers={**OP, "Idempotency-Key": "egress-3"},
                      json={"destination": "mock://ledger", "payload": {"name": "Nexora", "amount_idr": 8500000}})
check("AC-09 redacted payload allowed", allowed.json()["decision"] == "ALLOW" and allowed.json()["delivered"])
retry = client.post("/api/v1/egress/send", headers={**OP, "Idempotency-Key": "egress-3"},
                    json={"destination": "mock://ledger", "payload": {"name": "Nexora", "amount_idr": 8500000}})
check("AC-09 retry does not duplicate delivery", retry.json()["replayed"] and anchor_count() == 1)

# events chain is append-only
events = client.get(f"/api/v1/executions/{r.json()['execution_id']}/events", headers=AUDITOR).json()["events"]
check("event chain linked", all(events[i]["prev_hash"] == events[i - 1]["hash"] for i in range(1, len(events))))

# ------------------------------------------------------------------ demo UI

ui = TestClient(harness.app, follow_redirects=False)
check("UI login page renders", ui.get("/ui").status_code == 200 and "Masuk demo" in ui.get("/ui").text)
check("UI rejects unknown token", ui.post("/ui/login", data={"token": "nope"}).status_code == 401)
login = ui.post("/ui/login", data={"token": "tok-operator"})
check("UI login sets session", login.status_code == 303 and ui.cookies.get("vt_session")
      and ui.cookies.get("vt_session") != "tok-operator")
csrf = ui.cookies.get("vt_csrf")
check("UI sets CSRF cookie", bool(csrf))
dash = ui.get("/ui/dashboard")
check("UI dashboard renders", dash.status_code == 200 and "Approval menunggu" in dash.text)
blocked_ui = ui.post("/ui/egress", data={"csrf": csrf, "destination": "mock://crm", "payload": '{"api_key":"sk-live"}'})
check("UI blocks sensitive egress", blocked_ui.status_code == 200 and "SENSITIVE_FIELD" in blocked_ui.text)
check("UI CSRF enforced", ui.post("/ui/tasks", data={"invoice_id": "X", "amount_idr": "1", "vendor": "ABC"}).status_code == 403)
created = ui.post("/ui/tasks", data={"csrf": csrf, "invoice_id": "INV-UI-001", "amount_idr": "8500000", "vendor": "ABC"})
check("UI creates approval-required task", created.status_code == 303)
exec_page = ui.get(created.headers["location"])
check("UI execution page renders", exec_page.status_code == 200 and "WAITING_APPROVAL" in exec_page.text)

ui2 = TestClient(harness.app, follow_redirects=False)
ui2.post("/ui/login", data={"token": "tok-approver"})
csrf2 = ui2.cookies.get("vt_csrf")
ap = next(a for a in harness.rows("SELECT * FROM approvals WHERE status='pending'"))
decided = ui2.post(f"/ui/approvals/{ap['id']}/decisions",
                   data={"csrf": csrf2, "decision": "approve", "reason": "OK via UI"})
check("UI approval grants execution", decided.status_code == 303 and "SUCCEEDED" in ui2.get(decided.headers["location"]).text)

# ------------------------------------------------------------------ expiry sweeper

late = task("INV-EXP-001", 9_500_000)
late_exec, late_approval = late.json()["execution_id"], late.json()["approval_id"]
harness.run("UPDATE approvals SET expires_at=? WHERE id=?", ("2000-01-01T00:00:00Z", late_approval))
expired = client.post(f"/api/v1/approvals/{late_approval}/decisions", headers=APPROVER,
                      json={"decision": "approve", "reason": "too late"})
check("expired approval rejected", expired.status_code == 409 and expired.json()["error"]["code"] == "APPROVAL_EXPIRED")
late_view = client.get(f"/api/v1/executions/{late_exec}", headers=AUDITOR).json()
check("expired execution terminal", late_view["status"] == "EXPIRED")
check("expired zero tool calls", late_view["tool_calls"] == 0)
check("expired approval not listed", all(a["id"] != late_approval for a in
      client.get("/api/v1/approvals", headers=APPROVER).json()["approvals"]))

# ------------------------------------------------------------------ read models for the frontend

listed = client.get("/api/v1/executions", headers=AUDITOR, params={"limit": 10})
check("execution list returns scoped items",
      listed.status_code == 200 and listed.json()["total"] >= 5 and len(listed.json()["executions"]) <= 10)
check("execution list carries timestamps", "created_at" in listed.json()["executions"][0])
denied_only = client.get("/api/v1/executions", headers=AUDITOR, params={"status": "DENIED"}).json()
check("execution list filters status",
      denied_only["total"] >= 1 and all(item["status"] == "DENIED" for item in denied_only["executions"]))
check("execution list requires authentication",
      client.get("/api/v1/executions", headers={"Authorization": "Bearer nope"}).status_code == 401)
summary = client.get("/api/v1/dashboard/summary", headers=AUDITOR).json()
check("summary totals match list", summary["executions"]["total"] == listed.json()["total"])
check("summary reports pending approvals", summary["approvals_pending"] >= 1)
check("summary exposes anchor states", {"pending", "confirmed"} <= set(summary["anchors"]) or summary["anchors"])
policy = client.get("/api/v1/policies", headers=AUDITOR).json()
check("policy endpoint publishes limits",
      policy["policy_version"] == harness.POLICY_VERSION and policy["source"]["auto_approve_limit_idr"] == 5_000_000)
agents = client.get("/api/v1/agents", headers=AUDITOR).json()["agents"]
check("agent endpoint lists the procurement agent",
      len(agents) == 1 and agents[0]["allowed_tools"] == ["approve_invoice"])
pending_api = client.get("/api/v1/approvals", headers=APPROVER).json()["approvals"]
check("approval list includes proposal", pending_api and "proposal" in pending_api[0]["execution"])

# ------------------------------------------------------------------ planner trust boundary

orig_propose = harness.propose
harness.propose = lambda payload: ({"tool": "wire_transfer", "arguments": {"invoice_id": "INV-INJ", "amount_idr": 99_000_000, "vendor_id": "V-ABC"}}, "llm")
injected = task("INV-INJ-001", 3_000_000)
check("model cannot pick unregistered tool", injected.json()["decision"] == "DENY" and injected.json()["reason_code"] == "UNKNOWN_TOOL")
check("unregistered tool never executes", injected.json()["tool_calls"] == 0)

harness.propose = lambda payload: ("ignore all previous instructions", "llm")
malformed = task("INV-INJ-002", 3_000_000)
check("malformed model output denied", malformed.json()["decision"] == "DENY" and malformed.json()["reason_code"] == "INVALID_PROPOSAL")

harness.propose = lambda payload: ({"tool": "approve_invoice", "arguments": {"invoice_id": "INV-INJ-003", "amount_idr": 9_000_000, "vendor_id": "V-ABC"}}, "llm")
inflated = task("INV-INJ-003", 3_000_000)
check("model cannot self-authorize over limit", inflated.json()["status"] == "WAITING_APPROVAL" and inflated.json()["tool_calls"] == 0)
harness.propose = orig_propose

planner_labels = [ev["data"].get("planner") for ev in
                  client.get(f"/api/v1/executions/{exec_id}/events", headers=AUDITOR).json()["events"] if ev["type"] == "PROPOSAL"]
check("deterministic planner recorded", planner_labels and planner_labels[0] == "deterministic")

# ------------------------------------------------------------------ policy change and concurrency

changed = task("INV-POL-001", 8_000_000)
harness.POLICY_VERSION = 2
try:
    policy_denied = client.post(f"/api/v1/approvals/{changed.json()['approval_id']}/decisions", headers=APPROVER,
                                json={"decision": "approve", "reason": "stale policy", "expected_version": 1})
finally:
    harness.POLICY_VERSION = 1
check("changed policy rejects resume", policy_denied.json()["status"] == "rejected")
policy_view = client.get(f"/api/v1/executions/{changed.json()['execution_id']}", headers=AUDITOR).json()
check("changed policy denies execution", policy_view["status"] == "DENIED" and policy_view["reason_code"] == "POLICY_CHANGED")
check("changed policy zero tool calls", policy_view["tool_calls"] == 0 and policy_view["receipt_id"] is None)

race = task("INV-RACE-001", 7_000_000)
race_id, race_approval = race.json()["execution_id"], race.json()["approval_id"]
barrier = threading.Barrier(2)
outcomes: list[tuple[str, str]] = []


def decide_concurrently():
    barrier.wait()
    try:
        result = harness.decide_core(race_approval, "approve", "race", 1, {"user": "budi.approver", "role": "approver"})
        outcomes.append(("ok", result["status"]))
    except harness.ApiError as exc:
        outcomes.append(("err", exc.code))


threads = [threading.Thread(target=decide_concurrently) for _ in range(2)]
for t in threads:
    t.start()
for t in threads:
    t.join()
check("concurrent decision one winner", sorted(item[0] for item in outcomes) == ["err", "ok"])
check("concurrent decision tool call once",
      harness.one("SELECT COUNT(*) AS n FROM tool_calls WHERE execution_id=?", (race_id,))["n"] == 1)
check("concurrent decision one receipt",
      harness.one("SELECT COUNT(*) AS n FROM receipts WHERE execution_id=?", (race_id,))["n"] == 1)

# ------------------------------------------------------------------ observability

check("metrics require internal token", client.get("/metrics").status_code == 401)
metrics_text = client.get("/metrics", headers=INTERNAL).text
check("metrics expose request counters", "veritas_http_requests_total{" in metrics_text)
check("metrics expose business gauges",
      all(name in metrics_text for name in ("veritas_tool_calls_total", "veritas_receipts_total",
                                            "veritas_approvals_pending", "veritas_denied_total")))
check("openapi is 3.1", harness.app.openapi()["openapi"].startswith("3.1"))

seed_env = {**os.environ, "VERITAS_SIGNING_SEED": "11" * 32}
key_ids = []
for name in ("seeded-key-a.db", "seeded-key-b.db"):
    result = subprocess.run(
        [sys.executable, "-c", "import veritas_harness as h; print(h.KEY_ID)"],
        cwd=str(pathlib.Path(__file__).resolve().parents[1]), capture_output=True, text=True,
        env={**seed_env, "VERITAS_DB": os.path.join(tempfile.mkdtemp(), name)},
    )
    key_ids.append(result.stdout.strip())
check("injected signing seed is deterministic", len(key_ids[0]) == 16 and key_ids[0] == key_ids[1])
check("injected seed overrides stored key", key_ids[0] != harness.KEY_ID)

# ------------------------------------------------------------------ public trust explorer

check("trust page public", "Trust Explorer" in client.get("/trust").text)
trusted = client.get(f"/trust?receipt_id={receipt_id}").text
check("trust verifies confirmed receipt", ">VERIFIED</span>" in trusted and ">PASS</span>" in trusted)

export_row = harness.one("SELECT * FROM receipts WHERE id=?", (receipt_id,))
export = json.loads(export_row["body_json"])
check("receipt carries a random nonce", len(export.get("nonce", "")) == 32)
export.update({"signature": export_row["signature"], "key_id": export_row["key_id"]})
check("trust accepts untampered export", ">VERIFIED</span>" in client.post("/trust/verify", data={"receipt_json": json.dumps(export)}).text)
tampered = dict(export, outcome="FAILED")
rejected = client.post("/trust/verify", data={"receipt_json": json.dumps(tampered)}).text
check("trust rejects tampered export", ">NOT VERIFIED</span>" in rejected and ">FAIL</span>" in rejected)
check("trust rejects malformed JSON", client.post("/trust/verify", data={"receipt_json": "{"}).status_code == 422)

# ------------------------------------------------------------------ API session auth for separate frontend

api = TestClient(harness.app)
preflight = api.options("/api/v1/tasks", headers={"Origin": "http://localhost:3000",
                                                 "Access-Control-Request-Method": "POST"})
check("CORS preflight allows frontend origin", preflight.headers.get("access-control-allow-origin") == "http://localhost:3000")
check("API login rejects unknown token", api.post("/api/v1/auth/login", json={"token": "nope"}).status_code == 401)
login_response = api.post("/api/v1/auth/login", json={"token": "tok-admin"})
check("API login sets session cookie", login_response.status_code == 200 and api.cookies.get("vt_session")
      and api.cookies.get("vt_session") != "tok-admin")
api_csrf = login_response.json()["csrf_token"]
check("API me returns identity", api.get("/api/v1/me").json()["role"] == "admin")
no_csrf = api.post("/api/v1/egress/send", headers={"Idempotency-Key": "api-csrf-1"},
                   json={"destination": "mock://crm", "payload": {"name": "Nexora"}})
check("cookie mutation without CSRF denied", no_csrf.status_code == 403 and no_csrf.json()["error"]["code"] == "CSRF_REQUIRED")
with_csrf = api.post("/api/v1/egress/send", headers={"Idempotency-Key": "api-csrf-1", "X-CSRF-Token": api_csrf},
                     json={"destination": "mock://crm", "payload": {"name": "Nexora"}})
check("cookie mutation with CSRF allowed", with_csrf.status_code == 202 and with_csrf.json()["decision"] == "ALLOW")

# ------------------------------------------------------------------ email login and server-side sessions

sess = TestClient(harness.app, follow_redirects=False)
email_login = sess.post("/api/v1/auth/login",
                        json={"email": "marcus.vance@nexora.internal", "password": "demo123456"})
check("email login accepted", email_login.status_code == 200 and email_login.json()["role"] == "operator")
opaque = sess.cookies.get("vt_session")
check("email session token is opaque", bool(opaque) and opaque != "tok-operator")
stored = harness.one("SELECT * FROM sessions WHERE user='marcus.vance' ORDER BY created_at DESC LIMIT 1")
check("session token stored hashed", stored is not None and stored["token_hash"] == harness.sha(opaque))
me = sess.get("/api/v1/me").json()
check("email session resolves /me", me["user"] == "marcus.vance" and me["email"] == "marcus.vance@nexora.internal")
wrong = TestClient(harness.app).post("/api/v1/auth/login",
                                     json={"email": "marcus.vance@nexora.internal", "password": "nope"})
check("wrong password rejected", wrong.status_code == 401)

harness.run("UPDATE sessions SET expires_at='2000-01-01T00:00:00Z' WHERE token_hash=?", (harness.sha(opaque),))
check("expired session rejected", sess.get("/api/v1/me").status_code == 401)

sess2 = TestClient(harness.app, follow_redirects=False)
second = sess2.post("/api/v1/auth/login",
                    json={"email": "sarah.jenkins@nexora.internal", "password": "demo123456"})
check("logout requires CSRF for cookie sessions",
      sess2.post("/api/v1/auth/logout").status_code == 403)
check("session logout succeeds", sess2.post("/api/v1/auth/logout",
      headers={"X-CSRF-Token": second.json()["csrf_token"]}).status_code == 200)
check("revoked session rejected", sess2.get("/api/v1/me").status_code == 401)

legacy = TestClient(harness.app).get("/api/v1/me", headers={"Cookie": "vt_session=tok-admin"})
check("static token cookie no longer authenticates", legacy.status_code == 401)

throttle = TestClient(harness.app)
for _ in range(harness.LOGIN_MAX_FAILURES):
    throttle.post("/api/v1/auth/login", json={"email": "rate.limit@nexora.internal", "password": "nope"})
check("login rate limited", throttle.post("/api/v1/auth/login",
      json={"email": "rate.limit@nexora.internal", "password": "nope"}).status_code == 429)
harness.LOGIN_FAILURES.clear()

pending_anchor = harness.one("SELECT id FROM anchors WHERE status='pending' LIMIT 1")
check("anchor confirm rejects non-admin",
      TestClient(harness.app).post(f"/api/v1/anchors/{pending_anchor['id']}/confirm",
                                   headers={"Authorization": "Bearer tok-approver"}).status_code == 403)
confirmed = api.post(f"/api/v1/anchors/{pending_anchor['id']}/confirm", headers={"X-CSRF-Token": api_csrf})
check("anchor confirm admin succeeds", confirmed.status_code == 200 and confirmed.json()["status"] == "confirmed")

# ------------------------------------------------------------------ organization scope

harness.TOKENS["tok-other"] = {"user": "other.admin", "role": "admin", "org": "org-other", "project": "proj-other"}
OTHER = {"Authorization": "Bearer tok-other"}
other_task = client.post("/api/v1/tasks", headers={**OTHER, "Idempotency-Key": "other-inv-1"},
                         json={"task_type": "invoice_review", "payload": {
                             "invoice_id": "INV-OTHER-001", "amount_idr": 3_000_000, "vendor": "ABC"}})
other_view = other_task.json()
check("other org task executes in its own org", other_task.status_code == 202 and other_view["status"] == "SUCCEEDED")
check("other org identity in /me", client.get("/api/v1/me", headers=OTHER).json()["organization_id"] == "org-other")
check("cross-org execution hidden", client.get(f"/api/v1/executions/{other_view['execution_id']}", headers=AUDITOR).status_code == 404)
check("cross-org events hidden", client.get(f"/api/v1/executions/{other_view['execution_id']}/events", headers=AUDITOR).status_code == 404)
check("cross-org receipt hidden", client.get(f"/api/v1/receipts/{other_view['receipt_id']}", headers=AUDITOR).status_code == 404)
check("own org reads its execution", client.get(f"/api/v1/executions/{other_view['execution_id']}", headers=OTHER).status_code == 200)

other_pending = client.post("/api/v1/tasks", headers={**OTHER, "Idempotency-Key": "other-inv-2"},
                            json={"task_type": "invoice_review", "payload": {
                                "invoice_id": "INV-OTHER-002", "amount_idr": 8_500_000, "vendor": "ABC"}}).json()
visible = client.get("/api/v1/approvals", headers=APPROVER).json()["approvals"]
check("cross-org approval filtered from list", all(a["id"] != other_pending["approval_id"] for a in visible))
cross_decide = client.post(f"/api/v1/approvals/{other_pending['approval_id']}/decisions", headers=APPROVER,
                           json={"decision": "approve", "reason": "should not work", "expected_version": 1})
check("cross-org approval cannot be decided", cross_decide.status_code == 404)

shared = client.post("/api/v1/tasks", headers={**OP, "Idempotency-Key": "shared-idem"},
                     json={"payload": {"invoice_id": "INV-SHARED", "amount_idr": 2_000_000, "vendor": "ABC"}})
shared_replay = client.post("/api/v1/tasks", headers={**OTHER, "Idempotency-Key": "shared-idem"},
                            json={"payload": {"invoice_id": "INV-SHARED", "amount_idr": 2_000_000, "vendor": "ABC"}})
check("cross-org idempotency key does not leak a view",
      shared.status_code == 202 and shared_replay.status_code == 404)
harness.TOKENS.pop("tok-other")

# ------------------------------------------------------------------ EVM anchor adapter (fake JSON-RPC node)

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

node = {"fail": False, "corrupt": False, "tx": {}}


class FakeRpc(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        method = body["method"]
        if method == "eth_sendTransaction":
            if node["fail"]:
                self.send_response(500)
                self.end_headers()
                return
            digest = body["params"][0]["data"][2:]
            tx_hash = "0x" + hashlib.sha256(digest.encode()).hexdigest()
            node["tx"][tx_hash] = "f" * 64 if node["corrupt"] else digest
            result = tx_hash
        elif method == "eth_getTransactionByHash":
            tx_hash = body["params"][0]
            result = ({"hash": tx_hash, "input": "0x" + node["tx"][tx_hash], "blockNumber": "0x1"}
                      if tx_hash in node["tx"] else None)
        else:
            result = None
        payload = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRpc)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ["VERITAS_ANCHOR_RPC_URL"] = f"http://127.0.0.1:{server.server_port}"
os.environ["VERITAS_ANCHOR_FROM"] = "0x" + "11" * 20

node["fail"] = True
chain_fail = task("INV-CHAIN-001", 3_000_000).json()
check("chain outage keeps receipt durable", chain_fail["status"] == "SUCCEEDED" and chain_fail["receipt_id"])
check("chain outage leaves anchor pending with error",
      chain_fail["anchor"]["status"] == "pending" and chain_fail["anchor"]["attempts"] >= 1
      and "eth_sendTransaction" in (chain_fail["anchor"]["last_error"] or ""))
check("chain outage still serves the receipt", client.get(f"/api/v1/receipts/{chain_fail['receipt_id']}", headers=AUDITOR).status_code == 200)
chain_anchor_id = harness.one("SELECT id FROM anchors WHERE receipt_id=?", (chain_fail["receipt_id"],))["id"]
check("manual confirm disabled in chain mode",
      client.post(f"/internal/v1/anchors/{chain_anchor_id}/confirm", headers=INTERNAL).status_code == 409)

node["fail"] = False
sweep = client.post("/internal/v1/anchors/sweep", headers=INTERNAL).json()
check("chain sweep submits pending anchor", sweep["submitted"] >= 1)
check("chain sweep confirms read-back match", sweep["confirmed"] >= 1)
chain_anchor = harness.one("SELECT * FROM anchors WHERE receipt_id=?", (chain_fail["receipt_id"],))
check("chain anchor stores tx hash", chain_anchor["status"] == "confirmed" and chain_anchor["tx_ref"].startswith("0x"))
check("chain-confirmed receipt verifies publicly", ">VERIFIED</span>" in client.get(f"/trust?receipt_id={chain_fail['receipt_id']}").text)

node["corrupt"] = True
mismatch = task("INV-CHAIN-002", 3_000_000).json()
client.post("/internal/v1/anchors/sweep", headers=INTERNAL)
check("chain read-back mismatch marks anchor failed",
      harness.one("SELECT status FROM anchors WHERE receipt_id=?", (mismatch["receipt_id"],))["status"] == "failed")
check("chain-failed receipt is not verified",
      ">NOT VERIFIED</span>" in client.get(f"/trust?receipt_id={mismatch['receipt_id']}").text)

server.shutdown()
os.environ.pop("VERITAS_ANCHOR_RPC_URL", None)
os.environ.pop("VERITAS_ANCHOR_FROM", None)

print("\nAll checks passed.")