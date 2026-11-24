'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import AvatarCursor from '@/components/AvatarCursor';
import { motion, AnimatePresence } from 'motion/react';
import { 
  ShieldCheck, 
  ArrowRight, 
  Check, 
  Send, 
  Sparkles, 
  Lock, 
  Cpu, 
  Sliders, 
  FileCheck, 
  Database, 
  Activity, 
  CheckCircle2, 
  AlertTriangle,
  Fingerprint,
  RefreshCw,
  Eye,
  CornerDownLeft,
  ChevronRight
} from 'lucide-react';

export default function LandingPage() {
  // Parallax mouse position state for the hero cards
  const heroRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setMousePos({ x, y });
  };

  // AI Composer prompt state with simulated typing
  const [composerPrompt, setComposerPrompt] = useState('Review server maintenance invoice INV-2036-001 for IDR 8,500,000');
  const [composerOutput, setComposerOutput] = useState<{
    tool: string;
    decision: 'ALLOWED' | 'APPROVAL_REQUIRED' | 'DENIED';
    reason: string;
    amount: string;
  }>({
    tool: 'approve_invoice',
    decision: 'APPROVAL_REQUIRED',
    reason: 'Amount exceeds automatic policy limit of IDR 5,000,000 &bull; Dispatched to Sarah Jenkins (Approver)',
    amount: 'IDR 8,500,000',
  });

  // Workbench auto-playing tab state (Steep Signature Feature!)
  const [activeTab, setActiveTab] = useState<'policy' | 'approval' | 'receipt'>('policy');
  const [isPaused, setIsPaused] = useState(false);
  const [tabProgressKey, setTabProgressKey] = useState(0);

  // Interactive Policy Slider in Workbench
  const [wbAmount, setWbAmount] = useState<number>(8500000);
  const [wbVendor, setWbVendor] = useState<string>('PT Global Tech');

  // Interactive Tamper state in Workbench
  const [wbTampered, setWbTampered] = useState(false);

  // Auto-cycle workbench tabs every 6 seconds if not paused
  useEffect(() => {
    if (isPaused) return;
    const timer = setInterval(() => {
      setActiveTab((prev) => {
        if (prev === 'policy') return 'approval';
        if (prev === 'approval') return 'receipt';
        return 'policy';
      });
      setTabProgressKey((k) => k + 1);
    }, 6000);

    return () => clearInterval(timer);
  }, [isPaused, activeTab]);

  const samplePrompts = [
    {
      label: 'Invoice > 5M (Gate)',
      text: 'Review server maintenance invoice INV-2036-001 for IDR 8,500,000',
      tool: 'approve_invoice',
      decision: 'APPROVAL_REQUIRED' as const,
      reason: 'Amount IDR 8,500,000 exceeds automatic policy limit of IDR 5,000,000.',
      amount: 'IDR 8,500,000',
    },
    {
      label: 'Invoice <= 5M (Auto)',
      text: 'Process monthly GPU compute licensing INV-2036-002 for IDR 3,200,000',
      tool: 'approve_invoice',
      decision: 'ALLOWED' as const,
      reason: 'Within auto-approval ceiling & vendor allowlist matched. Executed & signed.',
      amount: 'IDR 3,200,000',
    },
    {
      label: 'Unknown Tool Attack',
      text: 'Attempt direct wire transfer to overseas account for IDR 90,000,000',
      tool: 'transfer_wire_unlimited',
      decision: 'DENIED' as const,
      reason: 'UNAUTHORIZED_TOOL: Blocked by Harness Policy Gateway (Deny-by-default).',
      amount: 'IDR 90,000,000',
    },
  ];

  const handleSelectPrompt = (p: typeof samplePrompts[0]) => {
    setComposerPrompt(p.text);
    setComposerOutput({
      tool: p.tool,
      decision: p.decision,
      reason: p.reason,
      amount: p.amount,
    });
  };

  return (
    <div className="landing-page min-h-screen bg-white flex flex-col font-body text-[#17191c] antialiased selection:bg-[#fbe1d1] selection:text-[#5d2a1a]">
      <Navbar />

      {/* ========================================================================= */}
      {/* 1. HERO SECTION (STEEP COLLAGE PATTERN WITH MOTION & PARALLAX)             */}
      {/* ========================================================================= */}
      <section
        ref={heroRef}
        onMouseMove={handleMouseMove}
        className="landing-hero relative pt-12 pb-24 md:pt-16 md:pb-32 px-6 overflow-hidden"
      >
        <div className="hero-stage">
        <div className="max-w-[1240px] mx-auto relative">
          
          {/* CENTER HERO COPY WITH SPRING REVEAL */}
          <div className="hero-copy text-center space-y-7 relative z-20 max-w-3xl mx-auto">
            {/* Top pill badge */}
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-black/8 bg-black/[0.03] text-[14px] text-[#17191c] hover:bg-black/[0.06] transition-colors"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-sans font-normal">VERITAS AI · An enterprise governance demo</span>
              <span className="text-[#979799]">&rarr;</span>
            </motion.div>

            {/* Headline: Serif Signifier/Newsreader with delicate spring appearance */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="font-display text-[44px] sm:text-[60px] md:text-[72px] lg:text-[80px] text-[#17191c] leading-[1.04] tracking-[-0.025em] mx-auto text-balance"
            >
              For companies that work with <em>AI agents</em>
            </motion.h1>

            {/* Subhead: Sohne 18-20px */}
            <motion.p
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="text-[17px] sm:text-[19px] md:text-[20px] text-[#777b86] max-w-xl mx-auto font-sans leading-[1.4] font-normal"
            >
              Give your AI agents room to work, with policy checks before they act and a clear record of every decision.
            </motion.p>

            {/* Paired Pill Buttons on the same baseline with hover arrow slide */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-2"
            >
              <Link
                href="/dashboard"
                className="group pill-button-filled !h-12 !px-8 !text-[16px]"
              >
                <span>Get started</span>
                <span className="arrow-slide inline-block">&rarr;</span>
              </Link>
              <Link
                href="/#workbench"
                className="pill-button-ghost !h-12 !px-8 !text-[16px]"
              >
                <span>Explore platform</span>
              </Link>
            </motion.div>
          </div>

          {/* ========================================================================= */}
          {/* FLOATING COLLAGE ARTIFACTS WITH PARALLAX & CONTINUOUS BREATHING MOTION    */}
          {/* ========================================================================= */}

          {/* FLOATING ARTIFACT 1: TOP LEFT — ALLOWED TOOL REGISTRY TABLE */}
          <motion.div
            initial={{ opacity: 0, x: -40, y: -20 }}
            animate={{ 
              opacity: 1, 
              x: mousePos.x * -25, 
              y: mousePos.y * -20 
            }}
            transition={{ type: 'spring', stiffness: 80, damping: 20 }}
            className="hero-fragment hero-fragment-left hidden lg:block absolute top-2 -left-36 w-80 floating-artifact p-4 animate-float-1 z-10"
          >
            <div className="flex items-center justify-between pb-2.5 border-b border-[#ececec]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
                Allowed Tool Registry
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#f2f2f3] text-[#777b86]">
                3 Tools Active
              </span>
            </div>
            <table className="w-full text-left text-[11px] mt-2 border-collapse">
              <thead>
                <tr className="text-[#979799] font-medium border-b border-[#f2f2f3]">
                  <th className="pb-1.5 font-normal">Tool</th>
                  <th className="pb-1.5 font-normal">Ceiling</th>
                  <th className="pb-1.5 text-right font-normal">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f2f2f3] font-mono">
                <tr className="hover:bg-[#fafafb] transition-colors">
                  <td className="py-1.5 text-[#17191c]">approve_invoice</td>
                  <td className="py-1.5 text-[#777b86]">Rp 5.0M</td>
                  <td className="py-1.5 text-right text-amber-700 font-medium">Tier 2</td>
                </tr>
                <tr className="hover:bg-[#fafafb] transition-colors">
                  <td className="py-1.5 text-[#17191c]">vendor_status</td>
                  <td className="py-1.5 text-[#777b86]">&infin;</td>
                  <td className="py-1.5 text-right text-emerald-700 font-medium">Tier 0</td>
                </tr>
                <tr className="hover:bg-[#fafafb] transition-colors">
                  <td className="py-1.5 text-[#17191c]">reconciliation</td>
                  <td className="py-1.5 text-[#777b86]">Read</td>
                  <td className="py-1.5 text-right text-blue-700 font-medium">Tier 1</td>
                </tr>
              </tbody>
            </table>
          </motion.div>

          {/* FLOATING ARTIFACT 2: TOP RIGHT — APPROVAL GATE STAT WITH LIVE CURSOR */}
          <motion.div
            initial={{ opacity: 0, x: 40, y: -20 }}
            animate={{ 
              opacity: 1, 
              x: mousePos.x * 30, 
              y: mousePos.y * -25 
            }}
            transition={{ type: 'spring', stiffness: 80, damping: 20 }}
            className="hero-fragment hero-fragment-right hidden lg:block absolute top-8 -right-36 w-76 floating-artifact p-4 animate-float-2 z-10 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
                Approval Gate
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-medium">
                HELD
              </span>
            </div>
            <div>
              <div className="text-[26px] font-sans font-medium text-[#17191c] leading-tight">
                Rp 8.500.000
              </div>
              <div className="text-[12px] text-[#777b86] flex items-center gap-1.5 mt-0.5">
                <span className="text-amber-800 font-medium">&uarr; Over Rp 5M limit</span>
                <span>&bull; INV-2036-001</span>
              </div>
            </div>

            {/* Smooth Sienna Brown Curve Chart with path draw animation */}
            <svg className="w-full h-8 pt-1" viewBox="0 0 100 24" fill="none">
              <path
                d="M0 18 C 20 18, 30 10, 50 14 C 70 18, 80 4, 100 6"
                stroke="#5d2a1a"
                strokeWidth="2"
                strokeLinecap="round"
                className="animate-draw-chart"
              />
            </svg>

            {/* Steep Signature Cursor Avatar */}
            <div className="pt-1 flex items-center justify-end">
              <AvatarCursor
                initials="SJ"
                name="Sarah Jenkins (Approver)"
                color="peach"
                pointerDirection="top-left"
              />
            </div>
          </motion.div>

          {/* FLOATING ARTIFACT 3: BOTTOM LEFT — MEDIATION GAUGE */}
          <motion.div
            initial={{ opacity: 0, x: -40, y: 30 }}
            animate={{ 
              opacity: 1, 
              x: mousePos.x * -20, 
              y: mousePos.y * 25 
            }}
            transition={{ type: 'spring', stiffness: 80, damping: 20 }}
            className="hero-fragment hero-fragment-bottom-left hidden lg:block absolute bottom-12 -left-2 w-64 floating-artifact p-4 animate-float-3 z-10 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
                Gateway Enforcement
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-[28px] font-sans font-medium text-[#17191c] leading-tight">
              100%
            </div>
            <p className="text-[12px] text-[#777b86] leading-snug">
              Protected tool calls mediated through deterministic policy engine.
            </p>
            <div className="pt-1 flex items-center gap-1.5">
              <AvatarCursor
                initials="MV"
                name="Marcus (Operator)"
                color="blue"
                pointerDirection="top-left"
              />
            </div>
          </motion.div>

          {/* FLOATING ARTIFACT 4: BOTTOM RIGHT — BESU ANCHOR PROVENANCE */}
          <motion.div
            initial={{ opacity: 0, x: 40, y: 30 }}
            animate={{ 
              opacity: 1, 
              x: mousePos.x * 25, 
              y: mousePos.y * 20 
            }}
            transition={{ type: 'spring', stiffness: 80, damping: 20 }}
            className="hero-fragment hero-fragment-bottom-right hidden lg:block absolute bottom-8 -right-4 w-72 floating-artifact p-4 animate-float-1 z-10 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
                Private Ledger Anchor
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium">
                CONFIRMED
              </span>
            </div>
            <div className="space-y-1">
              <div className="font-mono text-[13px] text-[#17191c] font-medium">
                Besu Block #10482
              </div>
              <div className="font-mono text-[10px] text-[#777b86] truncate">
                Tx: 0x7a3f8190c2b54d7e98a1023c4d5e6f7a...
              </div>
            </div>
            <div className="pt-1 flex items-center justify-between text-[11px] text-[#979799] border-t border-[#f2f2f3]">
              <span>Ed25519 Signed</span>
              <span className="text-emerald-700 font-medium">RFC 8785 JCS</span>
            </div>
          </motion.div>

          {/* ========================================================================= */}
          {/* STEEP SIGNATURE AI COMPOSER BAR (CENTER BOTTOM)                           */}
          {/* ========================================================================= */}
          <div className="hero-product-reveal">
          <div className="hero-product-frame">
          <div className="hero-product-heading" aria-hidden="true">
            <span>VERITAS / WORKSPACE</span>
            <span>Illustrative demo</span>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="hero-composer mt-14 max-w-2xl mx-auto relative z-20"
          >
            <div className="bg-white rounded-[20px] p-2.5 sm:p-3 border border-[#ececec] shadow-[0_0_0_1px_rgba(4,23,43,0.05),0_20px_25px_-5px_rgba(0,0,0,0.08),0_8px_10px_-6px_rgba(0,0,0,0.04)] space-y-3">
              <div className="flex items-center gap-3 px-3 py-1">
                <span className="text-[#979799] font-mono text-[18px]">@</span>
                <input
                  type="text"
                  value={composerPrompt}
                  onChange={(e) => setComposerPrompt(e.target.value)}
                  placeholder="Ask agent or trigger tool proposal..."
                  className="w-full bg-transparent text-[15px] sm:text-[16px] text-[#17191c] placeholder:text-[#a3a6af] focus:outline-none font-sans"
                />
                <button
                  type="button"
                  onClick={() => {
                    setComposerOutput({
                      tool: 'approve_invoice',
                      decision: composerPrompt.includes('3,200,000') ? 'ALLOWED' : 'APPROVAL_REQUIRED',
                      reason: composerPrompt.includes('3,200,000')
                        ? 'Amount within Rp 5M threshold &bull; Auto-executed'
                        : 'Amount exceeds Rp 5M threshold &bull; Held for human approval',
                      amount: composerPrompt.includes('3,200,000') ? 'IDR 3,200,000' : 'IDR 8,500,000',
                    });
                  }}
                  className="w-10 h-10 rounded-full bg-[#17191c] text-white flex items-center justify-center shrink-0 hover:opacity-90 active:scale-95 transition-all shadow-sm"
                  title="Evaluate proposal"
                >
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {/* Sample Prompts Pills */}
              <div className="flex flex-wrap items-center gap-2 pt-1 px-2 border-t border-[#f2f2f3]">
                <span className="text-[11px] font-medium text-[#979799] uppercase tracking-wider mr-1">
                  Try Sample:
                </span>
                {samplePrompts.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSelectPrompt(p)}
                    className="text-[12px] px-3 py-1 rounded-full bg-[#f2f2f3] text-[#17191c] hover:bg-[#e8e8e9] active:scale-95 transition-all font-sans"
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Reactive Composer Output Pill with smooth layout pop */}
              <AnimatePresence mode="wait">
                {composerOutput && (
                  <motion.div
                    key={composerOutput.tool + composerOutput.amount}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                    className="mx-2 p-3 rounded-xl bg-[#fafafb] border border-[#ececec] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[12px]"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-white border border-[#ececec] text-[#17191c]">
                        {composerOutput.tool}
                      </span>
                      <span
                        className="text-[#777b86]"
                        dangerouslySetInnerHTML={{ __html: composerOutput.reason }}
                      />
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full font-medium shrink-0 ${
                      composerOutput.decision === 'ALLOWED'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : composerOutput.decision === 'DENIED'
                        ? 'bg-rose-50 text-rose-800 border border-rose-200'
                        : 'bg-amber-50 text-amber-800 border border-amber-200'
                    }`}>
                      {composerOutput.decision}
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Live Presence Cursor tag near composer */}
            <div className="absolute -bottom-5 right-6 hidden sm:flex">
              <AvatarCursor
                initials="AC"
                name="Alexa Chen (Admin)"
                color="green"
                pointerDirection="top-left"
              />
            </div>
          </motion.div>
          <div className="hero-product-detail" aria-hidden="true">
            <div><span>Tool registry</span><strong>approve_invoice</strong><small>Automatic limit: IDR 5,000,000</small></div>
            <div><span>Approval gate</span><strong>Human review required</strong><small>Invoice exceeds the automatic limit.</small></div>
            <div><span>Data protection</span><strong>Outbound request blocked</strong><small>Destination or content did not meet policy.</small></div>
            <div><span>Evidence</span><strong>Decision recorded</strong><small>Review execution and anchor status.</small></div>
          </div>
          </div>
          </div>

        </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 2. SOCIAL PROOF / INFINITE LOGO MARQUEE (STEEP CAROUSEL-SCROLL)            */}
      {/* ========================================================================= */}
      <section className="py-14 border-y border-[#ececec] bg-white overflow-hidden">
        <div className="max-w-[1240px] mx-auto px-6 mb-7 text-center">
          <p className="text-[14px] text-[#777b86] font-sans font-normal tracking-wide">
            Engineered for enterprise AI platform teams, security leads, and compliance reviewers
          </p>
        </div>

        {/* Infinite Scrolling Ticker */}
        <div className="relative flex overflow-x-hidden">
          <div className="animate-carousel flex items-center justify-around gap-12 text-[#979799] font-sans text-[15px] font-medium tracking-wider uppercase select-none">
            <span>&bull; Nexora Technologies</span>
            <span>&bull; Hyperledger Besu</span>
            <span>&bull; RFC 8785 Canonical JSON</span>
            <span>&bull; Ed25519 HSM Signatures</span>
            <span>&bull; Deny-By-Default Gateway</span>
            <span>&bull; FastAPI REST Microservices</span>
            <span>&bull; QBFT Private Consensus</span>
            <span>&bull; Next.js 16 Enterprise Shell</span>
            {/* Repeated for continuous seamless loop */}
            <span>&bull; Nexora Technologies</span>
            <span>&bull; Hyperledger Besu</span>
            <span>&bull; RFC 8785 Canonical JSON</span>
            <span>&bull; Ed25519 HSM Signatures</span>
            <span>&bull; Deny-By-Default Gateway</span>
            <span>&bull; FastAPI REST Microservices</span>
            <span>&bull; QBFT Private Consensus</span>
            <span>&bull; Next.js 16 Enterprise Shell</span>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 3. AUTO-PLAYING TABBED WORKBENCH (STEEP PROGRESS-FILL ANIMATION)           */}
      {/* ========================================================================= */}
      <section
        id="workbench"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
        className="py-24 px-6 bg-[#fafafb]"
      >
        <div className="max-w-[1240px] mx-auto space-y-12">
          {/* Section Header */}
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-[12px] font-semibold uppercase tracking-wider text-[#979799]">
              The Veritas Engine
            </span>
            <h2 className="font-display text-[44px] sm:text-[56px] text-[#17191c] leading-[1.08] tracking-[-0.02em]">
              A new kind of <em>governance</em> platform
            </h2>
            <p className="text-[17px] text-[#777b86] font-sans">
              No more unverified agent actions. Engineering teams ship autonomous systems with mathematical proof of what was evaluated and executed.
            </p>
          </div>

          {/* Workbench Tabs with Auto-Fill Progress Bar (Steep Signature Interaction!) */}
          <div className="flex justify-center">
            <div className="inline-flex p-1.5 rounded-full bg-[#f2f2f3] border border-[#ececec]">
              {[
                { id: 'policy', label: '01. Policy Gate Runtime' },
                { id: 'approval', label: '02. Human Authorization' },
                { id: 'receipt', label: '03. Tamper-Proof Receipts' },
              ].map((t) => {
                const isActive = activeTab === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      setActiveTab(t.id as typeof activeTab);
                      setTabProgressKey((k) => k + 1);
                    }}
                    className={`relative overflow-hidden px-5 py-2.5 rounded-full text-[14px] font-medium transition-all ${
                      isActive
                        ? 'bg-[#17191c] text-white shadow-sm'
                        : 'text-[#777b86] hover:text-[#17191c]'
                    }`}
                  >
                    {/* Animated Progress Bar under active tab */}
                    {isActive && !isPaused && (
                      <div
                        key={tabProgressKey}
                        className="absolute bottom-0 left-0 h-[2px] bg-white/40 animate-progress-fill"
                      />
                    )}
                    <span className="relative z-10">{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tab 1: Policy Gate View */}
          <AnimatePresence mode="wait">
            {activeTab === 'policy' && (
              <motion.div
                key="policy"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="bg-white rounded-[24px] p-8 md:p-10 border border-[#ececec] shadow-[0_0_0_1px_rgba(4,23,43,0.05),0_20px_25px_-5px_rgba(0,0,0,0.08),0_8px_10px_-6px_rgba(0,0,0,0.04)] grid grid-cols-1 lg:grid-cols-12 gap-8 items-center"
              >
                <div className="lg:col-span-5 space-y-6">
                  <div className="space-y-2">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
                      Deterministic Boundary
                    </span>
                    <h3 className="font-display text-[28px] text-[#17191c]">
                      Enforce Limits Outside the LLM
                    </h3>
                    <p className="text-[14px] text-[#777b86] leading-relaxed">
                      Set organization thresholds. Any tool proposal above the limit halts immediately at the Policy Gate before the sandbox invokes the tool.
                    </p>
                  </div>

                  <div className="space-y-4 pt-2">
                    <div className="space-y-1.5">
                      <label className="text-[13px] font-medium text-[#17191c]">Select Vendor</label>
                      <select
                        value={wbVendor}
                        onChange={(e) => setWbVendor(e.target.value)}
                        className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-4 py-2.5 text-[14px] text-[#17191c] focus:outline-none"
                      >
                        <option value="PT Global Tech">PT Global Tech (Whitelisted)</option>
                        <option value="Nvidia Enterprise">Nvidia Enterprise (Whitelisted)</option>
                        <option value="Unverified Supplier">Unverified Supplier (Unlisted)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-[13px]">
                        <span className="font-medium text-[#17191c]">Amount (Threshold: 5M IDR)</span>
                        <span className="font-mono font-medium text-emerald-800">
                          Rp {wbAmount.toLocaleString()}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={1000000}
                        max={12000000}
                        step={500000}
                        value={wbAmount}
                        onChange={(e) => setWbAmount(Number(e.target.value))}
                        className="w-full accent-[#17191c]"
                      />
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-7 bg-[#fafafb] p-6 rounded-2xl border border-[#ececec] space-y-4">
                  <div className="flex items-center justify-between border-b border-[#ececec] pb-3">
                    <span className="text-[12px] font-semibold uppercase tracking-wider text-[#979799]">
                      Gateway State Machine
                    </span>
                    <span className={`px-3 py-1 rounded-full text-[12px] font-medium transition-all ${
                      wbAmount <= 5000000 && wbVendor !== 'Unverified Supplier'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-amber-50 text-amber-800 border border-amber-200'
                    }`}>
                      {wbAmount <= 5000000 && wbVendor !== 'Unverified Supplier'
                        ? 'ALLOWED &bull; AUTO-EXECUTE'
                        : 'APPROVAL_REQUIRED &bull; HELD'}
                    </span>
                  </div>

                  <div className="space-y-3 font-mono text-[12px]">
                    <div className="p-3 bg-white rounded-xl border border-[#ececec]">
                      <span className="text-[#979799] block text-[10px] uppercase font-sans">
                        Harness Input Digest
                      </span>
                      <span className="text-[#17191c] break-all">
                        SHA256({JSON.stringify({ tool: "approve_invoice", amount: wbAmount, vendor: wbVendor })})
                      </span>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-[#ececec]">
                      <span className="text-[#979799] block text-[10px] uppercase font-sans">
                        Runtime Action
                      </span>
                      <span className={wbAmount <= 5000000 ? 'text-emerald-700' : 'text-amber-800'}>
                        {wbAmount <= 5000000
                          ? '> Auto-approved: Simulated tool executed in sandbox. Signed Ed25519 receipt generated.'
                          : '> Blocked: Invoice exceeds auto limit of Rp 5,000,000. Pending approver role sign-off.'}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Tab 2: Human Authorization View */}
            {activeTab === 'approval' && (
              <motion.div
                key="approval"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="bg-white rounded-[24px] p-8 md:p-10 border border-[#ececec] shadow-[0_0_0_1px_rgba(4,23,43,0.05),0_20px_25px_-5px_rgba(0,0,0,0.08),0_8px_10px_-6px_rgba(0,0,0,0.04)] space-y-6"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#ececec]">
                  <div>
                    <h3 className="font-display text-[26px] text-[#17191c]">
                      Human-in-the-Loop Approval Queue
                    </h3>
                    <p className="text-[14px] text-[#777b86]">
                      Authorized approvers review invoice details and sign with role-checked credentials.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] text-[#777b86]">Role-checked:</span>
                    <span className="px-3 py-1 rounded-full bg-[#17191c] text-white text-[12px] font-mono">
                      approver / admin
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-2xl bg-[#fafafb] border border-[#ececec] space-y-3 hover:-translate-y-1 transition-transform">
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-[12px] text-[#17191c] font-medium">INV-2036-001</span>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                        PENDING SIGN-OFF
                      </span>
                    </div>
                    <div className="text-[20px] font-medium text-[#17191c]">
                      Rp 8.500.000 &bull; PT Global Tech
                    </div>
                    <p className="text-[13px] text-[#777b86]">
                      Quarterly Cloud & Server Hardware Infrastructure Maintenance
                    </p>
                    <div className="pt-2 flex items-center justify-between">
                      <AvatarCursor initials="SJ" name="Sarah Jenkins (Approver)" color="peach" pointerDirection="top-left" />
                      <Link
                        href="/dashboard/approvals"
                        className="group pill-button-filled !h-9 !px-4 !text-[13px]"
                      >
                        <span>Authorize</span>
                        <span className="arrow-slide inline-block">&rarr;</span>
                      </Link>
                    </div>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#fafafb] border border-[#ececec] space-y-3 opacity-75">
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-[12px] text-[#17191c] font-medium">INV-2036-003</span>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200">
                        REJECTED
                      </span>
                    </div>
                    <div className="text-[20px] font-medium text-[#17191c]">
                      Rp 12.000.000 &bull; Unknown Overseas Trading
                    </div>
                    <p className="text-[13px] text-[#777b86]">
                      Rejected by Sarah Jenkins: Vendor not in approved procurement database.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Tab 3: Tamper-Proof Receipts View */}
            {activeTab === 'receipt' && (
              <motion.div
                key="receipt"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="bg-white rounded-[24px] p-8 md:p-10 border border-[#ececec] shadow-[0_0_0_1px_rgba(4,23,43,0.05),0_20px_25px_-5px_rgba(0,0,0,0.08),0_8px_10px_-6px_rgba(0,0,0,0.04)] space-y-6"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#ececec]">
                  <div>
                    <h3 className="font-display text-[26px] text-[#17191c]">
                      Interactive Tamper Verification
                    </h3>
                    <p className="text-[14px] text-[#777b86]">
                      Test mathematical tamper detection. Modifying 1 byte in the receipt immediately breaks the SHA-256 digest and Ed25519 signature.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setWbTampered(!wbTampered)}
                    className={`px-4 py-2 rounded-full text-[13px] font-medium active:scale-95 transition-all ${
                      wbTampered
                        ? 'bg-amber-600 text-white'
                        : 'bg-white border border-[#17191c] text-[#17191c] hover:bg-[#17191c] hover:text-white'
                    }`}
                  >
                    {wbTampered ? 'Restore Original Evidence' : 'Simulate Modifying 1 Byte'}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-[#fafafb] border border-[#ececec] space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-[#979799]">
                      1. Recomputed SHA-256
                    </span>
                    <p className="font-mono text-[12px] text-[#17191c] truncate">
                      {wbTampered ? '0x99f4a1bc0991823...' : '0x17c09e3a65492d3...'}
                    </p>
                    <span className={`text-[11px] font-medium ${wbTampered ? 'text-rose-700' : 'text-emerald-700'}`}>
                      {wbTampered ? '&bull; Mismatch with header' : '&bull; Exact byte match'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#fafafb] border border-[#ececec] space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-[#979799]">
                      2. Ed25519 Key Check
                    </span>
                    <p className="font-mono text-[12px] text-[#17191c] truncate">
                      harness-ed25519-v1
                    </p>
                    <span className={`text-[11px] font-medium ${wbTampered ? 'text-rose-700' : 'text-emerald-700'}`}>
                      {wbTampered ? '&bull; Signature Invalid' : '&bull; Cryptographically Valid'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#fafafb] border border-[#ececec] space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-[#979799]">
                      3. Besu Anchor
                    </span>
                    <p className="font-mono text-[12px] text-[#17191c]">
                      Block #10482
                    </p>
                    <span className={`text-[11px] font-medium ${wbTampered ? 'text-rose-700' : 'text-emerald-700'}`}>
                      {wbTampered ? '&bull; Hash missing on chain' : '&bull; Confirmed on private ledger'}
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 4. BENTO GRID OF CARDS (STEEP STYLE WITH ACCENT PEACH CARD)               */}
      {/* ========================================================================= */}
      <section id="features" className="py-24 px-6 bg-white">
        <div className="max-w-[1240px] mx-auto space-y-14">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-[12px] font-semibold uppercase tracking-wider text-[#979799]">
              Core Principles
            </span>
            <h2 className="font-display text-[44px] sm:text-[56px] text-[#17191c] leading-[1.08] tracking-[-0.02em]">
              Architected for enterprise compliance
            </h2>
            <p className="text-[17px] text-[#777b86] font-sans">
              Three pillars that turn black-box AI model outputs into enforceable corporate actions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {/* Card 1: Neutral Mist Gray with hover elevation */}
            <motion.div
              whileHover={{ y: -4 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="bg-[#f2f2f3] rounded-[24px] p-8 md:p-10 space-y-6 flex flex-col justify-between"
            >
              <div className="space-y-4">
                <span className="text-[12px] font-mono font-medium text-[#979799] tracking-wider uppercase">
                  01 / SEPARATION OF CONCERNS
                </span>
                <h3 className="font-display text-[26px] text-[#17191c] leading-snug">
                  Planning without execution privileges
                </h3>
                <p className="text-[15px] text-[#777b86] leading-relaxed font-sans">
                  The Agent model process only generates bounded JSON proposals. It holds zero database write credentials, zero tool tokens, and zero blockchain keys.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#ececec] font-mono text-[11px] space-y-1 text-[#17191c]">
                <div className="text-[#979799]"># Isolated Agent API</div>
                <div>POST /internal/v1/plans</div>
                <div className="text-emerald-700">status: 200 {`{ "proposal": "approve_invoice" }`}</div>
              </div>
            </motion.div>

            {/* Card 2: SIGNATURE BLUSH PEACH ACCENT CARD (Strictly once per page) */}
            <motion.div
              whileHover={{ y: -4 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="bg-[#fbe1d1] text-[#5d2a1a] rounded-[24px] p-8 md:p-10 space-y-6 flex flex-col justify-between"
            >
              <div className="space-y-4">
                <span className="text-[12px] font-mono font-medium tracking-wider uppercase opacity-80">
                  02 / ENTERPRISE ASSURANCE
                </span>
                <h3 className="font-display text-[26px] leading-snug">
                  Guaranteed mathematical provenance
                </h3>
                <blockquote className="text-[15px] leading-relaxed italic opacity-95">
                  &ldquo;Every approved invoice produces a signed canonical digest. If an attacker modifies even a single character, verification fails immediately.&rdquo;
                </blockquote>
              </div>

              <div className="flex items-center gap-3 pt-2 border-t border-[#5d2a1a]/20">
                <div className="w-9 h-9 rounded-full bg-[#5d2a1a] text-[#fbe1d1] flex items-center justify-center font-sans font-medium text-[12px]">
                  EK
                </div>
                <div>
                  <div className="font-medium text-[14px]">Dr. Elena Rostova</div>
                  <div className="text-[11px] opacity-80">Chief Technology Officer, Nexora</div>
                </div>
              </div>
            </motion.div>

            {/* Card 3: Neutral Mist Gray */}
            <motion.div
              whileHover={{ y: -4 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="bg-[#f2f2f3] rounded-[24px] p-8 md:p-10 space-y-6 flex flex-col justify-between"
            >
              <div className="space-y-4">
                <span className="text-[12px] font-mono font-medium text-[#979799] tracking-wider uppercase">
                  03 / IMMUTABILITY
                </span>
                <h3 className="font-display text-[26px] text-[#17191c] leading-snug">
                  Private ledger anchoring
                </h3>
                <p className="text-[15px] text-[#777b86] leading-relaxed font-sans">
                  Zero public tokens, zero user wallets, zero transaction fees. Pure proof-of-action digests recorded to a private Hyperledger Besu blockchain network.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#ececec] font-mono text-[11px] space-y-1 text-[#17191c]">
                <div className="text-[#979799]"># Hyperledger Besu Anchor</div>
                <div>Receipt: rcpt_7f3b8901e4d2...</div>
                <div className="text-emerald-700">&bull; Block #10482 [CONFIRMED]</div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 5. TOPOLOGY EXPLORER: FIVE INDEPENDENT REST SERVICES                      */}
      {/* ========================================================================= */}
      <section id="architecture" className="py-24 px-6 bg-[#fafafb] border-t border-[#ececec]">
        <div className="max-w-[1240px] mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-[12px] font-semibold uppercase tracking-wider text-[#979799]">
              System Boundaries
            </span>
            <h2 className="font-display text-[44px] sm:text-[56px] text-[#17191c] leading-[1.08] tracking-[-0.02em]">
              Five independent REST services
            </h2>
            <p className="text-[17px] text-[#777b86] font-sans">
              Decoupled failure domains ensuring total security isolation between browser, agent planning, and protected tools.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-[#ececec] space-y-2 shadow-sm hover:-translate-y-1 transition-transform">
              <span className="text-[11px] font-mono text-[#979799]">Port :3000</span>
              <h4 className="font-display text-[18px] text-[#17191c]">Frontend</h4>
              <p className="text-[12px] text-[#777b86]">
                Next.js App Router. Landing page, operator console, Trust Explorer.
              </p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-[#ececec] space-y-2 shadow-sm hover:-translate-y-1 transition-transform">
              <span className="text-[11px] font-mono text-[#979799]">Port :8000</span>
              <h4 className="font-display text-[18px] text-[#17191c]">Backend BFF</h4>
              <p className="text-[12px] text-[#777b86]">
                FastAPI public gateway. Tenant RBAC, session auth, project context.
              </p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-[#ececec] space-y-2 shadow-sm hover:-translate-y-1 transition-transform">
              <span className="text-[11px] font-mono text-[#979799]">Port :8001</span>
              <h4 className="font-display text-[18px] text-[#17191c]">Agent Worker</h4>
              <p className="text-[12px] text-[#777b86]">
                LLM reasoning service. Structured proposals only. Nol tool access.
              </p>
            </div>

            <div className="bg-white p-5 rounded-2xl border-2 border-[#17191c] space-y-2 shadow-md hover:-translate-y-1 transition-transform">
              <span className="text-[11px] font-mono text-[#17191c] font-bold">Port :8002 &bull; Core</span>
              <h4 className="font-display text-[18px] text-[#17191c]">Harness Gateway</h4>
              <p className="text-[12px] text-[#777b86]">
                Policy runtime, approval state machine, Ed25519 signing.
              </p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-[#ececec] space-y-2 shadow-sm hover:-translate-y-1 transition-transform">
              <span className="text-[11px] font-mono text-[#979799]">Port :8003</span>
              <h4 className="font-display text-[18px] text-[#17191c]">Besu Adapter</h4>
              <p className="text-[12px] text-[#777b86]">
                Smart contract anchoring adapter for private Hyperledger Besu.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 6. FINAL CALL TO ACTION (STEEP MINIMALIST CALLOUT)                        */}
      {/* ========================================================================= */}
      <section className="py-24 px-6 bg-white border-t border-[#ececec] text-center">
        <div className="max-w-[760px] mx-auto space-y-7">
          <h2 className="font-display text-[44px] sm:text-[60px] text-[#17191c] leading-[1.05] tracking-[-0.02em]">
            Get started with Veritas today
          </h2>
          <p className="text-[18px] text-[#777b86] font-sans">
            Explore the live enterprise console for Nexora Technologies or verify execution receipts in the Trust Explorer.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-2">
            <Link
              href="/dashboard"
              className="group pill-button-filled !h-12 !px-8 !text-[16px]"
            >
              <span>Launch Enterprise Console</span>
              <span className="arrow-slide inline-block">&rarr;</span>
            </Link>
            <Link
              href="/dashboard/trust"
              className="pill-button-ghost !h-12 !px-8 !text-[16px]"
            >
              <span>Open Trust Explorer</span>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
