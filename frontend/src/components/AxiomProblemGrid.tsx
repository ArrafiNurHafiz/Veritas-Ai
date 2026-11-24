'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { EyeOff, ShieldAlert, FileX, CheckCircle2 } from 'lucide-react';
import { motion } from 'motion/react';

const problems = [
  {
    icon: EyeOff,
    tag: 'VISIBILITY',
    title: 'Visibility shrinks as autonomy scales',
    subtitle: 'Prompt logs cannot track multi-step loops.',
    description:
      'When agents plan 10+ steps ahead across autonomous tool loops, humans cannot review token streams in real-time. Without a dedicated gateway, unauthorized invocations execute before anyone notices.',
    metric: '94%',
    metricLabel: 'of agent security breaches occur in unintercepted tool chains',
    accentColor: '#DA5C2B',
  },
  {
    icon: ShieldAlert,
    tag: 'BOUNDARY',
    title: 'Prompt guardrails break at the model boundary',
    subtitle: 'Adversarial injections bypass LLM self-policing.',
    description:
      'Asking the model to check its own tools is like asking a suspect to guard the evidence room. Veritas extracts the policy runtime completely outside the LLM context into deterministic Python rules.',
    metric: '0%',
    metricLabel: 'LLM self-governance authority in the Veritas Harness',
    accentColor: '#EF4444',
  },
  {
    icon: FileX,
    tag: 'COMPLIANCE',
    title: 'Audit logs without cryptographic receipts are liabilities',
    subtitle: 'Editable database rows fail regulatory audit.',
    description:
      'Standard application logs can be modified or spoofed. Veritas signs every execution before releasing protected tool output, creating immutable Ed25519 evidence anchored to a cryptographic digest.',
    metric: '100%',
    metricLabel: 'Ed25519 verifiable non-repudiation on all released tool calls',
    accentColor: '#22C55E',
  },
];

export default function AxiomProblemGrid() {
  const [mousePos, setMousePos] = useState<{ [key: number]: { x: number; y: number } }>({});

  const handleMouseMove = (idx: number, e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePos((prev) => ({
      ...prev,
      [idx]: {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      },
    }));
  };

  return (
    <section id="problems" className="py-24 sm:py-32 bg-[#08090A] border-b border-[#1A1C22]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Heading with scroll reveal */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl"
        >
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
            Why Traditional Security Fails
          </p>
          <h2 className="mt-4 text-[32px] font-medium leading-[1.1] tracking-[-0.03em] text-white sm:text-[44px] md:text-[52px]">
            What worked for chatbots <br />
            <span className="text-[#8F94A0]">doesn&apos;t work for autonomous agents.</span>
          </h2>
          <p className="mt-5 text-[16px] leading-relaxed text-[#8F94A0]">
            Autonomous agents do not just generate chat replies—they execute protected tools, invoice approvals, and database updates. When agents act on external systems, probabilistic prompt guardrails collapse.
          </p>
        </motion.div>

        {/* 3 Bento Cards with Staggered Scroll Animation and Spotlight Hover */}
        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
          {problems.map((p, idx) => {
            const Icon = p.icon;
            const pos = mousePos[idx] || { x: 0, y: 0 };
            return (
              <motion.div
                key={p.tag}
                initial={{ opacity: 0, y: 32 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.65, delay: idx * 0.15, ease: [0.16, 1, 0.3, 1] }}
                onMouseMove={(e) => handleMouseMove(idx, e)}
                className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-[#1E2129] bg-[#0D0E13] p-7 transition-all duration-300 hover:border-[#DA5C2B]/40 hover:bg-[#101218] hover:-translate-y-1"
              >
                {/* Mouse-tracking radial spotlight glow */}
                <div
                  className="pointer-events-none absolute -inset-px opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                  style={{
                    background: `radial-gradient(400px circle at ${pos.x}px ${pos.y}px, rgba(218, 92, 43, 0.12), transparent 70%)`,
                  }}
                  aria-hidden="true"
                />

                {/* Top subtle highlight */}
                <div
                  className="pointer-events-none absolute inset-x-0 -top-px h-px opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                  style={{
                    background: `linear-gradient(90deg, transparent, ${p.accentColor}, transparent)`,
                  }}
                  aria-hidden="true"
                />

                <div className="relative z-10">
                  <div className="flex items-center justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#20232C] bg-[#14161F] text-white transition-transform group-hover:scale-105">
                      <Icon className="h-5 w-5" style={{ color: p.accentColor }} />
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-[#5A606E]">
                      {p.tag}
                    </span>
                  </div>

                  <h3 className="mt-6 text-[18px] font-semibold tracking-[-0.015em] text-white">
                    {p.title}
                  </h3>
                  <p className="mt-1 font-mono text-[11px] text-[#DA5C2B]">
                    {p.subtitle}
                  </p>
                  <p className="mt-4 text-[13px] leading-relaxed text-[#8F94A0]">
                    {p.description}
                  </p>
                </div>

                <div className="relative z-10 mt-8 border-t border-[#1C1E26] pt-5">
                  <div className="text-[26px] font-semibold tracking-tight text-white font-mono">
                    {p.metric}
                  </div>
                  <div className="mt-1 text-[11px] text-[#606575]">
                    {p.metricLabel}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Bottom banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-12 flex flex-col items-start justify-between gap-4 rounded-xl border border-[#20232C] bg-[#0E1015] p-6 sm:flex-row sm:items-center hover:border-[#DA5C2B]/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[#22C55E]/10 text-[#22C55E]">
              <CheckCircle2 className="h-4 w-4" />
            </span>
            <div>
              <p className="text-[13px] font-medium text-white">
                The Solution: Control Before Action (Veritas Architectural Pattern)
              </p>
              <p className="text-[12px] text-[#7D828F]">
                The agent proposes. The deterministic harness inspects. Human approves if needed. Signed receipt is recorded.
              </p>
            </div>
          </div>
          <Link
            href="/#features"
            className="group inline-flex items-center gap-1.5 whitespace-nowrap text-[12px] font-medium text-[#DA5C2B] hover:underline"
          >
            <span>Explore the 3 Gateways</span>
            <span aria-hidden="true" className="axiom-btn-arrow font-mono">
              <span className="arrow-primary">→</span>
              <span className="arrow-secondary">→</span>
            </span>
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
