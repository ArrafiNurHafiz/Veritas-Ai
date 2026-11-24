'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/store';
import { ExecutionRecord } from '@/lib/types';
import StateTimeline from '@/components/StateTimeline';
import ReceiptViewer from '@/components/ReceiptViewer';
import { 
  Send, 
  Check, 
  Lock, 
  AlertCircle 
} from 'lucide-react';

export default function TaskCenterPage() {
  const { policy, submitTask, currentUser } = useApp();

  const [invoiceId, setInvoiceId] = useState('INV-2036-009');
  const [vendor, setVendor] = useState('V-ABC');
  const [amountIdr, setAmountIdr] = useState(8500000);
  const [description, setDescription] = useState('Quarterly Datacenter Server Infrastructure Maintenance');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [currentExecution, setCurrentExecution] = useState<ExecutionRecord | null>(null);

  const isAuthorized = currentUser.role === 'operator' || currentUser.role === 'admin';

  const presets = [
    {
      title: 'Auto-Approval Flow',
      amount: 3200000,
      vendor: 'V-ABC',
      desc: 'Monthly cloud backup storage quota (Under 5M threshold)',
      expected: 'ALLOWED &rarr; Auto-executed',
    },
    {
      title: 'Approval Gate Flow',
      amount: 8500000,
      vendor: 'V-ABC',
      desc: 'Enterprise hardware server expansion (Over 5M threshold)',
      expected: 'APPROVAL_REQUIRED &rarr; Gate held',
    },
    {
      title: 'High-Value Unverified Vendor',
      amount: 14500000,
      vendor: 'V-EVIL',
      desc: 'Emergency hardware import order (Over limit + unlisted)',
      expected: 'DENIED &rarr; Unlisted vendor blocked',
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthorized) {
      setSubmitError(`Role "${currentUser.role}" is not permitted to submit tasks. Switch to Operator or Admin.`);
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const res = await submitTask({
        agentId: 'procurement-agent',
        invoiceId,
        vendor,
        amountIdr: Number(amountIdr),
        description,
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
        <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
          Task Orchestration
        </span>
        <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
          Procurement Task Center
        </h1>
        <p className="text-[16px] text-[#777b86]">
          Dispatch procurement invoice validation requests to autonomous agents and monitor policy mediation.
        </p>
      </div>

      {/* Role Authorization Alert */}
      {!isAuthorized ? (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start justify-between gap-4 text-[13px] text-amber-900">
          <div className="flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Role Authorization Notice: </strong>
              You are signed in as <span className="font-mono underline">{currentUser.name} ({currentUser.role})</span>. In accordance with enterprise separation of duties, only <span className="font-mono font-medium">operator</span> or <span className="font-mono font-medium">admin</span> can dispatch procurement tasks.
            </div>
          </div>
          <span className="text-[12px] text-amber-800 shrink-0">
            (Switch to Marcus Vance - Operator via header)
          </span>
        </div>
      ) : (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-between text-[13px] text-emerald-900">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Authorized Operator: <strong>{currentUser.name}</strong> ({currentUser.role}). Live dispatch to Harness Gateway is active.</span>
          </div>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
            Bearer tok-{currentUser.role}
          </span>
        </div>
      )}

      {submitError && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-[13px] flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* Preset Buttons */}
      <div className="space-y-2">
        <span className="text-[12px] font-semibold uppercase tracking-wider text-[#979799]">
          Fast Demo Scenarios (Click to Preload)
        </span>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {presets.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setAmountIdr(p.amount);
                setVendor(p.vendor);
                setDescription(p.desc);
                setInvoiceId('INV-2036-0' + Math.floor(10 + Math.random() * 90));
              }}
              className="text-left p-3.5 rounded-2xl bg-[#fafafb] border border-[#ececec] hover:border-[#17191c] hover:bg-white transition-all space-y-1 group"
            >
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-medium text-[#17191c] group-hover:underline">
                  {p.title}
                </span>
                <span className="font-mono text-[12px] text-[#17191c]">
                  Rp {p.amount.toLocaleString()}
                </span>
              </div>
              <p className="text-[11px] text-[#777b86] leading-snug">{p.desc}</p>
              <div
                className="text-[11px] text-amber-800 font-medium pt-1"
                dangerouslySetInnerHTML={{ __html: p.expected }}
              />
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Task Form */}
        <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-6">
          <div className="space-y-1">
            <h3 className="font-display text-[22px] text-[#17191c]">Submit Procurement Task</h3>
            <p className="text-[13px] text-[#777b86]">
              Submits request to <code className="font-mono text-[#17191c]">POST /api/v1/tasks</code>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium text-[#17191c]">Assigned Agent</label>
              <div className="p-3 rounded-xl bg-[#fafafb] border border-[#ececec] text-[13px] flex items-center justify-between">
                <div>
                  <span className="font-medium text-[#17191c]">Procurement Agent</span>
                  <span className="text-[#777b86] ml-2">(v1.2.0 • Operational)</span>
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                  Tool: approve_invoice
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-[#17191c]">Invoice Reference ID</label>
                <input
                  type="text"
                  required
                  value={invoiceId}
                  onChange={(e) => setInvoiceId(e.target.value)}
                  className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[14px] font-mono text-[#17191c] focus:outline-none focus:border-[#17191c]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-[#17191c]">Supplier / Vendor</label>
                <input
                  type="text"
                  required
                  value={vendor}
                  onChange={(e) => setVendor(e.target.value)}
                  className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[14px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[13px] font-medium text-[#17191c]">Invoice Amount (IDR)</label>
                <span className="text-[12px] text-[#777b86]">
                  Threshold: Rp {policy.maxAutoAmountIdr.toLocaleString()}
                </span>
              </div>
              <input
                type="number"
                required
                min={0}
                value={amountIdr}
                onChange={(e) => setAmountIdr(Number(e.target.value))}
                className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[15px] font-mono text-[#17191c] focus:outline-none focus:border-[#17191c]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-medium text-[#17191c]">Description / Purpose</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl p-3 text-[13px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
              />
            </div>

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
                  : 'Submit Task for Execution'}
              </span>
            </button>
          </form>
        </div>

        {/* Live Execution Output Result */}
        <div className="space-y-6">
          {currentExecution ? (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#ececec] pb-4">
                  <div>
                    <span className="text-[11px] font-semibold text-[#979799] uppercase tracking-wider">
                      Execution Result
                    </span>
                    <h3 className="font-display text-[22px] text-[#17191c]">
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
                <div className="p-4 rounded-xl bg-[#fafafb] border border-[#ececec] space-y-2 text-[13px]">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-[#17191c]">Policy Engine Decision:</span>
                    <strong className="text-[#17191c] font-mono">
                      {currentExecution.policyResult?.decision}
                    </strong>
                  </div>
                  <p className="text-[#777b86]">
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
            <div className="bg-[#fafafb] rounded-2xl p-12 border border-[#ececec] text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-white border border-[#ececec] flex items-center justify-center mx-auto text-[#777b86]">
                <Send className="w-5 h-5" />
              </div>
              <h4 className="font-display text-[20px] text-[#17191c]">Ready for Dispatch</h4>
              <p className="text-[13px] text-[#777b86] max-w-sm mx-auto">
                Select a fast demo scenario on top or fill out the form to watch the deterministic policy gate in action.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
