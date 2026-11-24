'use client';

import React from 'react';
import { AppProvider } from '@/lib/store';
import DashboardHeader from '@/components/DashboardHeader';
import DashboardSidebar from '@/components/DashboardSidebar';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppProvider>
      <div className="min-h-screen flex flex-col bg-white">
        <DashboardHeader />
        <div className="flex-1 flex flex-col md:flex-row">
          <DashboardSidebar />
          <main className="flex-1 p-6 lg:p-8 bg-white overflow-y-auto">
            <div className="max-w-[1200px] mx-auto">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AppProvider>
  );
}
