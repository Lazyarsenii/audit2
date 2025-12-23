'use client';

import { useLanguage } from '@/contexts/LanguageContext';

export default function HomePage() {
  const { t } = useLanguage();

  const steps = t('home', 'steps');

  return (
    <div className="min-h-[calc(100vh-64px)] flex flex-col">
      {/* Hero Section */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
            {t('home', 'title')}
          </h1>
          <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto">
            {t('home', 'subtitle')}
          </p>

          {/* Main Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {/* Start Workflow */}
            <a
              href="/workflow"
              className="group bg-primary-600 hover:bg-primary-700 text-white rounded-xl p-6 transition-all hover:scale-105 hover:shadow-lg"
            >
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2">
                {t('home', 'actions').workflow.title}
              </h3>
              <p className="text-primary-100 text-sm">
                {t('home', 'actions').workflow.description}
              </p>
            </a>

            {/* Projects */}
            <a
              href="/projects"
              className="group bg-white hover:bg-slate-50 border-2 border-slate-200 hover:border-primary-300 rounded-xl p-6 transition-all hover:scale-105 hover:shadow-lg"
            >
              <div className="w-12 h-12 bg-slate-100 group-hover:bg-primary-100 rounded-lg flex items-center justify-center mb-4 mx-auto transition-colors">
                <svg className="w-6 h-6 text-slate-600 group-hover:text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                {t('home', 'actions').projects.title}
              </h3>
              <p className="text-slate-500 text-sm">
                {t('home', 'actions').projects.description}
              </p>
            </a>

            {/* Documentation */}
            <a
              href="/docs"
              className="group bg-white hover:bg-slate-50 border-2 border-slate-200 hover:border-primary-300 rounded-xl p-6 transition-all hover:scale-105 hover:shadow-lg"
            >
              <div className="w-12 h-12 bg-slate-100 group-hover:bg-primary-100 rounded-lg flex items-center justify-center mb-4 mx-auto transition-colors">
                <svg className="w-6 h-6 text-slate-600 group-hover:text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                {t('home', 'actions').docs.title}
              </h3>
              <p className="text-slate-500 text-sm">
                {t('home', 'actions').docs.description}
              </p>
            </a>
          </div>
        </div>
      </div>

      {/* Quick Guide */}
      <div className="bg-white border-t border-slate-200 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-semibold text-slate-900 mb-6 text-center">
            {t('home', 'howItWorks')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {Array.isArray(steps) &&
              steps.map((item, index) => (
                <div key={item.title} className="text-center">
                  <div className="w-10 h-10 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center font-bold mx-auto mb-3">
                    {index + 1}
                  </div>
                  <h3 className="font-medium text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-500">{item.description}</p>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
