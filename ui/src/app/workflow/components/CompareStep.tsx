'use client';

import React, { useState } from 'react';

// Inline icons
const UploadIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
  </svg>
);

const AlertCircleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CheckCircleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const TrendingUpIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);

interface ParsedContract {
  id: string;
  filename?: string;
  contract_title?: string;
  contract_number?: string;
  work_plan?: any[];
  budget?: any[];
  total_budget?: number;
}

interface ComparisonData {
  overall_status: 'on_track' | 'at_risk' | 'off_track';
  overall_score: number;
  work_plan?: { status: string };
  budget?: { status: string };
  recommendations?: string[];
}

interface CompareStepProps {
  parsedContracts: ParsedContract[];
  selectedContract: string | null;
  comparisonData: ComparisonData | null;
  uploadingContract: boolean;
  loading: boolean;
  onSelectContract: (contractId: string) => void;
  onUploadContract: (file: File) => void;
  onUploadMultipleContracts: (files: FileList) => void;
  onCreateDemoContract: () => void;
  onRunComparison: () => void;
  onComplete: () => void;
}

const getStatusColor = (status: string): { bg: string; text: string; border: string } => {
  switch (status) {
    case 'on_track':
      return { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' };
    case 'at_risk':
      return { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' };
    case 'off_track':
      return { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
    default:
      return { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'on_track':
      return <CheckCircleIcon className="w-5 h-5 text-green-600" />;
    case 'at_risk':
      return <AlertCircleIcon className="w-5 h-5 text-yellow-600" />;
    case 'off_track':
      return <AlertCircleIcon className="w-5 h-5 text-red-600" />;
    default:
      return null;
  }
};

const getStatusLabel = (status: string): string => {
  switch (status) {
    case 'on_track':
      return 'On Track';
    case 'at_risk':
      return 'At Risk';
    case 'off_track':
      return 'Off Track';
    default:
      return 'Unknown';
  }
};

export default function CompareStep({
  parsedContracts,
  selectedContract,
  comparisonData,
  uploadingContract,
  loading,
  onSelectContract,
  onUploadContract,
  onUploadMultipleContracts,
  onCreateDemoContract,
  onRunComparison,
  onComplete,
}: CompareStepProps) {
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      if (files.length === 1) {
        onUploadContract(files[0]);
      } else {
        onUploadMultipleContracts(files);
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (files && files.length > 0) {
      if (files.length === 1) {
        onUploadContract(files[0]);
      } else {
        onUploadMultipleContracts(files);
      }
    }
  };

  const selectedContractData = parsedContracts.find(c => c.id === selectedContract);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-gray-200 pb-6">
        <h2 className="text-3xl font-bold text-gray-900">Step 7: Contract Comparison</h2>
        <p className="mt-2 text-gray-600">
          Upload a contract and compare it with your analysis to ensure alignment
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Contract</h3>

        {/* Drag and Drop Area */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition ${
            dragActive
              ? 'border-blue-500 bg-blue-100'
              : 'border-gray-300 bg-white hover:border-blue-400'
          }`}
        >
          <UploadIcon className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-sm text-gray-600 mb-2">
            Drag and drop your files here, or click to browse
          </p>
          <p className="text-xs text-gray-500 mb-4">Supports PDF, DOCX, and other formats</p>

          <input
            type="file"
            onChange={handleFileInput}
            disabled={uploadingContract}
            className="hidden"
            id="file-input-single"
          />
          <label
            htmlFor="file-input-single"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition disabled:bg-gray-400"
          >
            Upload Single File
          </label>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div>
            <input
              type="file"
              onChange={handleFileInput}
              disabled={uploadingContract}
              multiple
              className="hidden"
              id="file-input-multiple"
            />
            <label
              htmlFor="file-input-multiple"
              className="block w-full px-4 py-3 bg-indigo-600 text-white text-center rounded-lg cursor-pointer hover:bg-indigo-700 transition disabled:bg-gray-400 font-medium"
            >
              {uploadingContract ? 'Uploading...' : 'Upload Multiple Files'}
            </label>
          </div>

          <button
            onClick={onCreateDemoContract}
            disabled={uploadingContract || loading}
            className="w-full px-4 py-3 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition disabled:bg-gray-400 font-medium"
          >
            Use Demo Contract
          </button>

          <button
            disabled={true}
            className="w-full px-4 py-3 bg-gray-300 text-gray-600 rounded-lg cursor-not-allowed font-medium"
            title="Coming soon"
          >
            Template Library
          </button>
        </div>
      </div>

      {/* Parsed Contracts List */}
      {parsedContracts.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Contracts</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {parsedContracts.map(contract => (
              <div
                key={contract.id}
                onClick={() => onSelectContract(contract.id)}
                className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                  selectedContract === contract.id
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <p className="font-medium text-gray-900 truncate">{contract.filename}</p>
                <p className="text-sm text-gray-600 mt-1">
                  Contract: {contract.contract_number}
                </p>
                {contract.contract_title && <p className="text-sm text-gray-600">{contract.contract_title}</p>}
                <div className="flex gap-4 mt-3 text-xs text-gray-500">
                  <span>Activities: {contract.work_plan?.length ?? 0}</span>
                  <span>Budget Items: {contract.budget?.length ?? 0}</span>
                </div>
                {contract.total_budget !== undefined && (
                  <p className="text-sm font-semibold text-gray-900 mt-2">
                    Budget: ${contract.total_budget.toLocaleString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contract Selection and Comparison Button */}
      {parsedContracts.length > 0 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Contract for Comparison
            </label>
            <select
              value={selectedContract || ''}
              onChange={e => onSelectContract(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Choose a contract...</option>
              {parsedContracts.map(contract => (
                <option key={contract.id} value={contract.id}>
                  {contract.contract_number} - {contract.filename}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={onRunComparison}
            disabled={!selectedContract || loading}
            className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 transition disabled:from-gray-400 disabled:to-gray-400"
          >
            {loading ? 'Running Comparison...' : 'Run Comparison'}
          </button>
        </div>
      )}

      {/* Comparison Results */}
      {comparisonData && selectedContractData && (
        <div className="space-y-6 bg-gray-50 rounded-lg p-6 border border-gray-200">
          <h3 className="text-xl font-bold text-gray-900">Comparison Results</h3>

          {/* Status Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Overall Status Card */}
            <div
              className={`rounded-lg p-4 border-2 ${getStatusColor(
                comparisonData.overall_status
              ).bg} ${getStatusColor(comparisonData.overall_status).border}`}
            >
              <div className="flex items-center gap-2 mb-2">
                {getStatusIcon(comparisonData.overall_status)}
                <p className="text-sm font-medium text-gray-600">Overall Status</p>
              </div>
              <p
                className={`text-2xl font-bold ${getStatusColor(
                  comparisonData.overall_status
                ).text}`}
              >
                {getStatusLabel(comparisonData.overall_status)}
              </p>
            </div>

            {/* Score Card */}
            <div className="rounded-lg p-4 border-2 border-purple-200 bg-purple-50">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUpIcon className="w-5 h-5 text-purple-600" />
                <p className="text-sm font-medium text-gray-600">Overall Score</p>
              </div>
              <p className="text-2xl font-bold text-purple-700">
                {comparisonData.overall_score.toFixed(1)}%
              </p>
            </div>

            {/* Work Plan Status Card */}
            {comparisonData.work_plan && (
            <div
              className={`rounded-lg p-4 border-2 ${getStatusColor(
                comparisonData.work_plan.status
              ).bg} ${getStatusColor(comparisonData.work_plan.status).border}`}
            >
              <div className="flex items-center gap-2 mb-2">
                {getStatusIcon(comparisonData.work_plan.status)}
                <p className="text-sm font-medium text-gray-600">Work Plan</p>
              </div>
              <p
                className={`text-lg font-bold ${getStatusColor(
                  comparisonData.work_plan.status
                ).text}`}
              >
                {getStatusLabel(comparisonData.work_plan.status)}
              </p>
            </div>
            )}

            {/* Budget Status Card */}
            {comparisonData.budget && (
            <div
              className={`rounded-lg p-4 border-2 ${getStatusColor(
                comparisonData.budget.status
              ).bg} ${getStatusColor(comparisonData.budget.status).border}`}
            >
              <div className="flex items-center gap-2 mb-2">
                {getStatusIcon(comparisonData.budget.status)}
                <p className="text-sm font-medium text-gray-600">Budget</p>
              </div>
              <p
                className={`text-lg font-bold ${getStatusColor(
                  comparisonData.budget.status
                ).text}`}
              >
                {getStatusLabel(comparisonData.budget.status)}
              </p>
            </div>
            )}
          </div>

          {/* Recommendations */}
          {comparisonData.recommendations && comparisonData.recommendations.length > 0 && (
            <div className="bg-blue-50 border-l-4 border-blue-600 rounded-r-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-4">Recommendations</h4>
              <ul className="space-y-3">
                {comparisonData.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex gap-3 text-sm text-blue-900">
                    <span className="text-blue-600 font-bold flex-shrink-0">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Complete Workflow Button */}
      {comparisonData && (
        <div className="flex justify-end">
          <button
            onClick={onComplete}
            className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition"
          >
            Complete Workflow
          </button>
        </div>
      )}

      {/* Empty State */}
      {parsedContracts.length === 0 && !uploadingContract && (
        <div className="text-center py-12 border border-dashed border-gray-300 rounded-lg bg-gray-50">
          <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">No contracts uploaded yet</p>
          <p className="text-gray-500 text-sm mt-1">
            Upload a contract or use a demo contract to get started
          </p>
        </div>
      )}
    </div>
  );
}
