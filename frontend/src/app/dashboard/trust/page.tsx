'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/store';
import { IS_ENTERPRISE } from '@/lib/api';
import ReceiptViewer from '@/components/ReceiptViewer';
import { ShieldCheck, Fingerprint } from 'lucide-react';

export default function TrustExplorerPage() {
  const { executions } = useApp();

  // Find all executions that have receipts
  const receiptsList = executions
    .filter((e) => e.receipt)
    .map((e) => e.receipt!);

  const [selectedReceiptId, setSelectedReceiptId] = useState<string>(
    receiptsList[0]?.receiptId || ''
  );

  const activeReceipt = receiptsList.find((r) => r.receiptId === selectedReceiptId) || receiptsList[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#6D7344] uppercase tracking-wider">
          Cryptographic Provenance
        </span>
        <h1 className="font-display text-[44px] text-[#192319] leading-[1.1] tracking-[-0.66px]">
          Public Trust Explorer
        </h1>
        <p className="text-[16px] text-[#2D372D]">
          {IS_ENTERPRISE
            ? 'Independently verify Ed25519 signatures, RFC 8785 canonical hashes, and cryptographic ledger anchors.'
            : 'Independently verify Ed25519 signatures, RFC 8785 canonical hashes, and local mock anchors.'}
        </p>
      </div>

      {/* Honest Boundary Clarification (Threat Model Rule!) */}
      <div className="p-4 rounded-2xl bg-[#F3FFCC] text-[#043423] border border-[#ABE082] space-y-1 text-[13px]">
        <strong className="font-medium text-[14px] flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-[#043423]" />
          Verification Semantics:
        </strong>
        <p className="leading-relaxed">
          &quot;VALID&quot; establishes byte-for-byte record integrity, server key authenticity, and on-chain immutability. It proves what policy was evaluated and what tool was executed. It does <em>not</em> imply that upstream LLM reasoning or invoices were factually truthful.
        </p>
      </div>

      {/* Receipt Selector Tabs */}
      <div className="space-y-3">
        <span className="text-[12px] font-semibold uppercase tracking-wider text-[#6D7344]">
          Select Evidence Record ({receiptsList.length} Anchored)
        </span>
        <div className="flex flex-wrap gap-2.5">
          {receiptsList.map((r) => (
            <button
              key={r.receiptId}
              onClick={() => setSelectedReceiptId(r.receiptId)}
              className={`px-4 py-2 rounded-xl text-[13px] font-mono transition-all flex items-center gap-2 border ${
                activeReceipt?.receiptId === r.receiptId
                  ? 'bg-[#192319] text-white border-[#192319] shadow-sm'
                  : 'bg-white text-[#192319] border-[#DCDCD7] hover:bg-[#F8F8F8]'
              }`}
            >
              <Fingerprint className="w-3.5 h-3.5" />
              <span>{r.receiptId}</span>
              <span className="text-[11px] opacity-70">
                (Block #{r.anchor.blockNumber})
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Receipt Viewer Component */}
      {activeReceipt ? (
        <ReceiptViewer
          key={activeReceipt.receiptId}
          receipt={activeReceipt}
        />
      ) : (
        <div className="bg-[#F8F8F8] rounded-2xl p-12 border border-[#DCDCD7] text-center space-y-2">
          <p className="text-[14px] text-[#2D372D]">
            No anchored receipts found. Execute an invoice task in the Task Center first!
          </p>
        </div>
      )}
    </div>
  );
}
