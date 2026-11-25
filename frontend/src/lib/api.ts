import {
  AgentInfo,
  AnchorStatus,
  ExecutionEvent,
  ExecutionReceipt,
  ExecutionRecord,
  ExecutionStatus,
  PolicyRule,
  User,
  UserRole,
} from './types';
import { canonicalizeJson } from './canonical';

/**
 * Build-time mode switch. Demo remains the default; enterprise is opt-in.
 * NEXT_PUBLIC_* values are inlined into the client bundle and carry no secrets.
 */
export const VERITAS_MODE =
  (process.env.NEXT_PUBLIC_VERITAS_MODE || '').trim().toLowerCase() === 'enterprise'
    ? 'enterprise'
    : 'demo';
export const IS_ENTERPRISE = VERITAS_MODE === 'enterprise';
export const VERITAS_TEST_MODE = process.env.NEXT_PUBLIC_VERITAS_TEST_MODE === '1';
export const ENTERPRISE_AUTH_PATH = VERITAS_TEST_MODE
  ? '/api/v1/auth/test-login'
  : '/api/v1/auth/start';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);

export class ApiError extends Error {
  status: number;
  code: string;
  correlationId?: string;

  constructor(status: number, code: string, message: string, correlationId?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

interface MeResponse {
  user?: string;
  user_id?: string;
  role?: UserRole;
  roles?: UserRole[];
  organization_id?: string;
  tenant_id?: string;
  project_id?: string;
  email?: string;
}

interface ExecutionView {
  execution_id: string;
  status: string;
  organization_id: string;
  project_id: string;
  agent_id: string;
  task_type: string;
  payload?: { invoice_id?: string; amount_idr?: number; vendor?: string; description?: string };
  proposal: { tool: string; arguments: Record<string, unknown> } | null;
  decision: string | null;
  reason_code: string | null;
  tool_calls: number;
  receipt_id: string | null;
  approval_id: string | null;
  idempotency_key: string;
  actor: string | null;
  created_at: string;
  updated_at: string;
  anchor?: { status: string; tx_ref: string | null; attempts: number; last_error: string | null };
  replayed?: boolean;
}

interface EventView {
  seq: number;
  type: string;
  data: Record<string, unknown>;
  prev_hash: string;
  hash: string;
  created_at: string;
}

interface ReceiptView {
  receipt: Record<string, unknown>;
  signature: string;
  key_id: string;
  digest: string;
  anchor: { id: string; status: string; tx_ref: string | null } | null;
}

interface PolicyView {
  policy_version?: number;
  version?: number;
  digest: string;
  source: { auto_approve_limit_idr: number; hard_cap_idr?: number; vendors: string[] };
  approval_ttl_seconds?: number;
  tool?: { name: string; simulated?: boolean };
}

interface AgentView {
  agent_id: string;
  name: string;
  status: 'OPERATIONAL' | 'PLANNED';
  allowed_tools: string[];
  policy_version: number;
  executions: number;
}

export interface VerificationView {
  receipt_id: string | null;
  signature_valid: boolean;
  trusted_key: boolean;
  hash_matches: boolean;
  anchor_status: string;
  anchor_matches: boolean;
  verified: boolean;
}

function csrfToken(): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.split('; ').find((row) => row.startsWith('vt_csrf='));
  return match ? decodeURIComponent(match.slice('vt_csrf='.length)) : '';
}

function parseJson<T>(value: unknown, fallback: T): T {
  if (typeof value !== 'string') return (value as T) ?? fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

// The enterprise backend returns ORM rows (id/payload_json/data_json) while
// the demo API returns already-shaped views. Normalize here so the UI consumes
// one representation without fabricating any data.
function normalizeExecutionView(row: ExecutionView): ExecutionView {
  const raw = row as unknown as Record<string, unknown>;
  return {
    ...row,
    execution_id: (raw.execution_id as string) || (raw.id as string) || '',
    organization_id: (raw.organization_id as string) || (raw.tenant_id as string) || '',
    payload: parseJson(raw.payload_json, parseJson(raw.payload, {})),
    proposal: parseJson(raw.proposal_json, parseJson(raw.proposal, null)),
    decision: (raw.decision as string | null) ?? null,
    reason_code: (raw.reason_code as string | null) ?? null,
    tool_calls: Number(raw.tool_calls ?? 0),
    actor: (raw.actor as string | null) ?? null,
    created_at: (raw.created_at as string) || '',
    updated_at: (raw.updated_at as string) || '',
  };
}

function normalizeEventView(row: EventView): EventView {
  const raw = row as unknown as Record<string, unknown>;
  return {
    seq: Number(raw.seq ?? 0),
    type: (raw.type as string) || '',
    data: parseJson(raw.data_json, parseJson(raw.data, {})),
    prev_hash: (raw.prev_hash as string) || '',
    hash: (raw.hash as string) || '',
    created_at: (raw.created_at as string) || '',
  };
}

export const ROLE_TOKENS: Record<string, string> = {
  operator: 'tok-operator',
  approver: 'tok-approver',
  admin: 'tok-admin',
  auditor: 'tok-auditor',
};

export function setAuthToken(token: string) {
  if (IS_ENTERPRISE) {
    // Enterprise uses the server-side session cookie; never persist a bearer token.
    return;
  }
  if (typeof window !== 'undefined') {
    localStorage.setItem('veritas_token', token);
  }
}

function defaultAuthHeader(): string {
  if (typeof window === 'undefined') return '';
  const stored = localStorage.getItem('veritas_token');
  if (stored) return `Bearer ${stored}`;
  try {
    const userStr = localStorage.getItem('veritas_user');
    if (userStr) {
      const u = JSON.parse(userStr);
      if (u.role && ROLE_TOKENS[u.role]) return `Bearer ${ROLE_TOKENS[u.role]}`;
    }
  } catch {}
  return 'Bearer tok-admin';
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const isUnsafe = !SAFE_METHODS.has((init.method || 'GET').toUpperCase());
  const csrf = csrfToken();

  if (IS_ENTERPRISE) {
    // Session cookie only: strip any caller-supplied bearer token so a demo
    // persona can never reach the production backend, even by accident.
    headers.delete('Authorization');
    // Double-submit CSRF is required for every state-changing request.
    if (isUnsafe) {
      if (csrf) headers.set('X-CSRF-Token', csrf);
      else console.warn(`[veritas] vt_csrf cookie missing for ${init.method || 'GET'} ${path}`);
    }
  } else {
    if (csrf) headers.set('X-CSRF-Token', csrf);
    if (!headers.has('Authorization')) {
      const auth = defaultAuthHeader();
      if (auth) headers.set('Authorization', auth);
    }
  }

  const response = await fetch(path, { ...init, headers, credentials: 'include' });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = data?.error;
    throw new ApiError(
      response.status,
      error?.code || 'HTTP_ERROR',
      error?.message || `Request failed with status ${response.status}.`,
      data?.correlation_id,
    );
  }
  return data as T;
}

export function login(email: string, password: string) {
  return request<{ user: string; role: UserRole; csrf_token: string }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return request<{ status: string }>('/api/v1/auth/logout', { method: 'POST' });
}

export function getMe() {
  return request<MeResponse>('/api/v1/me');
}

export async function getExecutions(limit = 100) {
  const data = await request<{ executions: ExecutionView[]; total: number }>(
    `/api/v1/executions?limit=${limit}`
  );
  return IS_ENTERPRISE
    ? { ...data, executions: data.executions.map(normalizeExecutionView) }
    : data;
}

// The enterprise backend returns events embedded in the execution detail,
// rather than exposing the demo-only /events subresource.
export async function getExecution(executionId: string) {
  const data = await request<ExecutionView & { events: EventView[] }>(
    `/api/v1/executions/${executionId}`
  );
  return IS_ENTERPRISE
    ? { ...normalizeExecutionView(data), events: (data.events || []).map(normalizeEventView) }
    : data;
}

export function getEvents(executionId: string) {
  return request<{ events: EventView[] }>(`/api/v1/executions/${executionId}/events`);
}

export function getReceipt(receiptId: string) {
  return request<ReceiptView>(`/api/v1/receipts/${receiptId}`);
}

export function getPolicy() {
  return request<PolicyView>('/api/v1/policies');
}

export function getAgents() {
  return request<{ agents: AgentView[] }>('/api/v1/agents');
}

export async function createTask(payload: Record<string, unknown>, idempotencyKey: string) {
  const data = await request<ExecutionView>('/api/v1/tasks', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ task_type: 'invoice_review', payload }),
  });
  return IS_ENTERPRISE ? normalizeExecutionView(data) : data;
}

export async function decide(approvalId: string, decision: 'approve' | 'reject', reason: string) {
  const data = await request<{ approval_id: string; status: string; execution: ExecutionView }>(
    `/api/v1/approvals/${approvalId}/decisions`,
    { method: 'POST', body: JSON.stringify({ decision, reason }) },
  );
  return IS_ENTERPRISE
    ? { ...data, execution: normalizeExecutionView(data.execution) }
    : data;
}

export function verifySupplied(body: Record<string, unknown>) {
  return request<VerificationView>('/api/v1/verify', { method: 'POST', body: JSON.stringify(body) });
}

export function verifyStored(receiptId: string) {
  return request<VerificationView>(`/api/v1/receipts/${receiptId}/verify`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function updatePolicy(payload: {
  auto_approve_limit_idr: number;
  hard_cap_idr?: number;
  vendors?: string[];
}) {
  return request<PolicyView>('/api/v1/policies', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function resetDemo() {
  return request<{ status: string; executions: number; receipts: number; pending_approvals: number }>(
    '/api/v1/demo/reset',
    { method: 'POST', body: JSON.stringify({}) },
  );
}

const STATUS_MAP: Record<string, ExecutionStatus> = {
  CREATED: 'CREATED',
  POLICY_CHECK: 'POLICY_CHECK',
  WAITING_APPROVAL: 'WAITING_APPROVAL',
  ALLOWED: 'ALLOWED',
  EXECUTING: 'EXECUTING',
  SUCCEEDED: 'SUCCEEDED',
  REJECTED: 'REJECTED',
  DENIED: 'DENIED',
  EXPIRED: 'EXPIRED',
};

const DECISION_MAP: Record<string, 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED'> = {
  ALLOW: 'ALLOWED',
  ALLOWED: 'ALLOWED',
  APPROVAL_REQUIRED: 'APPROVAL_REQUIRED',
  DENY: 'DENIED',
  DENIED: 'DENIED',
};

export function mapStatus(status: string): ExecutionStatus {
  return STATUS_MAP[status] ?? 'FAILED';
}

export function mapDecision(decision: string | null): 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED' {
  return (decision && DECISION_MAP[decision]) || 'DENIED';
}

export function mapAnchorStatus(status: string | null | undefined): AnchorStatus {
  const value = (status || '').toLowerCase();
  if (value === 'confirmed') return 'CONFIRMED';
  if (value === 'pending') return 'PENDING';
  if (value === 'failed') return 'FAILED';
  return 'NOT_REQUESTED';
}

export function displayVendor(vendor: string): string {
  return vendor.startsWith('V-') ? vendor.slice(2) : vendor;
}

function personName(local: string): string {
  return local
    .split(/[._-]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function mapUser(me: MeResponse): User {
  const userId = me.user || me.user_id || '';
  const role = me.role || (Array.isArray(me.roles) ? me.roles[0] : undefined) || 'auditor';
  const email = me.email || `${userId}@idp.local`;
  const local = email.split('@')[0];
  const name = personName(userId || local);
  return {
    id: userId,
    name,
    email: me.email || (IS_ENTERPRISE ? '' : `${userId}@nexora.internal`),
    role,
    organizationId: me.organization_id || me.tenant_id || '',
    organizationName: me.organization_id || (IS_ENTERPRISE ? me.tenant_id || '' : 'Nexora Technologies'),
    avatar: name
      .split(' ')
      .map((part) => part.charAt(0))
      .join('')
      .slice(0, 2)
      .toUpperCase(),
  };
}

export function mapPolicy(policy: PolicyView): PolicyRule {
  return {
    id: 'harness-policy',
    version: policy.policy_version ?? policy.version ?? 1,
    name: 'Harness Server Policy (enforced)',
    maxAutoAmountIdr: policy.source.auto_approve_limit_idr,
    allowedVendors: policy.source.vendors,
    restrictedTools: policy.tool ? [policy.tool.name] : [],
    requiredApproverRoles: ['approver', 'admin'],
    defaultAction: 'DENY',
    updatedAt: new Date().toISOString(),
    policyDigest: policy.digest,
  };
}

export function mapAgents(agents: AgentView[], executions: ExecutionRecord[]): AgentInfo[] {
  return agents.map((agent) => ({
    id: agent.agent_id,
    name: agent.name,
    version: `policy-v${agent.policy_version}`,
    description: 'Proposal-only procurement agent; Harness validates and executes.',
    status: agent.status,
    allowedTools: agent.allowed_tools,
    totalExecutions: agent.executions,
    blockedCount: executions.filter(
      (exec) => exec.agentId === agent.agent_id && (exec.status === 'DENIED' || exec.status === 'REJECTED'),
    ).length,
  }));
}

function mapEvents(events: EventView[]): ExecutionEvent[] {
  return events.map((event) => {
    const data = event.data || {};
    const reason = typeof data.reason_code === 'string' ? ` — ${data.reason_code}` : '';
    return {
      id: `evt_${event.seq}`,
      timestamp: event.created_at,
      sequence: event.seq,
      stage: (event.type as ExecutionStatus) || 'CREATED',
      message: `${event.type.replaceAll('_', ' ').toLowerCase()}${reason}`,
      details: data,
      digest: event.hash,
    };
  });
}

function mapReceipt(view: ReceiptView): ExecutionReceipt {
  const body = view.receipt;
  const str = (key: string) => (typeof body[key] === 'string' ? (body[key] as string) : '');
  return {
    receiptVersion: String(body.version ?? '1'),
    receiptId: str('receipt_id'),
    executionId: str('execution_id'),
    agentId: str('agent_id'),
    agentName: 'Procurement Agent',
    organizationId: str('organization_id'),
    tool: str('tool'),
    inputDigest: str('input_digest'),
    outputDigest: '',
    policyDigest: str('policy_digest'),
    decision: mapDecision(str('decision')),
    actorId: str('actor'),
    actorRole: 'harness',
    timestampUtc: str('created_at'),
    outcome: str('outcome') as ExecutionReceipt['outcome'],
    correlationId: str('correlation_id'),
    previousEventHash: str('previous_event_hash'),
    canonicalJson: canonicalizeJson(body),
    signature: view.signature,
    keyId: view.key_id,
    receiptDigest: view.digest,
    anchor: {
      chainId: 'evm-json-rpc',
      txHash: view.anchor?.tx_ref ?? '',
      status: mapAnchorStatus(view.anchor?.status),
    },
  };
}

export function mapExecution(
  view: ExecutionView,
  events: EventView[],
  receipt: ReceiptView | null,
): ExecutionRecord {
  const payload = view.payload || {};
  const args = view.proposal?.arguments || {};
  const arguedAmount = args.amount_idr;
  const rawVendor =
    typeof payload.vendor === 'string'
      ? payload.vendor
      : typeof args.vendor_id === 'string'
        ? args.vendor_id
        : '';
  const decision = mapDecision(view.decision);
  const mappedEvents = mapEvents(events);
  const approvedEvent = events.find((event) => event.type === 'APPROVED');
  const rejectedEvent = events.find((event) => event.type === 'REJECTED');
  const approved = approvedEvent
    ? mappedEvents.find((event) => event.sequence === approvedEvent.seq)
    : undefined;
  const rejected = rejectedEvent
    ? mappedEvents.find((event) => event.sequence === rejectedEvent.seq)
    : undefined;

  let approval: ExecutionRecord['approval'];
  if (view.approval_id) {
    const decided = approved || rejected;
    const decidedData = decided?.details || {};
    const status =
      approved ? 'APPROVED' : rejected ? 'REJECTED' : view.status === 'EXPIRED' ? 'EXPIRED' : 'PENDING';
    approval = {
      id: view.approval_id,
      status,
      decidedBy: typeof decidedData.approver === 'string' ? decidedData.approver : undefined,
      reason: typeof decidedData.reason === 'string' ? decidedData.reason : undefined,
      decidedAt: decided?.timestamp,
      expiresAt: '',
    };
  }

  return {
    id: view.execution_id,
    taskId: view.idempotency_key,
    agentId: view.agent_id,
    agentName: 'Procurement Agent',
    taskType: view.task_type,
    instruction: `Review supplier invoice ${payload.invoice_id ?? ''} from ${displayVendor(rawVendor)}.`,
    payload: {
      invoiceId: typeof payload.invoice_id === 'string' ? payload.invoice_id : String(args.invoice_id ?? ''),
      vendor: displayVendor(rawVendor),
      amountIdr: typeof payload.amount_idr === 'number' ? payload.amount_idr : Number(arguedAmount ?? 0),
      description: typeof payload.description === 'string' ? payload.description : '',
    },
    status: mapStatus(view.status),
    proposal: view.proposal
      ? {
          name: view.proposal.tool,
          arguments: view.proposal.arguments,
        }
      : undefined,
    policyResult: {
      decision,
      reason: view.reason_code || 'NO_REASON',
    },
    approval,
    events: mappedEvents,
    receipt: receipt ? mapReceipt(receipt) : undefined,
    createdAt: view.created_at,
    updatedAt: view.updated_at,
    idempotencyKey: view.idempotency_key,
  };
}

export async function hydrateExecution(view: ExecutionView): Promise<ExecutionRecord> {
  if (IS_ENTERPRISE) {
    // Enterprise keeps events on the execution detail; never fall back to
    // demo fixtures when that read fails.
    const [detail, receipt] = await Promise.all([
      getExecution(view.execution_id),
      view.receipt_id
        ? getReceipt(view.receipt_id).catch(() => null)
        : Promise.resolve(null),
    ]);
    return mapExecution(view, detail.events || [], receipt);
  }
  const [events, receipt] = await Promise.all([
    getEvents(view.execution_id),
    view.receipt_id
      ? getReceipt(view.receipt_id).catch(() => null)
      : Promise.resolve(null),
  ]);
  return mapExecution(view, events.events, receipt);
}