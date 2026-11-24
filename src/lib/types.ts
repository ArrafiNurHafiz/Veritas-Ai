export type UserRole = 'admin' | 'operator' | 'approver' | 'auditor';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  organizationId: string;
  organizationName: string;
  avatar: string;
}

export type ExecutionStatus = 
  | 'CREATED'
  | 'PLANNING'
  | 'POLICY_CHECK'
  | 'ALLOWED'
  | 'APPROVAL_REQUIRED'
  | 'WAITING_APPROVAL'
  | 'EXECUTING'
  | 'SUCCEEDED'
  | 'REJECTED'
  | 'DENIED'
  | 'FAILED';

export type AnchorStatus = 'NOT_REQUESTED' | 'PENDING' | 'CONFIRMED' | 'FAILED';

export interface ToolCallProposal {
  name: string;
  arguments: Record<string, unknown>;
  rationale?: string;
  confidence?: number;
}

export interface PolicyRule {
  id: string;
  version: number;
  name: string;
  maxAutoAmountIdr: number;
  allowedVendors: string[];
  restrictedTools: string[];
  requiredApproverRoles: UserRole[];
  defaultAction: 'DENY' | 'ALLOW';
  updatedAt: string;
  policyDigest: string;
}

export interface ExecutionEvent {
  id: string;
  timestamp: string;
  sequence: number;
  stage: ExecutionStatus;
  message: string;
  details?: Record<string, unknown>;
  digest: string;
}

export interface ExecutionReceipt {
  receiptVersion: string;
  receiptId: string;
  executionId: string;
  agentId: string;
  agentName: string;
  organizationId: string;
  tool: string;
  inputDigest: string;
  outputDigest: string;
  policyDigest: string;
  decision: 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED';
  actorId: string;
  actorRole: string;
  timestampUtc: string;
  outcome: 'SUCCEEDED' | 'REJECTED' | 'DENIED' | 'FAILED';
  correlationId: string;
  previousEventHash: string;
  canonicalJson: string;
  signature: string;
  keyId: string;
  receiptDigest: string;
  anchor: {
    chainId: string;
    blockNumber: number;
    txHash: string;
    status: AnchorStatus;
    confirmedAt?: string;
  };
}

export interface ExecutionRecord {
  id: string;
  taskId: string;
  agentId: string;
  agentName: string;
  taskType: string;
  instruction: string;
  payload: {
    invoiceId: string;
    vendor: string;
    amountIdr: number;
    description?: string;
  };
  status: ExecutionStatus;
  proposal?: ToolCallProposal;
  policyResult?: {
    decision: 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED';
    reason: string;
    thresholdIdr: number;
  };
  approval?: {
    id: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    decidedBy?: string;
    decidedRole?: UserRole;
    reason?: string;
    decidedAt?: string;
    expiresAt: string;
  };
  events: ExecutionEvent[];
  receipt?: ExecutionReceipt;
  createdAt: string;
  updatedAt: string;
  idempotencyKey: string;
}

export interface AgentInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  status: 'OPERATIONAL' | 'PLANNED';
  allowedTools: string[];
  totalExecutions: number;
  blockedCount: number;
}
