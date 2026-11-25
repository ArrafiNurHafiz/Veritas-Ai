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

    if allow_insecure and hostname in {"127.0.0.1", "localhost", "::1"}:
        return

    try:
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise SsrfBlockedError(f"Could not resolve hostname '{hostname}'.") from exc

    for info in infos:
        ip_str = info[4][0].split("%")[0]
        ip = ipaddress.ip_address(ip_str)
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


def execute_erp_tool(
    *,
    execution_id: str,
    tenant_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute a validated tool call against a configured ERP webhook or local ledger."""
    erp_url = os.environ.get("VERITAS_ERP_WEBHOOK_URL", "").strip()
    if not erp_url:
        return {
            "mode": "local_ledger",
            "tool": tool_name,
            "execution_id": execution_id,
            "status": "executed",
        }

    validate_outbound_url(erp_url)
    body = {
        "execution_id": execution_id,
        "tenant_id": tenant_id,
        "tool": tool_name,
        "arguments": dict(arguments),
    }
    body_bytes = canonical_json(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": f"tool-{execution_id}",
        "X-Veritas-Tenant": tenant_id,
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
        "tool": tool_name,
        "execution_id": execution_id,
        "status_code": resp.status_code,
    }


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
