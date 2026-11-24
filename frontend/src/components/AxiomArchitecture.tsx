'use client';

import React from 'react';
import { motion } from 'motion/react';

const boundaries = [
  {
    port: ':3000',
    title: 'Frontend Console',
    role: 'Next.js App Router',
    status: 'LIVE',
    statusColor: '#22C55E',
    desc: 'Operator console, task proposal streaming, human sign-off portal, and Trust Explorer.',
  },
  {
    port: ':8002',
    title: 'Harness Gateway',
    role: 'FastAPI Policy Runtime',
    status: 'LIVE · CORE',
    statusColor: '#DA5C2B',
    desc: 'Deterministic policy gates, human approval queue, Ed25519 asymmetric receipt signing, and outbound data quarantine.',
  },
  {
    port: ':8001',
    title: 'Agent Service',
    role: 'Proposal Planner',
    status: 'OPTIONAL',
    statusColor: '#A855F7',
    desc: 'Proposal-only planner behind shared token. Deterministic mock planner when unset. Never holds execution credentials.',
  },
  {
    port: 'EVM RPC',
    title: 'Anchor Adapter',
    role: 'Besu JSON-RPC',
    status: 'OPTIONAL',
    statusColor: '#A855F7',
    desc: 'Submits batch SHA-256 state roots to Besu EVM node. Local mock confirmation enabled by default.',
  },
  {
    port: 'Public GW',
    title: 'Backend BFF',
    role: 'Tenant Gateway',
    status: 'PLANNED',
    statusColor: '#5A606E',
    desc: 'Multi-tenant routing and project context. Currently, the Harness is the single vertical slice service.',
  },
];

export default function AxiomArchitecture() {
  return (
    <section id="architecture" className="border-b border-[#1A1C22] bg-[#07080A] py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header with scroll reveal */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col justify-between gap-6 md:flex-row md:items-end"
        >
          <div className="max-w-2xl">
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
              System Architecture
            </p>
            <h2 className="mt-4 text-[32px] font-medium leading-[1.1] tracking-[-0.03em] text-white sm:text-[44px]">
              One enforced path. <br />
              <span className="text-[#8F94A0]">Five clear boundaries.</span>
            </h2>
            <p className="mt-4 text-[15px] leading-relaxed text-[#8F94A0]">
              Control Before Action enforces rigid network and authorization barriers between the agent and protected tools.
            </p>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-4 font-mono text-[11px]">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#22C55E]" />
              <span className="text-white font-medium">LIVE</span> in repository
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#A855F7]" />
              <span className="text-[#A6ABB7]">OPTIONAL</span> via config
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#5A606E]" />
              <span className="text-[#666B79]">PLANNED</span>
            </span>
          </div>
        </motion.div>

        {/* 5 Column Cards with staggered scroll reveal */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.75, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="mt-14 grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[#1E2129] bg-[#1E2129] sm:grid-cols-2 lg:grid-cols-5"
        >
          {boundaries.map((b) => (
            <div
              key={b.title}
              className="flex flex-col justify-between bg-[#0B0C10] p-6 transition-colors hover:bg-[#0E1015]"
            >
              <div>
                <div className="flex items-center justify-between font-mono text-[10px]">
                  <span className="text-[#5A606E]">{b.port}</span>
                  <span
                    className="font-semibold"
                    style={{ color: b.statusColor }}
                  >
                    {b.status}
                  </span>
                </div>

                <h3 className="mt-6 text-[16px] font-semibold text-white">
                  {b.title}
                </h3>
                <p className="mt-1 font-mono text-[11px] text-[#DA5C2B]">
                  {b.role}
                </p>
                <p className="mt-3 text-[12px] leading-relaxed text-[#8F94A0]">
                  {b.desc}
                </p>
              </div>

              <div className="mt-6 border-t border-[#16181E] pt-3 font-mono text-[10px] text-[#555A67]">
                Status: Verified
              </div>
            </div>
          ))}
        </motion.div>

        {/* Footnote */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-[#555A67]">
          <span>Service isolation: The LLM agent NEVER holds direct execution credentials</span>
          <span>FastAPI uvicorn on :8002</span>
        </div>
      </div>
    </section>
  );
}
