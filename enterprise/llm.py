"""LLM adapter. The model only proposes; the Harness still decides."""

from __future__ import annotations

from collections import deque
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from .agents import (
    agent_allows_tool,
    deterministic_agent_proposal,
    system_prompt_for_agent,
)
from .tools import ToolDenied, ToolRegistry

SYSTEM_PROMPT = system_prompt_for_agent("procurement-agent", "invoice_review")

MAX_PAYLOAD_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 20.0
_RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


class ProviderCircuitOpenError(RuntimeError):
    """Raised when repeated upstream failures tripped the circuit breaker."""


class _CircuitBreaker:
    """Thread-safe consecutive-failure circuit breaker per upstream URL."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[str, int] = {}
        self._opened_until: dict[str, float] = {}

    def _threshold(self) -> int:
        raw = os.environ.get("VERITAS_LLM_CB_THRESHOLD", "5").strip()
        try:
            return max(0, int(raw))
        except ValueError:
            return 5

    def _cooldown(self) -> float:
        raw = os.environ.get("VERITAS_LLM_CB_COOLDOWN_SECONDS", "30").strip()
        try:
            return max(1.0, float(raw))
        except ValueError:
            return 30.0

    def allow(self, key: str) -> bool:
        threshold = self._threshold()
        if threshold <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            until = self._opened_until.get(key, 0.0)
            if until > now:
                return False
            if until and until <= now:
                self._opened_until.pop(key, None)
                self._failures[key] = 0
            return True

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._opened_until.pop(key, None)

    def record_failure(self, key: str) -> None:
        threshold = self._threshold()
        if threshold <= 0:
            return
        now = time.monotonic()
        with self._lock:
            count = self._failures.get(key, 0) + 1
            self._failures[key] = count
            if count >= threshold:
                self._opened_until[key] = now + self._cooldown()

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._opened_until.clear()


class _TenantRateLimiter:
    """Sliding 60s window limiter per tenant before invoking remote LLM providers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, deque[float]] = {}

    def _limit(self) -> int:
        raw = os.environ.get("VERITAS_LLM_RPM_LIMIT", "0").strip()
        try:
            return max(0, int(raw))
        except ValueError:
            return 0

    def consume(self, tenant_id: str) -> bool:
        limit = self._limit()
        if limit <= 0:
            return True
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._windows.setdefault(tenant_id, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


_CIRCUIT_BREAKER = _CircuitBreaker()
_TENANT_RATE_LIMITER = _TenantRateLimiter()


def reset_llm_guards() -> None:
    """Reset in-memory LLM rate limiter and circuit breaker state (for tests)."""
    _CIRCUIT_BREAKER.reset()
    _TENANT_RATE_LIMITER.reset()


@dataclass(frozen=True)
class Proposal:
    tool: str | None
    arguments: dict[str, Any] | None
    planner: str
    error: str | None = None

    @property
    def valid(self) -> bool:
        return self.error is None and self.tool is not None and self.arguments is not None


def _strip_fences(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[-1]
        if value.endswith("```"):
            value = value[:-3]
    return value.strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from provider output, ignoring <think> blocks or prose."""
    cleaned = re.sub(r"<think>.*?</think>", "", _strip_fences(text), flags=re.DOTALL).strip()
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(cleaned):
        if ch == "{":
            try:
                parsed, _ = decoder.raw_decode(cleaned, idx)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    raise ValueError("INVALID_PROPOSAL")


def deterministic_proposal(
    payload: Mapping[str, Any],
    *,
    agent_id: str = "procurement-agent",
    task_type: str | None = None,
) -> Proposal:
    """Offline planner used when no LLM provider is configured."""
    tool, arguments, error = deterministic_agent_proposal(
        payload, agent_id=agent_id, task_type=task_type
    )
    return Proposal(tool, arguments, "deterministic", error)


def _post_chat_completion(
    url: str,
    headers: dict[str, str],
    request_body: dict[str, Any],
    timeout: float,
) -> Any:
    """Send chat completion request, retrying without response_format if unsupported (400/422)."""
    response = httpx.post(url, headers=headers, timeout=timeout, json=request_body)
    status = getattr(response, "status_code", 200)
    if status in (400, 422) and "response_format" in request_body:
        fallback_body = {k: v for k, v in request_body.items() if k != "response_format"}
        response = httpx.post(url, headers=headers, timeout=timeout, json=fallback_body)
    return response


def _call_provider(
    payload: Mapping[str, Any],
    base_url: str,
    model: str,
    timeout: float,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict[str, Any]:
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise ValueError("PAYLOAD_TOO_LARGE")
    endpoint_key = base_url.rstrip("/")
    if not _CIRCUIT_BREAKER.allow(endpoint_key):
        raise ProviderCircuitOpenError("PROVIDER_CIRCUIT_OPEN")

    headers = {"Content-Type": "application/json"}
    api_key = (
        os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("VERITAS_LLM_API_KEY", "").strip()
    )
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = os.environ.get("VERITAS_PUBLIC_URL", "http://localhost:3000")
        headers["X-Title"] = "VERITAS AI"

    request_body: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
        ],
    }
    if os.environ.get("VERITAS_LLM_JSON_MODE", "1").strip() in {"1", "true", "yes", "on"}:
        request_body["response_format"] = {"type": "json_object"}

    try:
        max_retries = max(0, int(os.environ.get("VERITAS_LLM_MAX_RETRIES", "1").strip() or "1"))
    except ValueError:
        max_retries = 1

    url = f"{endpoint_key}/chat/completions"
    last_exc: Exception | None = None
    response = None
    for attempt in range(max_retries + 1):
        try:
            response = _post_chat_completion(url, headers, request_body, timeout)
            status = getattr(response, "status_code", 200)
            if status in _RETRYABLE_STATUS_CODES and attempt < max_retries:
                time.sleep(min(2.0, 0.25 * (2**attempt)))
                continue
            response.raise_for_status()
            _CIRCUIT_BREAKER.record_success(endpoint_key)
            last_exc = None
            break
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(min(2.0, 0.25 * (2**attempt)))
                continue
        except Exception as exc:
            last_exc = exc
            break

    if last_exc is not None or response is None:
        _CIRCUIT_BREAKER.record_failure(endpoint_key)
        assert last_exc is not None
        raise last_exc

    try:
        envelope = response.json()
    except ValueError:
        envelope = _extract_json_object(response.text)
    content = envelope["choices"][0]["message"]["content"]
    return _extract_json_object(str(content))


def _validate_proposal_for_agent(
    *,
    tenant_id: str,
    agent_id: str,
    registry: ToolRegistry,
    tool: str,
    arguments: Mapping[str, Any],
    planner: str,
) -> Proposal:
    """Validate proposed tool against tenant registry first, then agent's bounded tool catalog."""
    normalized = dict(arguments)
    if tool in {"approve_invoice", "check_vendor_status"}:
        vendor_val = normalized.get("vendor_id")
        if isinstance(vendor_val, str) and vendor_val.strip() and not vendor_val.strip().startswith("V-"):
            normalized["vendor_id"] = f"V-{vendor_val.strip()}"
    try:
        registry.validate(tenant_id, tool, normalized)
    except ToolDenied as exc:
        return Proposal(None, None, planner, str(exc))
    if not agent_allows_tool(agent_id, tool):
        return Proposal(None, None, planner, "TOOL_NOT_ALLOWED_FOR_AGENT")
    return Proposal(tool, normalized, planner)


def _call_agent_service(
    *,
    agent_url: str,
    token: str,
    agent_id: str,
    task_type: str | None,
    payload: Mapping[str, Any],
    timeout: float,
) -> tuple[str, dict[str, Any], str]:
    """Request an untrusted proposal from the isolated Agent Service."""
    response = httpx.post(
        f"{agent_url.rstrip('/')}/internal/v1/agents/{agent_id}/proposals",
        headers={"X-Agent-Token": token},
        timeout=timeout,
        json={"task_type": task_type, "payload": dict(payload)},
    )
    response.raise_for_status()
    body = response.json()
    proposal = body.get("proposal")
    if not isinstance(proposal, dict):
        raise ValueError("INVALID_PROPOSAL")
    tool = proposal.get("tool")
    arguments = proposal.get("arguments")
    if not isinstance(tool, str) or not isinstance(arguments, dict):
        raise ValueError("INVALID_PROPOSAL")
    planner = str(body.get("planner") or "agent_service")
    return tool, dict(arguments), planner


def propose(
    payload: Mapping[str, Any],
    *,
    tenant_id: str,
    registry: ToolRegistry,
    agent_id: str = "procurement-agent",
    task_type: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
) -> Proposal:
    """Return a validated proposal. Provider output is never trusted as authorization."""
    agent_url = os.environ.get("VERITAS_AGENT_URL", "").strip().rstrip("/")
    if base_url is None and agent_url:
        token = os.environ.get("VERITAS_AGENT_TOKEN", "").strip()
        if not token:
            return Proposal(None, None, "agent_unavailable", "AGENT_UNAVAILABLE")
        if not _TENANT_RATE_LIMITER.consume(tenant_id):
            return Proposal(None, None, "rate_limited", "LLM_RATE_LIMITED")
        req_timeout = timeout or float(os.environ.get("VERITAS_LLM_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
        try:
            tool, arguments, planner = _call_agent_service(
                agent_url=agent_url,
                token=token,
                agent_id=agent_id,
                task_type=task_type,
                payload=payload,
                timeout=req_timeout,
            )
            return _validate_proposal_for_agent(
                tenant_id=tenant_id,
                agent_id=agent_id,
                registry=registry,
                tool=tool,
                arguments=arguments,
                planner=planner,
            )
        except Exception:
            return Proposal(None, None, "agent_unavailable", "AGENT_UNAVAILABLE")

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    endpoint = (
        base_url
        if base_url is not None
        else os.environ.get("VERITAS_LLM_BASE_URL", "").strip()
        or ("https://openrouter.ai/api/v1" if openrouter_key else "")
    )
    if not endpoint:
        fallback = deterministic_proposal(payload, agent_id=agent_id, task_type=task_type)
        if fallback.tool:
            return _validate_proposal_for_agent(
                tenant_id=tenant_id,
                agent_id=agent_id,
                registry=registry,
                tool=fallback.tool,
                arguments=fallback.arguments or {},
                planner="deterministic",
            )
        return fallback

    if not _TENANT_RATE_LIMITER.consume(tenant_id):
        return Proposal(None, None, "rate_limited", "LLM_RATE_LIMITED")

    resolved_model = (
        model
        or os.environ.get("OPENROUTER_MODEL", "").strip()
        or os.environ.get("VERITAS_LLM_MODEL", "").strip()
        or ("openai/gpt-4o-mini" if "openrouter.ai" in endpoint else "gpt-4o-mini")
    )
    prompt = system_prompt_for_agent(agent_id, task_type)
    try:
        parsed = _call_provider(
            payload,
            endpoint,
            resolved_model,
            timeout or float(os.environ.get("VERITAS_LLM_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))),
            system_prompt=prompt,
        )
        tool = parsed.get("tool")
        arguments = parsed.get("arguments")
        if not isinstance(tool, str) or not isinstance(arguments, dict):
            return Proposal(None, None, "llm", "INVALID_PROPOSAL")
        return _validate_proposal_for_agent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            registry=registry,
            tool=tool,
            arguments=arguments,
            planner="llm",
        )
    except ProviderCircuitOpenError:
        return Proposal(None, None, "llm_circuit_open", "PROVIDER_CIRCUIT_OPEN")
    except Exception:
        # Fail closed: a provider outage or malformed output must not authorize anything.
        fallback = deterministic_proposal(payload, agent_id=agent_id, task_type=task_type)
        if fallback.tool:
            try:
                registry.validate(tenant_id, fallback.tool, fallback.arguments or {})
            except ToolDenied as exc:
                return Proposal(None, None, "llm_fallback_denied", str(exc))
        return Proposal(None, None, "llm_fallback_denied", fallback.error or "PROVIDER_UNAVAILABLE")
