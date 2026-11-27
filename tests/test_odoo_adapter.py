"""Unit tests for the real Odoo JSON-RPC 2.0 adapter in enterprise/adapters.py."""
from __future__ import annotations

from typing import Any

import pytest

from enterprise.adapters import AdapterDeliveryError, execute_erp_tool


class _FakeResp:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_odoo_jsonrpc_approve_invoice_creates_and_posts_bill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERITAS_ERP_ADAPTER", "odoo")
    monkeypatch.setenv("VERITAS_ERP_WEBHOOK_URL", "http://127.0.0.1:8069")
    monkeypatch.setenv("VERITAS_ALLOW_INSECURE_WEBHOOKS", "1")
    monkeypatch.setenv("VERITAS_ODOO_DB", "veritas_odoo")
    monkeypatch.setenv("VERITAS_ODOO_USERNAME", "admin")
    monkeypatch.setenv("VERITAS_ODOO_PASSWORD", "admin")

    calls: list[dict[str, Any]] = []

    def fake_post(url: str, json: dict[str, Any], timeout: float = 10.0) -> _FakeResp:
        calls.append({"url": url, "json": json})
        params = json["params"]
        if params["service"] == "common" and params["method"] == "authenticate":
            return _FakeResp(200, {"jsonrpc": "2.0", "id": 1, "result": 2})
        model = params["args"][3]
        method = params["args"][4]
        if model == "res.partner" and method == "search":
            return _FakeResp(200, {"jsonrpc": "2.0", "id": 2, "result": [7]})
        if model == "res.currency" and method == "search":
            return _FakeResp(200, {"jsonrpc": "2.0", "id": 3, "result": [13]})
        if model == "account.move" and method == "create":
            return _FakeResp(200, {"jsonrpc": "2.0", "id": 4, "result": 42})
        if model == "account.move" and method == "action_post":
            return _FakeResp(200, {"jsonrpc": "2.0", "id": 5, "result": True})
        raise AssertionError(f"Unexpected RPC call: {params}")

    monkeypatch.setattr("enterprise.adapters.httpx.post", fake_post)

    res = execute_erp_tool(
        execution_id="exec_odoo_001",
        tenant_id="default",
        tool_name="approve_invoice",
        arguments={"invoice_id": "INV-2036-009", "vendor_code": "V-ABC", "amount_idr": 3200000},
    )
    assert res["mode"] == "odoo_jsonrpc"
    assert res["adapter"] == "odoo"
    assert res["odoo_partner_id"] == 7
    assert res["odoo_move_id"] == 42
    assert res["odoo_state"] == "posted"
    assert all(c["url"] == "http://127.0.0.1:8069/jsonrpc" for c in calls)


def test_odoo_jsonrpc_auth_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERITAS_ERP_ADAPTER", "odoo")
    monkeypatch.setenv("VERITAS_ERP_WEBHOOK_URL", "http://127.0.0.1:8069")
    monkeypatch.setenv("VERITAS_ALLOW_INSECURE_WEBHOOKS", "1")
    monkeypatch.setenv("VERITAS_ODOO_DB", "veritas_odoo")

    monkeypatch.setattr(
        "enterprise.adapters.httpx.post",
        lambda url, json, timeout=10.0: _FakeResp(200, {"jsonrpc": "2.0", "id": 1, "result": False}),
    )

    with pytest.raises(AdapterDeliveryError, match="authentication failed"):
        execute_erp_tool(
            execution_id="exec_odoo_fail",
            tenant_id="default",
            tool_name="approve_invoice",
            arguments={"invoice_id": "INV-ERR", "vendor_code": "V-ABC", "amount_idr": 100000},
        )
