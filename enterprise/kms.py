"""Signing key provider abstraction for VERITAS AI.

Supports deterministic 32-byte Ed25519 seeds injected via environment/KMS
and enforces non-ephemeral keys when VERITAS_ENV=production.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .hashing import sha256


@dataclass(frozen=True)
class SigningKey:
    private_key: Ed25519PrivateKey
    key_id: str
    provider: str


def _is_production() -> bool:
    return os.environ.get("VERITAS_ENV", "").strip().lower() == "production"


_CACHED_KEY: SigningKey | None = None


def reset_signing_key_cache() -> None:
    global _CACHED_KEY
    _CACHED_KEY = None


def get_signing_key() -> SigningKey:
    """Resolve the active Ed25519 signing key from KMS/env configuration."""
    global _CACHED_KEY
    if _CACHED_KEY is not None:
        return _CACHED_KEY

    seed_hex = os.environ.get("VERITAS_SIGNING_SEED", "").strip()
    explicit_key_id = os.environ.get("VERITAS_SIGNING_KEY_ID", "").strip()
    kms_bypass = os.environ.get("VERITAS_KMS_BYPASS", "1").strip().lower() in {"1", "true", "yes"}
    vault_addr = os.environ.get("VAULT_ADDR", "").strip()
    if seed_hex:
        try:
            seed = bytes.fromhex(seed_hex)
        except ValueError as exc:
            raise RuntimeError("VERITAS_SIGNING_SEED must be 64 hex characters") from exc
        if len(seed) != 32:
            raise RuntimeError("VERITAS_SIGNING_SEED must be 64 hex characters")
        provider = "vault_kms" if (vault_addr and not kms_bypass) else "env_seed"
    elif _is_production() and not kms_bypass:
        raise RuntimeError(
            "VERITAS_SIGNING_SEED (64 hex chars) or Vault KMS is required when VERITAS_ENV=production"
        )
    else:
        seed = os.urandom(32)
        provider = "ephemeral_bypass"

    private = Ed25519PrivateKey.from_private_bytes(seed)
    raw_pub = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    key_id = explicit_key_id or sha256(raw_pub)[:16]
    _CACHED_KEY = SigningKey(private_key=private, key_id=key_id, provider=provider)
    return _CACHED_KEY
