"""Role-based access control and tenant/separation-of-duties checks.

All denials are :class:`~enterprise.auth.ApiError` 401/403 with a stable code.
These helpers operate on the server-derived :class:`Identity`; no client
input is trusted for role or tenant decisions.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, Request

from .auth import ApiError, Identity, constant_time_equals, current_identity

ROLES: frozenset[str] = frozenset({"operator", "approver", "admin", "auditor"})
APPROVAL_ROLES: frozenset[str] = frozenset({"approver", "admin"})


def normalize_roles(values: object) -> tuple[str, ...]:
    """Lowercase, de-duplicate and drop roles outside the canonical set."""
    if isinstance(values, str):
        values = tuple(part.strip() for part in values.split(",") if part.strip())
    if not isinstance(values, (tuple, list, set, frozenset)):
        return ()
    cleaned = (str(value).strip().lower() for value in values)
    return tuple(dict.fromkeys(role for role in cleaned if role in ROLES))


def has_role(identity: Identity, role: str) -> bool:
    return role.strip().lower() in {item.lower() for item in identity.roles}


def assert_role(identity: Identity, *roles: str) -> None:
    allowed = {role.strip().lower() for role in roles} if roles else set(ROLES)
    if not any(has_role(identity, role) for role in allowed):
        raise ApiError(
            403, "FORBIDDEN", "Role not permitted for this action.",
            {"required_roles": sorted(allowed)},
        )


def assert_tenant_access(identity: Identity, tenant_id: str) -> None:
    target = str(tenant_id or "").strip()
    if not target or not constant_time_equals(identity.tenant_id, target):
        raise ApiError(403, "TENANT_FORBIDDEN", "Resource belongs to another tenant.")


def assert_not_requester(actor_id: str, requester_id: str) -> None:
    """Separation of duties: the requester can never decide their own proposal."""
    actor, requester = str(actor_id or "").strip(), str(requester_id or "").strip()
    if not actor or not requester or constant_time_equals(actor, requester):
        raise ApiError(
            403, "SEPARATION_OF_DUTIES",
            "Requester cannot approve or reject their own proposal.",
            {"actor_id": actor, "requester_id": requester},
        )


def assert_approval_allowed(actor: Identity, requester_id: str, tenant_id: str,
                            *, roles: frozenset[str] = APPROVAL_ROLES) -> None:
    """Composite gate for an approval decision: role + tenant + SoD."""
    assert_role(actor, *sorted(roles))
    assert_tenant_access(actor, tenant_id)
    assert_not_requester(actor.user_id, requester_id)


def require_role(*roles: str) -> Callable[..., Identity]:
    """FastAPI dependency enforcing roles on the resolved session identity.

    ``require_role()`` with no arguments requires an authenticated session only.
    """

    def dependency(request: Request,
                   identity: Identity = Depends(current_identity)) -> Identity:
        assert_role(identity, *roles)
        request.state.identity = identity
        return identity

    return dependency


def require_tenant_access(tenant_id: str,
                          identity: Identity = Depends(current_identity)) -> Identity:
    """FastAPI dependency: bind ``tenant_id`` from the route's path/query param.

    Usage: ``def route(tenant_id: str, i=Depends(require_tenant_access))``.
    When the tenant comes from a loaded resource instead, call
    :func:`assert_tenant_access` inside the handler.
    """
    assert_tenant_access(identity, tenant_id)
    return identity


def require_tenant_in(tenant_id: str) -> Callable[..., Identity]:
    """Factory for a fixed tenant value not present in the request path."""

    def dependency(identity: Identity = Depends(current_identity)) -> Identity:
        assert_tenant_access(identity, tenant_id)
        return identity

    return dependency


__all__ = [
    "ROLES", "APPROVAL_ROLES", "normalize_roles", "has_role", "assert_role",
    "assert_tenant_access", "assert_not_requester", "assert_approval_allowed",
    "require_role", "require_tenant_access", "require_tenant_in",
]
