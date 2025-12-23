const API_KEY_STORAGE_KEY = 'ra_api_key';

/**
 * Base URL for backend API. Prefer an explicit deployment URL when available,
 * otherwise fall back to Railway production URL or empty for local dev.
 */
const getApiBase = (): string => {
  // Check env variables first
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (process.env.NEXT_PUBLIC_BACKEND_URL) return process.env.NEXT_PUBLIC_BACKEND_URL;
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  
  // In browser on Vercel, use Railway backend
  if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
    return 'https://auditor-production-f8be.up.railway.app';
  }
  
  // Local development - use relative paths (proxy) or localhost
  return '';
};

export const API_BASE = getApiBase();

export const getStoredApiKey = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(API_KEY_STORAGE_KEY);
};

export const setApiKey = (key: string) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(API_KEY_STORAGE_KEY, key);
};

export const clearApiKey = () => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(API_KEY_STORAGE_KEY);
};

export const hasApiKey = (): boolean => !!getStoredApiKey();

export const getAuthHeaders = (): Record<string, string> => {
  const key = getStoredApiKey();
  return key ? { 'X-API-Key': key } : {};
};

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit) {
  const mergedHeaders = {
    ...getAuthHeaders(),
    ...(init?.headers instanceof Headers
      ? Object.fromEntries(init.headers.entries())
      : (init?.headers as Record<string, string> | undefined)),
  } as Record<string, string>;

  return fetch(input, {
    ...init,
    headers: mergedHeaders,
  });
}
