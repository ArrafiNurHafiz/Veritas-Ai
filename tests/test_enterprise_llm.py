"""Tests for the enterprise LLM boundary. No external provider calls."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enterprise.llm import propose  # noqa: E402
from enterprise.tools import ToolDenied, ToolRegistry  # noqa: E402


class FakeResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


def llm_body(tool: str, arguments: dict) -> dict:
    import json

    return {"choices": [{"message": {"content": json.dumps({"tool": tool, "arguments": arguments})}}]}


class ToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

    def test_unknown_tool_denied(self):
        with self.assertRaises(ToolDenied):
            self.registry.validate("tenant-a", "wire_money", {})

    def test_invalid_amount_denied(self):
        with self.assertRaises(ToolDenied):
            self.registry.validate(
                "tenant-a",
                "approve_invoice",
                {"invoice_id": "INV-1", "amount_idr": -5, "vendor_id": "V-ABC"},
            )

    def test_valid_arguments_accepted(self):
        self.registry.validate(
            "tenant-a",
            "approve_invoice",
            {"invoice_id": "INV-1", "amount_idr": 1000, "vendor_id": "V-ABC"},
        )


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        self.payload = {"invoice_id": "INV-1", "amount_idr": 3_200_000, "vendor": "ABC"}

    def test_deterministic_fallback(self):
        result = propose(self.payload, tenant_id="tenant-a", registry=self.registry, base_url="")
        self.assertTrue(result.valid)
        self.assertEqual(result.planner, "deterministic")
        self.assertIsNotNone(result.arguments)
        self.assertEqual(result.arguments["vendor_id"], "V-ABC")  # type: ignore[index]

    def test_llm_unregistered_tool_is_denied(self):
        body = llm_body("wire_money", {"invoice_id": "INV-1"})
        with patch("enterprise.llm.httpx.post", return_value=FakeResponse(body)):
            result = propose(
                self.payload,
                tenant_id="tenant-a",
                registry=self.registry,
                base_url="http://llm.test/v1",
            )
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "UNKNOWN_TOOL")

    def test_llm_valid_proposal(self):
        body = llm_body(
            "approve_invoice",
            {"invoice_id": "INV-1", "amount_idr": 3_200_000, "vendor_id": "V-ABC"},
        )
        with patch("enterprise.llm.httpx.post", return_value=FakeResponse(body)):
            result = propose(
                self.payload,
                tenant_id="tenant-a",
                registry=self.registry,
                base_url="http://llm.test/v1",
            )
        self.assertTrue(result.valid)
        self.assertEqual(result.planner, "llm")


if __name__ == "__main__":
    unittest.main(verbosity=2)
