# Product Requirements — VERITAS AI

**Status:** Planned MVP baseline, consolidated from specifications v1.0 and enterprise update v1.1 (23 November 2026).

## Product overview

VERITAS AI is an enterprise governance platform for organizations operating autonomous agents. Its primary promise is **Control Before Action**: an agent may propose a business action or outbound data transfer, but a protected tool must not run until an independent policy check and any required human approval have passed. Signed receipts and verifiable anchors support accountability after the action.

The prospective buyers are AI platform leads, security leads and CTOs; this buyer hypothesis is not yet validated. The demo's primary users are a procurement operator, an authorized approver and an auditor. Developers integrate agents but are not the primary product persona.

## BUILD 2036 positioning

- **Primary frontier:** Applied AI & Agentic Intelligence. Digital Infrastructure is a supporting thematic fit, not a confirmed second entry.
- **Submission positioning:** enterprise governance for agent actions and outbound data; cybersecurity and verifiable evidence support the AI-agent narrative.
- **Vision:** organizations operating many agents need enforceable boundaries over what those agents may do on their behalf.
- **Demo thesis:** an invoice action above a configured limit remains unexecuted until an authorized person approves that exact action and the harness revalidates it.
- **Evidence is supporting value:** a signed receipt and optional ledger anchor help verify recorded evidence; neither establishes that the model's decision or source data was correct.
- Track eligibility, judging criteria, team rules, submission time and timezone, and travel requirements require confirmation against organizer rules. [Official BUILD 2036 page](https://tieglobalsummit.org/hackathon/) lists submission 19–30 November 2026; verify any updates on the competition platform.

## Problem and outcomes

Agents can propose actions beyond their authority; prompts alone do not provide enforceable authorization or reliable audit evidence.

- **G1:** Demonstrate an end-to-end procurement scenario across five independently deployable services.
- **G2:** Prevent protected tool execution without authorization.
- **G3:** Independently verify evidence against a ledger anchor.

## Personas and journeys

| Persona | Journey |
| --- | --- |
| Developer | Register an agent and allowed tools; test policy in Playground; inspect contracts and receipts. |
| Organization admin | Configure the organization, members, agents and versioned policies. |
| Operator | Submit an invoice task and observe planning, decisions and results. |
| Approver | Review a pending request and approve or reject it with a reason. |
| Auditor | Inspect a receipt and verify its signature, hash and anchor. |

## Product surfaces

- Public: Home, Features, How It Works, Documentation and Get Started.
- Authenticated: Overview, AI Workforce, Task Center, Harness Playground, Policy Manager, Approval Center, Execution Monitor, Trust Explorer and Organization Settings.
- Procurement Agent is the only operational agent in the MVP. Finance, HR and Security agents must be labeled **planned**, not operational.

## MVP requirements

### P0 — hackathon demo critical path

The existing service boundaries remain the architectural target; five independently deployable services, a full policy builder and complete multi-tenant administration are not prerequisites for proving the demo thesis if they threaten delivery. Any reduced deployment must still preserve the trust boundary: only the harness invokes the protected simulated tool, and authorization is checked server-side. Do not represent a stub, bypass or simulated anchor as a live integration.

1. A company operator submits a synthetic invoice to one Procurement Agent and sees its proposed tool and arguments.
2. Harness validates the proposal and policy before invoking the simulated tool; unknown tools and invalid requests default to deny.
3. Amounts up to and including IDR 5,000,000 may be automatically allowed; amounts above the threshold require approval. Vendor and other policy constraints still apply.
4. A pending action cannot execute until an authorized human approves the exact bound action. Reject unauthorized or expired decisions and revalidate arguments and current policy before resuming.
5. An allowed action changes only simulated invoice state, idempotently; rejection and pending approval never invoke the tool.
6. Show a truthful execution timeline and a durable signed receipt. Verify the signature and receipt hash, and report the ledger anchor separately; an unconfirmed anchor is never verified.
7. Provide a reproducible demo, repository, architecture and documentation, following confirmed submission rules.
8. Demonstrate outbound-data policy: inspect destination and payload before a protected send tool runs. Block a designated synthetic sensitive field or a destination outside the allowlist; permit a compliant redacted payload to an allowed destination. Use a local mock receiver, not a real external service.

Outbound-data enforcement covers only harness-mediated paths. Direct agent networking, provider calls, credentials and other egress must be restricted separately or disclosed as uncovered. Production protection requires an OS/network-enforced boundary, not an application convention alone. Define deterministic demo rules and synthetic fields; do not claim comprehensive DLP.

### Enterprise platform target

The following remain target capabilities; demo-critical portions above take precedence over breadth.

1. Public landing page, documentation links, sign-in, dashboard and execution overview.
2. Organization-scoped users and RBAC: admin, operator, approver and auditor. Derive tenant context from the authenticated session.
3. Register agents and enable only catalogued tools. Policies are versioned per organization and scoped to the relevant project and agent.
4. Submit a task and generate a bounded, schema-valid tool proposal. The agent cannot execute protected tools.
5. Evaluate policy before any protected tool execution; default deny. For the demo policy, amounts up to and including IDR 5,000,000 may be automatically allowed; higher amounts require approval. Vendor allowlisting and other constraints still apply.
6. Persist pending approvals. Require an authorized human, bind approval to the request, and revalidate before resuming. Enforce separation of duties when configured.
7. Execute a simulated, idempotent `approve_invoice` tool with deterministic state; never transfer money.
8. Produce a canonical, signed receipt with event hashes, and anchor its SHA-256 digest to a private blockchain. Show anchor status as pending, confirmed or failed.
9. Provide a read-only Trust Explorer that independently checks signature, hash and anchor.
10. Publish OpenAPI contracts, health endpoints, structured logs and correlation IDs.

### P1 — if time permits

Python SDK adapter and CLI verification; SSE with polling fallback; a second example agent; multiple validator nodes.

## Acceptance scenarios

- **AC-01:** An allowed IDR 3,000,000 invoice produces a simulated approval, signed receipt and confirmed anchor.
- **AC-02:** An IDR 8,500,000 invoice requires approval; no protected call occurs before valid approval.
- **AC-03:** An unauthorized approval returns 403 and leaves the execution pending.
- **AC-04:** Unknown tools, invalid amounts, missing project access and expired approvals are denied.
- **AC-05:** A modified receipt fails signature or hash verification.
- **AC-06:** When blockchain is offline, the receipt remains durable and the anchor remains pending; the UI does not claim confirmation.
- **AC-07:** Reusing an idempotency key does not duplicate a protected action.
- **AC-08:** A prohibited destination or designated synthetic sensitive field is denied before the mock receiver is called; raw sensitive data does not appear in logs, receipt or chain.
- **AC-09:** A compliant redacted payload to an allowlisted destination reaches the mock receiver once; retry does not duplicate delivery.
- **AC-10:** Policy failure or unclassifiable data fails closed for the protected send tool. Direct agent/provider egress not controlled by the deployment is disclosed as a coverage gap.

## Demo and success measures

Seed fictional **Nexora Technologies** with demo users and synthetic data. Submit invoice `INV-2036-001` for IDR 8,500,000, show approval-required, then demonstrate rejection and approval on separate executions. Verify a confirmed anchor and show tamper detection.

In the demo, 100% of protected calls must traverse the gateway, with zero executions for denied or pending decisions. Provide reproducible allowed, approval-required and denied/tampered cases.

Show one blocked outbound transfer and one permitted redacted transfer to a local mock receiver. This demonstrates only the tested rules and mediated paths.

## Boundaries and open questions

- No cryptocurrency, coins, tokens, user wallets, live payments, vendor settlement, public token network, universal sandboxing or production compliance certification.
- Blockchain demonstrates recorded evidence integrity and provenance, not the correctness of AI reasoning or the truth of upstream data. A single-node demo does not demonstrate decentralized consensus.
- Blockchain does not provide confidentiality. Do not anchor plaintext sensitive data; ordinary hashes of predictable values can be guessed. Sensitive or low-entropy commitments require a reviewed design.
- Redact sensitive invoice fields in public audit views; use demo data only.
- Confirm hackathon eligibility and blockchain restrictions with the organizer; topical alignment is not formal approval.
