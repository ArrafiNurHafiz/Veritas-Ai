"""External tool and outbound egress adapters with SSRF protection and HMAC signing."""
from __future__ import annotations

from datetime import date
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import socket
import time
from typing import Any, Mapping
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
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


SUPPORTED_ERP_ADAPTERS: frozenset[str] = frozenset({"local_ledger", "webhook", "odoo", "sap", "custom_rest"})
ERP_AUTH_TYPES: frozenset[str] = frozenset({"none", "bearer", "api_key", "basic", "hmac", "odoo_jsonrpc"})
ERP_TOOLS: frozenset[str] = frozenset({
    "approve_invoice",
    "check_vendor_status",
    "audit_reconciliation",
    "flag_discrepancy",
})


def _erp_fernet() -> Fernet:
    seed = (
        os.environ.get("VERITAS_ERP_ENCRYPTION_KEY", "").strip()
        or os.environ.get("VERITAS_SIGNING_SECRET", "").strip()
        or os.environ.get("VERITAS_SESSION_SECRET", "").strip()
        or "veritas-dev-erp-secret-key"
    )
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_erp_credentials(creds: Mapping[str, Any]) -> str:
    """Encrypt tenant ERP credentials at rest using Fernet symmetric encryption."""
    clean = {str(k): str(v) for k, v in creds.items() if v is not None and str(v).strip()}
    payload = json.dumps(clean, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _erp_fernet().encrypt(payload).decode("utf-8")


def decrypt_erp_credentials(token: str | None) -> dict[str, str]:
    """Decrypt tenant ERP credentials; returns empty dict if unset or invalid."""
    if not token:
        return {}
    try:
        raw = _erp_fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (InvalidToken, ValueError, TypeError):
        return {}


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if len(s) <= 4:
        return "••••"
    return f"••••{s[-4:]}"


def _apply_field_mapping(payload: dict[str, Any], field_mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    if not field_mapping:
        return payload
    mapped = dict(payload)
    for src_key, dst_key in field_mapping.items():
        if not isinstance(src_key, str) or not isinstance(dst_key, str) or not dst_key.strip():
            continue
        if src_key in mapped:
            mapped[dst_key.strip()] = mapped[src_key]
        elif isinstance(mapped.get("arguments"), Mapping) and src_key in mapped["arguments"]:
            mapped[dst_key.strip()] = mapped["arguments"][src_key]
    return mapped


def _build_auth_headers(
    *,
    auth_type: str,
    auth_header: str,
    creds: Mapping[str, str],
    body_bytes: bytes,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = creds.get("api_key", "").strip()
    hmac_secret = creds.get("hmac_secret", "").strip()
    if auth_type == "bearer" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_type == "api_key" and api_key:
        hdr = (auth_header or "X-API-Key").strip() or "X-API-Key"
        headers[hdr] = api_key
    elif auth_type == "basic" and api_key:
        token = base64.b64encode(api_key.encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    elif auth_type == "none" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if hmac_secret:
        headers["X-Veritas-Signature"] = f"sha256={sign_webhook_payload(body_bytes, hmac_secret)}"
    return headers


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


def _odoo_jsonrpc_url(raw_url: str) -> str:
    base = raw_url.strip().rstrip("/")
    return base if base.endswith("/jsonrpc") else f"{base}/jsonrpc"


def _odoo_rpc_call(rpc_url: str, service: str, method: str, args: list[Any]) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
        "id": int(time.time() * 1000) % 1_000_000,
    }
    try:
        resp = httpx.post(rpc_url, json=payload, timeout=10.0)
    except httpx.HTTPError as exc:
        raise AdapterDeliveryError(f"Odoo JSON-RPC request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise AdapterDeliveryError(f"Odoo JSON-RPC returned HTTP {resp.status_code}")
    data = resp.json()
    if "error" in data:
        err = data["error"]
        msg = err.get("data", {}).get("message") or err.get("message") or str(err)
        raise AdapterDeliveryError(f"Odoo JSON-RPC error: {msg}")
    return data.get("result")


def _execute_odoo_jsonrpc(
    *,
    erp_url: str,
    execution_id: str,
    tenant_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    odoo_db: str | None = None,
    odoo_username: str | None = None,
    odoo_secret: str | None = None,
) -> dict[str, Any]:
    """Execute an ERP tool directly against a real Odoo instance via JSON-RPC 2.0."""
    validate_outbound_url(erp_url)
    rpc_url = _odoo_jsonrpc_url(erp_url)
    db = (odoo_db or os.environ.get("VERITAS_ODOO_DB", "")).strip()
    username = (odoo_username or os.environ.get("VERITAS_ODOO_USERNAME", "admin")).strip()
    secret = (
        (odoo_secret or "").strip()
        or os.environ.get("VERITAS_ODOO_API_KEY", "").strip()
        or os.environ.get("VERITAS_ODOO_PASSWORD", "admin").strip()
    )

    uid = _odoo_rpc_call(rpc_url, "common", "authenticate", [db, username, secret, {}])
    if not uid:
        raise AdapterDeliveryError("Odoo JSON-RPC authentication failed.")

    args = dict(arguments)
    vendor_ref = str(
        args.get("vendor_code") or args.get("vendor") or args.get("account_code") or "V-DEFAULT"
    ).strip()

    if tool_name == "check_vendor_status":
        rows = _odoo_rpc_call(
            rpc_url,
            "object",
            "execute_kw",
            [db, uid, secret, "res.partner", "search_read", [[["ref", "=", vendor_ref]]], {"fields": ["id", "name", "ref", "supplier_rank"], "limit": 1}],
        )
        return {
            "mode": "odoo_jsonrpc",
            "adapter": "odoo",
            "tool": tool_name,
            "execution_id": execution_id,
            "status_code": 200,
            "odoo_db": db,
            "vendor_found": bool(rows),
            "vendor": rows[0] if rows else None,
        }

    # Resolve or auto-create supplier partner in Odoo
    partner_ids = _odoo_rpc_call(
        rpc_url,
        "object",
        "execute_kw",
        [db, uid, secret, "res.partner", "search", [[["ref", "=", vendor_ref]]], {"limit": 1}],
    )
    if partner_ids:
        partner_id = int(partner_ids[0])
    else:
        partner_id = int(
            _odoo_rpc_call(
                rpc_url,
                "object",
                "execute_kw",
                [db, uid, secret, "res.partner", "create", [{"name": vendor_ref, "ref": vendor_ref, "supplier_rank": 1, "is_company": True}]],
            )
        )

    if tool_name == "approve_invoice":
        invoice_ref = str(args.get("invoice_id") or args.get("reference_id") or execution_id)
        amount = float(args.get("amount_idr") or args.get("amount") or 0)
        desc = str(args.get("description") or f"VERITAS AI Execution {execution_id}")
        move_vals: dict[str, Any] = {
            "move_type": "in_invoice",
            "partner_id": partner_id,
            "ref": f"{invoice_ref} [{execution_id[:12]}]",
            "invoice_date": date.today().isoformat(),
            "invoice_line_ids": [
                (0, 0, {"name": desc, "quantity": 1.0, "price_unit": amount}),
            ],
        }
        currency_ids = _odoo_rpc_call(
            rpc_url,
            "object",
            "execute_kw",
            [db, uid, secret, "res.currency", "search", [[["name", "=", "IDR"]]], {"limit": 1}],
        )
        if currency_ids:
            move_vals["currency_id"] = int(currency_ids[0])

        move_id = int(
            _odoo_rpc_call(
                rpc_url,
                "object",
                "execute_kw",
                [db, uid, secret, "account.move", "create", [move_vals]],
            )
        )
        posted = False
        try:
            _odoo_rpc_call(rpc_url, "object", "execute_kw", [db, uid, secret, "account.move", "action_post", [[move_id]]])
            posted = True
        except AdapterDeliveryError:
            posted = False
        return {
            "mode": "odoo_jsonrpc",
            "adapter": "odoo",
            "tool": tool_name,
            "execution_id": execution_id,
            "status_code": 200,
            "odoo_db": db,
            "odoo_partner_id": partner_id,
            "odoo_move_id": move_id,
            "odoo_state": "posted" if posted else "draft",
        }

    # audit_reconciliation / flag_discrepancy: log chatter note on partner
    note = f"[VERITAS AI · {tenant_id}] {tool_name} ({execution_id}): {args}"
    _odoo_rpc_call(
        rpc_url,
        "object",
        "execute_kw",
        [db, uid, secret, "res.partner", "message_post", [[partner_id]], {"body": note}],
    )
    return {
        "mode": "odoo_jsonrpc",
        "adapter": "odoo",
        "tool": tool_name,
        "execution_id": execution_id,
        "status_code": 200,
        "odoo_db": db,
        "odoo_partner_id": partner_id,
    }


def _resolve_runtime_erp(erp_config: Mapping[str, Any] | None) -> tuple[str, str, str, str, dict[str, str], dict[str, Any] | None]:
    """Resolve effective (adapter, erp_url, auth_type, auth_header, creds, field_mapping)."""
    if erp_config and erp_config.get("enabled", True):
        adapter = str(erp_config.get("adapter") or "webhook").strip().lower()
        erp_url = str(erp_config.get("endpoint_url") or "").strip()
        auth_type = str(erp_config.get("auth_type") or "none").strip().lower()
        auth_header = str(erp_config.get("auth_header") or "Authorization").strip()
        creds = dict(erp_config.get("credentials") or {})
        field_mapping = erp_config.get("field_mapping") if isinstance(erp_config.get("field_mapping"), Mapping) else None
        return adapter, erp_url, auth_type, auth_header, creds, dict(field_mapping) if field_mapping else None

    adapter = resolve_erp_adapter()
    erp_url = os.environ.get("VERITAS_ERP_WEBHOOK_URL", "").strip()
    creds = {
        "api_key": os.environ.get("VERITAS_ERP_API_KEY", "").strip(),
        "hmac_secret": os.environ.get("VERITAS_ERP_HMAC_SECRET", "").strip(),
        "odoo_db": os.environ.get("VERITAS_ODOO_DB", "").strip(),
        "odoo_username": os.environ.get("VERITAS_ODOO_USERNAME", "admin").strip(),
    }
    return adapter, erp_url, "bearer", "Authorization", creds, None


def execute_erp_tool(
    *,
    execution_id: str,
    tenant_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    erp_config: Mapping[str, Any] | None = None,
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
    adapter, erp_url, auth_type, auth_header, creds, field_mapping = _resolve_runtime_erp(erp_config)
    odoo_db = creds.get("odoo_db", "").strip() or os.environ.get("VERITAS_ODOO_DB", "").strip()
    if adapter == "odoo" and erp_url and odoo_db:
        return _execute_odoo_jsonrpc(
            erp_url=erp_url,
            execution_id=execution_id,
            tenant_id=tenant_id,
            tool_name=tool_name,
            arguments=arguments,
            odoo_db=odoo_db,
            odoo_username=creds.get("odoo_username"),
            odoo_secret=creds.get("api_key"),
        )
    body = build_erp_payload(
        adapter if adapter != "custom_rest" else "webhook",
        execution_id=execution_id,
        tenant_id=tenant_id,
        tool_name=tool_name,
        arguments=arguments,
    )
    body = _apply_field_mapping(body, field_mapping)
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
        **_build_auth_headers(auth_type=auth_type, auth_header=auth_header, creds=creds, body_bytes=body_bytes),
    }

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
    erp_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Best-effort webhook sync back to ERP sandbox when an execution is rejected."""
    if tool_name not in ERP_TOOLS:
        return {"synced": False, "reason": "non_erp_tool"}
    adapter, erp_url, auth_type, auth_header, creds, _ = _resolve_runtime_erp(erp_config)
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
        **_build_auth_headers(auth_type=auth_type, auth_header=auth_header, creds=creds, body_bytes=body_bytes),
    }
    try:
        resp = httpx.post(erp_url, content=body_bytes, headers=headers, timeout=3.0)
        return {"synced": resp.status_code < 400, "status_code": resp.status_code}
    except httpx.HTTPError as exc:
        return {"synced": False, "reason": str(exc)}


def test_erp_connection(*, tenant_id: str, erp_config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate SSRF policy and test live connectivity to a tenant's configured ERP."""
    adapter, erp_url, auth_type, auth_header, creds, _ = _resolve_runtime_erp(erp_config)
    if adapter == "local_ledger":
        return {"ok": True, "adapter": adapter, "status_code": 200, "detail": "Local in-process ledger active."}
    if not erp_url:
        raise AdapterDeliveryError("Endpoint URL is required for external ERP adapters.")
    validate_outbound_url(erp_url)
    started = time.monotonic()
    if adapter == "odoo":
        db = creds.get("odoo_db", "").strip()
        if not db:
            raise AdapterDeliveryError("Odoo database name (odoo_db) is required.")
        username = creds.get("odoo_username", "admin").strip() or "admin"
        secret = creds.get("api_key", "").strip()
        uid = _odoo_rpc_call(_odoo_jsonrpc_url(erp_url), "common", "authenticate", [db, username, secret, {}])
        if not uid:
            raise AdapterDeliveryError("Odoo JSON-RPC authentication failed.")
        return {
            "ok": True,
            "adapter": "odoo",
            "status_code": 200,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "detail": f"Authenticated to Odoo DB '{db}' (uid={uid}).",
        }
    body = {"event": "veritas.connection_test", "tenant_id": tenant_id, "adapter": adapter}
    body_bytes = canonical_json(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Veritas-Tenant": tenant_id,
        "X-Veritas-ERP-Adapter": adapter,
        **_build_auth_headers(auth_type=auth_type, auth_header=auth_header, creds=creds, body_bytes=body_bytes),
    }
    try:
        resp = httpx.post(erp_url, content=body_bytes, headers=headers, timeout=5.0)
    except httpx.HTTPError as exc:
        raise AdapterDeliveryError(f"ERP connection test failed: {exc}") from exc
    if resp.status_code >= 400:
        raise AdapterDeliveryError(f"ERP endpoint returned HTTP {resp.status_code}")
    return {
        "ok": True,
        "adapter": adapter,
        "status_code": resp.status_code,
        "latency_ms": round((time.monotonic() - started) * 1000, 1),
        "detail": f"Endpoint responded HTTP {resp.status_code}.",
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
