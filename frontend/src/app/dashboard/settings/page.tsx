'use client';

import React, { useEffect, useState } from 'react';
import { useApp } from '@/lib/store';
import { DEMO_USERS } from '@/lib/mockData';
import * as api from '@/lib/api';
import { UserRole } from '@/lib/types';
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Key,
  Plus,
  Server,
  Users,
  Wrench,
} from 'lucide-react';

export default function SettingsPage() {
  const { currentUser, refreshExecutions } = useApp();
  const isAdmin = currentUser.role === 'admin';

  const [users, setUsers] = useState<api.TenantUserView[]>([]);
  const [tools, setTools] = useState<api.ToolView[]>([]);
  const [loading, setLoading] = useState(api.IS_ENTERPRISE);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [newEmail, setNewEmail] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('operator');
  const [newPassword, setNewPassword] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!api.IS_ENTERPRISE) return;
    let active = true;
    Promise.all([
      api.getTools().catch(() => null),
      isAdmin ? api.getUsers().catch(() => null) : Promise.resolve(null),
    ])
      .then(([toolsRes, usersRes]) => {
        if (!active) return;
        if (toolsRes?.tools) setTools(toolsRes.tools);
        if (usersRes?.users) setUsers(usersRes.users);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isAdmin]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;
    setCreating(true);
    setErrorMsg(null);
    setFeedback(null);
    try {
      const created = await api.createUser({
        email: newEmail.trim(),
        display_name: newDisplayName.trim() || undefined,
        role: newRole,
        password: newPassword,
      });
      setUsers((prev) => [...prev, created]);
      setNewEmail('');
      setNewDisplayName('');
      setNewPassword('');
      setFeedback(`User ${created.email} created with role "${created.role}".`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to create user.');
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (userId: string, role: UserRole, status?: 'active' | 'disabled') => {
    if (!isAdmin) return;
    setErrorMsg(null);
    setFeedback(null);
    try {
      const updated = await api.updateUserRole(userId, { role, status });
      setUsers((prev) =>
        prev.map((u) => (u.user_id === userId ? { ...u, role: updated.role, status: updated.status } : u)),
      );
      setFeedback(`Updated user ${userId} to role "${updated.role}" (${updated.status}).`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to update role.');
    }
  };

  const handleToggleTool = async (toolName: string, currentEnabled: boolean) => {
    if (!isAdmin) return;
    setErrorMsg(null);
    setFeedback(null);
    try {
      const updated = await api.setToolEnabled(toolName, !currentEnabled);
      setTools((prev) => prev.map((t) => (t.tool_name === toolName ? updated : t)));
      await refreshExecutions();
      setFeedback(`Tool "${updated.tool_name}" is now ${updated.enabled ? 'ENABLED' : 'DISABLED'}.`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to toggle tool.');
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1.5">
        <span className="text-[12px] font-semibold text-[#6D7344] uppercase tracking-wider">
          Enterprise Governance
        </span>
        <h1 className="font-display text-[44px] text-[#192319] leading-[1.1] tracking-[-0.66px]">
          Organization Settings
        </h1>
        <p className="text-[16px] text-[#2D372D]">
          Manage tenant identity, cryptographic signer credentials, tool registry, and team access.
        </p>
      </div>

      {feedback && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-[13px] flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-[13px] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Tenant Profile */}
        <div className="bg-white rounded-2xl p-6 border border-[#DCDCD7] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F0F0EC] flex items-center justify-center text-[#192319]">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#192319]">Tenant Organization</h3>
              <p className="text-[12px] text-[#2D372D]">
                {api.IS_ENTERPRISE ? 'Production tenant boundary' : 'Fictional enterprise sandbox configuration'}
              </p>
            </div>
          </div>

          <div className="space-y-3 text-[13px]">
            <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
              <span className="text-[#2D372D]">Organization Name:</span>
              <strong className="text-[#192319]">{currentUser.organizationName || currentUser.organizationId}</strong>
            </div>
            <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
              <span className="text-[#2D372D]">Tenant ID:</span>
              <span className="font-mono text-[#192319]">{currentUser.organizationId}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
              <span className="text-[#2D372D]">Authenticated Email:</span>
              <span className="font-mono text-[#192319]">{currentUser.email || 'session-identity'}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-[#2D372D]">Current Session:</span>
              <span className="font-medium text-[#192319]">
                {currentUser.name} ({currentUser.role})
              </span>
            </div>
          </div>
        </div>

        {/* Cryptographic Key Store */}
        <div className="bg-white rounded-2xl p-6 border border-[#DCDCD7] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F0F0EC] flex items-center justify-center text-[#192319]">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#192319]">Harness Signer Key</h3>
              <p className="text-[12px] text-[#2D372D]">Ed25519 receipt signing & canonical verification</p>
            </div>
          </div>

          <div className="space-y-3 text-[13px]">
            <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
              <span className="text-[#2D372D]">Algorithm:</span>
              <span className="font-mono text-[#192319]">Ed25519 (RFC 8032)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
              <span className="text-[#2D372D]">Canonicalization:</span>
              <span className="font-mono text-[#192319]">RFC 8785 JCS</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
              <span className="text-[#2D372D]">Session Backend:</span>
              <span className="font-mono text-[#192319]">
                {api.IS_ENTERPRISE ? 'PostgreSQL + HttpOnly + CSRF' : 'Local Harness Store'}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-[#2D372D]">Storage Location:</span>
              <span className="text-emerald-700 font-medium">Server Env / Vault (Never in Git)</span>
            </div>
          </div>
        </div>

        {/* Tool Registry Controls (Enterprise) or Anchor Status */}
        <div className="bg-white rounded-2xl p-6 border border-[#DCDCD7] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F0F0EC] flex items-center justify-center text-[#192319]">
              {api.IS_ENTERPRISE ? <Wrench className="w-5 h-5" /> : <Server className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#192319]">
                {api.IS_ENTERPRISE ? 'Tenant Tool Registry' : 'Local Mock Anchor'}
              </h3>
              <p className="text-[12px] text-[#2D372D]">
                {api.IS_ENTERPRISE
                  ? 'Server-side allowlisted tools enforced before any agent execution'
                  : 'Digest anchoring simulated in SQLite (no external chain)'}
              </p>
            </div>
          </div>

          {api.IS_ENTERPRISE ? (
            <div className="space-y-2.5 text-[13px]">
              {loading && tools.length === 0 ? (
                <p className="text-[#2D372D]">Loading tool registry...</p>
              ) : tools.length === 0 ? (
                <p className="text-[#2D372D]">No tools registered for this tenant.</p>
              ) : (
                tools.map((t) => (
                  <div
                    key={t.id}
                    className="p-3 rounded-xl bg-[#F8F8F8] border border-[#DCDCD7] flex items-center justify-between"
                  >
                    <div>
                      <span className="font-mono font-medium text-[#192319]">{t.tool_name}</span>
                      <span className="block text-[11px] text-[#2D372D]">
                        Tier: {t.risk_tier} · Schema {t.schema_version}
                      </span>
                    </div>
                    <button
                      type="button"
                      disabled={!isAdmin}
                      onClick={() => handleToggleTool(t.tool_name, t.enabled)}
                      className={`px-3 py-1 rounded-full text-[11px] font-medium border transition-colors disabled:opacity-50 ${
                        t.enabled
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                          : 'bg-zinc-100 text-zinc-600 border-zinc-300 hover:bg-zinc-200'
                      }`}
                    >
                      {t.enabled ? 'ENABLED' : 'DISABLED'}
                    </button>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-3 text-[13px]">
              <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
                <span className="text-[#2D372D]">RPC Endpoint:</span>
                <span className="font-mono text-[#192319]">in-process (SQLite)</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
                <span className="text-[#2D372D]">Chain ID:</span>
                <span className="font-mono text-[#192319]">n/a (mock)</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#DCDCD7]">
                <span className="text-[#2D372D]">Confirmation:</span>
                <span className="text-[#192319]">Admin/internal mock confirm</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-[#2D372D]">User Wallets / Gas:</span>
                <span className="text-[#2D372D] italic">None (Gas-free private infrastructure)</span>
              </div>
            </div>
          )}
        </div>

        {/* Authorized Team Members / Enterprise User Management */}
        <div className="bg-white rounded-2xl p-6 border border-[#DCDCD7] shadow-sm space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F0F0EC] flex items-center justify-center text-[#192319]">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-[20px] text-[#192319]">
                {api.IS_ENTERPRISE ? 'User & Role Management' : 'RBAC Team Members'}
              </h3>
              <p className="text-[12px] text-[#2D372D]">
                {api.IS_ENTERPRISE
                  ? isAdmin
                    ? 'Provision users and assign RBAC roles in PostgreSQL'
                    : 'Only tenant Admins can manage user accounts'
                  : 'Demo personas configured for evaluation'}
              </p>
            </div>
          </div>

          {api.IS_ENTERPRISE ? (
            isAdmin ? (
              <div className="space-y-4">
                <form onSubmit={handleCreateUser} className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 p-3.5 rounded-xl bg-[#F8F8F8] border border-[#DCDCD7]">
                  <input
                    type="email"
                    required
                    placeholder="user@company.com"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className="bg-white border border-[#DCDCD7] rounded-lg px-3 py-2 text-[12px] text-[#192319]"
                  />
                  <input
                    type="text"
                    placeholder="Display name"
                    value={newDisplayName}
                    onChange={(e) => setNewDisplayName(e.target.value)}
                    className="bg-white border border-[#DCDCD7] rounded-lg px-3 py-2 text-[12px] text-[#192319]"
                  />
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as UserRole)}
                    className="bg-white border border-[#DCDCD7] rounded-lg px-3 py-2 text-[12px] text-[#192319]"
                  >
                    <option value="operator">operator</option>
                    <option value="approver">approver</option>
                    <option value="auditor">auditor</option>
                    <option value="admin">admin</option>
                  </select>
                  <input
                    type="password"
                    required
                    minLength={8}
                    placeholder="Password (min 8 chars)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="bg-white border border-[#DCDCD7] rounded-lg px-3 py-2 text-[12px] text-[#192319]"
                  />
                  <button
                    type="submit"
                    disabled={creating}
                    className="sm:col-span-2 pill-button-filled !h-9 !text-[12px] flex items-center justify-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>{creating ? 'Provisioning...' : 'Add Tenant User'}</span>
                  </button>
                </form>

                <div className="space-y-2 text-[13px] max-h-64 overflow-y-auto">
                  {users.length === 0 ? (
                    <p className="text-[12px] text-[#2D372D]">
                      No database users provisioned yet. Add one above.
                    </p>
                  ) : (
                    users.map((u) => (
                      <div
                        key={u.user_id}
                        className="p-2.5 rounded-xl bg-[#F8F8F8] border border-[#DCDCD7] flex items-center justify-between gap-3"
                      >
                        <div className="min-w-0">
                          <span className="font-medium text-[#192319] block truncate">{u.display_name}</span>
                          <span className="text-[#6D7344] block text-[11px] truncate">{u.email}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <select
                            value={u.role}
                            onChange={(e) =>
                              handleRoleChange(u.user_id, e.target.value as UserRole, u.status as 'active' | 'disabled')
                            }
                            className="bg-white border border-[#DCDCD7] rounded-lg px-2 py-1 text-[11px] font-mono text-[#192319]"
                          >
                            <option value="operator">operator</option>
                            <option value="approver">approver</option>
                            <option value="auditor">auditor</option>
                            <option value="admin">admin</option>
                          </select>
                          <button
                            type="button"
                            onClick={() =>
                              handleRoleChange(u.user_id, u.role, u.status === 'active' ? 'disabled' : 'active')
                            }
                            className={`px-2 py-1 rounded text-[10px] font-mono border ${
                              u.status === 'active'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-rose-50 text-rose-700 border-rose-200'
                            }`}
                          >
                            {u.status}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <p className="text-[13px] text-[#2D372D]">
                Signed in as <span className="font-mono">{currentUser.role}</span>. User management is restricted to tenant Admins.
              </p>
            )
          ) : (
            <div className="space-y-2 text-[13px]">
              {DEMO_USERS.map((u) => (
                <div key={u.id} className="p-2.5 rounded-xl bg-[#F8F8F8] border border-[#DCDCD7] flex items-center justify-between">
                  <div>
                    <span className="font-medium text-[#192319]">{u.name}</span>
                    <span className="text-[#6D7344] block text-[11px]">{u.email}</span>
                  </div>
                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-white border border-[#DCDCD7] capitalize">
                    {u.role}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
