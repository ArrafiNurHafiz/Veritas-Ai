"""Minimal EVM JSON-RPC anchor adapter.

The receipt digest is written into the transaction calldata; read-back fetches the
same transaction and compares it. This is a single-node demo anchor, not proof of
consensus, and it is not a contract call.

Env:
  VERITAS_ANCHOR_RPC_URL  e.g. http://localhost:8545 (unset = local mock confirm)
  VERITAS_ANCHOR_FROM     0x-prefixed funded account the node will sign for

ponytail: eth_sendTransaction relies on a node-managed unlocked account; a real
deployment signs locally or calls a deployed contract. One call, no retry here.
"""
from __future__ import annotations

import os

import httpx

TIMEOUT_SECONDS = 5
_id = 0


class AnchorError(Exception):
    pass


def enabled() -> bool:
    return bool(os.environ.get("VERITAS_ANCHOR_RPC_URL", "").strip())


def _rpc(method: str, params: list) -> object:
    global _id
    url = os.environ.get("VERITAS_ANCHOR_RPC_URL", "").strip().rstrip("/")
    _id += 1
    try:
        response = httpx.post(url, timeout=TIMEOUT_SECONDS,
                              json={"jsonrpc": "2.0", "id": _id, "method": method, "params": params})
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # network, HTTP, JSON
        raise AnchorError(f"{method}: {type(exc).__name__}") from exc
    if payload.get("error"):
        raise AnchorError(f"{method}: {payload['error'].get('message', 'rpc error')}")
    return payload.get("result")


def submit_digest(digest: str) -> str:
    sender = os.environ.get("VERITAS_ANCHOR_FROM", "").strip()
    if not sender:
        raise AnchorError("VERITAS_ANCHOR_FROM is required")
    tx_hash = _rpc("eth_sendTransaction", [{
        "from": sender,
        "to": sender,
        "value": "0x0",
        "data": "0x" + digest,
    }])
    if not isinstance(tx_hash, str) or not tx_hash.startswith("0x"):
        raise AnchorError("eth_sendTransaction returned no transaction hash")
    return tx_hash


def read_digest(tx_hash: str) -> str | None:
    """Return the calldata digest once the transaction is mined, else None."""
    tx = _rpc("eth_getTransactionByHash", [tx_hash])
    if not tx or tx.get("blockNumber") in (None, "0x0"):
        return None
    data = str(tx.get("input", ""))
    return data[2:].lower() if data.startswith("0x") else data.lower()
