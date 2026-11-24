'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function AxiomFeatureDeepDives() {
  // Feature 1: Policy Gate Slider & Vendor
  const [vendor, setVendor] = useState<'V-ABC' | 'V-XYZ' | 'V-MALICIOUS'>('V-ABC');
  const [amount, setAmount] = useState<number>(8500000);

  const isVendorAllowed = vendor !== 'V-MALICIOUS';
  const policyDecision: 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED' = !isVendorAllowed
    ? 'DENIED'
    : amount <= 5000000
      ? 'ALLOWED'
      : amount <= 25000000
        ? 'APPROVAL_REQUIRED'
        : 'DENIED';

  const reasonCode = !isVendorAllowed
    ? 'VENDOR_NOT_ALLOWLISTED'
    : amount > 25000000
      ? 'HARD_CAP_EXCEEDED (>25M)'
      : amount > 5000000
        ? 'AMOUNT_ABOVE_AUTO_CEILING (>5M)'
        : 'WITHIN_AUTOMATIC_LIMIT (<=5M)';

  // Feature 2: Human Sign-Off State
  const [approvalAction, setApprovalAction] = useState<'PENDING' | 'APPROVED' | 'REJECTED'>('PENDING');

  // Feature 3: Tamper Byte State
  const [isTampered, setIsTampered] = useState<boolean>(false);

  return (
    <div id="features" className="bg-[#08090A] text-[#EDEDED]">
      {/* ========================================================================= */}
      {/* FEATURE 1: NO ACTION LEFT UNGUARDED (DETERMINISTIC POLICY GATE)            */}
      {/* ========================================================================= */}
      <section className="border-b border-[#1A1C22] py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-16">
            {/* Left copy */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="lg:col-span-5"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
                01 · Deterministic Policy Gate
              </span>
              <h2 className="mt-4 text-[32px] font-medium leading-[1.08] tracking-[-0.03em] text-white sm:text-[44px]">
                No action left <br />
                <span className="text-[#DA5C2B]">unguarded.</span>
              </h2>
              <p className="mt-5 text-[15px] leading-relaxed text-[#8F94A0]">
                Every tool proposal is intercepted prior to execution. Policies are strictly evaluated in deterministic code—never delegated to probabilistic model completions. Deny-by-default with configurable ceilings.
              </p>
              
              <ul className="mt-6 space-y-2.5 font-mono text-[12px] text-[#A6ABB7]">
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
                  <span>Sub-millisecond execution overhead (&lt;2ms)</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
                  <span>Vendor allowlists &amp; hard ceiling thresholds</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
                  <span>Zero unauthorized tool calls reach production</span>
                </li>
              </ul>

              <div className="mt-8">
                <Link
                  href="/dashboard/policies"
                  className="group inline-flex items-center gap-1.5 text-[13px] font-medium text-[#DA5C2B] hover:underline"
                >
                  <span>Configure custom policy rules</span>
                  <span aria-hidden="true" className="axiom-btn-arrow font-mono">
                    <span className="arrow-primary">→</span>
                    <span className="arrow-secondary">→</span>
                  </span>
                </Link>
              </div>
            </motion.div>

            {/* Right Interactive Simulator */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="lg:col-span-7"
            >
              <div className="axiom-frame overflow-hidden rounded-xl border border-[#20232C] bg-[#0C0D11] p-6 shadow-2xl hover:border-[#DA5C2B]/30 transition-colors">
                <div className="flex items-center justify-between border-b border-[#1E2129] pb-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-[#DA5C2B]" />
                    <span className="font-mono text-[12px] font-medium text-white">
                      policy.evaluate() Playground
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-[#555A67]">Live simulation</span>
                </div>

                <div className="mt-6 space-y-5">
                  {/* Vendor selector */}
                  <div>
                    <label className="block font-mono text-[11px] uppercase tracking-wider text-[#7D828F]">
                      Target Vendor
                    </label>
                    <div className="mt-2 grid grid-cols-3 gap-2 font-mono text-[12px]">
                      {(['V-ABC', 'V-XYZ', 'V-MALICIOUS'] as const).map((v) => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => setVendor(v)}
                          className={`rounded-md border px-3 py-2 text-left transition-all ${
                            vendor === v
                              ? 'border-[#DA5C2B] bg-[#DA5C2B]/10 text-white shadow-[0_0_12px_rgba(218,92,43,0.15)]'
                              : 'border-[#20232C] bg-[#0E1015] text-[#8F94A0] hover:border-[#303440]'
                          }`}
                        >
                          <div className="font-semibold">{v}</div>
                          <div className="text-[10px] text-[#5A606E]">
                            {v === 'V-MALICIOUS' ? 'Unlisted' : 'Allowlisted'}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Amount slider */}
                  <div>
                    <div className="flex items-center justify-between font-mono text-[12px]">
                      <span className="text-[#7D828F]">Proposal Amount:</span>
                      <span className="font-semibold text-white">IDR {amount.toLocaleString()}</span>
                    </div>
                    <input
                      type="range"
                      min={1000000}
                      max={30000000}
                      step={500000}
                      value={amount}
                      onChange={(e) => setAmount(Number(e.target.value))}
                      className="mt-2 w-full accent-[#DA5C2B] cursor-pointer"
                    />
                    <div className="mt-1 flex justify-between font-mono text-[10px] text-[#5A606E]">
                      <span>1M</span>
                      <span className="text-[#22C55E]">5M (Auto Ceiling)</span>
                      <span className="text-[#EF4444]">25M (Hard Cap)</span>
                      <span>30M</span>
                    </div>
                  </div>

                  {/* Reactive Policy Output Box */}
                  <motion.div
                    key={`${vendor}-${amount}`}
                    initial={{ scale: 0.99, opacity: 0.8 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.15 }}
                    className="rounded-lg border border-[#1E2129] bg-[#060709] p-4 font-mono text-[12px]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[#5A606E]">VERDICT RESULT</span>
                      <span
                        className={`rounded px-2.5 py-0.5 text-[11px] font-semibold transition-colors ${
                          policyDecision === 'ALLOWED'
                            ? 'bg-[#22C55E]/10 text-[#22C55E] border border-[#22C55E]/30'
                            : policyDecision === 'APPROVAL_REQUIRED'
                              ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30'
                              : 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/30'
                        }`}
                      >
                        {policyDecision}
                      </span>
                    </div>
                    <div className="mt-3 text-[11px] leading-relaxed text-[#A6ABB7]">
                      Reason Code: <span className="text-white">{reasonCode}</span>
                    </div>
                    <div className="mt-2 text-[10px] text-[#5A606E]">
                      Harness Action: {policyDecision === 'ALLOWED' ? 'Pass tool call with generated Ed25519 receipt' : policyDecision === 'APPROVAL_REQUIRED' ? 'Queue in human authorization ledger (hold execution)' : 'Immediate 403 Forbidden rejection'}
                    </div>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* FEATURE 2: HUMAN APPROVAL GATE (A PERSON HOLDS THE GATE)                  */}
      {/* ========================================================================= */}
      <section className="border-b border-[#1A1C22] py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-16">
            {/* Left Interactive Approval Card */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="order-2 lg:order-1 lg:col-span-7"
            >
              <div className="axiom-frame overflow-hidden rounded-xl border border-[#20232C] bg-[#0C0D11] p-6 shadow-2xl hover:border-[#F59E0B]/30 transition-colors">
                <div className="flex items-center justify-between border-b border-[#1E2129] pb-4">
                  <div className="flex items-center gap-2 font-mono text-[12px]">
                    <span className="h-2 w-2 rounded-full bg-[#F59E0B]" />
                    <span className="font-medium text-white">approval.queue · Task #APR-2036-001</span>
                  </div>
                  <span className="font-mono text-[11px] text-[#F59E0B] bg-[#F59E0B]/10 px-2 py-0.5 rounded">
                    {approvalAction === 'PENDING' ? 'WAITING SIGN-OFF' : approvalAction}
                  </span>
                </div>

                <div className="mt-5 space-y-4 font-mono text-[12px]">
                  <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-[#8F94A0]">Proposal: Review Invoice INV-2036-001</span>
                      <span className="text-white font-bold">IDR 8,500,000</span>
                    </div>
                    <p className="mt-2 text-[11px] text-[#5A606E]">
                      Requested by <span className="text-[#A6ABB7]">agent.procurement_bot</span> for allowlisted vendor <span className="text-[#DA5C2B]">V-ABC</span>.
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="rounded-lg border border-[#1E2129] bg-[#060709] p-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="text-[11px] text-[#7D828F]">Authorized Approver:</div>
                        <div className="text-[13px] font-semibold text-white">Sarah Jenkins (Role: Approver)</div>
                      </div>

                      <div className="flex items-center gap-2">
                        {approvalAction === 'PENDING' ? (
                          <>
                            <button
                              type="button"
                              onClick={() => setApprovalAction('REJECTED')}
                              className="rounded-md border border-[#EF4444]/40 bg-[#EF4444]/10 px-3 py-1.5 text-[11px] font-medium text-[#EF4444] transition-all hover:bg-[#EF4444]/20 active:scale-95"
                            >
                              Deny Call
                            </button>
                            <button
                              type="button"
                              onClick={() => setApprovalAction('APPROVED')}
                              className="rounded-md bg-[#22C55E] px-3.5 py-1.5 text-[11px] font-medium text-black transition-all hover:bg-[#16A34A] hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] active:scale-95"
                            >
                              Sign &amp; Release
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setApprovalAction('PENDING')}
                            className="inline-flex items-center gap-1.5 rounded-md border border-[#262A34] px-3 py-1.5 text-[11px] text-[#A6ABB7] hover:text-white transition-colors"
                          >
                            <RefreshCw className="h-3 w-3" /> Reset Demo
                          </button>
                        )}
                      </div>
                    </div>

                    <AnimatePresence>
                      {approvalAction === 'APPROVED' && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-4 border-t border-[#1A1C22] pt-3 text-[11px] text-[#22C55E]"
                        >
                          ✓ Tool released to target service. Receipt Ed25519 generated and signed.
                        </motion.div>
                      )}
                      {approvalAction === 'REJECTED' && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-4 border-t border-[#1A1C22] pt-3 text-[11px] text-[#EF4444]"
                        >
                          ✕ Tool execution rejected by operator. No external data released.
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Right Copy */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="order-1 lg:order-2 lg:col-span-5"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
                02 · Human-in-the-Loop Gateway
              </span>
              <h2 className="mt-4 text-[32px] font-medium leading-[1.08] tracking-[-0.03em] text-white sm:text-[44px]">
                A person holds <br />
                <span className="text-[#DA5C2B]">the gate.</span>
              </h2>
              <p className="mt-5 text-[15px] leading-relaxed text-[#8F94A0]">
                High-value, destructive, or anomalous proposals halt automatically at designated human approval queues. The agent cannot self-authorize or bypass the human approver.
              </p>

              <ul className="mt-6 space-y-2.5 font-mono text-[12px] text-[#A6ABB7]">
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
                  <span>Strict separation of duty: Requester ≠ Approver</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
                  <span>Automatic TTL expiration for stale pending requests</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
                  <span>Interactive approval console with audit trail</span>
                </li>
              </ul>

              <div className="mt-8">
                <Link
                  href="/dashboard/approvals"
                  className="group inline-flex items-center gap-1.5 text-[13px] font-medium text-[#DA5C2B] hover:underline"
                >
                  <span>Open Human Approval Console</span>
                  <span aria-hidden="true" className="axiom-btn-arrow font-mono">
                    <span className="arrow-primary">→</span>
                    <span className="arrow-secondary">→</span>
                  </span>
                </Link>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* FEATURE 3: CRYPTOGRAPHIC TRUST (ED25519 RECEIPTS & TAMPER PROOF)          */}
      {/* ========================================================================= */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-16">
            {/* Left Copy */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="lg:col-span-5"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
                03 · Cryptographic Non-Repudiation
              </span>
              <h2 className="mt-4 text-[32px] font-medium leading-[1.08] tracking-[-0.03em] text-white sm:text-[44px]">
                Evidence you can <br />
                <span className="text-[#DA5C2B]">verify.</span>
              </h2>
              <p className="mt-5 text-[15px] leading-relaxed text-[#8F94A0]">
                Every executed action leaves an asymmetric Ed25519 receipt with a canonical SHA-256 digest. Even a 1-bit alteration to proposal payload immediately invalidates verification.
              </p>

              <div className="mt-8">
                <Link
                  href="/dashboard/trust"
                  className="group inline-flex items-center gap-1.5 text-[13px] font-medium text-[#DA5C2B] hover:underline"
                >
                  <span>Explore live Trust Explorer</span>
                  <span aria-hidden="true" className="axiom-btn-arrow font-mono">
                    <span className="arrow-primary">→</span>
                    <span className="arrow-secondary">→</span>
                  </span>
                </Link>
              </div>
            </motion.div>

            {/* Right Interactive Tamper Simulator */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="lg:col-span-7"
            >
              <div className="axiom-frame overflow-hidden rounded-xl border border-[#20232C] bg-[#0C0D11] p-6 shadow-2xl hover:border-[#22C55E]/30 transition-colors">
                <div className="flex items-center justify-between border-b border-[#1E2129] pb-4">
                  <div className="flex items-center gap-2 font-mono text-[12px]">
                    <span className="h-2 w-2 rounded-full bg-[#22C55E]" />
                    <span className="font-medium text-white">receipt.verify_signature()</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsTampered(!isTampered)}
                    className={`rounded px-3 py-1 font-mono text-[11px] font-semibold transition-all active:scale-95 ${
                      isTampered
                        ? 'bg-[#EF4444] text-white shadow-[0_0_12px_rgba(239,68,68,0.4)]'
                        : 'border border-[#2A2E3B] bg-[#141720] text-[#A6ABB7] hover:text-white'
                    }`}
                  >
                    {isTampered ? 'Restore Original Byte' : 'Tamper with 1 Byte'}
                  </button>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3 font-mono text-[11px]">
                  <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2E3342]">
                    <span className="text-[#5A606E] text-[10px] uppercase">1. SHA-256 Hash</span>
                    <p className="mt-2 truncate font-bold text-white">
                      {isTampered ? '0x99f4a1bc0991823...' : '0x17c09e3a65492d3...'}
                    </p>
                    <span
                      className={`mt-1 inline-block text-[10px] font-semibold ${
                        isTampered ? 'text-[#EF4444]' : 'text-[#22C55E]'
                      }`}
                    >
                      {isTampered ? '✕ HASH MISMATCH' : '✓ CANONICAL MATCH'}
                    </span>
                  </div>

                  <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2E3342]">
                    <span className="text-[#5A606E] text-[10px] uppercase">2. Ed25519 Sig</span>
                    <p className="mt-2 truncate font-bold text-white">
                      {isTampered ? 'sig_corrupted_byte' : 'harness-ed25519-v1'}
                    </p>
                    <span
                      className={`mt-1 inline-block text-[10px] font-semibold ${
                        isTampered ? 'text-[#EF4444]' : 'text-[#22C55E]'
                      }`}
                    >
                      {isTampered ? '✕ INVALID SIGNATURE' : '✓ CRYPTOGRAPHICALLY VALID'}
                    </span>
                  </div>

                  <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2E3342]">
                    <span className="text-[#5A606E] text-[10px] uppercase">3. Anchor</span>
                    <p className="mt-2 font-bold text-white">Besu EVM RPC</p>
                    <span className="mt-1 inline-block text-[10px] text-[#A6ABB7]">
                      {isTampered ? 'Reconciliation Failed' : 'Confirmed on Chain'}
                    </span>
                  </div>
                </div>

                <div className="mt-4 rounded-lg border border-[#1E2129] bg-[#050608] p-3 font-mono text-[11px] text-[#7D828F]">
                  <p>
                    {isTampered
                      ? '⚠️ TAMPER DETECTED: Changing even one byte of vendor name or amount produces an entirely different SHA-256 digest, which fails Ed25519 signature verification against the Harness public key.'
                      : '✓ VERIFIED: Payload matches the signed receipt issued by Harness :8002 prior to execution. Audit trail is mathematically secure.'}
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>
    </div>
  );
}
