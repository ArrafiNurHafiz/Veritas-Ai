'use client';

import React from 'react';
import Link from 'next/link';
import { ShieldCheck } from 'lucide-react';

const productLinks = [
  { label: 'Executive Dashboard', href: '/dashboard' },
  { label: 'Agent Tasks & Proposals', href: '/dashboard/tasks' },
  { label: 'Human-in-the-Loop Approvals', href: '/dashboard/approvals' },
  { label: 'Policy Rules Engine', href: '/dashboard/policies' },
  { label: 'Cryptographic Trust Explorer', href: '/dashboard/trust' },
];

const architectureLinks = [
  { label: 'Deterministic Gate (veritas_harness.py)', href: '/#architecture' },
  { label: 'Ed25519 Receipts Specification', href: '/#features' },
  { label: 'Besu EVM Anchor RPC (Optional)', href: '/#architecture' },
  { label: 'Egress Data Quarantine', href: '/#features' },
  { label: 'FastAPI REST Endpoints (:8002)', href: '/#architecture' },
];

const complianceLinks = [
  { label: 'Zero-Trust Tool Isolation', href: '/#problems' },
  { label: 'Deny-by-Default Policy Model', href: '/#features' },
  { label: 'Mathematical Non-Repudiation', href: '/#interactive' },
  { label: 'Synthetic Demo Isolation (Nexora)', href: '/#quote' },
  { label: 'Immutable Audit Trail', href: '/dashboard/trust' },
];

export default function Footer() {
  return (
    <footer className="border-t border-[#1C1E24] bg-[#07080A] text-[#8F94A0]">
      {/* Top section with columns */}
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
          {/* Brand & mission */}
          <div className="space-y-4 lg:col-span-4">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DA5C2B]/40 bg-[#DA5C2B]/10 text-[#DA5C2B]">
                <ShieldCheck className="h-4 w-4 stroke-[2.2]" />
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-[18px] font-semibold tracking-[-0.03em] text-white">
                  VERITAS
                </span>
                <span className="font-mono text-[9px] font-medium uppercase tracking-[0.18em] text-[#DA5C2B]">
                  AI
                </span>
              </div>
            </Link>

            <p className="max-w-sm text-[13px] leading-relaxed text-[#7D828F]">
              The modern governance & control platform for enterprise autonomous agents. Sub-millisecond deterministic policy evaluation, human sign-off gates, and tamper-proof Ed25519 receipts.
            </p>

            <div className="pt-2">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#232730] bg-[#0E1014] px-3 py-1 font-mono text-[11px] text-[#A6ABB7]">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#22C55E] opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[#22C55E]" />
                </span>
                <span>Harness Gateway: <strong className="text-white">Active (:8002)</strong></span>
              </div>
            </div>

            <div className="pt-2">
              <p className="font-mono text-[10px] uppercase tracking-wider text-[#585D6A]">
                Synthetic Demo Dataset · Nexora Technologies
              </p>
            </div>
          </div>

          {/* Nav columns */}
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3 lg:col-span-8">
            <div>
              <h4 className="text-[12px] font-semibold uppercase tracking-wider text-white">
                Platform
              </h4>
              <ul className="mt-4 space-y-2.5 text-[13px]">
                {productLinks.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="transition-colors hover:text-[#EDEDED]"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-[12px] font-semibold uppercase tracking-wider text-white">
                Architecture
              </h4>
              <ul className="mt-4 space-y-2.5 text-[13px]">
                {architectureLinks.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="transition-colors hover:text-[#EDEDED]"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-[12px] font-semibold uppercase tracking-wider text-white">
                Governance & Trust
              </h4>
              <ul className="mt-4 space-y-2.5 text-[13px]">
                {complianceLinks.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="transition-colors hover:text-[#EDEDED]"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-[#1C1E24] pt-8 text-[12px] sm:flex-row">
          <p className="font-mono text-[#585D6A]">
            © 2026 VERITAS AI Platform. Built with deterministic zero-trust architecture.
          </p>
          <div className="flex items-center gap-6 font-mono text-[11px] text-[#7D828F]">
            <Link href="/#architecture" className="hover:text-white transition-colors">
              SPEC v1.1
            </Link>
            <span>•</span>
            <Link href="/#interactive" className="hover:text-white transition-colors">
              APL ENGINE
            </Link>
            <span>•</span>
            <Link href="/login" className="hover:text-white transition-colors">
              OPERATOR CONSOLE
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
