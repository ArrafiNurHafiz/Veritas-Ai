'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Bot, 
  Send, 
  CheckSquare, 
  Sliders, 
  Activity, 
  ShieldCheck, 
  Settings,
  ArrowUpRight
} from 'lucide-react';
import { useApp } from '@/lib/store';

export default function DashboardSidebar() {
  const pathname = usePathname();
  const { executions } = useApp();

  const pendingApprovalsCount = executions.filter(
    (e) => e.status === 'WAITING_APPROVAL' && e.approval?.status === 'PENDING'
  ).length;

  const navItems = [
    {
      label: 'Overview',
      href: '/dashboard',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      label: 'AI Workforce',
      href: '/dashboard/agents',
      icon: Bot,
      badge: '1 Live',
    },
    {
      label: 'Task Center',
      href: '/dashboard/tasks',
      icon: Send,
      badge: null,
    },
    {
      label: 'Approval Center',
      href: '/dashboard/approvals',
      icon: CheckSquare,
      badge: pendingApprovalsCount > 0 ? String(pendingApprovalsCount) : null,
      highlight: pendingApprovalsCount > 0,
    },
    {
      label: 'Policy Manager',
      href: '/dashboard/policies',
      icon: Sliders,
      badge: null,
    },
    {
      label: 'Execution Monitor',
      href: '/dashboard/executions',
      icon: Activity,
      badge: null,
    },
    {
      label: 'Trust Explorer',
      href: '/dashboard/trust',
      icon: ShieldCheck,
      badge: 'Ledger',
    },
    {
      label: 'Organization Settings',
      href: '/dashboard/settings',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <aside className="w-full md:w-64 md:shrink-0 border-b md:border-b-0 md:border-r border-[#ececec] bg-[#fafafb] flex flex-col justify-between p-4 md:min-h-[calc(100vh-65px)]">
      <div className="space-y-6">
        {/* Brand Home Link */}
        <div className="px-3 pt-2">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-7 h-7 rounded-full bg-[#17191c] flex items-center justify-center text-white">
              <ShieldCheck className="w-4 h-4 stroke-[2]" />
            </div>
            <div className="flex flex-col">
              <span className="font-display text-[18px] text-[#17191c] leading-tight group-hover:opacity-80 transition-opacity">
                VERITAS AI
              </span>
              <span className="text-[10px] text-[#979799] tracking-wider uppercase font-medium">Console v1.1</span>
            </div>
          </Link>
        </div>

        {/* Navigation Section */}
        <nav className="space-y-1">
          <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#979799]">
            Governance Surfaces
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-[14px] font-normal transition-all ${
                  isActive
                    ? 'bg-[#17191c] text-white font-medium shadow-sm'
                    : 'text-[#17191c] hover:bg-[#f2f2f3]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-[#777b86]'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                      isActive
                        ? 'bg-zinc-700 text-white'
                        : item.highlight
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-[#ececec] text-[#777b86]'
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
      <div className="bg-white rounded-2xl p-3.5 border border-[#ececec] space-y-2.5 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#979799] uppercase tracking-wider">Harness Mesh</span>
          <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Synchronized
          </span>
        </div>
        <div className="space-y-1 text-[11px] text-[#777b86]">
          <div className="flex justify-between">
            <span>Policy Engine:</span>
            <span className="font-mono text-[#17191c]">Deny-by-default</span>
          </div>
          <div className="flex justify-between">
            <span>Key Scheme:</span>
            <span className="font-mono text-[#17191c]">Ed25519 (HSM)</span>
          </div>
          <div className="flex justify-between">
            <span>Ledger Anchor:</span>
            <span className="font-mono text-[#17191c]">Local mock anchor</span>
          </div>
        </div>
        <div className="pt-1 border-t border-[#f2f2f3]">
          <Link
            href="/"
            className="text-[11px] text-[#777b86] hover:text-[#17191c] flex items-center justify-between group"
          >
            <span>Return to Public Site</span>
            <ArrowUpRight className="w-3 h-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </Link>
        </div>
      </div>
    </aside>
  );
}
