'use client';

import { useCallback, memo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';

function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();

  const handleSetEn = useCallback(() => setLanguage('en'), [setLanguage]);
  const handleSetUk = useCallback(() => setLanguage('uk'), [setLanguage]);

  return (
    <div className="flex bg-slate-100 rounded-full p-1 border border-slate-200">
      <button
        type="button"
        onClick={handleSetEn}
        className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
          language === 'en'
            ? 'bg-white shadow-sm text-slate-900'
            : 'text-slate-500 hover:text-slate-700'
        }`}
        aria-pressed={language === 'en'}
      >
        EN
      </button>
      <button
        type="button"
        onClick={handleSetUk}
        className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
          language === 'uk'
            ? 'bg-white shadow-sm text-slate-900'
            : 'text-slate-500 hover:text-slate-700'
        }`}
        aria-pressed={language === 'uk'}
      >
        UA
      </button>
    </div>
  );
}

export default memo(LanguageSwitcher);
