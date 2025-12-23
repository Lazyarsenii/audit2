'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE, apiFetch } from '@/lib/api';
import FolderUpload from '@/components/FolderUpload';
import GoogleDrivePicker from '@/components/GoogleDrivePicker';
import GitHubRepoPicker from '@/components/GitHubRepoPicker';

type SourceType = 'url' | 'upload' | 'gdrive';

interface DriveItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  mimeType: string;
}

interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  url: string;
  clone_url: string;
  private: boolean;
  default_branch: string;
}

export default function NewAnalysis() {
  const router = useRouter();
  const [sourceType, setSourceType] = useState<SourceType>('url');
  const [repoUrl, setRepoUrl] = useState('');
  const [selectedGitHubRepo, setSelectedGitHubRepo] = useState<GitHubRepo | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);
  const [uploadInfo, setUploadInfo] = useState<{ uploadId: string; fileCount: number } | null>(null);
  const [selectedDriveFolder, setSelectedDriveFolder] = useState<DriveItem | null>(null);
  const [branch, setBranch] = useState('');
  const [regionMode, setRegionMode] = useState('EU_UA');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showManualInput, setShowManualInput] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    let targetUrl: string | null = null;
    let sourceTypeApi: string = 'github';

    if (sourceType === 'url') {
      targetUrl = selectedGitHubRepo?.clone_url || repoUrl;
      sourceTypeApi = 'github';
      // Use selected repo's branch if available
      if (selectedGitHubRepo && !branch) {
        setBranch(selectedGitHubRepo.default_branch);
      }
    } else if (sourceType === 'upload') {
      targetUrl = uploadedPath;
      sourceTypeApi = 'local';
    } else if (sourceType === 'gdrive') {
      targetUrl = selectedDriveFolder?.id || null;
      sourceTypeApi = 'gdrive';
    }

    if (!targetUrl) {
      const messages: Record<SourceType, string> = {
        url: 'Please enter a repository URL',
        upload: 'Please upload a folder or ZIP file first',
        gdrive: 'Please select a Google Drive folder',
      };
      setError(messages[sourceType]);
      setLoading(false);
      return;
    }

    try {
      const res = await apiFetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: targetUrl,
          branch: branch || undefined,
          region_mode: regionMode,
          source_type: sourceTypeApi,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to start analysis');
      }

      const data = await res.json();
      router.push(`/analysis/${data.analysis_id}`);
    } catch {
      setError('Failed to start analysis. Please check the input and try again.');
      setLoading(false);
    }
  };

  const handleUploadComplete = (result: { uploadId: string; path: string; fileCount: number }) => {
    setUploadedPath(result.path);
    setUploadInfo({ uploadId: result.uploadId, fileCount: result.fileCount });
    setError(null);
  };

  const clearUpload = () => {
    setUploadedPath(null);
    setUploadInfo(null);
  };

  const handleDriveFolderSelect = (item: DriveItem) => {
    setSelectedDriveFolder(item);
    setError(null);
  };

  const clearDriveSelection = () => {
    setSelectedDriveFolder(null);
  };

  const handleGitHubRepoSelect = (repo: GitHubRepo) => {
    setSelectedGitHubRepo(repo);
    setRepoUrl(repo.clone_url);
    setBranch(repo.default_branch);
    setError(null);
  };

  const clearGitHubSelection = () => {
    setSelectedGitHubRepo(null);
    setRepoUrl('');
    setBranch('');
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
          <a href="/" className="hover:text-primary-600">Dashboard</a>
          <span>/</span>
          <span>New Analysis</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">New Repository Analysis</h1>
        <p className="text-slate-600 mt-1">
          Analyze repository health, technical debt, and estimate costs.
        </p>
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Source Type Tabs */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Repository Source
            </label>
            <div className="flex border border-slate-200 rounded-lg p-1 bg-slate-50">
              <button
                type="button"
                onClick={() => setSourceType('url')}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-all ${
                  sourceType === 'url'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Git URL
              </button>
              <button
                type="button"
                onClick={() => setSourceType('gdrive')}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-all ${
                  sourceType === 'gdrive'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M7.71 3.5L1.15 15l2.85 5 6.56-11.47L7.71 3.5zM22.85 15L16.29 3.5h-5.71l6.57 11.5h5.7zM8.73 16.5l-2.86 5h12.27l2.86-5H8.73z"/>
                </svg>
                Google Drive
              </button>
              <button
                type="button"
                onClick={() => setSourceType('upload')}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-all ${
                  sourceType === 'upload'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload
              </button>
            </div>
          </div>

          {/* Git URL Input */}
          {sourceType === 'url' && (
            <div>
              {selectedGitHubRepo ? (
                /* Selected repo display */
                <div className="border border-green-200 bg-green-50 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-green-600" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-green-800">{selectedGitHubRepo.full_name}</p>
                        <p className="text-sm text-green-600">
                          {selectedGitHubRepo.private ? 'Private' : 'Public'} • {selectedGitHubRepo.default_branch}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={clearGitHubSelection}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              ) : showManualInput ? (
                /* Manual URL input */
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label htmlFor="repo_url" className="block text-sm font-medium text-slate-700">
                      Repository URL <span className="text-red-500">*</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowManualInput(false)}
                      className="text-xs text-primary-600 hover:text-primary-700"
                    >
                      Back to list
                    </button>
                  </div>
                  <input
                    type="url"
                    id="repo_url"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <p className="mt-1 text-sm text-slate-500">
                    Enter the HTTPS URL of any Git repository.
                  </p>
                </div>
              ) : (
                /* GitHub repo picker */
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-slate-700">
                      Select Repository
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowManualInput(true)}
                      className="text-xs text-primary-600 hover:text-primary-700"
                    >
                      Enter URL manually
                    </button>
                  </div>
                  <GitHubRepoPicker
                    onSelect={handleGitHubRepoSelect}
                    onError={setError}
                  />
                </div>
              )}
            </div>
          )}

          {/* Google Drive Picker */}
          {sourceType === 'gdrive' && (
            <div>
              {selectedDriveFolder ? (
                <div className="border border-green-200 bg-green-50 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-green-600" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M7.71 3.5L1.15 15l2.85 5 6.56-11.47L7.71 3.5zM22.85 15L16.29 3.5h-5.71l6.57 11.5h5.7zM8.73 16.5l-2.86 5h12.27l2.86-5H8.73z"/>
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-green-800">Folder selected</p>
                        <p className="text-sm text-green-600">
                          {selectedDriveFolder.name}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={clearDriveSelection}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              ) : (
                <GoogleDrivePicker
                  onSelect={handleDriveFolderSelect}
                  onError={setError}
                />
              )}
            </div>
          )}

          {/* Folder Upload */}
          {sourceType === 'upload' && (
            <div>
              {uploadedPath ? (
                <div className="border border-green-200 bg-green-50 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-green-800">Repository uploaded</p>
                        <p className="text-sm text-green-600">
                          {uploadInfo?.fileCount} files ready for analysis
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={clearUpload}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              ) : (
                <FolderUpload
                  onUploadComplete={handleUploadComplete}
                  onError={setError}
                />
              )}
            </div>
          )}

          {/* Branch */}
          <div>
            <label
              htmlFor="branch"
              className="block text-sm font-medium text-slate-700 mb-2"
            >
              Branch (optional)
            </label>
            <input
              type="text"
              id="branch"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <p className="mt-1 text-sm text-slate-500">
              {sourceType === 'url' ? 'Leave empty to use the default branch.' : 'Not applicable for this source type.'}
            </p>
          </div>

          {/* Region Mode */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Cost Estimation Region
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { value: 'EU_UA', label: 'EU & UA', desc: 'Both regions' },
                { value: 'EU', label: 'EU Only', desc: 'European rates' },
                { value: 'UA', label: 'UA Only', desc: 'Ukrainian rates' },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`relative flex flex-col items-center p-4 border rounded-lg cursor-pointer transition-all ${
                    regionMode === option.value
                      ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="region_mode"
                    value={option.value}
                    checked={regionMode === option.value}
                    onChange={(e) => setRegionMode(e.target.value)}
                    className="sr-only"
                  />
                  <span className="font-medium text-slate-900">{option.label}</span>
                  <span className="text-xs text-slate-500">{option.desc}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Submit */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading || (
                sourceType === 'url' ? !repoUrl :
                sourceType === 'gdrive' ? !selectedDriveFolder :
                !uploadedPath
              )}
              className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Starting Analysis...
                </span>
              ) : (
                'Start Analysis'
              )}
            </button>
            <a
              href="/"
              className="px-6 py-3 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 font-medium"
            >
              Cancel
            </a>
          </div>
        </form>
      </div>

      {/* Info */}
      <div className="mt-8 bg-slate-50 rounded-xl p-6">
        <h3 className="font-medium text-slate-900 mb-3">What will be analyzed?</h3>
        <ul className="space-y-2 text-sm text-slate-600">
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Repository Health:</strong> Documentation, structure, runability, commit history</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Technical Debt:</strong> Architecture, code quality, testing, infrastructure, security</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Product Level:</strong> R&D Spike → Prototype → Internal Tool → Platform Module → Near-Product</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Cost Estimates:</strong> Forward-looking and historical effort/cost estimates</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Task Backlog:</strong> Prioritized improvement tasks with estimates</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
