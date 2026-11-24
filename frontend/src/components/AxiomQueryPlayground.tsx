'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Play, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const presets = [
  {
    name: 'Invoice Policy (>5M)',
    query: `['agent-proposals']
| where ['tool'] == "approve_invoice"
| where ['amount_idr'] > 5000000
| enforce human_approval(role="approver")
| sign ed25519_receipt()`,
    verdict: 'APPROVAL_REQUIRED',
    reason: 'AMOUNT_EXCEEDS_AUTO_CEILING',
    time: '1.2ms',
    scanned: '14,290',
    receipt: '0x17c09e3a65492d3b8f10a8c2e914...',
    details: [
      { key: 'proposal_id', val: 'PRP-2026-091' },
      { key: 'tool', val: 'approve_invoice' },
      { key: 'amount_idr', val: '8,500,000' },
      { key: 'vendor_id', val: 'V-ABC (allowlisted)' },
      { key: 'policy_action', val: 'HOLD_FOR_SIGN_OFF' },
    ],
  },
  {
    name: 'Unlisted Vendor Block',
    query: `['agent-proposals']
| where ['vendor_id'] notin allowlist("active_vendors")
| reject immediate(code="UNAUTHORIZED_VENDOR")
| alert security_ops()`,
    verdict: 'DENIED',
    reason: 'VENDOR_NOT_IN_ALLOWLIST',
    time: '0.8ms',
    scanned: '8,412',
    receipt: '0x00000000000000000000000000...',
    details: [
      { key: 'proposal_id', val: 'PRP-2026-093' },
      { key: 'tool', val: 'wire_transfer_swift' },
      { key: 'amount_idr', val: '90,000,000' },
      { key: 'vendor_id', val: 'V-UNKNOWN (unlisted)' },
      { key: 'policy_action', val: 'IMMEDIATE_403_REJECT' },
    ],
  },
  {
    name: 'Egress Data Quarantine',
    query: `['outbound-egress']
| scan pii_fields(["tax_id", "phone", "bank_account"])
| where count_unhashed() > 0
| quarantine_payload()`,
    verdict: 'DENIED',
    reason: 'EGRESS_PII_VIOLATION',
    time: '1.9ms',
    scanned: '22,104',
    receipt: '0x3310fa0982bb147d018cb174...',
    details: [
      { key: 'proposal_id', val: 'PRP-2026-094' },
      { key: 'egress_target', val: 'ext-gateway.sink' },
      { key: 'detected_pii', val: '3 unhashed fields' },
      { key: 'policy_action', val: 'QUARANTINE_EGRESS' },
    ],
  },
];

export default function AxiomQueryPlayground() {
  const [activePreset, setActivePreset] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'apl' | 'builder' | 'json'>('apl');
  const [hasRun, setHasRun] = useState(true);

  const preset = presets[activePreset];

  const handleRun = () => {
    setIsRunning(true);
    setTimeout(() => {
      setIsRunning(false);
      setHasRun(true);
    }, 350);
  };

  // 24 bars for the Axiom-style histogram
  const histogramBars = [
    18, 24, 32, 28, 45, 60, 52, 78, 64, 82, 95, 70, 85, 92, 100, 88, 75, 68, 80, 90, 84, 60, 48, 55,
  ];

  return (
    <section id="interactive" className="border-b border-[#1A1C22] bg-[#090A0D] py-24 sm:py-32 axiom-grid-bg">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Title with scroll reveal */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl"
        >
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
            Interactive Policy Console
          </p>
          <h2 className="mt-4 text-[32px] font-medium leading-[1.1] tracking-[-0.03em] text-white sm:text-[44px] md:text-[52px]">
            Run an inspection. <br />
            <span className="text-[#8F94A0]">No setup required.</span>
          </h2>
          <p className="mt-5 text-[16px] leading-relaxed text-[#8F94A0]">
            No account required. Test deterministic rule parsing, latency benchmarks, and Ed25519 signature generation right in your browser.
          </p>
        </motion.div>

        {/* Playground Frame with scroll animation */}
        <motion.div
          initial={{ opacity: 0, y: 35 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.75, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12 overflow-hidden rounded-xl border border-[#20232C] bg-[#0C0D11] shadow-[0_30px_90px_-20px_rgba(0,0,0,0.9)] hover:border-[#DA5C2B]/30 transition-colors"
        >
          {/* Top header bar */}
          <div className="flex flex-wrap items-center justify-between border-b border-[#1E2129] bg-[#07080A] px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[#DA5C2B]" />
              <span className="font-mono text-[12px] font-medium text-white">
                Veritas Policy DSL (APL Engine)
              </span>
            </div>

            {/* Presets */}
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              <span className="hidden text-[#5A606E] sm:inline">Presets:</span>
              {presets.map((p, idx) => (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => {
                    setActivePreset(idx);
                    handleRun();
                  }}
                  className={`rounded px-2.5 py-1 transition-all ${
                    activePreset === idx
                      ? 'bg-[#DA5C2B] text-white font-medium shadow-[0_0_12px_rgba(218,92,43,0.3)]'
                      : 'border border-[#20232B] bg-[#0E1015] text-[#8F94A0] hover:text-white hover:border-[#353947]'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          {/* Action row & tabs */}
          <div className="flex flex-wrap items-center justify-between border-b border-[#1A1C22] bg-[#0A0C0F] px-4 py-2 text-[12px] font-mono">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveTab('apl')}
                className={`rounded px-3 py-1 transition-colors ${
                  activeTab === 'apl'
                    ? 'bg-[#1E212A] text-white'
                    : 'text-[#7D828F] hover:text-white'
                }`}
              >
                Policy APL
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('builder')}
                className={`rounded px-3 py-1 transition-colors ${
                  activeTab === 'builder'
                    ? 'bg-[#1E212A] text-white'
                    : 'text-[#7D828F] hover:text-white'
                }`}
              >
                Visual Builder
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('json')}
                className={`rounded px-3 py-1 transition-colors ${
                  activeTab === 'json'
                    ? 'bg-[#1E212A] text-white'
                    : 'text-[#7D828F] hover:text-white'
                }`}
              >
                JSON Contract
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRun}
                disabled={isRunning}
                className="inline-flex items-center gap-1.5 rounded bg-[#DA5C2B] px-3.5 py-1 text-[11px] font-semibold text-white transition-all hover:bg-[#EB6733] hover:shadow-[0_0_14px_rgba(218,92,43,0.35)] active:scale-95 disabled:opacity-50 cursor-pointer"
              >
                <Play className="h-3 w-3 fill-current" />
                <span>{isRunning ? 'Running...' : 'Run ▶'}</span>
              </button>
              <button
                type="button"
                onClick={() => setHasRun(false)}
                className="rounded border border-[#20232B] p-1 text-[#666B79] hover:text-white cursor-pointer"
                title="Clear"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Editor content */}
          <div className="p-4 sm:p-5 bg-[#08090C] font-mono text-[12.5px] leading-relaxed">
            {activeTab === 'apl' && (
              <div className="space-y-1">
                {preset.query.split('\n').map((line, idx) => (
                  <div key={idx} className="flex">
                    <span className="w-8 select-none text-[#3A3F4E]">{idx + 1}</span>
                    <span className="text-[#EDEDED]">
                      {line.startsWith('| where') && (
                        <span>
                          <span className="text-[#DA5C2B]">| where </span>
                          <span className="text-[#7DD3FC]">{line.replace('| where ', '')}</span>
                        </span>
                      )}
                      {line.startsWith('| enforce') && (
                        <span>
                          <span className="text-[#F59E0B]">| enforce </span>
                          <span className="text-[#FDE047]">{line.replace('| enforce ', '')}</span>
                        </span>
                      )}
                      {line.startsWith('| sign') && (
                        <span>
                          <span className="text-[#22C55E]">| sign </span>
                          <span className="text-[#86EFAC]">{line.replace('| sign ', '')}</span>
                        </span>
                      )}
                      {line.startsWith('| reject') && (
                        <span>
                          <span className="text-[#EF4444]">| reject </span>
                          <span className="text-[#FCA5A5]">{line.replace('| reject ', '')}</span>
                        </span>
                      )}
                      {line.startsWith('| scan') && (
                        <span>
                          <span className="text-[#A855F7]">| scan </span>
                          <span className="text-[#D8B4FE]">{line.replace('| scan ', '')}</span>
                        </span>
                      )}
                      {!line.startsWith('|') && <span className="text-[#38BDF8]">{line}</span>}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'builder' && (
              <div className="space-y-3 py-2 text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#1E212A] px-2 py-0.5 text-[#DA5C2B]">SOURCE</span>
                  <span className="text-[#8F94A0]">agent-proposals (deterministic stream)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#1E212A] px-2 py-0.5 text-[#7DD3FC]">FILTER</span>
                  <span className="text-white">amount_idr &gt; 5,000,000 AND vendor in allowlist</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#1E212A] px-2 py-0.5 text-[#F59E0B]">ACTION</span>
                  <span className="text-white">Hold execution &rarr; Route to role: approver</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#1E212A] px-2 py-0.5 text-[#22C55E]">EVIDENCE</span>
                  <span className="text-white">Generate Ed25519 receipt with SHA-256 digest</span>
                </div>
              </div>
            )}

            {activeTab === 'json' && (
              <pre className="text-[11.5px] text-[#A6ABB7] overflow-x-auto">
{JSON.stringify(
  {
    rule_id: 'POL-INVOICE-001',
    description: 'Enforce human approval above automatic ceiling',
    tool: 'approve_invoice',
    max_auto_amount: 5000000,
    hard_cap: 25000000,
    required_role: 'approver',
    require_receipt: true,
    signature_algorithm: 'ed25519',
  },
  null,
  2
)}
              </pre>
            )}
          </div>

          {/* Axiom-style Telemetry Histogram with animated bars */}
          <div className="border-t border-[#1A1C22] bg-[#07080A] px-4 py-4 sm:px-6">
            <div className="flex items-center justify-between text-[11px] font-mono text-[#606575]">
              <span>Proposal Evaluation Rate (past 1 hour)</span>
              <span>100% Policy Gated</span>
            </div>

            <div className="mt-3 flex h-14 items-end gap-1 sm:gap-2">
              {histogramBars.map((height, i) => (
                <div
                  key={i}
                  className="group relative flex-1 cursor-pointer"
                  style={{ height: `${height}%` }}
                >
                  <motion.div
                    initial={{ scaleY: 0 }}
                    whileInView={{ scaleY: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: i * 0.02, ease: [0.16, 1, 0.3, 1] }}
                    style={{ originY: 1 }}
                    className="h-full w-full rounded-t-sm bg-[#1E222C] transition-colors group-hover:bg-[#DA5C2B] group-hover:shadow-[0_0_8px_rgba(218,92,43,0.5)]"
                  />
                </div>
              ))}
            </div>
            <div className="mt-2 flex justify-between font-mono text-[9px] text-[#444956]">
              <span>13:00</span>
              <span>13:15</span>
              <span>13:30</span>
              <span>13:45</span>
              <span>14:00 (Live)</span>
            </div>
          </div>

          {/* Execution Result Banner with AnimatePresence */}
          <AnimatePresence>
            {hasRun && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="border-t border-[#1A1C22] bg-[#090B0E] p-4 sm:p-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#16181E] pb-3 font-mono text-[11px]">
                  <div className="flex items-center gap-3">
                    <span
                      className={`rounded px-2.5 py-0.5 font-bold ${
                        preset.verdict === 'APPROVAL_REQUIRED'
                          ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30'
                          : preset.verdict === 'DENIED'
                            ? 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/30'
                            : 'bg-[#22C55E]/10 text-[#22C55E] border border-[#22C55E]/30'
                      }`}
                    >
                      {preset.verdict}
                    </span>
                    <span className="text-[#8F94A0]">
                      Latency: <strong className="text-white">{preset.time}</strong>
                    </span>
                    <span className="text-[#8F94A0]">
                      Evaluated: <strong className="text-white">{preset.scanned} rules</strong>
                    </span>
                  </div>

                  <div className="text-[10px] text-[#606575]">
                    Receipt: <span className="text-[#DA5C2B]">{preset.receipt}</span>
                  </div>
                </div>

                {/* Scanned Details Grid */}
                <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5 font-mono text-[11px]">
                  {preset.details.map((d) => (
                    <div key={d.key} className="rounded border border-[#1A1C22] bg-[#0E1015] p-2.5 transition-colors hover:border-[#2F3443]">
                      <div className="text-[10px] text-[#5A606E]">{d.key}</div>
                      <div className="mt-1 font-medium text-[#EDEDED] truncate">{d.val}</div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* CTA link */}
        <div className="mt-8 text-center">
          <Link
            href="/dashboard/tasks"
            className="group inline-flex items-center gap-2 text-[13px] font-medium text-[#DA5C2B] hover:underline"
          >
            <span>Open live tasks in operator console</span>
            <span aria-hidden="true" className="axiom-btn-arrow font-mono">
              <span className="arrow-primary">→</span>
              <span className="arrow-secondary">→</span>
            </span>
          </Link>
        </div>
      </div>
    </section>
  );
}
