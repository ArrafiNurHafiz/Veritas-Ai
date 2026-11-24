'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useApp } from '@/lib/store';
import { 
  Bot, 
  CheckCircle2, 
  Clock, 
  ShieldAlert, 
  ArrowRight, 
  Send, 
  ExternalLink,
  ChevronRight,
  TrendingUp,
  ShieldCheck,
  Check
} from 'lucide-react';

export default function DashboardOverview() {
  const { executions, agents, policy, submitTask, currentUser } = useApp();

  const [quickAmount, setQuickAmount] = useState('8500000');
  const [quickVendor, setQuickVendor] = useState('PT Global Tech');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);

  // Computations
  const totalExecutions = executions.length;
  const autoApproved = executions.filter(
    (e) => e.status === 'SUCCEEDED' && e.policyResult?.decision === 'ALLOWED'
  ).length;
  const pendingApprovals = executions.filter(
    (e) => e.status === 'WAITING_APPROVAL' && e.approval?.status === 'PENDING'
  ).length;
  const blockedViolations = executions.filter(
    (e) => e.status === 'DENIED' || e.status === 'REJECTED'
  ).length;

  const handleQuickSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmittedMessage(null);
    try {
      const amt = Number(quickAmount) || 0;
      const res = await submitTask({
        agentId: 'procurement-agent',
        invoiceId: 'INV-' + Math.floor(1000 + Math.random() * 9000),
        vendor: quickVendor,
        amountIdr: amt,
        description: 'Dashboard quick evaluation task submission.',
      });
      setSubmittedMessage(`Task ${res.id} queued -> Status: ${res.status}`);
      setTimeout(() => setSubmittedMessage(null), 4000);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-10">
      {/* Title & Context */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1.5">
          <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
            Nexora Technologies • Procurement Operations
          </span>
          <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
            Governance & Execution Telemetry
          </h1>
          <p className="text-[16px] text-[#777b86]">
            Real-time policy mediation, human-in-the-loop gates, and cryptographic ledger receipts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/tasks"
            className="pill-button-filled !h-10 !px-5 !text-[14px]"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Submit Invoice Task</span>
          </Link>
        </div>
      </div>

      {/* 4 Stat Cards in Steep Editorial Style */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Stat 1 */}
        <div className="bg-[#f2f2f3] rounded-[24px] p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-[#777b86] font-medium">Total Agent Tasks</span>
            <span className="w-2 h-2 rounded-full bg-[#17191c]"></span>
          </div>
          <div className="space-y-1">
            <div className="font-sans text-[36px] font-medium text-[#17191c] leading-none">
              {totalExecutions}
            </div>
            <p className="text-[12px] text-[#777b86]">100% routed via policy gateway</p>
          </div>
        </div>

        {/* Stat 2 */}
        <div className="bg-[#f2f2f3] rounded-[24px] p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-[#777b86] font-medium">Auto-Approved (&le; 5M)</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="space-y-1">
            <div className="font-sans text-[36px] font-medium text-[#17191c] leading-none">
              {autoApproved}
            </div>
            <p className="text-[12px] text-emerald-700 font-medium">Deterministic allowance</p>
          </div>
        </div>

        {/* Stat 3 */}
        <div className={`rounded-[24px] p-6 space-y-3 border transition-all ${
          pendingApprovals > 0 ? 'bg-amber-50 border-amber-200' : 'bg-[#f2f2f3] border-transparent'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-[13px] font-medium ${pendingApprovals > 0 ? 'text-amber-900' : 'text-[#777b86]'}`}>
              Pending Human Sign-Off
            </span>
            <Clock className={`w-4 h-4 ${pendingApprovals > 0 ? 'text-amber-600' : 'text-[#777b86]'}`} />
          </div>
          <div className="space-y-1">
            <div className={`font-sans text-[36px] font-medium leading-none ${pendingApprovals > 0 ? 'text-amber-900' : 'text-[#17191c]'}`}>
              {pendingApprovals}
            </div>
            <p className={`text-[12px] ${pendingApprovals > 0 ? 'text-amber-800 font-medium' : 'text-[#777b86]'}`}>
              Awaiting role sign-off
            </p>
          </div>
        </div>

        {/* Stat 4 */}
        <div className="bg-[#f2f2f3] rounded-[24px] p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[13px] text-[#777b86] font-medium">Policy Blocks / Rejections</span>
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <div className="space-y-1">
            <div className="font-sans text-[36px] font-medium text-[#17191c] leading-none">
              {blockedViolations}
            </div>
            <p className="text-[12px] text-rose-700 font-medium">Zero unauthorized execution</p>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Quick Dispatch + Active Policy */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Dispatch Widget */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-display text-[22px] text-[#17191c]">Interactive Policy Dispatcher</h3>
              <p className="text-[13px] text-[#777b86]">
                Instantly trigger policy evaluation with sample amounts to observe automatic allowance vs human gate.
              </p>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#f2f2f3] text-[#777b86]">
              Target: Procurement Agent
            </span>
          </div>

          <form onSubmit={handleQuickSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-[#17191c]">Vendor Name</label>
                <select
                  value={quickVendor}
                  onChange={(e) => setQuickVendor(e.target.value)}
                  className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[14px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
                >
                  <option value="PT Global Tech">PT Global Tech (Whitelisted)</option>
                  <option value="Nvidia Enterprise">Nvidia Enterprise (Whitelisted)</option>
                  <option value="AWS Cloud Services">AWS Cloud Services (Whitelisted)</option>
                  <option value="Unknown Overseas Trading">Unknown Overseas Trading (Unverified)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-[#17191c]">Invoice Amount (IDR)</label>
                <div className="relative">
                  <input
                    type="number"
                    value={quickAmount}
                    onChange={(e) => setQuickAmount(e.target.value)}
                    className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[14px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
                    placeholder="8500000"
                  />
                  <div className="absolute right-2 top-2 flex gap-1">
                    <button
                      type="button"
                      onClick={() => setQuickAmount('3200000')}
                      className="text-[11px] px-2 py-0.5 rounded bg-white border border-[#ececec] text-[#777b86] hover:text-[#17191c]"
                    >
                      3.2M (Auto)
                    </button>
                    <button
                      type="button"
                      onClick={() => setQuickAmount('8500000')}
                      className="text-[11px] px-2 py-0.5 rounded bg-white border border-[#ececec] text-[#777b86] hover:text-[#17191c]"
                    >
                      8.5M (Gate)
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="text-[12px] text-[#777b86]">
                {Number(quickAmount) > policy.maxAutoAmountIdr ? (
                  <span className="text-amber-800 font-medium">
                    &bull; Exceeds IDR {policy.maxAutoAmountIdr.toLocaleString()} limit &rarr; Will trigger APPROVAL_REQUIRED
                  </span>
                ) : (
                  <span className="text-emerald-700 font-medium">
                    &bull; Within IDR {policy.maxAutoAmountIdr.toLocaleString()} limit &rarr; Will AUTO-EXECUTE & sign
                  </span>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="pill-button-filled !h-10 !px-6 !text-[13px] flex items-center gap-2"
              >
                <span>{isSubmitting ? 'Evaluating Policy...' : 'Submit to Harness'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {submittedMessage && (
              <div className="p-3 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-[13px] flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>{submittedMessage}</span>
              </div>
            )}
          </form>
        </div>

        {/* Active Policy Rules Card */}
        <div className="bg-[#fafafb] rounded-2xl p-6 border border-[#ececec] flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#979799] uppercase tracking-wider">Active Policy</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white text-[#777b86] border border-[#ececec]">
                v{policy.version}
              </span>
            </div>
            <h4 className="font-sans text-[16px] font-medium text-[#17191c] leading-snug">
              {policy.name}
            </h4>
            <div className="space-y-2 text-[13px] text-[#777b86]">
              <div className="flex justify-between py-1 border-b border-[#ececec]">
                <span>Auto-Approval Ceiling:</span>
                <strong className="text-[#17191c]">Rp {policy.maxAutoAmountIdr.toLocaleString()}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-[#ececec]">
                <span>Default Unregistered Rule:</span>
                <span className="text-rose-700 font-mono font-medium">{policy.defaultAction}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#ececec]">
                <span>Allowed Vendors:</span>
                <span className="text-[#17191c]">{policy.allowedVendors.length} companies</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Required Approver Roles:</span>
                <span className="text-[#17191c] font-medium">approver, admin</span>
              </div>
            </div>
          </div>

          <Link
            href="/dashboard/policies"
            className="text-[13px] text-[#17191c] font-medium flex items-center justify-between p-3 rounded-xl bg-white border border-[#ececec] hover:bg-[#f2f2f3] transition-colors"
          >
            <span>Configure Policy Rules</span>
            <ChevronRight className="w-4 h-4 text-[#777b86]" />
          </Link>
        </div>
      </div>

      {/* Recent Executions Table */}
      <div className="bg-white rounded-2xl border border-[#ececec] overflow-hidden shadow-sm">
        <div className="p-6 border-b border-[#ececec] flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="font-display text-[22px] text-[#17191c]">Recent Agent Executions</h3>
            <p className="text-[13px] text-[#777b86]">
              Deterministic progression: Planning &rarr; Policy Gate &rarr; Human Sign-off &rarr; Sandboxed Tool &rarr; Besu Anchor.
            </p>
          </div>
          <Link
            href="/dashboard/executions"
            className="text-[13px] text-[#17191c] font-medium hover:underline flex items-center gap-1"
          >
            <span>View All Executions</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-[#ececec] bg-[#fafafb] text-[#979799] font-medium">
                <th className="px-6 py-3.5">Execution ID</th>
                <th className="px-6 py-3.5">Invoice / Vendor</th>
                <th className="px-6 py-3.5">Amount (IDR)</th>
                <th className="px-6 py-3.5">Policy Decision</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Trust Evidence</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ececec]">
              {executions.slice(0, 6).map((item) => {
                const isOverLimit = item.payload.amountIdr > policy.maxAutoAmountIdr;
                return (
                  <tr key={item.id} className="hover:bg-[#fafafb] transition-colors">
                    <td className="px-6 py-4 font-mono font-medium text-[#17191c]">
                      {item.id}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-[#17191c]">{item.payload.invoiceId}</div>
                      <div className="text-[12px] text-[#777b86]">{item.payload.vendor}</div>
                    </td>
                    <td className="px-6 py-4 font-mono text-[#17191c]">
                      Rp {item.payload.amountIdr.toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                        item.policyResult?.decision === 'ALLOWED'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : item.policyResult?.decision === 'APPROVAL_REQUIRED'
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}>
                        {item.policyResult?.decision}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 text-[12px] font-medium ${
                        item.status === 'SUCCEEDED'
                          ? 'text-emerald-700'
                          : item.status === 'WAITING_APPROVAL'
                          ? 'text-amber-700'
                          : 'text-rose-700'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          item.status === 'SUCCEEDED'
                            ? 'bg-emerald-500'
                            : item.status === 'WAITING_APPROVAL'
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}></span>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {item.receipt ? (
                        <div className="flex items-center gap-1.5 text-[12px] text-emerald-700 font-medium">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Anchored #{item.receipt.anchor.blockNumber}</span>
                        </div>
                      ) : item.status === 'WAITING_APPROVAL' ? (
                        <span className="text-[12px] text-amber-800">Pending sign-off</span>
                      ) : (
                        <span className="text-[12px] text-[#979799]">No receipt (Denied)</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {item.status === 'WAITING_APPROVAL' ? (
                        <Link
                          href="/dashboard/approvals"
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-600 text-white text-[12px] font-medium hover:bg-amber-700 transition-colors"
                        >
                          Review &rarr;
                        </Link>
                      ) : item.receipt ? (
                        <Link
                          href="/dashboard/trust"
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[#f2f2f3] text-[#17191c] text-[12px] font-medium hover:bg-[#e5e5e6] transition-colors"
                        >
                          Inspect Receipt
                        </Link>
                      ) : (
                        <span className="text-[12px] text-[#979799]">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
