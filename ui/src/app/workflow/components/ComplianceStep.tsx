'use client';

import React, { useState } from 'react';
import { AlertCircle, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

interface ComplianceProfile {
  id: string;
  label: string;
  requirements: string[];
}

interface ComplianceComponent {
  id: string;
  name: string;
  enabled: boolean;
  source: string;
}

interface ComplianceData {
  verdict: 'COMPLIANT' | 'PARTIAL' | 'NON_COMPLIANT';
  compliance_percent: number;
  passed: number;
  failed: number;
  critical_failed: number;
}

interface ComplianceStepProps {
  complianceProfile: string;
  complianceProfiles: ComplianceProfile[];
  complianceComponents: ComplianceComponent[];
  complianceData: ComplianceData | null;
  customPolicyText: string;
  loading: boolean;
  onProfileChange: (profileId: string) => void;
  onComponentToggle: (id: string) => void;
  onAddCustomPolicy: (text: string) => void;
  onCustomPolicyTextChange: (text: string) => void;
  onCheckCompliance: () => void;
  onBack: () => void;
  onContinue: () => void;
}

const ComplianceStep: React.FC<ComplianceStepProps> = ({
  complianceProfile,
  complianceProfiles,
  complianceComponents,
  complianceData,
  customPolicyText,
  loading,
  onProfileChange,
  onComponentToggle,
  onAddCustomPolicy,
  onCustomPolicyTextChange,
  onCheckCompliance,
  onBack,
  onContinue,
}) => {
  const [expandedProfile, setExpandedProfile] = useState<string | null>(
    complianceProfile || null
  );

  const currentProfile = complianceProfiles.find(p => p.id === complianceProfile);

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'COMPLIANT':
        return 'bg-green-50 border-green-200';
      case 'PARTIAL':
        return 'bg-yellow-50 border-yellow-200';
      case 'NON_COMPLIANT':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getVerdictTextColor = (verdict: string) => {
    switch (verdict) {
      case 'COMPLIANT':
        return 'text-green-700';
      case 'PARTIAL':
        return 'text-yellow-700';
      case 'NON_COMPLIANT':
        return 'text-red-700';
      default:
        return 'text-gray-700';
    }
  };

  const getVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case 'COMPLIANT':
        return <CheckCircle className="w-6 h-6 text-green-600" />;
      case 'PARTIAL':
        return <AlertTriangle className="w-6 h-6 text-yellow-600" />;
      case 'NON_COMPLIANT':
        return <XCircle className="w-6 h-6 text-red-600" />;
      default:
        return null;
    }
  };

  const handleAddCustomPolicy = () => {
    if (customPolicyText.trim()) {
      onAddCustomPolicy(customPolicyText);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">Step 4: Policy Compliance Check</h1>
        <p className="text-gray-600">
          Verify that your repository meets compliance requirements and policies
        </p>
      </div>

      {/* Profile Selection and Check Button */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Compliance Profile
              </label>
              <select
                value={complianceProfile}
                onChange={(e) => {
                  onProfileChange(e.target.value);
                  setExpandedProfile(e.target.value);
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select a compliance profile</option>
                {complianceProfiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={onCheckCompliance}
                disabled={!complianceProfile || loading}
                className="w-full px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Checking...' : 'Run Compliance Check'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Requirements */}
      {currentProfile && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Requirements - {currentProfile.label}
          </h2>
          <div className="space-y-3">
            {currentProfile.requirements.map((requirement) => {
              const component = complianceComponents.find(c => c.name === requirement);
              return (
                <div
                  key={requirement}
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={component?.enabled || false}
                    onChange={() => {
                      if (component) {
                        onComponentToggle(component.id);
                      }
                    }}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="flex-1 text-gray-700">{requirement}</span>
                  {component && (
                    <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">
                      {component.source}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Components List */}
      {complianceComponents.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Components</h2>
          <div className="space-y-2">
            {complianceComponents.map((component) => (
              <div
                key={component.id}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={component.enabled}
                  onChange={() => onComponentToggle(component.id)}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="flex-1 text-gray-700">{component.name}</span>
                <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">
                  {component.source}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Custom Policy */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Custom Requirement</h2>
        <div className="flex flex-col gap-3">
          <textarea
            value={customPolicyText}
            onChange={(e) => onCustomPolicyTextChange(e.target.value)}
            placeholder="Enter a custom policy requirement..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
          <button
            onClick={handleAddCustomPolicy}
            disabled={!customPolicyText.trim()}
            className="px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            Add Custom Requirement
          </button>
        </div>
      </div>

      {/* Compliance Results */}
      {complianceData && (
        <div className="space-y-4">
          {/* Critical Warning */}
          {complianceData.critical_failed > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-900">Critical Issues Found</h3>
                <p className="text-sm text-red-800">
                  {complianceData.critical_failed} critical compliance failures require immediate attention.
                </p>
              </div>
            </div>
          )}

          {/* Results Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Verdict Card */}
            <div
              className={`rounded-lg border p-6 ${getVerdictColor(complianceData.verdict)}`}
            >
              <div className="flex items-center gap-3 mb-2">
                {getVerdictIcon(complianceData.verdict)}
                <h3 className="text-sm font-medium text-gray-700">Verdict</h3>
              </div>
              <p className={`text-2xl font-bold ${getVerdictTextColor(complianceData.verdict)}`}>
                {complianceData.verdict.replace('_', ' ')}
              </p>
            </div>

            {/* Compliance Percentage Card */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <CheckCircle className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-medium text-gray-700">Compliance</h3>
              </div>
              <p className="text-2xl font-bold text-blue-700">
                {complianceData.compliance_percent.toFixed(1)}%
              </p>
            </div>

            {/* Passed Card */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <h3 className="text-sm font-medium text-gray-700">Passed</h3>
              </div>
              <p className="text-2xl font-bold text-green-700">{complianceData.passed}</p>
            </div>

            {/* Failed Card */}
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <XCircle className="w-5 h-5 text-red-600" />
                <h3 className="text-sm font-medium text-gray-700">Failed</h3>
              </div>
              <p className="text-2xl font-bold text-red-700">{complianceData.failed}</p>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4 pt-6 border-t border-gray-200">
        <button
          onClick={onBack}
          className="px-6 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
        >
          Back to Audit
        </button>
        <button
          onClick={onContinue}
          disabled={!complianceData}
          className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors ml-auto"
        >
          Continue to Cost Estimation
        </button>
      </div>
    </div>
  );
};

export default ComplianceStep;
