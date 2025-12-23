'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';
import { ProductLevelBadge } from './ProductLevelBadge';

interface DocumentTemplate {
  type: string;
  name: string;
  description: string;
  category: string;
  estimated_pages: number;
  sections: string[];
  is_required: boolean;
  output_formats: string[];
}

interface DocumentPackage {
  product_level: string;
  is_platform_module: boolean;
  has_donors: boolean;
  base_documents: DocumentTemplate[];
  platform_documents: DocumentTemplate[];
  donor_documents: DocumentTemplate[];
  total_documents: number;
  total_pages: number;
}

interface MatrixSummary {
  [key: string]: {
    base: { count: number; pages: number };
    platform: { count: number; pages: number };
    donor: { count: number; pages: number };
    total: { count: number; pages: number };
  };
}

interface DocumentMatrixProps {
  productLevel: string;
  analysisId?: string;
  isPlatformModule?: boolean;
  hasDonors?: boolean;
  onGenerateDocument?: (docType: string) => void;
}

export function DocumentMatrix({
  productLevel,
  analysisId,
  isPlatformModule = false,
  hasDonors = false,
  onGenerateDocument,
}: DocumentMatrixProps) {
  const [documentPackage, setDocumentPackage] = useState<DocumentPackage | null>(null);
  const [matrixSummary, setMatrixSummary] = useState<MatrixSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingDoc, setGeneratingDoc] = useState<string | null>(null);
  const [showAllLevels, setShowAllLevels] = useState(false);
  const [gdriveConfigured, setGdriveConfigured] = useState<boolean>(false);
  const [uploadingToDrive, setUploadingToDrive] = useState<string | null>(null);
  const [showFolderPicker, setShowFolderPicker] = useState<boolean>(false);
  const [pendingUploadDocType, setPendingUploadDocType] = useState<string | null>(null);
  const [driveFolders, setDriveFolders] = useState<Array<{id: string; name: string}>>([]);
  const [currentDriveFolder, setCurrentDriveFolder] = useState<string | null>(null);
  const [driveFolderPath, setDriveFolderPath] = useState<Array<{id: string | null; name: string}>>([{id: null, name: 'Root'}]);
  const [loadingFolders, setLoadingFolders] = useState<boolean>(false);

  useEffect(() => {
    fetchDocumentPackage();
    fetchMatrixSummary();
    checkGdriveStatus();
  }, [productLevel, isPlatformModule, hasDonors]);

  const checkGdriveStatus = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/gdrive/status`);
      const data = await res.json();
      setGdriveConfigured(data.configured);
    } catch {
      setGdriveConfigured(false);
    }
  };

  const loadDriveFolders = async (folderId: string | null) => {
    setLoadingFolders(true);
    try {
      const url = folderId
        ? `${API_BASE}/api/gdrive/list?folder_id=${folderId}`
        : `${API_BASE}/api/gdrive/list`;
      const res = await apiFetch(url);
      if (!res.ok) throw new Error('Failed to load folders');
      const data = await res.json();
      // Filter only folders
      const folders = data.items.filter((item: any) => item.type === 'folder');
      setDriveFolders(folders);
    } catch {
      setDriveFolders([]);
    } finally {
      setLoadingFolders(false);
    }
  };

  const openFolderPicker = (docType: string) => {
    setPendingUploadDocType(docType);
    setShowFolderPicker(true);
    setCurrentDriveFolder(null);
    setDriveFolderPath([{id: null, name: 'Root'}]);
    loadDriveFolders(null);
  };

  const navigateToDriveFolder = (folder: {id: string; name: string}) => {
    setCurrentDriveFolder(folder.id);
    setDriveFolderPath([...driveFolderPath, folder]);
    loadDriveFolders(folder.id);
  };

  const navigateBackToFolder = (index: number) => {
    const newPath = driveFolderPath.slice(0, index + 1);
    setDriveFolderPath(newPath);
    const folderId = newPath[newPath.length - 1].id;
    setCurrentDriveFolder(folderId);
    loadDriveFolders(folderId);
  };

  const confirmFolderAndUpload = async () => {
    if (!pendingUploadDocType) return;
    setShowFolderPicker(false);
    await handleUploadToDrive(pendingUploadDocType, currentDriveFolder);
    setPendingUploadDocType(null);
  };

  const fetchDocumentPackage = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`${API_BASE}/api/documents/package`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_level: productLevel,
          is_platform_module: isPlatformModule,
          has_donors: hasDonors,
        }),
      });
      if (!response.ok) throw new Error('Failed to fetch document package');
      const data = await response.json();
      setDocumentPackage(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchMatrixSummary = async () => {
    try {
      const response = await apiFetch(`${API_BASE}/api/documents/matrix/summary`);
      if (!response.ok) throw new Error('Failed to fetch matrix summary');
      const data = await response.json();
      setMatrixSummary(data);
    } catch (err) {
      console.error('Failed to fetch matrix summary:', err);
    }
  };

  const handleGenerateDocument = async (docType: string) => {
    if (!analysisId) {
      alert('No analysis selected');
      return;
    }

    setGeneratingDoc(docType);
    try {
      const response = await apiFetch(`${API_BASE}/api/documents/generate-typed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_id: analysisId,
          document_type: docType,
          format: 'md',
          language: 'uk',
        }),
      });

      if (!response.ok) throw new Error('Failed to generate document');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${docType}-${analysisId}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      onGenerateDocument?.(docType);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate document');
    } finally {
      setGeneratingDoc(null);
    }
  };

  const handleUploadToDrive = async (docType: string, folderId: string | null = null) => {
    if (!analysisId) {
      alert('No analysis selected');
      return;
    }

    setUploadingToDrive(docType);
    try {
      // Generate document first
      const response = await apiFetch(`${API_BASE}/api/documents/generate-typed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_id: analysisId,
          document_type: docType,
          format: 'md',
          language: 'uk',
        }),
      });

      if (!response.ok) throw new Error('Failed to generate document');

      const blob = await response.blob();
      const arrayBuffer = await blob.arrayBuffer();
      const base64Content = btoa(
        new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      );

      // Upload to Google Drive
      const uploadPayload: any = {
        file_content: base64Content,
        file_name: `${docType}-${analysisId}.md`,
        mime_type: 'text/markdown',
      };
      if (folderId) {
        uploadPayload.folder_id = folderId;
      }

      const uploadResponse = await apiFetch(`${API_BASE}/api/gdrive/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(uploadPayload),
      });

      if (!uploadResponse.ok) throw new Error('Failed to upload to Google Drive');

      const result = await uploadResponse.json();
      alert(`Document uploaded to Google Drive!\nFile: ${result.name}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to upload to Google Drive');
    } finally {
      setUploadingToDrive(null);
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'base':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'platform':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'donor':
        return 'bg-green-100 text-green-700 border-green-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'base':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case 'platform':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        );
      case 'donor':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="bg-red-50 rounded-lg p-4 text-red-700">
          <p className="font-medium">Error loading document matrix</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!documentPackage) return null;

  const renderDocumentCard = (doc: DocumentTemplate) => (
    <div
      key={doc.type}
      className={`border rounded-lg p-4 transition-all hover:shadow-md ${getCategoryColor(doc.category)}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {getCategoryIcon(doc.category)}
          <h4 className="font-medium">{doc.name}</h4>
        </div>
        {doc.is_required && (
          <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">Required</span>
        )}
      </div>
      <p className="text-sm opacity-80 mb-3">{doc.description}</p>
      <div className="flex items-center justify-between text-xs">
        <span className="opacity-70">~{doc.estimated_pages} pages</span>
        <div className="flex gap-1">
          {doc.output_formats.map((fmt) => (
            <span key={fmt} className="uppercase px-1.5 py-0.5 bg-white/50 rounded">
              {fmt}
            </span>
          ))}
        </div>
      </div>
      {analysisId && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => handleGenerateDocument(doc.type)}
            disabled={generatingDoc === doc.type}
            className="flex-1 text-sm py-2 px-3 bg-white/80 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
          >
            {generatingDoc === doc.type ? 'Generating...' : 'Download'}
          </button>
          {gdriveConfigured && (
            <button
              onClick={() => openFolderPicker(doc.type)}
              disabled={uploadingToDrive === doc.type}
              className="text-sm py-2 px-3 bg-white/80 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
              title="Save to Google Drive"
            >
              {uploadingToDrive === doc.type ? (
                <span className="animate-spin">↻</span>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );

  const renderDocumentSection = (
    title: string,
    docs: DocumentTemplate[],
    category: string,
    description: string
  ) => {
    if (docs.length === 0) return null;

    return (
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-1.5 rounded-lg ${getCategoryColor(category)}`}>
            {getCategoryIcon(category)}
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{title}</h3>
            <p className="text-xs text-slate-500">{description}</p>
          </div>
          <span className="ml-auto text-sm text-slate-400">{docs.length} documents</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {docs.map(renderDocumentCard)}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Document Matrix</h2>
          <p className="text-sm text-slate-500 mt-1">
            Documents automatically selected based on product level
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ProductLevelBadge level={documentPackage.product_level} />
          <div className="text-right">
            <div className="text-2xl font-bold text-slate-900">{documentPackage.total_documents}</div>
            <div className="text-xs text-slate-500">{documentPackage.total_pages} pages total</div>
          </div>
        </div>
      </div>

      {/* Context Badges */}
      <div className="flex gap-2 mb-6">
        {isPlatformModule && (
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm">
            Platform Module
          </span>
        )}
        {hasDonors && (
          <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
            Has Donors
          </span>
        )}
      </div>

      {/* Document Sections */}
      {renderDocumentSection(
        'Base Documents',
        documentPackage.base_documents,
        'base',
        'Standard technical documentation'
      )}
      {renderDocumentSection(
        'Platform Documents',
        documentPackage.platform_documents,
        'platform',
        'Required for platform integration'
      )}
      {renderDocumentSection(
        'Donor Documents',
        documentPackage.donor_documents,
        'donor',
        'Required for donor reporting'
      )}

      {/* Matrix Overview Toggle */}
      <div className="mt-6 pt-6 border-t border-slate-200">
        <button
          onClick={() => setShowAllLevels(!showAllLevels)}
          className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
        >
          <svg
            className={`w-4 h-4 transition-transform ${showAllLevels ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          {showAllLevels ? 'Hide' : 'Show'} Document Matrix Overview
        </button>

        {showAllLevels && matrixSummary && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 font-medium text-slate-600">Product Level</th>
                  <th className="text-center py-2 px-3 font-medium text-slate-600">Base</th>
                  <th className="text-center py-2 px-3 font-medium text-slate-600">Platform</th>
                  <th className="text-center py-2 px-3 font-medium text-slate-600">Donor</th>
                  <th className="text-center py-2 px-3 font-medium text-slate-600">Total</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(matrixSummary).map(([level, data]) => (
                  <tr
                    key={level}
                    className={`border-b border-slate-100 ${
                      level === documentPackage.product_level ? 'bg-primary-50' : ''
                    }`}
                  >
                    <td className="py-2 px-3 font-medium">{level}</td>
                    <td className="text-center py-2 px-3">
                      {data.base.count} <span className="text-slate-400">({data.base.pages}p)</span>
                    </td>
                    <td className="text-center py-2 px-3">
                      {data.platform.count}{' '}
                      <span className="text-slate-400">({data.platform.pages}p)</span>
                    </td>
                    <td className="text-center py-2 px-3">
                      {data.donor.count} <span className="text-slate-400">({data.donor.pages}p)</span>
                    </td>
                    <td className="text-center py-2 px-3 font-semibold">
                      {data.total.count}{' '}
                      <span className="text-slate-400">({data.total.pages}p)</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Google Drive Folder Picker Modal */}
      {showFolderPicker && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="p-4 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-900">Select Google Drive Folder</h3>
                <button
                  onClick={() => {
                    setShowFolderPicker(false);
                    setPendingUploadDocType(null);
                  }}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {/* Breadcrumb */}
              <div className="flex items-center gap-1 mt-2 text-sm overflow-x-auto">
                {driveFolderPath.map((folder, index) => (
                  <div key={index} className="flex items-center">
                    {index > 0 && <span className="text-slate-400 mx-1">/</span>}
                    <button
                      onClick={() => navigateBackToFolder(index)}
                      className={`hover:text-primary-600 whitespace-nowrap ${
                        index === driveFolderPath.length - 1 ? 'font-medium text-slate-900' : 'text-slate-600'
                      }`}
                    >
                      {folder.name}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="max-h-64 overflow-y-auto">
              {loadingFolders ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
                </div>
              ) : driveFolders.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <svg className="w-10 h-10 mx-auto mb-2 text-slate-300" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
                  </svg>
                  <p className="text-sm">No folders found</p>
                  <p className="text-xs text-slate-400 mt-1">Upload here or go back</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {driveFolders.map((folder) => (
                    <button
                      key={folder.id}
                      onClick={() => navigateToDriveFolder(folder)}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 text-left"
                    >
                      <svg className="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2h-8l-2-2z" />
                      </svg>
                      <span className="text-slate-700 truncate">{folder.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">
                  Upload to: <span className="font-medium">{driveFolderPath[driveFolderPath.length - 1].name}</span>
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setShowFolderPicker(false);
                      setPendingUploadDocType(null);
                    }}
                    className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmFolderAndUpload}
                    className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    Upload Here
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
