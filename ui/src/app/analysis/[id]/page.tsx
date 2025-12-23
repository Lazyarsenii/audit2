'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Analysis } from '@/types/analysis';
import { API_BASE, apiFetch } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import { ComplexityBadge } from '@/components/ComplexityBadge';
import { ProductLevelBadge } from '@/components/ProductLevelBadge';
import { ScoreBar } from '@/components/ScoreBar';
import { DocumentMatrix } from '@/components/DocumentMatrix';
import AnalysisProgress from '@/components/AnalysisProgress';

export default function AnalysisDetail() {
  const params = useParams();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'costs' | 'documents'>('overview');

  useEffect(() => {
    async function loadAnalysis() {
      try {
        const res = await apiFetch(`${API_BASE}/api/analysis/${params.id}`);
        if (res.ok) {
          const data = await res.json();
          setAnalysis(data);
        } else {
          setAnalysis(null);
          setError(res.status === 404 ? 'Analysis not found' : 'Failed to load analysis');
        }
      } catch (err) {
        setAnalysis(null);
        setError('Unable to connect to server');
        console.error('Failed to load analysis:', err);
      } finally {
        setLoading(false);
      }
    }

    loadAnalysis();
  }, [params.id]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-20">
          <div className="bg-red-50 rounded-xl border border-red-200 p-8 max-w-md mx-auto">
            <svg className="w-12 h-12 mx-auto text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h2 className="text-xl font-medium text-slate-900 mb-2">{error || 'Analysis not found'}</h2>
            <p className="text-slate-600 text-sm mb-4">
              The requested analysis could not be loaded. Please check the ID or try again.
            </p>
            <a
              href="/"
              className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
            >
              Back to Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Show progress widget when analysis is running or queued
  if (analysis.status === 'running' || analysis.status === 'queued') {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <a href="/" className="hover:text-primary-600">Dashboard</a>
            <span>/</span>
            <span>Analysis in Progress</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            {analysis.repo_name || extractRepoName(analysis.repo_url)}
          </h1>
          <p className="text-slate-500 mt-1">{analysis.repo_url}</p>
        </div>

        <AnalysisProgress
          analysisId={analysis.analysis_id}
          onComplete={() => window.location.reload()}
          onError={(err) => setError(err)}
        />

        <div className="mt-6 text-center">
          <a
            href="/"
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
          <a href="/" className="hover:text-primary-600">Dashboard</a>
          <span>/</span>
          <span>Analysis</span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-slate-900">
                {analysis.repo_name || extractRepoName(analysis.repo_url)}
              </h1>
              <StatusBadge status={analysis.status} />
            </div>
            <p className="text-slate-500">{analysis.repo_url}</p>
            {analysis.branch && (
              <p className="text-sm text-slate-400 mt-1">
                Branch: <code className="bg-slate-100 px-1 rounded">{analysis.branch}</code>
              </p>
            )}
          </div>

          {analysis.status === 'completed' && (
            <div className="flex flex-wrap gap-2">
              <a
                href={`${API_BASE}/api/analysis/${analysis.analysis_id}/export/pdf`}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-red-700 hover:bg-red-100 text-sm font-medium"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                PDF
              </a>
              <a
                href={`${API_BASE}/api/analysis/${analysis.analysis_id}/export/excel`}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-green-50 border border-green-200 rounded-lg text-green-700 hover:bg-green-100 text-sm font-medium"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Excel
              </a>
              <a
                href={`${API_BASE}/api/analysis/${analysis.analysis_id}/export/word`}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 hover:bg-blue-100 text-sm font-medium"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Word
              </a>
              <a
                href={`${API_BASE}/api/analysis/${analysis.analysis_id}/export/markdown`}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-100 text-sm font-medium"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Markdown
              </a>
            </div>
          )}
        </div>
      </div>

      {analysis.status === 'completed' && analysis.repo_health && analysis.tech_debt && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="text-sm text-slate-500 mb-2">Product Level</div>
              {analysis.product_level && (
                <ProductLevelBadge level={analysis.product_level} />
              )}
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="text-sm text-slate-500 mb-2">Complexity</div>
              {analysis.complexity && (
                <ComplexityBadge complexity={analysis.complexity} />
              )}
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="text-sm text-slate-500 mb-2">Repo Health</div>
              <div className="text-2xl font-bold text-slate-900">
                {analysis.repo_health.total}/{analysis.repo_health.max_possible}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="text-sm text-slate-500 mb-2">Tech Debt Score</div>
              <div className="text-2xl font-bold text-slate-900">
                {analysis.tech_debt.total}/{analysis.tech_debt.max_possible}
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-slate-200 mb-6">
            <nav className="flex gap-6">
              {['overview', 'tasks', 'costs', 'documents'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab as any)}
                  className={`py-3 text-sm font-medium border-b-2 -mb-px ${
                    activeTab === tab
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Repo Health */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Repository Health</h3>
                <div className="space-y-4">
                  <ScoreBar
                    score={analysis.repo_health.documentation}
                    maxScore={3}
                    label="Documentation"
                  />
                  <ScoreBar
                    score={analysis.repo_health.structure}
                    maxScore={3}
                    label="Structure"
                  />
                  <ScoreBar
                    score={analysis.repo_health.runability}
                    maxScore={3}
                    label="Runability"
                  />
                  <ScoreBar
                    score={analysis.repo_health.commit_history}
                    maxScore={3}
                    label="Commit History"
                  />
                </div>
              </div>

              {/* Tech Debt */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Technical Debt</h3>
                <div className="space-y-4">
                  <ScoreBar
                    score={analysis.tech_debt.architecture}
                    maxScore={3}
                    label="Architecture"
                  />
                  <ScoreBar
                    score={analysis.tech_debt.code_quality}
                    maxScore={3}
                    label="Code Quality"
                  />
                  <ScoreBar
                    score={analysis.tech_debt.testing}
                    maxScore={3}
                    label="Testing"
                  />
                  <ScoreBar
                    score={analysis.tech_debt.infrastructure}
                    maxScore={3}
                    label="Infrastructure"
                  />
                  <ScoreBar
                    score={analysis.tech_debt.security_deps}
                    maxScore={3}
                    label="Security & Deps"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'tasks' && analysis.tasks && (
            <div className="bg-white rounded-xl border border-slate-200">
              <div className="p-6 border-b border-slate-100">
                <h3 className="text-lg font-semibold text-slate-900">
                  Improvement Tasks ({analysis.tasks.length})
                </h3>
              </div>
              <div className="divide-y divide-slate-100">
                {analysis.tasks.map((task) => (
                  <div key={task.id} className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${
                              task.priority === 'P1'
                                ? 'bg-red-100 text-red-700'
                                : task.priority === 'P2'
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {task.priority}
                          </span>
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                            {task.category}
                          </span>
                        </div>
                        <h4 className="font-medium text-slate-900 mb-1">{task.title}</h4>
                        {task.description && (
                          <p className="text-sm text-slate-500">{task.description}</p>
                        )}
                        {task.labels.length > 0 && (
                          <div className="flex gap-1 mt-2">
                            {task.labels.map((label) => (
                              <span
                                key={label}
                                className="px-1.5 py-0.5 bg-slate-50 text-slate-500 rounded text-xs"
                              >
                                {label}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      {task.estimate_hours && (
                        <div className="text-sm text-slate-500 ml-4">
                          ~{task.estimate_hours}h
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'costs' && analysis.cost_estimates && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Forward Estimate */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">
                  Forward-Looking Estimate
                </h3>
                <div className="space-y-4">
                  <div>
                    <div className="text-sm text-slate-500 mb-2">Hours Breakdown (Typical)</div>
                    <table className="w-full text-sm">
                      <tbody>
                        {Object.entries(analysis.cost_estimates.hours.typical)
                          .filter(([k]) => k !== 'total')
                          .map(([key, value]) => (
                            <tr key={key} className="border-b border-slate-50">
                              <td className="py-2 text-slate-600 capitalize">{key}</td>
                              <td className="py-2 text-right font-medium">{Math.round(value as number)}h</td>
                            </tr>
                          ))}
                        <tr className="font-semibold">
                          <td className="py-2">Total</td>
                          <td className="py-2 text-right">
                            {Math.round(analysis.cost_estimates.hours.typical.total)}h
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div className="pt-4 border-t border-slate-100">
                    <div className="text-sm text-slate-500 mb-2">Cost Ranges</div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-50 rounded-lg p-3">
                        <div className="text-xs text-slate-500 mb-1">EU</div>
                        <div className="font-semibold text-slate-900">
                          {analysis.cost_estimates.cost.eu.formatted}
                        </div>
                      </div>
                      <div className="bg-slate-50 rounded-lg p-3">
                        <div className="text-xs text-slate-500 mb-1">UA</div>
                        <div className="font-semibold text-slate-900">
                          {analysis.cost_estimates.cost.ua.formatted}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400">
                    Tech debt multiplier: {analysis.cost_estimates.tech_debt_multiplier}x
                  </div>
                </div>
              </div>

              {/* Historical Estimate */}
              {analysis.historical_estimate && (
                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">
                    Historical Estimate
                  </h3>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-slate-500">Active Days</div>
                        <div className="text-xl font-semibold text-slate-900">
                          ~{analysis.historical_estimate.active_days}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-slate-500">Hours</div>
                        <div className="text-xl font-semibold text-slate-900">
                          {Math.round(analysis.historical_estimate.hours.min)}-
                          {Math.round(analysis.historical_estimate.hours.max)}h
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-slate-500 mb-2">Person-Months</div>
                      <div className="text-lg font-semibold text-slate-900">
                        {analysis.historical_estimate.person_months.min.toFixed(1)} -{' '}
                        {analysis.historical_estimate.person_months.max.toFixed(1)} PM
                      </div>
                    </div>

                    <div className="pt-4 border-t border-slate-100">
                      <div className="text-sm text-slate-500 mb-2">Estimated Cost</div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-50 rounded-lg p-3">
                          <div className="text-xs text-slate-500 mb-1">EU</div>
                          <div className="font-semibold text-slate-900">
                            {analysis.historical_estimate.cost.eu.formatted}
                          </div>
                        </div>
                        <div className="bg-slate-50 rounded-lg p-3">
                          <div className="text-xs text-slate-500 mb-1">UA</div>
                          <div className="font-semibold text-slate-900">
                            {analysis.historical_estimate.cost.ua.formatted}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="bg-amber-50 rounded-lg p-3 text-sm">
                      <div className="font-medium text-amber-800 mb-1">
                        Confidence: {analysis.historical_estimate.confidence}
                      </div>
                      <div className="text-amber-700">{analysis.historical_estimate.note}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Documents Tab */}
          {activeTab === 'documents' && analysis.product_level && (
            <DocumentMatrix
              productLevel={getProductLevelKey(analysis.product_level)}
              analysisId={analysis.analysis_id}
              isPlatformModule={analysis.product_level === 'Platform Module Candidate'}
              hasDonors={false}
            />
          )}
        </>
      )}
    </div>
  );
}

function getProductLevelKey(level: string): string {
  const mapping: Record<string, string> = {
    'R&D Spike': 'R&D Spike',
    'Prototype': 'Prototype',
    'Internal Tool': 'Internal Tool',
    'Platform Module Candidate': 'Platform Module Candidate',
    'Near-Product': 'Near-Product',
  };
  return mapping[level] || 'Prototype';
}

function extractRepoName(url: string): string {
  try {
    const parts = url.replace(/\.git$/, '').split('/');
    return parts[parts.length - 1] || 'Unknown';
  } catch {
    return 'Unknown';
  }
}
