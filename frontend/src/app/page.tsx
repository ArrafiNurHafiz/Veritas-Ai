'use client';

import React from 'react';
import Navbar from '@/components/Navbar';
import SauceHeroAndOutcomes from '@/components/SauceHeroAndOutcomes';
import SaucePlatformAndProof from '@/components/SaucePlatformAndProof';
import Footer from '@/components/Footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#F0F0EC] text-[#192319] font-sans antialiased">
      <Navbar />
      <main>
        <SauceHeroAndOutcomes />
        <SaucePlatformAndProof />
      </main>
      <Footer />
    </div>
  );
}
