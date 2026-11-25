"""Deterministic canonicalization and hashing primitives for VERITAS AI.

These helpers deliberately preserve the legacy ``veritas_harness.py`` semantics:
sorted keys, compact separators, UTF-8 without ASCII escaping. They are used for
receipt digests and for the append-only audit hash chain.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

GENESIS_HASH = "genesis"


def canonical_json(value: Any) -> str:
    """Return canonical JSON: sorted keys, no whitespace, non-ASCII preserved."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256(data: str | bytes) -> str:
    """Return the lower-case hex SHA-256 digest of ``data``."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def audit_hash(prev_hash: str, payload: Mapping[str, Any] | str) -> str:
    """Compute ``sha256(prev_hash + canonical(payload))`` for an audit event.

    ``payload`` may be the original mapping or its already-canonical JSON form,
    so a stored ``payload_json`` can always be re-hashed during verification.
    """
    canonical = payload if isinstance(payload, str) else canonical_json(payload)
    return sha256(f"{prev_hash}{canonical}")


def utc_now() -> str:
    """UTC timestamp in the legacy ISO-8601 ``...Z`` wire format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_plus(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
