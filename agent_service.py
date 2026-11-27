"""Local proposal-only agent service; it cannot invoke protected tools."""
import hmac
import json
import os
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, StrictInt

from enterprise.agents import (
    deterministic_agent_proposal,
    get_agent,
    list_agent_specs,
    system_prompt_for_agent,
)
from enterprise.llm import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_PAYLOAD_BYTES,
    ProviderCircuitOpenError,
    _call_provider,
)

app = FastAPI(title="VERITAS Proposal Agent Service")


class Invoice(BaseModel):
    invoice_id: str = Field(min_length=1)
    amount_idr: Annotated[StrictInt, Field(gt=0)]
    vendor: str = Field(min_length=1)


class AgentTaskPayload(BaseModel):
    task_type: str | None = None
    payload: dict[str, Any]


def _require_agent_token(x_agent_token: str) -> None:
    token = os.environ.get("VERITAS_AGENT_TOKEN", "")
    if not token or not hmac.compare_digest(x_agent_token, token):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _llm_endpoint_and_model() -> tuple[str, str]:
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    endpoint = (
        os.environ.get("VERITAS_LLM_BASE_URL", "").strip()
        or ("https://openrouter.ai/api/v1" if openrouter_key else "")
    )
    model = (
        os.environ.get("OPENROUTER_MODEL", "").strip()
        or os.environ.get("VERITAS_LLM_MODEL", "").strip()
        or ("openai/gpt-4o-mini" if "openrouter.ai" in endpoint else "gpt-4o-mini")
    )
    return endpoint, model


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/internal/v1/agents")
def list_internal_agents(x_agent_token: str = Header(default="")) -> dict:
    _require_agent_token(x_agent_token)
    return {
        "agents": [
            {
                "agent_id": spec.agent_id,
                "name": spec.name,
                "version": spec.version,
                "status": spec.status,
                "default_task_type": spec.default_task_type,
                "task_types": list(spec.task_types),
                "tools": list(spec.tools),
            }
            for spec in list_agent_specs()
        ]
    }


@app.post("/internal/v1/proposals")
def proposal(invoice: Invoice, x_agent_token: str = Header(default="")) -> dict:
    _require_agent_token(x_agent_token)
    vendor = invoice.vendor if invoice.vendor.startswith("V-") else f"V-{invoice.vendor}"
    return {
        "proposal": {
            "tool": "approve_invoice",
            "arguments": {
                "invoice_id": invoice.invoice_id,
                "amount_idr": invoice.amount_idr,
                "vendor_id": vendor,
            },
        }
    }


@app.post("/internal/v1/agents/{agent_id}/proposals")
def agent_proposal(
    agent_id: str,
    body: AgentTaskPayload,
    x_agent_token: str = Header(default=""),
) -> dict:
    _require_agent_token(x_agent_token)
    spec = get_agent(agent_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_id}'")
    resolved_task = (body.task_type or spec.default_task_type).strip()
    if resolved_task not in spec.task_types:
        raise HTTPException(status_code=422, detail=f"INVALID_TASK_TYPE:{resolved_task}")
    if len(json.dumps(body.payload, separators=(",", ":")).encode()) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PAYLOAD_TOO_LARGE")

    endpoint, model = _llm_endpoint_and_model()
    if endpoint:
        timeout = float(os.environ.get("VERITAS_LLM_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
        prompt = system_prompt_for_agent(spec.agent_id, resolved_task)
        try:
            parsed = _call_provider(
                body.payload,
                endpoint,
                model,
                timeout,
                system_prompt=prompt,
            )
            tool = parsed.get("tool")
            arguments = parsed.get("arguments")
            if not isinstance(tool, str) or not isinstance(arguments, dict):
                raise HTTPException(status_code=422, detail="INVALID_PROPOSAL")
            return {
                "agent_id": spec.agent_id,
                "planner": "agent_service:llm",
                "proposal": {"tool": tool, "arguments": arguments},
            }
        except HTTPException:
            raise
        except ProviderCircuitOpenError as exc:
            raise HTTPException(status_code=503, detail="PROVIDER_CIRCUIT_OPEN") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="PROVIDER_UNAVAILABLE") from exc

    tool, arguments, error = deterministic_agent_proposal(
        body.payload,
        agent_id=spec.agent_id,
        task_type=resolved_task,
    )
    if error or tool is None or arguments is None:
        raise HTTPException(status_code=422, detail=error or "INVALID_PROPOSAL")
    return {
        "agent_id": spec.agent_id,
        "planner": "agent_service:deterministic",
        "proposal": {"tool": tool, "arguments": arguments},
    }
