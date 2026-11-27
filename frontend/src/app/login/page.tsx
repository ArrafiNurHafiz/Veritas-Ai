'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { DEMO_USERS } from '@/lib/mockData';
import { UserRole } from '@/lib/types';
import {
  ENTERPRISE_AUTH_PATH,
  IS_ENTERPRISE,
  ROLE_TOKENS,
  login,
  setAuthToken,
} from '@/lib/api';
import { ArrowRight, AlertCircle, Lock } from 'lucide-react';

const ENTERPRISE_DEMO_PERSONAS: Array<{ role: UserRole; label: string; email: string }> = [
  { role: 'admin', label: 'Admin', email: 'admin@veritas.local' },
  { role: 'approver', label: 'Approver', email: 'approver@veritas.local' },
  { role: 'operator', label: 'Operator', email: 'operator@veritas.local' },
  { role: 'auditor', label: 'Auditor', email: 'auditor@veritas.local' },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleEnterprisePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    try {
      await login(email.trim(), password);
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sign in failed';
      setErrorMsg(msg);
      setIsLoading(false);
    }
  };

  const handleEnterpriseDemoLogin = async (role: UserRole, personaEmail: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(
        `/api/v1/auth/test-login?role=${encodeURIComponent(role)}&email=${encodeURIComponent(personaEmail)}`,
        { credentials: 'include' }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const msg =
          typeof body?.error?.message === 'string'
            ? body.error.message
            : typeof body?.detail === 'string'
              ? body.detail
              : `Demo login failed (${res.status})`;
        throw new Error(msg);
      }
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Demo login failed';
      setErrorMsg(msg);
      setIsLoading(false);
    }
  };

  const handleSelectDemoUser = (role: UserRole) => {
    const user = DEMO_USERS.find((u) => u.role === role);
    if (user) {
      setEmail(user.email);
      setErrorMsg(null);
    }
  };

  const handleDemoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    const user = DEMO_USERS.find((u) => u.email.toLowerCase() === email.trim().toLowerCase()) || {
      id: 'usr_custom',
      name: email.split('@')[0],
      email: email.trim(),
      role: 'operator' as UserRole,
      organizationId: 'org_nexora_tech',
      organizationName: 'Nexora Technologies',
      avatar: email.substring(0, 2).toUpperCase(),
    };

    const token = ROLE_TOKENS[user.role] || 'tok-admin';

    try {
      await login(email.trim(), password).catch(() => null);
      setAuthToken(token);
      localStorage.setItem('veritas_user', JSON.stringify(user));
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sign in failed';
      setErrorMsg(msg);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F0F0EC] text-[#192319] lg:grid lg:grid-cols-2">
      {/* Left Pine Editorial Panel */}
      <aside className="hidden lg:flex flex-col justify-between bg-[#192319] text-[#F0F0EC] sauce-dark-grid-bg p-12 border-r border-[#2D372D]">
        <Link
          href="/"
          className="inline-flex w-max items-center rounded-2xl bg-[#F0F0EC] px-4 py-2.5 group"
        >
          <Image
            src="/veritas-logo.png"
            alt="VERITAS — Control Before Action"
            width={2172}
            height={724}
            priority
            className="h-14 w-auto object-contain group-hover:scale-[1.02] transition-transform"
          />
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
          className="max-w-md space-y-5"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#043423] border border-[#3C483C] font-mono text-[10.5px] uppercase tracking-[0.16em] text-[#ABE082]">
            <Lock className="w-3 h-3" />
            <span>Governance Console</span>
          </span>
          <h1 className="font-display text-[48px] font-medium leading-[1.02] text-white">
            Control before <span className="text-[#ABE082] italic">action.</span>
          </h1>
          <p className="text-[15px] leading-relaxed text-[#DCDCD7]">
            AI agents only propose structured actions. The Harness validates deterministic
            policies, enforces human separation-of-duties, and signs Ed25519 receipts.
          </p>

          <div className="pt-6 border-t border-[#2D372D] grid gap-2.5 font-mono text-[11.5px] text-[#C8C8BE]">
            <span className="flex items-center gap-2.5">
              <span className="h-2 w-2 rounded-full bg-[#ABE082]" />
              Enterprise Harness · deny-by-default policy gate
            </span>
            <span className="flex items-center gap-2.5">
              <span className="h-2 w-2 rounded-full bg-[#F1BE23]" />
              Agent Service · isolated proposal-only container
            </span>
            <span className="flex items-center gap-2.5">
              <span className="h-2 w-2 rounded-full bg-[#4790DD]" />
              Ed25519 receipts · append-only hash chain
            </span>
          </div>
        </motion.div>

        <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-[#ABAD6C]">
          VERITAS AI · Enterprise Runtime Governance
        </p>
      </aside>

      {/* Right Sign-In Form */}
      <main className="flex items-center justify-center px-6 py-12 sauce-grid-bg">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="w-full max-w-[440px] rounded-[26px] bg-[#F8F8F8] border border-[#DCDCD7] p-7 sm:p-9 shadow-[0_24px_60px_-24px_rgba(25,35,25,0.16)]"
        >
          <div className="lg:hidden flex items-center mb-6">
            <Image
              src="/veritas-logo.png"
              alt="VERITAS — Control Before Action"
              width={2172}
              height={724}
              priority
              className="h-14 w-auto object-contain"
            />
          </div>

          <h2 className="font-display text-[32px] font-medium leading-tight text-[#192319]">
            Sign in to Console
          </h2>
          <p className="mt-1.5 text-[13.5px] text-[#2D372D]">
            {IS_ENTERPRISE
              ? 'Sign in with your organization account, SSO, or Demo Login.'
              : 'Sign in or select a demo persona to switch roles.'}
          </p>

          <form
            onSubmit={IS_ENTERPRISE ? handleEnterprisePasswordLogin : handleDemoSubmit}
            className="mt-6 space-y-4"
          >
            {errorMsg && (
              <div className="flex items-center gap-2 rounded-xl border border-[#F55524]/40 bg-[#F55524]/10 p-3 text-[12.5px] text-[#961001]">
                <AlertCircle className="h-4 w-4 shrink-0 text-[#F55524]" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-[#6D7344] font-semibold"
              >
                Work email
              </label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@veritas.local"
                className="h-11 w-full rounded-xl border border-[#DCDCD7] bg-white px-3.5 text-[13.5px] text-[#192319] outline-none transition-colors placeholder:text-[#C8C8BE] focus:border-[#192319]"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-[#6D7344] font-semibold"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                required={IS_ENTERPRISE}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-11 w-full rounded-xl border border-[#DCDCD7] bg-white px-3.5 text-[13.5px] text-[#192319] outline-none transition-colors focus:border-[#192319]"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="group inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[#ABE082] px-5 text-[14px] font-semibold text-[#192319] transition-all hover:bg-[#9cd670] active:scale-[0.99] disabled:opacity-60"
            >
              <span>{isLoading ? 'Signing in…' : 'Sign in'}</span>
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </form>

          {IS_ENTERPRISE && (
            <button
              type="button"
              disabled={isLoading}
              onClick={() => window.location.assign(ENTERPRISE_AUTH_PATH)}
              className="mt-3 inline-flex h-11 w-full items-center justify-center gap-2 rounded-full border border-[#192319] bg-white px-5 text-[13.5px] font-semibold text-[#192319] transition-colors hover:bg-[#F0F0EC] disabled:opacity-60"
            >
              <span>Continue with Organization SSO</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          )}

          <div className="mt-6 border-t border-[#DCDCD7] pt-5">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#6D7344] font-semibold">
              {IS_ENTERPRISE ? 'Demo Login (SSO Bypass)' : 'Quick Demo Personas'}
            </span>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              {(IS_ENTERPRISE ? ENTERPRISE_DEMO_PERSONAS : DEMO_USERS).map((persona) => (
                <button
                  key={persona.role}
                  type="button"
                  disabled={isLoading}
                  onClick={() =>
                    IS_ENTERPRISE
                      ? handleEnterpriseDemoLogin(persona.role, persona.email)
                      : handleSelectDemoUser(persona.role)
                  }
                  className="rounded-xl border border-[#DCDCD7] bg-white px-3 py-2.5 text-left transition-all hover:border-[#192319] hover:bg-[#F3FFCC]/50 disabled:opacity-60"
                >
                  <span className="block text-[12.5px] font-semibold text-[#192319] capitalize">
                    {'label' in persona ? persona.label : persona.role}
                  </span>
                  <span className="mt-0.5 block font-mono text-[10px] text-[#2D372D] truncate">
                    {persona.email}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <p className="mt-5 font-mono text-[10px] uppercase leading-relaxed tracking-[0.1em] text-[#6D7344]">
            Access is controlled by tenant RBAC and server-side sessions.
          </p>
        </motion.div>
      </main>
    </div>
  );
}
