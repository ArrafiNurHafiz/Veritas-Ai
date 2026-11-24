# Implementation, Testing and Deployment

**Status:** Proposed seven-day delivery plan; no implementation is implied.

Checklist pelaksanaan terurut dan kriteria selesai tersedia di [TODO implementasi](TODO.md).

## Hackathon delivery priority

The approved product positioning is enterprise governance with **Control Before Action**. The submission must first demonstrate that a protected action is stopped before execution, then provide a truthful audit trail and verification. The seven-day sequence below is a reference plan, not a claim that seven full days remain; replan against the actual deadline and team capacity.

| Priority | Deliverable | Completion evidence |
| --- | --- | --- |
| 1 | One procurement agent proposes a synthetic invoice action. | The operator can inspect the exact tool and arguments. |
| 2 | Harness validates policy and blocks pending or denied calls. | Automated checks and demo show the tool was not invoked. |
| 3 | Authorized approval binds the action and is revalidated. | Unauthorized, expired, changed and replayed approvals do not execute. |
| 4 | Allowed action updates simulated state once and emits a signed receipt. | Repeated request does not duplicate execution; tampering fails verification. |
| 5 | Present execution timeline and honest anchor status. | Pending or failed anchor is never displayed as verified. |
| 6 | Integrate private Besu and verified chain read-back if feasible. | A real confirmed anchor is independently checked; otherwise explicitly disclose that end-to-end anchoring is incomplete and do not claim the original full-chain acceptance criterion passed. |
| 7 | Demonstrate controlled outbound data using a local mock receiver. | A synthetic sensitive field or unapproved destination is denied before delivery; a compliant redacted payload is delivered once. |

Keep the five-service deployment, full organization administration, policy builder, additional agents and SDK as platform targets rather than allowing them to displace the core demo. A reduced topology is acceptable only if the harness remains the sole protected-tool invoker and security checks remain server-side. The original full MVP acceptance criteria remain in [PRD](01_PRD.md); the reduced demonstration does not satisfy the confirmed-anchor criterion until a real anchor is verified.

The organizer's [public schedule](https://tieglobalsummit.org/hackathon/) lists prototype submission through 30 November 2026. Confirm the actual submission deadline, timezone, eligibility, team rules, judging criteria and in-person requirements on the competition platform.

## Planned repository layout

- `frontend/`: Next.js landing and enterprise dashboard.
- `backend/`: FastAPI public BFF, identity, organizations, projects and task facade.
- `agent/`: FastAPI planning, provider abstraction and structured output schemas.
- `harness/`: FastAPI state machine, policy, fixed tool registry, approvals and evidence.
- `blockchain/`: FastAPI adapter, Solidity contract, Besu configuration and deployment scripts.
- `contracts/openapi/`: versioned API contracts.
- `infrastructure/`: Docker Compose, environment examples and CI scripts.
- `examples/procurement-agent/`: reproducible procurement example.

Each service should have a Dockerfile, dependency manifest, tests, README, environment example and health endpoints.

## Seven-day plan

| Day | Deliverable |
| --- | --- |
| 1 | Contracts, service skeletons, Compose, health checks, landing/dashboard shell and tenant auth fixtures. |
| 2 | Structured agent proposals, harness state machine, Task Center and deterministic demo fallback. |
| 3 | Deny-by-default policy, protected gateway, simulated invoice tool and approval lifecycle/UI. |
| 4 | Canonical receipts, hash chain, Ed25519 signing, key registry, timeline and tamper tests. |
| 5 | Private Besu and contract, anchor/verify adapter, durable retries and truthful anchor status. |
| 6 | Dashboard integration, Trust Explorer, contract tests, E2E cases and fault injection. |
| 7 | Security checks, deployment rehearsal, demo seed and recording, documentation and submission. |

## Definition of done

- Services start reproducibly in Compose; health checks and valid OpenAPI contracts are available.
- Task submission persists execution and returns 202; agent proposals are schema validated.
- Unknown tools and unauthorized actions are denied; approval cannot be bypassed.
- Receipts verify locally, tampering fails, and anchored hashes can be read back.
- Dashboard displays actual execution and anchor statuses, including loading, empty and error states.
- Automated tests pass; environment variables and migrations are documented; no secrets are embedded.
- Deliver README, environment examples, OpenAPI, seed script, migrations, tests, demo script, architecture diagram, threat model, verification instructions, screenshots, working demo URL, video and pitch materials.

## Test strategy

- **Unit:** amount boundaries 0, 5,000,000 and 5,000,001; negative and invalid amounts; vendor allowlist; policy default deny.
- **Integration:** backend–harness–agent contracts, approval races, idempotent execution and safe retry after timeout.
- **Cryptography:** deterministic canonicalization, key mismatch, altered payload, invalid signature and anchor mismatch.
- **E2E:** allowed, approval-required, approved and rejected cases; unknown tool; offline blockchain and recovery.
- **Security:** cross-tenant/project IDOR, role escalation, prompt injection, direct service bypass, secret leakage and replay.
- **Outbound data:** sensitive fixture, disallowed destination, unknown classification and policy outage produce zero mock deliveries; allowed redacted payload is delivered once. Check that receipts, logs and chain contain no raw sensitive payload. Test direct agent/provider network restrictions separately; report any uncovered path.
- **Smoke/load:** 20 concurrent tasks, stable transitions and no duplicate actions, if resources allow.

## Deployment and operations

Local deployment uses Compose, PostgreSQL, Besu and seeded synthetic data. Expose frontend and backend over HTTPS; keep Agent, Harness, Blockchain and Besu RPC internal. Inject model and signing keys from a secret manager; environment examples contain placeholders only. CI runs lint, type checks, unit and integration tests, OpenAPI validation and container builds.

Runbooks should cover correlation IDs, health checks, approval queues, anchor retries, signing-key rotation, backup and restore, and retention.

## Demo walkthrough

Show Nexora Technologies with Admin, Approver and Auditor; display four workforce cards with the three non-procurement agents labeled planned. Configure IDR 5,000,000 automatic limit, submit an IDR 8,500,000 invoice, show approval required, then demonstrate rejection and approval on separate executions. Verify a confirmed anchor and demonstrate failure on an altered exported receipt.

## Risks and mitigations

- Five services in one week: contract-first delivery, mocks and vertical slices.
- Besu configuration: implement local receipt verification first, then integrate anchoring behind an interface.
- LLM nondeterminism: constrained schemas and deterministic recorded fallback.
- Integrity is not truth: restrict claims to policy enforcement at the gateway and integrity of recorded evidence.
