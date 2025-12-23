'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { clearApiKey, getAuthHeaders, setApiKey } from '@/lib/api';

export default function AuthPage() {
  const router = useRouter();
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);

  useEffect(() => {
    const storedKey = getAuthHeaders()['X-API-Key'];
    if (storedKey) {
      setActiveKey(storedKey);
    }
  }, []);

  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    setStatus('loading');
    setMessage(null);

    try {
      setApiKey(apiKeyInput.trim());
      setActiveKey(apiKeyInput.trim());
      setStatus('success');
      setMessage('Welcome!');

      setTimeout(() => {
        const redirect = sessionStorage.getItem('auth_redirect') || '/';
        sessionStorage.removeItem('auth_redirect');
        router.push(redirect);
      }, 500);

    } catch (err) {
      setStatus('error');
      setMessage(err instanceof Error ? err.message : 'Authentication failed');
    }
  };

  const handleClear = () => {
    clearApiKey();
    setActiveKey(null);
    setStatus('idle');
    setMessage(null);
  };

  if (activeKey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 px-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-slate-900">Authenticated</h1>
              <p className="text-slate-500 mt-1">You're logged in</p>
            </div>

            <button
              onClick={() => router.push('/')}
              className="w-full px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium text-lg mb-3"
            >
              Continue to Dashboard
            </button>

            <button
              onClick={handleClear}
              className="w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Repo Auditor</h1>
          <p className="text-slate-500 mt-2">Enter your API key to continue</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
          <form onSubmit={handleAuthenticate} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                API Key
              </label>
              <input
                type="password"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Enter your API key"
                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-lg"
                autoFocus
                required
              />
            </div>

            {message && (
              <div
                className={`text-sm px-4 py-3 rounded-lg ${
                  status === 'success'
                    ? 'bg-green-50 text-green-800 border border-green-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}
              >
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={status === 'loading' || !apiKeyInput.trim()}
              className="w-full px-4 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-lg transition-colors"
            >
              {status === 'loading' ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Authenticating...
                </span>
              ) : (
                'Continue'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-200 text-center">
            <p className="text-sm text-slate-500">
              Contact admin for API credentials
            </p>
          </div>
        </div>

        <p className="text-center text-sm text-slate-400 mt-6">
          SEH Foundation · Repo Auditor
        </p>
      </div>
    </div>
  );
}
