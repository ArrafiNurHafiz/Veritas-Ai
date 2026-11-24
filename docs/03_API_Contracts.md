# REST API and Data Contracts

**Status:** Proposed contract baseline; OpenAPI source files and generated clients are planned, not yet present. Enterprise v1.1 endpoint names take precedence.

## Conventions

- Public API: `/api/v1`; internal API: `/internal/v1`. JSON fields use `snake_case`; timestamps use RFC 3339 UTC; identifiers use UUIDv7 or UUID4 unless explicitly documented otherwise.
- Public requests require a session and tenant authorization except intentionally public, read-only verification routes. The backend derives `organization_id` from the session. Internal APIs require authenticated, audience-scoped service identity.
- State-changing POST requests use the `Idempotency-Key` header. Conflicting reuse returns 409. The v1.1 example's body-level `idempotency_key` is not the canonical contract here.
- Lists support `limit`, `cursor` and `next_cursor`. Validation errors and upstream failures must not expose stack traces.
- Canonical error envelope: `{"error":{"code":"POLICY_DENIED","message":"...","details":{}},"correlation_id":"..."}`. This resolves the original `trace_id` versus nested `correlation_id` inconsistency; tracing systems may additionally associate a trace ID with the correlation ID.
- Maintain OpenAPI 3.1 source of truth in `contracts/openapi`, publish each service's `/openapi.json`, validate contracts in CI and generate typed frontend clients.

## Public backend surface

| Method and route | Purpose |
| --- | --- |
| `POST /api/v1/auth/login` | Sign in and establish session (email/password or demo token). |
| `GET /api/v1/me` | Current identity. |
| `GET /api/v1/organizations/current` | Current organization. |
| `GET /api/v1/dashboard/summary` | Dashboard counts. |
| `GET, POST /api/v1/projects` | List or create projects. |
| `GET, POST /api/v1/agents` | List or register agents. |
| `POST /api/v1/tasks` | Submit a task; return 202. |
| `GET /api/v1/tasks/{id}` | Task status. |
| `GET /api/v1/executions/{id}` | Execution and anchor status. |
| `GET /api/v1/executions/{id}/events` | Execution timeline. |
| `GET, PUT /api/v1/policies/{id}` | Read or update an authorized policy. |
| `GET /api/v1/approvals` | List authorized pending approvals. |
| `POST /api/v1/approvals/{id}/decisions` | Approve or reject. |
| `GET /api/v1/receipts/{id}` | Read a redacted receipt. |
| `POST /api/v1/receipts/{id}/verify` | Verify a stored receipt. |
| `POST /api/v1/verify` | Verify a supplied receipt, including an altered export. |
| `GET /api/v1/audit/events` | Read authorized audit events. |

The public verification route, its access rules and its redaction policy must be specified before implementation. Do not assume all receipt endpoints are public.

### Task example

```http
POST /api/v1/tasks
Idempotency-Key: demo-inv-001
Content-Type: application/json
```

```json
{"agent_id":"procurement-agent","task_type":"invoice_review","payload":{"invoice_id":"INV-2036-001","vendor":"ABC","amount_idr":8500000}}
```

Response: `202 {"task_id":"...","execution_id":"...","status":"queued"}`. The sample agent ID is illustrative; production identifier format must follow the finalized schema. Project selection when an organization has multiple projects remains to be specified; it must be authorized server-side.

### Approval example

`POST /api/v1/approvals/{id}/decisions` with `{"decision":"approve","reason":"Reviewed","expected_version":3}`. Require the approver role, check pending state and version, record actor and time, and return 409 for conflicting or repeated decisions. Reject unauthorized users with 403.

### Verification example

```json
{"receipt_id":"...","signature_valid":true,"hash_matches":true,"anchor_status":"confirmed","anchor_matches":true,"verified":true}
```

`verified` is true only when all required checks pass and the signer is trusted. Pending or failed anchors are not verified. Verification does not establish decision correctness.

## Internal APIs

The planned outbound-data demonstration has no finalized endpoint or tool schema yet. Its contract must identify an allowlisted destination and the final payload, bind both to the policy decision and any approval, fail closed on unavailable policy or unknown classification, and prevent raw sensitive payloads from entering errors, logs or receipts. It targets a local mock receiver; provider requests and direct agent network access are outside this contract unless separately mediated. Do not treat this paragraph as an implemented API.

| Service | Method and route | Purpose |
| --- | --- | --- |
| Agent | `POST /internal/v1/plans` | Request structured tool proposals with allowed tool schemas. |
| Harness | `POST /internal/v1/executions` | Start workflow. |
| Harness | `GET /internal/v1/executions/{id}` | Read workflow state. |
| Harness | `POST /internal/v1/policies/evaluate` | Evaluate validated request deterministically. |
| Harness | `POST /internal/v1/approvals/{id}/decide` | Record role-checked decision. |
| Harness | `GET /internal/v1/receipts/{id}` | Read receipt. |
| Harness | `POST /internal/v1/receipts/verify` | Verify receipt. |
| Harness | `POST /internal/v1/executions/{id}/cancel` | Safely cancel. |
| Blockchain | `POST /internal/v1/anchors` | Submit hash and execution reference; return 202 and pending anchor ID. |
| Blockchain | `GET /internal/v1/anchors/{id}` | Read anchor status. |
| Blockchain | `POST /internal/v1/anchors/verify` | Compare hash to chain record. |

`/internal/v1/plans` is the selected Agent route; the architecture update's `/internal/v1/agents/plan` is superseded here. Each service exposes `/health/live` and `/health/ready`. Agent provider errors return explicit 502/503; invalid structured output returns 422.

Example proposal: `{"tool":"approve_invoice","arguments":{"invoice_id":"INV-001","amount_idr":8500000,"vendor_id":"V-ABC"}}`. Policy decision: `{"decision":"APPROVAL_REQUIRED","policy_version":1,"reason_code":"AMOUNT_LIMIT","execution_id":"..."}`. The precise mapping between the task's vendor field and the tool's vendor ID remains to be specified in OpenAPI.
