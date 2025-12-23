'use client';

import React from 'react';

// Inline icons
const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const Loader2Icon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
  </svg>
);

const ArrowLeftIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
  </svg>
);

const ArrowRightIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
  </svg>
);

interface Region {
  id: string;
  name: string;
  currency: string;
}

interface Methodology {
  id: string;
  name: string;
  description?: string;
  confidence?: string;
}

interface AIEfficiencyMode {
  hours: number;
  cost: number;
  efficiency_gain?: number;
}

interface CostEstimate {
  summary?: {
    average_cost: number;
    average_hours: number;
    cost_range: {
      min: number;
      max: number;
    };
  };
  methodologies?: Array<{
    id: string;
    name: string;
    hours: number;
    cost: number;
    confidence: string;
  }>;
  ai_efficiency?: {
    pure_human?: AIEfficiencyMode;
    ai_assisted?: AIEfficiencyMode;
    hybrid?: AIEfficiencyMode;
  };
}

interface CostStepProps {
  selectedRegion: string;
  hourlyRate: number;
  regions: Region[];
  methodologiesList: Methodology[];
  costEstimate: CostEstimate | null;
  showAllMethodologies: boolean;
  loading: boolean;
  onRegionChange: (regionId: string) => void;
  onHourlyRateChange: (rate: number) => void;
  onToggleShowAll: () => void;
  onGetCostEstimate: () => void;
  onBack: () => void;
  onContinue: () => void;
}

const getConfidenceBadgeColor = (confidence: string): string => {
  switch (confidence.toLowerCase()) {
    case 'high':
      return 'bg-green-100 text-green-800 border-green-300';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 'low':
      return 'bg-gray-100 text-gray-800 border-gray-300';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300';
  }
};

export default function CostStep({
  selectedRegion,
  hourlyRate,
  regions,
  methodologiesList,
  costEstimate,
  showAllMethodologies,
  loading,
  onRegionChange,
  onHourlyRateChange,
  onToggleShowAll,
  onGetCostEstimate,
  onBack,
  onContinue,
}: CostStepProps) {
  const selectedRegionData = regions.find((r) => r.id === selectedRegion);
  const displayedMethodologies = showAllMethodologies
    ? methodologiesList
    : methodologiesList.slice(0, 9);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Step 5: Cost Estimation</h1>
        <p className="text-gray-600">Configure pricing parameters and calculate project costs</p>
      </div>

      {/* Pricing Configuration */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Pricing Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Region Dropdown */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Region
            </label>
            <div className="relative">
              <select
                value={selectedRegion}
                onChange={(e) => onRegionChange(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg appearance-none bg-white cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {regions.map((region) => (
                  <option key={region.id} value={region.id}>
                    {region.name} ({region.currency})
                  </option>
                ))}
              </select>
              <ChevronDownIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Hourly Rate Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hourly Rate ({selectedRegionData?.currency || 'USD'}/hour)
            </label>
            <input
              type="number"
              value={hourlyRate}
              onChange={(e) => onHourlyRateChange(Math.max(0, Number(e.target.value)))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter hourly rate"
              min="0"
              step="0.01"
            />
          </div>
        </div>
      </div>

      {/* Available Methodologies */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Available Methodologies</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {displayedMethodologies.map((methodology) => (
            <div
              key={methodology.id}
              className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900 flex-1">{methodology.name}</h3>
                {methodology.confidence && (
                  <span
                    className={`ml-2 px-3 py-1 rounded-full text-xs font-medium border ${getConfidenceBadgeColor(
                      methodology.confidence
                    )}`}
                  >
                    {methodology.confidence}
                  </span>
                )}
              </div>
              {methodology.description && <p className="text-sm text-gray-600">{methodology.description}</p>}
            </div>
          ))}
        </div>

        {methodologiesList.length > 9 && (
          <button
            onClick={onToggleShowAll}
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            {showAllMethodologies ? 'Show Less' : `Show All (${methodologiesList.length} methodologies)`}
          </button>
        )}
      </div>

      {/* Calculate Button */}
      <div className="mb-8">
        <button
          onClick={onGetCostEstimate}
          disabled={loading || hourlyRate <= 0}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2Icon className="w-5 h-5 animate-spin" />
              Calculating Estimate...
            </>
          ) : (
            'Calculate Comprehensive Estimate'
          )}
        </button>
      </div>

      {/* Cost Estimate Results */}
      {costEstimate && costEstimate.summary && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {/* Average Cost */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 font-medium mb-2">Average Cost</p>
              <p className="text-3xl font-bold text-gray-900">
                {selectedRegionData?.currency}
                {costEstimate.summary.average_cost.toLocaleString('en-US', {
                  maximumFractionDigits: 0,
                })}
              </p>
            </div>

            {/* Average Hours */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 font-medium mb-2">Average Hours</p>
              <p className="text-3xl font-bold text-gray-900">
                {costEstimate.summary.average_hours.toLocaleString('en-US', {
                  maximumFractionDigits: 0,
                })}
              </p>
            </div>

            {/* Minimum Cost */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 font-medium mb-2">Minimum</p>
              <p className="text-3xl font-bold text-green-600">
                {selectedRegionData?.currency}
                {costEstimate.summary.cost_range.min.toLocaleString('en-US', {
                  maximumFractionDigits: 0,
                })}
              </p>
            </div>

            {/* Maximum Cost */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <p className="text-sm text-gray-600 font-medium mb-2">Maximum</p>
              <p className="text-3xl font-bold text-red-600">
                {selectedRegionData?.currency}
                {costEstimate.summary.cost_range.max.toLocaleString('en-US', {
                  maximumFractionDigits: 0,
                })}
              </p>
            </div>
          </div>

          {/* Methodologies Table */}
          {costEstimate.methodologies && costEstimate.methodologies.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Estimation by Methodology</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                      Methodology
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                      Hours
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                      Cost
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                      Confidence
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {costEstimate.methodologies.map((methodology) => (
                    <tr key={methodology.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {methodology.name}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {methodology.hours.toLocaleString('en-US', {
                          maximumFractionDigits: 0,
                        })}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {selectedRegionData?.currency}
                        {methodology.cost.toLocaleString('en-US', {
                          maximumFractionDigits: 0,
                        })}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium border ${getConfidenceBadgeColor(
                            methodology.confidence
                          )}`}
                        >
                          {methodology.confidence}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          )}

          {/* AI Efficiency Section */}
          {costEstimate.ai_efficiency && (costEstimate.ai_efficiency.pure_human || costEstimate.ai_efficiency.ai_assisted || costEstimate.ai_efficiency.hybrid) && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">AI Efficiency Comparison</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Pure Human */}
              {costEstimate.ai_efficiency.pure_human && (
              <div className="border border-gray-200 rounded-lg p-6 bg-gray-50">
                <h4 className="font-semibold text-gray-900 mb-4">Pure Human Development</h4>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Hours Required</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {costEstimate.ai_efficiency.pure_human.hours.toLocaleString('en-US', {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Estimated Cost</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {selectedRegionData?.currency}
                      {costEstimate.ai_efficiency.pure_human.cost.toLocaleString('en-US', {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                </div>
              </div>
              )}

              {/* AI-Assisted */}
              {costEstimate.ai_efficiency.ai_assisted && (
              <div className="border border-blue-200 rounded-lg p-6 bg-blue-50 relative">
                <div className="absolute top-3 right-3 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-semibold">
                  Recommended
                </div>
                <h4 className="font-semibold text-gray-900 mb-4">AI-Assisted Development</h4>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Hours Required</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {costEstimate.ai_efficiency.ai_assisted.hours.toLocaleString('en-US', {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Estimated Cost</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {selectedRegionData?.currency}
                      {costEstimate.ai_efficiency.ai_assisted.cost.toLocaleString('en-US', {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  {costEstimate.ai_efficiency.ai_assisted.efficiency_gain !== undefined && (
                  <div className="bg-blue-100 rounded px-3 py-2">
                    <p className="text-xs text-blue-900 font-semibold">
                      {costEstimate.ai_efficiency.ai_assisted.efficiency_gain.toLocaleString('en-US', {
                        maximumFractionDigits: 1,
                      })}
                      % Efficiency Gain
                    </p>
                  </div>
                  )}
                </div>
              </div>
              )}

              {/* Hybrid */}
              {costEstimate.ai_efficiency.hybrid && (
              <div className="border border-purple-200 rounded-lg p-6 bg-purple-50">
                <h4 className="font-semibold text-gray-900 mb-4">Hybrid Approach</h4>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Hours Required</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {costEstimate.ai_efficiency.hybrid.hours.toLocaleString('en-US', {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Estimated Cost</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {selectedRegionData?.currency}
                      {costEstimate.ai_efficiency.hybrid.cost.toLocaleString('en-US', {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  {costEstimate.ai_efficiency.hybrid.efficiency_gain !== undefined && (
                  <div className="bg-purple-100 rounded px-3 py-2">
                    <p className="text-xs text-purple-900 font-semibold">
                      {costEstimate.ai_efficiency.hybrid.efficiency_gain.toLocaleString('en-US', {
                        maximumFractionDigits: 1,
                      })}
                      % Efficiency Gain
                    </p>
                  </div>
                  )}
                </div>
              </div>
              )}
            </div>
          </div>
          )}
        </>
      )}

      {/* Navigation Buttons */}
      <div className="flex gap-4">
        <button
          onClick={onBack}
          className="flex-1 border border-gray-300 hover:border-gray-400 text-gray-700 font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <ArrowLeftIcon className="w-5 h-5" />
          Back to Compliance
        </button>
        <button
          onClick={onContinue}
          disabled={!costEstimate || loading}
          className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          Generate Documents
          <ArrowRightIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
