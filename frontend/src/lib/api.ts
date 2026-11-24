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
  user: string;
  role: UserRole;
  organization_id: string;
  project_id: string;
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
  policy_version: number;
  digest: string;
  source: { auto_approve_limit_idr: number; hard_cap_idr: number; vendors: string[] };
  approval_ttl_seconds: number;
  tool: { name: string; simulated: boolean };
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

export const ROLE_TOKENS: Record<string, string> = {
  operator: 'tok-operator',
  approver: 'tok-approver',
  admin: 'tok-admin',
  auditor: 'tok-auditor',
};

export function setAuthToken(token: string) {
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
  const csrf = csrfToken();
  if (csrf) headers.set('X-CSRF-Token', csrf);
  if (!headers.has('Authorization')) {
    const auth = defaultAuthHeader();
    if (auth) headers.set('Authorization', auth);
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

export function getExecutions(limit = 100) {
  return request<{ executions: ExecutionView[]; total: number }>(`/api/v1/executions?limit=${limit}`);
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

export function createTask(payload: Record<string, unknown>, idempotencyKey: string) {
  return request<ExecutionView>('/api/v1/tasks', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ task_type: 'invoice_review', payload }),
  });
}

export function decide(approvalId: string, decision: 'approve' | 'reject', reason: string) {
  return request<{ approval_id: string; status: string; execution: ExecutionView }>(
    `/api/v1/approvals/${approvalId}/decisions`,
    { method: 'POST', body: JSON.stringify({ decision, reason }) },
  );
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
  const email = me.email || `${me.user}@nexora.internal`;
  const local = email.split('@')[0];
  const name = personName(me.user || local);
  return {
    id: me.user,
    name,
    email,
    role: me.role,
    organizationId: me.organization_id,
    organizationName: 'Nexora Technologies',
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
    version: policy.policy_version,
    name: 'Harness Server Policy (enforced)',
    maxAutoAmountIdr: policy.source.auto_approve_limit_idr,
    allowedVendors: policy.source.vendors,
    restrictedTools: [policy.tool.name],
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
  const [events, receipt] = await Promise.all([
    getEvents(view.execution_id),
    view.receipt_id
      ? getReceipt(view.receipt_id).catch(() => null)
      : Promise.resolve(null),
  ]);
  return mapExecution(view, events.events, receipt);
}