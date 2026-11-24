'use client';

import React from 'react';
import { useApp } from '@/lib/store';
import { Bot, CheckCircle2, Shield, Wrench, AlertCircle, Layers } from 'lucide-react';

export default function AgentsPage() {
  const { agents } = useApp();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
          Enterprise Workforce
        </span>
        <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
          Registered AI Agents
        </h1>
        <p className="text-[16px] text-[#777b86]">
          Autonomous reasoning units with bounded tool catalogs and zero direct execution privileges.
        </p>
      </div>

      {/* Honest Boundary Notice as per PRD */}
      <div className="p-4 rounded-2xl bg-[#fafafb] border border-[#ececec] flex items-start gap-3 text-[13px] text-[#777b86]">
        <AlertCircle className="w-4 h-4 text-[#17191c] shrink-0 mt-0.5" />
        <div>
          <strong className="text-[#17191c] font-medium">Architectural Isolation Guarantee: </strong>
          Agent planning processes are strictly read-only and generate JSON tool proposals. The Agent service has zero access to tool credentials, zero database write permissions, and zero blockchain keys.
        </div>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {agents.map((agent) => {
          const isOperational = agent.status === 'OPERATIONAL';
          return (
            <div
              key={agent.id}
              className={`rounded-[24px] p-6 border transition-all flex flex-col justify-between space-y-6 ${
                isOperational
                  ? 'bg-white border-[#ececec] shadow-sm'
                  : 'bg-[#fafafb] border-[#ececec]/60 opacity-80'
              }`}
            >
              <div className="space-y-4">
                {/* Top status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${
                      isOperational ? 'bg-[#17191c] text-white' : 'bg-[#e5e5e6] text-[#777b86]'
                    }`}>
                      <Bot className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-display text-[20px] text-[#17191c] leading-tight">
                        {agent.name}
                      </h3>
                      <span className="font-mono text-[11px] text-[#979799]">
                        ID: {agent.id} &bull; v{agent.version}
                      </span>
                    </div>
                  </div>

                  <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${
                    isOperational
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-zinc-100 text-zinc-600 border border-zinc-200'
                  }`}>
                    {agent.status}
                  </span>
                </div>

                <p className="text-[14px] text-[#777b86] leading-relaxed">
                  {agent.description}
                </p>

                {/* Allowed Tools list */}
                <div className="space-y-2">
                  <span className="text-[12px] font-medium text-[#17191c] flex items-center gap-1.5">
                    <Wrench className="w-3.5 h-3.5 text-[#777b86]" />
                    <span>Registered Tool Catalog ({agent.allowedTools.length})</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {agent.allowedTools.map((t) => (
                      <span
                        key={t}
                        className="px-2.5 py-1 rounded-lg bg-[#f2f2f3] text-[#17191c] font-mono text-[11px] border border-[#ececec]"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Bottom statistics & controls */}
              <div className="pt-4 border-t border-[#ececec] flex items-center justify-between text-[12px]">
                {isOperational ? (
                  <>
                    <span className="text-emerald-700 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Live in Harness Policy Loop
                    </span>
                    <span className="text-[#777b86]">
                      {agent.totalExecutions} total tasks executed
                    </span>
                  </>
                ) : (
                  <span className="text-[#979799] italic">
                    Planned in Roadmap &bull; Non-operational in MVP
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
