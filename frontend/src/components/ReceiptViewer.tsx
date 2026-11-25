'use client';

import React, { useState, useEffect } from 'react';
import { ExecutionReceipt } from '@/lib/types';
import { verifyReceiptPayload, VerificationResult } from '@/lib/crypto';
import { IS_ENTERPRISE } from '@/lib/api';
import {
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  AlertTriangle,
  FileCode,
  RefreshCw,
  Fingerprint,
} from 'lucide-react';

interface ReceiptViewerProps {
  receipt: ExecutionReceipt;
  onReceiptUpdated?: (updatedReceipt: ExecutionReceipt) => void;
}

export default function ReceiptViewer({ receipt }: ReceiptViewerProps) {
  const [copied, setCopied] = useState(false);
  const [isTampered, setIsTampered] = useState(false);
  const [currentCanonicalJson, setCurrentCanonicalJson] = useState(receipt.canonicalJson);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const handleVerify = async (jsonToTest: string, useStoredVerification = true) => {
    setIsVerifying(true);
    try {
      const res = await verifyReceiptPayload(
        jsonToTest,
        receipt.receiptDigest,
        receipt.signature,
        receipt.anchor.status,
        {
          keyId: receipt.keyId,
          receiptId: receipt.receiptId,
          useStoredVerification,
        },
      );
      setVerification(res);
    } finally {
      setIsVerifying(false);
    }
  };

  // Reset the sandbox whenever a different receipt is selected.
  useEffect(() => {
    let active = true;
    verifyReceiptPayload(
      receipt.canonicalJson,
      receipt.receiptDigest,
      receipt.signature,
      receipt.anchor.status,
      {
        keyId: receipt.keyId,
        receiptId: receipt.receiptId,
        useStoredVerification: true,
      },
    ).then((res) => {
      if (active) setVerification(res);
    });
    return () => {
      active = false;
    };
  }, [receipt]);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(currentCanonicalJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTamperToggle = () => {
    if (!isTampered) {
      const tamperedJson = currentCanonicalJson.replace(
        'procurement-agent',
        'procurement-agent-MALICIOUS',
      );
      setCurrentCanonicalJson(tamperedJson);
      setIsTampered(true);
      void handleVerify(tamperedJson, false);
    } else {
      setCurrentCanonicalJson(receipt.canonicalJson);
      setIsTampered(false);
      void handleVerify(receipt.canonicalJson, true);
    }
  };

  const anchorStatus = verification?.anchorStatus || receipt.anchor.status;
  const integrityFailed =
    isTampered || (verification !== null && (!verification.hashMatches || !verification.signatureValid));
  const anchorPending =
    anchorStatus === 'PENDING' || anchorStatus === 'FAILED' || anchorStatus === 'NOT_REQUESTED';

  let badge: { label: string; ok: boolean } = { label: 'VERIFICATION PENDING', ok: false };
  if (verification?.verified && !isTampered) {
    badge = { label: 'CRYPTOGRAPHICALLY VALID', ok: true };
  } else if (integrityFailed) {
    badge = { label: 'VERIFICATION FAILED (INTEGRITY)', ok: false };
  } else if (anchorPending) {
    badge = { label: 'NOT VERIFIED — MOCK ANCHOR PENDING', ok: false };
  } else if (verification) {
    badge = { label: 'NOT VERIFIED', ok: false };
  }

  return (
    <div className="bg-white rounded-2xl border border-[#ececec] overflow-hidden shadow-sm">
      <div className="p-6 border-b border-[#ececec] flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#fafafb]">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <Fingerprint className="w-5 h-5 text-[#17191c]" />
            <h3 className="font-display text-[22px] text-[#17191c]">Execution Receipt</h3>
            <span className="font-mono text-[12px] px-2.5 py-0.5 rounded-full bg-[#f2f2f3] text-[#777b86] border border-[#ececec]">
              {receipt.receiptId}
            </span>
          </div>
          <p className="text-[13px] text-[#777b86]">
            Canonical RFC 8785 evidence signed by Ed25519 key ID{' '}
            <code className="font-mono text-[#17191c]">{receipt.keyId}</code>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-[13px] font-medium ${
              badge.ok
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-amber-50 text-amber-900 border-amber-200'
            }`}
          >
            {badge.ok ? (
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-amber-600" />
            )}
            <span>{badge.label}</span>
          </div>
          <button
            onClick={() => void handleVerify(currentCanonicalJson, !isTampered)}
            disabled={isVerifying}
            className="p-2 rounded-full hover:bg-white text-[#777b86] hover:text-[#17191c] border border-transparent hover:border-[#ececec] transition-all"
            title="Re-run verification"
          >
            <RefreshCw className={`w-4 h-4 ${isVerifying ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div
        className={`p-4 border-b text-[13px] flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          isTampered
            ? 'bg-amber-50/80 border-amber-200 text-amber-900'
            : 'bg-[#f2f2f3]/50 border-[#ececec] text-[#777b86]'
        }`}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className={`w-4 h-4 ${isTampered ? 'text-amber-600' : 'text-[#777b86]'}`} />
          <span>
            {isTampered
              ? 'Tamper Active: the payload was altered. Integrity checks must reject it.'
              : 'Interactive Verification Sandbox: test what happens when stored evidence is modified.'}
          </span>
        </div>
        <button
          onClick={handleTamperToggle}
          className={`px-3 py-1.5 rounded-full text-[12px] font-medium transition-all ${
            isTampered
              ? 'bg-amber-600 text-white hover:bg-amber-700'
              : 'bg-white border border-[#17191c] text-[#17191c] hover:bg-[#17191c] hover:text-white'
          }`}
        >
          {isTampered ? 'Restore Original Evidence' : 'Simulate Payload Tampering'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#ececec] border-b border-[#ececec]">
        <div className="p-4 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
              1. SHA-256 Digest
            </span>
            {verification?.hashMatches ? (
              <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
                <Check className="w-3 h-3" /> Matched
              </span>
            ) : (
              <span className="text-[11px] text-rose-600 font-medium flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Mismatch
              </span>
            )}
          </div>
          <p className="font-mono text-[11px] text-[#17191c] truncate" title={verification?.computedHash}>
            {verification?.computedHash || receipt.receiptDigest}
          </p>
        </div>

        <div className="p-4 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
              2. Ed25519 Signature
            </span>
            {verification?.signatureValid ? (
              <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
                <Check className="w-3 h-3" /> Verified
              </span>
            ) : (
              <span className="text-[11px] text-rose-600 font-medium flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Invalid
              </span>
            )}
          </div>
          <p className="font-mono text-[11px] text-[#17191c] truncate" title={receipt.signature}>
            {receipt.signature}
          </p>
        </div>

        <div className="p-4 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
              {IS_ENTERPRISE ? '3. Cryptographic Anchor' : '3. Local Mock Anchor'}
            </span>
            <span
              className={`text-[11px] font-medium ${
                anchorStatus === 'CONFIRMED' ? 'text-emerald-600' : 'text-amber-700'
              }`}
            >
              {anchorStatus || 'UNKNOWN'}
            </span>
          </div>
          <p className="font-mono text-[11px] text-[#17191c] truncate" title={receipt.anchor.txHash}>
            Tx: {receipt.anchor.txHash || 'not anchored'}
          </p>
        </div>
      </div>

      <div className="p-6 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[13px] font-medium text-[#17191c]">
            <FileCode className="w-4 h-4 text-[#777b86]" />
            <span>Canonical JSON Payload (RFC 8785 format)</span>
          </div>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1.5 text-[12px] text-[#777b86] hover:text-[#17191c] px-2.5 py-1 rounded-md hover:bg-[#f2f2f3] transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Canonical JSON'}</span>
          </button>
        </div>

        <pre className="p-4 rounded-xl bg-[#fafafb] border border-[#ececec] text-[12px] font-mono text-[#17191c] overflow-x-auto leading-relaxed whitespace-pre-wrap break-all">
          {currentCanonicalJson}
        </pre>

        {verification && (
          <div className="mt-4 p-3.5 rounded-xl bg-[#f2f2f3] text-[12px] text-[#777b86] space-y-1">
            <span className="font-semibold text-[#17191c] block">Audit Diagnostics:</span>
            {verification.details.map((msg, i) => (
              <p key={i} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#17191c]"></span>
                {msg}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
