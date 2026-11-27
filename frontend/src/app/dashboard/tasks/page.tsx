'use client';

import React, { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useApp } from '@/lib/store';
import { IS_ENTERPRISE, AGENT_METADATA } from '@/lib/api';
import { AgentInfo, ExecutionRecord } from '@/lib/types';
import StateTimeline from '@/components/StateTimeline';
import ReceiptViewer from '@/components/ReceiptViewer';
import {
  Send,
  Check,
  Lock,
  AlertCircle,
  Bot,
} from 'lucide-react';

interface PresetItem {
  title: string;
  taskType: string;
  badge: string;
  expected: string;
  desc: string;
  fields: Record<string, string | number>;
}

const AGENT_ORDER = [
  'procurement-agent',
  'finance-risk-agent',
  'hr-operations-agent',
  'security-audit-agent',
] as const;

const AGENT_TASK_TYPES: Record<string, { value: string; label: string; tool: string }[]> = {
  'procurement-agent': [
    { value: 'invoice_review', label: 'Invoice Review', tool: 'approve_invoice' },
    { value: 'vendor_verification', label: 'Vendor Verification', tool: 'check_vendor_status' },
  ],
  'finance-risk-agent': [
    { value: 'ledger_reconciliation', label: 'Ledger Reconciliation', tool: 'audit_reconciliation' },
    { value: 'discrepancy_flag', label: 'Discrepancy Flagging', tool: 'flag_discrepancy' },
  ],
  'hr-operations-agent': [
    { value: 'workspace_provisioning', label: 'Workspace Provisioning', tool: 'provision_workspace' },
    { value: 'badge_request', label: 'Facility Badge Request', tool: 'log_badge_request' },
  ],
  'security-audit-agent': [
    { value: 'iam_posture_scan', label: 'IAM Posture Scan', tool: 'scan_iam_keys' },
    { value: 'token_revocation', label: 'Token Revocation', tool: 'revoke_stale_token' },
  ],
};

const AGENT_PRESETS: Record<string, PresetItem[]> = {
  'procurement-agent': [
    {
      title: 'Auto-Approval Flow',
      taskType: 'invoice_review',
      badge: 'Rp 3,200,000',
      desc: 'Monthly cloud backup storage quota (Under 5M threshold)',
      expected: 'ALLOWED → Auto-executed',
      fields: {
        invoice_id: 'INV-2036-101',
        vendor: 'V-ABC',
        amount_idr: 3200000,
        description: 'Monthly cloud backup storage quota (Under 5M threshold)',
      },
    },
    {
      title: 'Approval Gate Flow',
      taskType: 'invoice_review',
      badge: 'Rp 8,500,000',
      desc: 'Enterprise hardware server expansion (Over 5M threshold)',
      expected: 'APPROVAL_REQUIRED → Gate held',
      fields: {
        invoice_id: 'INV-2036-102',
        vendor: 'V-ABC',
        amount_idr: 8500000,
        description: 'Enterprise hardware server expansion (Over 5M threshold)',
      },
    },
    {
      title: 'Unverified Vendor Block',
      taskType: 'invoice_review',
      badge: 'Rp 14,500,000',
      desc: 'Emergency hardware import order from unlisted vendor',
      expected: 'DENIED → Unlisted vendor blocked',
      fields: {
        invoice_id: 'INV-2036-103',
        vendor: 'V-EVIL',
        amount_idr: 14500000,
        description: 'Emergency hardware import order (Over limit + unlisted)',
      },
    },
  ],
  'finance-risk-agent': [
    {
      title: 'Small Variance Auto-Reconcile',
      taskType: 'ledger_reconciliation',
      badge: 'Rp 1,250,000',
      desc: 'Routine GL-4100 clearing variance within auto limit',
      expected: 'ALLOWED → Auto-reconciled',
      fields: {
        reference_id: 'REC-2026-041',
        account_code: 'GL-4100',
        amount_idr: 1250000,
        description: 'Routine clearing variance within auto ceiling',
      },
    },
    {
      title: 'High Variance Gate',
      taskType: 'ledger_reconciliation',
      badge: 'Rp 11,400,000',
      desc: 'Unmatched FX settlement variance exceeding 5M ceiling',
      expected: 'APPROVAL_REQUIRED → CFO / Approver gate',
      fields: {
        reference_id: 'REC-2026-042',
        account_code: 'GL-9200',
        amount_idr: 11400000,
        description: 'Unmatched FX settlement variance requiring controller sign-off',
      },
    },
    {
      title: 'Critical Anomaly Escalation',
      taskType: 'discrepancy_flag',
      badge: 'CRITICAL',
      desc: 'Duplicate wire settlement alert on treasury ledger',
      expected: 'APPROVAL_REQUIRED → High-risk escalation',
      fields: {
        reference_id: 'ANOM-2026-009',
        severity: 'critical',
        reason: 'Duplicate outbound settlement pattern detected in GL-9200',
      },
    },
  ],
  'hr-operations-agent': [
    {
      title: 'Standard Onboarding Access',
      taskType: 'workspace_provisioning',
      badge: 'standard',
      desc: 'Provision standard workspace for new engineering hire',
      expected: 'ALLOWED → Auto-provisioned',
      fields: {
        employee_id: 'EMP-4091',
        department: 'Engineering',
        access_tier: 'standard',
      },
    },
    {
      title: 'Elevated Access Gate',
      taskType: 'workspace_provisioning',
      badge: 'elevated',
      desc: 'Request elevated production-support permissions',
      expected: 'APPROVAL_REQUIRED → Manager gate',
      fields: {
        employee_id: 'EMP-4092',
        department: 'Platform SRE',
        access_tier: 'elevated',
      },
    },
    {
      title: 'Admin Privilege Escalation',
      taskType: 'workspace_provisioning',
      badge: 'admin',
      desc: 'Attempt direct super-admin workspace provisioning',
      expected: 'DENIED → Privilege escalation blocked',
      fields: {
        employee_id: 'EMP-4093',
        department: 'Contractor',
        access_tier: 'admin',
      },
    },
  ],
  'security-audit-agent': [
    {
      title: 'Staging IAM Posture Scan',
      taskType: 'iam_posture_scan',
      badge: 'staging',
      desc: 'Read-only IAM key rotation check on staging account',
      expected: 'ALLOWED → Scan executed',
      fields: {
        account_id: 'AWS-STG-01',
        scope: 'staging',
      },
    },
    {
      title: 'Production Token Revocation',
      taskType: 'token_revocation',
      badge: 'svc-prod',
      desc: 'Revoke production service credential (blast radius gate)',
      expected: 'APPROVAL_REQUIRED → Security sign-off',
      fields: {
        principal_id: 'svc-prod-billing',
        token_id: 'AKIA-PROD-8821',
        reason: 'Key age > 90 days detected during rotation audit',
      },
    },
    {
      title: 'Root Account Lockout Guard',
      taskType: 'token_revocation',
      badge: 'root',
      desc: 'Attempt automated revocation of root breakglass account',
      expected: 'DENIED → Protected principal guard',
      fields: {
        principal_id: 'root-breakglass',
        token_id: 'ROOT-0001',
        reason: 'Automated stale key sweep attempt',
      },
    },
  ],
};

function strField(fields: Record<string, string | number> | undefined, key: string, fallback: string): string {
  const val = fields?.[key];
  return typeof val === 'string' ? val : fallback;
}

function numField(fields: Record<string, string | number> | undefined, key: string, fallback: number): number {
  const val = fields?.[key];
  return typeof val === 'number' ? val : fallback;
}

function TaskCenterContent({ initialAgentId }: { initialAgentId: string }) {
  const { agents, policy, submitTask, currentUser } = useApp();
  const initialPreset = AGENT_PRESETS[initialAgentId]?.[0];
  const initialFields = initialPreset?.fields;

  const [selectedAgentId, setSelectedAgentId] = useState<string>(initialAgentId);
  const [taskType, setTaskType] = useState<string>(
    initialPreset?.taskType || AGENT_TASK_TYPES[initialAgentId]?.[0]?.value || 'invoice_review',
  );

  // Procurement / Financial fields
  const [invoiceId, setInvoiceId] = useState(() => strField(initialFields, 'invoice_id', 'INV-2036-009'));
  const [vendor, setVendor] = useState(() => strField(initialFields, 'vendor', 'V-ABC'));
  const [amountIdr, setAmountIdr] = useState(() => numField(initialFields, 'amount_idr', 8500000));
  const [description, setDescription] = useState(() =>
    strField(initialFields, 'description', 'Quarterly Datacenter Server Infrastructure Maintenance'),
  );

  // Multi-agent domain fields
  const [referenceId, setReferenceId] = useState(() => strField(initialFields, 'reference_id', 'REC-2026-041'));
  const [accountCode, setAccountCode] = useState(() => strField(initialFields, 'account_code', 'GL-4100'));
  const [severity, setSeverity] = useState(() => strField(initialFields, 'severity', 'high'));
  const [employeeId, setEmployeeId] = useState(() => strField(initialFields, 'employee_id', 'EMP-4091'));
  const [department, setDepartment] = useState(() => strField(initialFields, 'department', 'Engineering'));
  const [accessTier, setAccessTier] = useState(() => strField(initialFields, 'access_tier', 'standard'));
  const [zone, setZone] = useState(() => strField(initialFields, 'zone', 'office'));
  const [accountId, setAccountId] = useState(() => strField(initialFields, 'account_id', 'AWS-STG-01'));
  const [scope, setScope] = useState(() => strField(initialFields, 'scope', 'staging'));
  const [principalId, setPrincipalId] = useState(() => strField(initialFields, 'principal_id', 'svc-prod-billing'));
  const [tokenId, setTokenId] = useState(() => strField(initialFields, 'token_id', 'AKIA-PROD-8821'));
  const [reason, setReason] = useState(() =>
    strField(initialFields, 'reason', 'Key age > 90 days detected during rotation audit'),
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [currentExecution, setCurrentExecution] = useState<ExecutionRecord | null>(null);

  const isAuthorized = currentUser.role === 'operator' || currentUser.role === 'admin';

  const applyPreset = (preset: PresetItem) => {
    setTaskType(preset.taskType);
    const f = preset.fields;
    if (typeof f.invoice_id === 'string') setInvoiceId(f.invoice_id);
    if (typeof f.vendor === 'string') setVendor(f.vendor);
    if (typeof f.amount_idr === 'number') setAmountIdr(f.amount_idr);
    if (typeof f.description === 'string') setDescription(f.description);
    if (typeof f.reference_id === 'string') setReferenceId(f.reference_id);
    if (typeof f.account_code === 'string') setAccountCode(f.account_code);
    if (typeof f.severity === 'string') setSeverity(f.severity);
    if (typeof f.employee_id === 'string') setEmployeeId(f.employee_id);
    if (typeof f.department === 'string') setDepartment(f.department);
    if (typeof f.access_tier === 'string') setAccessTier(f.access_tier);
    if (typeof f.zone === 'string') setZone(f.zone);
    if (typeof f.account_id === 'string') setAccountId(f.account_id);
    if (typeof f.scope === 'string') setScope(f.scope);
    if (typeof f.principal_id === 'string') setPrincipalId(f.principal_id);
    if (typeof f.token_id === 'string') setTokenId(f.token_id);
    if (typeof f.reason === 'string') setReason(f.reason);
  };

  const selectAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
    setSubmitError(null);
    const presets = AGENT_PRESETS[agentId];
    if (presets && presets.length > 0) {
      applyPreset(presets[0]);
    } else {
      const firstTask = AGENT_TASK_TYPES[agentId]?.[0]?.value || 'invoice_review';
      setTaskType(firstTask);
    }
  };

  const agentOptions: AgentInfo[] =
    agents.length > 0
      ? agents
      : AGENT_ORDER.map((id) => ({
          id,
          name: AGENT_METADATA[id].name,
          version: AGENT_METADATA[id].version,
          description: AGENT_METADATA[id].description,
          status: 'OPERATIONAL' as const,
          allowedTools: [] as string[],
          totalExecutions: 0,
          blockedCount: 0,
        }));

  const selectedAgent = agentOptions.find((a) => a.id === selectedAgentId) || agentOptions[0];
  const taskOptions = AGENT_TASK_TYPES[selectedAgentId] || AGENT_TASK_TYPES['procurement-agent'];
  const activeTaskMeta = taskOptions.find((t) => t.value === taskType) || taskOptions[0];
  const isSelectedToolDisabled =
    agents.length > 0 && selectedAgent !== undefined && !selectedAgent.allowedTools.includes(activeTaskMeta.tool);
  const presets = AGENT_PRESETS[selectedAgentId] || AGENT_PRESETS['procurement-agent'];

  const buildPayload = (): Record<string, unknown> => {
    switch (taskType) {
      case 'invoice_review':
        return {
          invoice_id: invoiceId,
          vendor,
          amount_idr: Number(amountIdr),
          description,
        };
      case 'vendor_verification':
        return { vendor };
      case 'ledger_reconciliation':
        return {
          reference_id: referenceId,
          account_code: accountCode,
          amount_idr: Number(amountIdr),
          description,
        };
      case 'discrepancy_flag':
        return {
          reference_id: referenceId,
          severity,
          reason,
        };
      case 'workspace_provisioning':
        return {
          employee_id: employeeId,
          department,
          access_tier: accessTier,
        };
      case 'badge_request':
        return {
          employee_id: employeeId,
          zone,
        };
      case 'iam_posture_scan':
        return {
          account_id: accountId,
          scope,
        };
      case 'token_revocation':
        return {
          principal_id: principalId,
          token_id: tokenId,
          reason,
        };
      default:
        return { invoice_id: invoiceId, vendor, amount_idr: Number(amountIdr), description };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthorized) {
      setSubmitError(`Role "${currentUser.role}" is not permitted to submit tasks. Switch to Operator or Admin.`);
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const payload = buildPayload();
      const res = await submitTask({
        agentId: selectedAgentId,
        taskType,
        payload,
        invoiceId: String(payload.invoice_id || payload.reference_id || payload.employee_id || payload.principal_id || payload.account_id || ''),
        vendor: String(payload.vendor || payload.account_code || payload.department || payload.zone || payload.scope || ''),
        amountIdr: typeof payload.amount_idr === 'number' ? payload.amount_idr : 0,
        description: String(payload.description || payload.reason || ''),
      });
      setCurrentExecution(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Task submission failed';
      setSubmitError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#6D7344] uppercase tracking-wider">
          Task Orchestration
        </span>
        <h1 className="font-display text-[44px] text-[#192319] leading-[1.1] tracking-[-0.66px]">
          Multi-Agent Task Center
        </h1>
        <p className="text-[16px] text-[#2D372D]">
          Dispatch domain tasks across operational AI agents and monitor deterministic policy mediation.
        </p>
      </div>

      {/* Role Authorization Alert */}
      {!isAuthorized ? (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start justify-between gap-4 text-[13px] text-amber-900">
          <div className="flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Role Authorization Notice: </strong>
              You are signed in as <span className="font-mono underline">{currentUser.name} ({currentUser.role})</span>. In accordance with enterprise separation of duties, only <span className="font-mono font-medium">operator</span> or <span className="font-mono font-medium">admin</span> can dispatch tasks.
            </div>
          </div>
          <span className="text-[12px] text-amber-800 shrink-0">
            {IS_ENTERPRISE ? '(Requires Operator or Admin role)' : '(Switch to Marcus Vance - Operator via header)'}
          </span>
        </div>
      ) : (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-between text-[13px] text-emerald-900">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Authorized Operator: <strong>{currentUser.name}</strong> ({currentUser.role}). Live dispatch to Harness Gateway is active.</span>
          </div>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
            Session Active
          </span>
        </div>
      )}

      {submitError && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-[13px] flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* Agent Selector */}
      <div className="space-y-2">
        <span className="text-[12px] font-semibold uppercase tracking-wider text-[#6D7344]">
          1. Select Target Agent ({agentOptions.length} Operational)
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {agentOptions.map((agent) => {
            const active = agent.id === selectedAgentId;
            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => selectAgent(agent.id)}
                className={`text-left p-3.5 rounded-2xl border transition-all space-y-1.5 ${
                  active
                    ? 'bg-[#192319] text-white border-[#192319] shadow-sm'
                    : 'bg-white text-[#192319] border-[#DCDCD7] hover:border-[#192319]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className={`w-4 h-4 ${active ? 'text-white' : 'text-[#2D372D]'}`} />
                    <span className="text-[13px] font-semibold">{agent.name}</span>
                  </div>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    active ? 'bg-white/15 text-white' : 'bg-[#F0F0EC] text-[#2D372D]'
                  }`}>
                    v{agent.version}
                  </span>
                </div>
                <p className={`text-[11px] line-clamp-2 ${active ? 'text-zinc-300' : 'text-[#2D372D]'}`}>
                  {agent.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="space-y-2">
        <span className="text-[12px] font-semibold uppercase tracking-wider text-[#6D7344]">
          2. Quick Scenario Templates for {selectedAgent?.name || 'Agent'}
        </span>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {presets.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                applyPreset(p);
                if (p.taskType === 'invoice_review') {
                  setInvoiceId('INV-2036-0' + Math.floor(10 + Math.random() * 90));
                }
              }}
              className="text-left p-3.5 rounded-2xl bg-[#F8F8F8] border border-[#DCDCD7] hover:border-[#192319] hover:bg-white transition-all space-y-1 group"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[13px] font-medium text-[#192319] group-hover:underline">
                  {p.title}
                </span>
                <span className="font-mono text-[11px] text-[#192319] bg-white px-2 py-0.5 rounded border border-[#DCDCD7]">
                  {p.badge}
                </span>
              </div>
              <p className="text-[11px] text-[#2D372D] leading-snug">{p.desc}</p>
              <div className="text-[11px] text-amber-800 font-medium pt-1">
                {p.expected}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Task Form */}
        <div className="bg-white rounded-2xl p-6 border border-[#DCDCD7] shadow-sm space-y-6">
          <div className="space-y-1">
            <h3 className="font-display text-[22px] text-[#192319]">
              Submit {selectedAgent?.name || 'Agent'} Task
            </h3>
            <p className="text-[13px] text-[#2D372D]">
              Submits request to <code className="font-mono text-[#192319]">POST /api/v1/tasks</code>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium text-[#192319]">Assigned Agent & Tool Boundary</label>
              <div className="p-3 rounded-xl bg-[#F8F8F8] border border-[#DCDCD7] text-[13px] flex items-center justify-between gap-2">
                <div>
                  <span className="font-medium text-[#192319]">{selectedAgent?.name}</span>
                  <span className="text-[#2D372D] ml-2">(v{selectedAgent?.version} • {selectedAgent?.status})</span>
                </div>
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                  isSelectedToolDisabled
                    ? 'bg-rose-50 text-rose-800 border-rose-200'
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}>
                  Tool: {activeTaskMeta.tool}{isSelectedToolDisabled ? ' (DISABLED)' : ''}
                </span>
              </div>
              {isSelectedToolDisabled && (
                <p className="text-[12px] text-rose-700">
                  Tool <code className="font-mono">{activeTaskMeta.tool}</code> is disabled in Organization Settings; Harness will deny proposals until re-enabled.
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-medium text-[#192319]">Task Flow</label>
              <select
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
              >
                {taskOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label} ({opt.value} → {opt.tool})
                  </option>
                ))}
              </select>
            </div>

            {taskType === 'invoice_review' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Invoice Reference ID</label>
                    <input
                      type="text"
                      required
                      value={invoiceId}
                      onChange={(e) => setInvoiceId(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Supplier / Vendor</label>
                    <input
                      type="text"
                      required
                      value={vendor}
                      onChange={(e) => setVendor(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-[13px] font-medium text-[#192319]">Invoice Amount (IDR)</label>
                    <span className="text-[12px] text-[#2D372D]">
                      Threshold: Rp {policy.maxAutoAmountIdr.toLocaleString()}
                    </span>
                  </div>
                  <input
                    type="number"
                    required
                    min={1}
                    value={amountIdr}
                    onChange={(e) => setAmountIdr(Number(e.target.value))}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[15px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Description / Purpose</label>
                  <textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl p-3 text-[13px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
              </>
            )}

            {taskType === 'vendor_verification' && (
              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-[#192319]">Vendor Code</label>
                <input
                  type="text"
                  required
                  value={vendor}
                  onChange={(e) => setVendor(e.target.value)}
                  className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                />
              </div>
            )}

            {taskType === 'ledger_reconciliation' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Reconciliation Reference ID</label>
                    <input
                      type="text"
                      required
                      value={referenceId}
                      onChange={(e) => setReferenceId(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Ledger Account Code</label>
                    <input
                      type="text"
                      required
                      value={accountCode}
                      onChange={(e) => setAccountCode(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-[13px] font-medium text-[#192319]">Variance Amount (IDR)</label>
                    <span className="text-[12px] text-[#2D372D]">
                      Threshold: Rp {policy.maxAutoAmountIdr.toLocaleString()}
                    </span>
                  </div>
                  <input
                    type="number"
                    required
                    min={1}
                    value={amountIdr}
                    onChange={(e) => setAmountIdr(Number(e.target.value))}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[15px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Reconciliation Notes</label>
                  <textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl p-3 text-[13px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
              </>
            )}

            {taskType === 'discrepancy_flag' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Anomaly Reference ID</label>
                    <input
                      type="text"
                      required
                      value={referenceId}
                      onChange={(e) => setReferenceId(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Severity</label>
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
                    >
                      <option value="low">low (Auto-Allowed)</option>
                      <option value="medium">medium (Auto-Allowed)</option>
                      <option value="high">high (Approval Required)</option>
                      <option value="critical">critical (Approval Required)</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Discrepancy Reason</label>
                  <textarea
                    rows={2}
                    required
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl p-3 text-[13px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
              </>
            )}

            {taskType === 'workspace_provisioning' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Employee ID</label>
                    <input
                      type="text"
                      required
                      value={employeeId}
                      onChange={(e) => setEmployeeId(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Department</label>
                    <input
                      type="text"
                      required
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Access Tier</label>
                  <select
                    value={accessTier}
                    onChange={(e) => setAccessTier(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  >
                    <option value="standard">standard (Auto-Allowed)</option>
                    <option value="elevated">elevated (Approval Gate)</option>
                    <option value="admin">admin (Denied by Policy)</option>
                  </select>
                </div>
              </>
            )}

            {taskType === 'badge_request' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Employee ID</label>
                  <input
                    type="text"
                    required
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Facility Zone</label>
                  <select
                    value={zone}
                    onChange={(e) => setZone(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  >
                    <option value="office">office (Auto-Allowed)</option>
                    <option value="general">general (Auto-Allowed)</option>
                    <option value="datacenter">datacenter (Approval Gate)</option>
                    <option value="vault">vault (Approval Gate)</option>
                  </select>
                </div>
              </div>
            )}

            {taskType === 'iam_posture_scan' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Cloud Account ID</label>
                  <input
                    type="text"
                    required
                    value={accountId}
                    onChange={(e) => setAccountId(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Scan Scope</label>
                  <select
                    value={scope}
                    onChange={(e) => setScope(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  >
                    <option value="staging">staging (Auto-Allowed)</option>
                    <option value="prod-readonly">prod-readonly (Auto-Allowed)</option>
                    <option value="global-all">global-all (Approval Gate)</option>
                    <option value="root">root (Denied by Policy)</option>
                  </select>
                </div>
              </div>
            )}

            {taskType === 'token_revocation' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Principal ID</label>
                    <input
                      type="text"
                      required
                      value={principalId}
                      onChange={(e) => setPrincipalId(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[13px] font-medium text-[#192319]">Token ID</label>
                    <input
                      type="text"
                      required
                      value={tokenId}
                      onChange={(e) => setTokenId(e.target.value)}
                      className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#192319] focus:outline-none focus:border-[#192319]"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[13px] font-medium text-[#192319]">Revocation Reason</label>
                  <textarea
                    rows={2}
                    required
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full bg-[#F8F8F8] border border-[#DCDCD7] rounded-xl p-3 text-[13px] text-[#192319] focus:outline-none focus:border-[#192319]"
                  />
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !isAuthorized}
              className="w-full pill-button-filled !h-12 !text-[15px] flex items-center justify-center gap-2 mt-4 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
              <span>
                {!isAuthorized
                  ? `Forbidden for ${currentUser.role} (Operator only)`
                  : isSubmitting
                  ? 'Evaluating via Policy Engine...'
                  : `Submit to ${selectedAgent?.name || 'Harness'}`}
              </span>
            </button>
          </form>
        </div>

        {/* Live Execution Output Result */}
        <div className="space-y-6">
          {currentExecution ? (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="bg-white rounded-2xl p-6 border border-[#DCDCD7] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#DCDCD7] pb-4">
                  <div>
                    <span className="text-[11px] font-semibold text-[#6D7344] uppercase tracking-wider">
                      {currentExecution.agentName} &bull; Execution Result
                    </span>
                    <h3 className="font-display text-[22px] text-[#192319]">
                      {currentExecution.id}
                    </h3>
                  </div>

                  <span className={`px-3 py-1 rounded-full text-[12px] font-medium ${
                    currentExecution.status === 'SUCCEEDED'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : currentExecution.status === 'WAITING_APPROVAL'
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : 'bg-rose-50 text-rose-800 border border-rose-200'
                  }`}>
                    {currentExecution.status}
                  </span>
                </div>

                {/* Policy Decision Summary */}
                <div className="p-4 rounded-xl bg-[#F8F8F8] border border-[#DCDCD7] space-y-2 text-[13px]">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-[#192319]">Policy Engine Decision:</span>
                    <strong className="text-[#192319] font-mono">
                      {currentExecution.policyResult?.decision}
                    </strong>
                  </div>
                  <p className="text-[#2D372D]">
                    {currentExecution.policyResult?.reason}
                  </p>
                </div>

                {/* State Machine Stepper */}
                <StateTimeline
                  events={currentExecution.events}
                  currentStatus={currentExecution.status}
                />
              </div>

              {/* Receipt Preview if auto-approved */}
              {currentExecution.receipt && (
                <ReceiptViewer receipt={currentExecution.receipt} />
              )}
            </div>
          ) : (
            <div className="bg-[#F8F8F8] rounded-2xl p-12 border border-[#DCDCD7] text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-white border border-[#DCDCD7] flex items-center justify-center mx-auto text-[#2D372D]">
                <Send className="w-5 h-5" />
              </div>
              <h4 className="font-display text-[20px] text-[#192319]">Ready for Dispatch</h4>
              <p className="text-[13px] text-[#2D372D] max-w-sm mx-auto">
                Choose any operational agent above and select a scenario template to watch deterministic policy mediation in action.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TaskCenterInner() {
  const searchParams = useSearchParams();
  const rawAgent = searchParams.get('agent');
  const agentParam = rawAgent && AGENT_TASK_TYPES[rawAgent] ? rawAgent : 'procurement-agent';
  return <TaskCenterContent key={agentParam} initialAgentId={agentParam} />;
}

export default function TaskCenterPage() {
  return (
    <Suspense fallback={<div className="p-8 text-[14px] text-[#2D372D]">Loading Task Center...</div>}>
      <TaskCenterInner />
    </Suspense>
  );
}
