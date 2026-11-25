"""Tool registry. LLM output is untrusted data and must pass this boundary."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


class ToolDenied(ValueError):
    """Raised when a proposal names a tool or arguments that are not registered."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    required: tuple[str, ...]
    amount_field: str | None = None
    vendor_field: str | None = None


DEFAULT_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="approve_invoice",
        required=("invoice_id", "amount_idr", "vendor_id"),
        amount_field="amount_idr",
        vendor_field="vendor_id",
    ),
    ToolSpec(name="check_vendor_status", required=("vendor_id",), vendor_field="vendor_id"),
)


def _configured_tools() -> tuple[ToolSpec, ...]:
    raw = os.environ.get("VERITAS_TOOLS", "")
    if not raw.strip():
        return DEFAULT_TOOLS
    names = {item.strip() for item in raw.split(",") if item.strip()}
    return tuple(tool for tool in DEFAULT_TOOLS if tool.name in names)


class ToolRegistry:
    """Per-tenant allowlist of tools. Unknown tools are denied by construction."""

    def __init__(self, tools: tuple[ToolSpec, ...] | None = None) -> None:
        self._tools = {tool.name: tool for tool in (tools or _configured_tools())}
        self._tenant_tools: dict[str, set[str]] = {}

    def allow(self, tenant_id: str, tool_name: str) -> None:
        if tool_name not in self._tools:
            raise ToolDenied(f"unregistered tool: {tool_name}")
        self._tenant_tools.setdefault(tenant_id, set()).add(tool_name)

    def is_allowed(self, tenant_id: str, tool_name: str) -> bool:
        if tool_name not in self._tools:
            return False
        allowed = self._tenant_tools.get(tenant_id)
        if allowed is None:
            return tool_name in self._tools
        return tool_name in allowed

    def validate(self, tenant_id: str, tool_name: str, arguments: Mapping[str, Any]) -> None:
        spec = self._tools.get(tool_name)
        if spec is None:
            raise ToolDenied("UNKNOWN_TOOL")
        if not self.is_allowed(tenant_id, tool_name):
            raise ToolDenied("TOOL_NOT_ALLOWED_FOR_TENANT")
        if not isinstance(arguments, Mapping):
            raise ToolDenied("INVALID_ARGUMENTS")
        for key in spec.required:
            if key not in arguments:
                raise ToolDenied(f"MISSING_ARGUMENT:{key}")
        if spec.amount_field:
            amount = arguments[spec.amount_field]
            if type(amount) is not int or amount <= 0:
                raise ToolDenied("INVALID_AMOUNT")
        if spec.vendor_field:
            vendor = arguments[spec.vendor_field]
            if not isinstance(vendor, str) or not vendor.strip():
                raise ToolDenied("INVALID_VENDOR")
        invoice_id = arguments.get("invoice_id")
        if invoice_id is not None and (not isinstance(invoice_id, str) or not invoice_id.strip()):
            raise ToolDenied("INVALID_INVOICE_ID")
