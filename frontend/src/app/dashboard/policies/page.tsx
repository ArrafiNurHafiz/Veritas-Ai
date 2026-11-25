'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/store';
import { IS_ENTERPRISE } from '@/lib/api';
import { 
  ShieldCheck, 
  Save, 
  Plus, 
  Trash2, 
  AlertCircle, 
  Check, 
  Lock
} from 'lucide-react';

export default function PolicyManagerPage() {
  const { policy, updatePolicy, currentUser } = useApp();

  const [thresholdOverride, setThresholdOverride] = useState<{ key: string; value: number } | null>(null);
  const [vendorOverride, setVendorOverride] = useState<{ key: string; value: string[] } | null>(null);
  const policyKey = `${policy.version}:${policy.policyDigest}`;
  const threshold = thresholdOverride?.key === policyKey ? thresholdOverride.value : policy.maxAutoAmountIdr;
  const vendorList = vendorOverride?.key === policyKey ? vendorOverride.value : policy.allowedVendors;
  const setThreshold = (value: number) => setThresholdOverride({ key: policyKey, value });
  const setVendorList = (value: string[]) => setVendorOverride({ key: policyKey, value });

  const [newVendor, setNewVendor] = useState('');
  const defaultAction = policy.defaultAction;
  const [saved, setSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isAdmin = currentUser.role === 'admin';

  const handleAddVendor = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;
    if (newVendor.trim() && !vendorList.includes(newVendor.trim())) {
      setVendorList([...vendorList, newVendor.trim()]);
      setNewVendor('');
    }
  };

  const handleRemoveVendor = (v: string) => {
    if (!isAdmin) return;
    setVendorList(vendorList.filter((item) => item !== v));
  };

  const handleSave = async () => {
    if (!isAdmin) {
      setErrorMsg(`Role "${currentUser.role}" has read-only access. Switch to Admin (Alexa Chen) to publish policy changes.`);
      return;
    }
    setErrorMsg(null);
    setIsSaving(true);
    try {
      await updatePolicy({
        maxAutoAmountIdr: Number(threshold),
        allowedVendors: vendorList,
        defaultAction: defaultAction,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update policy';
      setErrorMsg(msg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1.5">
          <span className="text-[12px] font-semibold text-[#979799] uppercase tracking-wider">
            Deterministic Engine
          </span>
          <h1 className="font-display text-[44px] text-[#17191c] leading-[1.1] tracking-[-0.66px]">
            Policy Rule Manager
          </h1>
          <p className="text-[16px] text-[#777b86]">
            Configure deterministic constraints enforced by the Harness prior to any tool execution.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={!isAdmin || isSaving}
          className="pill-button-filled !h-11 !px-6 !text-[14px] flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saved ? <Check className="w-4 h-4 text-emerald-400" /> : <Save className="w-4 h-4" />}
          <span>
            {!isAdmin
              ? `Read-Only (${currentUser.role})`
              : isSaving
              ? 'Publishing...'
              : saved
              ? `Policy Saved (v${policy.version})`
              : 'Publish Policy Changes'}
          </span>
        </button>
      </div>

      {/* Role Authorization Alert */}
      {!isAdmin ? (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start justify-between gap-4 text-[13px] text-amber-900">
          <div className="flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Governance Scope Notice: </strong>
              You are viewing policies as <span className="font-mono underline">{currentUser.name} ({currentUser.role})</span>. Deterministic policy mutation is restricted to <span className="font-mono font-medium">admin</span>.
            </div>
          </div>
          <span className="text-[12px] text-amber-800 shrink-0">
            {IS_ENTERPRISE ? '(Requires Admin role)' : '(Switch to Alexa Chen - Admin via top bar)'}
          </span>
        </div>
      ) : (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-between text-[13px] text-emerald-900">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Policy Authority Active: <strong>{currentUser.name}</strong> ({currentUser.role}). Changes update the deterministic gateway rules.</span>
          </div>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
            Bearer tok-admin
          </span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-[13px] flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Active Version Info Card */}
      <div className="p-4 rounded-2xl bg-[#fafafb] border border-[#ececec] flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-[13px]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#17191c] text-white flex items-center justify-center font-mono text-[12px]">
            v{policy.version}
          </div>
          <div>
            <span className="font-medium text-[#17191c]">{policy.name}</span>
            <span className="text-[#979799] block font-mono text-[11px]">
              SHA-256 Digest: {policy.policyDigest.substring(0, 32)}...
            </span>
          </div>
        </div>
        <span className="text-[#777b86] text-[12px]">
          Last Updated: {new Date(policy.updatedAt).toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Core Limits */}
        <div className="space-y-6">
          {/* Automatic Approval Threshold */}
          <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-4">
            <div className="space-y-1">
              <h3 className="font-display text-[20px] text-[#17191c]">
                Auto-Approval Threshold
              </h3>
              <p className="text-[13px] text-[#777b86]">
                Tool executions with amount &le; this limit run automatically. Above this triggers human sign-off.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-[13px] font-medium text-[#17191c]">
                Threshold Amount (IDR)
              </label>
              <div className="relative">
                <input
                  type="number"
                  disabled={!isAdmin}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-4 py-3 text-[16px] font-mono text-[#17191c] focus:outline-none focus:border-[#17191c] disabled:opacity-60 disabled:cursor-not-allowed"
                />
                <span className="absolute right-4 top-3.5 text-[13px] text-[#979799]">
                  IDR
                </span>
              </div>
              <p className="text-[12px] text-[#777b86]">
                Currently: <strong>Rp {Number(threshold).toLocaleString()}</strong>
              </p>
            </div>
          </div>

          {/* Default Gateway Action */}
          <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-4">
            <div className="space-y-1">
              <h3 className="font-display text-[20px] text-[#17191c]">
                Default Gateway Posture
              </h3>
              <p className="text-[13px] text-[#777b86]">
                Enforce security baseline when unmapped tools or unspecified edge conditions arise.
              </p>
            </div>

            <div className="space-y-2">
              <div className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-emerald-950 text-[13px]">DENY BY DEFAULT (Recommended)</span>
                  <p className="text-[12px] text-emerald-800">
                    Any tool proposal not strictly registered in the agent schema is rejected immediately.
                  </p>
                </div>
                <span className="w-3 h-3 rounded-full bg-emerald-600"></span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Whitelisted Vendors */}
        <div className="bg-white rounded-2xl p-6 border border-[#ececec] shadow-sm space-y-5">
          <div className="space-y-1">
            <h3 className="font-display text-[20px] text-[#17191c]">
              Approved Vendor Allowlist ({vendorList.length})
            </h3>
            <p className="text-[13px] text-[#777b86]">
              Autonomous agents can only issue payment proposals for vendors enrolled in this list.
            </p>
          </div>

          <form onSubmit={handleAddVendor} className="flex gap-2">
            <input
              type="text"
              disabled={!isAdmin}
              value={newVendor}
              onChange={(e) => setNewVendor(e.target.value)}
              placeholder={isAdmin ? "e.g. Sinar Megah Logistics" : "Admin required to add vendor"}
              className="flex-1 bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[13px] text-[#17191c] focus:outline-none focus:border-[#17191c] disabled:opacity-60 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!isAdmin}
              className="pill-button-filled !h-10 !px-4 !text-[13px] flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add</span>
            </button>
          </form>

          <div className="space-y-2 pt-2 max-h-72 overflow-y-auto">
            {vendorList.map((v) => (
              <div
                key={v}
                className="flex items-center justify-between p-3 rounded-xl bg-[#fafafb] border border-[#ececec] text-[13px]"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span className="font-medium text-[#17191c]">{v}</span>
                </div>
                {isAdmin && (
                  <button
                    onClick={() => handleRemoveVendor(v)}
                    className="text-[#979799] hover:text-rose-600 p-1 transition-colors"
                    title="Remove vendor"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
