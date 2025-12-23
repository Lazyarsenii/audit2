'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { hasApiKey, API_BASE } from '@/lib/api';

// Public paths that don't require auth
const PUBLIC_PATHS = ['/auth'];

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [apiKeyRequired, setApiKeyRequired] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if backend requires API key
    const checkApiKeyRequired = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/settings/auth-required`);
        if (res.ok) {
          const data = await res.json();
          setApiKeyRequired(data.api_key_required ?? false);
        } else {
          // If endpoint doesn't exist or fails, assume not required
          setApiKeyRequired(false);
        }
      } catch {
        // Network error - assume not required for better UX
        setApiKeyRequired(false);
      }
    };

    checkApiKeyRequired();
  }, []);

  useEffect(() => {
    // Wait for apiKeyRequired check
    if (apiKeyRequired === null) return;

    // If API key is not required by backend, authorize immediately
    if (!apiKeyRequired) {
      setIsAuthorized(true);
      return;
    }

    // Check public paths
    const isPublicPath = PUBLIC_PATHS.some(path => pathname.startsWith(path));
    
    if (isPublicPath) {
      setIsAuthorized(true);
      return;
    }

    // Check for API key
    if (hasApiKey()) {
      setIsAuthorized(true);
    } else {
      // Save redirect target
      if (pathname !== '/') {
        sessionStorage.setItem('auth_redirect', pathname);
      }
      // Redirect to auth page
      router.push('/auth');
    }
  }, [pathname, router, apiKeyRequired]);

  // Show loading while checking
  if (isAuthorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
