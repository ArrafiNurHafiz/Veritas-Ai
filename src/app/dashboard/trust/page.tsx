'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/store';
import ReceiptViewer from '@/components/ReceiptViewer';
import { ShieldCheck, Search, Database, Lock, Fingerprint } from 'lucide-react';

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
        <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
          Cryptographic Provenance
        </span>
        <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
          Public Trust Explorer
        </h1>
        <p className="text-[16px] text-[#777b86]">
          Independently verify Ed25519 signatures, RFC 8785 canonical hashes, and Hyperledger Besu on-chain anchors.
        </p>
      </div>

      {/* Honest Boundary Clarification (Threat Model Rule!) */}
      <div className="p-4 rounded-2xl bg-[#fbe1d1] text-[#5d2a1a] border border-[#f5cfb8] space-y-1 text-[13px]">
        <strong className="font-medium text-[14px] flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-[#5d2a1a]" />
          Verification Semantics:
        </strong>
        <p className="leading-relaxed">
          &quot;VALID&quot; establishes byte-for-byte record integrity, server key authenticity, and on-chain immutability. It proves what policy was evaluated and what tool was executed. It does <em>not</em> imply that upstream LLM reasoning or invoices were factually truthful.
        </p>
      </div>

      {/* Receipt Selector Tabs */}
      <div className="space-y-3">
        <span className="text-[12px] font-semibold uppercase tracking-wider text-[#979799]">
          Select Evidence Record ({receiptsList.length} Anchored)
        </span>
        <div className="flex flex-wrap gap-2.5">
          {receiptsList.map((r) => (
            <button
              key={r.receiptId}
              onClick={() => setSelectedReceiptId(r.receiptId)}
              className={`px-4 py-2 rounded-xl text-[13px] font-mono transition-all flex items-center gap-2 border ${
                activeReceipt?.receiptId === r.receiptId
                  ? 'bg-[#17191c] text-white border-[#17191c] shadow-sm'
                  : 'bg-white text-[#17191c] border-[#ececec] hover:bg-[#fafafb]'
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
        <ReceiptViewer receipt={activeReceipt} />
      ) : (
        <div className="bg-[#fafafb] rounded-2xl p-12 border border-[#ececec] text-center space-y-2">
          <p className="text-[14px] text-[#777b86]">
            No anchored receipts found. Execute an invoice task in the Task Center first!
          </p>
        </div>
      )}
    </div>
  );
}
