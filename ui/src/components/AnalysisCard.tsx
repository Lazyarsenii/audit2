'use client';

import Link from 'next/link';
import { Analysis } from '@/types/analysis';
import { StatusBadge } from './StatusBadge';
import { ComplexityBadge } from './ComplexityBadge';
import { ProductLevelBadge } from './ProductLevelBadge';
import { ScoreBar } from './ScoreBar';

interface AnalysisCardProps {
  analysis: Analysis;
}

export function AnalysisCard({ analysis }: AnalysisCardProps) {
  const repoName = analysis.repo_name || extractRepoName(analysis.repo_url);
  const isCompleted = analysis.status === 'completed';

  return (
    <Link href={`/analysis/${analysis.analysis_id}`}>
      <div className="bg-white rounded-xl border border-slate-200 p-6 card-hover cursor-pointer">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <svg
                className="w-5 h-5 text-slate-400 flex-shrink-0"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              <h3 className="text-lg font-semibold text-slate-900 truncate">
                {repoName}
              </h3>
            </div>
            <p className="text-sm text-slate-500 truncate">{analysis.repo_url}</p>
            {analysis.branch && (
              <p className="text-xs text-slate-400 mt-1">
                Branch: <code className="bg-slate-100 px-1 rounded">{analysis.branch}</code>
              </p>
            )}
          </div>
          <StatusBadge status={analysis.status} />
        </div>

        {/* Completed Analysis Details */}
        {isCompleted && analysis.repo_health && analysis.tech_debt && (
          <>
            {/* Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              {analysis.product_level && (
                <ProductLevelBadge level={analysis.product_level} />
              )}
              {analysis.complexity && (
                <ComplexityBadge complexity={analysis.complexity} />
              )}
            </div>

            {/* Scores */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="space-y-2">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Repo Health
                </div>
                <ScoreBar
                  score={analysis.repo_health.total}
                  maxScore={analysis.repo_health.max_possible}
                  label=""
                  showValue={true}
                />
              </div>
              <div className="space-y-2">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  Tech Debt
                </div>
                <ScoreBar
                  score={analysis.tech_debt.total}
                  maxScore={analysis.tech_debt.max_possible}
                  label=""
                  showValue={true}
                />
              </div>
            </div>

            {/* Cost Summary */}
            {analysis.cost_estimates && (
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                  Estimated Cost
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-slate-500">EU:</span>{' '}
                    <span className="font-medium text-slate-900">
                      {analysis.cost_estimates.cost.eu.formatted}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">UA:</span>{' '}
                    <span className="font-medium text-slate-900">
                      {analysis.cost_estimates.cost.ua.formatted}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  ~{Math.round(analysis.cost_estimates.hours.typical.total)}h typical
                </div>
              </div>
            )}
          </>
        )}

        {/* Running/Queued State */}
        {(analysis.status === 'running' || analysis.status === 'queued') && (
          <div className="flex items-center justify-center py-8">
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2" />
              <span className="text-sm text-slate-500">
                {analysis.status === 'running' ? 'Analyzing...' : 'Queued'}
              </span>
            </div>
          </div>
        )}

        {/* Failed State */}
        {analysis.status === 'failed' && (
          <div className="bg-red-50 rounded-lg p-3 text-sm text-red-700">
            {analysis.error_message || 'Analysis failed'}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100 text-xs text-slate-400">
          <span>
            {new Date(analysis.created_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          <span className="text-primary-600 font-medium">View Details →</span>
        </div>
      </div>
    </Link>
  );
}

function extractRepoName(url: string): string {
  try {
    const parts = url.replace(/\.git$/, '').split('/');
    return parts[parts.length - 1] || 'Unknown';
  } catch {
    return 'Unknown';
  }
}
