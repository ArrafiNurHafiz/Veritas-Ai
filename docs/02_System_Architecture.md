# System Architecture and Technical Design

**Status:** Planned architecture. The enterprise v1.1 update takes precedence over conflicting v1.0 wording.

## Architectural priority

**Control Before Action** is the primary product promise: the harness checks authorization before any protected tool invocation, and pending or denied actions cannot execute. Evidence and anchoring support subsequent verification. The five-service topology below is the architectural target; a smaller hackathon deployment may be used if it preserves the server-side harness and authorization boundary and labels all mocks accurately. This is a delivery option, not a claim that a reduced deployment has been implemented.

For the outbound-data demo, the harness also inspects the proposed destination and payload before a protected send tool can reach a local mock receiver. Apply explicit allowlist and deterministic synthetic-field rules; deny on an unknown classification or policy failure. Allowed data must be redacted before transmission. Bind the final destination and payload to the policy decision and any approval so they cannot be changed between check and send.

This protects only mediated paths. Restrict agent and tool networking and credentials at OS/network level in any deployment claiming enforcement; explicitly mark unmediated traffic, including model-provider requests, as outside the guarantee until separately controlled. Treat provider prompts and configuration as potential data egress; never assume the demo send-tool policy covers them.

## Service boundaries

| Service | Planned stack / port | Responsibility |
| --- | --- | --- |
| Frontend | Next.js / 3000 | Landing, dashboard and verification UI; calls only the backend. |
| Backend | FastAPI / 8000 | Public API/BFF, authentication, organization and project authorization, agent registration and tasks. |
| Agent | FastAPI / 8001 | LLM planning and structured proposals only; no protected-tool credentials. |
| Harness | FastAPI / 8002 | Policy, execution state machine, fixed tool gateway, approvals, receipts and anchor requests. |
| Blockchain adapter | FastAPI / 8003 | Authenticated anchoring and verification against private Besu JSON-RPC. |

PostgreSQL stores durable metadata. Services own their schemas; cross-service writes occur through APIs, not direct database writes. Backend owns users, organizations, memberships, agents and tasks; Harness owns policies, executions, approvals and receipts; Agent owns model configuration and transient planning metadata; Blockchain owns anchor references and chain connectivity.

## Trust boundaries and flow

Browser → Backend → Harness → Agent for planning; Harness evaluates the proposal and either denies, waits for approval, or invokes an allowlisted simulated tool. Harness signs a receipt and requests an anchor through Blockchain. Backend exposes execution and receipt status to the dashboard and Trust Explorer.

- Browser authentication uses a session or JWT with appropriate CSRF protection.
- Backend derives organization context from verified identity. Harness independently verifies internal service identity and organization scope.
- Internal services use mTLS or short-lived, audience-scoped credentials. Internal endpoints and Besu RPC are not publicly exposed.
- Agent must not have tool credentials, protected database write access or blockchain access. Restrict outbound networking where feasible.
- Policy uses validated structured fields and the server-side tool registry, never model assertions of authorization. Treat document content as untrusted.

## Execution and approval

```text
CREATED → PLANNING → POLICY_CHECK → ALLOWED → EXECUTING → SUCCEEDED | FAILED
                              ├→ DENIED
                              └→ APPROVAL_REQUIRED → WAITING_APPROVAL → POLICY_CHECK
```

Timeout and cancellation produce terminal states and receipts. Anchoring is independent: `NOT_REQUESTED → PENDING → CONFIRMED | FAILED`. An anchor failure does not retroactively turn a successful execution into a failed execution.

Policy contains version, organization/project and agent scope, allowed tools, amount limits, approver roles, expiry and argument constraints. Explicit deny rules take precedence; missing rules deny. The demo policy allows automatic approval up to IDR 5,000,000, requires approval above that limit and requires an allowlisted vendor.

An approval binds execution ID, tool, canonical argument hash, policy digest, requester and expiry. On resume, verify role, freshness, unchanged arguments and current policy. Prevent replay and enforce separation of duties where configured. Use optimistic concurrency for competing approval decisions.

## Evidence protocol

- Canonicalize JSON using RFC 8785 JCS or a precisely documented equivalent; hash UTF-8 bytes with SHA-256.
- Receipt fields include version, receipt and execution IDs, organization/project and agent IDs, tool, input and output digests, policy digest, decision, actor, UTC timestamp, outcome, correlation ID and previous event hash.
- Sign canonical receipt bytes excluding the signature field using Ed25519. Store key ID and rotation metadata separately; keep private keys in a secret manager.
- Anchor only the receipt digest. Never put invoices, PII, prompts or secrets on chain.
- Do not include raw sensitive payloads in logs, events or receipts. Hashes of predictable sensitive values can be guessed; assess commitment design, key management and access before persisting such values. Blockchain does not provide data confidentiality.
- Verification recomputes the canonical digest, verifies the signature against a trusted key and compares the anchor. Report each result separately.

This protocol establishes integrity and provenance of captured records, not factual correctness of model output or honesty of input data.

## Private blockchain

Use a private permissioned Hyperledger Besu network and a minimal authorized contract method `anchor(bytes32 receiptHash, bytes32 executionRef)` with a `ReceiptAnchored` event and duplicate handling. Infrastructure signing identities are not end-user wallets. A zero-price private configuration may still have internal EVM gas accounting; do not claim gas is nonexistent. A one-node MVP proves anchoring only; multiple validators are a stretch goal.

## Data and reliability

Core entities: organizations, users, memberships, projects, agents, policies, executions, tool calls, approvals, receipts, anchors and append-only events. Mutable resources carry organization ID and project ID where applicable. Executions and state-changing requests have idempotency keys; events record sequence and previous hash.

Use durable outbox/retry for anchors, bounded timeouts and exponential backoff only for safe or idempotent operations. Dead-letter failed anchors. Expose `/health/live` and dependency-aware `/health/ready`, structured JSON logs, correlation/trace IDs and metrics for latency, policy decisions, pending approvals, execution outcomes, anchor lag and verification failures.
