'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
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

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User>(() => readStored('veritas_user', DEMO_USERS[0]));
  const [agents, setAgents] = useState<AgentInfo[]>(INITIAL_AGENTS);
  const [policy, setPolicy] = useState<PolicyRule>(() => readStored('veritas_policy', INITIAL_POLICY));
  const [executions, setExecutions] = useState<ExecutionRecord[]>(
    () => readStored('veritas_executions', INITIAL_EXECUTIONS),
  );

  // Load from localStorage & sync live state from local backend
  useEffect(() => {
    let isMounted = true;
    async function initAndSync() {
      // Live sync from local Harness API (/api/v1)
      try {
        const [policyRes, execsRes] = await Promise.all([
          api.getPolicy().catch(() => null),
          api.getExecutions(50).catch(() => null),
        ]);
        if (!isMounted) return;

        if (policyRes) {
          setPolicy(api.mapPolicy(policyRes));
        }

        if (execsRes && Array.isArray(execsRes.executions) && execsRes.executions.length > 0) {
          const hydrated = await Promise.all(
            execsRes.executions.map((e) => api.hydrateExecution(e).catch(() => null))
          );
          const valid = hydrated.filter((e): e is ExecutionRecord => e !== null);
          if (valid.length > 0 && isMounted) {
            setExecutions(valid);
          }
          const agentsRes = await api.getAgents().catch(() => null);
          if (agentsRes && isMounted) {
            setAgents(api.mapAgents(agentsRes.agents, valid));
          }
        }
      } catch {
        // Local backend not reachable, keep local state
      }
    }

    initAndSync();
    return () => {
      isMounted = false;
    };
  }, []);

  // Save changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('veritas_user', JSON.stringify(currentUser));
      localStorage.setItem('veritas_executions', JSON.stringify(executions));
      localStorage.setItem('veritas_policy', JSON.stringify(policy));
    } catch {
      // LocalStorage error ignore
    }
  }, [currentUser, executions, policy]);

  const refreshExecutions = async () => {
    try {
      const [policyRes, execsRes] = await Promise.all([
        api.getPolicy().catch(() => null),
        api.getExecutions(50).catch(() => null),
      ]);
      if (policyRes) {
        setPolicy(api.mapPolicy(policyRes));
      }
      if (execsRes && Array.isArray(execsRes.executions) && execsRes.executions.length > 0) {
        const hydrated = await Promise.all(
          execsRes.executions.map((e) => api.hydrateExecution(e).catch(() => null))
        );
        const valid = hydrated.filter((e): e is ExecutionRecord => e !== null);
        if (valid.length > 0) {
          setExecutions(valid);
        }
        const agentsRes = await api.getAgents().catch(() => null);
        if (agentsRes) {
          setAgents(api.mapAgents(agentsRes.agents, valid));
        }
      }
    } catch {
      // Ignore background sync errors
    }
  };

  const setUserRole = (role: UserRole) => {
    const target = DEMO_USERS.find((u) => u.role === role) || {
      ...currentUser,
      role,
    };
    setCurrentUser(target);
    const token = api.ROLE_TOKENS[role] || 'tok-admin';
    if (typeof window !== 'undefined') {
      localStorage.setItem('veritas_token', token);
      localStorage.setItem('veritas_user', JSON.stringify(target));
    }
    // Refresh executions under the new role scope
    refreshExecutions();
  };

  const updatePolicy = async (updated: Partial<PolicyRule>): Promise<void> => {
    if (currentUser.role !== 'admin') {
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
    if (currentUser.role === 'auditor') {
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
    if (currentUser.role !== 'approver' && currentUser.role !== 'admin') {
      throw new api.ApiError(
        403,
        'FORBIDDEN',
        `Role "${currentUser.role}" is not authorized to sign approvals. Only Approvers (Sarah Jenkins) and Admins (Alexa Chen) can decide approvals.`
      );
    }

    // Attempt dispatch to real live Harness Gateway
    const targetItem = executions.find((e) => e.id === executionId);
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
