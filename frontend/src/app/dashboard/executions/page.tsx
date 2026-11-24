'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/store';
import { ExecutionRecord } from '@/lib/types';
import StateTimeline from '@/components/StateTimeline';
import ReceiptViewer from '@/components/ReceiptViewer';
import { 
  Search, 
  ShieldCheck, 
  X
} from 'lucide-react';

export default function ExecutionMonitorPage() {
  const { executions } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedExec, setSelectedExec] = useState<ExecutionRecord | null>(null);

  const filtered = executions.filter((item) => {
    const matchesSearch = 
      item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.payload.invoiceId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.payload.vendor.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'ALL' || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
          Runtime Observability
        </span>
        <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
          Execution Monitor
        </h1>
        <p className="text-[16px] text-[#777b86]">
          Inspect state machine transitions, event digests, and immutable signed evidence.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white p-4 rounded-2xl border border-[#ececec]">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-[#777b86] absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search execution, invoice, or vendor..."
            className="w-full pl-10 pr-4 py-2 bg-[#fafafb] border border-[#ececec] rounded-xl text-[13px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'SUCCEEDED', 'WAITING_APPROVAL', 'REJECTED', 'DENIED'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-full text-[12px] font-medium transition-all ${
                statusFilter === s
                  ? 'bg-[#17191c] text-white'
                  : 'bg-[#f2f2f3] text-[#777b86] hover:bg-[#e8e8e9]'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-[#ececec] overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-[#ececec] bg-[#fafafb] text-[#979799]">
                <th className="px-6 py-3.5">ID</th>
                <th className="px-6 py-3.5">Invoice / Vendor</th>
                <th className="px-6 py-3.5">Amount</th>
                <th className="px-6 py-3.5">Decision</th>
                <th className="px-6 py-3.5">State Machine</th>
                <th className="px-6 py-3.5">Evidence Anchor</th>
                <th className="px-6 py-3.5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ececec]">
              {filtered.map((item) => (
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
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#f2f2f3] text-[#17191c]">
                      {item.policyResult?.decision}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 text-[12px] font-medium ${
                      item.status === 'SUCCEEDED' ? 'text-emerald-700' :
                      item.status === 'WAITING_APPROVAL' ? 'text-amber-700' : 'text-rose-700'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        item.status === 'SUCCEEDED' ? 'bg-emerald-500' :
                        item.status === 'WAITING_APPROVAL' ? 'bg-amber-500' : 'bg-rose-500'
                      }`}></span>
                      {item.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {item.receipt ? (
                      <span className="text-[12px] text-emerald-700 font-medium flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        {item.receipt.anchor.status || 'PENDING'}
                      </span>
                    ) : (
                      <span className="text-[12px] text-[#979799]">None</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setSelectedExec(item)}
                      className="px-3 py-1 rounded-full bg-[#f2f2f3] hover:bg-[#e8e8e9] text-[12px] font-medium text-[#17191c] transition-colors"
                    >
                      Inspect &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedExec && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-[24px] max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl border border-[#ececec] space-y-6 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between border-b border-[#ececec] pb-4">
              <div>
                <span className="text-[11px] font-semibold text-[#979799] uppercase tracking-wider">
                  Execution Inspector
                </span>
                <h3 className="font-display text-[24px] text-[#17191c]">
                  {selectedExec.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedExec(null)}
                className="text-[#777b86] hover:text-[#17191c] text-[20px]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* State Machine Stepper */}
            <StateTimeline
              events={selectedExec.events}
              currentStatus={selectedExec.status}
            />

            {/* Payload details */}
            <div className="p-4 rounded-xl bg-[#fafafb] border border-[#ececec] space-y-2 text-[13px]">
              <span className="font-semibold text-[#17191c] block">Tool Call Proposal:</span>
              <pre className="font-mono text-[12px] p-3 rounded-lg bg-white border border-[#ececec] overflow-x-auto">
                {JSON.stringify(selectedExec.proposal, null, 2)}
              </pre>
            </div>

            {/* Receipt if present */}
            {selectedExec.receipt && (
              <ReceiptViewer receipt={selectedExec.receipt} />
            )}

            <div className="flex justify-end pt-4 border-t border-[#ececec]">
              <button
                onClick={() => setSelectedExec(null)}
                className="pill-button-filled !h-10 !px-5 !text-[13px]"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
