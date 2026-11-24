"""Contract snapshot the frontend agent codes against.

    .venv/bin/python tests/test_openapi.py           # fail when the snapshot is stale
    .venv/bin/python tests/test_openapi.py --write   # refresh after an intended API change
"""
import json
import os
import pathlib
import sys
import tempfile

os.environ["VERITAS_DB"] = os.path.join(tempfile.mkdtemp(), "openapi-test.db")
ROOT = pathlib.Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "openapi.json"
sys.path.insert(0, str(ROOT))

import veritas_harness as harness  # noqa: E402


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"ok  {name}")


spec = harness.app.openapi()
check("openapi is 3.1", spec["openapi"].startswith("3.1"))
for path in (
    "/api/v1/tasks",
    "/api/v1/executions/{execution_id}",
    "/api/v1/approvals/{approval_id}/decisions",
    "/api/v1/egress/send",
    "/api/v1/receipts/{receipt_id}/verify",
    "/api/v1/auth/login",
    "/api/v1/anchors/{anchor_id}/confirm",
):
    check(f"contract includes {path}", path in spec["paths"])

if "--write" in sys.argv:
    SNAPSHOT.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {SNAPSHOT}")
else:
    stored = json.loads(SNAPSHOT.read_text())
    assert stored == spec, "docs/openapi.json is stale; rerun with --write and review the diff"
    print("ok  snapshot current")
    print("\nAll checks passed.")
