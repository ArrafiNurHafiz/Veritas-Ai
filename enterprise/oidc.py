"""Generic OIDC authorization-code flow with PKCE (Keycloak/Google/Entra).

Configuration comes only from the environment: OIDC_ISSUER, OIDC_CLIENT_ID,
OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI. No secret is hardcoded or logged.
State, nonce and PKCE verifier are single-use and kept server-side.

All access denials are :class:`~enterprise.auth.ApiError` 401/403; IdP/network
misconfiguration is reported as 503 and never becomes a valid session.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Protocol, cast
from urllib.parse import urlencode

import httpx
import jwt

from .auth import (
    ApiError, CookieConfig, Identity, constant_time_equals, issue_session,
)
from .rbac import normalize_roles

STATE_COOKIE = "vt_oidc_state"


# --------------------------------------------------------------------------- pure generators

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_state(token_bytes: Callable[[int], bytes] = secrets.token_bytes) -> str:
    """Random 256-bit CSRF state (pure; inject token_bytes for deterministic tests)."""
    return _b64url(token_bytes(32))


def generate_nonce(token_bytes: Callable[[int], bytes] = secrets.token_bytes) -> str:
    return _b64url(token_bytes(32))


def generate_pkce_verifier(token_bytes: Callable[[int], bytes] = secrets.token_bytes) -> str:
    """RFC 7636 verifier: 64 chars from the unreserved alphabet."""
    return _b64url(token_bytes(48))


def pkce_challenge(verifier: str) -> str:
    """RFC 7636 S256 challenge (pure)."""
    if not 43 <= len(verifier) <= 128:
        raise ValueError("PKCE verifier must be 43-128 characters")
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def generate_pkce_pair(token_bytes: Callable[[int], bytes] = secrets.token_bytes) -> tuple[str, str]:
    verifier = generate_pkce_verifier(token_bytes)
    return verifier, pkce_challenge(verifier)


def validate_state(expected: str, actual: str) -> None:
    """Constant-time state comparison; mismatch is a 401 denial."""
    if not expected or not actual or not constant_time_equals(expected, actual):
        raise ApiError(401, "OIDC_INVALID_STATE", "OIDC state mismatch; login aborted.")


# --------------------------------------------------------------------------- configuration

@dataclass(frozen=True)
class OidcConfig:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: str = "openid email profile"
    tenant_claim: str = "tenant_id"
    roles_claim: str = "realm_access.roles"
    id_token_algorithms: tuple[str, ...] = ("RS256",)
    client_auth_method: str = "client_secret_basic"
    leeway_seconds: int = 30
    http_timeout_seconds: float = 10.0
    discovery_ttl_seconds: int = 3600
    flow_ttl_seconds: int = 600
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    jwks_url: str = ""

    @classmethod
    def from_env(cls) -> "OidcConfig":
        algorithms = tuple(
            item.strip() for item in
            os.environ.get("OIDC_ID_TOKEN_ALGORITHMS", "RS256").split(",") if item.strip()
        )
        return cls(
            issuer=os.environ.get("OIDC_ISSUER", "").strip().rstrip("/"),
            client_id=os.environ.get("OIDC_CLIENT_ID", "").strip(),
            client_secret=os.environ.get("OIDC_CLIENT_SECRET", "").strip(),
            redirect_uri=os.environ.get("OIDC_REDIRECT_URI", "").strip(),
            scopes=os.environ.get("OIDC_SCOPES", "openid email profile").strip(),
            tenant_claim=os.environ.get("OIDC_TENANT_CLAIM", "tenant_id").strip(),
            roles_claim=os.environ.get("OIDC_ROLES_CLAIM", "realm_access.roles").strip(),
            id_token_algorithms=algorithms or ("RS256",),
            client_auth_method=os.environ.get(
                "OIDC_CLIENT_AUTH_METHOD", "client_secret_basic").strip().lower(),
            leeway_seconds=int(os.environ.get("OIDC_LEEWAY_SECONDS", "30")),
            http_timeout_seconds=float(os.environ.get("OIDC_HTTP_TIMEOUT_SECONDS", "10")),
            discovery_ttl_seconds=int(os.environ.get("OIDC_DISCOVERY_TTL_SECONDS", "3600")),
            flow_ttl_seconds=int(os.environ.get("OIDC_FLOW_TTL_SECONDS", "600")),
            authorization_endpoint=os.environ.get("OIDC_AUTHORIZATION_ENDPOINT", "").strip(),
            token_endpoint=os.environ.get("OIDC_TOKEN_ENDPOINT", "").strip(),
            jwks_url=os.environ.get("OIDC_JWKS_URL", "").strip(),
        )

    def require(self) -> None:
        missing = [name for name, value in (
            ("OIDC_ISSUER", self.issuer), ("OIDC_CLIENT_ID", self.client_id),
            ("OIDC_CLIENT_SECRET", self.client_secret), ("OIDC_REDIRECT_URI", self.redirect_uri),
        ) if not value]
        if missing:
            raise ApiError(503, "OIDC_NOT_CONFIGURED", "OIDC is not configured.",
                           {"missing": missing})
        if self.client_auth_method not in {"client_secret_basic", "client_secret_post"}:
            raise ApiError(503, "OIDC_NOT_CONFIGURED", "Unsupported OIDC client auth method.")
        if not self.id_token_algorithms:
            raise ApiError(503, "OIDC_NOT_CONFIGURED", "No accepted ID token algorithms.")


@dataclass(frozen=True)
class ProviderMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


_DISCOVERY_CACHE: dict[str, tuple[float, ProviderMetadata]] = {}


async def discover(config: OidcConfig,
                   client: httpx.AsyncClient | None = None) -> ProviderMetadata:
    """Discovery with a short TTL cache; explicit env endpoints override it."""
    config.require()
    if all((config.authorization_endpoint, config.token_endpoint, config.jwks_url)):
        return ProviderMetadata(config.issuer, config.authorization_endpoint,
                                config.token_endpoint, config.jwks_url)
    cached = _DISCOVERY_CACHE.get(config.issuer)
    if cached and cached[0] > time.time():
        return cached[1]
    owns = client is None
    client = client or httpx.AsyncClient(timeout=config.http_timeout_seconds)
    try:
        response = await client.get(f"{config.issuer}/.well-known/openid-configuration")
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApiError(503, "OIDC_DISCOVERY_UNAVAILABLE", "OIDC discovery failed.") from exc
    finally:
        if owns:
            await client.aclose()
    issuer = str(data.get("issuer") or "").rstrip("/")
    if not issuer or issuer != config.issuer:
        raise ApiError(503, "OIDC_DISCOVERY_INVALID", "Discovery issuer does not match OIDC_ISSUER.")
    metadata = ProviderMetadata(
        issuer=issuer,
        authorization_endpoint=config.authorization_endpoint or str(data.get("authorization_endpoint") or ""),
        token_endpoint=config.token_endpoint or str(data.get("token_endpoint") or ""),
        jwks_uri=config.jwks_url or str(data.get("jwks_uri") or ""),
    )
    if not all((metadata.authorization_endpoint, metadata.token_endpoint, metadata.jwks_uri)):
        raise ApiError(503, "OIDC_DISCOVERY_INVALID", "Discovery is missing required endpoints.")
    _DISCOVERY_CACHE[config.issuer] = (time.time() + config.discovery_ttl_seconds, metadata)
    return metadata


# --------------------------------------------------------------------------- single-use flow state

@dataclass(frozen=True)
class AuthorizationFlow:
    state: str
    code_verifier: str
    nonce: str
    created_at: float
    expires_at: float

    def expired(self, now: float | None = None) -> bool:
        return (time.time() if now is None else now) >= self.expires_at


class AuthorizationFlowStore(Protocol):
    def save(self, flow: AuthorizationFlow) -> None: ...

    def consume(self, state: str) -> AuthorizationFlow | None: ...


class InMemoryAuthorizationFlowStore:
    """Single-instance flow store. Multi-instance deployments must inject a shared store."""

    def __init__(self) -> None:
        self._flows: dict[str, AuthorizationFlow] = {}
        self._lock = threading.RLock()

    def save(self, flow: AuthorizationFlow) -> None:
        with self._lock:
            self._flows[flow.state] = flow

    def consume(self, state: str) -> AuthorizationFlow | None:
        with self._lock:
            return self._flows.pop(state, None)


_FLOW_STORE: AuthorizationFlowStore = InMemoryAuthorizationFlowStore()


def configure_flow_store(store: AuthorizationFlowStore | None) -> AuthorizationFlowStore:
    global _FLOW_STORE
    if store is not None:
        _FLOW_STORE = store
    return _FLOW_STORE


def get_flow_store() -> AuthorizationFlowStore:
    return _FLOW_STORE


# --------------------------------------------------------------------------- authorization URL

def build_authorization_url(config: OidcConfig, metadata: ProviderMetadata,
                            state: str, code_challenge: str, nonce: str) -> str:
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    separator = "&" if "?" in metadata.authorization_endpoint else "?"
    return metadata.authorization_endpoint + separator + urlencode(params)


async def start_authorization(response: Any, *, config: OidcConfig | None = None,
                              flow_store: AuthorizationFlowStore | None = None,
                              client: httpx.AsyncClient | None = None) -> str:
    """Create a PKCE flow, set a short-lived state cookie, return the redirect URL."""
    config = config or OidcConfig.from_env()
    config.require()
    metadata = await discover(config, client=client)
    state, nonce = generate_state(), generate_nonce()
    verifier, challenge = generate_pkce_pair()
    now = time.time()
    (flow_store or get_flow_store()).save(AuthorizationFlow(
        state=state, code_verifier=verifier, nonce=nonce,
        created_at=now, expires_at=now + config.flow_ttl_seconds,
    ))
    cookie = CookieConfig.from_env(
        ttl_env="OIDC_FLOW_TTL_SECONDS", default_ttl=config.flow_ttl_seconds)
    response.set_cookie(
        STATE_COOKIE, state, httponly=True, secure=cookie.secure,
        samesite=cast(Literal["lax", "strict", "none"], cookie.samesite),
        max_age=config.flow_ttl_seconds, path=cookie.path, domain=cookie.domain,
    )
    return build_authorization_url(config, metadata, state, challenge, nonce)


# --------------------------------------------------------------------------- token + ID token verification

async def exchange_code(config: OidcConfig, metadata: ProviderMetadata, code: str,
                        code_verifier: str,
                        client: httpx.AsyncClient | None = None) -> Mapping[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.redirect_uri,
        "code_verifier": code_verifier,
    }
    auth = None
    if config.client_auth_method == "client_secret_basic":
        auth = (config.client_id, config.client_secret)
    else:
        data["client_id"] = config.client_id
        data["client_secret"] = config.client_secret
    owns = client is None
    client = client or httpx.AsyncClient(timeout=config.http_timeout_seconds)
    request_kwargs: dict[str, Any] = {"data": data}
    if auth is not None:
        request_kwargs["auth"] = auth
    try:
        response = await client.post(metadata.token_endpoint, **request_kwargs)
    except httpx.HTTPError as exc:
        raise ApiError(503, "OIDC_TOKEN_ENDPOINT_UNAVAILABLE", "Token endpoint unavailable.") from exc
    finally:
        if owns:
            await client.aclose()
    if response.status_code < 200 or response.status_code >= 300:
        raise ApiError(401, "OIDC_TOKEN_EXCHANGE_FAILED", "Authorization code was rejected.",
                       {"idp_status": response.status_code})
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(401, "OIDC_TOKEN_EXCHANGE_FAILED", "Token response is invalid.") from exc
    if not isinstance(payload, Mapping):
        raise ApiError(401, "OIDC_TOKEN_EXCHANGE_FAILED", "Token response is invalid.")
    return payload


async def verify_id_token(id_token: str, config: OidcConfig, jwks_uri: str,
                          *, expected_nonce: str | None = None) -> dict[str, Any]:
    """Verify signature, issuer, audience, expiry and nonce with PyJWT/JWKS."""
    if not jwks_uri:
        raise ApiError(503, "OIDC_NOT_CONFIGURED", "JWKS URL is unavailable.")
    client = jwt.PyJWKClient(jwks_uri, timeout=config.http_timeout_seconds)
    try:
        signing_key = client.get_signing_key_from_jwt(id_token)
    except jwt.PyJWKClientConnectionError as exc:
        raise ApiError(503, "OIDC_JWKS_UNAVAILABLE", "JWKS endpoint unavailable.") from exc
    except jwt.PyJWTError as exc:
        raise ApiError(401, "OIDC_ID_TOKEN_KEY_UNKNOWN", "No matching signing key.") from exc
    try:
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=list(config.id_token_algorithms),
            audience=config.client_id,
            issuer=config.issuer,
            leeway=config.leeway_seconds,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise ApiError(401, "OIDC_INVALID_ID_TOKEN", "ID token verification failed.") from exc
    if not isinstance(claims, dict):
        raise ApiError(401, "OIDC_INVALID_ID_TOKEN", "ID token claims are invalid.")
    if claims.get("azp") and claims["azp"] != config.client_id:
        raise ApiError(401, "OIDC_INVALID_ID_TOKEN", "ID token authorized party mismatch.")
    if expected_nonce:
        nonce = claims.get("nonce")
        if not nonce:
            raise ApiError(401, "OIDC_NONCE_MISSING", "ID token is missing the nonce claim.")
        if not constant_time_equals(str(nonce), expected_nonce):
            raise ApiError(401, "OIDC_NONCE_MISMATCH", "ID token nonce mismatch.")
    return claims


def _claim_path(claims: Mapping[str, Any], path: str) -> Any:
    value: Any = claims
    for part in (part for part in path.split(".") if part):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def identity_from_claims(claims: Mapping[str, Any], config: OidcConfig) -> Identity:
    """Map verified claims to a server-side Identity; deny-by-default on gaps."""
    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise ApiError(401, "OIDC_SUB_MISSING", "ID token has no subject.")
    tenant_id = _claim_path(claims, config.tenant_claim)
    if not isinstance(tenant_id, (str, int)) or not str(tenant_id).strip():
        raise ApiError(403, "OIDC_TENANT_MISSING", "No tenant claim in the ID token.")
    roles_value = _claim_path(claims, config.roles_claim)
    if roles_value is None:
        for fallback in ("roles", "groups", "app_roles"):
            roles_value = _claim_path(claims, fallback)
            if roles_value is not None:
                break
    roles = normalize_roles(roles_value)
    if not roles:
        raise ApiError(403, "OIDC_NO_ROLES", "No recognized enterprise role in the ID token.")
    email = str(claims.get("email") or claims.get("preferred_username") or "").strip()
    return Identity(user_id=user_id, tenant_id=str(tenant_id).strip(),
                    roles=roles, email=email)


# --------------------------------------------------------------------------- callback

async def complete_authorization(request: Any, response: Any, *,
                                 config: OidcConfig | None = None,
                                 flow_store: AuthorizationFlowStore | None = None,
                                 client: httpx.AsyncClient | None = None) -> Identity:
    """Validate callback, exchange code, verify ID token, issue the app session."""
    config = config or OidcConfig.from_env()
    config.require()
    if request.query_params.get("error"):
        raise ApiError(401, "OIDC_CALLBACK_ERROR", "Identity provider rejected the login.")
    code = request.query_params.get("code", "").strip()
    state = request.query_params.get("state", "").strip()
    cookie_state = request.cookies.get(STATE_COOKIE, "").strip()
    if not code:
        raise ApiError(401, "OIDC_CALLBACK_INVALID", "Authorization code is missing.")
    validate_state(cookie_state, state)
    flow = (flow_store or get_flow_store()).consume(state)
    if flow is None or flow.expired():
        raise ApiError(401, "OIDC_STATE_EXPIRED", "Login flow expired or was already used.")
    metadata = await discover(config, client=client)
    tokens = await exchange_code(config, metadata, code, flow.code_verifier, client=client)
    id_token = tokens.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise ApiError(401, "OIDC_ID_TOKEN_MISSING", "Token response has no ID token.")
    claims = await verify_id_token(id_token, config, metadata.jwks_uri,
                                   expected_nonce=flow.nonce)
    identity = identity_from_claims(claims, config)
    issue_session(response, identity)
    cookie = CookieConfig.from_env()
    samesite = cast(Literal["lax", "strict", "none"], cookie.samesite)
    response.delete_cookie(STATE_COOKIE, path=cookie.path, domain=cookie.domain,
                           secure=cookie.secure, samesite=samesite)
    return identity


__all__ = [
    "STATE_COOKIE", "generate_state", "generate_nonce", "generate_pkce_verifier",
    "pkce_challenge", "generate_pkce_pair", "validate_state", "OidcConfig",
    "ProviderMetadata", "discover", "AuthorizationFlow", "AuthorizationFlowStore",
    "InMemoryAuthorizationFlowStore", "configure_flow_store", "get_flow_store",
    "build_authorization_url", "start_authorization", "exchange_code",
    "verify_id_token", "identity_from_claims", "complete_authorization",
]
