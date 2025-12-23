'use client';

import { useState } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface AuditResult {
  success: boolean;
  repo_name: string;
  analysis_summary: {
    total_loc: number;
    files_count: number;
    languages: string[];
    repo_health_score: number;
    tech_debt_score: number;
    complexity_avg: number;
    duplication_percent: number;
  };
  documents: { name: string; type: string }[];
  gdrive_folder_url: string | null;
  message: string;
}

export default function QuickAudit() {
  const [repoUrl, setRepoUrl] = useState('');
  const [gdriveFolderId, setGdriveFolderId] = useState('');
  const [includePdf, setIncludePdf] = useState(true);
  const [includeExcel, setIncludeExcel] = useState(true);
  const [includeMarkdown, setIncludeMarkdown] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AuditResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    if (!repoUrl.trim()) {
      setError('Please enter a repository URL');
      setLoading(false);
      return;
    }

    try {
      const res = await apiFetch(`${API_BASE}/api/quick-audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl.trim(),
          gdrive_folder_id: gdriveFolderId.trim() || null,
          include_pdf: includePdf,
          include_excel: includeExcel,
          include_markdown: includeMarkdown,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Audit failed');
      }

      const data: AuditResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audit failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    setError(null);
    setLoading(true);

    try {
      const res = await apiFetch(`${API_BASE}/api/quick-audit/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl.trim(),
          gdrive_folder_id: null,
          include_pdf: includePdf,
          include_excel: includeExcel,
          include_markdown: includeMarkdown,
        }),
      });

      if (!res.ok) {
        throw new Error('Download failed');
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = res.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename=(.+)/);
      const filename = filenameMatch ? filenameMatch[1] : 'audit_report.zip';

      // Create blob and download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
          <a href="/" className="hover:text-primary-600">Dashboard</a>
          <span>/</span>
          <span>Quick Audit</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Quick Repository Audit</h1>
        <p className="text-slate-600 mt-1">
          One-click analysis with automatic document generation.
        </p>
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Repository URL */}
          <div>
            <label htmlFor="repo_url" className="block text-sm font-medium text-slate-700 mb-2">
              Repository URL <span className="text-red-500">*</span>
            </label>
            <input
              type="url"
              id="repo_url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-lg"
              disabled={loading}
            />
            <p className="mt-1 text-sm text-slate-500">
              Public GitHub, GitLab, or any Git repository URL
            </p>
          </div>

          {/* Google Drive Folder ID (Optional) */}
          <div>
            <label htmlFor="gdrive_folder" className="block text-sm font-medium text-slate-700 mb-2">
              Google Drive Folder ID <span className="text-slate-400">(optional)</span>
            </label>
            <input
              type="text"
              id="gdrive_folder"
              value={gdriveFolderId}
              onChange={(e) => setGdriveFolderId(e.target.value)}
              placeholder="1ABC123xyz..."
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              disabled={loading}
            />
            <p className="mt-1 text-sm text-slate-500">
              Documents will be uploaded to this folder (requires server-side Google API setup)
            </p>
          </div>

          {/* Document Options */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Include Documents
            </label>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includePdf}
                  onChange={(e) => setIncludePdf(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  disabled={loading}
                />
                <span className="text-sm text-slate-700">PDF Report</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeExcel}
                  onChange={(e) => setIncludeExcel(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  disabled={loading}
                />
                <span className="text-sm text-slate-700">Excel Metrics</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeMarkdown}
                  onChange={(e) => setIncludeMarkdown(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  disabled={loading}
                />
                <span className="text-sm text-slate-700">Markdown Summary</span>
              </label>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Submit Buttons */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading || !repoUrl.trim()}
              className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Analyzing...
                </span>
              ) : (
                'Run Quick Audit'
              )}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              disabled={loading || !repoUrl.trim()}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Download ZIP
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="mt-8 bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{result.repo_name}</h2>
              <p className="text-sm text-slate-500">{result.message}</p>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-slate-900">{result.analysis_summary.total_loc.toLocaleString()}</div>
              <div className="text-xs text-slate-500">Lines of Code</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-slate-900">{result.analysis_summary.files_count}</div>
              <div className="text-xs text-slate-500">Files</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{result.analysis_summary.repo_health_score}/12</div>
              <div className="text-xs text-slate-500">Health Score</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-orange-600">{result.analysis_summary.tech_debt_score}/15</div>
              <div className="text-xs text-slate-500">Tech Debt</div>
            </div>
          </div>

          {/* Languages */}
          {result.analysis_summary.languages.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-slate-700 mb-2">Languages</h3>
              <div className="flex flex-wrap gap-2">
                {result.analysis_summary.languages.map((lang) => (
                  <span key={lang} className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm">
                    {lang}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Generated Documents */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-slate-700 mb-2">Generated Documents</h3>
            <div className="flex flex-wrap gap-2">
              {result.documents.map((doc) => (
                <span key={doc.name} className="px-3 py-1 bg-slate-100 text-slate-700 rounded-lg text-sm flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {doc.name}
                </span>
              ))}
            </div>
          </div>

          {/* Google Drive Link */}
          {result.gdrive_folder_url && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M7.71 3.5L1.15 15l2.85 5 6.56-11.47L7.71 3.5zM22.85 15L16.29 3.5h-5.71l6.57 11.5h5.7zM8.73 16.5l-2.86 5h12.27l2.86-5H8.73z"/>
                </svg>
                <span className="text-sm text-blue-800">Documents uploaded to Google Drive:</span>
              </div>
              <a
                href={result.gdrive_folder_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-blue-600 hover:text-blue-700 underline text-sm"
              >
                Open in Google Drive
              </a>
            </div>
          )}

          {/* Download Button */}
          <div className="mt-6">
            <button
              onClick={handleDownload}
              disabled={loading}
              className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download All Documents (ZIP)
            </button>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-8 bg-slate-50 rounded-xl p-6">
        <h3 className="font-medium text-slate-900 mb-3">What you get:</h3>
        <ul className="space-y-2 text-sm text-slate-600">
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>PDF Report:</strong> Complete audit report with health scores, tech debt analysis</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Excel Metrics:</strong> Detailed metrics spreadsheet for further analysis</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>Markdown Summary:</strong> Quick overview for documentation</span>
          </li>
          <li className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span><strong>JSON Data:</strong> Raw analysis data for custom integrations</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
