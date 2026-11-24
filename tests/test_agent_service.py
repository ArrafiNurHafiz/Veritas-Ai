"""Contract checks for the separate, proposal-only procurement agent."""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["VERITAS_AGENT_TOKEN"] = "test-agent-token"

from fastapi.testclient import TestClient
from agent_service import app
import llm_planner

client = TestClient(app)
payload = {"invoice_id": "INV-1", "amount_idr": 8500000, "vendor": "ABC"}

assert client.post("/internal/v1/proposals", json=payload).status_code == 401
response = client.post("/internal/v1/proposals", json=payload, headers={"X-Agent-Token": "test-agent-token"})
assert response.status_code == 200
assert response.json()["proposal"] == {
    "tool": "approve_invoice",
    "arguments": {"invoice_id": "INV-1", "amount_idr": 8500000, "vendor_id": "V-ABC"},
}
assert client.post("/internal/v1/proposals", json={**payload, "amount_idr": -1},
                   headers={"X-Agent-Token": "test-agent-token"}).status_code == 422
with patch.dict(os.environ, {"VERITAS_AGENT_URL": "http://127.0.0.1:1", "VERITAS_AGENT_TOKEN": "test-agent-token"}):
    proposal, source = llm_planner.propose(payload)
    assert proposal == {} and source == "agent_unavailable"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "agent_service:app", "--port", str(port), "--log-level", "error"])
try:
    with patch.dict(os.environ, {"VERITAS_AGENT_URL": f"http://127.0.0.1:{port}", "VERITAS_AGENT_TOKEN": "test-agent-token"}):
        for _ in range(50):
            proposal, source = llm_planner.propose(payload)
            if source == "agent_service":
                break
            time.sleep(0.1)
        assert source == "agent_service"
        assert proposal["arguments"]["vendor_id"] == "V-ABC"
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(os.environ, {"VERITAS_DB": str(Path(tempdir) / "test.db")}):
            import veritas_harness
            harness = TestClient(veritas_harness.app)
            headers = {"Authorization": "Bearer tok-operator", "Idempotency-Key": "agent-live"}
            result = harness.post("/api/v1/tasks", json={"payload": payload}, headers=headers)
            assert result.status_code == 202, result.text
            assert result.json()["status"] == "WAITING_APPROVAL"
            assert result.json()["tool_calls"] == 0
            events = harness.get(f"/api/v1/executions/{result.json()['execution_id']}/events", headers=headers)
            assert "agent_service" in events.text
            server.terminate()
            server.wait(timeout=10)
            result = harness.post("/api/v1/tasks", json={"payload": payload},
                                  headers={**headers, "Idempotency-Key": "agent-offline"})
            assert result.status_code == 202, result.text
            assert result.json()["status"] == "DENIED"
            assert result.json()["tool_calls"] == 0
finally:
    server.terminate()
    server.wait(timeout=10)
print("Agent service checks passed.")
