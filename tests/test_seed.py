"""Seed is idempotent and produces the documented demo story."""
import os
import pathlib
import sys
import tempfile

os.environ["VERITAS_DB"] = os.path.join(tempfile.mkdtemp(), "seed-test.db")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import seed_demo  # noqa: E402
import veritas_harness as harness  # noqa: E402


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"ok  {name}")


first = seed_demo.seed()
second = seed_demo.seed()

statuses = [view["status"] for view in first["executions"]]
check("seed runs five executions", len(first["executions"]) == 5)
check("seed statuses", statuses == ["SUCCEEDED", "SUCCEEDED", "WAITING_APPROVAL", "DENIED", "DENIED"])
check("seed has one pending approval", len(first["pending_approvals"]) == 1)
check("seed first execution has receipt", bool(first["executions"][0]["receipt_id"]))
check("seed egress blocked then allowed", [d["decision"] for d in first["egress"]] == ["DENY", "ALLOW"])
check("seed rerun reuses executions", [v["execution_id"] for v in second["executions"]] == [v["execution_id"] for v in first["executions"]])
check("seed did not duplicate rows", harness.one("SELECT COUNT(*) AS n FROM executions")["n"] == 5)
check("seed delivered exactly one payload", harness.one("SELECT COUNT(*) AS n FROM mock_inbox")["n"] == 1)
check("seed confirmed first anchor", harness.one("SELECT status FROM anchors LIMIT 1")["status"] == "confirmed")

print("\nAll checks passed.")