'use client';

import { useState, useRef } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface ComparisonResult {
  contract_id: string;
  analysis_id: string | null;
  compared_at: string;
  overall_status: string;
  overall_score: number;
  work_plan: {
    status: string;
    total: number;
    on_track: number;
    at_risk: number;
    behind: number;
    details: Array<{
      activity_id: string;
      activity_name: string;
      planned_status: string;
      actual_status: string;
      status: string;
      completion_percent: number;
    }>;
  };
  budget: {
    status: string;
    planned: number;
    estimated: number;
    variance: number;
    variance_percent: number;
    details: Array<{
      category: string;
      planned_amount: number;
      estimated_amount: number;
      variance: number;
      variance_percent: number;
      status: string;
    }>;
  };
  indicators: {
    status: string;
    total: number;
    met: number;
    at_risk: number;
    not_met: number;
    details: Array<{
      indicator_id: string;
      indicator_name: string;
      target_value: number | null;
      actual_value: number | null;
      unit: string;
      achievement_percent: number | null;
      status: string;
    }>;
  };
  recommendations: string[];
  risks: string[];
}

interface ParsedContract {
  id: string;
  filename: string;
  parsed_at: string;
  contract_number: string | null;
  contract_title: string | null;
  total_budget: number | null;
  currency: string;
  work_plan: Array<{ id: string; name: string; status: string }>;
  milestones: Array<{ id: string; name: string; due_date: string | null }>;
  budget: Array<{ category: string; total: number }>;
  indicators: Array<{ id: string; name: string; target: number | null }>;
  policies: Array<{ id: string; title: string }>;
  summary: {
    activities_count: number;
    milestones_count: number;
    budget_lines_count: number;
    indicators_count: number;
    policies_count: number;
    templates_count: number;
  };
}

export default function ContractComparisonPage() {
  const [activeTab, setActiveTab] = useState<'upload' | 'parsed' | 'compare'>('upload');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedContract, setParsedContract] = useState<ParsedContract | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await apiFetch(`${API_BASE}/api/contract-parser/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();

      // Fetch full parsed contract
      const detailRes = await apiFetch(`${API_BASE}/api/contract-parser/parsed/${data.contract_id}`);
      if (detailRes.ok) {
        const parsed = await detailRes.json();
        setParsedContract(parsed);
        setActiveTab('parsed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`${API_BASE}/api/contract-parser/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (!res.ok) throw new Error('Failed to load demo');

      const data = await res.json();
      setParsedContract(data);
      setActiveTab('parsed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load demo');
    } finally {
      setLoading(false);
    }
  };

  const handleRunComparison = async () => {
    if (!parsedContract) return;

    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`${API_BASE}/api/contract-parser/compare-demo`);

      if (!res.ok) throw new Error('Comparison failed');

      const data = await res.json();
      setComparison(data);
      setActiveTab('compare');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on_track':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'at_risk':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'behind':
      case 'over_budget':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'under_budget':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'on_track':
        return (
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'at_risk':
        return (
          <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'behind':
      case 'over_budget':
        return (
          <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const renderUploadTab = () => (
    <div className="space-y-6">
      {/* Upload Area */}
      <div
        className="border-2 border-dashed border-slate-300 rounded-xl p-12 text-center hover:border-primary-500 transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          onChange={handleFileUpload}
          className="hidden"
        />
        <svg className="w-16 h-16 text-slate-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Upload Contract Document</h3>
        <p className="text-slate-600 mb-4">
          Drag and drop or click to upload PDF, DOCX, or TXT files
        </p>
        <p className="text-sm text-slate-500">
          The system will extract work plan, budget, indicators, and policies
        </p>
      </div>

      {/* Or Demo */}
      <div className="flex items-center gap-4">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-sm text-slate-500">or</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>

      {/* Demo Button */}
      <button
        onClick={handleLoadDemo}
        disabled={loading}
        className="w-full py-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium disabled:opacity-50"
      >
        {loading ? 'Loading...' : 'Load Demo Contract'}
      </button>

      {/* Capabilities */}
      <div className="bg-slate-50 rounded-xl p-6">
        <h3 className="font-semibold text-slate-900 mb-4">What gets extracted:</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { name: 'Work Plan', desc: 'Activities, tasks, schedules' },
            { name: 'Milestones', desc: 'Deliverables, payment triggers' },
            { name: 'Budget', desc: 'Line items by category' },
            { name: 'Indicators', desc: 'KPIs, performance metrics' },
            { name: 'Policies', desc: 'Requirements, compliance' },
            { name: 'Templates', desc: 'Required documents' },
          ].map((item) => (
            <div key={item.name} className="flex items-start gap-2">
              <svg className="w-5 h-5 text-green-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <div className="font-medium text-slate-900">{item.name}</div>
                <div className="text-sm text-slate-500">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderParsedTab = () => {
    if (!parsedContract) return null;

    return (
      <div className="space-y-6">
        {/* Contract Header */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">
                {parsedContract.contract_title || parsedContract.filename}
              </h2>
              {parsedContract.contract_number && (
                <p className="text-slate-600">Contract #{parsedContract.contract_number}</p>
              )}
            </div>
            {parsedContract.total_budget && (
              <div className="text-right">
                <div className="text-2xl font-bold text-slate-900">
                  {parsedContract.total_budget.toLocaleString()} {parsedContract.currency}
                </div>
                <div className="text-sm text-slate-500">Total Budget</div>
              </div>
            )}
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            {[
              { label: 'Activities', value: parsedContract.summary.activities_count },
              { label: 'Milestones', value: parsedContract.summary.milestones_count },
              { label: 'Budget Lines', value: parsedContract.summary.budget_lines_count },
              { label: 'Indicators', value: parsedContract.summary.indicators_count },
              { label: 'Policies', value: parsedContract.summary.policies_count },
              { label: 'Templates', value: parsedContract.summary.templates_count },
            ].map((stat) => (
              <div key={stat.label} className="bg-slate-50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-slate-900">{stat.value}</div>
                <div className="text-xs text-slate-600">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Work Plan */}
        {parsedContract.work_plan.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-4">Work Plan Activities</h3>
            <div className="space-y-2">
              {parsedContract.work_plan.map((activity) => (
                <div key={activity.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                    {activity.id}
                  </span>
                  <span className="flex-1 text-slate-900">{activity.name}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    activity.status === 'completed' ? 'bg-green-100 text-green-700' :
                    activity.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {activity.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Budget */}
        {parsedContract.budget.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-4">Budget Breakdown</h3>
            <div className="space-y-2">
              {parsedContract.budget.map((line, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="font-medium text-slate-900 capitalize">{line.category}</span>
                  <span className="text-slate-700">
                    {line.total.toLocaleString()} {parsedContract.currency}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Indicators */}
        {parsedContract.indicators.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-4">Performance Indicators</h3>
            <div className="space-y-2">
              {parsedContract.indicators.map((ind) => (
                <div key={ind.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                    {ind.id}
                  </span>
                  <span className="flex-1 text-slate-900">{ind.name}</span>
                  {ind.target && (
                    <span className="text-slate-600 text-sm">Target: {ind.target}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Compare Button */}
        <button
          onClick={handleRunComparison}
          disabled={loading}
          className="w-full py-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium disabled:opacity-50"
        >
          {loading ? 'Comparing...' : 'Compare with Analysis'}
        </button>
      </div>
    );
  };

  const renderCompareTab = () => {
    if (!comparison) return null;

    return (
      <div className="space-y-6">
        {/* Overall Status */}
        <div className={`rounded-xl border-2 p-6 ${getStatusColor(comparison.overall_status)}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getStatusIcon(comparison.overall_status)}
              <div>
                <h2 className="text-xl font-bold">
                  {comparison.overall_status.replace('_', ' ').toUpperCase()}
                </h2>
                <p className="text-sm opacity-80">Overall compliance status</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold">{comparison.overall_score.toFixed(0)}%</div>
              <div className="text-sm opacity-80">Score</div>
            </div>
          </div>
        </div>

        {/* Work Plan Comparison */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {getStatusIcon(comparison.work_plan.status)}
              <h3 className="font-semibold text-slate-900">Work Plan Progress</h3>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(comparison.work_plan.status)}`}>
              {comparison.work_plan.status.replace('_', ' ')}
            </span>
          </div>

          {/* Progress Bars */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{comparison.work_plan.on_track}</div>
              <div className="text-sm text-slate-600">On Track</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-600">{comparison.work_plan.at_risk}</div>
              <div className="text-sm text-slate-600">At Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{comparison.work_plan.behind}</div>
              <div className="text-sm text-slate-600">Behind</div>
            </div>
          </div>

          {/* Details */}
          <div className="space-y-2">
            {comparison.work_plan.details.slice(0, 5).map((act) => (
              <div key={act.activity_id} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                <span className="text-sm text-slate-900">{act.activity_name}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        act.status === 'on_track' ? 'bg-green-500' :
                        act.status === 'at_risk' ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${act.completion_percent}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-600 w-10">{act.completion_percent}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Budget Comparison */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {getStatusIcon(comparison.budget.status)}
              <h3 className="font-semibold text-slate-900">Budget Comparison</h3>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(comparison.budget.status)}`}>
              {comparison.budget.variance_percent > 0 ? '+' : ''}{comparison.budget.variance_percent.toFixed(1)}%
            </span>
          </div>

          {/* Budget Summary */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-slate-900">
                ${comparison.budget.planned.toLocaleString()}
              </div>
              <div className="text-xs text-slate-600">Planned Budget</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-slate-900">
                ${comparison.budget.estimated.toLocaleString()}
              </div>
              <div className="text-xs text-slate-600">Estimated Cost</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${getStatusColor(comparison.budget.status)}`}>
              <div className="text-lg font-bold">
                {comparison.budget.variance > 0 ? '+' : ''}${comparison.budget.variance.toLocaleString()}
              </div>
              <div className="text-xs opacity-80">Variance</div>
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="space-y-2">
            {comparison.budget.details.map((cat) => (
              <div key={cat.category} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                <span className="text-sm text-slate-900 capitalize">{cat.category}</span>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-600">
                    ${cat.planned_amount.toLocaleString()} vs ${cat.estimated_amount.toLocaleString()}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(cat.status)}`}>
                    {cat.variance_percent > 0 ? '+' : ''}{cat.variance_percent.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Indicators Comparison */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {getStatusIcon(comparison.indicators.status)}
              <h3 className="font-semibold text-slate-900">Indicators Achievement</h3>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(comparison.indicators.status)}`}>
              {comparison.indicators.met}/{comparison.indicators.total} met
            </span>
          </div>

          <div className="space-y-2">
            {comparison.indicators.details.map((ind) => (
              <div key={ind.indicator_id} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                <span className="text-sm text-slate-900">{ind.indicator_name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-600">
                    {ind.actual_value ?? 'N/A'} / {ind.target_value ?? 'N/A'}
                  </span>
                  {ind.achievement_percent !== null && (
                    <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(ind.status)}`}>
                      {ind.achievement_percent.toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risks & Recommendations */}
        {(comparison.risks.length > 0 || comparison.recommendations.length > 0) && (
          <div className="grid md:grid-cols-2 gap-6">
            {comparison.risks.length > 0 && (
              <div className="bg-red-50 rounded-xl border border-red-200 p-6">
                <h3 className="font-semibold text-red-900 mb-4">Identified Risks</h3>
                <ul className="space-y-2">
                  {comparison.risks.map((risk, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-red-800">
                      <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {comparison.recommendations.length > 0 && (
              <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
                <h3 className="font-semibold text-blue-900 mb-4">Recommendations</h3>
                <ul className="space-y-2">
                  {comparison.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-blue-800">
                      <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Contract Comparison</h1>
        <p className="text-slate-600">
          Upload contract documents and compare with analysis results
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 p-1 rounded-lg">
        {[
          { id: 'upload', label: 'Upload Contract' },
          { id: 'parsed', label: 'Parsed Data', disabled: !parsedContract },
          { id: 'compare', label: 'Comparison', disabled: !comparison },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => !tab.disabled && setActiveTab(tab.id as typeof activeTab)}
            disabled={tab.disabled}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-slate-900 shadow-sm'
                : tab.disabled
                ? 'text-slate-400 cursor-not-allowed'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Content */}
      {activeTab === 'upload' && renderUploadTab()}
      {activeTab === 'parsed' && renderParsedTab()}
      {activeTab === 'compare' && renderCompareTab()}
    </div>
  );
}
