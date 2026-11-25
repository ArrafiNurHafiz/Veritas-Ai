'use client';

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { User, AgentInfo, PolicyRule, ExecutionRecord, UserRole, ExecutionStatus, ExecutionEvent } from './types';
import { DEMO_USERS, INITIAL_AGENTS, INITIAL_POLICY, INITIAL_EXECUTIONS } from './mockData';
import { canonicalizeJson, computeSha256 } from './crypto';
import * as api from './api';

interface AppContextType {
  currentUser: User;
  setCurrentUser: (user: User) => void;
  setUserRole: (role: UserRole) => void;
  agents: AgentInfo[];
  policy: PolicyRule;
  updatePolicy: (updated: Partial<PolicyRule>) => Promise<void>;
  executions: ExecutionRecord[];
  syncError: string | null;
  refreshExecutions: () => Promise<void>;
  submitTask: (data: {
    agentId: string;
    invoiceId: string;
    vendor: string;
    amountIdr: number;
    description?: string;
  }) => Promise<ExecutionRecord>;
  decideApproval: (
    executionId: string,
    decision: 'APPROVED' | 'REJECTED',
    reason: string
  ) => Promise<void>;
  resetToDefault: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

function readStored<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

// Neutral placeholders for enterprise: identity, role and policy data must
// come from the session/backend, never from the demo fixtures below.
const ENTERPRISE_USER: User = {
  id: '',
  name: 'Session user',
  email: '',
  role: 'auditor',
  organizationId: '',
  organizationName: '',
  avatar: 'SU',
};

const ENTERPRISE_POLICY: PolicyRule = {
  ...INITIAL_POLICY,
  version: 0,
  maxAutoAmountIdr: 0,
  allowedVendors: [],
  restrictedTools: [],
  policyDigest: '',
  updatedAt: '',
};

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User>(() =>
    api.IS_ENTERPRISE ? ENTERPRISE_USER : readStored('veritas_user', DEMO_USERS[0]));
  const [agents, setAgents] = useState<AgentInfo[]>(api.IS_ENTERPRISE ? [] : INITIAL_AGENTS);
  const [policy, setPolicy] = useState<PolicyRule>(() =>
    api.IS_ENTERPRISE ? ENTERPRISE_POLICY : readStored('veritas_policy', INITIAL_POLICY));
  const [executions, setExecutions] = useState<ExecutionRecord[]>(
    () => api.IS_ENTERPRISE ? [] : readStored('veritas_executions', INITIAL_EXECUTIONS),
  );
  const [syncError, setSyncError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  useEffect(() => () => { mountedRef.current = false; }, []);

  const reportEnterpriseError = useCallback((scope: string, err: unknown) => {
    const detail = err instanceof Error ? err.message : String(err);
    console.error(`[veritas] enterprise ${scope} failed: ${detail}. No demo fallback will be used.`, err);
    if (mountedRef.current) setSyncError(`${scope}: ${detail}`);
  }, []);

  // Shared by first mount and manual refresh. Demo behaviour is unchanged.
  const loadFromBackend = useCallback(async () => {
    if (api.IS_ENTERPRISE) {
      let failed = false;
      const fail = (scope: string, err: unknown) => {
        failed = true;
        reportEnterpriseError(scope, err);
      };
      try {
        const [meRes, policyRes, execsRes] = await Promise.allSettled([
          api.getMe(),
          api.getPolicy(),
          api.getExecutions(50),
        ]);

        // Identity is authoritative in the backend session. Some enterprise
        // deployments do not expose /me, so this is advisory only.
        if (meRes.status === 'fulfilled') {
          if (mountedRef.current) setCurrentUser(api.mapUser(meRes.value));
        } else {
          console.warn('[veritas] identity endpoint unavailable; backend session remains authoritative.', meRes.reason);
        }

        if (policyRes.status === 'fulfilled') {
          if (mountedRef.current) setPolicy(api.mapPolicy(policyRes.value));
        } else {
          fail('policy load', policyRes.reason);
        }

        if (execsRes.status === 'fulfilled') {
          const records = await Promise.all(
            execsRes.value.executions.map(async (view) => {
              try {
                return await api.hydrateExecution(view);
              } catch (err) {
                fail('execution detail', err);
                return null;
              }
            }),
          );
          if (mountedRef.current) {
            const valid = records.filter((record): record is ExecutionRecord => record !== null);
            setExecutions(valid);
            // No demo agent fixtures in enterprise; the backend owns agents.
            setAgents(api.mapAgents([], valid));
          }
        } else {
          fail('execution load', execsRes.reason);
        }
        if (mountedRef.current && !failed) setSyncError(null);
      } catch (err) {
        fail('backend sync', err);
      }
      return;
    }

    // Demo: local Harness API with the original offline fallback semantics.
    try {
      const [policyRes, execsRes] = await Promise.all([
        api.getPolicy().catch(() => null),
        api.getExecutions(50).catch(() => null),
      ]);
      if (!mountedRef.current) return;

      if (policyRes) {
        setPolicy(api.mapPolicy(policyRes));
      }

      if (execsRes && Array.isArray(execsRes.executions) && execsRes.executions.length > 0) {
        const hydrated = await Promise.all(
          execsRes.executions.map((e) => api.hydrateExecution(e).catch(() => null))
        );
        const valid = hydrated.filter((e): e is ExecutionRecord => e !== null);
        if (valid.length > 0 && mountedRef.current) {
          setExecutions(valid);
        }
        const agentsRes = await api.getAgents().catch(() => null);
        if (agentsRes && mountedRef.current) {
          setAgents(api.mapAgents(agentsRes.agents, valid));
        }
      }
    } catch {
      // Local backend not reachable, keep local state
    }
  }, [reportEnterpriseError]);

  useEffect(() => {
    // Defer the async sync so no state is set synchronously in the effect body.
    void Promise.resolve().then(loadFromBackend);
  }, [loadFromBackend]);

  // Demo only: persist the local sandbox view. Enterprise uses server sessions.
  useEffect(() => {
    if (api.IS_ENTERPRISE) return;
    try {
      localStorage.setItem('veritas_user', JSON.stringify(currentUser));
      localStorage.setItem('veritas_executions', JSON.stringify(executions));
      localStorage.setItem('veritas_policy', JSON.stringify(policy));
    } catch {
      // LocalStorage error ignore
    }
  }, [currentUser, executions, policy]);

  const refreshExecutions = async () => {
    await loadFromBackend();
  };

  const setUserRole = (role: UserRole) => {
    if (api.IS_ENTERPRISE) {
      console.warn('[veritas] demo role switching is disabled in enterprise mode; roles come from the IdP.');
      return;
    }
    const target = DEMO_USERS.find((u) => u.role === role) || {
      ...currentUser,
      role,
    };
    setCurrentUser(target);
    const token = api.ROLE_TOKENS[role] || 'tok-admin';
    api.setAuthToken(token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('veritas_user', JSON.stringify(target));
    }
    // Refresh executions under the new role scope
    refreshExecutions();
  };

  const updatePolicy = async (updated: Partial<PolicyRule>): Promise<void> => {
    // Roles are asserted by the backend from the IdP identity in enterprise.
    if (!api.IS_ENTERPRISE && currentUser.role !== 'admin') {
      throw new api.ApiError(
        403,
        'FORBIDDEN',
        `Role "${currentUser.role}" cannot modify policy rules. Only Admin (Alexa Chen) has policy authority.`
      );
    }

    const next = {
      ...policy,
      ...updated,
    };

    try {
      const live = await api.updatePolicy({
        auto_approve_limit_idr: next.maxAutoAmountIdr,
        vendors: next.allowedVendors,
      });
      const mapped = api.mapPolicy(live);
      setPolicy({ ...mapped, name: next.name, updatedAt: new Date().toISOString() });
      return;
    } catch (err) {
      if (err instanceof api.ApiError && (err.status === 403 || err.status === 401 || err.status === 422)) {
        throw err;
      }
      if (api.IS_ENTERPRISE) {
        reportEnterpriseError('policy update', err);
        throw err;
      }
      // Backend unavailable: keep the offline demo deterministic.
    }

    setPolicy({
      ...next,
      version: next.version + 1,
      updatedAt: new Date().toISOString(),
    });
  };

  const submitTask = async (data: {
    agentId: string;
    invoiceId: string;
    vendor: string;
    amountIdr: number;
    description?: string;
  }): Promise<ExecutionRecord> => {
    if (!api.IS_ENTERPRISE && currentUser.role === 'auditor') {
      throw new api.ApiError(
        403,
        'FORBIDDEN',
        'Auditors have read-only access and cannot submit procurement tasks. Switch to Operator or Admin.'
      );
    }

    // Attempt dispatch to real live Harness Gateway
    try {
      const idempKey = 'idemp_' + Math.random().toString(36).substring(2, 10);
      const created = await api.createTask(
        {
          invoice_id: data.invoiceId,
          amount_idr: data.amountIdr,
          vendor: data.vendor,
          description: data.description,
        },
        idempKey,
      );
      if (created && created.execution_id) {
        const fullRecord = await api.hydrateExecution(created);
        setExecutions((prev) => [fullRecord, ...prev]);
        return fullRecord;
      }
    } catch (err) {
      if (err instanceof api.ApiError && (err.status === 403 || err.status === 401)) {
        throw err;
      }
      if (api.IS_ENTERPRISE) {
        reportEnterpriseError('task submission', err);
        throw err;
      }
      // Backend not running or call failed; proceed to local deterministic fallback below
    }

    const execId = 'exec_' + Math.random().toString(36).substring(2, 9);
    const now = new Date().toISOString();
    const isOverLimit = data.amountIdr > policy.maxAutoAmountIdr;
    const isVendorAllowed = policy.allowedVendors.includes(data.vendor);

    // Initial created record
    const newExec: ExecutionRecord = {
      id: execId,
      taskId: 'task_' + Math.random().toString(36).substring(2, 8),
      agentId: data.agentId,
      agentName: 'Procurement Agent',
      taskType: 'invoice_review',
      instruction: `Review and evaluate supplier invoice ${data.invoiceId} from ${data.vendor} for IDR ${data.amountIdr.toLocaleString()}.`,
      payload: {
        invoiceId: data.invoiceId,
        vendor: data.vendor,
        amountIdr: data.amountIdr,
        description: data.description || 'Enterprise procurement automated task submission.',
      },
      status: isOverLimit || !isVendorAllowed ? 'WAITING_APPROVAL' : 'SUCCEEDED',
      proposal: {
        name: 'approve_invoice',
        arguments: {
          invoice_id: data.invoiceId,
          amount_idr: data.amountIdr,
          vendor: data.vendor,
        },
        rationale: isOverLimit
          ? `Invoice amount IDR ${data.amountIdr.toLocaleString()} exceeds automatic limit of IDR ${policy.maxAutoAmountIdr.toLocaleString()}.`
          : 'Invoice strictly matches contract schedule and is within automatic policy limits.',
        confidence: 0.99,
      },
      policyResult: {
        decision: isOverLimit || !isVendorAllowed ? 'APPROVAL_REQUIRED' : 'ALLOWED',
        reason: isOverLimit
          ? `AMOUNT_LIMIT: Amount IDR ${data.amountIdr.toLocaleString()} exceeds automatic limit of IDR ${policy.maxAutoAmountIdr.toLocaleString()}.`
          : 'POLICY_PERMITTED: Invoice amount within auto-approval ceiling and vendor allowed.',
        thresholdIdr: policy.maxAutoAmountIdr,
      },
      events: [
        {
          id: 'evt_' + Math.random().toString(36).substring(2, 7),
          timestamp: now,
          sequence: 1,
          stage: 'CREATED',
          message: 'Task received by Veritas Backend and dispatched to Harness Runtime.',
          digest: '0x' + Math.random().toString(36).substring(2, 10),
        },
        {
          id: 'evt_' + Math.random().toString(36).substring(2, 7),
          timestamp: now,
          sequence: 2,
          stage: 'PLANNING',
          message: 'Agent returned structured tool call proposal for approve_invoice.',
          digest: '0x' + Math.random().toString(36).substring(2, 10),
        },
        {
          id: 'evt_' + Math.random().toString(36).substring(2, 7),
          timestamp: now,
          sequence: 3,
          stage: 'POLICY_CHECK',
          message: `Deterministic policy evaluated: ${isOverLimit ? 'APPROVAL_REQUIRED' : 'ALLOWED'}.`,
          digest: '0x' + Math.random().toString(36).substring(2, 10),
        },
      ],
      createdAt: now,
      updatedAt: now,
      idempotencyKey: 'idemp_' + Math.random().toString(36).substring(2, 10),
    };

    if (isOverLimit || !isVendorAllowed) {
      newExec.approval = {
        id: 'appr_' + Math.random().toString(36).substring(2, 8),
        status: 'PENDING',
        expiresAt: new Date(Date.now() + 86400000).toISOString(),
      };
      newExec.events.push({
        id: 'evt_' + Math.random().toString(36).substring(2, 7),
        timestamp: now,
        sequence: 4,
        stage: 'WAITING_APPROVAL',
        message: 'Execution held at Policy Gate; pending authorized human sign-off.',
        digest: '0x' + Math.random().toString(36).substring(2, 10),
      });
    } else {
      // Auto-approved & executed
      const canonicalReceiptObj = {
        actor_id: 'harness_runtime_01',
        actor_role: 'system_harness',
        agent_id: data.agentId,
        correlation_id: 'corr_' + Math.random().toString(36).substring(2, 8),
        decision: 'ALLOWED',
        execution_id: execId,
        input_digest: '0x' + Math.random().toString(36).substring(2, 18),
        organization_id: 'org_nexora_tech',
        outcome: 'SUCCEEDED',
        output_digest: '0x' + Math.random().toString(36).substring(2, 18),
        policy_digest: policy.policyDigest,
        previous_event_hash: '0x0000000000000000000000000000000000000000000000000000000000000000',
        receipt_id: 'rcpt_' + Math.random().toString(36).substring(2, 12),
        receipt_version: '1.0.0',
        timestamp_utc: now,
        tool: 'approve_invoice',
      };
      const canonicalJson = canonicalizeJson(canonicalReceiptObj);
      const digest = await computeSha256(canonicalJson);

      newExec.receipt = {
        receiptVersion: '1.0.0',
        receiptId: canonicalReceiptObj.receipt_id,
        executionId: execId,
        agentId: data.agentId,
        agentName: 'Procurement Agent',
        organizationId: 'org_nexora_tech',
        tool: 'approve_invoice',
        inputDigest: canonicalReceiptObj.input_digest,
        outputDigest: canonicalReceiptObj.output_digest,
        policyDigest: policy.policyDigest,
        decision: 'ALLOWED',
        actorId: 'harness_runtime_01',
        actorRole: 'system_harness',
        timestampUtc: now,
        outcome: 'SUCCEEDED',
        correlationId: canonicalReceiptObj.correlation_id,
        previousEventHash: canonicalReceiptObj.previous_event_hash,
        canonicalJson,
        signature: '0x' + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
        keyId: 'harness-ed25519-v1',
        receiptDigest: digest,
        anchor: {
          chainId: 'besu_private_1337',
          blockNumber: 10485,
          txHash: '0x' + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
          status: 'CONFIRMED',
          confirmedAt: now,
        },
      };

      newExec.events.push(
        {
          id: 'evt_' + Math.random().toString(36).substring(2, 7),
          timestamp: now,
          sequence: 4,
          stage: 'EXECUTING',
          message: 'Tool approve_invoice executed in isolated sandbox gateway.',
          digest: '0x' + Math.random().toString(36).substring(2, 10),
        },
        {
          id: 'evt_' + Math.random().toString(36).substring(2, 7),
          timestamp: now,
          sequence: 5,
          stage: 'SUCCEEDED',
          message: 'Canonical signed receipt anchored to Besu block #10485.',
          digest: digest,
        }
      );
    }

    setExecutions((prev) => [newExec, ...prev]);
    return newExec;
  };

  const decideApproval = async (
    executionId: string,
    decision: 'APPROVED' | 'REJECTED',
    reason: string
  ): Promise<void> => {
    if (!api.IS_ENTERPRISE && currentUser.role !== 'approver' && currentUser.role !== 'admin') {
      throw new api.ApiError(
        403,
        'FORBIDDEN',
        `Role "${currentUser.role}" is not authorized to sign approvals. Only Approvers (Sarah Jenkins) and Admins (Alexa Chen) can decide approvals.`
      );
    }

    // Attempt dispatch to real live Harness Gateway
    const targetItem = executions.find((e) => e.id === executionId);
    if (api.IS_ENTERPRISE && !targetItem?.approval?.id) {
      const err = new Error(`No approval id is available for execution ${executionId}.`);
      reportEnterpriseError('approval decision', err);
      throw err;
    }
    if (targetItem?.approval?.id && !targetItem.approval.id.startsWith('appr_')) {
      try {
        const decidedRes = await api.decide(
          targetItem.approval.id,
          decision === 'APPROVED' ? 'approve' : 'reject',
          reason
        );
        if (decidedRes?.execution) {
          const fullRecord = await api.hydrateExecution(decidedRes.execution);
          setExecutions((prev) => prev.map((item) => (item.id === executionId ? fullRecord : item)));
          return;
        }
      } catch (err) {
        if (err instanceof api.ApiError && (err.status === 403 || err.status === 401)) {
          throw err;
        }
        if (api.IS_ENTERPRISE) {
          reportEnterpriseError('approval decision', err);
          throw err;
        }
        // Backend not running; fallback to local state update below
      }
    }

    const now = new Date().toISOString();
    setExecutions((prev) =>
      prev.map((item) => {
        if (item.id !== executionId) return item;

        const isApproved = decision === 'APPROVED';
        const updatedStatus: ExecutionStatus = isApproved ? 'SUCCEEDED' : 'REJECTED';

        const updatedEvents: ExecutionEvent[] = [
          ...item.events,
          {
            id: 'evt_' + Math.random().toString(36).substring(2, 7),
            timestamp: now,
            sequence: item.events.length + 1,
            stage: updatedStatus,
            message: `Approver ${currentUser.name} (${currentUser.role}) decided ${decision}: ${reason}`,
            digest: '0x' + Math.random().toString(36).substring(2, 10),
          },
        ];

        let receipt = item.receipt;
        if (isApproved) {
          const canonicalReceiptObj = {
            actor_id: currentUser.id,
            actor_role: currentUser.role,
            agent_id: item.agentId,
            correlation_id: 'corr_appr_' + Math.random().toString(36).substring(2, 8),
            decision: 'APPROVAL_REQUIRED',
            execution_id: item.id,
            input_digest: '0x' + Math.random().toString(36).substring(2, 18),
            organization_id: 'org_nexora_tech',
            outcome: 'SUCCEEDED',
            output_digest: '0x' + Math.random().toString(36).substring(2, 18),
            policy_digest: policy.policyDigest,
            previous_event_hash: '0x0000000000000000000000000000000000000000000000000000000000000000',
            receipt_id: 'rcpt_' + Math.random().toString(36).substring(2, 12),
            receipt_version: '1.0.0',
            timestamp_utc: now,
            tool: item.proposal?.name || 'approve_invoice',
          };
          const canonicalJson = canonicalizeJson(canonicalReceiptObj);
          
          receipt = {
            receiptVersion: '1.0.0',
            receiptId: canonicalReceiptObj.receipt_id,
            executionId: item.id,
            agentId: item.agentId,
            agentName: item.agentName,
            organizationId: 'org_nexora_tech',
            tool: item.proposal?.name || 'approve_invoice',
            inputDigest: canonicalReceiptObj.input_digest,
            outputDigest: canonicalReceiptObj.output_digest,
            policyDigest: policy.policyDigest,
            decision: 'APPROVAL_REQUIRED',
            actorId: currentUser.id,
            actorRole: currentUser.role,
            timestampUtc: now,
            outcome: 'SUCCEEDED',
            correlationId: canonicalReceiptObj.correlation_id,
            previousEventHash: canonicalReceiptObj.previous_event_hash,
            canonicalJson,
            signature: '0x' + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
            keyId: 'harness-ed25519-v1',
            receiptDigest: '0x99a8b7c6d5e4f3a2b1c09876543210abcdef0123456789abcdef0123456789ab',
            anchor: {
              chainId: 'besu_private_1337',
              blockNumber: 10486,
              txHash: '0x' + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
              status: 'CONFIRMED',
              confirmedAt: now,
            },
          };
        }

        return {
          ...item,
          status: updatedStatus,
          approval: {
            id: item.approval?.id || 'appr_decided',
            status: isApproved ? 'APPROVED' : 'REJECTED',
            decidedBy: currentUser.name,
            decidedRole: currentUser.role,
            reason: reason,
            decidedAt: now,
            expiresAt: item.approval?.expiresAt || now,
          },
          events: updatedEvents,
          receipt,
          updatedAt: now,
        };
      })
    );
  };

  const resetToDefault = async (): Promise<void> => {
    if (api.IS_ENTERPRISE) {
      console.warn('[veritas] demo reset is disabled in enterprise mode; backend data is authoritative.');
      return;
    }
    try {
      await api.resetDemo();
    } catch {
      // Backend unavailable: reset only the local demo view.
    }
    localStorage.removeItem('veritas_user');
    localStorage.removeItem('veritas_executions');
    localStorage.removeItem('veritas_policy');
    setCurrentUser(DEMO_USERS[0]);
    setAgents(INITIAL_AGENTS);
    setPolicy(INITIAL_POLICY);
    setExecutions(INITIAL_EXECUTIONS);
    await refreshExecutions();
  };

  return (
    <AppContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        setUserRole,
        agents,
        policy,
        updatePolicy,
        executions,
        syncError,
        refreshExecutions,
        submitTask,
        decideApproval,
        resetToDefault,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
