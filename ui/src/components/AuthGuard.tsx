'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { hasApiKey } from '@/lib/api';

// Только страница входа публичная
const PUBLIC_PATHS = ['/auth'];

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    // Проверяем публичные пути
    const isPublicPath = PUBLIC_PATHS.some(path => pathname.startsWith(path));
    
    if (isPublicPath) {
      setIsAuthorized(true);
      return;
    }

    // Проверяем наличие API ключа
    if (hasApiKey()) {
      setIsAuthorized(true);
    } else {
      // Сохраняем куда хотел пойти пользователь
      if (pathname !== '/') {
        sessionStorage.setItem('auth_redirect', pathname);
      }
      // Редирект на страницу входа
      router.push('/auth');
    }
  }, [pathname, router]);

  // Показываем загрузку пока проверяем
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
