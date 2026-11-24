import Link from 'next/link';
import { ShieldCheck } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-[#fafafb] border-t border-[#ececec] py-16">
      <div className="max-w-[1200px] mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Col 1 */}
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-full bg-[#17191c] flex items-center justify-center text-white">
                <ShieldCheck className="w-3.5 h-3.5 stroke-[2]" />
              </div>
              <span className="font-display text-[20px] text-[#17191c]">VERITAS AI</span>
            </div>
            <p className="text-[14px] text-[#777b86] leading-relaxed">
              Deterministic trust infrastructure mediating autonomous AI agent actions through policy gateways and signed private blockchain receipts.
            </p>
            <div className="pt-2">
              <span className="inline-block px-3 py-1 bg-[#f2f2f3] text-[#777b86] text-[12px] rounded-full border border-[#ececec]">
                Private Permissioned Ledger
              </span>
            </div>
          </div>

          {/* Col 2 */}
          <div className="space-y-3">
            <h4 className="text-[14px] font-medium text-[#17191c] uppercase tracking-wider">Product Surfaces</h4>
            <ul className="space-y-2 text-[14px] text-[#777b86]">
              <li><Link href="/dashboard" className="hover:text-[#17191c]">Enterprise Dashboard</Link></li>
              <li><Link href="/dashboard/tasks" className="hover:text-[#17191c]">Procurement Task Center</Link></li>
              <li><Link href="/dashboard/approvals" className="hover:text-[#17191c]">Human Approval Gate</Link></li>
              <li><Link href="/dashboard/policies" className="hover:text-[#17191c]">Policy Rule Manager</Link></li>
              <li><Link href="/dashboard/trust" className="hover:text-[#17191c]">Public Trust Explorer</Link></li>
            </ul>
          </div>

          {/* Col 3 */}
          <div className="space-y-3">
            <h4 className="text-[14px] font-medium text-[#17191c] uppercase tracking-wider">Governance & Trust</h4>
            <ul className="space-y-2 text-[14px] text-[#777b86]">
              <li><span className="hover:text-[#17191c]">RFC 8785 Canonical JCS</span></li>
              <li><span className="hover:text-[#17191c]">Ed25519 Cryptographic Signatures</span></li>
              <li><span className="hover:text-[#17191c]">Hyperledger Besu Private Anchor</span></li>
              <li><span className="hover:text-[#17191c]">Deny-by-Default Policy Gateway</span></li>
              <li><span className="hover:text-[#17191c]">Separation of AI Planning & Execution</span></li>
            </ul>
          </div>

          {/* Col 4 */}
          <div className="space-y-3">
            <h4 className="text-[14px] font-medium text-[#17191c] uppercase tracking-wider">Hackathon Evaluation</h4>
            <div className="bg-white p-4 rounded-[16px] border border-[#ececec] space-y-2 text-[13px] text-[#777b86]">
              <p className="font-medium text-[#17191c]">Demo Tenant: Nexora Technologies</p>
              <p>Synthetic procurement data only. No cryptocurrency, public tokens, user wallets, or live financial settlements.</p>
              <div className="pt-1 text-[11px] text-[#979799]">
                Specification v1.1 Baseline | Nov 2026
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-[#ececec] pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[13px] text-[#979799]">
          <p>© 2026 VERITAS AI Systems. Designed with Steep editorial minimalism.</p>
          <div className="flex items-center gap-6">
            <Link href="/#docs" className="hover:text-[#17191c]">REST API Contracts</Link>
            <Link href="/#architecture" className="hover:text-[#17191c]">Threat Model</Link>
            <Link href="/login" className="hover:text-[#17191c]">Sign In</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
