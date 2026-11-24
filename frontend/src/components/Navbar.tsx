'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ShieldCheck, Menu, X, ChevronRight } from 'lucide-react';

const navLinks = [
  { href: '/#interactive', label: 'Playground' },
  { href: '/#features', label: 'Platform' },
  { href: '/#problems', label: 'Solutions' },
  { href: '/#architecture', label: 'Architecture' },
  { href: '/#compare', label: 'Compare' },
  { href: '/dashboard/trust', label: 'Trust Explorer' },
];

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? 'border-b border-[#22252F] bg-[#08090A]/95 shadow-[0_10px_30px_-10px_rgba(0,0,0,0.8)] backdrop-blur-md'
          : 'border-b border-[#1A1C22]/60 bg-[#08090A]/80 backdrop-blur-sm'
      }`}
    >
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-90">
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DA5C2B]/40 bg-[#DA5C2B]/10 text-[#DA5C2B] transition-transform hover:scale-105">
            <ShieldCheck className="h-4 w-4 stroke-[2.2]" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[17px] font-semibold tracking-[-0.03em] text-white">
              VERITAS
            </span>
            <span className="font-mono text-[9px] font-medium uppercase tracking-[0.18em] text-[#DA5C2B]">
              AI
            </span>
          </div>
        </Link>

        {/* Center Nav Links - Desktop */}
        <nav aria-label="Main Navigation" className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-1.5 text-[13px] font-medium text-[#8F94A0] transition-colors hover:bg-white/[0.04] hover:text-[#EDEDED]"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right CTA */}
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="hidden text-[13px] font-medium text-[#8F94A0] transition-colors hover:text-white sm:inline-block"
          >
            Sign in
          </Link>
          
          <Link
            href="/dashboard"
            className="group inline-flex h-8 items-center gap-2 rounded-md bg-[#DA5C2B] px-3.5 text-[12px] font-medium text-white transition-all hover:bg-[#EB6733] hover:shadow-[0_0_15px_rgba(218,92,43,0.4)] active:scale-[0.98]"
          >
            <span>Open console</span>
            <span aria-hidden="true" className="axiom-btn-arrow font-mono text-[13px]">
              <span className="arrow-primary">→</span>
              <span className="arrow-secondary">→</span>
            </span>
          </Link>

          {/* Mobile menu button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-[#8F94A0] hover:bg-white/[0.05] hover:text-white md:hidden"
            aria-label="Toggle Menu"
          >
            {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-b border-[#1A1C22] bg-[#0C0D11] px-4 py-4 md:hidden">
          <div className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium text-[#8F94A0] hover:bg-white/[0.04] hover:text-white"
              >
                <span>{link.label}</span>
                <ChevronRight className="h-3.5 w-3.5 text-white/30" />
              </Link>
            ))}
            <div className="mt-3 border-t border-[#1A1C22] pt-3">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="block rounded-md px-3 py-2 text-sm font-medium text-[#8F94A0] hover:text-white"
              >
                Sign in
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
