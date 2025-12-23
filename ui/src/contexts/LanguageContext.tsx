'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type SupportedLanguage = 'en' | 'uk';

const STORAGE_KEY = 'auditor_language';

const translations = {
  en: {
    nav: {
      workflow: 'Workflow',
      projects: 'Projects',
      docs: 'Docs',
      matrix: 'Matrix',
      contracts: 'Contracts',
      llm: 'LLM',
      quick: 'Quick Audit',
      settings: 'Settings',
      auth: 'API Auth',
      start: 'Start Analysis',
    },
    home: {
      title: 'Repository Auditor',
      subtitle:
        'Professional repository analysis and evaluation platform. Assess code quality, estimate costs, and generate documentation.',
      actions: {
        workflow: {
          title: 'Start Workflow',
          description: 'Analyze repository, review scores, generate documents',
        },
        projects: {
          title: 'Projects',
          description: 'Manage projects, track progress, view history',
        },
        docs: {
          title: 'Documentation',
          description: 'Methodology, scoring system, user guide',
        },
      },
      howItWorks: 'How It Works',
      steps: [
        {
          title: 'Setup',
          description: 'Enter repository URL and select evaluation profile',
        },
        {
          title: 'Analyze',
          description: 'Automated code analysis and metrics collection',
        },
        {
          title: 'Review',
          description: 'Review scores, health metrics, and cost estimates',
        },
        { title: 'Export', description: 'Generate reports, acts, and invoices' },
      ],
    },
  },
  uk: {
    nav: {
      workflow: 'Робочий процес',
      projects: 'Проєкти',
      docs: 'Документи',
      matrix: 'Матриця',
      contracts: 'Контракти',
      llm: 'LLM',
      quick: 'Швидкий аудит',
      settings: 'Налаштування',
      auth: 'API Авторизація',
      start: 'Почати аналіз',
    },
    home: {
      title: 'Аудитор репозиторіїв',
      subtitle:
        'Платформа професійного аналізу репозиторіїв. Оцінюйте якість коду, розраховуйте витрати та формуйте документацію.',
      actions: {
        workflow: {
          title: 'Розпочати процес',
          description: 'Аналізуйте репозиторій, оцінюйте бали, генеруйте документи',
        },
        projects: {
          title: 'Проєкти',
          description: 'Керуйте проєктами, відстежуйте прогрес та історію',
        },
        docs: {
          title: 'Документація',
          description: 'Методологія, система оцінювання, інструкції',
        },
      },
      howItWorks: 'Як це працює',
      steps: [
        {
          title: 'Налаштування',
          description: 'Вкажіть URL репозиторію та оберіть профіль оцінки',
        },
        {
          title: 'Аналіз',
          description: 'Автоматичний аналіз коду та збір метрик',
        },
        {
          title: 'Огляд',
          description: 'Переглядайте бали, метрики стану та оцінку вартості',
        },
        {
          title: 'Експорт',
          description: 'Генеруйте звіти, акти та рахунки',
        },
      ],
    },
  },
};

export type TranslationContent = typeof translations.en;

type TranslationSection = keyof TranslationContent;

type LanguageContextValue = {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  toggleLanguage: () => void;
  t: (section: TranslationSection, key: string | number) => any;
};

const LanguageContext = createContext<LanguageContextValue | undefined>(
  undefined,
);

export const LanguageProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  const [language, setLanguageState] = useState<SupportedLanguage>('en');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = localStorage.getItem(STORAGE_KEY) as SupportedLanguage | null;
    if (stored === 'en' || stored === 'uk') {
      setLanguageState(stored);
      document.documentElement.lang = stored;
    }
  }, []);

  const setLanguage = useCallback((lang: SupportedLanguage) => {
    setLanguageState(lang);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, lang);
      document.documentElement.lang = lang;
    }
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguageState((prev) => {
      const next = prev === 'en' ? 'uk' : 'en';
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, next);
        document.documentElement.lang = next;
      }
      return next;
    });
  }, []);

  const t = useCallback((section: TranslationSection, key: string | number) => {
    const sectionData = translations[language][section];
    if (Array.isArray(sectionData) && typeof key === 'number') {
      const fallbackArray = translations.en[section] as any;
      return sectionData[key] ?? fallbackArray?.[key];
    }
    if (!Array.isArray(sectionData) && typeof key === 'string') {
      const currentSection = sectionData as Record<string, any>;
      const fallbackSection = translations.en[section] as Record<string, any>;
      return currentSection[key] ?? fallbackSection?.[key] ?? key;
    }
    return key;
  }, [language]);

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      toggleLanguage,
      t,
    }),
    [language, setLanguage, toggleLanguage, t],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
};
