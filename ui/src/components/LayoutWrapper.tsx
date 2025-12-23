'use client';

import React, { useState } from 'react';
import { usePathname } from 'next/navigation';

import AIAssistant from './AIAssistant';
import AuthGuard from './AuthGuard';
import AppHeader from './AppHeader';

interface LayoutWrapperProps {
  children: React.ReactNode;
}

export default function LayoutWrapper({ children }: LayoutWrapperProps) {
  const pathname = usePathname();
  const [chatOpen, setChatOpen] = useState(false);

  // На странице входа - чистый layout без header
  const isAuthPage = pathname === '/auth';

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <AppHeader />
        
        <div className="flex-1 flex">
          {/* Main content - shrinks when chat is open */}
          <div
            className={`flex-1 transition-all duration-300 ease-in-out ${
              chatOpen ? 'mr-96' : 'mr-0'
            }`}
          >
            {children}
          </div>

          {/* AI Assistant */}
          <AIAssistant onToggle={setChatOpen} />
        </div>
      </div>
    </AuthGuard>
  );
}
