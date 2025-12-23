'use client';

interface AnalysisStage {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'done' | 'error';
  detail?: string;
}

interface AnalysisData {
  repo_health?: { total?: number; [key: string]: any };
  tech_debt?: { total?: number; [key: string]: any };
  product_level?: string;
  complexity?: string;
  total_files?: number;
  status?: string;
  [key: string]: any;
}

interface AuditStepProps {
  analysisData: AnalysisData | null;
  analysisStages: AnalysisStage[];
  loading: boolean;
  onBackToReadiness: () => void;
  onGoToCompliance: () => void;
}

const PROJECT_TYPES: { [key: string]: { label: string; description: string; color: string } } = {
  'rnd_spike': { label: 'R&D Spike', description: 'Experimental code, proof of concept', color: 'bg-purple-100 text-purple-800' },
  'prototype': { label: 'Prototype', description: 'Working demo, not production-ready', color: 'bg-blue-100 text-blue-800' },
  'internal_tool': { label: 'Internal Tool', description: 'For internal use, basic quality', color: 'bg-cyan-100 text-cyan-800' },
  'platform_module': { label: 'Platform Module', description: 'Candidate for platform integration', color: 'bg-green-100 text-green-800' },
  'near_product': { label: 'Near-Product', description: 'Almost production-ready', color: 'bg-amber-100 text-amber-800' },
};

export default function AuditStep({
  analysisData,
  analysisStages,
  loading,
  onBackToReadiness,
  onGoToCompliance,
}: AuditStepProps) {
  const getProjectIcon = (productLevel: string): string => {
    switch (productLevel) {
      case 'rnd_spike': return '🔬';
      case 'prototype': return '🧪';
      case 'internal_tool': return '🔧';
      case 'platform_module': return '📦';
      case 'near_product': return '🚀';
      default: return '📊';
    }
  };

  const getComplexityLabel = (complexity: string): string => {
    switch (complexity) {
      case 'S': return 'Small';
      case 'M': return 'Medium';
      case 'L': return 'Large';
      case 'XL': return 'Extra Large';
      default: return complexity || 'N/A';
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Step 3: Full Analysis Results</h2>

      {loading ? (
        <div className="space-y-6">
          {/* Analysis Stages Visualization */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium mb-4">Analysis Progress</h3>
            <div className="space-y-3">
              {analysisStages.map((stage, idx) => (
                <div key={stage.id} className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                      stage.status === 'done'
                        ? 'bg-green-500 text-white'
                        : stage.status === 'running'
                        ? 'bg-blue-500 text-white animate-pulse'
                        : stage.status === 'error'
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {stage.status === 'done'
                      ? '✓'
                      : stage.status === 'running'
                      ? '⟳'
                      : stage.status === 'error'
                      ? '✕'
                      : idx + 1}
                  </div>
                  <div className="flex-1">
                    <div
                      className={`font-medium ${
                        stage.status === 'running' ? 'text-blue-700' : ''
                      }`}
                    >
                      {stage.label}
                    </div>
                    {stage.status === 'running' && (
                      <div className="text-xs text-gray-500">Processing...</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Spinner */}
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full mx-auto" />
          </div>
        </div>
      ) : analysisData?.status === 'completed' ? (
        <>
          {/* Project Type - Clear Display */}
          {analysisData.product_level && (
            <div
              className={`p-4 rounded-lg border-2 ${
                PROJECT_TYPES[analysisData.product_level]?.color ||
                'bg-gray-100'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium opacity-75">
                    Project Classification
                  </div>
                  <div className="text-2xl font-bold">
                    {PROJECT_TYPES[analysisData.product_level]?.label ||
                      analysisData.product_level}
                  </div>
                  <div className="text-sm mt-1">
                    {PROJECT_TYPES[analysisData.product_level]
                      ?.description}
                  </div>
                </div>
                <div className="text-4xl opacity-50">
                  {getProjectIcon(analysisData.product_level)}
                </div>
              </div>
            </div>
          )}

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-700">
                {analysisData.repo_health?.total || 0}/12
              </div>
              <div className="text-sm text-gray-600">Health Score</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-700">
                {analysisData.tech_debt?.total || 0}/15
              </div>
              <div className="text-sm text-gray-600">Tech Debt Score</div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-xl font-bold">
                {getComplexityLabel(analysisData.complexity || '')}
              </div>
              <div className="text-sm text-gray-600">Complexity</div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-xl font-bold">
                {analysisData.total_files || 0}
              </div>
              <div className="text-sm text-gray-600">Files Analyzed</div>
            </div>
          </div>

          {/* Tools & Metrics Used */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium mb-3">Analysis Tools & Metrics</h3>
            <div className="flex flex-wrap gap-2">
              {[
                'Structure Analyzer',
                'Static Analysis',
                'Git History',
                'Dependency Scanner',
                'Documentation Check',
                'Test Coverage',
              ].map((tool) => (
                <span
                  key={tool}
                  className="px-2 py-1 bg-white border border-gray-200 rounded text-sm"
                >
                  {tool}
                </span>
              ))}
            </div>
          </div>

          {/* Score Breakdowns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Repository Health */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="font-medium mb-3">Repository Health</h3>
              <div className="space-y-2">
                {[
                  'documentation',
                  'structure',
                  'runability',
                  'commit_history',
                  'history',
                ].map((key) => {
                  const value = analysisData.repo_health?.[key];
                  if (value === undefined) return null;
                  return (
                    <div
                      key={key}
                      className="flex justify-between text-sm"
                    >
                      <span className="capitalize text-gray-600">
                        {key.replace('_', ' ')}
                      </span>
                      <span className="font-medium">{value}/3</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Technical Debt */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="font-medium mb-3">Technical Debt</h3>
              <div className="space-y-2">
                {[
                  'architecture',
                  'code_quality',
                  'testing',
                  'infrastructure',
                  'security_deps',
                  'security',
                ].map((key) => {
                  const value = analysisData.tech_debt?.[key];
                  if (value === undefined) return null;
                  return (
                    <div
                      key={key}
                      className="flex justify-between text-sm"
                    >
                      <span className="capitalize text-gray-600">
                        {key.replace('_', ' ')}
                      </span>
                      <span className="font-medium">{value}/3</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={onBackToReadiness}
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Back to Readiness
            </button>
            <button
              onClick={onGoToCompliance}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Check Compliance
            </button>
          </div>
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No analysis data available.
        </div>
      )}
    </div>
  );
}
