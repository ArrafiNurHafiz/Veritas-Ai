import Link from 'next/link';
import { ShieldCheck, Lock, FileCheck, ArrowRight } from 'lucide-react';

const features = [
  {
    index: '01',
    icon: ShieldCheck,
    status: 'LIVE',
    title: 'Policy before action',
    description:
      'Every proposal is checked against vendor allowlists and amount ceilings before a protected tool can run. Deny by default.',
    rows: [
      ['tool', 'approve_invoice'],
      ['vendor', 'V-ABC'],
      ['amount', '8,500,000'],
    ],
    result: 'APPROVAL_REQUIRED',
    reason: 'AMOUNT_LIMIT',
    tone: '#fec740',
  },
  {
    index: '02',
    icon: Lock,
    status: 'LIVE',
    title: 'A person holds the gate',
    description:
      'Amounts over the automatic limit stop at a human approval queue. The approver signs off before the harness releases the call.',
    rows: [
      ['approval', 'APR-2036-001'],
      ['approver', 'sarah.jenkins'],
      ['state', 'HELD'],
    ],
    result: 'APPROVED',
    reason: 'HUMAN_SIGNOFF',
    tone: '#20df6f',
  },
  {
    index: '03',
    icon: FileCheck,
    status: 'LIVE · MOCK ANCHOR',
    title: 'Evidence you can verify',
    description:
      'Each execution leaves an Ed25519-signed receipt. Verification is available now; the default anchor is a local mock.',
    rows: [
      ['digest', '0x17c0…9f2'],
      ['signature', 'ed25519 valid'],
      ['anchor', 'local mock'],
    ],
    result: 'VERIFIED',
    reason: 'MOCK_ANCHOR',
    tone: '#20df6f',
  },
] as const;

export default function FeaturesShowcase() {
  return (
    <section id="features" className="px-6 py-20 md:py-24">
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-12 max-w-3xl">
          <p className="mb-4 text-sm font-semibold uppercase tracking-wider text-[#0075ff]">
            The control plane
          </p>
          <h2 className="text-[32px] font-medium leading-[1.1] tracking-[-0.04em] text-white md:text-[40px] lg:text-[46px]">
            Three checks <span className="text-[#0075ff]">before</span> any tool runs.
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-[#a7babe] md:text-lg">
            The agent proposes. The harness checks policy, asks a person when the amount is over
            limit, then records the decision as signed evidence. One path, no bypass.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <article
                key={feature.index}
                className="group flex flex-col rounded-[16px] border border-white/[0.08] bg-white/[0.02] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#0075ff]/60 hover:bg-white/[0.04]"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-9 w-9 items-center justify-center rounded-[8px] border border-[#0075ff]/25 bg-[#0075ff]/10 text-[#0075ff]">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="font-code text-[10px] uppercase tracking-[0.14em] text-white/35">
                    {feature.index} · {feature.status}
                  </span>
                </div>

                <div className="mt-6 rounded-[12px] border border-white/[0.06] bg-[#001027] p-4 font-code text-[11px]">
                  <div className="space-y-1">
                    {feature.rows.map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between gap-4">
                        <span className="text-white/35">{key}</span>
                        <span className="truncate text-[#d7e3f4]">{value}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-white/[0.06] pt-3">
                    <span className="text-white/25">&rarr;</span>
                    <span style={{ color: feature.tone }}>{feature.result}</span>
                    <span className="text-white/30">· {feature.reason}</span>
                  </div>
                </div>

                <h3 className="mt-6 text-[19px] font-medium tracking-[-0.02em] text-white">
                  {feature.title}
                </h3>
                <p className="mt-2 font-body-trigger text-[13px] leading-relaxed text-[#a7babe]">
                  {feature.description}
                </p>

                <Link
                  href={feature.index === '03' ? '/dashboard/trust' : '/dashboard'}
                  className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-[#0075ff] transition-opacity hover:opacity-80"
                >
                  {feature.index === '03' ? 'Open Trust Explorer' : 'See it in the console'}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </article>
            );
          })}
        </div>

        <p className="mt-8 font-code text-[10px] uppercase tracking-[0.14em] text-white/30">
          Panels are illustrative · harness :8002 · synthetic data
        </p>
      </div>
    </section>
  );
}
