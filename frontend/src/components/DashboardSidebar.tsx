'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { motion } from 'motion/react';
import {
  LayoutDashboard,
  Bot,
  Send,
  CheckSquare,
  Sliders,
  Activity,
  ShieldCheck,
  Settings,
  ArrowUpRight,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { useApp } from '@/lib/store';
import { IS_ENTERPRISE } from '@/lib/api';

export default function DashboardSidebar() {
  const pathname = usePathname();
  const { executions, agents } = useApp();
  const [collapsed, setCollapsed] = useState(false);

  const pendingApprovalsCount = executions.filter(
    (e) => e.status === 'WAITING_APPROVAL' && e.approval?.status === 'PENDING'
  ).length;
  const liveAgentsCount = agents.filter((a) => a.status === 'OPERATIONAL').length;

  const navItems = [
    { label: 'Overview', href: '/dashboard', icon: LayoutDashboard, badge: null },
    {
      label: 'AI Workforce',
      href: '/dashboard/agents',
      icon: Bot,
      badge: liveAgentsCount > 0 ? `${liveAgentsCount} Live` : null,
    },
    { label: 'Task Center', href: '/dashboard/tasks', icon: Send, badge: null },
    {
      label: 'Approval Center',
      href: '/dashboard/approvals',
      icon: CheckSquare,
      badge: pendingApprovalsCount > 0 ? String(pendingApprovalsCount) : null,
      highlight: pendingApprovalsCount > 0,
    },
    { label: 'Policy Manager', href: '/dashboard/policies', icon: Sliders, badge: null },
    { label: 'Execution Monitor', href: '/dashboard/executions', icon: Activity, badge: null },
    { label: 'Trust Explorer', href: '/dashboard/trust', icon: ShieldCheck, badge: 'Ledger' },
    { label: 'Organization Settings', href: '/dashboard/settings', icon: Settings, badge: null },
  ];

  return (
    <aside
      className={`w-full md:shrink-0 border-b md:border-b-0 md:border-r border-[#DCDCD7] bg-[#F8F8F8] flex flex-col justify-between p-3.5 md:h-full md:overflow-y-auto transition-all duration-200 ${
        collapsed ? 'md:w-[78px]' : 'md:w-68'
      }`}
    >
      <div className="space-y-5">
        {/* Brand + Collapse Toggle */}
        <div
          className={`flex items-center pt-1 ${
            collapsed ? 'justify-center' : 'justify-between px-1.5 gap-2'
          }`}
        >
          {!collapsed && (
            <Link href="/" className="inline-flex items-center group min-w-0">
              <Image
                src="/veritas-logo.png"
                alt="VERITAS — Control Before Action"
                width={2172}
                height={724}
                priority
                className="h-12 w-auto object-contain group-hover:opacity-85 transition-opacity"
              />
            </Link>
          )}

          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            title={collapsed ? 'Expand sidebar' : 'Hide sidebar labels'}
            aria-label={collapsed ? 'Expand sidebar' : 'Hide sidebar labels'}
            className="hidden md:inline-flex items-center justify-center w-9 h-9 rounded-xl border border-[#DCDCD7] bg-white text-[#192319] hover:border-[#192319] hover:bg-[#F0F0EC] transition-colors shrink-0"
          >
            {collapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Section */}
        <nav className="space-y-1">
          {!collapsed && (
            <div className="px-3 py-1.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[#6D7344]">
              Governance Surfaces
            </div>
          )}
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? item.label : undefined}
                aria-label={item.label}
                className={`relative flex items-center rounded-xl text-[13.5px] transition-colors ${
                  collapsed ? 'justify-center px-2.5 py-2.5' : 'justify-between px-3.5 py-2.5'
                } ${
                  isActive
                    ? 'text-[#F0F0EC] font-semibold'
                    : 'text-[#192319] hover:bg-[#F0F0EC]'
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="sauce-sidebar-active"
                    transition={{ type: 'spring', stiffness: 360, damping: 32 }}
                    className="absolute inset-0 rounded-xl bg-[#192319] shadow-sm"
                  />
                )}
                <div className="relative z-10 flex items-center gap-3">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[#ABE082]' : 'text-[#2D372D]'}`} />
                  {!collapsed && <span>{item.label}</span>}
                </div>
                {collapsed && item.highlight && (
                  <span
                    aria-hidden="true"
                    className="absolute top-1.5 right-1.5 z-10 w-2 h-2 rounded-full bg-[#F1BE23]"
                  />
                )}
                {!collapsed && item.badge && (
                  <span
                    className={`relative z-10 text-[10.5px] px-2 py-0.5 rounded-full font-mono font-semibold ${
                      isActive
                        ? 'bg-[#043423] text-[#ABE082] border border-[#3C483C]'
                        : item.highlight
                          ? 'bg-[#F1BE23] text-[#192319]'
                          : 'bg-[#F0F0EC] text-[#2D372D] border border-[#DCDCD7]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom Service Mesh Status Card */}
      {collapsed ? (
        <Link
          href="/dashboard/trust"
          title="Harness Mesh: Synchronized — Open Trust Explorer"
          className="hidden md:flex mt-6 mx-auto w-10 h-10 rounded-xl bg-[#192319] text-[#ABE082] border border-[#2D372D] items-center justify-center hover:bg-[#043423] transition-colors"
        >
          <span className="w-2.5 h-2.5 rounded-full bg-[#ABE082] animate-pulse" />
        </Link>
      ) : (
        <div className="mt-6 bg-[#192319] text-[#F0F0EC] rounded-2xl p-4 border border-[#2D372D] space-y-2.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-semibold text-[#ABAD6C] uppercase tracking-[0.14em]">
              Harness Mesh
            </span>
            <span className="text-[11px] text-[#ABE082] font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ABE082] animate-pulse" />
              Synchronized
            </span>
          </div>
          <div className="space-y-1.5 text-[11px] text-[#C8C8BE]">
            <div className="flex justify-between">
              <span>Policy Engine:</span>
              <span className="font-mono text-[#F0F0EC]">Deny-by-default</span>
            </div>
            <div className="flex justify-between">
              <span>Key Scheme:</span>
              <span className="font-mono text-[#F0F0EC]">Ed25519</span>
            </div>
            <div className="flex justify-between">
              <span>Ledger Anchor:</span>
              <span className="font-mono text-[#ABE082]">
                {IS_ENTERPRISE ? 'PostgreSQL + Outbox' : 'Local mock anchor'}
              </span>
            </div>
          </div>
          <div className="pt-2 border-t border-[#2D372D]">
            <Link
              href="/dashboard/trust"
              className="text-[11.5px] text-[#ABE082] font-medium flex items-center justify-between hover:underline"
            >
              <span>Open Trust Explorer</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}
    </aside>
  );
}
