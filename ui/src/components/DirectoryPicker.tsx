'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface DirectoryItem {
  name: string;
  path: string;
  is_dir: boolean;
  is_git: boolean;
}

interface QuickPath {
  name: string;
  path: string;
  icon: string;
}

interface DirectoryPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
}

export default function DirectoryPicker({
  isOpen,
  onClose,
  onSelect,
}: DirectoryPickerProps) {
  const apiUrl = API_BASE || 'http://localhost:8000';
  const [currentPath, setCurrentPath] = useState('~');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [items, setItems] = useState<DirectoryItem[]>([]);
  const [quickPaths, setQuickPaths] = useState<QuickPath[]>([]);
  const [isGitRepo, setIsGitRepo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load quick paths on mount
  useEffect(() => {
    if (isOpen) {
      loadQuickPaths();
      loadDirectory('~');
    }
  }, [isOpen]);

  const loadQuickPaths = async () => {
    try {
      const res = await apiFetch(`${apiUrl}/api/browse/quick-paths`);
      if (res.ok) {
        const data = await res.json();
        setQuickPaths(data.paths);
      }
    } catch (err) {
      console.error('Failed to load quick paths:', err);
    }
  };

  const loadDirectory = async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(
        `${apiUrl}/api/browse?path=${encodeURIComponent(path)}&dirs_only=true`
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to load directory');
      }
      const data = await res.json();
      setCurrentPath(data.current_path);
      setParentPath(data.parent_path);
      setItems(data.items);
      setIsGitRepo(data.is_git_repo);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load directory');
    } finally {
      setLoading(false);
    }
  };

  const handleNavigate = (path: string) => {
    loadDirectory(path);
  };

  const handleSelect = () => {
    onSelect(currentPath);
    onClose();
  };

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'home':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        );
      case 'desktop':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        );
      case 'download':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        );
      case 'code':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
        );
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Select Repository Directory</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Quick Paths */}
        <div className="px-6 py-3 border-b border-slate-100 flex gap-2 flex-wrap">
          {quickPaths.map((qp) => (
            <button
              key={qp.path}
              onClick={() => handleNavigate(qp.path)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm text-slate-700 transition-colors"
            >
              {getIcon(qp.icon)}
              <span>{qp.name}</span>
            </button>
          ))}
        </div>

        {/* Current Path */}
        <div className="px-6 py-3 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Location:</span>
            <code className="flex-1 text-sm text-slate-700 bg-white px-3 py-1 rounded border border-slate-200 truncate">
              {currentPath}
            </code>
            {isGitRepo && (
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                Git Repo
              </span>
            )}
          </div>
        </div>

        {/* Directory List */}
        <div className="flex-1 overflow-y-auto p-2">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
              <button
                onClick={() => loadDirectory('~')}
                className="mt-2 text-primary-600 hover:underline text-sm"
              >
                Go to Home
              </button>
            </div>
          ) : (
            <div className="space-y-1">
              {/* Parent Directory */}
              {parentPath && (
                <button
                  onClick={() => handleNavigate(parentPath)}
                  className="w-full flex items-center gap-3 px-4 py-2 hover:bg-slate-100 rounded-lg transition-colors text-left"
                >
                  <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                  </svg>
                  <span className="text-slate-600">..</span>
                </button>
              )}

              {/* Directory Items */}
              {items.map((item) => (
                <div
                  key={item.path}
                  className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                    item.is_git
                      ? 'bg-green-50 border border-green-200'
                      : 'hover:bg-slate-50'
                  }`}
                >
                  {/* Navigate button (click on folder icon + name) */}
                  <button
                    onClick={() => loadDirectory(item.path)}
                    className="flex items-center gap-3 flex-1 text-left hover:opacity-70"
                    title="Open folder"
                  >
                    {item.is_git ? (
                      <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                    )}
                    <span className={item.is_git ? 'text-green-700 font-medium' : 'text-slate-700'}>
                      {item.name}
                    </span>
                  </button>
                  {/* Select button */}
                  <button
                    onClick={() => {
                      onSelect(item.path);
                      onClose();
                    }}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      item.is_git
                        ? 'bg-green-600 hover:bg-green-700 text-white'
                        : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
                    }`}
                  >
                    Select
                  </button>
                </div>
              ))}

              {items.length === 0 && !loading && (
                <div className="text-center py-8 text-slate-500">
                  No directories found
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-between bg-slate-50">
          <p className="text-sm text-slate-500">
            {isGitRepo ? 'Current directory is a Git repository' : 'Navigate to a Git repository or select any folder'}
          </p>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSelect}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              Select This Folder
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
