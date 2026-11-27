#!/usr/bin/env python3
"""Initialize Odoo 17 Community Edition for VERITAS AI (Accounting, Purchase, MRP).

1. Waits for Odoo HTTP readiness (:8069).
2. Initializes the `veritas_odoo` database with `account`, `purchase`, `mrp` modules
   if not already initialized (via `odoo` CLI inside the `veritas-odoo` container).
3. Seeds IDR currency / demo vendors (V-ABC, V-XYZ) via JSON-RPC so VERITAS AI
   can create and post real Vendor Bills (`account.move`) immediately.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any

import httpx

ODOO_URL = os.environ.get("VERITAS_ERP_WEBHOOK_URL", "http://127.0.0.1:8069").rstrip("/")
if ODOO_URL.endswith("/jsonrpc"):
    ODOO_URL = ODOO_URL[: -len("/jsonrpc")]
ODOO_DB = os.environ.get("VERITAS_ODOO_DB", "veritas_odoo")
ODOO_USER = os.environ.get("VERITAS_ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.environ.get("VERITAS_ODOO_PASSWORD", "admin")
ODOO_CONTAINER = os.environ.get("VERITAS_ODOO_CONTAINER", "veritas-odoo")


def _jsonrpc(service: str, method: str, args: list[Any]) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
        "id": int(time.time() * 1000) % 100000,
    }
    resp = httpx.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Odoo JSON-RPC error: {data['error']}")
    return data.get("result")


def _wait_http(timeout_s: int = 90) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = httpx.get(f"{ODOO_URL}/web/health", timeout=3.0)
            if r.status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise TimeoutError(f"Odoo did not become reachable at {ODOO_URL} within {timeout_s}s")


def _db_exists() -> bool:
    try:
        dbs = _jsonrpc("db", "list", [])
        return isinstance(dbs, list) and ODOO_DB in dbs
    except Exception:
        return False


def _init_db_in_container() -> None:
    print(f"[setup_odoo] Initializing database '{ODOO_DB}' with modules account,purchase,mrp...")
    cmd = [
        "docker",
        "exec",
        ODOO_CONTAINER,
        "odoo",
        "-d",
        ODOO_DB,
        "-i",
        "account,purchase,mrp",
        "--without-demo=all",
        "--stop-after-init",
        "--db_host",
        "odoo_db",
        "--db_user",
        "odoo",
        "--db_password",
        os.environ.get("ODOO_DB_PASSWORD", "odoo_veritas_2036"),
    ]
    subprocess.run(cmd, check=True)
    print(f"[setup_odoo] Database '{ODOO_DB}' initialized successfully.")


def _seed_vendors(uid: int) -> None:
    # Ensure IDR is active
    idr_ids = _jsonrpc(
        "object",
        "execute_kw",
        [ODOO_DB, uid, ODOO_PASSWORD, "res.currency", "search", [[["name", "=", "IDR"]]]],
    )
    if idr_ids:
        _jsonrpc(
            "object",
            "execute_kw",
            [ODOO_DB, uid, ODOO_PASSWORD, "res.currency", "write", [idr_ids, {"active": True}]],
        )

    vendors = [
        ("V-ABC", "PT ABC Cloud & Infra (V-ABC)"),
        ("V-XYZ", "CV XYZ Logistics (V-XYZ)"),
    ]
    for ref, name in vendors:
        existing = _jsonrpc(
            "object",
            "execute_kw",
            [ODOO_DB, uid, ODOO_PASSWORD, "res.partner", "search", [[["ref", "=", ref]]]],
        )
        if not existing:
            pid = _jsonrpc(
                "object",
                "execute_kw",
                [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "res.partner",
                    "create",
                    [{"name": name, "ref": ref, "supplier_rank": 1, "is_company": True}],
                ],
            )
            print(f"[setup_odoo] Created vendor {ref} (partner_id={pid})")
        else:
            print(f"[setup_odoo] Vendor {ref} already exists (partner_id={existing[0]})")


def main() -> int:
    print(f"[setup_odoo] Waiting for Odoo at {ODOO_URL}...")
    _wait_http()
    if not _db_exists():
        _init_db_in_container()
    else:
        print(f"[setup_odoo] Database '{ODOO_DB}' already exists.")

    uid = _jsonrpc("common", "authenticate", [ODOO_DB, ODOO_USER, ODOO_PASSWORD, {}])
    if not uid:
        print("[setup_odoo] ERROR: Authentication failed for user", ODOO_USER, file=sys.stderr)
        return 1
    print(f"[setup_odoo] Authenticated as uid={uid}")
    _seed_vendors(uid)
    print(f"[setup_odoo] Ready! Open Odoo UI at {ODOO_URL} (db={ODOO_DB}, user={ODOO_USER}, pass={ODOO_PASSWORD})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
