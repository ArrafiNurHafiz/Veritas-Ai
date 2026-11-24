'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useApp } from '@/lib/store';
import { DEMO_USERS } from '@/lib/mockData';
import { UserRole } from '@/lib/types';
import { ShieldCheck, ArrowRight, Building2, User, Key, Check } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_USERS[0].email);
  const [password, setPassword] = useState('demo123456');
  const [isLoading, setIsLoading] = useState(false);

  const handleSelectDemoUser = (role: UserRole) => {
    const user = DEMO_USERS.find((u) => u.role === role);
    if (user) {
      setEmail(user.email);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      router.push('/dashboard');
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#fafafb] flex flex-col justify-between">
      {/* Top Bar */}
      <header className="p-6">
        <Link href="/" className="flex items-center gap-2.5 max-w-[1200px] mx-auto group">
          <div className="w-8 h-8 rounded-full bg-[#17191c] flex items-center justify-center text-white">
            <ShieldCheck className="w-4 h-4 stroke-[2]" />
          </div>
          <span className="font-display text-[22px] text-[#17191c]">VERITAS AI</span>
        </Link>
      </header>

      {/* Main Login Card */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="bg-white rounded-[24px] max-w-md w-full p-8 border border-[#ececec] shadow-[0_0_0_1px_rgba(4,23,43,0.05),0_20px_25px_-5px_rgba(0,0,0,0.08),0_8px_10px_-6px_rgba(0,0,0,0.04)] space-y-6">
          <div className="space-y-1.5 text-center">
            <span className="text-[11px] font-semibold text-[#979799] uppercase tracking-wider">
              Tenant SSO &bull; Nexora Technologies
            </span>
            <h1 className="font-display text-[32px] text-[#17191c] leading-tight">
              Sign in to Console
            </h1>
            <p className="text-[14px] text-[#777b86]">
              Select a persona below for immediate role-based evaluation.
            </p>
          </div>

          {/* Quick Demo Persona Switcher */}
          <div className="space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#979799] block text-center">
              One-Click Persona Login
            </span>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_USERS.map((u) => {
                const isSelected = email === u.email;
                return (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => handleSelectDemoUser(u.role)}
                    className={`p-2.5 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'border-[#17191c] bg-[#17191c] text-white shadow-sm'
                        : 'border-[#ececec] bg-[#fafafb] hover:bg-white text-[#17191c]'
                    }`}
                  >
                    <div className="text-[12px] font-medium leading-tight">{u.name}</div>
                    <div className={`text-[10px] capitalize font-mono ${isSelected ? 'text-zinc-300' : 'text-[#777b86]'}`}>
                      {u.role}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium text-[#17191c]">Work Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[14px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[13px] font-medium text-[#17191c]">Password</label>
                <span className="text-[11px] text-[#777b86]">Sandbox: any password</span>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#fafafb] border border-[#ececec] rounded-xl px-3.5 py-2.5 text-[14px] text-[#17191c] focus:outline-none focus:border-[#17191c]"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full pill-button-filled !h-11 !text-[14px] flex items-center justify-center gap-2 mt-4"
            >
              <span>{isLoading ? 'Verifying Session...' : 'Authenticate & Enter Dashboard'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="pt-2 text-center text-[12px] text-[#979799]">
            Demo Environment &bull; Synthetic Organization Data Only
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="p-6 text-center text-[12px] text-[#979799]">
        &copy; 2026 VERITAS AI Systems. Private Hyperledger Besu Ledger Node.
      </footer>
    </div>
  );
}
