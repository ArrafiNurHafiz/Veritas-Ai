"""Server-side session storage for VERITAS AI.

Only hashed session/CSRF tokens are persisted. The DB API is intentionally
small (create/load/revoke/sweep) so a Postgres adapter can be swapped in
without touching the auth dependencies.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .auth import Identity, hash_secret, new_opaque_token

_TABLE = "enterprise_sessions"


@dataclass(frozen=True)
class SessionView:
    identity: Identity
    csrf_hash: str
    token_hash: str
    expires_at: int


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    view: SessionView


class SessionStore(Protocol):
    def create(self, identity: Identity) -> IssuedSession: ...

    def load(self, token: str) -> SessionView | None: ...

    def revoke(self, token: str) -> bool: ...

    def sweep(self) -> int: ...


def _ttl_seconds() -> int:
    try:
        ttl = int(os.environ.get("VERITAS_SESSION_TTL_SECONDS", str(12 * 60 * 60)))
    except ValueError as exc:
        raise ValueError("VERITAS_SESSION_TTL_SECONDS must be an integer") from exc
    if ttl <= 0:
        raise ValueError("VERITAS_SESSION_TTL_SECONDS must be positive")
    return ttl


def _row_to_view(row: Mapping[str, Any]) -> SessionView:
    roles: Any = row["roles"]
    if isinstance(roles, str):
        roles = json.loads(roles)
    email = row["email"] if "email" in row.keys() else ""
    return SessionView(
        identity=Identity(
            user_id=str(row["user_id"]),
            tenant_id=str(row["tenant_id"]),
            roles=tuple(str(role) for role in roles),
            email=str(email or ""),
        ),
        csrf_hash=str(row["csrf_hash"]),
        token_hash=str(row["token_hash"]),
        expires_at=int(row["expires_at"]),
    )


class InMemorySessionStore:
    """Single-process store; for tests and local development only."""

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds or _ttl_seconds()
        self._entries: dict[str, tuple[SessionView, int | None]] = {}
        self._lock = threading.RLock()

    def create(self, identity: Identity) -> IssuedSession:
        token, csrf = new_opaque_token(), new_opaque_token(16)
        now = int(time.time())
        view = SessionView(identity, hash_secret(csrf), hash_secret(token), now + self._ttl)
        with self._lock:
            self._entries[view.token_hash] = (view, now)
        return IssuedSession(token, csrf, view)

    def load(self, token: str) -> SessionView | None:
        token_hash = hash_secret(token)
        now = int(time.time())
        with self._lock:
            entry = self._entries.get(token_hash)
            if entry is None or entry[0].expires_at <= now:
                self._entries.pop(token_hash, None)
                return None
            view, _ = entry
            self._entries[token_hash] = (view, now)
            return view

    def revoke(self, token: str) -> bool:
        token_hash = hash_secret(token)
        with self._lock:
            entry = self._entries.get(token_hash)
            if entry is None or entry[0].expires_at == 0:
                return False
            view = entry[0]
            self._entries[token_hash] = (
                SessionView(view.identity, view.csrf_hash, view.token_hash, 0),
                entry[1],
            )
            return True

    def sweep(self) -> int:
        now = int(time.time())
        with self._lock:
            stale = [key for key, (view, _) in self._entries.items() if view.expires_at <= now]
            for key in stale:
                self._entries.pop(key, None)
            return len(stale)


class SqliteSessionStore:
    """Durable single-instance store. Only token/CSRF hashes are written."""

    def __init__(self, db_path: str | None = None, *, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds or _ttl_seconds()
        self._path = db_path or os.environ.get("VERITAS_DB", "veritas.db")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False, timeout=10)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
                " token_hash TEXT PRIMARY KEY,"
                " csrf_hash TEXT NOT NULL,"
                " user_id TEXT NOT NULL,"
                " tenant_id TEXT NOT NULL,"
                " roles TEXT NOT NULL,"
                " email TEXT NOT NULL DEFAULT '',"
                " created_at INTEGER NOT NULL,"
                " last_seen_at INTEGER NOT NULL,"
                " expires_at INTEGER NOT NULL,"
                " revoked_at INTEGER)"
            )
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS {_TABLE}_expiry ON {_TABLE}(expires_at)"
            )

    def create(self, identity: Identity) -> IssuedSession:
        token, csrf = new_opaque_token(), new_opaque_token(16)
        now = int(time.time())
        token_hash, csrf_hash = hash_secret(token), hash_secret(csrf)
        view = SessionView(identity, csrf_hash, token_hash, now + self._ttl)
        with self._lock, self._conn:
            self._conn.execute(
                f"INSERT INTO {_TABLE}"
                " (token_hash,csrf_hash,user_id,tenant_id,roles,email,created_at,last_seen_at,expires_at,revoked_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,NULL)",
                (token_hash, csrf_hash, identity.user_id, identity.tenant_id,
                 json.dumps(list(identity.roles)), identity.email, now, now, view.expires_at),
            )
        return IssuedSession(token, csrf, view)

    def load(self, token: str) -> SessionView | None:
        token_hash = hash_secret(token)
        now = int(time.time())
        with self._lock, self._conn:
            row = self._conn.execute(
                f"SELECT * FROM {_TABLE}"
                " WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?",
                (token_hash, now),
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                f"UPDATE {_TABLE} SET last_seen_at=? WHERE token_hash=?", (now, token_hash)
            )
            return _row_to_view(row)

    def revoke(self, token: str) -> bool:
        token_hash = hash_secret(token)
        with self._lock, self._conn:
            cursor = self._conn.execute(
                f"UPDATE {_TABLE} SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                (int(time.time()), token_hash),
            )
            return cursor.rowcount > 0

    def sweep(self) -> int:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                f"DELETE FROM {_TABLE} WHERE expires_at<=? OR (revoked_at IS NOT NULL AND revoked_at<?)",
                (int(time.time()), int(time.time()) - 7 * 24 * 60 * 60),
            )
            return max(cursor.rowcount, 0)


class PostgresSessionStore:
    """Postgres adapter (psycopg v3). DSN comes from the environment/vault."""

    def __init__(self, dsn: str, *, ttl_seconds: int | None = None) -> None:
        try:
            import psycopg  # type: ignore
            from psycopg.rows import dict_row  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional runtime dep
            raise RuntimeError("psycopg is required for VERITAS_SESSION_DSN=postgres*") from exc
        self._psycopg = psycopg
        self._dict_row = dict_row
        self._dsn = dsn
        self._ttl = ttl_seconds or _ttl_seconds()
        with self._connect() as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
                " token_hash TEXT PRIMARY KEY,"
                " csrf_hash TEXT NOT NULL,"
                " user_id TEXT NOT NULL,"
                " tenant_id TEXT NOT NULL,"
                " roles JSONB NOT NULL,"
                " email TEXT NOT NULL DEFAULT '',"
                " created_at BIGINT NOT NULL,"
                " last_seen_at BIGINT NOT NULL,"
                " expires_at BIGINT NOT NULL,"
                " revoked_at BIGINT)"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS {_TABLE}_expiry ON {_TABLE}(expires_at)"
            )

    def _connect(self):
        return self._psycopg.connect(self._dsn, autocommit=True, row_factory=self._dict_row)

    def create(self, identity: Identity) -> IssuedSession:
        token, csrf = new_opaque_token(), new_opaque_token(16)
        now = int(time.time())
        token_hash, csrf_hash = hash_secret(token), hash_secret(csrf)
        view = SessionView(identity, csrf_hash, token_hash, now + self._ttl)
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO {_TABLE}"
                " (token_hash,csrf_hash,user_id,tenant_id,roles,email,created_at,last_seen_at,expires_at,revoked_at)"
                " VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,NULL)",
                (token_hash, csrf_hash, identity.user_id, identity.tenant_id,
                 json.dumps(list(identity.roles)), identity.email, now, now, view.expires_at),
            )
        return IssuedSession(token, csrf, view)

    def load(self, token: str) -> SessionView | None:
        token_hash, now = hash_secret(token), int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {_TABLE}"
                " WHERE token_hash=%s AND revoked_at IS NULL AND expires_at>%s",
                (token_hash, now),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                f"UPDATE {_TABLE} SET last_seen_at=%s WHERE token_hash=%s", (now, token_hash)
            )
            return _row_to_view(dict(row))

    def revoke(self, token: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE {_TABLE} SET revoked_at=%s WHERE token_hash=%s AND revoked_at IS NULL",
                (int(time.time()), hash_secret(token)),
            )
            return cursor.rowcount > 0

    def sweep(self) -> int:
        now = int(time.time())
        with self._connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM {_TABLE} WHERE expires_at<=%s OR (revoked_at IS NOT NULL AND revoked_at<%s)",
                (now, now - 7 * 24 * 60 * 60),
            )
            return max(cursor.rowcount, 0)


_STORE: SessionStore | None = None
_STORE_LOCK = threading.Lock()


def configure_session_store(store: SessionStore | None) -> None:
    """Inject a store (tests) or reset the cached singleton."""
    global _STORE
    with _STORE_LOCK:
        _STORE = store


class JwtSessionStore:
    """Stateless HMAC-SHA256 JWT session store for serverless multi-instance deployments."""

    def __init__(self, secret: str | None = None, *, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds or _ttl_seconds()
        self._secret = (
            secret
            or os.environ.get("VERITAS_SESSION_SECRET", "").strip()
            or os.environ.get("VERITAS_AGENT_TOKEN", "").strip()
            or "veritas-dev-jwt-secret-change-me"
        )

    def create(self, identity: Identity) -> IssuedSession:
        import jwt as pyjwt

        csrf = new_opaque_token(16)
        csrf_hash = hash_secret(csrf)
        now = int(time.time())
        exp = now + self._ttl
        payload = {
            "uid": identity.user_id,
            "tid": identity.tenant_id,
            "roles": list(identity.roles),
            "email": identity.email,
            "csrf": csrf_hash,
            "iat": now,
            "exp": exp,
        }
        token = pyjwt.encode(payload, self._secret, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        view = SessionView(
            identity=identity,
            csrf_hash=csrf_hash,
            token_hash=hash_secret(token),
            expires_at=exp,
        )
        return IssuedSession(token=token, csrf_token=csrf, view=view)

    def load(self, token: str) -> SessionView | None:
        import jwt as pyjwt

        if not token:
            return None
        try:
            data = pyjwt.decode(token, self._secret, algorithms=["HS256"])
        except Exception:
            return None
        return SessionView(
            identity=Identity(
                user_id=str(data["uid"]),
                tenant_id=str(data["tid"]),
                roles=tuple(str(r) for r in data.get("roles", [])),
                email=str(data.get("email") or ""),
            ),
            csrf_hash=str(data["csrf"]),
            token_hash=hash_secret(token),
            expires_at=int(data["exp"]),
        )

    def revoke(self, token: str) -> bool:
        return bool(token)

    def sweep(self) -> int:
        return 0


def get_session_store() -> SessionStore:
    global _STORE
    if _STORE is not None:
        return _STORE
    with _STORE_LOCK:
        if _STORE is not None:
            return _STORE
        choice = os.environ.get("VERITAS_SESSION_STORE", "").strip().lower()
        dsn = os.environ.get("VERITAS_SESSION_DSN", "").strip()
        if not dsn:
            db_url = os.environ.get("DATABASE_URL", "").strip()
            if db_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                dsn = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
        if choice == "memory":
            _STORE = InMemorySessionStore()
        elif choice == "jwt":
            _STORE = JwtSessionStore()
        elif choice in {"postgres", "postgresql"} or (not choice and dsn.startswith(("postgres://", "postgresql://"))):
            if not dsn:
                raise RuntimeError("VERITAS_SESSION_DSN or Postgres DATABASE_URL is required for the postgres session store")
            _STORE = PostgresSessionStore(dsn)
        elif choice in {"", "sqlite"}:
            _STORE = SqliteSessionStore()
        else:
            raise RuntimeError("VERITAS_SESSION_STORE must be memory, sqlite, postgres, or jwt")
        return _STORE


__all__ = [
    "SessionView", "IssuedSession", "SessionStore", "InMemorySessionStore",
    "SqliteSessionStore", "PostgresSessionStore", "JwtSessionStore",
    "configure_session_store", "get_session_store",
]
