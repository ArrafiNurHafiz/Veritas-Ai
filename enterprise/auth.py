"""Production authentication primitives for VERITAS AI.

No demo tokens and no hardcoded credentials live in this module. The only
fallback identity is gated behind ``VERITAS_AUTH_TEST_MODE=1`` plus an
explicit ``VERITAS_TEST_IDENTITY_JSON`` value (tests only).

Dependency order: this module is the base. ``session_store`` imports from
here; ``rbac`` and ``oidc`` import from here and from ``session_store``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from typing import Any, Literal, Mapping, TYPE_CHECKING, cast

from fastapi import Request, Response
from fastapi.responses import JSONResponse

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from .session_store import SessionStore

SESSION_COOKIE = "vt_session"
CSRF_COOKIE = "vt_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


# --------------------------------------------------------------------------- errors

class ApiError(Exception):
    """One error shape for all auth denials and OIDC failures.

    Every access denial uses 401 (unauthenticated) or 403 (forbidden) with a
    stable machine-readable ``code``. Misconfiguration/upstream outages use
    503 and are never treated as a successful authorization.
    """

    def __init__(self, status: int, code: str, message: str,
                 details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = dict(details or {})


def install_error_handler(app: Any) -> None:
    """Register the VERITAS JSON error envelope on a FastAPI app."""

    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "")
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "correlation_id": correlation_id,
            },
        )


# --------------------------------------------------------------------------- identity

@dataclass(frozen=True)
class Identity:
    """Server-side identity; never trust a client-supplied tenant_id."""

    user_id: str
    tenant_id: str
    roles: tuple[str, ...]
    email: str = ""

    def has_role(self, role: str) -> bool:
        return role.lower() in {item.lower() for item in self.roles}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Identity":
        roles = data.get("roles", ())
        if isinstance(roles, str):
            roles = tuple(part.strip() for part in roles.split(",") if part.strip())
        if not isinstance(roles, (tuple, list, set, frozenset)):
            raise ValueError("roles must be a sequence of strings")
        clean_roles = tuple(dict.fromkeys(str(role).strip().lower() for role in roles if str(role).strip()))
        user_id = str(data.get("user_id") or "").strip()
        tenant_id = str(data.get("tenant_id") or "").strip()
        if not user_id or not tenant_id:
            raise ValueError("user_id and tenant_id are required")
        return cls(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=clean_roles,
            email=str(data.get("email") or "").strip(),
        )


# --------------------------------------------------------------------------- pure token/cookie helpers

def hash_secret(value: str) -> str:
    """SHA-256 of a bearer/CSRF secret. Only hashes are persisted."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_opaque_token(nbytes: int = 32) -> str:
    """URL-safe high-entropy token for sessions and CSRF."""
    return secrets.token_urlsafe(nbytes)


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CookieConfig:
    secure: bool
    samesite: str
    ttl_seconds: int
    path: str = "/"
    domain: str | None = None

    @classmethod
    def from_env(cls, *, prefix: str = "VERITAS_COOKIE_",
                 ttl_env: str = "VERITAS_SESSION_TTL_SECONDS",
                 default_ttl: int = 12 * 60 * 60) -> "CookieConfig":
        samesite = os.environ.get(prefix + "SAMESITE", "lax").strip().lower() or "lax"
        if samesite not in {"lax", "strict", "none"}:
            raise ValueError("cookie SameSite must be lax, strict or none")
        secure = env_flag(prefix + "SECURE", default=True)
        if samesite == "none" and not secure:
            raise ValueError("SameSite=none requires Secure cookies")
        try:
            ttl = int(os.environ.get(ttl_env, str(default_ttl)))
        except ValueError as exc:
            raise ValueError(f"{ttl_env} must be an integer") from exc
        if ttl <= 0:
            raise ValueError(f"{ttl_env} must be positive")
        domain = os.environ.get(prefix + "DOMAIN", "").strip() or None
        return cls(secure=secure, samesite=samesite, ttl_seconds=ttl, domain=domain)


def set_auth_cookies(response: Response, session_token: str, csrf_token: str,
                     *, config: CookieConfig | None = None) -> None:
    """Set the HttpOnly session cookie and the JS-readable CSRF cookie."""
    config = config or CookieConfig.from_env()
    samesite = cast(Literal["lax", "strict", "none"], config.samesite)
    common: dict[str, Any] = {
        "max_age": config.ttl_seconds,
        "path": config.path,
        "domain": config.domain,
        "secure": config.secure,
        "samesite": samesite,
    }
    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, **common)
    response.headers["Cache-Control"] = "no-store"


def clear_auth_cookies(response: Response, *, config: CookieConfig | None = None) -> None:
    config = config or CookieConfig.from_env()
    samesite = cast(Literal["lax", "strict", "none"], config.samesite)
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path=config.path, domain=config.domain,
                               secure=config.secure, samesite=samesite)


def _test_identity_from_env() -> Identity | None:
    """Test-only identity source. Never enabled without the explicit flag."""
    if not env_flag("VERITAS_AUTH_TEST_MODE", default=False):
        return None
    raw = os.environ.get("VERITAS_TEST_IDENTITY_JSON", "").strip()
    if not raw:
        return None
    try:
        return Identity.from_mapping(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ApiError(401, "TEST_IDENTITY_INVALID", "Test identity is malformed.") from exc


# --------------------------------------------------------------------------- CSRF

def csrf_is_valid(csrf_cookie: str, csrf_header: str, csrf_hash: str) -> bool:
    """Double-submit: cookie must equal header AND header must match the session hash."""
    if not csrf_cookie or not csrf_header:
        return False
    return (constant_time_equals(csrf_cookie, csrf_header)
            and constant_time_equals(hash_secret(csrf_header), csrf_hash))


def enforce_csrf(request: Request, csrf_hash: str) -> None:
    if request.method.upper() in SAFE_METHODS:
        return
    supplied = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not csrf_is_valid(cookie, supplied, csrf_hash):
        raise ApiError(
            403, "CSRF_REQUIRED",
            "X-CSRF-Token must match the csrf cookie and the active session.",
        )


# --------------------------------------------------------------------------- session helpers

def get_session_store() -> SessionStore:
    from .session_store import get_session_store as _get_session_store
    return _get_session_store()


def issue_session(response: Response, identity: Identity,
                  *, store: SessionStore | None = None,
                  config: CookieConfig | None = None) -> str:
    """Create a server-side session, set cookies, return the CSRF token.

    Call this from the OIDC callback: ``issue_session(response, identity)``.
    """
    store = store or get_session_store()
    issued = store.create(identity)
    set_auth_cookies(response, issued.token, issued.csrf_token, config=config)
    return issued.csrf_token


def revoke_session(request: Request, response: Response | None = None,
                   *, store: SessionStore | None = None,
                   config: CookieConfig | None = None) -> bool:
    """Revoke the active session; clear cookies when a response is supplied."""
    store = store or get_session_store()
    token = request.cookies.get(SESSION_COOKIE, "")
    revoked = bool(token) and store.revoke(token)
    if response is not None:
        clear_auth_cookies(response, config=config)
    return revoked


# --------------------------------------------------------------------------- dependencies

def current_identity(request: Request) -> Identity:
    """Resolve identity from the server-side session cookie only.

    Enforces CSRF double-submit on every unsafe HTTP method before any
    mutation dependency or handler can run.
    """
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        view = get_session_store().load(token)
        if view is None:
            raise ApiError(401, "UNAUTHENTICATED", "Session is invalid, expired or revoked.")
        enforce_csrf(request, view.csrf_hash)
        identity = view.identity
    else:
        identity = _test_identity_from_env()
        if identity is None:
            raise ApiError(401, "UNAUTHENTICATED", "A valid session cookie is required.")
        if request.method.upper() not in SAFE_METHODS:
            supplied = request.headers.get(CSRF_HEADER, "")
            cookie = request.cookies.get(CSRF_COOKIE, "")
            if not supplied or not cookie or not constant_time_equals(supplied, cookie):
                raise ApiError(403, "CSRF_REQUIRED", "Double-submit CSRF token is required.")
    request.state.identity = identity
    return identity


__all__ = [
    "ApiError", "Identity", "CookieConfig", "SESSION_COOKIE", "CSRF_COOKIE",
    "CSRF_HEADER", "SAFE_METHODS", "install_error_handler", "hash_secret",
    "new_opaque_token", "constant_time_equals", "env_flag", "set_auth_cookies",
    "clear_auth_cookies", "csrf_is_valid", "enforce_csrf", "get_session_store",
    "issue_session", "revoke_session", "current_identity",
]
