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
  CheckCircle2,
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
    <header className="sticky top-0 z-40 bg-[#F8F8F8]/95 backdrop-blur-md border-b border-[#DCDCD7]">
      {IS_ENTERPRISE ? (
        <div className="bg-[#192319] text-[#DCDCD7] px-6 py-1.5 flex items-center gap-2 text-[12px]">
          <span className="w-2 h-2 rounded-full bg-[#ABE082] animate-pulse" />
          <span className="font-semibold text-[#ABE082]">Enterprise session</span>
          <span className="text-[#6D7344]">|</span>
          <span>Roles and tenant come from your identity provider</span>
        </div>
      ) : (
        <div className="bg-[#192319] text-[#DCDCD7] px-6 py-1.5 flex items-center justify-between text-[12px]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#ABE082] animate-pulse" />
            <span className="font-semibold text-[#ABE082]">Tenant: Nexora Technologies</span>
            <span className="text-[#6D7344]">|</span>
            <span>Enterprise AI Governance Sandbox (No real funds or tokens)</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[#C8C8BE] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ABE082]" />
              Local mock anchor [Active]
            </span>
            <button
              onClick={() => void resetToDefault()}
              title="Reset demo data to initial state"
              className="hover:text-[#ABE082] flex items-center gap-1 text-[11px] underline underline-offset-2"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Demo State
            </button>
          </div>
        </div>
      )}

      {IS_ENTERPRISE && syncError && (
        <div
          role="alert"
          className="border-b border-[#F55524]/40 bg-[#F55524]/10 px-6 py-2 text-[12px] text-[#961001] font-medium"
        >
          Backend sync problem: {syncError}. Demo data will not be shown.
        </div>
      )}

      {/* Main App Header */}
      <div className="px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-[#F0F0EC] border border-[#DCDCD7]">
            <Building2 className="w-4 h-4 text-[#192319]" />
            <span className="text-[13px] font-semibold text-[#192319]">
              {IS_ENTERPRISE
                ? currentUser.organizationName || currentUser.organizationId || 'Enterprise Tenant'
                : 'Nexora Technologies'}
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded-md bg-white text-[#2D372D] font-mono border border-[#DCDCD7]">
              {IS_ENTERPRISE ? currentUser.organizationId || 'default' : 'ORG-NX88'}
            </span>
          </div>
          <span className="text-[13px] text-[#2D372D] hidden md:inline">
            Project:{' '}
            <strong className="text-[#192319] font-semibold">
              {IS_ENTERPRISE ? 'Multi-Agent Governance' : 'Core Procurement & ERP'}
            </strong>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/approvals"
            className={`relative flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[13px] font-medium transition-colors border ${
              pendingApprovalsCount > 0
                ? 'bg-[#F1E082]/50 text-[#192319] border-[#F1BE23] hover:bg-[#F1E082]'
                : 'bg-[#F0F0EC] text-[#2D372D] border-[#DCDCD7] hover:border-[#192319]'
            }`}
          >
            <Bell className="w-3.5 h-3.5" />
            <span>Approvals</span>
            {pendingApprovalsCount > 0 && (
              <span className="w-5 h-5 rounded-full bg-[#192319] text-[#ABE082] text-[11px] font-bold flex items-center justify-center">
                {pendingApprovalsCount}
              </span>
            )}
          </Link>

          {!IS_ENTERPRISE && (
            <div className="relative group">
              <button className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#192319] hover:bg-[#F0F0EC] transition-colors text-[13px]">
                <span className="w-2 h-2 rounded-full bg-[#ABE082] border border-[#192319]" />
                <span className="text-[#2D372D]">Role:</span>
                <span className="font-semibold text-[#192319] capitalize">{currentUser.role}</span>
                <span className="hidden xl:inline font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#F0F0EC] text-[#2D372D]">
                  tok-{currentUser.role}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-[#2D372D] group-hover:rotate-180 transition-transform" />
              </button>

              <div className="absolute right-0 mt-2 w-72 bg-[#F8F8F8] rounded-2xl shadow-xl border border-[#DCDCD7] p-2 hidden group-hover:block z-50">
                <div className="px-3 py-2 border-b border-[#DCDCD7] mb-1">
                  <p className="font-mono text-[10px] font-semibold tracking-wider text-[#6D7344] uppercase">
                    Switch Demo Role
                  </p>
                  <p className="text-[12px] text-[#2D372D]">
                    Active Bearer header switches automatically
                  </p>
                </div>
                <div className="space-y-1">
                  {roles.map((r) => (
                    <button
                      key={r.role}
                      onClick={() => setUserRole(r.role)}
                      className={`w-full text-left px-3 py-2 rounded-xl text-[13px] transition-all flex flex-col ${
                        currentUser.role === r.role
                          ? 'bg-[#192319] text-[#F0F0EC]'
                          : 'hover:bg-[#F0F0EC] text-[#192319]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{r.label}</span>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                              currentUser.role === r.role
                                ? 'bg-[#043423] text-[#ABE082]'
                                : 'bg-[#DCDCD7] text-[#192319]'
                            }`}
                          >
                            tok-{r.role}
                          </span>
                          {currentUser.role === r.role && <CheckCircle2 className="w-3.5 h-3.5 text-[#ABE082]" />}
                        </div>
                      </div>
                      <span className={`text-[11px] ${currentUser.role === r.role ? 'text-[#C8C8BE]' : 'text-[#2D372D]'}`}>
                        {r.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="w-9 h-9 rounded-full bg-[#192319] text-[#ABE082] border border-[#3C483C] flex items-center justify-center font-semibold text-[12px]">
            {currentUser.avatar}
          </div>
        </div>
      </div>
    </header>
  );
}
