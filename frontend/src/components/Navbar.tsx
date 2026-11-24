'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-[#ececec]/60 transition-all">
      <div className="max-w-[1240px] mx-auto px-6 h-20 flex items-center justify-between">
        {/* Brand Logo - Steep Style */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-full bg-[#17191c] flex items-center justify-center text-white transition-transform group-hover:scale-105">
            <ShieldCheck className="w-4 h-4 stroke-[2]" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-display text-[24px] text-[#17191c] tracking-[-0.5px] leading-none">
              Veritas
            </span>
            <span className="font-sans text-[11px] font-medium text-[#979799] tracking-widest uppercase">
              AI
            </span>
          </div>
        </Link>

        {/* Center Nav Links - Whisper quiet */}
        <nav className="hidden md:flex items-center gap-9">
          <Link
            href="/#workbench"
            className="text-[16px] font-sans text-[#17191c] hover:text-[#777b86] transition-colors"
          >
            Platform
          </Link>
          <Link
            href="/#architecture"
            className="text-[16px] font-sans text-[#17191c] hover:text-[#777b86] transition-colors"
          >
            Architecture
          </Link>
          <Link
            href="/#features"
            className="text-[16px] font-sans text-[#17191c] hover:text-[#777b86] transition-colors"
          >
            Features
          </Link>
          <Link
            href="/dashboard/trust"
            className="text-[16px] font-sans text-[#17191c] hover:text-[#777b86] transition-colors flex items-center gap-1.5"
          >
            <span>Trust Explorer</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          </Link>
          <Link
            href="/#docs"
            className="text-[16px] font-sans text-[#17191c] hover:text-[#777b86] transition-colors"
          >
            Documentation
          </Link>
        </nav>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-5">
          <Link
            href="/login"
            className="text-[16px] font-sans font-normal text-[#17191c] hover:text-[#777b86] transition-colors"
          >
            Log in
          </Link>
          <Link
            href="/dashboard"
            className="group pill-button-filled !h-11 !px-5 !text-[15px] flex items-center gap-1.5 shadow-sm"
          >
            <span>Launch Console</span>
            <span className="arrow-slide inline-block">&rarr;</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
