# Security and Trust Model

**Status:** Planned controls and acceptance criteria, not a completed security assessment.

## Assets and threats

Assets include signing keys, policy configuration, approval authority, receipt integrity, tenant data, protected tool credentials and anchoring identities.

Threat actors include malicious prompt authors, compromised agents or services, unauthorized dashboard users, malicious approvers and insiders modifying evidence. Attack surfaces include browser sessions, public and internal REST APIs, model output and tool arguments, PostgreSQL, Besu RPC and CI/CD.

Priority threats: cross-tenant access, role escalation, forged or replayed approval, prompt injection, direct tool bypass, compromised service credentials, receipt tampering and blockchain unavailability.

Outbound leakage is also in scope for the planned demo: a protected send tool checks final destination and payload against deterministic synthetic-data rules before calling a local mock receiver. Deny unknown classification and policy outages; bind the checked payload and destination to the decision. Raw sensitive payloads must not enter logs, receipts or chain.

This is not comprehensive DLP. Unmediated agent network traffic and AI-provider calls are outside this check unless separately controlled. Blockchain verifies recorded integrity, not confidentiality; predictable values may be guessed from ordinary hashes.

## Controls by boundary

| Boundary | Planned controls |
| --- | --- |
| Frontend | HttpOnly secure cookies, CSRF mitigation where applicable, CSP, accessible controls and no browser-bundled secrets. |
| Backend | Organization/project authorization on every object; request validation, throttling, audit logging and authenticated internal calls. Never proxy arbitrary agent-provided URLs. |
| Agent | No protected tool credentials or execution privileges; strict proposal schema; untrusted context handling. |
| Harness | Verify service identity and tenant scope; fixed allowlisted tools, deterministic default-deny policy, idempotency and approval revalidation. |
| Blockchain | Private RPC, permissioned writers, allowlisted anchor identity, contract access control and confirmation checks. |
| Evidence | Canonical JSON, SHA-256, Ed25519, hash chain, trusted public keys and separate signature/hash/anchor checks. |

All sensitive operations carry correlation IDs and audit events. Logs and receipt payloads exclude secrets and redact sensitive data. Inject keys at runtime; plan rotation, backup, recovery and retention.

## Approval and tool safeguards

Approval is bound to role, execution, tool, argument digest, policy digest and expiry. It cannot be replayed. On resume, check current policy and arguments again; enforce separation of duties where applicable. The agent cannot invoke arbitrary Python, shell, raw network calls, dynamic imports or tools outside the server-side registry.

Use only fictional Nexora Technologies data and synthetic invoices. The simulated tool changes sandbox invoice state and must not initiate a financial transfer.

## Verification semantics

- **Valid / verified:** trusted signature, canonical hash and confirmed on-chain anchor all match.
- **Pending:** a durable receipt exists but its anchor has not been confirmed.
- **Failed:** verification cannot establish required integrity, such as a mismatched signature or hash, untrusted key, or failed anchor.

Never display verified when the chain is unavailable, the receipt is altered or the signer is untrusted. Verification proves integrity and provenance of recorded evidence, not correctness of the business action or truth of source data. Public verification must redact personal information; only hashes are anchored.

## Security acceptance checklist

- Unknown tools are rejected; blocked tools are never invoked and credentials are unavailable to Agent.
- Approval is authorized, fresh, bound to unchanged arguments and protected against replay and races.
- One organization or project cannot read another's receipts or approvals.
- Keys are injected at runtime and absent from source and Git history.
- Offline blockchain leaves a durable pending receipt and never produces a false verified state.
- Policy changes, approvals and sensitive operations produce audit events and correlation IDs.
