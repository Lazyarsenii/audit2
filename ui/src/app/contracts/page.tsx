'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface ContractProfile {
  id: string;
  label: string;
  description: string;
  source_type: string;
}

interface ScoringTemplate {
  id: string;
  label: string;
  description: string;
}

interface PricingProfile {
  id: string;
  label: string;
  description: string;
  regions: string[];
}

interface ComplianceResult {
  contract_profile_id: string;
  contract_label: string;
  total_requirements: number;
  passed: number;
  partial: number;
  failed: number;
  critical_failed: number;
  blocking_failed: number;
  compliance_percent: number;
  verdict: string;
  details: Array<{
    requirement_id: string;
    title: string;
    category: string;
    metric: string;
    min_level: number;
    fact_level: number | null;
    priority: string;
    blocking: boolean;
    status: string;
    gap: number;
  }>;
  threshold_results: Record<string, boolean>;
}

export default function ContractsPage() {
  const [activeTab, setActiveTab] = useState<'contracts' | 'scoring' | 'pricing' | 'check'>('contracts');
  const [contracts, setContracts] = useState<ContractProfile[]>([]);
  const [scoringTemplates, setScoringTemplates] = useState<ScoringTemplate[]>([]);
  const [pricingProfiles, setPricingProfiles] = useState<PricingProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Compliance check state
  const [selectedContract, setSelectedContract] = useState<string>('');
  const [scores, setScores] = useState({
    documentation: 2,
    structure: 2,
    runability: 1,
    history: 1,
    architecture: 2,
    code_quality: 2,
    testing: 1,
    infrastructure: 0,
    security: 2,
  });
  const [complianceResult, setComplianceResult] = useState<ComplianceResult | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const [contractsRes, scoringRes, pricingRes] = await Promise.all([
        apiFetch(`${API_BASE}/api/contracts/profiles`),
        apiFetch(`${API_BASE}/api/contracts/scoring-templates`),
        apiFetch(`${API_BASE}/api/contracts/pricing-profiles`),
      ]);

      if (contractsRes.ok) {
        const data = await contractsRes.json();
        setContracts(data.profiles || []);
      }
      if (scoringRes.ok) {
        const data = await scoringRes.json();
        setScoringTemplates(data.profiles || []);
      }
      if (pricingRes.ok) {
        const data = await pricingRes.json();
        setPricingProfiles(data.profiles || []);
      }
    } catch (err) {
      setError('Failed to load profiles. Make sure the API server is running.');
    }
    setLoading(false);
  };

  const handleCheckCompliance = async () => {
    if (!selectedContract) return;
    setChecking(true);
    setComplianceResult(null);

    try {
      const res = await apiFetch(`${API_BASE}/api/contracts/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract_profile_id: selectedContract,
          repo_health: {
            documentation: scores.documentation,
            structure: scores.structure,
            runability: scores.runability,
            history: scores.history,
            total: scores.documentation + scores.structure + scores.runability + scores.history,
          },
          tech_debt: {
            architecture: scores.architecture,
            code_quality: scores.code_quality,
            testing: scores.testing,
            infrastructure: scores.infrastructure,
            security: scores.security,
            total: scores.architecture + scores.code_quality + scores.testing + scores.infrastructure + scores.security,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setComplianceResult(data);
      } else {
        setError('Failed to check compliance');
      }
    } catch (err) {
      setError('Failed to connect to API');
    }
    setChecking(false);
  };

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'COMPLIANT':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'PARTIAL':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'NON_COMPLIANT':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return 'text-green-600';
      case 'partial':
        return 'text-amber-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-slate-400';
    }
  };

  const renderContractsTab = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-slate-900">Contract Profiles</h2>
        <span className="text-sm text-slate-500">{contracts.length} profiles</span>
      </div>
      {contracts.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          No contract profiles found. Add YAML files to profiles/contract/
        </div>
      ) : (
        <div className="grid gap-4">
          {contracts.map((contract) => (
            <div
              key={contract.id}
              className="bg-white rounded-lg border border-slate-200 p-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-slate-900">{contract.label}</h3>
                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
                  {contract.source_type}
                </span>
              </div>
              <p className="text-sm text-slate-600 mb-3">{contract.description}</p>
              <div className="flex items-center gap-2">
                <code className="text-xs bg-slate-100 px-2 py-1 rounded">{contract.id}</code>
                <button
                  onClick={() => {
                    setSelectedContract(contract.id);
                    setActiveTab('check');
                  }}
                  className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                >
                  Check Compliance
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderScoringTab = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-slate-900">Scoring Templates</h2>
        <span className="text-sm text-slate-500">{scoringTemplates.length} templates</span>
      </div>
      {scoringTemplates.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          No scoring templates found. Add YAML files to profiles/scoring/
        </div>
      ) : (
        <div className="grid gap-4">
          {scoringTemplates.map((template) => (
            <div
              key={template.id}
              className="bg-white rounded-lg border border-slate-200 p-4"
            >
              <h3 className="font-medium text-slate-900 mb-1">{template.label}</h3>
              <p className="text-sm text-slate-600 mb-2">{template.description}</p>
              <code className="text-xs bg-slate-100 px-2 py-1 rounded">{template.id}</code>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderPricingTab = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-slate-900">Pricing Profiles</h2>
        <span className="text-sm text-slate-500">{pricingProfiles.length} profiles</span>
      </div>
      {pricingProfiles.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          No pricing profiles found. Add YAML files to profiles/pricing/
        </div>
      ) : (
        <div className="grid gap-4">
          {pricingProfiles.map((profile) => (
            <div
              key={profile.id}
              className="bg-white rounded-lg border border-slate-200 p-4"
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-slate-900">{profile.label}</h3>
                <div className="flex gap-1">
                  {profile.regions?.map((region) => (
                    <span
                      key={region}
                      className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                    >
                      {region}
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-sm text-slate-600 mb-2">{profile.description}</p>
              <code className="text-xs bg-slate-100 px-2 py-1 rounded">{profile.id}</code>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderCheckTab = () => (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-900">Compliance Check</h2>

      {/* Contract Selection */}
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Select Contract Profile
        </label>
        <select
          value={selectedContract}
          onChange={(e) => setSelectedContract(e.target.value)}
          className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
        >
          <option value="">-- Select a contract --</option>
          {contracts.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      {/* Score Inputs */}
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <h3 className="font-medium text-slate-900 mb-4">Enter Scores</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Object.entries(scores).map(([key, value]) => (
            <div key={key}>
              <label className="block text-sm text-slate-600 mb-1 capitalize">
                {key.replace('_', ' ')}
              </label>
              <input
                type="number"
                min="0"
                max="3"
                value={value}
                onChange={(e) =>
                  setScores((s) => ({ ...s, [key]: parseInt(e.target.value) || 0 }))
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-slate-200 flex justify-between text-sm">
          <span className="text-slate-600">
            Repo Health: {scores.documentation + scores.structure + scores.runability + scores.history}/12
          </span>
          <span className="text-slate-600">
            Tech Debt: {scores.architecture + scores.code_quality + scores.testing + scores.infrastructure + scores.security}/15
          </span>
        </div>
      </div>

      {/* Check Button */}
      <button
        onClick={handleCheckCompliance}
        disabled={!selectedContract || checking}
        className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium"
      >
        {checking ? 'Checking...' : 'Check Compliance'}
      </button>

      {/* Results */}
      {complianceResult && (
        <div className="space-y-4">
          {/* Summary */}
          <div className={`rounded-lg border p-4 ${getVerdictColor(complianceResult.verdict)}`}>
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-semibold text-lg">{complianceResult.verdict}</h3>
                <p className="text-sm opacity-80">{complianceResult.contract_label}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">{complianceResult.compliance_percent}%</div>
                <div className="text-sm opacity-80">compliance</div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{complianceResult.passed}</div>
              <div className="text-sm text-slate-600">Passed</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
              <div className="text-2xl font-bold text-amber-600">{complianceResult.partial}</div>
              <div className="text-sm text-slate-600">Partial</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
              <div className="text-2xl font-bold text-red-600">{complianceResult.failed}</div>
              <div className="text-sm text-slate-600">Failed</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
              <div className="text-2xl font-bold text-red-800">{complianceResult.blocking_failed}</div>
              <div className="text-sm text-slate-600">Blocking</div>
            </div>
          </div>

          {/* Details */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-medium text-slate-900 mb-4">Requirements Details</h3>
            <div className="space-y-2">
              {complianceResult.details.map((req) => (
                <div
                  key={req.requirement_id}
                  className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${getStatusColor(req.status)}`}>
                        {req.status === 'passed' ? '[PASS]' : req.status === 'partial' ? '[PARTIAL]' : '[FAIL]'}
                      </span>
                      <span className="text-slate-900">{req.title}</span>
                      {req.blocking && (
                        <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
                          BLOCKING
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {req.category} | {req.metric} | Required: {req.min_level}, Actual: {req.fact_level ?? 'N/A'}
                    </div>
                  </div>
                  <div className="text-sm">
                    <span className={`px-2 py-1 rounded ${
                      req.priority === 'critical' ? 'bg-red-100 text-red-700' :
                      req.priority === 'high' ? 'bg-amber-100 text-amber-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {req.priority}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Contracts & Profiles</h1>
        <p className="text-slate-600">
          Manage contract requirements, scoring templates, and pricing profiles.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 p-1 rounded-lg">
        {[
          { id: 'contracts', label: 'Contracts' },
          { id: 'scoring', label: 'Scoring' },
          { id: 'pricing', label: 'Pricing' },
          { id: 'check', label: 'Compliance Check' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
          <button onClick={loadProfiles} className="ml-4 underline">
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      ) : (
        <>
          {activeTab === 'contracts' && renderContractsTab()}
          {activeTab === 'scoring' && renderScoringTab()}
          {activeTab === 'pricing' && renderPricingTab()}
          {activeTab === 'check' && renderCheckTab()}
        </>
      )}
    </div>
  );
}
