'use client';

import React from 'react';
import Link from 'next/link';
import { useApp } from '@/lib/store';
import { IS_ENTERPRISE } from '@/lib/api';
import { UserRole } from '@/lib/types';
import { 
  Building2, 
  ChevronDown, 
  RotateCcw, 
  Bell, 
  CheckCircle2 
} from 'lucide-react';

export default function DashboardHeader() {
  const { currentUser, setUserRole, executions, resetToDefault, syncError } = useApp();

  const pendingApprovalsCount = executions.filter(
    (e) => e.status === 'WAITING_APPROVAL' && e.approval?.status === 'PENDING'
  ).length;

  const roles: { role: UserRole; label: string; desc: string }[] = [
    { role: 'admin', label: 'Admin (Alexa Chen)', desc: 'Full tenant authority & policy control' },
    { role: 'approver', label: 'Approver (Sarah Jenkins)', desc: 'Authorized to approve invoices > Rp 5M' },
    { role: 'operator', label: 'Operator (Marcus Vance)', desc: 'Submits invoice tasks & monitors runs' },
    { role: 'auditor', label: 'Auditor (Dr. Rachel Kim)', desc: 'Verifies receipts & local mock anchors' },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-[#ececec]">
      {IS_ENTERPRISE ? (
        <div className="bg-[#fafafb] border-b border-[#ececec] px-6 py-1.5 flex items-center gap-2 text-[12px] text-[#777b86]">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span className="font-medium text-[#17191c]">Enterprise session</span>
          <span className="text-[#979799]">|</span>
          <span>Roles and tenant come from your identity provider</span>
        </div>
      ) : (
        /* Demo Sandbox Top Banner */
        <div className="bg-[#fafafb] border-b border-[#ececec] px-6 py-1.5 flex items-center justify-between text-[12px] text-[#777b86]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-medium text-[#17191c]">Tenant: Nexora Technologies</span>
            <span className="text-[#979799]">|</span>
            <span>Enterprise AI Governance Sandbox (No real funds or tokens)</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[#777b86] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#17191c]"></span>
              Local mock anchor [Active]
            </span>
            <button
              onClick={() => void resetToDefault()}
              title="Reset demo data to initial state"
              className="hover:text-[#17191c] flex items-center gap-1 text-[11px] underline underline-offset-2"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Demo State
            </button>
          </div>
        </div>
      )}

      {IS_ENTERPRISE && syncError && (
        <div role="alert" className="border-b border-rose-200 bg-rose-50 px-6 py-2 text-[12px] text-rose-800">
          Backend sync problem: {syncError}. Demo data will not be shown.
        </div>
      )}

      {/* Main App Header */}
      <div className="px-6 h-16 flex items-center justify-between">
        {/* Left: Organization context */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-[#f2f2f3] border border-[#e5e5e6]">
            <Building2 className="w-4 h-4 text-[#17191c]" />
            <span className="text-[13px] font-medium text-[#17191c]">Nexora Technologies</span>
            <span className="text-[11px] px-1.5 py-0.5 rounded bg-white text-[#777b86] font-mono border border-[#ececec]">
              ORG-NX88
            </span>
          </div>
          <span className="text-[13px] text-[#777b86] hidden md:inline">
            Project: <strong className="text-[#17191c] font-medium">Core Procurement & ERP</strong>
          </span>
        </div>

        {/* Right: Role Switcher & Notifications */}
        <div className="flex items-center gap-3">
          {/* Pending Approval Badge Link */}
          <Link
            href="/dashboard/approvals"
            className={`relative flex items-center gap-2 px-3 py-1.5 rounded-full text-[13px] transition-colors border ${
              pendingApprovalsCount > 0
                ? 'bg-amber-50 text-amber-900 border-amber-200 hover:bg-amber-100'
                : 'bg-[#f2f2f3] text-[#777b86] border-transparent hover:bg-[#e8e8e9]'
            }`}
          >
            <Bell className="w-3.5 h-3.5" />
            <span>Approvals</span>
            {pendingApprovalsCount > 0 && (
              <span className="w-5 h-5 rounded-full bg-amber-500 text-white text-[11px] font-medium flex items-center justify-center">
                {pendingApprovalsCount}
              </span>
            )}
          </Link>

          {/* Role comes from the IdP in enterprise: no demo switcher or token pill. */}
          {!IS_ENTERPRISE && (
          <div className="relative group">
            <button className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#17191c] hover:bg-[#f2f2f3] transition-colors text-[13px]">
              <span className="w-2 h-2 rounded-full bg-[#17191c]"></span>
              <span className="text-[#777b86]">Role:</span>
              <span className="font-medium text-[#17191c] capitalize">{currentUser.role}</span>
              <span className="hidden xl:inline font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#f2f2f3] text-[#777b86]">
                tok-{currentUser.role}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-[#777b86] group-hover:rotate-180 transition-transform" />
            </button>

            {/* Dropdown Menu */}
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-2xl shadow-xl border border-[#ececec] p-2 hidden group-hover:block z-50 animate-in fade-in slide-in-from-top-1 duration-150">
              <div className="px-3 py-2 border-b border-[#f2f2f3] mb-1">
                <p className="text-[11px] font-semibold tracking-wider text-[#979799] uppercase">Switch Demo Role</p>
                <p className="text-[12px] text-[#777b86]">Active Bearer header switches automatically</p>
              </div>
              <div className="space-y-1">
                {roles.map((r) => (
                  <button
                    key={r.role}
                    onClick={() => setUserRole(r.role)}
                    className={`w-full text-left px-3 py-2 rounded-xl text-[13px] transition-all flex flex-col ${
                      currentUser.role === r.role
                        ? 'bg-[#17191c] text-white'
                        : 'hover:bg-[#f2f2f3] text-[#17191c]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{r.label}</span>
                      <div className="flex items-center gap-1.5">
                        <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                          currentUser.role === r.role ? 'bg-white/20 text-white' : 'bg-[#e5e5e6] text-[#777b86]'
                        }`}>
                          tok-{r.role}
                        </span>
                        {currentUser.role === r.role && <CheckCircle2 className="w-3.5 h-3.5" />}
                      </div>
                    </div>
                    <span className={`text-[11px] ${currentUser.role === r.role ? 'text-zinc-300' : 'text-[#777b86]'}`}>
                      {r.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          )}

          {/* User Avatar */}
          <div className="w-8 h-8 rounded-full bg-[#17191c] text-white flex items-center justify-center font-medium text-[12px]">
            {currentUser.avatar}
          </div>
        </div>
      </div>
    </header>
  );
}
