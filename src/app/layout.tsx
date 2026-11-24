import type { Metadata } from "next";
import { Newsreader, Inter } from "next/font/google";
import "./globals.css";

const signifierFont = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  weight: ["400"],
  variable: "--font-signifier",
  display: "swap",
});

const sohneFont = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sohne",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VERITAS AI — Enterprise AI Governance & Trust Infrastructure",
  description:
    "Deterministic policy mediation, human-in-the-loop authorization, and tamper-proof execution receipts anchored to a private permissioned ledger.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${signifierFont.variable} ${sohneFont.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-white text-[#17191c]">
        {children}
      </body>
    </html>
  );
}
