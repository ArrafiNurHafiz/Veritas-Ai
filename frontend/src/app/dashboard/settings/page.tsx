'use client';

import React from 'react';
import { useApp } from '@/lib/store';
import { DEMO_USERS } from '@/lib/mockData';
import { Building2, Key, Server, Users, ShieldAlert } from 'lucide-react';

export default function SettingsPage() {
  const { currentUser } = useApp();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
          Enterprise Governance
        </span>
        <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
          Organization Settings
        </h1>
        <p className="text-[16px] text-[#777b86]">
          Manage tenant identity, cryptographic signer credentials, and private ledger nodes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Tenant Profile */}
        <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#f2f2f3] flex items-center justify-center text-[#17191c]">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#17191c]">Tenant Organization</h3>
              <p className="text-[12px] text-[#777b86]">Fictional enterprise sandbox configuration</p>
            </div>
          </div>

          <div className="space-y-3 text-[13px]">
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Organization Name:</span>
              <strong className="text-[#17191c]">Nexora Technologies</strong>
            </div>
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Tenant ID:</span>
              <span className="font-mono text-[#17191c]">org_nexora_tech</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Domain Scope:</span>
              <span className="font-mono text-[#17191c]">@nexora.internal</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-[#777b86]">Current Session:</span>
              <span className="font-medium text-[#17191c]">{currentUser.name} ({currentUser.role})</span>
            </div>
          </div>
        </div>

        {/* Cryptographic Key Store */}
        <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#f2f2f3] flex items-center justify-center text-[#17191c]">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#17191c]">Harness Signer Key</h3>
              <p className="text-[12px] text-[#777b86]">Hardware Security Module (HSM) Ed25519 reference</p>
            </div>
          </div>

          <div className="space-y-3 text-[13px]">
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Key Identifier:</span>
              <span className="font-mono text-[#17191c]">harness-ed25519-v1</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Algorithm:</span>
              <span className="font-mono text-[#17191c]">Ed25519 (RFC 8032)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Canonicalization:</span>
              <span className="font-mono text-[#17191c]">RFC 8785 JCS</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-[#777b86]">Storage Location:</span>
              <span className="text-emerald-700 font-medium">Harness Vault (Never in Git)</span>
            </div>
          </div>
        </div>

        {/* Private Ledger Configuration */}
        <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#f2f2f3] flex items-center justify-center text-[#17191c]">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#17191c]">Hyperledger Besu Node</h3>
              <p className="text-[12px] text-[#777b86]">Private permissioned blockchain RPC</p>
            </div>
          </div>

          <div className="space-y-3 text-[13px]">
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">RPC Endpoint:</span>
              <span className="font-mono text-[#17191c]">http://besu.internal:8545</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Chain ID:</span>
              <span className="font-mono text-[#17191c]">1337 (Permissioned)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#ececec]">
              <span className="text-[#777b86]">Consensus:</span>
              <span className="text-[#17191c]">QBFT (Proof-of-Authority)</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-[#777b86]">User Wallets / Gas:</span>
              <span className="text-[#777b86] italic">None (Gas-free private infrastructure)</span>
            </div>
          </div>
        </div>

        {/* Authorized Team Members */}
        <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#f2f2f3] flex items-center justify-center text-[#17191c]">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#17191c]">RBAC Team Members</h3>
              <p className="text-[12px] text-[#777b86]">Demo personas configured for evaluation</p>
            </div>
          </div>

          <div className="space-y-2 text-[13px]">
            {DEMO_USERS.map((u) => (
              <div key={u.id} className="p-2.5 rounded-xl bg-[#fafafb] border border-[#ececec] flex items-center justify-between">
                <div>
                  <span className="font-medium text-[#17191c]">{u.name}</span>
                  <span className="text-[#979799] block text-[11px]">{u.email}</span>
                </div>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-white border border-[#ececec] capitalize">
                  {u.role}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
