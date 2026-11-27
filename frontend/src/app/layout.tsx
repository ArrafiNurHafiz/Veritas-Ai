import type { Metadata } from "next";
import {
  Newsreader,
  Atkinson_Hyperlegible,
  Plus_Jakarta_Sans,
  Geist_Mono,
} from "next/font/google";
import "./globals.css";

const editorialSerif = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  weight: ["400", "500", "600"],
  variable: "--font-editorial",
  display: "swap",
});

const hyperlegibleSans = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-hyperlegible",
  display: "swap",
});

const jakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jakarta",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VERITAS AI — Control Before Action | Enterprise AI Governance",
  description:
    "Deterministic runtime governance harness for enterprise AI agents: policy checks before action, human separation-of-duties, and Ed25519 cryptographic receipts.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${editorialSerif.variable} ${hyperlegibleSans.variable} ${jakartaSans.variable} ${geistMono.variable} h-full antialiased scroll-smooth`}
    >
      <body className="min-h-full flex flex-col bg-[#F0F0EC] text-[#192319] selection:bg-[#ABE082] selection:text-[#192319]">
        {children}
      </body>
    </html>
  );
}
