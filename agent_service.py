"""Local proposal-only procurement agent; it cannot invoke protected tools."""
import hmac
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, StrictInt
from typing import Annotated

app = FastAPI(title="VERITAS Procurement Agent")


class Invoice(BaseModel):
    invoice_id: str = Field(min_length=1)
    amount_idr: Annotated[StrictInt, Field(gt=0)]
    vendor: str = Field(min_length=1)


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.post("/internal/v1/proposals")
def proposal(invoice: Invoice, x_agent_token: str = Header(default="")) -> dict:
    token = os.environ.get("VERITAS_AGENT_TOKEN", "")
    if not token or not hmac.compare_digest(x_agent_token, token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    vendor = invoice.vendor if invoice.vendor.startswith("V-") else f"V-{invoice.vendor}"
    return {"proposal": {"tool": "approve_invoice", "arguments": {
        "invoice_id": invoice.invoice_id, "amount_idr": invoice.amount_idr, "vendor_id": vendor,
    }}}
