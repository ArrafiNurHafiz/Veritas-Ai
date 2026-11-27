'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowRight,
  Play,
  X,
  Lock,
} from 'lucide-react';
import SauceHeroCanvas from '@/components/SauceHeroCanvas';

const MARQUEE_ITEMS = [
  'PostgreSQL 16 Append-Only Audit',
  'Ed25519 Signed Receipts',
  'RFC 8785 Canonical JSON',
  'Odoo & SAP HMAC Webhooks',
  'Docker Network Isolation (agent_net)',
  'PKCE OIDC + Scrypt Sessions',
  'Anti-TOCTOU Resume Revalidation',
  'Prometheus /metrics Telemetry',
];

const OUTCOME_CARDS = [
  {
    tag: 'CONTROL',
    dotColor: 'bg-[#6DB33F]',
    pixelColors: ['#ABE082', '#D8F3C0', '#6DB33F'],
    title: 'Verify every AI action against policy intent',
    desc: 'Deterministic policy checks validate schemas, FX-normalized ceilings, and vendor allowlists before any tool executes.',
    stat: '0',
    statSuffix: 'calls',
    statLabel: 'UNVERIFIED TOOL CALLS TO ERP',
    bullets: [
      'Server ToolRegistry blocks unknown tools',
      'USD / SGD / EUR normalized to IDR',
      'Prompt injections treated as raw data',
    ],
  },
  {
    tag: 'SPEED & SAFETY',
    dotColor: 'bg-[#E5A91A]',
    pixelColors: ['#F1E082', '#F7ECAE', '#F1BE23'],
    title: 'Keep humans at the core of high-risk approvals',
    desc: 'Low-risk actions auto-execute in milliseconds while high-value requests pause safely until an independent Approver signs off.',
    stat: '100',
    statSuffix: '%',
    statLabel: 'SEPARATION OF DUTIES ENFORCED',
    bullets: [
      '403 block if requester tries to approve',
      'Optimistic lock prevents race conditions',
      'Anti-TOCTOU revalidation on resume',
    ],
  },
  {
    tag: 'PROVEN PROOF',
    dotColor: 'bg-[#4790DD]',
    pixelColors: ['#BED1E4', '#DCE7F3', '#4790DD'],
    title: 'Prove compliance with cryptographic receipts',
    desc: 'Every allow, hold, or deny writes to an append-only hash chain and issues an Ed25519 receipt verifiable offline or in browser.',
    stat: '1',
    statSuffix: 'byte',
    statLabel: 'TAMPER DETECTION SENSITIVITY',
    bullets: [
      'PostgreSQL 16 triggers reject UPDATE/DELETE',
      'RFC 8785 canonical JSON + 128-bit nonce',
      'Live 1-byte tamper test in Trust Explorer',
    ],
  },
];

const ROLES = [
  {
    id: 'operator',
    tab: 'Operator',
    heading: 'For the Operator',
    sub: 'Task dispatch & policy visibility without approval conflicts.',
    route: '/dashboard/tasks',
    cta: 'OPEN TASK CENTER',
    stripTint: 'bg-[#D8E5BE]',
    dividerColor: 'border-[#9BB86A]',
    dotColor: 'bg-[#6DB33F]',
    outcomes: [
      'Dispatch tasks across 4 bounded AI agents',
      'Idempotency-Key prevents duplicate executions',
      'Blocked from approving own requests (403 SoD)',
    ],
  },
  {
    id: 'approver',
    tab: 'Approver',
    heading: 'For the Approver',
    sub: 'Human-in-the-loop sign-off that stops risky actions cold.',
    route: '/dashboard/approvals',
    cta: 'OPEN APPROVAL QUEUE',
    stripTint: 'bg-[#F1E082]',
    dividerColor: 'border-[#D4B83A]',
    dotColor: 'bg-[#E5A91A]',
    outcomes: [
      'Review WAITING_APPROVAL tasks held with 0 tool calls',
      'Inspect args_hash and policy_version lock',
      'Trigger ERP Sandbox sync-back on decision',
    ],
  },
  {
    id: 'admin',
    tab: 'Admin',
    heading: 'For the Admin',
    sub: 'Organization-wide guardrails, toggles, and audit control.',
    route: '/dashboard/policies',
    cta: 'OPEN POLICY MANAGER',
    stripTint: 'bg-[#EBC4D8]',
    dividerColor: 'border-[#D18FB3]',
    dotColor: 'bg-[#E070A8]',
    outcomes: [
      'Publish versioned auto-approve & hard-cap rules',
      'Enable or disable individual agents & tools live',
      'Onboard tenants & confirm ledger anchors',
    ],
  },
  {
    id: 'auditor',
    tab: 'Auditor',
    heading: 'For the Auditor',
    sub: 'Independent verification that never trusts mutable logs.',
    route: '/dashboard/trust',
    cta: 'OPEN TRUST EXPLORER',
    stripTint: 'bg-[#BED1E4]',
    dividerColor: 'border-[#7BA7D4]',
    dotColor: 'bg-[#4790DD]',
    outcomes: [
      'Verify Ed25519 signatures & RFC 8785 digests',
      'Run 1-byte tamper sandbox tests in real time',
      'Strictly read-only zero-mutation access',
    ],
  },
];

function TopPixelMosaic({ colors }: { colors: string[] }) {
  // Subtle pixelated mosaic along the top of Strategic Outcome cards (matching Screenshot 2)
  const cells = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2];
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 top-0 h-20 overflow-hidden opacity-55"
      style={{
        maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%)',
        WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%)',
      }}
    >
      <div className="grid grid-cols-12 gap-0.5">
        {cells.map((cIdx, idx) => (
          <div
            key={idx}
            className="h-5"
            style={{
              backgroundColor: idx % 3 === 0 ? 'transparent' : colors[cIdx % colors.length],
              opacity: ((idx * 7) % 10) / 14 + 0.2,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function SauceHeroAndOutcomes() {
  const [activeRole, setActiveRole] = useState<string>('admin');
  const [videoPlaying, setVideoPlaying] = useState(false);

  const currentRole = ROLES.find((r) => r.id === activeRole) || ROLES[2];

  return (
    <>
      {/* 1. CENTERED HERO SECTION */}
      <section
        className="relative overflow-hidden min-h-[76vh] flex flex-col justify-center pt-16 pb-20 sm:pt-24 sm:pb-24"
        style={{
          backgroundColor: '#F0F0EC',
          backgroundImage:
            'linear-gradient(180deg, rgba(240,240,236,0) 0%, rgba(241,224,130,0.52) 50%, rgba(240,240,236,1) 100%)',
        }}
      >
        <SauceHeroCanvas />
        <div className="max-w-[980px] mx-auto px-5 sm:px-8 text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-6"
          >
            <p className="font-mono text-[12px] uppercase tracking-[0.2em] text-[#2D372D]">
              FROM AI INTENT TO PRODUCTION CONFIDENCE
            </p>

            <h1 className="font-display text-[46px] sm:text-[64px] lg:text-[74px] font-medium leading-[0.96] tracking-[-0.03em] text-[#192319]">
              Verify AI-proposed actions at the pace they&apos;re generated.
            </h1>

            <p className="text-[17px] sm:text-[19px] leading-[1.5] text-[#2D372D] max-w-[62ch] mx-auto">
              VERITAS is the deterministic runtime governance harness for enterprise AI agents.
              It intercepts proposals, enforces human approvals, and signs Ed25519 receipts.
            </p>

            <div className="pt-2 flex flex-wrap items-center justify-center gap-3.5">
              <Link
                href="/dashboard"
                className="group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-[#192319] text-[#F0F0EC] font-semibold text-[15px] hover:bg-[#043423] active:scale-[0.98] transition-all"
              >
                <span>Open Live Console</span>
                <span className="sauce-btn-arrow">
                  <ArrowRight className="w-4 h-4 arrow-primary text-[#ABE082]" />
                  <ArrowRight className="w-4 h-4 arrow-secondary text-[#ABE082]" />
                </span>
              </Link>
              <Link
                href="/dashboard/trust"
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full border border-[#192319] bg-[#F8F8F8] text-[#192319] font-semibold text-[15px] hover:bg-[#ABE082] active:scale-[0.98] transition-all"
              >
                <Lock className="w-4 h-4" />
                <span>Verify Receipts</span>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 2. STANDARDS MARQUEE STRIP */}
      <section className="bg-[#F0F0EC] py-5 overflow-hidden border-y border-[#DCDCD7]">
        <div className="animate-sauce-marquee flex items-center gap-12">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, idx) => (
            <div key={idx} className="flex items-center gap-3 shrink-0">
              <span className="w-2.5 h-2.5 bg-[#192319]" />
              <span className="font-mono text-[12.5px] uppercase tracking-[0.12em] text-[#2D372D]">
                {item}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 3. VIDEO PLAYER SHOWCASE CARD (Matching Screenshot 3: Blue Shock Pixelated Video Player) */}
      <section className="bg-[#F0F0EC] py-14 sm:py-16">
        <div className="max-w-[820px] mx-auto px-5 sm:px-8">
          <motion.div
            initial={{ opacity: 0, y: 26 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="relative rounded-[28px] overflow-hidden border border-[#C8C8BE] shadow-[0_28px_64px_-24px_rgba(25,35,25,0.22)] w-full aspect-video bg-[#F0F0EC]"
          >
            {!videoPlaying ? (
              /* Crisp Video Poster State (0 bytes of video downloaded until Play is clicked) */
              <div
                onClick={() => setVideoPlaying(true)}
                className="relative w-full h-full cursor-pointer group"
              >
                <Image
                  src="/veritas-thumb.jpg"
                  alt="VERITAS — Control Before Action video preview"
                  fill
                  unoptimized
                  sizes="(max-width: 820px) 100vw, 820px"
                  className="object-cover transition-transform duration-500 group-hover:scale-[1.015]"
                />
                <div className="absolute inset-0 bg-[#192319]/10 group-hover:bg-[#192319]/20 transition-colors" />

                {/* Centered Play Button */}
                <button
                  type="button"
                  aria-label="Play VERITAS walkthrough"
                  className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 rounded-full bg-[#192319]/85 backdrop-blur-md border border-[#ABE082]/70 flex items-center justify-center text-[#ABE082] group-hover:scale-110 group-hover:bg-[#192319] transition-all shadow-xl"
                >
                  <Play className="w-8 h-8 fill-[#ABE082] ml-1" />
                </button>

                <span className="absolute bottom-4 right-4 font-mono text-[11px] uppercase tracking-[0.14em] text-[#F0F0EC] bg-[#192319]/80 backdrop-blur-sm px-3.5 py-1.5 rounded-full border border-white/15">
                  Watch 10s Overview
                </span>
              </div>
            ) : (
              /* Lazy-loaded HTML5 Video Player (0 bytes downloaded until Play is clicked) */
              <div className="relative z-10 w-full h-full bg-[#192319] flex items-center justify-center">
                <button
                  type="button"
                  onClick={() => setVideoPlaying(false)}
                  aria-label="Close video player"
                  className="absolute top-4 right-4 z-20 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#192319]/80 hover:bg-[#192319] border border-white/25 text-white text-[12px] font-medium backdrop-blur-sm transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Close</span>
                </button>
                <video
                  controls
                  autoPlay
                  playsInline
                  preload="metadata"
                  poster="/veritas-thumb.jpg"
                  onEnded={() => setVideoPlaying(false)}
                  className="w-full h-full object-cover"
                >
                  <source src="/veritas-demo.mp4" type="video/mp4" />
                  <source src="/veritas-demo.webm" type="video/webm" />
                </video>
              </div>
            )}
          </motion.div>
        </div>
      </section>

      {/* 4. STRATEGIC OUTCOMES — 3 PORTRAIT CARDS (Matching Screenshot 2) */}
      <section id="outcomes" className="bg-[#F0F0EC] py-16 sm:py-24">
        <div className="max-w-[1180px] mx-auto px-5 sm:px-8 space-y-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.55 }}
            className="text-center max-w-2xl mx-auto space-y-3"
          >
            <span className="font-mono text-[11.5px] uppercase tracking-[0.18em] text-[#6D7344]">
              Strategic Outcomes
            </span>
            <h2 className="font-display text-[38px] sm:text-[50px] leading-[1.05] text-[#192319]">
              Governance built for autonomous operations.
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {OUTCOME_CARDS.map((card, i) => (
              <motion.div
                key={card.tag}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="relative overflow-hidden rounded-[24px] border border-[#DCDCD7] p-7 sm:p-8 flex flex-col justify-between space-y-7 hover:border-[#192319] transition-colors"
                style={{
                  background:
                    'linear-gradient(155deg, #F8F8FB 0%, #EFEBF4 55%, #F4F6FA 100%)',
                }}
              >
                <TopPixelMosaic colors={card.pixelColors} />

                <div className="relative z-10 space-y-4 pt-3">
                  <div className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[#2D372D]">
                    <span className={`w-2.5 h-2.5 rounded-full ${card.dotColor}`} />
                    <span>{card.tag}</span>
                  </div>

                  <h3 className="font-display text-[28px] leading-[1.12] text-[#192319]">
                    {card.title}
                  </h3>

                  <p className="text-[14.5px] leading-[1.55] text-[#2D372D]">{card.desc}</p>

                  <div className="pt-2">
                    <div className="flex items-baseline gap-1.5">
                      <span className="font-display text-[56px] leading-none font-normal text-[#192319] tabular-nums">
                        {card.stat}
                      </span>
                      <span className="font-display text-[26px] text-[#192319]">
                        {card.statSuffix}
                      </span>
                    </div>
                    <p className="mt-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-[#2D372D]">
                      {card.statLabel}
                    </p>
                  </div>
                </div>

                <ul className="relative z-10 space-y-2.5 pt-4 border-t border-[#DCDCD7]/70">
                  {card.bullets.map((b) => (
                    <li key={b} className="flex items-start gap-2.5 text-[13.5px] text-[#192319]">
                      <span className={`w-2 h-2 rounded-full ${card.dotColor} shrink-0 mt-1.5`} />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. ROLE SEGMENTATION CARD (Matching Screenshot 1: For the C-suite with left pixel strip) */}
      <section className="bg-[#F8F8F8] py-20 border-y border-[#ABAD6C]">
        <div className="max-w-[1120px] mx-auto px-5 sm:px-8 space-y-10">
          <div className="text-center max-w-3xl mx-auto space-y-5">
            <h2 className="font-display text-[34px] sm:text-[46px] leading-[1.08] text-[#192319]">
              VERITAS delivers outcomes at every level of your enterprise organization.
            </h2>

            <div className="inline-flex flex-wrap justify-center gap-1.5 p-1.5 rounded-full bg-[#F0F0EC] border border-[#DCDCD7]">
              {ROLES.map((r) => {
                const active = r.id === activeRole;
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setActiveRole(r.id)}
                    className={`relative px-5 py-2 rounded-full text-[13.5px] font-semibold transition-colors ${
                      active ? 'text-[#192319]' : 'text-[#2D372D] hover:text-[#192319]'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="sauce-role-pill"
                        transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                        className="absolute inset-0 rounded-full bg-[#ABE082] shadow-sm"
                      />
                    )}
                    <span className="relative z-10">{r.tab}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={currentRole.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.22 }}
              className="relative overflow-hidden rounded-[24px] border border-[#C8C8BE] flex min-h-[290px]"
              style={{
                background:
                  'linear-gradient(135deg, #F8F8FB 0%, #EFEBF4 55%, #F3F4F8 100%)',
              }}
            >
              {/* Left Vertical Textured Pixel Strip (Matching Screenshot 1) */}
              <div
                aria-hidden="true"
                className={`hidden sm:block w-16 shrink-0 border-r ${currentRole.dividerColor} ${currentRole.stripTint}/45 relative overflow-hidden`}
                style={{
                  backgroundImage:
                    'repeating-linear-gradient(-45deg, rgba(25,35,25,0.06) 0px, rgba(25,35,25,0.06) 1px, transparent 1px, transparent 6px)',
                }}
              />

              {/* Circular Pixel Badge overlapping divider (Matching Screenshot 1) */}
              <div
                aria-hidden="true"
                className={`hidden sm:flex absolute left-11 top-8 w-10 h-10 rounded-full ${currentRole.stripTint} border ${currentRole.dividerColor} items-center justify-center shadow-sm z-10`}
              >
                <span className={`w-3 h-3 rounded-full ${currentRole.dotColor}`} />
              </div>

              <div className="flex-1 p-7 sm:p-10 sm:pl-12 flex flex-col justify-between gap-8">
                <h3 className="font-display text-[36px] sm:text-[42px] leading-none text-[#192319]">
                  {currentRole.heading}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
                  <div className="md:col-span-6 space-y-6">
                    <p className="text-[20px] sm:text-[22px] leading-[1.35] text-[#192319]">
                      {currentRole.sub}
                    </p>
                    <Link
                      href={currentRole.route}
                      className="inline-flex items-center gap-2 font-mono text-[11.5px] uppercase tracking-[0.12em] text-[#192319] underline underline-offset-4 hover:text-[#043423]"
                    >
                      <span>{currentRole.cta}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  <div className="md:col-span-6 space-y-3">
                    <span className="block font-mono text-[11px] uppercase tracking-[0.16em] text-[#6D7344]">
                      OUTCOMES
                    </span>
                    <ul className="space-y-2.5">
                      {currentRole.outcomes.map((o) => (
                        <li key={o} className="flex items-start gap-2.5 text-[14.5px] text-[#192319]">
                          <span className={`w-2.5 h-2.5 rounded-full ${currentRole.dotColor} shrink-0 mt-1.5`} />
                          <span>{o}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </section>
    </>
  );
}
