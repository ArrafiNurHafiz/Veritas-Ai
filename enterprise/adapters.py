"""External tool and outbound egress adapters with SSRF protection and HMAC signing."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import socket
from typing import Any, Mapping
from urllib.parse import urlparse

import httpx

from .hashing import canonical_json

SENSITIVE_FIELDS: frozenset[str] = frozenset({
    "customer_secret",
    "api_key",
    "card_number",
    "ssn",
    "private_key",
    "password",
})


class SsrfBlockedError(ValueError):
    """Raised when an outbound URL targets a private, loopback, or metadata address."""


class AdapterDeliveryError(RuntimeError):
    """Raised when an external ERP or webhook call fails."""


def _allow_insecure_webhooks() -> bool:
    return os.environ.get("VERITAS_ALLOW_INSECURE_WEBHOOKS", "").strip().lower() in {"1", "true", "yes"}


def validate_outbound_url(url: str) -> None:
    """Block non-HTTPS schemes (unless opted in for tests) and private/link-local/loopback IPs."""
    parsed = urlparse(url.strip())
    allow_insecure = _allow_insecure_webhooks()
    allowed_schemes = {"https", "http"} if allow_insecure else {"https"}
    if parsed.scheme.lower() not in allowed_schemes:
        raise SsrfBlockedError(f"Unsupported URL scheme '{parsed.scheme}'; HTTPS is required.")
    hostname = parsed.hostname
    if not hostname:
        raise SsrfBlockedError("URL hostname is missing.")

    lower_host = hostname.lower()
    if allow_insecure and lower_host in {"127.0.0.1", "localhost", "::1"}:
        return

    allowlisted_hosts = {
        h.strip().lower()
        for h in os.environ.get("VERITAS_WEBHOOK_ALLOW_HOSTS", "").split(",")
        if h.strip()
    }

    try:
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise SsrfBlockedError(f"Could not resolve hostname '{hostname}'.") from exc

    for info in infos:
        ip_str = info[4][0].split("%")[0]
        ip = ipaddress.ip_address(ip_str)
        if allow_insecure and lower_host in allowlisted_hosts and ip.is_private and not ip.is_link_local and not ip.is_loopback:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise SsrfBlockedError(f"Target IP {ip} for '{hostname}' is blocked by SSRF policy.")


def sign_webhook_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 hex signature for outbound webhook verification."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def find_sensitive_fields(payload: Any) -> list[str]:
    """Recursively detect forbidden sensitive field names in a JSON payload."""
    found: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for k, v in node.items():
                if str(k).strip().lower() in SENSITIVE_FIELDS:
                    found.add(str(k))
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return sorted(found)


SUPPORTED_ERP_ADAPTERS: frozenset[str] = frozenset({"local_ledger", "webhook", "odoo", "sap"})
ERP_TOOLS: frozenset[str] = frozenset({
    "approve_invoice",
    "check_vendor_status",
    "audit_reconciliation",
    "flag_discrepancy",
})


def resolve_erp_adapter() -> str:
    """Return the configured ERP adapter preset (local_ledger, webhook, odoo, or sap)."""
    raw = os.environ.get("VERITAS_ERP_ADAPTER", "").strip().lower()
    if raw in SUPPORTED_ERP_ADAPTERS:
        return raw
    if os.environ.get("VERITAS_ERP_WEBHOOK_URL", "").strip():
        return "webhook"
    return "local_ledger"


def build_erp_payload(
    adapter: str,
    *,
    execution_id: str,
    tenant_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Map validated tool arguments into the target ERP connector schema."""
    args = dict(arguments)
    if adapter == "odoo":
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "account.move",
                "method": "action_post",
                "veritas_execution_id": execution_id,
                "tenant_id": tenant_id,
                "tool": tool_name,
                "vals": {
                    "ref": args.get("invoice_id") or args.get("reference_id") or "",
                    "partner_code": args.get("vendor_code") or args.get("vendor") or args.get("account_code") or "",
                    "amount_total": args.get("amount_idr", 0),
                    "currency": args.get("currency", "IDR"),
                    "narration": args.get("description") or args.get("reason") or "",
                },
            },
        }
    if adapter == "sap":
        return {
            "DocumentType": "RE",
            "CompanyCode": tenant_id,
            "ReferenceDocument": args.get("invoice_id") or args.get("reference_id") or "",
            "VendorAccount": args.get("vendor_code") or args.get("vendor") or args.get("account_code") or "",
            "AmountInTransactionCurrency": args.get("amount_idr", 0),
            "Currency": args.get("currency", "IDR"),
            "VeritasExecutionId": execution_id,
            "Tool": tool_name,
            "RawArguments": args,
        }
    return {
        "execution_id": execution_id,
        "tenant_id": tenant_id,
        "tool": tool_name,
        "arguments": args,
    }


def execute_erp_tool(
    *,
    execution_id: str,
    tenant_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute a validated tool call against a configured ERP connector or isolated sandbox."""
    if tool_name not in ERP_TOOLS:
        return {
            "mode": "governance_sandbox",
            "adapter": "internal_policy_sandbox",
            "tool": tool_name,
            "execution_id": execution_id,
            "status": "executed",
            "payload": {
                "execution_id": execution_id,
                "tenant_id": tenant_id,
                "tool": tool_name,
                "arguments": dict(arguments),
            },
        }
    adapter = resolve_erp_adapter()
    erp_url = os.environ.get("VERITAS_ERP_WEBHOOK_URL", "").strip()
    body = build_erp_payload(
        adapter,
        execution_id=execution_id,
        tenant_id=tenant_id,
        tool_name=tool_name,
        arguments=arguments,
    )
    if adapter == "local_ledger" or not erp_url:
        return {
            "mode": "local_ledger",
            "adapter": adapter,
            "tool": tool_name,
            "execution_id": execution_id,
            "status": "executed",
            "payload": body,
        }

    validate_outbound_url(erp_url)
    body_bytes = canonical_json(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": f"tool-{execution_id}",
        "X-Veritas-Tenant": tenant_id,
        "X-Veritas-ERP-Adapter": adapter,
    }
    erp_api_key = os.environ.get("VERITAS_ERP_API_KEY", "").strip()
    if erp_api_key:
        headers["Authorization"] = f"Bearer {erp_api_key}"
    hmac_secret = os.environ.get("VERITAS_ERP_HMAC_SECRET", "").strip()
    if hmac_secret:
        headers["X-Veritas-Signature"] = f"sha256={sign_webhook_payload(body_bytes, hmac_secret)}"

    try:
        resp = httpx.post(erp_url, content=body_bytes, headers=headers, timeout=5.0)
    except httpx.HTTPError as exc:
        raise AdapterDeliveryError(f"ERP webhook request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise AdapterDeliveryError(f"ERP webhook returned HTTP {resp.status_code}")

    return {
        "mode": "erp_webhook",
        "adapter": adapter,
        "tool": tool_name,
        "execution_id": execution_id,
        "status_code": resp.status_code,
    }


def sync_erp_execution_status(
    *,
    execution_id: str,
    tenant_id: str,
    tool_name: str,
    status: str,
    reason: str = "",
) -> dict[str, Any]:
    """Best-effort webhook sync back to ERP sandbox when an execution is rejected."""
    if tool_name not in ERP_TOOLS:
        return {"synced": False, "reason": "non_erp_tool"}
    adapter = resolve_erp_adapter()
    erp_url = os.environ.get("VERITAS_ERP_WEBHOOK_URL", "").strip()
    if adapter == "local_ledger" or not erp_url:
        return {"synced": False, "reason": "local_ledger"}
    try:
        validate_outbound_url(erp_url)
    except SsrfBlockedError as exc:
        return {"synced": False, "reason": str(exc)}
    body = {
        "execution_id": execution_id,
        "tenant_id": tenant_id,
        "tool": tool_name,
        "status": status,
        "arguments": {"reason": reason},
    }
    body_bytes = canonical_json(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": f"status-{execution_id}-{status.lower()}",
        "X-Veritas-Tenant": tenant_id,
        "X-Veritas-ERP-Adapter": adapter,
    }
    erp_api_key = os.environ.get("VERITAS_ERP_API_KEY", "").strip()
    if erp_api_key:
        headers["Authorization"] = f"Bearer {erp_api_key}"
    hmac_secret = os.environ.get("VERITAS_ERP_HMAC_SECRET", "").strip()
    if hmac_secret:
        headers["X-Veritas-Signature"] = f"sha256={sign_webhook_payload(body_bytes, hmac_secret)}"
    try:
        resp = httpx.post(erp_url, content=body_bytes, headers=headers, timeout=3.0)
        return {"synced": resp.status_code < 400, "status_code": resp.status_code}
    except httpx.HTTPError as exc:
        return {"synced": False, "reason": str(exc)}


def deliver_egress_webhook(
    *,
    destination: str,
    idempotency_key: str,
    tenant_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Deliver a policy-approved payload to an HTTPS webhook destination."""
    if destination.startswith("mock://"):
        return {"mode": "mock_sink", "destination": destination, "status_code": 200}

    validate_outbound_url(destination)
    body_bytes = canonical_json(dict(payload)).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
        "X-Veritas-Tenant": tenant_id,
    }
    secret = os.environ.get("VERITAS_EGRESS_HMAC_SECRET", "").strip()
    if secret:
        headers["X-Veritas-Signature"] = f"sha256={sign_webhook_payload(body_bytes, secret)}"

    try:
        resp = httpx.post(destination, content=body_bytes, headers=headers, timeout=5.0)
    except httpx.HTTPError as exc:
        raise AdapterDeliveryError(f"Webhook delivery failed: {exc}") from exc

    if resp.status_code >= 400:
        raise AdapterDeliveryError(f"Webhook destination returned HTTP {resp.status_code}")

    return {"mode": "https_webhook", "destination": destination, "status_code": resp.status_code}
