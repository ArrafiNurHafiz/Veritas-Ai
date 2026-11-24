'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AgentInfo, PolicyRule, ExecutionRecord, UserRole, ExecutionStatus, ExecutionEvent } from './types';
import { DEMO_USERS, INITIAL_AGENTS, INITIAL_POLICY, INITIAL_EXECUTIONS } from './mockData';
import { canonicalizeJson, computeSha256 } from './crypto';

interface AppContextType {
  currentUser: User;
  setCurrentUser: (user: User) => void;
  setUserRole: (role: UserRole) => void;
  agents: AgentInfo[];
  policy: PolicyRule;
  updatePolicy: (updated: Partial<PolicyRule>) => void;
  executions: ExecutionRecord[];
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
  resetToDefault: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User>(DEMO_USERS[0]); // Default to Alexa Chen (Admin)
  const [agents, setAgents] = useState<AgentInfo[]>(INITIAL_AGENTS);
  const [policy, setPolicy] = useState<PolicyRule>(INITIAL_POLICY);
  const [executions, setExecutions] = useState<ExecutionRecord[]>(INITIAL_EXECUTIONS);

  // Load from localStorage on client mount if available
  useEffect(() => {
    try {
      const savedUser = localStorage.getItem('veritas_user');
      const savedExecutions = localStorage.getItem('veritas_executions');
      const savedPolicy = localStorage.getItem('veritas_policy');

      if (savedUser) setCurrentUser(JSON.parse(savedUser));
      if (savedExecutions) setExecutions(JSON.parse(savedExecutions));
      if (savedPolicy) setPolicy(JSON.parse(savedPolicy));
    } catch {
      // LocalStorage error ignore
    }
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

  const setUserRole = (role: UserRole) => {
    const target = DEMO_USERS.find((u) => u.role === role) || {
      ...currentUser,
      role,
    };
    setCurrentUser(target);
  };

  const updatePolicy = (updated: Partial<PolicyRule>) => {
    setPolicy((prev) => ({
      ...prev,
      ...updated,
      version: prev.version + 1,
      updatedAt: new Date().toISOString(),
    }));
  };

  const submitTask = async (data: {
    agentId: string;
    invoiceId: string;
    vendor: string;
    amountIdr: number;
    description?: string;
  }): Promise<ExecutionRecord> => {
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

  const resetToDefault = () => {
    localStorage.removeItem('veritas_user');
    localStorage.removeItem('veritas_executions');
    localStorage.removeItem('veritas_policy');
    setCurrentUser(DEMO_USERS[0]);
    setAgents(INITIAL_AGENTS);
    setPolicy(INITIAL_POLICY);
    setExecutions(INITIAL_EXECUTIONS);
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
