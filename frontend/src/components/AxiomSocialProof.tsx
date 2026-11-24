'use client';

import React from 'react';
import { motion } from 'motion/react';

const partners = [
  { name: 'Nexora Technologies', desc: 'Enterprise Tenant' },
  { name: 'FastAPI', desc: 'Sub-ms Harness' },
  { name: 'Ed25519', desc: 'Asymmetric Receipts' },
  { name: 'Hyperledger Besu', desc: 'EVM Anchor RPC' },
  { name: 'OpenTelemetry', desc: 'Audit Traces' },
  { name: 'SQLite WAL', desc: 'Deterministic Store' },
];

export default function AxiomSocialProof() {
  return (
    <section id="quote" className="overflow-hidden border-y border-[#1A1C22] bg-[#07080A] py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Quote in Axiom's exact editorial styling with scroll reveal */}
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto max-w-4xl text-center"
        >
          <span className="font-serif text-5xl leading-none text-[#DA5C2B] sm:text-6xl select-none">
            “
          </span>
          <blockquote className="mt-2 text-[20px] font-medium leading-relaxed tracking-[-0.015em] text-[#EDEDED] sm:text-[26px] md:text-[30px]">
            The beautiful thing about Veritas is it just works. No prompt injection bypasses, no hallucinations slipping into wire transfers. Every tool execution is deterministically checked, held when risky, and cryptographically signed.
          </blockquote>
          
          <div className="mt-6 flex flex-col items-center justify-center gap-1 sm:flex-row sm:gap-3">
            <span className="text-[14px] font-semibold text-white">Marcus Vance</span>
            <span className="hidden text-[#454A57] sm:inline">•</span>
            <span className="text-[13px] text-[#8F94A0]">
              Head of Platform Security @ <strong className="text-[#DA5C2B]">Nexora Technologies</strong>
            </span>
          </div>
        </motion.div>

        {/* Ecosystem Logos / Capabilities with Infinite Scrolling Marquee */}
        <div className="mt-16 border-t border-[#16181E] pt-12">
          <p className="text-center font-mono text-[10px] uppercase tracking-[0.2em] text-[#555A67]">
            Trusted security architecture & zero-trust primitives
          </p>
          
          {/* Continuous looping marquee */}
          <div className="relative mt-8 overflow-hidden mask-gradient">
            <div className="animate-axiom-marquee flex gap-4">
              {[...partners, ...partners].map((p, idx) => (
                <div
                  key={`${p.name}-${idx}`}
                  className="group flex w-[200px] shrink-0 flex-col items-center justify-center rounded-lg border border-[#1A1C22] bg-[#0A0C0F] p-4 text-center transition-all hover:border-[#DA5C2B]/40 hover:bg-[#0E1015]"
                >
                  <span className="font-mono text-[12px] font-medium text-[#EDEDED] group-hover:text-white">
                    {p.name}
                  </span>
                  <span className="mt-1 font-mono text-[10px] text-[#555A67]">
                    {p.desc}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
