'use client';

import React, { useEffect, useState, useRef } from 'react';
import {
  SourceType,
  CollectorInfo,
  ValidationResult,
  AnalysisCategory,
  ProjectType,
  PROJECT_TYPES,
} from '../hooks/useWorkflow';
import AnalysisProgress from '@/components/AnalysisProgress';
import { API_BASE, apiFetch } from '@/lib/api';
import { useLanguage } from '@/contexts/LanguageContext';
import {
  FileUp,
  FileText,
  FileCheck,
  Shield,
  Upload,
  Loader2,
  Trash2,
  Eye,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Settings,
  Layers,
  BarChart3,
  Lock,
  ScrollText,
  DollarSign,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface UploadedDocument {
  id: string;
  title: string;
  document_type: 'tz' | 'contract' | 'policy';
  file_name: string | null;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  extraction_confidence: number | null;
  created_at: string;
  requirements_count?: number;
}

interface ExtractedRequirement {
  id: string;
  category: string;
  text: string;
  source: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  checkable: boolean;
}

interface ReadinessArtifact {
  id: string;
  name: string;
  required: boolean;
  present: boolean;
  path?: string;
  for_analysis: string[];
}

interface ReadinessBlocker {
  code: string;
  message: string;
  severity: 'blocker' | 'critical';
}

interface ReadinessWarning {
  code: string;
  message: string;
  severity: 'warning' | 'important';
}

interface AvailableAnalysis {
  category: string;
  name: string;
  status: 'ready' | 'blocked';
  reasons?: string[];
}

interface ReadinessCheckResult {
  ready_to_analyze: boolean;
  readiness_score: number;
  blockers: ReadinessBlocker[];
  warnings: ReadinessWarning[];
  available_analyses: AvailableAnalysis[];
  blocked_analyses: AvailableAnalysis[];
  recommendations: ReadinessWarning[];
}

interface SetupStepProps {
  sourceType: 'github' | 'gitlab' | 'local';
  repoUrl: string;
  localPath: string;
  branch: string;
  regionMode: 'EU' | 'UA' | 'EU_UA';
  selectedCollectors: string[];
  collectorsList: CollectorInfo[];
  validationResult: ValidationResult | null;
  isValidating: boolean;
  loading: boolean;
  error: string | null;
  analysisId: string | null;
  // NEW: Analysis Configuration
  analysisCategories: AnalysisCategory[];
  projectType: ProjectType;
  baselineDocumentId: string | null;
  onSourceTypeChange: (type: SourceType) => void;
  onRepoUrlChange: (url: string) => void;
  onLocalPathChange: (path: string) => void;
  onBranchChange: (branch: string) => void;
  onRegionModeChange: (mode: 'EU' | 'UA' | 'EU_UA') => void;
  onToggleCollector: (id: string) => void;
  onStartAnalysis: () => void;
  onValidateSource: () => void;
  onLoadCollectors: () => void;
  onOpenDirectoryPicker: () => void;
  onAnalysisComplete?: () => void;
  onAnalysisError?: (error: string) => void;
  // NEW: Analysis Configuration handlers
  onToggleAnalysisCategory: (categoryId: string) => void;
  onProjectTypeChange: (type: ProjectType) => void;
  onBaselineDocumentChange: (docId: string | null) => void;
}

// ============================================================================
// DOCUMENT UPLOAD SECTION
// ============================================================================

// LLM extracted requirements type
interface LLMExtractedRequirement {
  id: string;
  category: string;
  requirement: string;
  metric: string;
  operator: string;
  threshold: string | number;
  priority: string;
}

interface LLMParseResult {
  success: boolean;
  checkable_requirements: LLMExtractedRequirement[];
  suggested_categories: string[];
  project_type_hint?: string;
  model_used?: string;
  latency_ms?: number;
}

const DocumentUploadSection: React.FC<{
  onDocumentsChange: (docs: UploadedDocument[]) => void;
  onRequirementsExtracted: (reqs: ExtractedRequirement[]) => void;
  onLLMRequirementsExtracted?: (result: LLMParseResult) => void;
}> = ({ onDocumentsChange, onRequirementsExtracted, onLLMRequirementsExtracted }) => {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState<string | null>(null);
  const [llmParsing, setLlmParsing] = useState<string | null>(null);
  const [llmResult, setLlmResult] = useState<LLMParseResult | null>(null);
  const [selectedDocType, setSelectedDocType] = useState<'tz' | 'contract' | 'policy'>('tz');
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('upload');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents?limit=50`);
      if (res.ok) {
        const data = await res.json();
        const docs = data.documents || [];
        setDocuments(docs);
        onDocumentsChange(docs);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  // LLM-assisted document parsing using Llama via Groq
  const parseLLMRequirements = async (docId: string, docText: string, docType: string) => {
    setLlmParsing(docId);

    try {
      const res = await apiFetch(`${API_BASE}/api/contract-parser/llm-extract-requirements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: docText,
          document_type: docType,
        }),
      });

      if (res.ok) {
        const result: LLMParseResult = await res.json();
        setLlmResult(result);

        if (result.success && onLLMRequirementsExtracted) {
          onLLMRequirementsExtracted(result);
        }

        return result;
      }
    } catch (err) {
      console.error('LLM parsing failed:', err);
    }

    setLlmParsing(null);
    return null;
  };

  // Get document text content for LLM parsing
  const getDocumentText = async (docId: string): Promise<string | null> => {
    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}/content`);
      if (res.ok) {
        const data = await res.json();
        return data.text || data.content || null;
      }
    } catch (err) {
      console.error('Failed to get document text:', err);
    }
    return null;
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // analysisId должен быть передан через props или context
    const analysisId = (window as any).currentAnalysisId || null;
    if (!analysisId) {
      setError('Please select a repository or directory before uploading documents.');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
    formData.append('document_type', 'auto');  // LLM will auto-detect type
    formData.append('storage_backend', 'local');
    formData.append('analysis_id', analysisId);

    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        await loadDocuments();
      } else {
        const err = await res.json();
        setError(err.detail || 'Upload failed');
      }
    } catch (err) {
      setError('Failed to upload document');
    }

    setUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleExtractRequirements = async (docId: string, docType: string) => {
    setExtracting(docId);
    setError(null);

    try {
      // First extract the document text
      const extractRes = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: 'hybrid', task_type: 'requirements' }),
      });

      if (extractRes.ok) {
        await loadDocuments();

        // Then get extracted requirements (legacy)
        const reqRes = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}/requirements`);
        if (reqRes.ok) {
          const data = await reqRes.json();
          onRequirementsExtracted(data.requirements || []);
        }

        // NOW: Also run LLM parsing for smart extraction
        const docText = await getDocumentText(docId);
        if (docText) {
          // Run LLM parsing in background (don't block UI)
          parseLLMRequirements(docId, docText, docType).then(result => {
            setLlmParsing(null);
            // LLM extraction complete - results will be used in subsequent steps
          });
        }
      } else {
        const err = await extractRes.json();
        setError(err.detail || 'Extraction failed');
      }
    } catch (err) {
      setError('Failed to extract requirements');
    }

    setExtracting(null);
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await loadDocuments();
      }
    } catch (err) {
      setError('Failed to delete document');
    }
  };

  const getDocTypeIcon = (type: string) => {
    switch (type) {
      case 'tz': return <FileText className="w-4 h-4 text-blue-600" />;
      case 'contract': return <FileCheck className="w-4 h-4 text-green-600" />;
      case 'policy': return <Shield className="w-4 h-4 text-purple-600" />;
      default: return <FileText className="w-4 h-4 text-gray-600" />;
    }
  };

  const getDocTypeLabel = (type: string) => {
    switch (type) {
      case 'tz': return 'TZ';
      case 'contract': return 'Contract';
      case 'policy': return 'Policy';
      default: return type;
    }
  };

  const getStatusBadge = (status: string, confidence?: number | null) => {
    const colors: Record<string, string> = {
      pending: 'bg-gray-100 text-gray-600',
      processing: 'bg-blue-100 text-blue-600',
      completed: 'bg-green-100 text-green-600',
      failed: 'bg-red-100 text-red-600',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] || colors.pending}`}>
        {status === 'completed' ? 'Processed' : status === 'pending' ? 'Pending' : status}
        {confidence !== null && confidence !== undefined && ` (${confidence}%)`}
      </span>
    );
  };

  const docsByType = {
    tz: documents.filter(d => d.document_type === 'tz'),
    contract: documents.filter(d => d.document_type === 'contract'),
    policy: documents.filter(d => d.document_type === 'policy'),
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpandedSection(expandedSection === 'upload' ? null : 'upload')}
        className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <FileUp className="w-5 h-5 text-blue-600" />
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">Documents for analysis</h3>
            <p className="text-sm text-gray-600">
              TZ, contracts and policies for compliance check
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {documents.length > 0 && (
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm font-medium">
              {documents.length} docs
            </span>
          )}
          {expandedSection === 'upload' ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {expandedSection === 'upload' && (
        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Upload Controls - Simplified: no type selection, LLM auto-detects */}
          <div className="flex flex-wrap items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md"
              onChange={handleFileSelect}
              className="hidden"
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload document
                </>
              )}
            </button>

            <span className="text-sm text-gray-500">
              PDF, DOCX, TXT — AI auto-detects type
            </span>
          </div>

          {/* Documents List by Type */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['tz', 'contract', 'policy'] as const).map(type => (
              <div key={type} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  {getDocTypeIcon(type)}
                  <h4 className="font-medium text-gray-900">{getDocTypeLabel(type)}</h4>
                  <span className="ml-auto text-xs text-gray-500">
                    {docsByType[type].length}
                  </span>
                </div>

                {docsByType[type].length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">
                    Not uploaded
                  </p>
                ) : (
                  <div className="space-y-2">
                    {docsByType[type].map(doc => (
                      <div
                        key={doc.id}
                        className="p-2 rounded bg-gray-50 border border-gray-100"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {doc.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              {getStatusBadge(doc.processing_status, doc.extraction_confidence)}
                            </div>
                          </div>
                          <div className="flex gap-1">
                            {doc.processing_status !== 'completed' ? (
                              <button
                                onClick={() => handleExtractRequirements(doc.id, doc.document_type)}
                                disabled={extracting === doc.id || llmParsing === doc.id}
                                className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-blue-600 disabled:opacity-50"
                                title="Extract requirements (+ AI analysis)"
                              >
                                {extracting === doc.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <RefreshCw className="w-4 h-4" />
                                )}
                              </button>
                            ) : llmParsing === doc.id ? (
                              <button
                                className="p-1 rounded bg-purple-100 text-purple-600"
                                title="AI analyzing..."
                              >
                                <Loader2 className="w-4 h-4 animate-spin" />
                              </button>
                            ) : (
                              <button
                                className="p-1 rounded hover:bg-gray-200 text-green-600"
                                title="Processed"
                              >
                                <CheckCircle2 className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => handleDelete(doc.id)}
                              className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-red-600"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* LLM Results */}
          {llmResult && llmResult.success && (
            <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🧠</span>
                <h4 className="font-semibold text-purple-900">AI Document Analysis</h4>
                {llmResult.model_used && (
                  <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">
                    {llmResult.model_used}
                  </span>
                )}
                {llmResult.latency_ms && (
                  <span className="text-xs text-purple-500">
                    {(llmResult.latency_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>

              {/* Suggested Categories */}
              {llmResult.suggested_categories && llmResult.suggested_categories.length > 0 && (
                <div className="mb-3">
                  <p className="text-sm font-medium text-purple-800 mb-2">Recommended categories:</p>
                  <div className="flex flex-wrap gap-2">
                    {llmResult.suggested_categories.map(cat => (
                      <span key={cat} className="px-2 py-1 bg-purple-200 text-purple-800 rounded text-sm">
                        {cat === 'state_quality' ? '📊 State & Quality' :
                         cat === 'security' ? '🔒 Security' :
                         cat === 'compliance' ? '✅ Compliance' :
                         cat === 'cost' ? '💰 Cost' :
                         cat === 'ip_ownership' ? '📜 IP & Ownership' : cat}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Requirements */}
              {llmResult.checkable_requirements && llmResult.checkable_requirements.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-purple-800 mb-2">
                    Extracted requirements ({llmResult.checkable_requirements.length}):
                  </p>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {llmResult.checkable_requirements.slice(0, 5).map((req, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <span className={`
                          px-1.5 py-0.5 rounded text-xs font-medium
                          ${req.priority === 'blocker' ? 'bg-red-100 text-red-700' :
                            req.priority === 'critical' ? 'bg-orange-100 text-orange-700' :
                            req.priority === 'important' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-600'}
                        `}>
                          {req.priority}
                        </span>
                        <span className="text-purple-900">{req.requirement}</span>
                      </div>
                    ))}
                    {llmResult.checkable_requirements.length > 5 && (
                      <p className="text-xs text-purple-600">
                        +{llmResult.checkable_requirements.length - 5} more...
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Project Type Hint */}
              {llmResult.project_type_hint && (
                <div className="mt-3 text-sm text-purple-700">
                  💡 Recommended project type: <strong>{llmResult.project_type_hint}</strong>
                </div>
              )}
            </div>
          )}

          {/* Info */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            <strong>Hint:</strong> Upload TZ, contract or policies before analysis.
            AI will automatically extract requirements and suggest analysis categories.
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// READINESS CHECK SECTION
// ============================================================================

const ReadinessCheckSection: React.FC<{
  readinessResult: ReadinessCheckResult | null;
  loading: boolean;
  onCheckReadiness: () => void;
}> = ({ readinessResult, loading, onCheckReadiness }) => {
  const [expanded, setExpanded] = useState(true);

  if (!readinessResult) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-gray-400" />
            <div>
              <h3 className="font-semibold text-gray-900">Readiness Check</h3>
              <p className="text-sm text-gray-600">
                Check project readiness based on selected categories
              </p>
            </div>
          </div>
          <button
            onClick={onCheckReadiness}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Checking...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Check Readiness
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  const scoreColor = readinessResult.readiness_score >= 80
    ? 'text-green-600'
    : readinessResult.readiness_score >= 50
      ? 'text-yellow-600'
      : 'text-red-600';

  const scoreBg = readinessResult.readiness_score >= 80
    ? 'bg-green-50 border-green-200'
    : readinessResult.readiness_score >= 50
      ? 'bg-yellow-50 border-yellow-200'
      : 'bg-red-50 border-red-200';

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          {readinessResult.ready_to_analyze ? (
            <CheckCircle2 className="w-5 h-5 text-green-600" />
          ) : (
            <AlertCircle className="w-5 h-5 text-yellow-600" />
          )}
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">Analysis Readiness</h3>
            <p className="text-sm text-gray-600">
              {readinessResult.ready_to_analyze
                ? 'Ready for analysis'
                : readinessResult.blockers.length > 0
                  ? 'Has blocking issues'
                  : 'Some analyses unavailable'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1 rounded-lg border ${scoreBg}`}>
            <span className={`text-lg font-bold ${scoreColor}`}>
              {readinessResult.readiness_score}%
            </span>
          </div>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="p-6 space-y-4">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{readinessResult.available_analyses.length}</p>
              <p className="text-sm text-green-700">Available</p>
            </div>
            <div className="text-center p-3 bg-yellow-50 rounded-lg">
              <p className="text-2xl font-bold text-yellow-600">{readinessResult.warnings.length}</p>
              <p className="text-sm text-yellow-700">Warnings</p>
            </div>
            <div className="text-center p-3 bg-red-50 rounded-lg">
              <p className="text-2xl font-bold text-red-600">{readinessResult.blockers.length}</p>
              <p className="text-sm text-red-700">Blockers</p>
            </div>
          </div>

          {/* Blockers */}
          {readinessResult.blockers.length > 0 && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="font-medium text-red-800 mb-3 flex items-center gap-2">
                <XCircle className="w-5 h-5" />
                Blocking Issues
              </h4>
              <div className="space-y-2">
                {readinessResult.blockers.map((blocker, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-red-700">
                    <span className="font-mono text-xs bg-red-100 px-1.5 py-0.5 rounded">
                      {blocker.code}
                    </span>
                    <span>{blocker.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Available Analyses */}
          {readinessResult.available_analyses.length > 0 && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <h4 className="font-medium text-green-800 mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5" />
                Available Analyses
              </h4>
              <div className="flex flex-wrap gap-2">
                {readinessResult.available_analyses.map((analysis, i) => (
                  <span key={i} className="px-3 py-1.5 bg-green-100 text-green-700 text-sm rounded-lg font-medium">
                    {analysis.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Blocked Analyses */}
          {readinessResult.blocked_analyses.length > 0 && (
            <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <h4 className="font-medium text-orange-800 mb-3 flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Unavailable Analyses
              </h4>
              <div className="space-y-2">
                {readinessResult.blocked_analyses.map((analysis, i) => (
                  <div key={i} className="flex items-start gap-3 p-2 bg-orange-100 rounded-lg">
                    <span className="font-medium text-orange-800 text-sm">{analysis.name}</span>
                    {analysis.reasons && analysis.reasons.length > 0 && (
                      <span className="text-xs text-orange-600">
                        — {analysis.reasons.join(', ')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {readinessResult.warnings.length > 0 && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h4 className="font-medium text-yellow-800 mb-3 flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Warnings
              </h4>
              <div className="space-y-2">
                {readinessResult.warnings.map((warning, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-yellow-700">
                    <span className="font-mono text-xs bg-yellow-100 px-1.5 py-0.5 rounded">
                      {warning.code}
                    </span>
                    <span>{warning.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {readinessResult.recommendations.length > 0 && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-medium text-blue-800 mb-3 flex items-center gap-2">
                <Eye className="w-5 h-5" />
                Recommendations
              </h4>
              <ul className="space-y-2">
                {readinessResult.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-blue-700">
                    <span className="font-mono text-xs bg-blue-100 px-1.5 py-0.5 rounded">
                      {rec.code}
                    </span>
                    <span>{rec.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recheck button */}
          <div className="flex justify-end pt-2">
            <button
              onClick={onCheckReadiness}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Re-check
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// ANALYSIS CATEGORIES SELECTOR
// ============================================================================

const getCategoryIcon = (categoryId: string) => {
  switch (categoryId) {
    case 'state_quality': return <BarChart3 className="w-5 h-5" />;
    case 'security': return <Lock className="w-5 h-5" />;
    case 'ip_ownership': return <ScrollText className="w-5 h-5" />;
    case 'compliance': return <CheckCircle2 className="w-5 h-5" />;
    case 'cost': return <DollarSign className="w-5 h-5" />;
    default: return <Layers className="w-5 h-5" />;
  }
};

const AnalysisCategoriesSection: React.FC<{
  categories: AnalysisCategory[];
  projectType: ProjectType;
  hasBaselineDocument: boolean;
  onToggleCategory: (id: string) => void;
  onProjectTypeChange: (type: ProjectType) => void;
}> = ({ categories, projectType, hasBaselineDocument, onToggleCategory, onProjectTypeChange }) => {
  const [expanded, setExpanded] = useState(true);

  const enabledCount = categories.filter(c => c.enabled).length;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-blue-600" />
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">Analysis Configuration</h3>
            <p className="text-sm text-gray-600">
              Select analysis categories
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm font-medium">
            {enabledCount} of {categories.length}
          </span>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="p-6 space-y-6">
          {/* Analysis Categories - ALL clickable, user has full control */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Analysis Categories
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {categories.map(category => {
                // Info notes (not blocking)
                const needsDocument = category.requires?.document && !hasBaselineDocument;

                return (
                  <button
                    key={category.id}
                    onClick={() => onToggleCategory(category.id)}
                    className={`
                      p-4 rounded-lg border-2 text-left transition-all relative cursor-pointer
                      ${category.enabled
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 bg-white hover:border-gray-300'}
                    `}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`
                        p-2 rounded-lg flex-shrink-0
                        ${category.enabled
                          ? 'bg-green-100 text-green-600'
                          : 'bg-gray-100 text-gray-500'}
                      `}>
                        {getCategoryIcon(category.id)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`font-medium ${
                            category.enabled ? 'text-green-700' : 'text-gray-700'
                          }`}>
                            {category.name}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {category.description}
                        </p>
                        {needsDocument && category.enabled && (
                          <p className="text-xs text-blue-600 mt-2 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Upload TZ/contract for full analysis
                          </p>
                        )}
                      </div>
                      <div className={`
                        w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0
                        ${category.enabled
                          ? 'border-green-500 bg-green-500'
                          : 'border-gray-300'}
                      `}>
                        {category.enabled && (
                          <CheckCircle2 className="w-3 h-3 text-white" />
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Info about selected categories */}
          <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            <strong>All categories available.</strong> Select what you need.
            Documents are optional — without them analysis shows less data.
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN SETUP STEP COMPONENT
// ============================================================================

export default function SetupStep({
  sourceType,
  repoUrl,
  localPath,
  branch,
  regionMode,
  selectedCollectors,
  collectorsList,
  validationResult,
  isValidating,
  loading,
  error,
  analysisId,
  // NEW: Analysis Configuration
  analysisCategories,
  projectType,
  baselineDocumentId,
  onSourceTypeChange,
  onRepoUrlChange,
  onLocalPathChange,
  onBranchChange,
  onRegionModeChange,
  onToggleCollector,
  onStartAnalysis,
  onValidateSource,
  onLoadCollectors,
  onOpenDirectoryPicker,
  onAnalysisComplete,
  onAnalysisError,
  // NEW: Analysis Configuration handlers
  onToggleAnalysisCategory,
  onProjectTypeChange,
  onBaselineDocumentChange,
}: SetupStepProps) {
  const [uploadedDocuments, setUploadedDocuments] = useState<UploadedDocument[]>([]);
  const [extractedRequirements, setExtractedRequirements] = useState<ExtractedRequirement[]>([]);
  const [readinessResult, setReadinessResult] = useState<ReadinessCheckResult | null>(null);
  const [checkingReadiness, setCheckingReadiness] = useState(false);

  // Check if we have a baseline document (TZ or contract) for compliance
  const hasBaselineDocument = uploadedDocuments.some(
    d => (d.document_type === 'tz' || d.document_type === 'contract') && d.processing_status === 'completed'
  );

  // Auto-select baseline document when uploaded
  useEffect(() => {
    if (hasBaselineDocument && !baselineDocumentId) {
      const tzDoc = uploadedDocuments.find(d => d.document_type === 'tz' && d.processing_status === 'completed');
      const contractDoc = uploadedDocuments.find(d => d.document_type === 'contract' && d.processing_status === 'completed');
      const doc = tzDoc || contractDoc;
      if (doc) {
        onBaselineDocumentChange(doc.id);
      }
    }
  }, [uploadedDocuments, hasBaselineDocument, baselineDocumentId, onBaselineDocumentChange]);

  // Load collectors on mount
  useEffect(() => {
    if (collectorsList.length === 0) {
      onLoadCollectors();
    }
  }, [collectorsList.length, onLoadCollectors]);

  const handleCheckReadiness = async () => {
    const source = sourceType === 'local' ? localPath : repoUrl;
    if (!source) return;

    setCheckingReadiness(true);

    try {
      // Get enabled categories
      const enabledCategories = analysisCategories
        .filter(cat => cat.enabled)
        .map(cat => cat.id);

      // Check document types
      const hasTz = uploadedDocuments.some(d => d.document_type === 'tz' && d.processing_status === 'completed');
      const hasContract = uploadedDocuments.some(d => d.document_type === 'contract' && d.processing_status === 'completed');
      const hasPolicy = uploadedDocuments.some(d => d.document_type === 'policy' && d.processing_status === 'completed');

      const res = await apiFetch(`${API_BASE}/api/readiness/project-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          // Source info
          source_type: sourceType,
          repo_url: source,
          // Analysis configuration
          analysis_categories: enabledCategories,
          project_type: projectType,
          // Documents
          has_tz_document: hasTz,
          has_contract_document: hasContract,
          has_policy_document: hasPolicy,
          baseline_document_id: baselineDocumentId,
          // Validation result
          is_git_repo: validationResult?.is_git_repo || false,
          has_readme: validationResult?.has_readme || false,
          has_tests: validationResult?.has_tests || false,
          has_ci: validationResult?.has_ci || false,
          detected_languages: validationResult?.detected_languages || [],
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setReadinessResult(data);
      }
    } catch (err) {
      console.error('Readiness check failed:', err);
    }

    setCheckingReadiness(false);
  };

  const isAnalysisDisabled = loading || isValidating ||
    (!repoUrl && sourceType !== 'local') ||
    (!localPath && sourceType === 'local');

  const canValidate = (repoUrl && sourceType !== 'local') || (localPath && sourceType === 'local');

  const getPlaceholder = () => {
    if (sourceType === 'github') return 'https://github.com/owner/repo';
    if (sourceType === 'gitlab') return 'https://gitlab.com/owner/repo';
    return '/path/to/repository';
  };

  const getSourceTypeLabel = (type: string) => {
    const labels: { [key: string]: string } = {
      github: 'GitHub',
      gitlab: 'GitLab',
      local: 'Local',
    };
    return labels[type] || type;
  };

  const getRegionModeLabel = (mode: string) => {
    const labels: { [key: string]: string } = {
      EU: 'European Union',
      UA: 'Ukraine',
      EU_UA: 'EU + Ukraine',
    };
    return labels[mode] || mode;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Step 1: Project Setup
        </h2>
        <p className="text-gray-600 mt-1">
          Select repository, upload documents and check readiness
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* === SECTION 1: Source Selection === */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm">1</span>
          Repository Selection
        </h3>

        {/* Source Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Source Type
          </label>
          <div className="flex gap-3">
            {(['github', 'gitlab', 'local'] as const).map(type => (
              <button
                key={type}
                onClick={() => onSourceTypeChange(type)}
                className={`
                  px-6 py-3 rounded-lg font-medium transition-all
                  border-2 text-sm md:text-base
                  ${
                    sourceType === type
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                  }
                `}
                disabled={loading}
              >
                {getSourceTypeLabel(type)}
              </button>
            ))}
          </div>
        </div>

        {/* Repository Input */}
        {sourceType === 'local' ? (
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Repository Path
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={localPath}
                onChange={e => onLocalPathChange(e.target.value)}
                placeholder={getPlaceholder()}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-shadow"
                disabled={loading}
              />
              <button
                onClick={onOpenDirectoryPicker}
                disabled={loading}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Browse
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Repository URL
              </label>
              <input
                type="text"
                value={repoUrl}
                onChange={e => onRepoUrlChange(e.target.value)}
                placeholder={getPlaceholder()}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-shadow"
                disabled={loading}
              />
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Branch (optional)
              </label>
              <input
                type="text"
                value={branch}
                onChange={e => onBranchChange(e.target.value)}
                placeholder="main"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-shadow"
                disabled={loading}
              />
            </div>
          </div>
        )}

        {/* Verify Access Button */}
        <div className="flex items-center gap-4 pt-2">
          <button
            onClick={onValidateSource}
            disabled={!canValidate || isValidating || loading}
            className={`
              px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2
              ${canValidate && !isValidating
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'}
            `}
          >
            {isValidating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Checking...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Check Access
              </>
            )}
          </button>

          {/* Validation Result */}
          {validationResult && (
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
              validationResult.accessible
                ? 'bg-green-50 text-green-700'
                : 'bg-red-50 text-red-700'
            }`}>
              {validationResult.accessible ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              <span>{validationResult.message}</span>
            </div>
          )}
        </div>

        {/* Validation Details */}
        {validationResult?.accessible && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm space-y-2">
            <div className="flex flex-wrap gap-3">
              {validationResult.is_git_repo && (
                <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                  Git Repository
                </span>
              )}
              {validationResult.has_readme && (
                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                  Has README
                </span>
              )}
              {validationResult.has_tests && (
                <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                  Has Tests
                </span>
              )}
              {validationResult.has_ci && (
                <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-medium">
                  Has CI/CD
                </span>
              )}
              {validationResult.file_count !== undefined && (
                <span className="px-2 py-1 bg-gray-200 text-gray-700 rounded-full text-xs font-medium">
                  {validationResult.file_count.toLocaleString()} files
                </span>
              )}
            </div>
            {validationResult.detected_languages && validationResult.detected_languages.length > 0 && (
              <div className="text-gray-600">
                <span className="font-medium">Languages: </span>
                {validationResult.detected_languages.join(', ')}
              </div>
            )}
          </div>
        )}
      </div>

      {/* === SECTION 2: Document Upload === */}
      <div className="space-y-2">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm">2</span>
          Upload Documents (optional)
        </h3>
        <DocumentUploadSection
          onDocumentsChange={setUploadedDocuments}
          onRequirementsExtracted={setExtractedRequirements}
          onLLMRequirementsExtracted={(result) => {
            // Auto-enable suggested categories
            if (result.suggested_categories) {
              result.suggested_categories.forEach(cat => {
                const category = analysisCategories.find(c => c.id === cat);
                if (category && !category.enabled) {
                  onToggleAnalysisCategory(cat);
                }
              });
            }
            // Auto-set project type if suggested
            if (result.project_type_hint) {
              onProjectTypeChange(result.project_type_hint as ProjectType);
            }
          }}
        />
      </div>

      {/* === SECTION 3: Analysis Configuration === */}
      <div className="space-y-2">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm">3</span>
          Analysis Configuration
        </h3>
        <AnalysisCategoriesSection
          categories={analysisCategories}
          projectType={projectType}
          hasBaselineDocument={hasBaselineDocument}
          onToggleCategory={onToggleAnalysisCategory}
          onProjectTypeChange={onProjectTypeChange}
        />
      </div>

      {/* === SECTION 4: Readiness Check === */}
      {validationResult?.accessible && (
        <div className="space-y-2">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm">4</span>
            Readiness Check
          </h3>
          <ReadinessCheckSection
            readinessResult={readinessResult}
            loading={checkingReadiness}
            onCheckReadiness={handleCheckReadiness}
          />
        </div>
      )}

      {/* === SECTION 5: Region Mode & Collectors === */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm">5</span>
          Analysis Settings
        </h3>

        {/* Region Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Region (for cost estimation)
          </label>
          <div className="flex gap-3 flex-wrap">
            {(['EU', 'UA', 'EU_UA'] as const).map(mode => (
              <button
                key={mode}
                onClick={() => onRegionModeChange(mode)}
                disabled={loading}
                className={`
                  px-4 py-2 rounded-lg font-medium transition-all border-2 text-sm
                  ${regionMode === mode
                    ? 'border-green-500 bg-green-50 text-green-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'}
                `}
              >
                {getRegionModeLabel(mode)}
              </button>
            ))}
          </div>
        </div>

        {/* Collectors Selection */}
        {collectorsList.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Analysis Collectors
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {collectorsList.map(collector => {
                const isSelected = selectedCollectors.includes(collector.id);
                return (
                  <button
                    key={collector.id}
                    onClick={() => !collector.required && onToggleCollector(collector.id)}
                    disabled={collector.required || loading}
                    className={`
                      p-3 rounded-lg border-2 text-left transition-all
                      ${isSelected
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 bg-white hover:border-gray-300'}
                      ${collector.required ? 'cursor-not-allowed' : 'cursor-pointer'}
                    `}
                  >
                    <div className="flex items-start gap-2">
                      <div className={`
                        w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5
                        ${isSelected ? 'border-green-500 bg-green-500' : 'border-gray-300'}
                      `}>
                        {isSelected && (
                          <CheckCircle2 className="w-3 h-3 text-white" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`font-medium text-sm ${isSelected ? 'text-green-700' : 'text-gray-700'}`}>
                            {collector.name}
                          </span>
                          {collector.required && (
                            <span className="px-1.5 py-0.5 bg-gray-200 text-gray-600 text-xs rounded">
                              Required
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5 truncate">
                          {collector.description}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-gray-500">
              Selected: {selectedCollectors.length} of {collectorsList.length} collectors
            </p>
          </div>
        )}
      </div>

      {/* === SECTION 6: Analysis Progress or Start Button === */}
      {loading && analysisId ? (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-3 mb-4">
              <Loader2 className="w-5 h-5 text-green-600 animate-spin" />
              <span className="font-medium text-green-800">
                Analysis started - ID: {analysisId.substring(0, 8)}...
              </span>
            </div>
          </div>
          <AnalysisProgress
            analysisId={analysisId}
            onComplete={onAnalysisComplete}
            onError={onAnalysisError}
          />
        </div>
      ) : (
        <div className="flex gap-3 flex-wrap items-center">
          <button
            onClick={onStartAnalysis}
            disabled={isAnalysisDisabled}
            className={`
              px-8 py-3 rounded-lg font-semibold text-white
              transition-all duration-200
              flex items-center gap-2
              ${
                isAnalysisDisabled
                  ? 'bg-gray-400 cursor-not-allowed opacity-60'
                  : 'bg-green-600 hover:bg-green-700 active:scale-95 shadow-md hover:shadow-lg'
              }
            `}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
            Start Analysis
          </button>

          {!isAnalysisDisabled && (
            <div className="text-xs text-gray-500 flex items-center gap-2 px-4 py-3 bg-gray-50 rounded-lg border border-gray-200">
              <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>
                {selectedCollectors.length} collectors, region {regionMode}
                {uploadedDocuments.length > 0 && `, ${uploadedDocuments.length} documents`}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
