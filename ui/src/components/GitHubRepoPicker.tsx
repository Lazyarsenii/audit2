'use client';

import { useState, useEffect, useCallback } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  url: string;
  clone_url: string;
  private: boolean;
  description?: string;
  language?: string;
  default_branch: string;
  updated_at?: string;
}

interface GitHubOrg {
  login: string;
  id: number;
  description?: string;
  avatar_url?: string;
}

interface GitHubRepoPickerProps {
  onSelect: (repo: GitHubRepo) => void;
  onError: (error: string) => void;
}

export default function GitHubRepoPicker({ onSelect, onError }: GitHubRepoPickerProps) {
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [orgs, setOrgs] = useState<GitHubOrg[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [username, setUsername] = useState<string>('');

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (configured) {
      loadOrgs();
      loadRepos(selectedOrg || undefined);
    }
  }, [configured, selectedOrg]);

  const checkStatus = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/github/status`);
      const data = await res.json();
      setConfigured(data.configured);
      if (data.configured) {
        setUsername(data.username || '');
      } else {
        onError(data.message || 'GitHub not configured');
        setLoading(false);
      }
    } catch {
      setConfigured(false);
      onError('Failed to check GitHub status');
      setLoading(false);
    }
  };

  const loadOrgs = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/github/orgs`);
      if (res.ok) {
        const data = await res.json();
        setOrgs(data.orgs || []);
      }
    } catch {
      // Orgs are optional
    }
  };

  const loadRepos = async (org?: string) => {
    setLoading(true);
    try {
      const url = org
        ? `${API_BASE}/api/github/repos?org=${org}`
        : `${API_BASE}/api/github/repos`;
      const res = await apiFetch(url);
      if (!res.ok) {
        throw new Error('Failed to load repositories');
      }
      const data = await res.json();
      setRepos(data.repos || []);
    } catch {
      onError('Failed to load repositories');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      loadRepos(selectedOrg || undefined);
      return;
    }
    setLoading(true);
    try {
      const url = selectedOrg
        ? `${API_BASE}/api/github/repos/search?q=${encodeURIComponent(searchQuery)}&org=${selectedOrg}`
        : `${API_BASE}/api/github/repos/search?q=${encodeURIComponent(searchQuery)}`;
      const res = await apiFetch(url);
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setRepos(data.repos || []);
    } catch {
      onError('Search failed');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedOrg, onError]);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  if (configured === false) {
    return (
      <div className="border border-amber-200 bg-amber-50 rounded-lg p-6 text-center">
        <svg className="w-12 h-12 text-amber-500 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 className="font-medium text-amber-800 mb-1">GitHub Not Connected</h3>
        <p className="text-sm text-amber-600">
          Set GITHUB_PAT in backend .env to access repositories.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      {/* Header with org selector */}
      <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <svg className="w-5 h-5 text-slate-600" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          {orgs.length > 0 ? (
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-md bg-white focus:ring-2 focus:ring-primary-500"
            >
              <option value="">{username ? `${username} (personal)` : 'Personal repositories'}</option>
              {orgs.map((org) => (
                <option key={org.id} value={org.login}>
                  {org.login}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm text-slate-600">
              {username ? `@${username}` : 'Personal repositories'}
            </span>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-slate-200 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search repositories..."
            className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <button
            type="button"
            onClick={handleSearch}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 disabled:opacity-50"
          >
            Search
          </button>
        </div>
      </div>

      {/* Repo List */}
      <div className="max-h-80 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : repos.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <p>No repositories found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {repos.map((repo) => (
              <div
                key={repo.id}
                className="px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => onSelect(repo)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900 truncate">
                        {repo.name}
                      </span>
                      {repo.private && (
                        <span className="px-1.5 py-0.5 text-xs bg-amber-100 text-amber-700 rounded">
                          Private
                        </span>
                      )}
                    </div>
                    {repo.description && (
                      <p className="text-sm text-slate-500 truncate mt-0.5">
                        {repo.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                      {repo.language && (
                        <span className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-primary-500" />
                          {repo.language}
                        </span>
                      )}
                      <span>Updated {formatDate(repo.updated_at)}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(repo);
                    }}
                    className="px-3 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 flex-shrink-0"
                  >
                    Select
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 text-xs text-slate-500">
        {repos.length} repositories • Click to select
      </div>
    </div>
  );
}
