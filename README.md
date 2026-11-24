# VERITAS AI — Harness slice

Working vertical slice of the P0 demo path described in `docs/`: **Control Before Action**.
One service (`veritas_harness.py`), SQLite, deterministic planner (no LLM), simulated
`approve_invoice` tool, Ed25519 receipts, local mock anchor (optional dev-EVM adapter), and an outbound-data gate to a
local mock receiver.

Status: Harness backend and its embedded demo UI exist. The Next.js app under
`frontend/` is present but still renders mock data; a separate Backend or Agent
service does not exist. Anchoring defaults to a local mock; an optional JSON-RPC
adapter can submit the digest to a dev EVM node, but no Besu network or contract
is deployed.

## Run

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tests/test_demo.py          # 138 acceptance checks, no framework
.venv/bin/python tests/test_e2e.py           # 36 checks against a real uvicorn process
.venv/bin/python tests/test_seed.py          # 9 seed checks
.venv/bin/python tests/test_openapi.py       # contract snapshot (use --write after an intended API change)
.venv/bin/python seed_demo.py                # Nexora demo dataset (idempotent)
.venv/bin/uvicorn veritas_harness:app --port 8002
```

Schema changes are versioned in `MIGRATIONS` and recorded in `schema_migrations`;
importing the module applies pending steps once and is safe to repeat.

## Demo credentials (dev defaults, override with `VERITAS_TOKENS`)

| Token | Role |
| --- | --- |
| `tok-operator` | operator |
| `tok-approver` | approver |
| `tok-admin` | admin |
| `tok-auditor` | auditor |

Send as `Authorization: Bearer <token>`. Internal routes use `X-Internal-Token`
(default `dev-internal`, override with `VERITAS_INTERNAL_TOKEN`).

## Run with a container

```sh
docker compose up --build -d
docker compose run --rm harness python seed_demo.py   # optional demo dataset
curl -s 127.0.0.1:8002/health/ready
```

The image runs as UID 10001 with the SQLite file on the `veritas-data` volume.
Override `VERITAS_CORS_ORIGINS`, `VERITAS_TOKENS`, `VERITAS_INTERNAL_TOKEN` and
`VERITAS_LOG_JSON` through the environment. This is still an HTTP demo: TLS,
network isolation and a reverse proxy belong to deployment, not this file.

## Separate frontend contract

The frontend runs on another origin. Set the allowlist (comma-separated, no
wildcard because credentials are sent):

```sh
export VERITAS_CORS_ORIGINS=http://localhost:3000
```

- `POST /api/v1/auth/login` accepts either demo credentials
  (`{"email":"marcus.vance@nexora.internal","password":"demo123456"}`) or a demo
  token (`{"token":"tok-operator"}`), returning `{user, role, csrf_token,
  expires_in}` plus `vt_session` + `vt_csrf` cookies. Sessions are server-side
  rows; only their hashes are stored. `POST /api/v1/auth/logout`,
  `GET /api/v1/me` (adds `email` for email logins).
- Demo email accounts use the frontend personas: `alexa.chen@nexora.internal`
  (admin), `sarah.jenkins@nexora.internal` (approver),
  `marcus.vance@nexora.internal` (operator), `dr.rachel.k@nexora.internal`
  (auditor). Override the password with `VERITAS_DEMO_PASSWORD` and the whole
  map with `VERITAS_ACCOUNTS`; these are synthetic accounts, not a user store.
- Session TTL is `VERITAS_SESSION_TTL_SECONDS` (default 12 hours); logout and
  expiry both stop cookie authentication. Set `VERITAS_COOKIE_SECURE=1` behind
  HTTPS and `VERITAS_COOKIE_SAMESITE` for cross-site deployments. Five failed
  logins per credential per minute answer `429 RATE_LIMITED` (in-process, per
  worker).
- Cookie-authenticated mutations must send `X-CSRF-Token` matching the `vt_csrf`
  cookie and the active session, otherwise `403 CSRF_REQUIRED`. Bearer requests
  need no CSRF header.
- Read models for the dashboard: `GET /api/v1/executions?status=&limit=&offset=`,
  `GET /api/v1/dashboard/summary`, `GET /api/v1/policies`, `GET /api/v1/agents`.
  Approval rows carry `execution.proposal` so the approver view does not need a
  second request.
- `POST /api/v1/anchors/{id}/confirm` is admin-only (bearer or cookie+CSRF); the
  `X-Internal-Token` route stays for service-to-service use.
- Error envelope `{"error":{"code","message","details"},"correlation_id"}`; every
  response carries `X-Correlation-ID`.
- Anchor `pending` never verifies. Only `confirmed` yields `verified=true`.
- Execution anchor view: `{status, tx_ref, attempts, last_error}`; `submitted` is still
  not verified until read-back confirms.

## Flow in 6 requests

Or open `http://localhost:8002/ui` and sign in with a demo token — the dashboard
covers submit, approve/reject, timeline, receipt verification, mock anchor confirm
and the outbound-data gate. Demo UI is embedded in the Harness (the separate
Frontend service from `docs/` is still pending); cookie session + double-submit CSRF.
`http://localhost:8002/trust` verifies a receipt without login, by ID or pasted JSON.

```sh
# 1. Operator submits an over-limit invoice -> WAITING_APPROVAL, zero tool calls
curl -s localhost:8002/api/v1/tasks -H 'Authorization: Bearer tok-operator' \
  -H 'Idempotency-Key: demo-inv-001' -H 'Content-Type: application/json' \
  -d '{"task_type":"invoice_review","payload":{"invoice_id":"INV-2036-001","amount_idr":8500000,"vendor":"ABC"}}'

# 2. Approver approves the bound action -> SUCCEEDED, receipt issued
curl -s localhost:8002/api/v1/approvals/<approval_id>/decisions \
  -H 'Authorization: Bearer tok-approver' -H 'Content-Type: application/json' \
  -d '{"decision":"approve","reason":"Reviewed","expected_version":1}'

# 3. Auditor verifies signature + hash; anchor is still pending -> verified=false
curl -s -X POST localhost:8002/api/v1/receipts/<receipt_id>/verify -H 'Authorization: Bearer tok-auditor'

# 4. Confirm the mock anchor, then verify again -> verified=true
curl -s -X POST localhost:8002/internal/v1/anchors/<anchor_id>/confirm -H 'X-Internal-Token: dev-internal'

# 5. Outbound data: sensitive field -> DENY, mock receiver records zero calls
curl -s localhost:8002/api/v1/egress/send -H 'Authorization: Bearer tok-operator' \
  -H 'Idempotency-Key: egress-1' -H 'Content-Type: application/json' \
  -d '{"destination":"mock://crm","payload":{"name":"Nexora","api_key":"sk-live-secret"}}'

# 6. Inspect mock receiver calls
curl -s localhost:8002/internal/mock/receiver/calls -H 'X-Internal-Token: dev-internal'
```

## Policy (deterministic, version 1)

- Auto-allow `approve_invoice` when `amount_idr <= 5,000,000` and vendor is `V-ABC`/`V-XYZ`.
- Above that, up to `25,000,000` → `APPROVAL_REQUIRED`; above → deny. Unknown tool/vendor → deny.
- Approval binds execution, argument hash and policy version; reject/expiry/replay produce zero tool calls.
- Token carries `org`/`project`; cross-org execution, event and receipt reads return `404`, and approval lists are filtered by scope.
- Egress allowlist `mock://crm`, `mock://ledger`; fields `customer_secret`, `api_key`, `card_number` are denied.
- Delivery outcome is recorded separately from the policy verdict (`DELIVERED`, `FAILED`, `SKIPPED`);
  replaying a failed idempotency key retries delivery and never delivers twice. The mock receiver can be
  failed on purpose with `POST /internal/mock/receiver/failures {"remaining": n}`.

## Demo dataset

`seed_demo.py` writes the Nexora story through the real API: one auto-allowed and
executed invoice with a confirmed anchor, one approved-then-executed invoice with a
pending anchor, one invoice still waiting for the live approval decision, one denied
by the hard cap, one denied by vendor allowlist, one blocked egress (sensitive field)
and one delivered redacted egress. Re-running is safe; fixed idempotency keys replay.

```sh
.venv/bin/python seed_demo.py && .venv/bin/uvicorn veritas_harness:app --port 8002
```

Schema changes are versioned in `MIGRATIONS` and recorded in `schema_migrations`;
importing the module applies pending steps once and is safe to repeat.

## Planner

Default: deterministic (`plan_task`), no key needed. Optional OpenAI-compatible model:

```sh
export VERITAS_LLM_BASE_URL=https://api.example.com/v1
export VERITAS_LLM_API_KEY=...
export VERITAS_LLM_MODEL=gpt-4o-mini
```

Model output is untrusted data: `proposal_error` + `evaluate` deny malformed or
unregistered proposals, and a model-proposed amount above the limit still needs
human approval. Provider failure or missing config falls back to the deterministic
planner; the chosen path is recorded in the `PROPOSAL` event (`planner` field).

## Anchoring

Default anchor is a local row: `pending` until an admin confirms it (or the internal
token route does). Public verification never treats `pending` as verified.

Optional single-node EVM adapter (no contract, digest goes in tx calldata):

```sh
export VERITAS_ANCHOR_RPC_URL=http://localhost:8545
export VERITAS_ANCHOR_FROM=0x...   # funded, node-managed account
curl -s -X POST localhost:8002/internal/v1/anchors/sweep -H 'X-Internal-Token: dev-internal'
```

On issuance the Harness tries one `eth_sendTransaction`; success stores the tx hash
(`submitted`), failure keeps the anchor `pending` with `last_error` while the receipt
stays durable. `sweep` retries pending anchors and confirms `submitted` ones only
when `eth_getTransactionByHash` returns matching calldata; a mismatch becomes
`failed`. While the adapter is configured, manual confirm returns `409 ANCHOR_MODE`.
This is one dev node: it proves the client and read-back logic, not consensus.

## Observability and keys

- `GET /health/live`, `GET /health/ready`; every response carries `X-Correlation-ID`.
- Request bodies above `VERITAS_MAX_BODY_BYTES` (default 65536) are rejected with `413`
  before routing. The check trusts the declared `Content-Length`; chunked bodies are not measured.
- `GET /metrics` (Prometheus text) requires `X-Internal-Token`. It exposes request
  counters plus execution, denial, tool-call, receipt, anchor and approval gauges.
- `VERITAS_LOG_JSON=1` turns each request into one JSON line (method, path, status,
  duration, correlation ID) on stdout.
- `VERITAS_SIGNING_SEED` (64 hex chars) injects the Ed25519 seed instead of the
  SQLite-stored one; restarting with the same seed keeps the same `key_id`.
- `docs/openapi.json` is the frozen contract; `tests/test_openapi.py` fails when the
  app changes without regenerating it.

## Honest limits

- Anchor is a local mock by default; the optional EVM adapter writes the digest as tx
  calldata on one dev node — no contract, no consensus proof.
- Only Harness-mediated egress is checked. Provider calls and direct agent networking are uncovered.
- The LLM adapter is exercised against a fake OpenAI-compatible server only; no real model or
  provider has been tested, and injection behaviour through one remains unproven.
- Rule-based egress checks are not DLP.
- SQLite single connection, single process; org scope comes from the token, but the demo
  UI and egress table remain single-org.
- No streaming/body-as-you-read cap: the 413 check uses the declared length, so a malicious
  client that omits `Content-Length` is not stopped by it.
