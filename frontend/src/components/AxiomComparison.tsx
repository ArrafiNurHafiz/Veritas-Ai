'use client';

import React from 'react';
import { ArrowUpRight, Check, X } from 'lucide-react';
import { motion } from 'motion/react';

const competitors = [
  {
    name: 'Direct LLM Tool Calls',
    subtitle: 'LangChain, AutoGPT, OpenAI Assistants',
    description: 'Models invoke tools directly via SDK functions without external policy enforcement.',
    pros: 'Simple to prototype quickly',
    cons: 'Vulnerable to prompt injections; no mathematical receipts; zero execution boundary',
    veritasAdvantage: 'Veritas isolates tool execution into a separate service (:8002). The LLM only produces proposals, never direct side-effects.',
  },
  {
    name: 'Prompt Guardrails',
    subtitle: 'NeMo Guardrails, LlamaGuard',
    description: 'Secondary LLMs or heuristic regex filters inspecting prompt completions.',
    pros: 'Catches basic vulgarity or off-topic conversational text',
    cons: 'High token latency (+500ms); non-deterministic; jailbreak bypasses still succeed',
    veritasAdvantage: 'Veritas runs sub-millisecond deterministic Python policy rules. No additional model latency, 100% deterministic reproducibility.',
  },
  {
    name: 'Traditional API Gateways',
    subtitle: 'Kong, Apigee, AWS API Gateway',
    description: 'HTTP reverse proxies managing rate limits and OAuth tokens.',
    pros: 'Standard HTTP token rate-limiting and route proxying',
    cons: 'No semantic agent state understanding; no multi-role human sign-off loop; no signed receipts',
    veritasAdvantage: 'Veritas is purpose-built for agent governance: deep parameter schema inspection, multi-role human approvals, and Ed25519 cryptographic receipts.',
  },
];

export default function AxiomComparison() {
  return (
    <section id="compare" className="border-b border-[#1A1C22] bg-[#08090A] py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Heading with scroll reveal */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl"
        >
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#DA5C2B]">
            Architecture Comparison
          </p>
          <h2 className="mt-4 text-[32px] font-medium leading-[1.1] tracking-[-0.03em] text-white sm:text-[44px]">
            Compare Veritas with <br />
            <span className="text-[#8F94A0]">alternative approaches.</span>
          </h2>
          <p className="mt-5 text-[16px] leading-relaxed text-[#8F94A0]">
            Why runtime interception beats prompt-based self-governance and generic API reverse proxies.
          </p>
        </motion.div>

        {/* 3 Column Cards with staggered scroll reveal */}
        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
          {competitors.map((c, idx) => (
            <motion.div
              key={c.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.65, delay: idx * 0.15, ease: [0.16, 1, 0.3, 1] }}
              className="group flex flex-col justify-between rounded-xl border border-[#1E2129] bg-[#0C0D11] p-7 transition-all duration-300 hover:border-[#DA5C2B]/40 hover:bg-[#0F1116] hover:-translate-y-1"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-[17px] font-semibold text-white group-hover:text-[#DA5C2B] transition-colors">
                      {c.name}
                    </h3>
                    <p className="mt-1 font-mono text-[11px] text-[#7A7F8E]">
                      {c.subtitle}
                    </p>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#5A606E] opacity-0 transition-opacity group-hover:opacity-100" />
                </div>

                <p className="mt-4 text-[13px] leading-relaxed text-[#8F94A0]">
                  {c.description}
                </p>

                <div className="mt-6 space-y-2 border-t border-[#1A1C22] pt-4 font-mono text-[11.5px]">
                  <div className="flex items-start gap-2 text-[#EF4444]">
                    <X className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                    <span className="text-[11px] text-[#8F94A0]">{c.cons}</span>
                  </div>
                </div>
              </div>

              <div className="mt-8 rounded-lg border border-[#1E2129] bg-[#07080A] p-3.5 group-hover:border-[#2C313E] transition-colors">
                <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase font-bold text-[#DA5C2B]">
                  <Check className="h-3 w-3 stroke-[3]" />
                  <span>The Veritas Advantage</span>
                </div>
                <p className="mt-2 text-[12px] leading-relaxed text-[#A6ABB7]">
                  {c.veritasAdvantage}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
