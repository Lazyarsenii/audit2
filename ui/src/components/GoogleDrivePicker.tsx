'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface DriveItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  mimeType: string;
  size?: number;
  modifiedTime?: string;
}

interface GoogleDrivePickerProps {
  onSelect: (item: DriveItem) => void;
  onError: (error: string) => void;
}

export default function GoogleDrivePicker({ onSelect, onError }: GoogleDrivePickerProps) {
  const [items, setItems] = useState<DriveItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentFolder, setCurrentFolder] = useState<string | null>(null);
  const [folderStack, setFolderStack] = useState<{ id: string | null; name: string }[]>([
    { id: null, name: 'Root' }
  ]);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (configured) {
      loadFolder(currentFolder);
    }
  }, [currentFolder, configured]);

  const checkStatus = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/gdrive/status`);
      const data = await res.json();
      setConfigured(data.configured);
      if (!data.configured) {
        onError(data.message);
        setLoading(false);
      }
    } catch {
      setConfigured(false);
      onError('Failed to check Google Drive status');
      setLoading(false);
    }
  };

  const loadFolder = async (folderId: string | null) => {
    setLoading(true);
    try {
      const url = folderId
        ? `${API_BASE}/api/gdrive/list?folder_id=${folderId}`
        : `${API_BASE}/api/gdrive/list`;
      const res = await apiFetch(url);
      if (!res.ok) {
        throw new Error('Failed to load folder');
      }
      const data = await res.json();
      setItems(data.items);
    } catch {
      onError('Failed to load Google Drive folder');
    } finally {
      setLoading(false);
    }
  };

  const navigateToFolder = (item: DriveItem) => {
    setFolderStack([...folderStack, { id: item.id, name: item.name }]);
    setCurrentFolder(item.id);
    setSearchQuery('');
  };

  const navigateBack = (index: number) => {
    const newStack = folderStack.slice(0, index + 1);
    setFolderStack(newStack);
    setCurrentFolder(newStack[newStack.length - 1].id);
    setSearchQuery('');
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadFolder(currentFolder);
      return;
    }
    setSearching(true);
    try {
      const url = currentFolder
        ? `${API_BASE}/api/gdrive/search?query=${encodeURIComponent(searchQuery)}&folder_id=${currentFolder}`
        : `${API_BASE}/api/gdrive/search?query=${encodeURIComponent(searchQuery)}`;
      const res = await apiFetch(url);
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setItems(data.items);
    } catch {
      onError('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  if (configured === false) {
    return (
      <div className="border border-amber-200 bg-amber-50 rounded-lg p-6 text-center">
        <svg className="w-12 h-12 text-amber-500 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 className="font-medium text-amber-800 mb-1">Google Drive Not Configured</h3>
        <p className="text-sm text-amber-600">
          Contact administrator to set up Google Drive integration.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      {/* Breadcrumb */}
      <div className="bg-slate-50 px-4 py-2 border-b border-slate-200 flex items-center gap-2 overflow-x-auto">
        {folderStack.map((folder, index) => (
          <div key={index} className="flex items-center">
            {index > 0 && <span className="text-slate-400 mx-1">/</span>}
            <button
              type="button"
              onClick={() => navigateBack(index)}
              className={`text-sm hover:text-primary-600 whitespace-nowrap ${
                index === folderStack.length - 1 ? 'font-medium text-slate-900' : 'text-slate-600'
              }`}
            >
              {folder.name}
            </button>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-slate-200 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search files..."
            className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <button
            type="button"
            onClick={handleSearch}
            disabled={searching}
            className="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 disabled:opacity-50"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {/* File List */}
      <div className="max-h-80 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <p>No files or folders found</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr>
                <th className="px-4 py-2 font-medium text-slate-600">Name</th>
                <th className="px-4 py-2 font-medium text-slate-600 w-24">Size</th>
                <th className="px-4 py-2 font-medium text-slate-600 w-28">Modified</th>
                <th className="px-4 py-2 w-20"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      {item.type === 'folder' ? (
                        <svg className="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      )}
                      {item.type === 'folder' ? (
                        <button
                          type="button"
                          onClick={() => navigateToFolder(item)}
                          className="text-slate-900 hover:text-primary-600 font-medium truncate max-w-[200px]"
                        >
                          {item.name}
                        </button>
                      ) : (
                        <span className="text-slate-700 truncate max-w-[200px]">{item.name}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-slate-500">{formatSize(item.size)}</td>
                  <td className="px-4 py-2 text-slate-500">{formatDate(item.modifiedTime)}</td>
                  <td className="px-4 py-2">
                    {item.type === 'folder' && (
                      <button
                        type="button"
                        onClick={() => onSelect(item)}
                        className="px-3 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
                      >
                        Select
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Help text */}
      <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 text-xs text-slate-500">
        Select a folder to analyze. Click folder name to navigate, or click "Select" to choose.
      </div>
    </div>
  );
}
