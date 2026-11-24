'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Copy, Check, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface ProposalScenario {
  id: string;
  timestamp: string;
  tool: string;
  vendor: string;
  amount: string;
  rawAmount: number;
  caller: string;
  status: 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED';
  reason: string;
  digest: string;
  signature: string;
  description: string;
}

const scenarios: ProposalScenario[] = [
  {
    id: 'PRP-2026-091',
    timestamp: '14:05:52.128',
    tool: 'approve_invoice',
    vendor: 'V-ABC',
    amount: 'IDR 8,500,000',
    rawAmount: 8500000,
    caller: 'agent.procure_v2',
    status: 'APPROVAL_REQUIRED',
    reason: 'AMOUNT_LIMIT (>5M auto ceiling)',
    digest: '0x17c09e3a65492d3b8f10a8c2...',
    signature: 'ed25519:v1:7f99a32c4e...',
    description: 'Quarterly datacenter maintenance invoice INV-2036-001. Amount exceeds auto-approval ceiling.',
  },
  {
    id: 'PRP-2026-092',
    timestamp: '14:05:50.014',
    tool: 'approve_invoice',
    vendor: 'V-ABC',
    amount: 'IDR 3,200,000',
    rawAmount: 3200000,
    caller: 'agent.procure_v2',
    status: 'ALLOWED',
    reason: 'WITHIN_AUTO_LIMIT (<=5M ceiling)',
    digest: '0x882a1d044f2b903e1a87c1...',
    signature: 'ed25519:v1:2d5e710b89...',
    description: 'Monthly GPU compute licensing INV-2036-002. Allowlisted vendor within automatic threshold.',
  },
  {
    id: 'PRP-2026-093',
    timestamp: '14:05:46.882',
    tool: 'wire_transfer_swift',
    vendor: 'V-UNKNOWN',
    amount: 'IDR 90,000,000',
    rawAmount: 90000000,
    caller: 'agent.finance_llm',
    status: 'DENIED',
    reason: 'UNAUTHORIZED_TOOL & UNLISTED_VENDOR',
    digest: '0x0000000000000000000000...',
    signature: 'BLOCKED_BEFORE_EXECUTION',
    description: 'Direct wire transfer to off-platform overseas account. Deny-by-default policy blocked call.',
  },
  {
    id: 'PRP-2026-094',
    timestamp: '14:05:41.310',
    tool: 'export_customer_pii',
    vendor: 'EXT-SINK',
    amount: '0 Records',
    rawAmount: 0,
    caller: 'agent.analyst',
    status: 'DENIED',
    reason: 'EGRESS_QUARANTINE_VIOLATION',
    digest: '0x3310fa0982bb147d018c...',
    signature: 'BLOCKED_BEFORE_EXECUTION',
    description: 'Attempt to dispatch unhashed customer phone and tax ID fields to external endpoint.',
  },
];

export default function AxiomHero() {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  const activeScenario = scenarios[selectedIdx];

  const handleCopyCommand = () => {
    navigator.clipboard.writeText('.venv/bin/uvicorn veritas_harness:app --port 8002');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="relative overflow-hidden pt-12 pb-20 sm:pt-16 sm:pb-28 axiom-grid-bg">
      {/* Top radial warm glow like Axiom */}
      <div className="pointer-events-none absolute inset-0 axiom-hero-glow" aria-hidden="true" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Notice Pill */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-center justify-center sm:justify-start"
        >
          <Link
            href="/#architecture"
            className="group inline-flex items-center gap-2 rounded-full border border-[#262832] bg-[#0E1015]/80 px-3.5 py-1 text-[12px] text-[#8F94A0] backdrop-blur transition-all hover:border-[#DA5C2B]/40 hover:text-white"
          >
            <span className="flex h-1.5 w-1.5 rounded-full bg-[#DA5C2B]" />
            <span className="font-mono text-[10px] uppercase font-semibold text-[#DA5C2B]">SPEC 1.1</span>
            <span className="text-[#3B3F4B]">|</span>
            <span>Deterministic Control Before Action is live</span>
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </motion.div>

        {/* Hero Title & Subtitle */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mt-6 max-w-4xl"
        >
          <h1 className="text-[38px] font-medium leading-[1.06] tracking-[-0.03em] text-white sm:text-[54px] md:text-[66px] lg:text-[72px]">
            The modern <br />
            <span className="text-[#DA5C2B]">agent control</span> platform.
          </h1>
          <p className="mt-6 max-w-2xl text-[16px] leading-relaxed text-[#8F94A0] sm:text-[18px]">
            Deterministic policy gates, human sign-off queues, and cryptographic Ed25519 receipts.
            Enforce control before action without running complex self-managed infrastructure.
          </p>

          {/* Action Row */}
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/dashboard"
              className="group inline-flex h-10 items-center gap-2 rounded-md bg-[#DA5C2B] px-5 text-[13px] font-medium text-white transition-all hover:bg-[#EB6733] hover:shadow-[0_0_20px_rgba(218,92,43,0.35)] active:scale-[0.98]"
            >
              <span>Open the console</span>
              <span aria-hidden="true" className="axiom-btn-arrow font-mono text-[14px]">
                <span className="arrow-primary">→</span>
                <span className="arrow-secondary">→</span>
              </span>
            </Link>

            <Link
              href="/#interactive"
              className="inline-flex h-10 items-center rounded-md border border-[#262933] bg-[#0E1014] px-4 text-[13px] font-medium text-[#EDEDED] transition-colors hover:border-[#3D4250] hover:bg-[#15171E]"
            >
              Interactive playground
            </Link>

            {/* Quick CLI command */}
            <div className="flex h-10 items-center gap-2 rounded-md border border-[#20232C] bg-[#0A0B0E] px-3 font-mono text-[12px] text-[#A6ABB7]">
              <span className="text-[#DA5C2B]">$</span>
              <span className="hidden sm:inline">.venv/bin/uvicorn veritas_harness:app --port 8002</span>
              <span className="sm:hidden">uvicorn veritas_harness:8002</span>
              <button
                type="button"
                onClick={handleCopyCommand}
                className="ml-2 rounded p-1 text-[#666B79] transition-colors hover:text-white"
                title="Copy command"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-[#22C55E]" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        </motion.div>

        {/* ========================================================================= */}
        {/* AXIOM HALLMARK: ILLUSTRATION FRAME (TELEMETRY & PROPOSAL INTERCEPTOR)     */}
        {/* ========================================================================= */}
        <motion.div
          initial={{ opacity: 0, y: 35 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12 overflow-hidden rounded-xl border border-[#20232B] bg-[#0C0D11] shadow-[0_30px_90px_-20px_rgba(0,0,0,0.9)] hover:border-[#DA5C2B]/30 transition-all duration-300"
        >
          {/* Frame top bar */}
          <div className="flex flex-wrap items-center justify-between border-b border-[#1E2129] bg-[#090A0D] px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-[#2E313D]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#2E313D]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#2E313D]" />
              </div>
              <span className="text-[#3E4351]">|</span>
              <div className="flex items-center gap-2 font-mono text-[11px] text-[#8F94A0]">
                <span>Datasets</span>
                <span className="text-[#555A67]">/</span>
                <span className="text-white font-medium">agent-proposals</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 font-mono text-[11px] text-[#22C55E]">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#22C55E] opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[#22C55E]" />
                </span>
                <span>STREAMING · 100% Policy Enforced</span>
              </div>
              <Link
                href="/dashboard/tasks"
                className="hidden font-mono text-[11px] text-[#DA5C2B] hover:underline sm:inline-flex"
              >
                Open in Stream →
              </Link>
            </div>
          </div>

          {/* Frame body */}
          <div className="grid grid-cols-1 lg:grid-cols-12">
            {/* Left sidebar: Schema & Dimensions */}
            <div className="border-b border-[#1E2129] p-4 font-mono text-[11px] lg:col-span-3 lg:border-b-0 lg:border-r">
              <span className="text-[10px] uppercase tracking-wider text-[#5A606E]">
                Schema Dimensions
              </span>
              <div className="mt-3 space-y-1.5 text-[#8F94A0]">
                <div className="flex items-center justify-between rounded px-2 py-1 bg-white/[0.03]">
                  <span>tool</span>
                  <span className="text-[10px] text-[#DA5C2B]">string</span>
                </div>
                <div className="flex items-center justify-between rounded px-2 py-1">
                  <span>vendor_id</span>
                  <span className="text-[10px] text-[#A6ABB7]">allowlist</span>
                </div>
                <div className="flex items-center justify-between rounded px-2 py-1">
                  <span>amount_idr</span>
                  <span className="text-[10px] text-[#A6ABB7]">int64</span>
                </div>
                <div className="flex items-center justify-between rounded px-2 py-1">
                  <span>caller_role</span>
                  <span className="text-[10px] text-[#A6ABB7]">enum</span>
                </div>
                <div className="flex items-center justify-between rounded px-2 py-1">
                  <span>ed25519_sig</span>
                  <span className="text-[10px] text-[#22C55E]">crypto</span>
                </div>
              </div>

              {/* Quick filter scenarios */}
              <div className="mt-6 border-t border-[#1E2129] pt-4">
                <span className="text-[10px] uppercase tracking-wider text-[#5A606E]">
                  Sample Proposals
                </span>
                <div className="mt-2 space-y-1">
                  {scenarios.map((s, idx) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setSelectedIdx(idx)}
                      className={`w-full rounded px-2.5 py-1.5 text-left text-[11px] transition-all duration-200 ${
                        selectedIdx === idx
                          ? 'bg-[#DA5C2B]/15 text-white font-medium border border-[#DA5C2B]/40 shadow-[0_0_10px_rgba(218,92,43,0.15)]'
                          : 'text-[#8F94A0] hover:bg-white/[0.03] hover:text-[#EDEDED]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{s.tool}</span>
                        <span
                          className={`text-[9px] px-1 py-0.5 rounded font-mono ${
                            s.status === 'ALLOWED'
                              ? 'text-[#22C55E] bg-[#22C55E]/10'
                              : s.status === 'APPROVAL_REQUIRED'
                                ? 'text-[#F59E0B] bg-[#F59E0B]/10'
                                : 'text-[#EF4444] bg-[#EF4444]/10'
                          }`}
                        >
                          {s.status === 'ALLOWED' ? 'OK' : s.status === 'APPROVAL_REQUIRED' ? 'HELD' : 'DENY'}
                        </span>
                      </div>
                      <div className="text-[10px] text-[#5A606E] truncate">{s.amount}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right main area: Live Proposal Inspector */}
            <div className="p-5 lg:col-span-9 bg-[#090A0D]">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeScenario.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1E2129] pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[12px] font-semibold text-white">
                          {activeScenario.id}
                        </span>
                        <span className="font-mono text-[10px] text-[#606575]">
                          {activeScenario.timestamp}
                        </span>
                      </div>
                      <p className="mt-1 text-[13px] text-[#8F94A0]">
                        {activeScenario.description}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-mono text-[11px] font-medium ${
                          activeScenario.status === 'ALLOWED'
                            ? 'bg-[#22C55E]/10 text-[#22C55E] border border-[#22C55E]/20'
                            : activeScenario.status === 'APPROVAL_REQUIRED'
                              ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20'
                              : 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20'
                        }`}
                      >
                        {activeScenario.status === 'ALLOWED' && <CheckCircle2 className="h-3.5 w-3.5" />}
                        {activeScenario.status === 'APPROVAL_REQUIRED' && <AlertTriangle className="h-3.5 w-3.5" />}
                        {activeScenario.status === 'DENIED' && <XCircle className="h-3.5 w-3.5" />}
                        {activeScenario.status}
                      </span>
                    </div>
                  </div>

                  {/* Data Table / Fields */}
                  <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 font-mono text-[11px]">
                    <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2C303E]">
                      <span className="text-[#5A606E] text-[10px] uppercase">Action Tool</span>
                      <p className="mt-1 font-medium text-white truncate">{activeScenario.tool}</p>
                    </div>
                    <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2C303E]">
                      <span className="text-[#5A606E] text-[10px] uppercase">Vendor ID</span>
                      <p className="mt-1 font-medium text-[#DA5C2B]">{activeScenario.vendor}</p>
                    </div>
                    <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2C303E]">
                      <span className="text-[#5A606E] text-[10px] uppercase">Amount IDR</span>
                      <p className="mt-1 font-medium text-white">{activeScenario.amount}</p>
                    </div>
                    <div className="rounded-lg border border-[#1E2129] bg-[#0E1015] p-3 transition-colors hover:border-[#2C303E]">
                      <span className="text-[#5A606E] text-[10px] uppercase">Caller Service</span>
                      <p className="mt-1 font-medium text-[#A6ABB7] truncate">{activeScenario.caller}</p>
                    </div>
                  </div>

                  {/* Code snippet / Policy Verdict box */}
                  <div className="mt-4 rounded-lg border border-[#1E2129] bg-[#050608] p-4 font-mono text-[11.5px] leading-relaxed">
                    <div className="flex items-center justify-between border-b border-[#1A1C22] pb-2 text-[10px] text-[#606575]">
                      <span>POLICY EVALUATION ENGINE</span>
                      <span>HARNESS 8002</span>
                    </div>
                    <div className="mt-3 space-y-1">
                      <div>
                        <span className="text-[#606575]">01 </span>
                        <span className="text-[#DA5C2B]">harness.intercept</span>(caller: &quot;{activeScenario.caller}&quot;, tool: &quot;{activeScenario.tool}&quot;)
                      </div>
                      <div>
                        <span className="text-[#606575]">02 </span>
                        <span className="text-[#8F94A0]">policy.check</span>(amount: {activeScenario.rawAmount}, vendor_allowlist: [&quot;V-ABC&quot;, &quot;V-XYZ&quot;])
                      </div>
                      <div>
                        <span className="text-[#606575]">03 </span>
                        <span className="text-[#22C55E]">verdict</span> &rarr; <span className="text-white font-bold">{activeScenario.status}</span> ({activeScenario.reason})
                      </div>
                      <div>
                        <span className="text-[#606575]">04 </span>
                        <span className="text-[#A6ABB7]">ed25519_digest</span>: <span className="text-[#DA5C2B]">{activeScenario.digest}</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </AnimatePresence>

              {/* Bottom control */}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[#1E2129] pt-3 text-[11px] font-mono text-[#666B79]">
                <span>Status: Deterministic check enforced prior to tool invocation</span>
                <Link
                  href="/dashboard/trust"
                  className="inline-flex items-center gap-1 text-[#DA5C2B] hover:underline"
                >
                  Verify Cryptographic Proof in Trust Explorer &rarr;
                </Link>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Bottom subtle note */}
        <p className="mt-4 text-center font-mono text-[11px] text-[#555A67]">
          Live vertical slice demonstration · FastAPI Harness :8002 · SQLite · Mock Besu EVM
        </p>
      </div>
    </section>
  );
}
