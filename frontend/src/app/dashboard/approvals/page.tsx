'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/store';
import { ExecutionRecord } from '@/lib/types';
import { 
  CheckSquare, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  ShieldCheck, 
  Clock, 
  UserCheck,
  Lock,
  ArrowRight
} from 'lucide-react';
import Link from 'next/link';

export default function ApprovalsPage() {
  const { executions, currentUser, decideApproval, policy } = useApp();

  const [selectedExec, setSelectedExec] = useState<ExecutionRecord | null>(null);
  const [decisionReason, setDecisionReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Filter items waiting for approval
  const pendingList = executions.filter(
    (e) => e.status === 'WAITING_APPROVAL' && e.approval?.status === 'PENDING'
  );

  const resolvedList = executions.filter(
    (e) => e.approval?.status === 'APPROVED' || e.approval?.status === 'REJECTED'
  );

  const isRoleAuthorized = currentUser.role === 'approver' || currentUser.role === 'admin';

  const handleDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!selectedExec) return;
    setIsProcessing(true);
    setFeedback(null);
    try {
      await decideApproval(
        selectedExec.id,
        decision,
        decisionReason || (decision === 'APPROVED' ? 'Verified against purchase order.' : 'Budget cap exceeded.')
      );
      setFeedback(`Execution ${selectedExec.id} was ${decision} by ${currentUser.name}. Signed receipt generated!`);
      setSelectedExec(null);
      setDecisionReason('');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
          Governance Gate
        </span>
        <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
          Human-in-the-Loop Approval Center
        </h1>
        <p className="text-[16px] text-[#777b86]">
          Review and authorize high-value agent actions exceeding automatic threshold of Rp {policy.maxAutoAmountIdr.toLocaleString()}.
        </p>
      </div>

      {/* Role Authorization Alert */}
      {!isRoleAuthorized ? (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start justify-between gap-4 text-[13px] text-amber-900">
          <div className="flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Role Authorization Notice: </strong>
              You are currently signed in as <span className="font-mono underline">{currentUser.role}</span>. Organization policy requires <span className="font-mono">approver</span> or <span className="font-mono">admin</span> to sign off on executions.
            </div>
          </div>
          <span className="text-[12px] text-amber-800">
            (Use top role switcher to toggle to Sarah Jenkins - Approver)
          </span>
        </div>
      ) : (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center gap-2.5 text-[13px] text-emerald-900">
          <UserCheck className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>
            Authorized Signer: <strong className="font-semibold">{currentUser.name}</strong> ({currentUser.role}). Your cryptographic signature will bind the execution receipt.
          </span>
        </div>
      )}

      {feedback && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-[13px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{feedback}</span>
          </div>
          <Link href="/dashboard/trust" className="font-medium underline hover:text-emerald-950">
            View in Trust Explorer &rarr;
          </Link>
        </div>
      )}

      {/* Pending Items Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-[22px] text-[#17191c]">
            Pending Approvals ({pendingList.length})
          </h3>
          <span className="text-[12px] text-[#777b86]">
            Strict timeout and replay prevention enforced
          </span>
        </div>

        {pendingList.length === 0 ? (
          <div className="bg-[#fafafb] rounded-2xl p-10 border border-[#ececec] text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <h4 className="font-display text-[18px] text-[#17191c]">No Pending Invoices</h4>
            <p className="text-[13px] text-[#777b86]">
              All high-value agent actions have been resolved.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {pendingList.map((item) => (
              <div
                key={item.id}
                className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6"
              >
                <div className="space-y-2 max-w-xl">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-[12px] px-2.5 py-0.5 rounded-full bg-[#f2f2f3] text-[#17191c] font-medium border border-[#ececec]">
                      {item.id}
                    </span>
                    <span className="text-[12px] text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium">
                      {item.policyResult?.decision}
                    </span>
                    <span className="text-[12px] text-[#979799]">
                      Requested by {item.agentName}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[18px] font-semibold text-[#17191c] flex items-center gap-3">
                      <span>{item.payload.invoiceId}</span>
                      <span className="text-[#979799] font-normal">&bull;</span>
                      <span>{item.payload.vendor}</span>
                      <span className="text-[#979799] font-normal">&bull;</span>
                      <span className="font-mono text-emerald-800">
                        Rp {item.payload.amountIdr.toLocaleString()}
                      </span>
                    </div>
                    <p className="text-[13px] text-[#777b86]">{item.payload.description}</p>
                  </div>

                  <div className="text-[12px] text-amber-900 bg-amber-50/70 p-2.5 rounded-xl border border-amber-200/60">
                    <strong>Gate Reason:</strong> {item.policyResult?.reason}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <button
                    disabled={!isRoleAuthorized}
                    onClick={() => setSelectedExec(item)}
                    className="pill-button-filled !h-10 !px-5 !text-[13px] disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Review & Decide &rarr;
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Decision Review Modal */}
      {selectedExec && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-[24px] max-w-xl w-full p-6 shadow-2xl border border-[#ececec] space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between border-b border-[#ececec] pb-4">
              <div>
                <span className="text-[11px] font-semibold text-[#979799] uppercase tracking-wider">
                  Reviewing Execution Authorization
                </span>
                <h3 className="font-display text-[22px] text-[#17191c]">
                  Invoice {selectedExec.payload.invoiceId}
                </h3>
              </div>
              <button
                onClick={() => setSelectedExec(null)}
                className="text-[#777b86] hover:text-[#17191c] text-[18px]"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-[13px]">
              <div className="grid grid-cols-2 gap-3 p-4 bg-[#fafafb] rounded-xl border border-[#ececec]">
                <div>
                  <span className="text-[#979799] block text-[11px] uppercase">Vendor</span>
                  <span className="font-medium text-[#17191c]">{selectedExec.payload.vendor}</span>
                </div>
                <div>
                  <span className="text-[#979799] block text-[11px] uppercase">Amount</span>
                  <span className="font-mono font-medium text-emerald-800 text-[14px]">
                    Rp {selectedExec.payload.amountIdr.toLocaleString()}
                  </span>
                </div>
                <div className="col-span-2">
                  <span className="text-[#979799] block text-[11px] uppercase">Agent Tool Proposal</span>
                  <span className="font-mono text-[#17191c]">
                    {selectedExec.proposal?.name}(invoice_id: &quot;{selectedExec.payload.invoiceId}&quot;)
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-[#17191c]">
                  Signer Reason / Audit Note
                </label>
                <textarea
                  rows={2}
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="e.g. Verified against supplier contract schedule and Q4 budget allocation."
                  className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl p-3 text-[13px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
                />
              </div>

              <div className="text-[12px] text-[#777b86] italic">
                * Approval will invoke the simulated <code className="font-mono">approve_invoice</code> tool in the Harness and issue a signed Ed25519 receipt anchored to the Besu private ledger.
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#ececec]">
              <button
                type="button"
                onClick={() => setSelectedExec(null)}
                className="pill-button-ghost !h-10 !px-4 !text-[13px]"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleDecision('REJECTED')}
                className="px-5 py-2 rounded-full border border-rose-300 text-rose-700 hover:bg-rose-50 text-[13px] font-medium transition-colors"
              >
                Reject Invoice
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleDecision('APPROVED')}
                className="pill-button-filled !h-10 !px-6 !text-[13px] bg-emerald-700 hover:bg-emerald-800 border-emerald-700"
              >
                {isProcessing ? 'Anchoring...' : 'Authorize & Sign'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resolved History Table */}
      <div className="space-y-3 pt-6 border-t border-[#ececec]">
        <h3 className="font-display text-[22px] text-[#17191c]">
          Resolved Approval History ({resolvedList.length})
        </h3>
        <div className="bg-white rounded-2xl border border-[#ececec] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-[#ececec] bg-[#fafafb] text-[#979799]">
                <th className="px-6 py-3.5">Execution</th>
                <th className="px-6 py-3.5">Invoice / Vendor</th>
                <th className="px-6 py-3.5">Amount</th>
                <th className="px-6 py-3.5">Decision</th>
                <th className="px-6 py-3.5">Decided By</th>
                <th className="px-6 py-3.5">Audit Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ececec]">
              {resolvedList.map((item) => (
                <tr key={item.id} className="hover:bg-[#fafafb]">
                  <td className="px-6 py-4 font-mono font-medium text-[#17191c]">{item.id}</td>
                  <td className="px-6 py-4">
                    <span className="font-medium text-[#17191c]">{item.payload.invoiceId}</span> &bull; {item.payload.vendor}
                  </td>
                  <td className="px-6 py-4 font-mono">Rp {item.payload.amountIdr.toLocaleString()}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                      item.approval?.status === 'APPROVED'
                        ? 'bg-emerald-50 text-emerald-800'
                        : 'bg-rose-50 text-rose-800'
                    }`}>
                      {item.approval?.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-medium text-[#17191c]">{item.approval?.decidedBy}</span>
                    <span className="text-[#979799] text-[11px] block">{item.approval?.decidedRole}</span>
                  </td>
                  <td className="px-6 py-4 text-[#777b86] max-w-xs truncate" title={item.approval?.reason}>
                    {item.approval?.reason || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
