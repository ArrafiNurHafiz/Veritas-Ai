'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useApp } from '@/lib/store';
import * as api from '@/lib/api';
import { Bot, CheckCircle2, Wrench, AlertCircle, ArrowRight } from 'lucide-react';

export default function AgentsPage() {
  const { agents, currentUser, refreshExecutions, syncError } = useApp();
  const isAdmin = currentUser.role === 'admin';
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleToggleAgent = async (agentId: string, nextEnabled: boolean) => {
    if (!api.IS_ENTERPRISE || !isAdmin) return;
    setTogglingId(agentId);
    setErrorMsg(null);
    try {
      await api.setAgentEnabled(agentId, nextEnabled);
      await refreshExecutions();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to toggle agent status.');
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#6D7344] uppercase tracking-wider">
          Enterprise Workforce
        </span>
        <h1 className="font-display text-[44px] text-[#192319] leading-[1.1] tracking-[-0.66px]">
          Registered AI Agents
        </h1>
        <p className="text-[16px] text-[#2D372D]">
          Autonomous reasoning units with bounded tool catalogs and zero direct execution privileges.
        </p>
      </div>

      {/* Honest Boundary Notice as per PRD */}
      <div className="p-4 rounded-2xl bg-[#F8F8F8] border border-[#DCDCD7] flex items-start gap-3 text-[13px] text-[#2D372D]">
        <AlertCircle className="w-4 h-4 text-[#192319] shrink-0 mt-0.5" />
        <div>
          <strong className="text-[#192319] font-medium">Architectural Isolation Guarantee: </strong>
          Agent planning processes are strictly read-only and generate JSON tool proposals. Each agent is restricted to its declared tool catalog and has zero direct access to tool credentials, database writes, or signing keys.
        </div>
      </div>

      {/* Agents Grid */}
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-[13px] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      )}
      {agents.length === 0 ? (
        <div className="p-10 rounded-[24px] bg-[#F8F8F8] border border-[#DCDCD7] text-center text-[14px] text-[#2D372D] space-y-3">
          {syncError ? (
            <>
              <p className="text-rose-700 font-medium">
                Gagal memuat agent dari Harness Gateway: {syncError}
              </p>
              <p className="text-[12px] text-[#2D372D]">
                Pastikan backend berjalan (./start_local.sh) dan Anda sudah login di /login.
              </p>
              <button
                type="button"
                onClick={() => void refreshExecutions()}
                className="px-4 py-1.5 rounded-full text-[12px] font-medium border border-[#C8C8BE] bg-white text-[#192319] hover:bg-[#F0F0EC] transition-colors"
              >
                Retry Sync
              </button>
            </>
          ) : (
            <span>Loading registered agents from Harness Gateway...</span>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {agents.map((agent) => {
            const isOperational = agent.status === 'OPERATIONAL';
            const isDisabled = agent.status === 'DISABLED';
            const canToggle = api.IS_ENTERPRISE && isAdmin && (isOperational || isDisabled);
            return (
              <div
                key={agent.id}
                className={`rounded-[24px] p-6 border transition-all flex flex-col justify-between space-y-6 ${
                  isOperational
                    ? 'bg-white border-[#DCDCD7] shadow-sm'
                    : 'bg-[#F8F8F8] border-[#DCDCD7]/60 opacity-80'
                }`}
              >
                <div className="space-y-4">
                  {/* Top status */}
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${
                        isOperational ? 'bg-[#192319] text-white' : 'bg-[#DCDCD7] text-[#2D372D]'
                      }`}>
                        <Bot className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="font-display text-[20px] text-[#192319] leading-tight">
                          {agent.name}
                        </h3>
                        <span className="font-mono text-[11px] text-[#6D7344]">
                          ID: {agent.id} &bull; v{agent.version}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${
                        isOperational
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : isDisabled
                            ? 'bg-amber-50 text-amber-800 border border-amber-200'
                            : 'bg-zinc-100 text-zinc-600 border border-zinc-200'
                      }`}>
                        {agent.status}
                      </span>
                      {canToggle && (
                        <button
                          type="button"
                          disabled={togglingId === agent.id}
                          onClick={() => handleToggleAgent(agent.id, !isOperational)}
                          className="px-2.5 py-1 rounded-full text-[11px] font-medium border border-[#C8C8BE] bg-white text-[#192319] hover:bg-[#F0F0EC] disabled:opacity-50 transition-colors"
                        >
                          {togglingId === agent.id
                            ? 'Saving…'
                            : isOperational
                              ? 'Disable'
                              : 'Enable'}
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="text-[14px] text-[#2D372D] leading-relaxed">
                    {agent.description}
                  </p>

                  {/* Task Types */}
                  {agent.taskTypes && agent.taskTypes.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-[#6D7344]">
                        Supported Task Flows
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {agent.taskTypes.map((tt) => (
                          <span
                            key={tt}
                            className="px-2 py-0.5 rounded-md bg-[#F8F8F8] text-[#2D372D] font-mono text-[11px] border border-[#DCDCD7]"
                          >
                            {tt}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Allowed Tools list */}
                  <div className="space-y-2">
                    <span className="text-[12px] font-medium text-[#192319] flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-[#2D372D]" />
                      <span>Bounded Tool Catalog ({agent.allowedTools.length})</span>
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {agent.allowedTools.length === 0 ? (
                        <span className="text-[12px] text-rose-700 italic">
                          All tools currently disabled by tenant administrator
                        </span>
                      ) : (
                        agent.allowedTools.map((t) => (
                          <span
                            key={t}
                            className="px-2.5 py-1 rounded-lg bg-[#F0F0EC] text-[#192319] font-mono text-[11px] border border-[#DCDCD7]"
                          >
                            {t}
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* Bottom statistics & controls */}
                <div className="pt-4 border-t border-[#DCDCD7] flex items-center justify-between gap-3 text-[12px]">
                  {isOperational ? (
                    <>
                      <div className="space-y-0.5">
                        <span className="text-emerald-700 font-medium flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Live in Harness Policy Loop
                        </span>
                        <span className="text-[#2D372D] block">
                          {agent.totalExecutions} tasks executed
                          {agent.blockedCount > 0 ? ` · ${agent.blockedCount} blocked` : ''}
                        </span>
                      </div>
                      <Link
                        href={`/dashboard/tasks?agent=${encodeURIComponent(agent.id)}`}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#192319] text-white font-medium hover:opacity-90 transition-opacity shrink-0"
                      >
                        <span>Dispatch Task</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </>
                  ) : (
                    <span className="text-[#6D7344] italic">
                      {isDisabled
                        ? 'Disabled by tenant administrator'
                        : 'Planned in Roadmap \u2022 Non-operational'}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
