'use client';

import React from 'react';

// Inline icons to avoid lucide-react dependency issues
interface IconProps {
  className?: string;
  style?: React.CSSProperties;
}

const AlertCircleIcon = ({ className, style }: IconProps) => (
  <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CheckCircleIcon = ({ className, style }: IconProps) => (
  <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const TrendingUpIcon = ({ className, style }: IconProps) => (
  <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);

const ListChecksIcon = ({ className, style }: IconProps) => (
  <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
);

interface ReadinessDataType {
  readiness_score: number;
  readiness_level: string;
  passed_checks: number;
  blockers_count: number;
  summary: string;
  next_steps?: string[];
}

interface ReadinessStepProps {
  readinessData: ReadinessDataType | null;
  loading: boolean;
  onViewAuditResults: () => void;
  onRunReadinessCheck: () => void;
}

const ReadinessStep: React.FC<ReadinessStepProps> = ({
  readinessData,
  loading,
  onViewAuditResults,
  onRunReadinessCheck,
}) => {
  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'var(--color-success, #10b981)';
    if (score >= 60) return 'var(--color-warning, #f59e0b)';
    return 'var(--color-danger, #ef4444)';
  };

  const getScoreBgClass = (score: number): string => {
    if (score >= 80) return 'bg-green-50 border-green-200';
    if (score >= 60) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
  };

  const getScoreTextClass = (score: number): string => {
    if (score >= 80) return 'text-green-700';
    if (score >= 60) return 'text-yellow-700';
    return 'text-red-700';
  };

  const getStatusBadgeClass = (level: string): string => {
    const levelLower = level.toLowerCase();
    if (levelLower === 'ready' || levelLower === 'approved') {
      return 'bg-green-100 text-green-800';
    }
    if (levelLower === 'warning' || levelLower === 'needs_review') {
      return 'bg-yellow-100 text-yellow-800';
    }
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="w-full">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-900" style={{ color: 'var(--text-primary, #1e293b)' }}>
          Step 2: Audit Readiness Check
        </h2>
        <p className="text-slate-600 mt-2" style={{ color: 'var(--text-secondary, #64748b)' }}>
          Evaluate your repository's preparedness for comprehensive analysis
        </p>
      </div>

      {/* No Data State */}
      {!readinessData && (
        <div
          className="rounded-lg border-2 border-dashed p-8 text-center"
          style={{
            borderColor: 'var(--border-color, #cbd5e1)',
            backgroundColor: 'var(--bg-secondary, #f8fafc)',
          }}
        >
          <CheckCircleIcon className="mx-auto mb-4 h-12 w-12 text-slate-400" />
          <p className="text-slate-600" style={{ color: 'var(--text-secondary, #64748b)' }}>
            Readiness check will run automatically after analysis completes.
          </p>
          <button
            onClick={onRunReadinessCheck}
            disabled={loading}
            className="mt-4 px-4 py-2 rounded-lg font-medium transition-all"
            style={{
              backgroundColor: loading ? 'var(--bg-tertiary, #e2e8f0)' : 'var(--color-primary, #3b82f6)',
              color: loading ? 'var(--text-tertiary, #94a3b8)' : '#ffffff',
              opacity: loading ? 0.5 : 1,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Checking...' : 'Run Readiness Check Now'}
          </button>
        </div>
      )}

      {/* Data Present State */}
      {readinessData && (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Score Card */}
            <div
              className={`rounded-lg border-2 p-6 ${getScoreBgClass(readinessData.readiness_score)}`}
              style={{
                borderColor: getScoreColor(readinessData.readiness_score),
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-600" style={{ color: 'var(--text-secondary, #64748b)' }}>
                  Readiness Score
                </span>
                <TrendingUpIcon className="h-5 w-5" style={{ color: getScoreColor(readinessData.readiness_score) }} />
              </div>
              <div className={`text-3xl font-bold ${getScoreTextClass(readinessData.readiness_score)}`}>
                {readinessData.readiness_score}%
              </div>
              <p className="text-xs text-slate-500 mt-1" style={{ color: 'var(--text-tertiary, #94a3b8)' }}>
                Overall readiness
              </p>
            </div>

            {/* Status Card */}
            <div
              className="rounded-lg border-2 p-6"
              style={{
                backgroundColor: 'var(--bg-secondary, #f8fafc)',
                borderColor: 'var(--border-color, #cbd5e1)',
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-600" style={{ color: 'var(--text-secondary, #64748b)' }}>
                  Status
                </span>
                <AlertCircleIcon className="h-5 w-5 text-slate-600" />
              </div>
              <div className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${getStatusBadgeClass(readinessData.readiness_level)}`}>
                {readinessData.readiness_level}
              </div>
              <p className="text-xs text-slate-500 mt-3" style={{ color: 'var(--text-tertiary, #94a3b8)' }}>
                Current readiness level
              </p>
            </div>

            {/* Passed Checks Card */}
            <div
              className="rounded-lg border-2 p-6"
              style={{
                backgroundColor: 'var(--bg-secondary, #f8fafc)',
                borderColor: 'var(--border-color, #cbd5e1)',
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-600" style={{ color: 'var(--text-secondary, #64748b)' }}>
                  Passed Checks
                </span>
                <CheckCircleIcon className="h-5 w-5 text-green-600" />
              </div>
              <div className="text-3xl font-bold text-slate-900">{readinessData.passed_checks}</div>
              <p className="text-xs text-slate-500 mt-1" style={{ color: 'var(--text-tertiary, #94a3b8)' }}>
                Checks passed
              </p>
            </div>

            {/* Blockers Card */}
            <div
              className="rounded-lg border-2 p-6"
              style={{
                backgroundColor: 'var(--bg-secondary, #f8fafc)',
                borderColor: 'var(--border-color, #cbd5e1)',
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-600" style={{ color: 'var(--text-secondary, #64748b)' }}>
                  Blockers
                </span>
                <AlertCircleIcon className={`h-5 w-5 ${readinessData.blockers_count > 0 ? 'text-red-600' : 'text-green-600'}`} />
              </div>
              <div className={`text-3xl font-bold ${readinessData.blockers_count > 0 ? 'text-red-700' : 'text-slate-900'}`}>
                {readinessData.blockers_count}
              </div>
              <p className="text-xs text-slate-500 mt-1" style={{ color: 'var(--text-tertiary, #94a3b8)' }}>
                Critical issues
              </p>
            </div>
          </div>

          {/* Summary Section */}
          <div
            className="rounded-lg border-2 p-6"
            style={{
              backgroundColor: 'var(--bg-secondary, #f8fafc)',
              borderColor: 'var(--border-color, #cbd5e1)',
            }}
          >
            <h3 className="text-lg font-semibold text-slate-900 mb-3" style={{ color: 'var(--text-primary, #1e293b)' }}>
              Summary
            </h3>
            <p className="text-slate-700 leading-relaxed" style={{ color: 'var(--text-secondary, #64748b)' }}>
              {readinessData.summary}
            </p>
          </div>

          {/* Next Steps Section */}
          {readinessData.next_steps && readinessData.next_steps.length > 0 && (
            <div
              className="rounded-lg border-2 p-6"
              style={{
                backgroundColor: '#eff6ff',
                borderColor: 'var(--color-primary, #3b82f6)',
              }}
            >
              <div className="flex items-center mb-4">
                <ListChecksIcon className="h-5 w-5 mr-3" style={{ color: 'var(--color-primary, #3b82f6)' }} />
                <h3 className="text-lg font-semibold" style={{ color: 'var(--color-primary, #3b82f6)' }}>
                  Recommended Next Steps
                </h3>
              </div>
              <ul className="space-y-3">
                {readinessData.next_steps.map((step, index) => (
                  <li key={index} className="flex items-start">
                    <div
                      className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mr-3 mt-0.5 font-semibold text-white text-sm"
                      style={{ backgroundColor: 'var(--color-primary, #3b82f6)' }}
                    >
                      {index + 1}
                    </div>
                    <span className="text-slate-700 pt-0.5" style={{ color: 'var(--text-secondary, #64748b)' }}>
                      {step}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-6">
            <button
              onClick={onViewAuditResults}
              className="flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all hover:opacity-90 active:scale-95"
              style={{
                backgroundColor: 'var(--color-primary, #3b82f6)',
              }}
            >
              View Audit Results
            </button>
            <button
              onClick={onRunReadinessCheck}
              disabled={loading}
              className="flex-1 px-6 py-3 rounded-lg font-semibold border-2 transition-all hover:bg-opacity-5 active:scale-95"
              style={{
                borderColor: 'var(--border-color, #cbd5e1)',
                color: loading ? 'var(--text-tertiary, #94a3b8)' : 'var(--text-primary, #1e293b)',
                opacity: loading ? 0.5 : 1,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Rechecking...' : 'Recheck Readiness'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReadinessStep;
