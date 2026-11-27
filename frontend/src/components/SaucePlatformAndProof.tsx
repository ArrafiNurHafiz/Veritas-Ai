'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'motion/react';
import {
  Bot,
  ShieldAlert,
  CheckCircle2,
  ChevronDown,
  ArrowRight,
  Fingerprint,
} from 'lucide-react';

const AGENTS = [
  {
    id: 'procurement-agent',
    name: 'Procurement Agent',
    tools: ['approve_invoice', 'check_vendor_status'],
    desc: 'Evaluates vendor invoices with FX normalization and strict allowlist enforcement.',
  },
  {
    id: 'finance-risk-agent',
    name: 'Finance Risk Agent',
    tools: ['audit_reconciliation', 'flag_discrepancy'],
    desc: 'Audits ledger variances and flags anomalies without direct posting privileges.',
  },
  {
    id: 'hr-operations-agent',
    name: 'HR Operations Agent',
    tools: ['provision_workspace', 'log_badge_request'],
    desc: 'Proposes employee workspace onboarding and physical badge requests under policy.',
  },
  {
    id: 'security-audit-agent',
    name: 'Security Audit Agent',
    tools: ['scan_iam_keys', 'revoke_stale_token'],
    desc: 'Inspects stale IAM credentials and gates token revocation behind approval rules.',
  },
];

const STATS = [
  { value: '49 / 49', label: 'Enterprise + PostgreSQL 16 Tests Passed (0 skipped)' },
  { value: '140+', label: 'Deterministic Policy & Security Acceptance Checks' },
  { value: '0', label: 'Tool Calls Executed on WAITING_APPROVAL or DENY' },
  { value: '1 Byte', label: 'Tamper Sensitivity via Ed25519 + RFC 8785 JCS' },
];

const FAQS = [
  {
    q: 'Can an AI agent bypass the Harness and call our ERP or database directly?',
    a: 'No. In Docker Compose, agent_service runs inside an internal-only network (agent_net) with zero database credentials, zero signing keys, and zero outbound internet access to target systems.',
  },
  {
    q: 'What happens if a policy or vendor blocklist changes while an approval is pending?',
    a: 'VERITAS performs anti-TOCTOU Resume Revalidation when the Approver signs off—re-checking policy_version, args_hash, active agent/tool toggles, and vendor status. Any drift transitions to DENIED_ON_RESUME with 0 tool calls.',
  },
  {
    q: 'Does VERITAS work without external LLM API keys?',
    a: 'Yes. By default, agent_service can run in offline deterministic mode, or connect to any OpenAI-compatible gateway such as local 9router or OpenRouter with circuit-breaker and payload protection.',
  },
];

export default function SaucePlatformAndProof() {
  const [amountIdr, setAmountIdr] = useState(4200000);
  const [vendorAllowed, setVendorAllowed] = useState(true);
  const [tampered, setTampered] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const policyVerdict = !vendorAllowed
    ? 'DENY'
    : amountIdr <= 5000000
      ? 'ALLOW'
      : amountIdr <= 25000000
        ? 'APPROVAL_REQUIRED'
        : 'DENY';

  return (
    <>
      {/* 6. FULL-LIFECYCLE PLATFORM & INTERACTIVE PLAYGROUND (Sauce Labs Off-White + Rounded Pine Card) */}
      <section id="agents" className="bg-[#F8F8F8] py-20 sm:py-24 border-b border-[#DCDCD7]">
        <div className="max-w-[1180px] mx-auto px-5 sm:px-8 space-y-14">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.55 }}
            className="text-center max-w-3xl mx-auto space-y-4"
          >
            <span className="font-mono text-[11.5px] uppercase tracking-[0.18em] text-[#6D7344]">
              Value Delivered Across Operations
            </span>
            <h2 className="font-display text-[36px] sm:text-[50px] leading-[1.06] text-[#192319]">
              The world&apos;s only full-lifecycle AI action governance harness.
            </h2>
            <p className="text-[16px] text-[#2D372D] max-w-2xl mx-auto">
              Four bounded operational agents propose actions; VERITAS enforces deterministic
              rules, human sign-off, and cryptographic receipts across every stage.
            </p>
          </motion.div>

          {/* 4 Agent Cards in Off-White/Ivory Editorial Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {AGENTS.map((agent, i) => (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: 22 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.48, delay: i * 0.08 }}
                className="rounded-[26px] bg-[#F0F0EC] border border-[#DCDCD7] p-6 flex flex-col justify-between space-y-5 hover:border-[#192319] hover:-translate-y-1 transition-all"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="w-10 h-10 rounded-xl bg-[#192319] text-[#ABE082] flex items-center justify-center">
                      <Bot className="w-5 h-5" />
                    </span>
                    <span className="px-2.5 py-0.5 rounded-md bg-[#F3FFCC] border border-[#ABE082] font-mono text-[10px] text-[#192319] uppercase font-semibold">
                      Bounded
                    </span>
                  </div>
                  <h3 className="font-display text-[22px] text-[#192319]">{agent.name}</h3>
                  <p className="text-[13.5px] leading-relaxed text-[#2D372D]">{agent.desc}</p>
                </div>
                <div className="pt-3 border-t border-[#DCDCD7] flex flex-wrap gap-1.5">
                  {agent.tools.map((t) => (
                    <span
                      key={t}
                      className="px-2.5 py-1 rounded-md bg-white border border-[#DCDCD7] font-mono text-[11px] text-[#192319]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Interactive Policy & 1-Byte Tamper Simulator (Sauce Labs Frosted Editorial Style) */}
          <motion.div
            id="playground"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.55 }}
            className="relative overflow-hidden rounded-[28px] border border-[#C8C8BE] grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-[#DCDCD7]"
            style={{
              background:
                'linear-gradient(155deg, #F8F8FB 0%, #EFEBF4 55%, #F4F6FA 100%)',
            }}
          >
            {/* Left Column: Controls */}
            <div className="lg:col-span-6 p-7 sm:p-10 space-y-6">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[#6D7344]">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#6DB33F]" />
                  <span>Interactive Policy &amp; Tamper Simulator</span>
                </div>
                <h3 className="font-display text-[30px] sm:text-[36px] text-[#192319] leading-[1.08]">
                  Test deterministic gates and 1-byte receipt integrity live.
                </h3>
              </div>

              <div className="rounded-[20px] bg-white border border-[#DCDCD7] divide-y divide-[#DCDCD7]">
                <div className="p-5 space-y-3">
                  <div className="flex items-center justify-between text-[13.5px]">
                    <span className="font-medium text-[#2D372D]">Invoice Amount (IDR)</span>
                    <span className="font-mono font-bold text-[#192319] tabular-nums">
                      Rp {amountIdr.toLocaleString('id-ID')}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={1000000}
                    max={30000000}
                    step={500000}
                    value={amountIdr}
                    onChange={(e) => setAmountIdr(Number(e.target.value))}
                    className="w-full accent-[#192319] cursor-pointer"
                  />
                  <div className="flex justify-between font-mono text-[10.5px] text-[#6D7344]">
                    <span>Rp 1M (Auto)</span>
                    <span>Rp 5M Ceiling</span>
                    <span>Rp 25M Hard Cap</span>
                  </div>
                </div>

                <div className="px-5 py-4 flex items-center justify-between gap-4">
                  <div>
                    <div className="text-[13.5px] font-medium text-[#192319]">
                      Vendor Allowlist (V-ABC)
                    </div>
                    <div className="text-[12px] text-[#2D372D]">
                      Toggle vendor trust state in Policy Engine
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setVendorAllowed((v) => !v)}
                    className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full font-mono text-[11px] font-semibold border transition-colors ${
                      vendorAllowed
                        ? 'bg-[#F3FFCC] border-[#ABE082] text-[#192319]'
                        : 'bg-[#F55524]/15 border-[#F55524] text-[#961001]'
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        vendorAllowed ? 'bg-[#6DB33F]' : 'bg-[#F55524]'
                      }`}
                    />
                    <span>{vendorAllowed ? 'ALLOWLISTED' : 'BLOCKED'}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Right Column: Live Verdict & Tamper Verification */}
            <div className="lg:col-span-6 p-7 sm:p-10 flex flex-col justify-between gap-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-[#6D7344]">
                    HARNESS VERDICT
                  </span>
                  <span
                    className={`inline-flex items-center gap-2 px-3.5 py-1 rounded-full font-mono text-[11.5px] font-bold border ${
                      policyVerdict === 'ALLOW'
                        ? 'bg-[#F3FFCC] border-[#ABE082] text-[#192319]'
                        : policyVerdict === 'APPROVAL_REQUIRED'
                          ? 'bg-[#F1E082]/60 border-[#F1BE23] text-[#192319]'
                          : 'bg-[#F55524]/15 border-[#F55524] text-[#961001]'
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        policyVerdict === 'ALLOW'
                          ? 'bg-[#6DB33F]'
                          : policyVerdict === 'APPROVAL_REQUIRED'
                            ? 'bg-[#E5A91A]'
                            : 'bg-[#F55524]'
                      }`}
                    />
                    <span>{policyVerdict}</span>
                  </span>
                </div>

                <div className="rounded-[20px] bg-white border border-[#DCDCD7] p-5 space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-2 font-mono text-[11.5px] font-semibold text-[#192319]">
                      <Fingerprint className="w-4 h-4 text-[#043423]" />
                      <span>Ed25519 Receipt Verification</span>
                    </span>
                    <span
                      className={`font-mono text-[11px] font-bold ${
                        tampered ? 'text-[#961001]' : 'text-[#043423]'
                      }`}
                    >
                      {tampered ? 'HASH_MISMATCH (INVALID)' : 'SIGNATURE_VALID'}
                    </span>
                  </div>
                  <div className="rounded-xl bg-[#F0F0EC] border border-[#DCDCD7] px-3.5 py-2.5 font-mono text-[11.5px] text-[#2D372D] break-all">
                    digest: {tampered ? '9f8e7d6c5b4a...TAMPERED_BYTE' : '4a71c9e02f1b8d34...verified'}
                  </div>
                  <p className="text-[12.5px] text-[#2D372D]">
                    {tampered
                      ? 'Changing 1 byte in the canonical payload immediately invalidates the Ed25519 signature.'
                      : 'Canonical RFC 8785 payload matches the server-signed Ed25519 receipt.'}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-[#DCDCD7]">
                <button
                  type="button"
                  onClick={() => setTampered((t) => !t)}
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-[12.5px] font-semibold border transition-colors ${
                    tampered
                      ? 'bg-[#ABE082] border-[#192319] text-[#192319]'
                      : 'bg-white border-[#C8C8BE] text-[#192319] hover:border-[#192319]'
                  }`}
                >
                  {tampered ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Restore Canonical Byte</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="w-4 h-4 text-[#F55524]" />
                      <span>Simulate 1-Byte Tamper</span>
                    </>
                  )}
                </button>
                <Link
                  href="/dashboard/tasks"
                  className="font-mono text-[11.5px] uppercase tracking-[0.12em] text-[#192319] underline underline-offset-4 hover:text-[#043423]"
                >
                  RUN REAL TASK IN CONSOLE →
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 7. CREDIBILITY MATRIX & COMPARISON TABLE (Sauce Labs Hairline Grid Container Style) */}
      <section className="bg-[#F0F0EC] py-20 border-b border-[#DCDCD7]">
        <div className="max-w-[1180px] mx-auto px-5 sm:px-8 space-y-12">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.5 }}
            className="text-center max-w-2xl mx-auto space-y-2"
          >
            <span className="font-mono text-[11.5px] uppercase tracking-[0.18em] text-[#6D7344]">
              Verified Engineering Proof
            </span>
            <h2 className="font-display text-[32px] sm:text-[42px] leading-[1.1] text-[#192319]">
              Your workflows are unique. Uncontrolled AI risks are not.
            </h2>
          </motion.div>

          {/* Hairline 4-Cell Stat Matrix (Sauce Labs Why-Sauce Grid) */}
          <div className="rounded-[28px] bg-[#F8F8F8] border border-[#C8C8BE] overflow-hidden grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-[#DCDCD7]">
            {STATS.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.4, delay: i * 0.06 }}
                className="p-7 flex flex-col justify-between gap-6 hover:bg-[#F3FFCC]/35 transition-colors"
              >
                <span className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-[#6D7344]">
                  VERIFIED METRIC 0{i + 1}
                </span>
                <div className="space-y-2">
                  <div className="font-display text-[44px] leading-none font-semibold text-[#192319] tabular-nums">
                    {s.value}
                  </div>
                  <p className="text-[13.5px] leading-snug text-[#2D372D]">{s.label}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Sauce Labs Frosted Editorial Comparison Cards (No dark table header) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {[
              {
                tag: 'VERITAS HARNESS',
                dot: 'bg-[#6DB33F]',
                highlight: true,
                title: 'Deterministic Runtime Gate',
                items: [
                  ['Execution Authority', 'Proposal-only agent; Harness executes'],
                  ['Human Approval & SoD', '403 SoD + Anti-TOCTOU resume check'],
                  ['Tamper-Evident Audit', 'Ed25519 receipt + PG16 append-only trigger'],
                ],
              },
              {
                tag: 'DIRECT LLM SDKS',
                dot: 'bg-[#E5A91A]',
                highlight: false,
                title: 'Unmediated Function Calling',
                items: [
                  ['Execution Authority', 'Model invokes tools directly'],
                  ['Human Approval & SoD', 'Ad-hoc / custom callbacks'],
                  ['Tamper-Evident Audit', 'Mutable application logs'],
                ],
              },
              {
                tag: 'PROMPT GUARDRAILS',
                dot: 'bg-[#4790DD]',
                highlight: false,
                title: 'Probabilistic Text Filtering',
                items: [
                  ['Execution Authority', 'Probabilistic text filter only'],
                  ['Human Approval & SoD', 'Not supported'],
                  ['Tamper-Evident Audit', 'Classification score logs'],
                ],
              },
            ].map((col, idx) => (
              <motion.div
                key={col.tag}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.45, delay: idx * 0.07 }}
                className={`rounded-[24px] border p-7 flex flex-col justify-between space-y-6 ${
                  col.highlight
                    ? 'border-[#ABE082] shadow-[0_12px_32px_-16px_rgba(109,179,63,0.28)]'
                    : 'border-[#DCDCD7]'
                }`}
                style={{
                  background: col.highlight
                    ? 'linear-gradient(155deg, #F9FFF2 0%, #F0F9E4 55%, #F8F8FB 100%)'
                    : 'linear-gradient(155deg, #F8F8FB 0%, #EFEBF4 55%, #F4F6FA 100%)',
                }}
              >
                <div className="space-y-3">
                  <div className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[#2D372D]">
                    <span className={`w-2.5 h-2.5 rounded-full ${col.dot}`} />
                    <span>{col.tag}</span>
                  </div>
                  <h3 className="font-display text-[24px] leading-tight text-[#192319]">
                    {col.title}
                  </h3>
                </div>

                <div className="divide-y divide-[#DCDCD7]/80 border-t border-[#DCDCD7]/80">
                  {col.items.map(([k, v]) => (
                    <div key={k} className="py-3 space-y-1">
                      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#6D7344]">
                        {k}
                      </div>
                      <div className="text-[13.5px] font-medium text-[#192319]">{v}</div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 8. SECURITY FAQ */}
      <section id="security" className="bg-[#F8F8F8] py-20">
        <div className="max-w-[920px] mx-auto px-5 sm:px-8 space-y-10">
          <div className="space-y-2 text-center">
            <span className="font-mono text-[11.5px] uppercase tracking-[0.18em] text-[#6D7344]">
              Enterprise Security &amp; Architecture
            </span>
            <h2 className="font-display text-[34px] sm:text-[42px] text-[#192319]">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-3">
            {FAQS.map((item, idx) => {
              const open = openFaq === idx;
              return (
                <div
                  key={item.q}
                  className="rounded-2xl bg-white border border-[#DCDCD7] overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaq(open ? null : idx)}
                    className="w-full px-6 py-4.5 flex items-center justify-between gap-4 text-left font-semibold text-[15.5px] text-[#192319] hover:bg-[#F0F0EC]/50 transition-colors"
                  >
                    <span>{item.q}</span>
                    <ChevronDown
                      className={`w-4 h-4 shrink-0 transition-transform duration-200 ${
                        open ? 'rotate-180' : ''
                      }`}
                    />
                  </button>
                  <AnimatePresence initial={false}>
                    {open && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.22 }}
                        className="overflow-hidden"
                      >
                        <div className="px-6 pb-5 text-[14.5px] leading-relaxed text-[#2D372D] border-t border-[#DCDCD7]/60 pt-3">
                          {item.a}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 9. FINAL CTA (Sauce Labs Signature Light Shock #BED1E4 Section) */}
      <section className="bg-[#BED1E4] text-[#192319] py-20 sm:py-24 border-t border-[#DCDCD7]">
        <div className="max-w-[960px] mx-auto px-5 sm:px-8 text-center space-y-6">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.55 }}
            className="font-display text-[38px] sm:text-[54px] leading-[1.05] text-[#192319]"
          >
            Stop letting unverified AI calls put production systems at risk.
          </motion.h2>
          <p className="text-[16.5px] sm:text-[18px] text-[#2D372D] max-w-2xl mx-auto">
            Launch the live governance console, test Separation of Duties across 4 roles, and
            verify Ed25519 receipts in under 3 minutes.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3.5 pt-2">
            <Link
              href="/login"
              className="group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-[#192319] text-[#F0F0EC] font-semibold text-[15px] hover:bg-[#043423] transition-all"
            >
              <span>Sign in to Console</span>
              <span className="sauce-btn-arrow">
                <ArrowRight className="w-4 h-4 arrow-primary text-[#ABE082]" />
                <ArrowRight className="w-4 h-4 arrow-secondary text-[#ABE082]" />
              </span>
            </Link>
            <Link
              href="/dashboard/trust"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full border border-[#192319] bg-[#F8F8F8] text-[#192319] font-semibold text-[15px] hover:bg-[#ABE082] transition-all"
            >
              <span>Public Trust Explorer</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
