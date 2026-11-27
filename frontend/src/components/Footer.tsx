'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowUpRight } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-[#192319] text-[#F0F0EC] border-t border-[#2D372D]">
      <div className="max-w-[1280px] mx-auto px-5 sm:px-8 py-14 sm:py-16">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 pb-12 border-b border-[#2D372D]">
          <div className="md:col-span-5 space-y-4">
            <Link
              href="/"
              className="inline-flex items-center rounded-2xl bg-[#F0F0EC] px-4 py-2.5"
            >
              <Image
                src="/veritas-logo.png"
                alt="VERITAS — Control Before Action"
                width={2172}
                height={724}
                className="h-14 w-auto object-contain"
              />
            </Link>
            <p className="text-[14px] leading-relaxed text-[#C8C8BE] max-w-sm">
              Deterministic execution control, human separation-of-duties, and Ed25519
              cryptographic receipts for autonomous enterprise AI agents.
            </p>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#043423] border border-[#3C483C] font-mono text-[11px] text-[#ABE082]">
              <span className="w-2 h-2 rounded-full bg-[#ABE082] animate-pulse" />
              <span>Control Before Action • Zero Direct Agent Privileges</span>
            </div>
          </div>

          <div className="md:col-span-2 space-y-3">
            <h4 className="font-mono text-[11px] uppercase tracking-[0.16em] text-[#ABAD6C]">
              Platform
            </h4>
            <ul className="space-y-2.5 text-[13.5px] text-[#DCDCD7]">
              <li><Link href="#outcomes" className="hover:text-[#ABE082] transition-colors">Strategic Outcomes</Link></li>
              <li><Link href="#agents" className="hover:text-[#ABE082] transition-colors">Bounded Agents</Link></li>
              <li><Link href="#playground" className="hover:text-[#ABE082] transition-colors">Policy Playground</Link></li>
              <li><Link href="#security" className="hover:text-[#ABE082] transition-colors">Security &amp; FAQ</Link></li>
            </ul>
          </div>

          <div className="md:col-span-3 space-y-3">
            <h4 className="font-mono text-[11px] uppercase tracking-[0.16em] text-[#ABAD6C]">
              Governance Console
            </h4>
            <ul className="space-y-2.5 text-[13.5px] text-[#DCDCD7]">
              <li><Link href="/dashboard" className="hover:text-[#ABE082] transition-colors">Overview</Link></li>
              <li><Link href="/dashboard/tasks" className="hover:text-[#ABE082] transition-colors">Multi-Agent Task Center</Link></li>
              <li><Link href="/dashboard/approvals" className="hover:text-[#ABE082] transition-colors">Approval Center (SoD)</Link></li>
              <li><Link href="/dashboard/trust" className="hover:text-[#ABE082] transition-colors">Public Trust Explorer</Link></li>
            </ul>
          </div>

          <div className="md:col-span-2 space-y-3">
            <h4 className="font-mono text-[11px] uppercase tracking-[0.16em] text-[#ABAD6C]">
              Access
            </h4>
            <ul className="space-y-2.5 text-[13.5px] text-[#DCDCD7]">
              <li>
                <Link href="/login" className="inline-flex items-center gap-1 hover:text-[#ABE082] transition-colors">
                  <span>Console Sign In</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </li>
              <li>
                <Link href="/dashboard/policies" className="hover:text-[#ABE082] transition-colors">
                  Policy Rules
                </Link>
              </li>
              <li>
                <Link href="/dashboard/agents" className="hover:text-[#ABE082] transition-colors">
                  Agent Catalog
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[12px] text-[#C8C8BE]">
          <p>© 2026 VERITAS AI. Built for deterministic enterprise AI governance.</p>
          <p className="font-mono text-[11px] text-[#ABAD6C]">
            Ed25519 • RFC 8785 JCS • PostgreSQL 16 Append-Only Audit
          </p>
        </div>
      </div>
    </footer>
  );
}
