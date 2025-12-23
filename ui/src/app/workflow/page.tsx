'use client';

/**
 * Workflow Page - Thin wrapper around useWorkflow hook and Step components
 *
 * ARCHITECTURE:
 * - All state and API logic lives in hooks/useWorkflow.ts
 * - Each step is a separate component in components/*Step.tsx
 * - This file only handles routing between steps and passing props
 *
 * RULES FOR AI CODER:
 * - DO NOT add business logic here
 * - DO NOT add new state here (add to useWorkflow.ts)
 * - DO NOT modify Step components from here (edit them directly)
 * - Only change this file to add/remove step routing
 */

import { useState, useEffect } from 'react';
import { useWorkflow, WorkflowStep, WORKFLOW_STEPS } from './hooks/useWorkflow';
import {
  Stepper,
  SetupStep,
  ReadinessStep,
  AuditStep,
  ComplianceStep,
  CostStep,
  DocumentsStep,
  CompareStep,
  CompleteStep,
} from './components';
import DirectoryPicker from '@/components/DirectoryPicker';
import { getRegionalRates, RegionalRate } from '@/lib/profiles';
import { API_BASE, apiFetch } from '@/lib/api';

const API_URL = API_BASE || 'http://localhost:8000';

export default function WorkflowPage() {
  const workflow = useWorkflow();
  const [showDirectoryPicker, setShowDirectoryPicker] = useState(false);

  // Reference data loaded once
  const [regions, setRegions] = useState<RegionalRate[]>([]);
  const [complianceProfiles, setComplianceProfiles] = useState<any[]>([]);
  const [parsedContracts, setParsedContracts] = useState<any[]>([]);

  // Load reference data on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setRegions(getRegionalRates());
    }

    // Load compliance profiles
    apiFetch(`${API_URL}/api/contracts/profiles`)
      .then(res => res.json())
      .then(data => {
        setComplianceProfiles(data.profiles || []);
        if (data.profiles?.length > 0) {
          const components = (data.profiles[0].requirements || []).map((r: any, i: number) => ({
            id: `req_${i}`,
            name: r.name || r.description || `Requirement ${i + 1}`,
            enabled: true,
            source: 'profile' as const,
          }));
          workflow.setComplianceComponents(components);
        }
      })
      .catch(() => {});

    // Load parsed contracts
    apiFetch(`${API_URL}/api/contract-parser/parsed`)
      .then(res => res.json())
      .then(data => setParsedContracts(data.contracts || []))
      .catch(() => {});

    // Load methodologies
    apiFetch(`${API_URL}/api/estimate/methodologies`)
      .then(res => res.json())
      .then(data => workflow.setMethodologiesList(data.methodologies || []))
      .catch(() => {});

    // Load document templates
    apiFetch(`${API_URL}/api/settings/templates`)
      .then(res => res.json())
      .then(data => workflow.setDocumentTemplates(data.templates || []))
      .catch(() => {});
  }, []);

  // Handle analysis start and polling
  const handleStartAnalysis = async () => {
    const analysisId = await workflow.startAnalysis();
    if (analysisId) {
      workflow.pollAnalysis(analysisId);
    }
  };

  // Refresh contracts list after upload
  const refreshContracts = async () => {
    const res = await apiFetch(`${API_URL}/api/contract-parser/parsed`);
    const data = await res.json();
    setParsedContracts(data.contracts || []);
  };

  const handleUploadContract = async (file: File) => {
    await workflow.uploadContract(file);
    await refreshContracts();
  };

  const handleUploadMultiple = async (files: FileList) => {
    await workflow.uploadMultipleContracts(files);
    await refreshContracts();
  };

  const handleCreateDemo = async () => {
    await workflow.createDemoContract();
    await refreshContracts();
  };

  // Current step index for stepper
  const currentStepIndex = WORKFLOW_STEPS.findIndex(s => s.key === workflow.state.step);

  // Render current step
  const renderStep = () => {
    switch (workflow.state.step) {
      case WorkflowStep.Setup:
        return (
          <SetupStep
            sourceType={workflow.state.sourceType}
            repoUrl={workflow.state.repoUrl}
            localPath={workflow.state.localPath}
            branch={workflow.state.branch}
            regionMode={workflow.state.regionMode}
            selectedCollectors={workflow.state.selectedCollectors}
            collectorsList={workflow.state.collectorsList}
            validationResult={workflow.state.validationResult}
            isValidating={workflow.state.isValidating}
            loading={workflow.state.loading}
            error={workflow.state.error}
            analysisId={workflow.state.analysisId}
            analysisCategories={workflow.state.analysisCategories}
            projectType={workflow.state.projectType}
            baselineDocumentId={workflow.state.baselineDocumentId}
            onSourceTypeChange={workflow.setSourceType}
            onRepoUrlChange={workflow.setRepoUrl}
            onLocalPathChange={workflow.setLocalPath}
            onBranchChange={workflow.setBranch}
            onRegionModeChange={workflow.setRegionMode}
            onToggleCollector={workflow.toggleCollector}
            onStartAnalysis={handleStartAnalysis}
            onValidateSource={workflow.validateSource}
            onLoadCollectors={workflow.loadCollectors}
            onOpenDirectoryPicker={() => setShowDirectoryPicker(true)}
            onToggleAnalysisCategory={workflow.toggleAnalysisCategory}
            onProjectTypeChange={workflow.setProjectType}
            onBaselineDocumentChange={workflow.setBaselineDocumentId}
          />
        );

      case WorkflowStep.Readiness:
        return (
          <ReadinessStep
            readinessData={workflow.state.readinessData}
            loading={workflow.state.loading}
            onViewAuditResults={() => workflow.setStep(WorkflowStep.Audit)}
            onRunReadinessCheck={() => workflow.runReadinessCheck()}
          />
        );

      case WorkflowStep.Audit:
        return (
          <AuditStep
            analysisData={workflow.state.analysisData}
            analysisStages={workflow.state.analysisStages}
            loading={workflow.state.loading}
            onBackToReadiness={() => workflow.setStep(WorkflowStep.Readiness)}
            onGoToCompliance={() => workflow.setStep(WorkflowStep.Compliance)}
          />
        );

      case WorkflowStep.Compliance:
        return (
          <ComplianceStep
            complianceProfile={workflow.state.complianceProfile}
            complianceProfiles={complianceProfiles}
            complianceComponents={workflow.state.complianceComponents}
            complianceData={workflow.state.complianceData}
            customPolicyText={workflow.state.customPolicyText}
            loading={workflow.state.loading}
            onProfileChange={workflow.setComplianceProfile}
            onComponentToggle={workflow.toggleComplianceComponent}
            onAddCustomPolicy={workflow.addCustomCompliance}
            onCustomPolicyTextChange={workflow.setCustomPolicyText}
            onCheckCompliance={workflow.checkCompliance}
            onBack={() => workflow.setStep(WorkflowStep.Audit)}
            onContinue={() => workflow.setStep(WorkflowStep.Cost)}
          />
        );

      case WorkflowStep.Cost:
        return (
          <CostStep
            selectedRegion={workflow.state.selectedRegion}
            hourlyRate={workflow.state.hourlyRate}
            regions={regions}
            methodologiesList={workflow.state.methodologiesList}
            costEstimate={workflow.state.costEstimate}
            showAllMethodologies={workflow.state.showAllMethodologies}
            loading={workflow.state.loading}
            onRegionChange={workflow.setSelectedRegion}
            onHourlyRateChange={workflow.setHourlyRate}
            onToggleShowAll={() => workflow.setShowAllMethodologies(!workflow.state.showAllMethodologies)}
            onGetCostEstimate={workflow.getCostEstimate}
            onBack={() => workflow.setStep(WorkflowStep.Compliance)}
            onContinue={() => workflow.setStep(WorkflowStep.Documents)}
          />
        );

      case WorkflowStep.Documents:
        return (
          <DocumentsStep
            generatedDocs={workflow.state.generatedDocs}
            documentData={workflow.state.documentData}
            documentsByLevel={workflow.state.documentsByLevel}
            productLevel={workflow.state.analysisData?.product_level || null}
            loading={workflow.state.loading}
            onGenerateDocument={workflow.generateDocument}
            onDownloadDocument={workflow.downloadDocument}
            onContinue={() => workflow.setStep(WorkflowStep.Compare)}
          />
        );

      case WorkflowStep.Compare:
        return (
          <CompareStep
            parsedContracts={parsedContracts}
            selectedContract={workflow.state.selectedContract}
            comparisonData={workflow.state.comparisonData}
            uploadingContract={workflow.state.uploadingContract}
            loading={workflow.state.loading}
            onSelectContract={workflow.setSelectedContract}
            onUploadContract={handleUploadContract}
            onUploadMultipleContracts={handleUploadMultiple}
            onCreateDemoContract={handleCreateDemo}
            onRunComparison={workflow.runComparison}
            onComplete={() => workflow.setStep(WorkflowStep.Complete)}
          />
        );

      case WorkflowStep.Complete:
        return (
          <CompleteStep
            analysisData={workflow.state.analysisData}
            readinessData={workflow.state.readinessData}
            complianceData={workflow.state.complianceData}
            costEstimate={workflow.state.costEstimate}
            generatedDocs={workflow.state.generatedDocs}
            comparisonData={workflow.state.comparisonData}
            onResetWorkflow={workflow.resetWorkflow}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg, #f5f5f5)' }}>
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold" style={{ color: 'var(--color-text, #111827)' }}>
            Audit Workflow
          </h1>
          <p style={{ color: 'var(--color-text-muted, #6b7280)' }}>
            Complete repository evaluation with 8-step process
          </p>
        </div>

        {/* Stepper */}
        <div className="mb-8">
          <Stepper
            steps={WORKFLOW_STEPS}
            currentStep={workflow.state.step}
            onStepClick={(step) => {
              const stepIndex = WORKFLOW_STEPS.findIndex(s => s.key === step);
              if (stepIndex <= currentStepIndex) {
                workflow.setStep(step as WorkflowStep);
              }
            }}
          />
        </div>

        {/* Error Display */}
        {workflow.state.error && (
          <div
            className="mb-4 p-4 rounded-lg border"
            style={{
              backgroundColor: 'var(--color-error-bg, #fee2e2)',
              borderColor: 'var(--color-error, #b91c1c)',
              color: 'var(--color-error, #b91c1c)'
            }}
          >
            {workflow.state.error}
            <button
              onClick={() => workflow.setError(null)}
              className="ml-4 underline hover:no-underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Step Content */}
        <div
          className="rounded-xl shadow-sm border p-6"
          style={{
            backgroundColor: 'var(--color-surface, #ffffff)',
            borderColor: 'var(--color-border, #e5e7eb)'
          }}
        >
          {renderStep()}
        </div>
      </div>

      {/* Directory Picker Modal */}
      <DirectoryPicker
        isOpen={showDirectoryPicker}
        onClose={() => setShowDirectoryPicker(false)}
        onSelect={(path) => {
          workflow.setLocalPath(path);
          setShowDirectoryPicker(false);
        }}
      />
    </div>
  );
}
