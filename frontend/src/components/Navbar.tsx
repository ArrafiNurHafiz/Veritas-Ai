'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, useScroll, useSpring } from 'motion/react';
import { ArrowRight, Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { label: 'Outcomes', href: '#outcomes' },
  { label: 'Agents', href: '#agents' },
  { label: 'Playground', href: '#playground' },
  { label: 'Security', href: '#security' },
  { label: 'Trust Explorer', href: '/dashboard/trust' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 220, damping: 30, restDelta: 0.001 });

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[#F0F0EC]/90 backdrop-blur-md border-b border-[#DCDCD7] shadow-[0_8px_30px_-12px_rgba(25,35,25,0.08)]'
          : 'bg-[#F0F0EC]/75 backdrop-blur-sm border-b border-transparent'
      }`}
    >
      {/* Scroll progress indicator */}
      <motion.div
        style={{ scaleX }}
        className="fixed top-0 left-0 right-0 h-[2.5px] bg-[#ABE082] origin-left z-50"
      />

      <div className="max-w-[1280px] mx-auto px-5 sm:px-8 h-[84px] flex items-center justify-between gap-4">
        {/* Brand */}
        <Link href="/" className="flex items-center group">
          <Image
            src="/veritas-logo.png"
            alt="VERITAS — Control Before Action"
            width={2172}
            height={724}
            priority
            className="h-14 sm:h-16 w-auto object-contain transition-transform duration-200 group-hover:scale-[1.02]"
          />
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="px-3.5 py-2 rounded-full text-[13.5px] font-medium text-[#2D372D] hover:text-[#192319] hover:bg-[#192319]/[0.05] transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Actions */}
        <div className="hidden md:flex items-center gap-2.5">
          <Link
            href="/login"
            className="px-4 py-2 rounded-full text-[13.5px] font-semibold text-[#192319] border border-[#C8C8BE] bg-[#F8F8F8] hover:border-[#192319] transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/dashboard"
            className="group inline-flex items-center gap-2 px-4.5 py-2 rounded-full text-[13.5px] font-semibold bg-[#ABE082] text-[#192319] hover:bg-[#9cd670] active:scale-[0.98] transition-all shadow-sm"
          >
            <span>Open Console</span>
            <span className="sauce-btn-arrow">
              <ArrowRight className="w-3.5 h-3.5 arrow-primary" />
              <ArrowRight className="w-3.5 h-3.5 arrow-secondary" />
            </span>
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Toggle menu"
          className="md:hidden p-2 rounded-lg border border-[#DCDCD7] bg-[#F8F8F8] text-[#192319]"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-t border-[#DCDCD7] bg-[#F8F8F8] px-5 py-4 space-y-2">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className="block px-3 py-2 rounded-lg text-[14px] font-medium text-[#192319] hover:bg-[#F0F0EC]"
            >
              {item.label}
            </Link>
          ))}
          <div className="pt-2 flex flex-col gap-2">
            <Link
              href="/login"
              onClick={() => setMobileOpen(false)}
              className="w-full text-center px-4 py-2.5 rounded-full text-[13.5px] font-semibold border border-[#C8C8BE] bg-white text-[#192319]"
            >
              Sign in
            </Link>
            <Link
              href="/dashboard"
              onClick={() => setMobileOpen(false)}
              className="w-full text-center px-4 py-2.5 rounded-full text-[13.5px] font-semibold bg-[#ABE082] text-[#192319]"
            >
              Open Console
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
