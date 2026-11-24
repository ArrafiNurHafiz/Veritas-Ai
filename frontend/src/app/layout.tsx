import type { Metadata } from "next";
import { Newsreader, Inter, Geist, Geist_Mono, Plus_Jakarta_Sans } from "next/font/google";
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

const jakartaFont = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jakarta",
  display: "swap",
});

const geistFont = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

const geistMonoFont = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VERITAS AI — Enterprise AI Governance & Trust Infrastructure",
  description:
    "An AI governance demo for policy checks before action, human approval, and controlled outbound data.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${signifierFont.variable} ${sohneFont.variable} ${jakartaFont.variable} ${geistFont.variable} ${geistMonoFont.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-white text-[#17191c]">
        {children}
      </body>
    </html>
  );
}
