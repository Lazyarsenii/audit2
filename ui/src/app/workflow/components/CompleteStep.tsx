'use client';

import Link from 'next/link';

interface CompleteStepProps {
  analysisData: {
    repo_health?: { total: number };
    tech_debt?: { total: number };
    product_level?: string;
    complexity?: string;
  } | null;
  readinessData: {
    readiness_level?: string;
  } | null;
  complianceData: {
    verdict?: string;
  } | null;
  costEstimate: {
    summary?: { average_cost: number };
  } | null;
  generatedDocs: string[];
  comparisonData: {
    overall_status?: string;
    overall_score?: number;
  } | null;
  onResetWorkflow: () => void;
}

export default function CompleteStep({
  analysisData,
  readinessData,
  complianceData,
  costEstimate,
  generatedDocs,
  comparisonData,
  onResetWorkflow,
}: CompleteStepProps) {
  const handleDownload = (docType: string) => {
    // TODO: Implement actual document download
    // For now, this is a placeholder that should trigger file download API
  };

  const getComplexityLabel = (complexity: string | undefined): string => {
    if (!complexity) return 'N/A';
    switch (complexity) {
      case 'S':
        return 'Small';
      case 'M':
        return 'Medium';
      case 'L':
        return 'Large';
      case 'XL':
        return 'Extra Large';
      default:
        return complexity;
    }
  };

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-8 h-8 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Audit Complete!</h2>
        <p className="text-gray-600 text-lg">All workflow steps have been completed.</p>
      </div>

      {/* Summary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Summary Block */}
        <div className="p-6 bg-gray-50 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
          <div className="space-y-3">
            {/* Health Score */}
            <div className="flex justify-between items-center pb-3 border-b border-gray-200">
              <span className="text-gray-600">Health Score</span>
              <span className="font-semibold text-gray-900">
                {analysisData?.repo_health?.total || 0}/12
              </span>
            </div>

            {/* Tech Debt */}
            <div className="flex justify-between items-center pb-3 border-b border-gray-200">
              <span className="text-gray-600">Tech Debt</span>
              <span className="font-semibold text-gray-900">
                {analysisData?.tech_debt?.total || 0}/15
              </span>
            </div>

            {/* Readiness Level */}
            <div className="flex justify-between items-center pb-3 border-b border-gray-200">
              <span className="text-gray-600">Readiness Level</span>
              <span className="font-semibold text-gray-900">
                {readinessData?.readiness_level
                  ? readinessData.readiness_level.replace(/_/g, ' ').toUpperCase()
                  : 'N/A'}
              </span>
            </div>

            {/* Compliance Verdict */}
            <div className="flex justify-between items-center pb-3 border-b border-gray-200">
              <span className="text-gray-600">Compliance Verdict</span>
              <span
                className={`font-semibold px-3 py-1 rounded-full text-sm ${
                  complianceData?.verdict === 'COMPLIANT'
                    ? 'bg-green-100 text-green-700'
                    : complianceData?.verdict === 'PARTIAL'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                }`}
              >
                {complianceData?.verdict || 'N/A'}
              </span>
            </div>

            {/* Estimated Cost */}
            <div className="flex justify-between items-center pb-3 border-b border-gray-200">
              <span className="text-gray-600">Estimated Cost</span>
              <span className="font-semibold text-gray-900">
                ${costEstimate?.summary?.average_cost?.toLocaleString() || 'N/A'}
              </span>
            </div>

            {/* Product Level */}
            {analysisData?.product_level && (
              <div className="flex justify-between items-center pb-3 border-b border-gray-200">
                <span className="text-gray-600">Product Level</span>
                <span className="font-semibold text-gray-900 capitalize">
                  {analysisData.product_level.replace(/_/g, ' ')}
                </span>
              </div>
            )}

            {/* Complexity */}
            {analysisData?.complexity && (
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Complexity</span>
                <span className="font-semibold text-gray-900">
                  {getComplexityLabel(analysisData.complexity)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Generated Documents Block */}
        <div className="p-6 bg-gray-50 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Generated Documents</h3>
          {generatedDocs && generatedDocs.length > 0 ? (
            <div className="space-y-2">
              {generatedDocs.map((doc) => (
                <div
                  key={doc}
                  className="flex justify-between items-center p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
                >
                  <span className="text-gray-700 capitalize font-medium">{doc}</span>
                  <button
                    onClick={() => handleDownload(doc)}
                    className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
                  >
                    Download
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-gray-500 text-sm">No documents generated</p>
            </div>
          )}
        </div>
      </div>

      {/* Comparison Results (if available) */}
      {comparisonData && (
        <div className="p-6 bg-blue-50 rounded-lg border border-blue-200">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">Comparison Results</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Overall Status</div>
              <div className="text-lg font-bold text-gray-900 capitalize">
                {comparisonData.overall_status?.replace(/_/g, ' ') || 'N/A'}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Overall Score</div>
              <div className="text-lg font-bold text-blue-700">
                {comparisonData.overall_score ?? 'N/A'}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4 pt-4">
        <button
          onClick={onResetWorkflow}
          className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
        >
          Start New Audit
        </button>
        <Link
          href="/projects"
          className="px-8 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition-colors shadow-sm text-center"
        >
          Go to Projects
        </Link>
      </div>
    </div>
  );
}
