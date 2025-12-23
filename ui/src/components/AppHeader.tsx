'use client';

import LanguageSwitcher from './LanguageSwitcher';
import { useLanguage } from '@/contexts/LanguageContext';

export default function AppHeader() {
  const { t } = useLanguage();

  const navItems = [
    { href: '/workflow', label: t('nav', 'workflow') },
    { href: '/projects', label: t('nav', 'projects') },
    { href: '/docs', label: t('nav', 'docs') },
    { href: '/document-matrix', label: t('nav', 'matrix') },
    { href: '/contract-comparison', label: t('nav', 'contracts') },
    { href: '/llm', label: t('nav', 'llm') },
    { href: '/quick', label: t('nav', 'quick') },
  ];

  return (
    <header className="bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap gap-4 justify-between items-center h-16">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2">
            <svg
              className="w-8 h-8 text-primary-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
              />
            </svg>
            <span className="text-xl font-bold text-slate-900">Repo Auditor</span>
          </a>

          {/* Main Navigation */}
          <nav className="flex flex-wrap items-center gap-4 md:gap-6">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-slate-600 hover:text-primary-600 font-medium transition-colors"
              >
                {item.label}
              </a>
            ))}

            <a
              href="/settings"
              className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
              title={t('nav', 'settings')}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </a>

            <a
              href="/auth"
              className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
              title={t('nav', 'auth')}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 11c.828 0 1.5-.672 1.5-1.5S12.828 8 12 8s-1.5.672-1.5 1.5S11.172 11 12 11zm0 7a9 9 0 100-18 9 9 0 000 18z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 14a2 2 0 104 0c0-1.105-2-2-2-2s-2 .895-2 2z"
                />
              </svg>
            </a>

            <a
              href="/workflow"
              className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 font-medium transition-colors"
            >
              {t('nav', 'start')}
            </a>

            <LanguageSwitcher />
          </nav>
        </div>
      </div>
    </header>
  );
}
