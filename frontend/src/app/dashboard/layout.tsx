'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { motion } from 'motion/react';
import { AppProvider } from '@/lib/store';
import DashboardHeader from '@/components/DashboardHeader';
import DashboardSidebar from '@/components/DashboardSidebar';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  return (
    <AppProvider>
      <div className="min-h-screen md:h-screen md:overflow-hidden flex flex-col bg-[#F0F0EC] text-[#192319]">
        <DashboardHeader />
        <div className="flex-1 md:min-h-0 flex flex-col md:flex-row">
          <DashboardSidebar />
          <main className="flex-1 p-5 sm:p-7 lg:p-9 bg-[#F0F0EC] md:overflow-y-auto">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              className="max-w-[1220px] mx-auto"
            >
              {children}
            </motion.div>
          </main>
        </div>
      </div>
    </AppProvider>
  );
}
