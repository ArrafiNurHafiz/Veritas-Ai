'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'motion/react';

export default function AxiomCTA() {
  return (
    <section className="relative overflow-hidden bg-[#07080A] py-28 sm:py-36 axiom-grid-bg">
      {/* Radial warm glow */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 top-1/4 axiom-hero-glow"
        aria-hidden="true"
      />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-60px' }}
        transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1] }}
        className="relative mx-auto max-w-5xl px-4 text-center sm:px-6 lg:px-8"
      >
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
          Deterministic Agent Governance
        </span>

        <h2 className="mt-5 text-[38px] font-medium leading-[1.08] tracking-[-0.03em] text-white sm:text-[54px] md:text-[64px]">
          Keep every action safe. <br />
          <span className="text-[#DA5C2B]">Verify every receipt.</span>
        </h2>

        <p className="mx-auto mt-6 max-w-2xl text-[16px] leading-relaxed text-[#8F94A0] sm:text-[18px]">
          Deploy zero-trust execution boundaries for your autonomous agents today. Deterministic policy gating, human sign-off escalation, and asymmetric cryptographic evidence.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="group inline-flex h-11 items-center gap-2 rounded-md bg-[#DA5C2B] px-6 text-[14px] font-medium text-white transition-all hover:bg-[#EB6733] hover:shadow-[0_0_25px_rgba(218,92,43,0.4)] active:scale-[0.98]"
          >
            <span>Open the demo console</span>
            <span aria-hidden="true" className="axiom-btn-arrow font-mono text-[15px]">
              <span className="arrow-primary">→</span>
              <span className="arrow-secondary">→</span>
            </span>
          </Link>

          <Link
            href="/#architecture"
            className="inline-flex h-11 items-center rounded-md border border-[#262A34] bg-[#0E1015] px-5 text-[14px] font-medium text-[#EDEDED] transition-colors hover:border-[#3D4252] hover:bg-[#14161E]"
          >
            Read specification
          </Link>
        </div>

        <div className="mt-12 flex items-center justify-center gap-6 font-mono text-[11px] text-[#555A67]">
          <span>FastAPI :8002</span>
          <span>•</span>
          <span>Ed25519 Receipts</span>
          <span>•</span>
          <span>Hyperledger Besu EVM</span>
        </div>
      </motion.div>
    </section>
  );
}
