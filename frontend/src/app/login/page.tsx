'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { DEMO_USERS } from '@/lib/mockData';
import { UserRole } from '@/lib/types';
import {
  ENTERPRISE_AUTH_PATH,
  IS_ENTERPRISE,
  ROLE_TOKENS,
  VERITAS_TEST_MODE,
  login,
  setAuthToken,
} from '@/lib/api';
import { ShieldCheck, ArrowRight, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_USERS[0].email);
  const [password, setPassword] = useState('demo123456');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!IS_ENTERPRISE || !VERITAS_TEST_MODE) return;
    // Full document navigation: test-login sets HttpOnly session cookies.
    window.location.assign(ENTERPRISE_AUTH_PATH);
  }, []);

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

  if (IS_ENTERPRISE) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-[#15171a] px-6 text-[#d7d9dd]">
        <div className="w-full max-w-[380px]">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-md border border-[#3b3e45] bg-[#121317]">
              <ShieldCheck className="h-4 w-4 stroke-[2]" />
            </span>
            <span className="font-trigger text-[20px] font-medium tracking-[-0.03em] text-[#e8e9ec]">VERITAS</span>
          </div>
          <h1 className="mt-10 font-trigger text-[32px] font-medium leading-tight tracking-[-0.03em] text-[#e8e9ec]">
            Sign in to Console
          </h1>
          <p className="mt-2 font-body-trigger text-[13px] leading-relaxed text-[#878c99]">
            {VERITAS_TEST_MODE
              ? 'Starting an automated test session with the configured identity.'
              : 'Sign in with your organization account or corporate SSO.'}
          </p>

          {!VERITAS_TEST_MODE && (
            <form onSubmit={handleEnterprisePasswordLogin} className="mt-6 space-y-4">
              {errorMsg && (
                <div className="flex items-center gap-2 rounded border border-rose-500/40 bg-rose-950/30 p-2.5 font-code text-[11px] text-rose-300">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                  <span>{errorMsg}</span>
                </div>
              )}
              <div className="space-y-1.5">
                <label htmlFor="ent-email" className="font-code text-[10px] uppercase tracking-[0.14em] text-[#878c99]">
                  Work email
                </label>
                <input
                  id="ent-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="h-10 w-full rounded border border-[#3b3e45] bg-[#121317] px-3 font-body-trigger text-[13px] text-[#e8e9ec] outline-none transition-colors placeholder:text-[#5f6570] focus:border-[#a8ff53]"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="ent-password" className="font-code text-[10px] uppercase tracking-[0.14em] text-[#878c99]">
                  Password
                </label>
                <input
                  id="ent-password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-10 w-full rounded border border-[#3b3e45] bg-[#121317] px-3 font-body-trigger text-[13px] text-[#e8e9ec] outline-none transition-colors focus:border-[#a8ff53]"
                />
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="group inline-flex h-10 w-full items-center justify-center gap-2 rounded bg-[#a8ff53] px-4 font-body-trigger text-[14px] font-medium text-[#121317] transition-colors hover:bg-[#cfffa0] disabled:opacity-70"
              >
                <span>{isLoading ? 'Signing in…' : 'Sign in'}</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </button>
            </form>
          )}

          <button
            type="button"
            onClick={() => window.location.assign(ENTERPRISE_AUTH_PATH)}
            className={`group inline-flex h-10 w-full items-center justify-center gap-2 rounded px-4 font-body-trigger text-[14px] font-medium transition-colors ${
              VERITAS_TEST_MODE
                ? 'mt-7 bg-[#a8ff53] text-[#121317] hover:bg-[#cfffa0]'
                : 'mt-3 border border-[#3b3e45] bg-[#121317] text-[#e8e9ec] hover:border-[#5f6570]'
            }`}
          >
            <span>{VERITAS_TEST_MODE ? 'Continue to test session' : 'Continue with Organization SSO'}</span>
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </button>
          <p className="mt-5 font-code text-[9px] uppercase leading-relaxed tracking-[0.12em] text-[#5f6570]">
            Access is controlled by tenant RBAC and server-side sessions.
          </p>
        </div>
      </main>
    );
  }

  const handleSelectDemoUser = (role: UserRole) => {
    const user = DEMO_USERS.find((u) => u.role === role);
    if (user) {
      setEmail(user.email);
      setErrorMsg(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
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
      // Attempt live login with backend to set session cookies
      await login(email.trim(), password).catch(() => null);
      
      // Store token and user locally for instantaneous API proxy auth
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
    <div className="min-h-screen bg-[#15171a] text-[#d7d9dd] lg:grid lg:grid-cols-2">
      <aside className="hidden flex-col justify-between border-r border-[#272a2e] bg-[#1a1b1f] p-10 lg:flex">
        <Link href="/" className="flex w-max items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md border border-[#3b3e45] bg-[#121317]">
            <ShieldCheck className="h-4 w-4 stroke-[2]" />
          </span>
          <span className="font-trigger text-[20px] font-medium tracking-[-0.03em] text-[#e8e9ec]">
            VERITAS
          </span>
          <span className="font-code text-[10px] uppercase tracking-[0.2em] text-[#878c99]">
            AI
          </span>
        </Link>

        <div className="max-w-md">
          <span className="font-code text-[11px] uppercase tracking-[0.2em] text-[#878c99]">
            / Governance console
          </span>
          <h1 className="mt-5 font-trigger text-[46px] font-medium leading-[0.98] tracking-[-0.045em] text-[#e8e9ec]">
            Control before
            <br />
            <span className="text-[#878c99]">action.</span>
          </h1>
          <p className="mt-5 font-body-trigger text-[14px] leading-relaxed text-[#878c99]">
            The agent only proposes. The Harness validates policy, asks a person when the amount is
            over limit, and signs the evidence.
          </p>

          <div className="mt-10 grid gap-2 border-t border-[#272a2e] pt-6 font-code text-[11px] text-[#878c99]">
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[#a8ff53]" />
              harness :8002 · policy deny-by-default
            </span>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[#9c9af2]" />
              agent :8001 optional · proposal-only
            </span>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[#41ff54]" />
              receipts signed · local mock anchor
            </span>
          </div>
        </div>

        <p className="font-code text-[10px] uppercase tracking-[0.14em] text-[#5f6570]">
          Synthetic demo data · no real funds or tokens
        </p>
      </aside>

      <main className="flex min-h-screen flex-col justify-center px-6 py-10">
        <div className="mx-auto w-full max-w-[380px]">
          <Link href="/" className="mb-10 flex w-max items-center gap-2.5 lg:hidden">
            <span className="flex h-8 w-8 items-center justify-center rounded-md border border-[#3b3e45] bg-[#1a1b1f]">
              <ShieldCheck className="h-4 w-4 stroke-[2]" />
            </span>
            <span className="font-trigger text-[20px] font-medium tracking-[-0.03em] text-[#e8e9ec]">
              VERITAS
            </span>
          </Link>

          <span className="font-code text-[10px] uppercase tracking-[0.18em] text-[#5f6570]">
            Tenant SSO · Nexora Technologies
          </span>
          <h2 className="mt-3 font-trigger text-[32px] font-medium leading-tight tracking-[-0.03em] text-[#e8e9ec]">
            Sign in to Console
          </h2>
          <p className="mt-2 font-body-trigger text-[13px] leading-relaxed text-[#878c99]">
            Pick a demo persona or enter credentials. Roles decide what each screen allows.
          </p>

          <div className="mt-7 space-y-2">
            <span className="font-code text-[10px] uppercase tracking-[0.16em] text-[#5f6570]">
              Demo personas
            </span>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_USERS.map((u) => {
                const isSelected = email === u.email;
                return (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => handleSelectDemoUser(u.role)}
                    className={`rounded border p-2.5 text-left transition-colors ${
                      isSelected
                        ? 'border-[#a8ff53]/50 bg-[#1a2013]'
                        : 'border-[#272a2e] bg-[#121317] hover:border-[#3b3e45]'
                    }`}
                  >
                    <span className="block font-body-trigger text-[12px] font-medium leading-tight text-[#e8e9ec]">
                      {u.name}
                    </span>
                    <span
                      className={`mt-0.5 block font-code text-[9px] uppercase tracking-[0.12em] ${
                        isSelected ? 'text-[#a8ff53]' : 'text-[#878c99]'
                      }`}
                    >
                      {u.role}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="my-6 flex items-center gap-3">
            <span className="h-px flex-1 bg-[#272a2e]" />
            <span className="font-code text-[9px] uppercase tracking-[0.16em] text-[#5f6570]">
              or use email
            </span>
            <span className="h-px flex-1 bg-[#272a2e]" />
          </div>

          {errorMsg && (
            <div className="mb-4 flex items-center gap-2 rounded border border-rose-500/40 bg-rose-950/30 p-2.5 font-code text-[11px] text-rose-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="font-code text-[10px] uppercase tracking-[0.14em] text-[#878c99]"
              >
                Work email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-10 w-full rounded border border-[#3b3e45] bg-[#121317] px-3 font-body-trigger text-[13px] text-[#e8e9ec] outline-none transition-colors placeholder:text-[#5f6570] focus:border-[#a8ff53]"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="font-code text-[10px] uppercase tracking-[0.14em] text-[#878c99]"
                >
                  Password
                </label>
                <span className="font-code text-[9px] uppercase tracking-[0.12em] text-[#5f6570]">
                  Sandbox: any password
                </span>
              </div>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-10 w-full rounded border border-[#3b3e45] bg-[#121317] px-3 font-body-trigger text-[13px] text-[#e8e9ec] outline-none transition-colors focus:border-[#a8ff53]"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="group mt-1 inline-flex h-10 w-full items-center justify-center gap-2 rounded bg-[#a8ff53] px-4 font-body-trigger text-[14px] font-medium text-[#121317] transition-colors hover:bg-[#cfffa0] disabled:opacity-70"
            >
              <span>{isLoading ? 'Opening console…' : 'Enter demo console'}</span>
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </form>

          <p className="mt-5 font-code text-[9px] uppercase leading-relaxed tracking-[0.12em] text-[#5f6570]">
            Synthetic demo accounts · session created in the local Harness sandbox.
          </p>

          <div className="mt-10 flex items-center justify-between border-t border-[#272a2e] pt-4 font-code text-[9px] uppercase tracking-[0.14em] text-[#5f6570]">
            <span>© 2026 VERITAS AI</span>
            <Link href="/" className="transition-colors hover:text-[#d7d9dd]">
              Back to site
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
