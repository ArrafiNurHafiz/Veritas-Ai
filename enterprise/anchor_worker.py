"""EVM / Hyperledger Besu JSON-RPC anchor adapter and background outbox worker."""
from __future__ import annotations

import os
import threading
from typing import Any

import httpx

from . import repositories as repo
from .config import session_scope

TIMEOUT_SECONDS = 5.0
MAX_ATTEMPTS = 10
_rpc_id = 0


class AnchorRpcError(RuntimeError):
    """Raised when an EVM JSON-RPC call fails or returns an error."""


def rpc_enabled() -> bool:
    return bool(os.environ.get("VERITAS_ANCHOR_RPC_URL", "").strip())


def _rpc_call(method: str, params: list[Any]) -> Any:
    global _rpc_id
    url = os.environ.get("VERITAS_ANCHOR_RPC_URL", "").strip().rstrip("/")
    if not url:
        raise AnchorRpcError("VERITAS_ANCHOR_RPC_URL is not configured")
    _rpc_id += 1
    try:
        resp = httpx.post(
            url,
            timeout=TIMEOUT_SECONDS,
            json={"jsonrpc": "2.0", "id": _rpc_id, "method": method, "params": params},
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise AnchorRpcError(f"{method}: {type(exc).__name__}") from exc
    if payload.get("error"):
        msg = payload["error"].get("message", "rpc error")
        raise AnchorRpcError(f"{method}: {msg}")
    return payload.get("result")


def submit_digest(digest: str) -> str:
    sender = os.environ.get("VERITAS_ANCHOR_FROM", "").strip()
    if not sender:
        raise AnchorRpcError("VERITAS_ANCHOR_FROM is required for EVM anchoring")
    contract = os.environ.get("VERITAS_ANCHOR_CONTRACT", "").strip() or sender
    tx_hash = _rpc_call(
        "eth_sendTransaction",
        [{"from": sender, "to": contract, "value": "0x0", "data": "0x" + digest}],
    )
    if not isinstance(tx_hash, str) or not tx_hash.startswith("0x"):
        raise AnchorRpcError("eth_sendTransaction returned no transaction hash")
    return tx_hash


def read_digest(tx_hash: str) -> str | None:
    tx = _rpc_call("eth_getTransactionByHash", [tx_hash])
    if not tx or tx.get("blockNumber") in (None, "0x0"):
        return None
    data = str(tx.get("input", ""))
    return data[2:].lower() if data.startswith("0x") else data.lower()


def process_anchor(session: Any, anchor: Any, *, actor: str = "system:anchor-worker") -> str:
    """Submit (if needed) and read-back confirm a single pending anchor row."""
    if not rpc_enabled() or anchor.status != "pending":
        return anchor.status
    if (anchor.attempts or 0) >= MAX_ATTEMPTS:
        repo.update_anchor_attempt(
            session,
            tenant_id=anchor.tenant_id,
            anchor_id=anchor.id,
            status="failed",
            last_error="max anchor retry attempts exceeded",
        )
        return "failed"

    tx_ref = anchor.tx_ref
    try:
        if not tx_ref:
            tx_ref = submit_digest(anchor.receipt_hash)
            repo.update_anchor_attempt(
                session,
                tenant_id=anchor.tenant_id,
                anchor_id=anchor.id,
                tx_ref=tx_ref,
                last_error=None,
            )
        on_chain = read_digest(tx_ref)
    except AnchorRpcError as exc:
        repo.update_anchor_attempt(
            session,
            tenant_id=anchor.tenant_id,
            anchor_id=anchor.id,
            tx_ref=tx_ref,
            last_error=str(exc),
        )
        return "pending"

    if on_chain is None:
        return "pending"
    if on_chain != anchor.receipt_hash.lower():
        repo.update_anchor_attempt(
            session,
            tenant_id=anchor.tenant_id,
            anchor_id=anchor.id,
            tx_ref=tx_ref,
            status="failed",
            last_error="on-chain digest mismatch",
        )
        return "failed"

    repo.set_anchor_status(
        session,
        tenant_id=anchor.tenant_id,
        anchor_id=anchor.id,
        status="confirmed",
        tx_ref=tx_ref,
    )
    repo.create_audit_event(
        session,
        tenant_id=anchor.tenant_id,
        actor=actor,
        action="anchor.confirmed",
        target_type="anchor",
        target_id=anchor.id,
        payload={"tx_ref": tx_ref, "mode": "evm_rpc", "anchor_is_mock": False},
    )
    return "confirmed"


def sweep_pending_anchors(*, tenant_id: str | None = None, actor: str = "system:anchor-worker") -> dict[str, int]:
    """Process all pending anchors (scoped to tenant_id if provided)."""
    counts = {"checked": 0, "confirmed": 0, "failed": 0, "pending": 0}
    if not rpc_enabled():
        return counts
    with session_scope() as session:
        if tenant_id:
            candidates = [
                row for row in repo.list_anchors(session, tenant_id=tenant_id)
                if row.status == "pending"
            ]
        else:
            candidates = repo.list_pending_anchors_for_sweep(session)
        for anchor in candidates:
            counts["checked"] += 1
            outcome = process_anchor(session, anchor, actor=actor)
            counts[outcome] = counts.get(outcome, 0) + 1
    return counts


class AnchorOutboxWorker:
    """Periodic background worker that flushes pending EVM anchors."""

    def __init__(self, poll_seconds: float | None = None) -> None:
        self._poll = poll_seconds or float(os.environ.get("VERITAS_ANCHOR_POLL_SECONDS", "5"))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None or not rpc_enabled():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="veritas-anchor-outbox", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.wait(self._poll):
            try:
                sweep_pending_anchors()
            except Exception:
                pass
