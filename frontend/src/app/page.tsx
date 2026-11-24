'use client';

import React from 'react';
import Navbar from '@/components/Navbar';
import AxiomHero from '@/components/AxiomHero';
import AxiomSocialProof from '@/components/AxiomSocialProof';
import AxiomProblemGrid from '@/components/AxiomProblemGrid';
import AxiomFeatureDeepDives from '@/components/AxiomFeatureDeepDives';
import AxiomQueryPlayground from '@/components/AxiomQueryPlayground';
import AxiomComparison from '@/components/AxiomComparison';
import AxiomArchitecture from '@/components/AxiomArchitecture';
import AxiomCTA from '@/components/AxiomCTA';
import Footer from '@/components/Footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#08090A] text-[#EDEDED] font-sans antialiased selection:bg-[#DA5C2B]/30 selection:text-white">
      {/* 1. Header Navigation */}
      <Navbar />

      <main>
        {/* 2. Hero with Interactive Telemetry & Proposal Interceptor */}
        <AxiomHero />

        {/* 3. Social Proof & Architecture Quote */}
        <AxiomSocialProof />

        {/* 4. Problem Bento: What worked for chatbots doesn't work for agents */}
        <AxiomProblemGrid />

        {/* 5. Feature Deep Dives (Interactive Policy, Human Gate, Tamper Receipt) */}
        <AxiomFeatureDeepDives />

        {/* 6. Axiom Interactive Query Playground (APL Engine & Histogram) */}
        <AxiomQueryPlayground />

        {/* 7. Architecture Comparison (vs LLM direct calls, prompt guardrails, API GW) */}
        <AxiomComparison />

        {/* 8. System Boundaries (5 Clear Network & Service Barriers) */}
        <AxiomArchitecture />

        {/* 9. Final Call to Action */}
        <AxiomCTA />
      </main>

      {/* 10. Multi-column Axiom Footer */}
      <Footer />
    </div>
  );
}
