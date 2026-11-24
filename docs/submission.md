# Submission pack — VERITAS AI

**Status: draft.** The hackathon rules, category and required fields are not yet confirmed
(T00.1 in [TODO](TODO.md)). Nothing here should be sent to an organizer until those rules
are checked. This file collects what already exists, what is missing, and the exact evidence
that can be re-run.

The product claim is narrow: **Control Before Action** — the Harness decides whether an
agent proposal or an outbound payload may run, records a signed receipt, and separates
"policy allowed" from "anchor confirmed". It is not a claim of full enterprise governance,
decentralized consensus, or market demand.

## Deliverable checklist

| Required by typical rules | State | Where |
| --- | --- | --- |
| Public repository | Ready | https://github.com/ArrafiNurHafiz/Veritas-Ai |
| Architecture description | Ready, labelled planned vs implemented | [System architecture](02_System_Architecture.md), [diagrams](architecture/README.md) |
| Run instructions | Ready and tested | [Root README](../README.md) |
| Demo URL | **Missing** — needs hosting/domain (T09.3) | — |
| Video / screenshots | **Missing** — not produced | — |
| Impact case | Drafted below, no invented market data | this file |
| Hackathon rules confirmation | **Open** — category, eligibility, team size, code rules | T00.1 |
| Final submission fields | **Open** — form not known | T00.2, T00.3 |

## Evidence snapshot (24 Nov 2026)

All commands run from the repository root with `.venv` installed:

| Check | Command | Observed |
| --- | --- | --- |
| Acceptance suite | `.venv/bin/python tests/test_demo.py` | 140 checks, all pass |
| Seed idempotency | `.venv/bin/python tests/test_seed.py` | 9 checks, all pass |
| OpenAPI drift | `.venv/bin/python tests/test_openapi.py` | 9 checks, all pass |
| Real HTTP end-to-end | `.venv/bin/python tests/test_e2e.py` | 36 checks against a real uvicorn process, all pass |
| Container | `docker compose up --build` | health check passes; email login and `/api/v1/me` verified inside the container |

`tests/test_e2e.py` starts real uvicorn processes and restarts them, so the restart-durability
claims below are exercised, not just asserted.

## Three-minute judge walkthrough

Prerequisite: `seed_demo.py` has been run against the demo database (or the demo database is
mounted). No wallet, chain, or external provider is required.

1. Open `/ui`, sign in as `marcus.vance@nexora.internal` / `demo123456` (operator).
2. Submit an invoice of `IDR 8,500,000` with vendor `ABC`. The execution page shows
   `WAITING_APPROVAL` and **zero tool calls**.
3. Sign in as `sarah.jenkins@nexora.internal` (approver) and approve with a reason. The
   execution becomes `SUCCEEDED`; a receipt is issued; the anchor is `pending`.
4. Open `/trust?receipt_id=<id>`: `Signature valid`, `Trusted key` and `Hash matches` show
   `PASS`, `Anchor confirmed` shows `FAIL`, and the overall verdict is `NOT VERIFIED` while
   the anchor is pending.
5. Confirm the mock anchor from the dashboard (admin) and verify again; only then does the
   anchor count as confirmed.
6. Post an outbound payload containing `api_key` to `mock://crm`: `DENY` with
   `SENSITIVE_FIELD`, and the mock receiver records zero calls.
7. Send a clean payload to `mock://crm`: `ALLOW`, `DELIVERED`. Inject
   `POST /internal/mock/receiver/failures {"remaining": 1}` and send another payload to show
   `FAILED`; replaying the same `Idempotency-Key` retries once and does not duplicate.

The operator/approver split is enforced by role, not by the UI alone: an operator token calling
the approve endpoint receives `403`.

## Impact case (bounded)

An agent can be wrong, manipulated, or simply over-scoped. This demo shows one concrete
control chain for a procurement invoice:

- The planner (deterministic or OpenAI-compatible) only **proposes**; unknown tools, malformed
  output, or prompt-injected invoice text cannot authorize anything. Evidence:
  `provider cannot pick an unregistered tool`, `malformed provider output falls back and still runs`
  in `tests/test_demo.py`.
- Above the policy limit, execution stops until a human with the right role decides; reject,
  expiry, replay and separation-of-duties violations produce zero tool calls.
- Outbound data is checked before a mock receiver sees it; sensitive fields and unknown
  destinations are denied, and denied sends are recorded as `SKIPPED`, not as delivered.
- Receipts are Ed25519-signed over canonical JSON; verification is independent of the demo UI
  and available unauthenticated at `/trust`. Anchor state is displayed separately, and
  `pending`/`failed` never verify.
- Delivery failure is distinct from policy failure: a receiver outage leaves the policy verdict
  `ALLOW` but `delivery_status=FAILED`, and retry is idempotent.

No claim is made about prevented losses, customer demand, or production readiness. The
supporting numbers are test counts and observed API responses, not market data.

## Claims: say / do not say

| Say | Do not say |
| --- | --- |
| "The Harness checks policy before the simulated tool runs." | "The agent is sandboxed at the network level." (No separate Agent service or network isolation: T02.3/T03.1.) |
| "Receipts are signed; the default anchor is a local mock." | "Anchored on Besu / decentralized consensus." (No Besu, contract, or confirmed chain anchor: T10.1–T10.3.) |
| "Harness-mediated egress is checked by fixed rules." | "Full DLP" or "all agent traffic is controlled." Provider calls and direct agent networking are uncovered. |
| "Pending or failed anchors are shown as not verified." | "The blockchain proves the data is true." The anchor proves a digest was recorded, not that the underlying claim is correct. |
| "Demo accounts are synthetic." | "Production identity / SSO / user management." |
| "SQLite, single process, one demo org." | "Multi-tenant enterprise deployment." |

## Still required before submission

1. Confirm hackathon rules and category (T00.1) — everything below depends on it.
2. Host the Harness over HTTPS with a domain, then re-run the E2E checklist against the public
   URL (T09.3).
3. Record the walkthrough above and capture screenshots that match the current UI (T09.4).
4. Freeze the commit used for the video and link it here.
5. Decide whether the separate Frontend service is part of the submitted demo; today `/ui` and
   `/trust` inside the Harness are the working surfaces.
6. Only if the rules require it: private Besu + deployed contract (T10.1) — currently blocked on
   infrastructure and not claimed.