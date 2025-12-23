'use client';

import React, { useState, useRef, useEffect } from 'react';
import { FileText, DollarSign, FileCheck, BarChart3, CheckCircle2, BookOpen, Download, Loader2, Upload, FileUp, Eye, Trash2, RefreshCw } from 'lucide-react';
import { API_BASE, apiFetch } from '@/lib/api';

interface DocumentInfo {
  generated_at?: string;
  type: string;
  content?: string;
  format?: string;
  download_url?: string;
}

interface RequiredDocument {
  id: string;
  name: string;
  required: boolean;
}

interface UploadedDocument {
  id: string;
  title: string;
  document_type: string;
  file_name: string | null;
  processing_status: string;
  extraction_confidence: number | null;
  created_at: string;
}

interface ContractData {
  contract_number?: string;
  contract_title?: string;
  contract_date?: string;
  total_amount?: number;
  currency?: string;
  client_name?: string;
  contractor_name?: string;
  work_plan?: Array<{ phase: string; description: string; duration_days?: number }>;
  budget_breakdown?: Array<{ category: string; amount_cents: number; description?: string }>;
}

interface DocumentsStepProps {
  generatedDocs: string[];
  documentData: { [docType: string]: DocumentInfo };
  documentsByLevel: { documents: RequiredDocument[] } | null;
  productLevel: string | null;
  loading: boolean;
  onGenerateDocument: (docType: string, format?: string) => void;
  onDownloadDocument: (docType: string, format?: string) => void;
  onContinue: () => void;
}

const DocumentCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  docType: string;
  isGenerated: boolean;
  loading: boolean;
  documentData: DocumentInfo | undefined;
  onGenerate: (docType: string) => void;
  onDownload: (docType: string, format: string) => void;
}> = ({
  icon,
  title,
  description,
  docType,
  isGenerated,
  loading,
  documentData,
  onGenerate,
  onDownload,
}) => {
  const formats = ['md', 'pdf', 'docx'];

  return (
    <div
      className={`rounded-lg border-2 p-6 transition-all ${
        isGenerated
          ? 'border-green-300 bg-green-50'
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <div className="text-2xl">{icon}</div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            {isGenerated && (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            )}
          </div>
          <p className="text-sm text-gray-600 mb-4">{description}</p>
        </div>
      </div>

      {isGenerated && documentData ? (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">
            Generated: {new Date(documentData.generated_at || '').toLocaleDateString()}
          </p>
          <div className="flex flex-wrap gap-2">
            {formats.map((format) => (
              <button
                key={format}
                onClick={() => onDownload(docType, format)}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1 rounded bg-green-100 text-green-700 text-xs font-medium hover:bg-green-200 disabled:opacity-50 transition-colors"
              >
                <Download className="w-3 h-3" />
                {format.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <button
          onClick={() => onGenerate(docType)}
          disabled={loading}
          className="w-full px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 flex items-center justify-center gap-2 transition-colors"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating...
            </>
          ) : (
            'Generate'
          )}
        </button>
      )}
    </div>
  );
};

// Source Documents Section - for uploading contracts/policies
const SourceDocumentsSection: React.FC<{
  analysisId?: string;
}> = ({ analysisId }) => {
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [contractData, setContractData] = useState<ContractData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setUploadedDocs(data.documents || []);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
    formData.append('document_type', 'contract');
    formData.append('storage_backend', 'local');
    if (analysisId) {
      formData.append('analysis_id', analysisId);
    }

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

  const handleExtract = async (docId: string) => {
    setExtracting(docId);
    setError(null);

    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: 'hybrid', task_type: 'contract' }),
      });

      if (res.ok) {
        await loadDocuments();
        const data = await res.json();
        if (data.success) {
          setContractData(data);
          setSelectedDoc(docId);
        }
      } else {
        const err = await res.json();
        setError(err.detail || 'Extraction failed');
      }
    } catch (err) {
      setError('Failed to extract data');
    }

    setExtracting(null);
  };

  const handleViewData = async (docId: string) => {
    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}/contract-data`);
      if (res.ok) {
        const data = await res.json();
        setContractData(data);
        setSelectedDoc(docId);
      }
    } catch (err) {
      setError('Failed to load contract data');
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      const res = await apiFetch(`${API_BASE}/api/document-management/documents/${docId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await loadDocuments();
        if (selectedDoc === docId) {
          setSelectedDoc(null);
          setContractData(null);
        }
      }
    } catch (err) {
      setError('Failed to delete document');
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
        {status}
        {confidence !== null && confidence !== undefined && ` (${confidence}%)`}
      </span>
    );
  };

  return (
    <section className="mb-8">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <FileUp className="w-5 h-5" />
          Source Documents
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Upload contracts and policies to extract data for comparison and analysis
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Upload & List */}
        <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white p-6">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={handleFileSelect}
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="w-full mb-4 px-4 py-3 rounded-lg border-2 border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors flex items-center justify-center gap-2 text-gray-600 hover:text-blue-600"
          >
            {uploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Upload Contract / Policy
              </>
            )}
          </button>

          {uploadedDocs.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-4">
              No documents uploaded yet
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {uploadedDocs.map((doc) => (
                <div
                  key={doc.id}
                  className={`p-3 rounded-lg border transition-colors ${
                    selectedDoc === doc.id
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 text-sm truncate">{doc.title}</p>
                      <p className="text-xs text-gray-500 truncate">{doc.file_name}</p>
                      <div className="mt-1 flex items-center gap-2">
                        {getStatusBadge(doc.processing_status, doc.extraction_confidence)}
                        <span className="text-xs text-gray-400">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {doc.processing_status === 'completed' ? (
                        <button
                          onClick={() => handleViewData(doc.id)}
                          className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-blue-600"
                          title="View extracted data"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleExtract(doc.id)}
                          disabled={extracting === doc.id}
                          className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-green-600 disabled:opacity-50"
                          title="Extract data"
                        >
                          {extracting === doc.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RefreshCw className="w-4 h-4" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-red-600"
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

        {/* Extracted Data Preview */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
            <Eye className="w-4 h-4" />
            Extracted Data
          </h3>

          {contractData ? (
            <div className="space-y-3 text-sm max-h-72 overflow-y-auto">
              {contractData.contract_number && (
                <div>
                  <span className="text-gray-500">Contract #:</span>{' '}
                  <span className="font-medium">{contractData.contract_number}</span>
                </div>
              )}
              {contractData.contract_title && (
                <div>
                  <span className="text-gray-500">Title:</span>{' '}
                  <span className="font-medium">{contractData.contract_title}</span>
                </div>
              )}
              {contractData.client_name && (
                <div>
                  <span className="text-gray-500">Client:</span>{' '}
                  <span className="font-medium">{contractData.client_name}</span>
                </div>
              )}
              {contractData.contractor_name && (
                <div>
                  <span className="text-gray-500">Contractor:</span>{' '}
                  <span className="font-medium">{contractData.contractor_name}</span>
                </div>
              )}
              {contractData.total_amount && (
                <div>
                  <span className="text-gray-500">Amount:</span>{' '}
                  <span className="font-medium">
                    {(contractData.total_amount / 100).toLocaleString()} {contractData.currency || 'USD'}
                  </span>
                </div>
              )}
              {contractData.work_plan && contractData.work_plan.length > 0 && (
                <div>
                  <span className="text-gray-500 block mb-1">Work Plan:</span>
                  <ul className="list-disc list-inside text-gray-700 space-y-1">
                    {contractData.work_plan.slice(0, 5).map((item, i) => (
                      <li key={i} className="truncate">{item.phase || item.description}</li>
                    ))}
                    {contractData.work_plan.length > 5 && (
                      <li className="text-gray-400">+{contractData.work_plan.length - 5} more...</li>
                    )}
                  </ul>
                </div>
              )}
              {contractData.budget_breakdown && contractData.budget_breakdown.length > 0 && (
                <div>
                  <span className="text-gray-500 block mb-1">Budget:</span>
                  <ul className="list-disc list-inside text-gray-700 space-y-1">
                    {contractData.budget_breakdown.slice(0, 3).map((item, i) => (
                      <li key={i}>
                        {item.category}: {(item.amount_cents / 100).toLocaleString()}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm text-center py-8">
              Select a document and extract data to view here
            </p>
          )}
        </div>
      </div>
    </section>
  );
};

const DocumentsStep: React.FC<DocumentsStepProps> = ({
  generatedDocs,
  documentData,
  documentsByLevel,
  productLevel,
  loading,
  onGenerateDocument,
  onDownloadDocument,
  onContinue,
}) => {
  const financialDocs = [
    {
      key: 'act_of_work',
      title: 'Act of Work',
      description: 'Document confirming completion of work and services rendered',
      icon: <FileText className="w-6 h-6 text-blue-600" />,
    },
    {
      key: 'invoice',
      title: 'Invoice',
      description: 'Financial invoice for services provided',
      icon: <DollarSign className="w-6 h-6 text-green-600" />,
    },
    {
      key: 'service_contract',
      title: 'Service Contract',
      description: 'Legal contract outlining service terms and conditions',
      icon: <FileCheck className="w-6 h-6 text-purple-600" />,
    },
  ];

  const auditDocs = [
    {
      key: 'analysis_report',
      title: 'Analysis Report',
      description: 'Comprehensive analysis of repository and codebase',
      icon: <BarChart3 className="w-6 h-6 text-indigo-600" />,
    },
    {
      key: 'acceptance_checklist',
      title: 'Acceptance Checklist',
      description: 'Verification checklist for project acceptance criteria',
      icon: <CheckCircle2 className="w-6 h-6 text-emerald-600" />,
    },
    {
      key: 'executive_summary',
      title: 'Executive Summary',
      description: 'High-level overview for decision makers',
      icon: <BookOpen className="w-6 h-6 text-amber-600" />,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Step 6: Generate Acceptance Documents
        </h1>
        <p className="text-gray-600">
          Generate comprehensive documentation for project acceptance and handover
        </p>
      </div>

      {/* Source Documents - Upload contracts/policies */}
      <SourceDocumentsSection />

      {/* Financial Documents Section */}
      <section>
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Financial Documents
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Essential documents for financial tracking and invoicing
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {financialDocs.map((doc) => (
            <DocumentCard
              key={doc.key}
              icon={doc.icon}
              title={doc.title}
              description={doc.description}
              docType={doc.key}
              isGenerated={generatedDocs.includes(doc.key)}
              loading={loading}
              documentData={documentData[doc.key]}
              onGenerate={onGenerateDocument}
              onDownload={onDownloadDocument}
            />
          ))}
        </div>
      </section>

      {/* Audit Reports Section */}
      <section>
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Audit Reports
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Analysis and verification documents for quality assurance
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {auditDocs.map((doc) => (
            <DocumentCard
              key={doc.key}
              icon={doc.icon}
              title={doc.title}
              description={doc.description}
              docType={doc.key}
              isGenerated={generatedDocs.includes(doc.key)}
              loading={loading}
              documentData={documentData[doc.key]}
              onGenerate={onGenerateDocument}
              onDownload={onDownloadDocument}
            />
          ))}
        </div>
      </section>

      {/* Required Documents by Product Level */}
      {documentsByLevel && documentsByLevel.documents.length > 0 && (
        <section>
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5" />
              Required Documents for {productLevel || 'Your Product Level'}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Documents required by your selected product level
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {documentsByLevel.documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 p-3 rounded-lg bg-gray-50"
                >
                  {doc.required ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
                  ) : (
                    <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{doc.name}</p>
                    {doc.required && (
                      <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                        Required
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Available Templates Info */}
      <section>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-6">
          <div className="flex gap-4">
            <BookOpen className="w-6 h-6 text-blue-600 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-blue-900 mb-1">
                Available Templates
              </h3>
              <p className="text-sm text-blue-800">
                All documents are generated using industry-standard templates customized
                for your project. You can download in multiple formats (Markdown, PDF,
                or Word) for maximum compatibility and easy sharing.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Continue Button */}
      <div className="flex justify-end pt-4 border-t border-gray-200">
        <button
          onClick={onContinue}
          disabled={loading}
          className="px-6 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:bg-gray-400 flex items-center gap-2 transition-colors"
        >
          Continue to Comparison
        </button>
      </div>
    </div>
  );
};

export default DocumentsStep;
