// app/workflow/hooks/useWorkflow.ts
// ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ ДЛЯ СОСТОЯНИЯ WORKFLOW
// Правила:
// 1. Добавлять новые функции - можно
// 2. Менять сигнатуры существующих функций - НЕЛЬЗЯ
// 3. Добавлять новые поля в WorkflowState - можно (дописывать в конец)

import { useState, useCallback, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

const API_URL = API_BASE || 'http://localhost:8000';

// LocalStorage keys for persistence
const STORAGE_KEYS = {
  ANALYSIS_ID: 'ra_workflow_analysis_id',
  REPO_URL: 'ra_workflow_repo_url',
  LOCAL_PATH: 'ra_workflow_local_path',
  SOURCE_TYPE: 'ra_workflow_source_type',
};

// ============================================================================
// TYPES - НЕ МЕНЯТЬ СУЩЕСТВУЮЩИЕ, ТОЛЬКО ДОПИСЫВАТЬ
// ============================================================================

export enum WorkflowStep {
  Setup = 'setup',
  Readiness = 'readiness',
  Audit = 'audit',
  Compliance = 'compliance',
  Cost = 'cost',
  Documents = 'documents',
  Compare = 'compare',
  Complete = 'complete',
}

export const WORKFLOW_STEPS = [
  { key: WorkflowStep.Setup, label: '1. Setup', description: 'Repository & Configuration' },
  { key: WorkflowStep.Readiness, label: '2. Readiness', description: 'Audit Readiness Check' },
  { key: WorkflowStep.Audit, label: '3. Audit', description: 'Full Analysis' },
  { key: WorkflowStep.Compliance, label: '4. Compliance', description: 'Policy Check' },
  { key: WorkflowStep.Cost, label: '5. Cost', description: 'Estimation' },
  { key: WorkflowStep.Documents, label: '6. Documents', description: 'Generate Acts' },
  { key: WorkflowStep.Compare, label: '7. Compare', description: 'Contract Comparison' },
  { key: WorkflowStep.Complete, label: '8. Complete', description: 'Summary' },
] as const;

export type SourceType = 'github' | 'gitlab' | 'local';

export interface AnalysisStage {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'done' | 'error';
  detail?: string;
}

export interface ComplianceComponent {
  id: string;
  name: string;
  enabled: boolean;
  source: 'profile' | 'custom';
}

export interface RepoHealth {
  documentation: number;
  structure: number;
  runability: number;
  commit_history: number;
  total: number;
}

export interface TechDebt {
  architecture: number;
  code_quality: number;
  testing: number;
  infrastructure: number;
  security_deps: number;
  total: number;
}

export interface AnalysisData {
  status: string;
  analysis_id?: string;
  repo_health?: RepoHealth;
  tech_debt?: TechDebt;
  product_level?: string;
  complexity?: string;
  total_files?: number;
  cost_estimate?: any;
  cost_estimates?: any;
  error_message?: string;
}

export interface ReadinessData {
  readiness_score: number;
  readiness_level: string;
  passed_checks: number;
  blockers_count: number;
  summary: string;
  next_steps: string[];
}

export interface ComplianceData {
  verdict: 'COMPLIANT' | 'PARTIAL' | 'NON_COMPLIANT';
  compliance_percent: number;
  passed: number;
  failed: number;
  critical_failed: number;
}

export interface CostMethodology {
  id: string;
  name: string;
  cost: number;
  hours: number;
  confidence?: string;
  description?: string;
}

export interface AIEfficiencyMode {
  hours: number;
  cost: number;
  efficiency_gain?: number;
}

export interface AIEfficiency {
  pure_human?: AIEfficiencyMode;
  ai_assisted?: AIEfficiencyMode;
  hybrid?: AIEfficiencyMode;
}

export interface CostEstimate {
  summary?: {
    average_cost: number;
    average_hours: number;
    cost_range: { min: number; max: number };
  };
  methodologies?: Array<{
    id: string;
    name: string;
    hours: number;
    cost: number;
    confidence: string;
  }>;
  ai_efficiency?: AIEfficiency;
}

export interface ComparisonData {
  overall_status: 'on_track' | 'at_risk' | 'off_track';
  overall_score: number;
  work_plan?: { status: string };
  budget?: { status: string };
  recommendations?: string[];
}

export interface WorkPlanItem {
  phase: string;
  description: string;
  duration?: number;
  start_date?: string;
  end_date?: string;
}

export interface BudgetItem {
  category: string;
  amount: number;
  description?: string;
  currency?: string;
}

export interface ParsedContract {
  id: string;
  filename?: string;
  contract_title?: string;
  contract_number?: string;
  work_plan?: WorkPlanItem[];
  budget?: BudgetItem[];
  total_budget?: number;
}

export interface DocumentData {
  generated_at: string;
  type: string;
  content?: string;
  format?: string;
  download_url?: string;
}

export interface DocumentTemplate {
  id: string;
  name: string;
  description?: string;
  category: string;
  format: string;
}

export interface RequiredDocument {
  id: string;
  name: string;
  required: boolean;
}

export interface DocumentsByLevel {
  documents: RequiredDocument[];
}

export interface CollectorInfo {
  id: string;
  name: string;
  description: string;
  required: boolean;
}

export interface ValidationResult {
  valid: boolean;
  accessible: boolean;
  message: string;
  detected_type?: string;
  is_git_repo?: boolean;
  detected_languages?: string[];
  file_count?: number;
  has_readme?: boolean;
  has_tests?: boolean;
  has_ci?: boolean;
}

// Analysis Categories - what user wants to analyze
export interface AnalysisCategory {
  id: string;
  name: string;
  description: string;
  icon: string;
  enabled: boolean;
  collectors: string[];  // Which collectors are needed
  requires?: {
    document?: boolean;  // Needs baseline document for compliance
    pricingProfile?: boolean;  // Needs pricing profile for cost
  };
}

export const DEFAULT_ANALYSIS_CATEGORIES: AnalysisCategory[] = [
  {
    id: 'state_quality',
    name: 'State & Quality',
    description: 'Repo health, tech debt, product level, complexity',
    icon: '📊',
    enabled: true,  // ON by default
    collectors: ['structure', 'git', 'static', 'coverage', 'pylint', 'complexity', 'duplication', 'dead_code', 'type_check'],
  },
  {
    id: 'security',
    name: 'Security',
    description: 'Vulnerabilities, secrets, dependency audit',
    icon: '🔒',
    enabled: true,  // ON by default
    collectors: ['security', 'pip_audit', 'secrets', 'dependencies'],
  },
  {
    id: 'ip_ownership',
    name: 'IP & Ownership',
    description: 'Authorship, bus factor, licenses, SBOM',
    icon: '📜',
    enabled: true,  // ON by default (was false)
    collectors: ['git_analytics', 'licenses', 'sbom'],
  },
  {
    id: 'compliance',
    name: 'Compliance',
    description: 'Check against TZ/contract requirements',
    icon: '✅',
    enabled: true,  // ON by default (was false)
    collectors: [],
    // NOTE: requires removed - category always available, just shows less data without docs
  },
  {
    id: 'cost',
    name: 'Cost Estimation',
    description: 'COCOMO, historical, activity breakdown',
    icon: '💰',
    enabled: true,  // ON by default
    collectors: ['static', 'git'],
  },
];

// Project type affects scoring thresholds
export type ProjectType = 'rnd' | 'internal' | 'production' | 'grant';

export interface ProjectTypeOption {
  id: ProjectType;
  name: string;
  description: string;
}

export const PROJECT_TYPES: ProjectTypeOption[] = [
  { id: 'rnd', name: 'R&D / Spike', description: 'Experimental, proof of concept' },
  { id: 'internal', name: 'Internal Tool', description: 'Internal use, limited users' },
  { id: 'production', name: 'Production', description: 'Customer-facing, SLA required' },
  { id: 'grant', name: 'Grant Project', description: 'Funded project with compliance requirements' },
];

export interface WorkflowState {
  // Navigation
  step: WorkflowStep;

  // Setup
  sourceType: SourceType;
  repoUrl: string;
  localPath: string;
  branch: string;
  regionMode: 'EU' | 'UA' | 'EU_UA';
  selectedCollectors: string[];
  collectorsList: CollectorInfo[];
  selectedProfiles: string[];
  validationResult: ValidationResult | null;
  isValidating: boolean;

  // NEW: Analysis Configuration
  analysisCategories: AnalysisCategory[];
  projectType: ProjectType;
  baselineDocumentId: string | null;  // Selected TZ/contract for compliance
  scoringProfileId: string | null;
  pricingProfileId: string | null;

  // Cost settings
  selectedRegion: string;
  hourlyRate: number;

  // Analysis
  analysisId: string | null;
  analysisData: AnalysisData | null;
  analysisStages: AnalysisStage[];

  // Readiness
  readinessData: ReadinessData | null;

  // Compliance
  complianceProfile: string;
  complianceData: ComplianceData | null;
  complianceComponents: ComplianceComponent[];
  customPolicyText: string;

  // Cost
  costEstimate: CostEstimate | null;
  showAllMethodologies: boolean;
  methodologiesList: CostMethodology[];

  // Documents
  generatedDocs: string[];
  documentData: { [key: string]: DocumentData };
  documentTemplates: DocumentTemplate[];
  documentsByLevel: DocumentsByLevel | null;

  // Compare
  selectedContract: string | null;
  comparisonData: ComparisonData | null;
  uploadingContract: boolean;
  uploadedFiles: File[];

  // UI
  loading: boolean;
  error: string | null;
}

const INITIAL_STAGES: AnalysisStage[] = [
  { id: 'fetch', label: 'Fetching Repository', status: 'pending' },
  { id: 'structure', label: 'Analyzing Structure', status: 'pending' },
  { id: 'static', label: 'Static Analysis', status: 'pending' },
  { id: 'metrics', label: 'Computing Metrics', status: 'pending' },
  { id: 'scoring', label: 'Scoring & Classification', status: 'pending' },
  { id: 'tasks', label: 'Generating Tasks', status: 'pending' },
];

const INITIAL_STATE: WorkflowState = {
  step: WorkflowStep.Setup,
  sourceType: 'github',
  repoUrl: '',
  localPath: '',
  branch: 'main',
  regionMode: 'EU_UA',
  selectedCollectors: ['structure', 'git', 'static'],
  collectorsList: [],
  selectedProfiles: [],
  validationResult: null,
  isValidating: false,
  // NEW: Analysis Configuration
  analysisCategories: DEFAULT_ANALYSIS_CATEGORIES,
  projectType: 'internal',
  baselineDocumentId: null,
  scoringProfileId: null,
  pricingProfileId: null,
  // Cost settings
  selectedRegion: 'ua',
  hourlyRate: 35,
  analysisId: null,
  analysisData: null,
  analysisStages: INITIAL_STAGES,
  readinessData: null,
  complianceProfile: 'global_fund_r13',
  complianceData: null,
  complianceComponents: [],
  customPolicyText: '',
  costEstimate: null,
  showAllMethodologies: false,
  methodologiesList: [],
  generatedDocs: [],
  documentData: {},
  documentTemplates: [],
  documentsByLevel: null,
  selectedContract: null,
  comparisonData: null,
  uploadingContract: false,
  uploadedFiles: [],
  loading: false,
  error: null,
};

// ============================================================================
// HOOK
// ============================================================================

export function useWorkflow() {
  const [state, setState] = useState<WorkflowState>(INITIAL_STATE);
  const [isInitialized, setIsInitialized] = useState(false);

  // ---------------------------------------------------------------------------
  // LOCALSTORAGE PERSISTENCE
  // ---------------------------------------------------------------------------

  // Load from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const savedAnalysisId = localStorage.getItem(STORAGE_KEYS.ANALYSIS_ID);
    const savedRepoUrl = localStorage.getItem(STORAGE_KEYS.REPO_URL);
    const savedLocalPath = localStorage.getItem(STORAGE_KEYS.LOCAL_PATH);
    const savedSourceType = localStorage.getItem(STORAGE_KEYS.SOURCE_TYPE) as SourceType | null;

    if (savedAnalysisId || savedRepoUrl || savedLocalPath) {
      setState(s => ({
        ...s,
        analysisId: savedAnalysisId || null,
        repoUrl: savedRepoUrl || '',
        localPath: savedLocalPath || '',
        sourceType: savedSourceType || 'github',
        // If we have a saved analysisId, show loading indicator
        loading: !!savedAnalysisId,
      }));
    }
    setIsInitialized(true);
  }, []);

  // Save to localStorage when state changes
  useEffect(() => {
    if (typeof window === 'undefined' || !isInitialized) return;

    if (state.analysisId) {
      localStorage.setItem(STORAGE_KEYS.ANALYSIS_ID, state.analysisId);
    } else {
      localStorage.removeItem(STORAGE_KEYS.ANALYSIS_ID);
    }

    if (state.repoUrl) {
      localStorage.setItem(STORAGE_KEYS.REPO_URL, state.repoUrl);
    }

    if (state.localPath) {
      localStorage.setItem(STORAGE_KEYS.LOCAL_PATH, state.localPath);
    }

    localStorage.setItem(STORAGE_KEYS.SOURCE_TYPE, state.sourceType);
  }, [state.analysisId, state.repoUrl, state.localPath, state.sourceType, isInitialized]);

  // Resume analysis from localStorage if available
  useEffect(() => {
    if (!isInitialized || !state.analysisId) return;

    // Check if analysis is still running and resume polling
    const checkAndResume = async () => {
      try {
        const res = await apiFetch(`${API_URL}/api/analysis/${state.analysisId}`);
        const data = await res.json();

        if (data.status === 'completed') {
          // Analysis already completed - load data
          setState(s => ({
            ...s,
            analysisData: data,
            loading: false,
            step: WorkflowStep.Readiness,
          }));

          // Load documents by product level
          if (data.product_level) {
            try {
              const levelMap: { [key: string]: string } = {
                'rnd_spike': 'R&D Spike',
                'prototype': 'Prototype',
                'internal_tool': 'Internal Tool',
                'platform_module': 'Platform Module Candidate',
                'near_product': 'Near-Product',
              };
              const level = levelMap[data.product_level] || 'Prototype';
              const docRes = await apiFetch(`${API_URL}/api/documents/matrix/${encodeURIComponent(level)}`);
              const docData = await docRes.json();
              setState(s => ({ ...s, documentsByLevel: docData }));
            } catch {}
          }
        } else if (data.status === 'running' || data.status === 'pending') {
          // Analysis still running - keep loading=true, UI will connect to WebSocket
          setState(s => ({ ...s, loading: true }));
        } else if (data.status === 'failed') {
          setState(s => ({
            ...s,
            error: data.error_message || 'Analysis failed',
            loading: false,
          }));
          // Clear saved analysis ID on failure
          localStorage.removeItem(STORAGE_KEYS.ANALYSIS_ID);
        }
      } catch (err) {
        // Analysis not found - clear localStorage
        localStorage.removeItem(STORAGE_KEYS.ANALYSIS_ID);
        setState(s => ({ ...s, analysisId: null, loading: false }));
      }
    };

    checkAndResume();
  }, [isInitialized, state.analysisId]);

  // ---------------------------------------------------------------------------
  // SETTERS - простые обновления состояния
  // ---------------------------------------------------------------------------

  const setStep = useCallback((step: WorkflowStep) => {
    setState(s => ({ ...s, step }));
  }, []);

  const setSourceType = useCallback((sourceType: SourceType) => {
    setState(s => ({ ...s, sourceType }));
  }, []);

  const setRepoUrl = useCallback((repoUrl: string) => {
    setState(s => ({ ...s, repoUrl }));
  }, []);

  const setLocalPath = useCallback((localPath: string) => {
    setState(s => ({ ...s, localPath }));
  }, []);

  const setBranch = useCallback((branch: string) => {
    setState(s => ({ ...s, branch }));
  }, []);

  const setSelectedRegion = useCallback((selectedRegion: string) => {
    setState(s => ({ ...s, selectedRegion }));
  }, []);

  const setHourlyRate = useCallback((hourlyRate: number) => {
    setState(s => ({ ...s, hourlyRate }));
  }, []);

  const setComplianceProfile = useCallback((complianceProfile: string) => {
    setState(s => ({ ...s, complianceProfile }));
  }, []);

  const setSelectedContract = useCallback((selectedContract: string | null) => {
    setState(s => ({ ...s, selectedContract }));
  }, []);

  const setShowAllMethodologies = useCallback((show: boolean) => {
    setState(s => ({ ...s, showAllMethodologies: show }));
  }, []);

  const setCustomPolicyText = useCallback((text: string) => {
    setState(s => ({ ...s, customPolicyText: text }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(s => ({ ...s, error }));
  }, []);

  const setComplianceComponents = useCallback((components: ComplianceComponent[]) => {
    setState(s => ({ ...s, complianceComponents: components }));
  }, []);

  const setMethodologiesList = useCallback((methodologies: CostMethodology[]) => {
    setState(s => ({ ...s, methodologiesList: methodologies }));
  }, []);

  const setDocumentTemplates = useCallback((templates: DocumentTemplate[]) => {
    setState(s => ({ ...s, documentTemplates: templates }));
  }, []);

  const setRegionMode = useCallback((mode: 'EU' | 'UA' | 'EU_UA') => {
    setState(s => ({ ...s, regionMode: mode }));
  }, []);

  const setSelectedCollectors = useCallback((collectors: string[]) => {
    setState(s => ({ ...s, selectedCollectors: collectors }));
  }, []);

  const toggleCollector = useCallback((collectorId: string) => {
    setState(s => {
      const collector = s.collectorsList.find(c => c.id === collectorId);
      if (collector?.required) return s;
      const isSelected = s.selectedCollectors.includes(collectorId);
      return {
        ...s,
        selectedCollectors: isSelected
          ? s.selectedCollectors.filter(id => id !== collectorId)
          : [...s.selectedCollectors, collectorId],
      };
    });
  }, []);

  const setCollectorsList = useCallback((collectors: CollectorInfo[]) => {
    setState(s => ({
      ...s,
      collectorsList: collectors,
      selectedCollectors: collectors.filter(c => c.required).map(c => c.id),
    }));
  }, []);

  const setSelectedProfiles = useCallback((profiles: string[]) => {
    setState(s => ({ ...s, selectedProfiles: profiles }));
  }, []);

  // NEW: Analysis Configuration setters
  const setProjectType = useCallback((projectType: ProjectType) => {
    setState(s => ({ ...s, projectType }));
  }, []);

  const setBaselineDocumentId = useCallback((id: string | null) => {
    setState(s => ({ ...s, baselineDocumentId: id }));
  }, []);

  const setScoringProfileId = useCallback((id: string | null) => {
    setState(s => ({ ...s, scoringProfileId: id }));
  }, []);

  const setPricingProfileId = useCallback((id: string | null) => {
    setState(s => ({ ...s, pricingProfileId: id }));
  }, []);

  const toggleAnalysisCategory = useCallback((categoryId: string) => {
    setState(s => ({
      ...s,
      analysisCategories: s.analysisCategories.map(cat =>
        cat.id === categoryId ? { ...cat, enabled: !cat.enabled } : cat
      ),
    }));
  }, []);

  const getEnabledCollectors = useCallback(() => {
    // Collect all collectors from enabled categories
    const collectors = new Set<string>();
    state.analysisCategories
      .filter(cat => cat.enabled)
      .forEach(cat => cat.collectors.forEach(c => collectors.add(c)));
    return Array.from(collectors);
  }, [state.analysisCategories]);

  // ---------------------------------------------------------------------------
  // HELPERS
  // ---------------------------------------------------------------------------

  const getRepoSource = useCallback(() => {
    return state.sourceType === 'local' ? state.localPath : state.repoUrl;
  }, [state.sourceType, state.localPath, state.repoUrl]);

  const updateStage = useCallback((stageId: string, status: 'running' | 'done' | 'error') => {
    setState(s => ({
      ...s,
      analysisStages: s.analysisStages.map(stage =>
        stage.id === stageId ? { ...stage, status } : stage
      ),
    }));
  }, []);

  // ---------------------------------------------------------------------------
  // STEP 1: SETUP - Validate Source & Load Collectors
  // ---------------------------------------------------------------------------

  const loadCollectors = useCallback(async () => {
    try {
      const res = await apiFetch(`${API_URL}/api/collectors`);
      const data = await res.json();
      if (data.collectors) {
        setCollectorsList(data.collectors);
      }
    } catch (err) {
      console.error('Failed to load collectors:', err);
    }
  }, []);

  const validateSource = useCallback(async () => {
    const source = state.sourceType === 'local' ? state.localPath : state.repoUrl;
    if (!source) {
      setState(s => ({ ...s, error: 'Please provide a repository URL or path' }));
      return null;
    }

    setState(s => ({ ...s, isValidating: true, error: null, validationResult: null }));

    try {
      const res = await apiFetch(`${API_URL}/api/validate-source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: source,
          source_type: state.sourceType,
          branch: state.branch || undefined,
        }),
      });

      const data = await res.json();
      setState(s => ({
        ...s,
        validationResult: data,
        isValidating: false,
        error: !data.accessible ? data.message : null,
      }));
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Validation failed';
      setState(s => ({
        ...s,
        isValidating: false,
        error: message,
        validationResult: null,
      }));
      return null;
    }
  }, [state.sourceType, state.localPath, state.repoUrl, state.branch]);

  // ---------------------------------------------------------------------------
  // STEP 1: SETUP - Start Analysis
  // ---------------------------------------------------------------------------

  const startAnalysis = useCallback(async () => {
    const source = state.sourceType === 'local' ? state.localPath : state.repoUrl;
    if (!source) {
      setState(s => ({ ...s, error: 'Please provide a repository URL or path' }));
      return;
    }

    setState(s => ({ ...s, loading: true, error: null }));

    try {
      const res = await apiFetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: source,
          branch: state.branch || 'main',
          region_mode: state.regionMode,
          source_type: state.sourceType,
          collectors: state.selectedCollectors.length > 0 ? state.selectedCollectors : undefined,
          profiles: state.selectedProfiles.length > 0 ? state.selectedProfiles : undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start analysis');

      // Stay on Setup step - progress will be shown there via AnalysisProgress component
      setState(s => ({
        ...s,
        analysisId: data.analysis_id,
        // Don't change step - stay on Setup to show progress
        analysisStages: INITIAL_STAGES,
      }));

      return data.analysis_id;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed';
      setState(s => ({ ...s, error: message, loading: false }));
      return null;
    }
  }, [state.sourceType, state.localPath, state.repoUrl, state.branch, state.selectedRegion]);

  // ---------------------------------------------------------------------------
  // STEP 3: AUDIT - Poll Analysis
  // ---------------------------------------------------------------------------

  const pollAnalysis = useCallback(async (analysisId: string) => {
    const stageOrder = ['fetch', 'structure', 'static', 'metrics', 'scoring', 'tasks'];
    let attempts = 0;
    const maxAttempts = 120;

    const poll = async (): Promise<void> => {
      try {
        const res = await apiFetch(`${API_URL}/api/analysis/${analysisId}`);
        const data = await res.json();

        // Update stages based on progress
        const currentStageIdx = Math.min(Math.floor(attempts / 3), stageOrder.length - 1);
        stageOrder.forEach((stageId, idx) => {
          if (idx < currentStageIdx) {
            updateStage(stageId, 'done');
          } else if (idx === currentStageIdx) {
            updateStage(stageId, 'running');
          }
        });

        if (data.status === 'completed') {
          stageOrder.forEach(stageId => updateStage(stageId, 'done'));
          setState(s => ({ ...s, analysisData: data, loading: false }));

          // Load documents by product level
          if (data.product_level) {
            await loadDocumentsByLevel(data.product_level);
          }

          // Auto-run readiness check
          await runReadinessCheck(data);
        } else if (data.status === 'failed') {
          updateStage(stageOrder[currentStageIdx], 'error');
          setState(s => ({
            ...s,
            error: data.error_message || 'Analysis failed',
            loading: false
          }));
        } else if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 2000);
        } else {
          setState(s => ({ ...s, error: 'Analysis timed out', loading: false }));
        }
      } catch {
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 2000);
        }
      }
    };

    poll();
  }, [updateStage]);

  // ---------------------------------------------------------------------------
  // STEP 2: READINESS - Check Readiness
  // ---------------------------------------------------------------------------

  const runReadinessCheck = useCallback(async (analysisData?: AnalysisData | null) => {
    const data = analysisData || state.analysisData;
    if (!data?.repo_health || !data?.tech_debt) return;

    try {
      const res = await apiFetch(`${API_URL}/api/readiness/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_health: data.repo_health,
          tech_debt: data.tech_debt,
          product_level: data.product_level || 'beta',
          complexity: data.complexity || 'moderate',
        }),
      });

      const readiness = await res.json();
      setState(s => ({ ...s, readinessData: readiness, step: WorkflowStep.Readiness }));
    } catch (err) {
      console.error('Readiness check failed:', err);
    }
  }, [state.analysisData]);

  // ---------------------------------------------------------------------------
  // STEP 4: COMPLIANCE - Check Compliance
  // ---------------------------------------------------------------------------

  const checkCompliance = useCallback(async () => {
    if (!state.analysisData?.repo_health) {
      setState(s => ({ ...s, error: 'No analysis data available' }));
      return;
    }

    setState(s => ({ ...s, loading: true, error: null }));

    try {
      const res = await apiFetch(`${API_URL}/api/contracts/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract_profile_id: state.complianceProfile,
          repo_health: state.analysisData.repo_health,
          tech_debt: state.analysisData.tech_debt,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Compliance check failed');

      setState(s => ({ ...s, complianceData: data, step: WorkflowStep.Cost, loading: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Compliance check failed';
      setState(s => ({ ...s, error: message, loading: false }));
    }
  }, [state.analysisData, state.complianceProfile]);

  // ---------------------------------------------------------------------------
  // STEP 5: COST - Get Cost Estimate
  // ---------------------------------------------------------------------------

  const getCostEstimate = useCallback(async () => {
    if (!state.analysisData?.cost_estimates && !state.analysisData?.cost_estimate) {
      setState(s => ({ ...s, error: 'No cost data available' }));
      return;
    }

    setState(s => ({ ...s, loading: true, error: null }));

    try {
      const costData = state.analysisData.cost_estimate || state.analysisData.cost_estimates;
      const loc = costData?.kloc ? Math.round(costData.kloc * 1000) : 10000;
      const complexity = state.analysisData.complexity === 'high' ? 2.0 :
                        state.analysisData.complexity === 'low' ? 1.0 : 1.5;

      const res = await apiFetch(`${API_URL}/api/estimate/comprehensive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loc,
          complexity,
          hourly_rate: state.hourlyRate,
          include_pert: true,
          include_ai_efficiency: true,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Cost estimation failed');

      setState(s => ({ ...s, costEstimate: data, step: WorkflowStep.Documents, loading: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Cost estimation failed';
      setState(s => ({ ...s, error: message, loading: false }));
    }
  }, [state.analysisData, state.hourlyRate]);

  // ---------------------------------------------------------------------------
  // STEP 6: DOCUMENTS - Generate & Download
  // ---------------------------------------------------------------------------

  const loadDocumentsByLevel = useCallback(async (productLevel: string) => {
    try {
      const levelMap: { [key: string]: string } = {
        'rnd_spike': 'R&D Spike',
        'prototype': 'Prototype',
        'internal_tool': 'Internal Tool',
        'platform_module': 'Platform Module Candidate',
        'near_product': 'Near-Product',
      };
      const level = levelMap[productLevel] || 'Prototype';
      const res = await apiFetch(`${API_URL}/api/documents/matrix/${encodeURIComponent(level)}`);
      const data = await res.json();
      setState(s => ({ ...s, documentsByLevel: data }));
    } catch (err) {
      console.error('Failed to load documents by level:', err);
    }
  }, []);

  const generateDocument = useCallback(async (docType: string, format: string = 'md') => {
    setState(s => ({ ...s, loading: true, error: null }));

    try {
      const res = await apiFetch(`${API_URL}/api/documents/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_type: docType,
          format,
          analysis_data: state.analysisData,
          cost_data: state.costEstimate,
          compliance_data: state.complianceData,
        }),
      });

      const data = await res.json();

      setState(s => ({
        ...s,
        loading: false,
        generatedDocs: s.generatedDocs.includes(docType) ? s.generatedDocs : [...s.generatedDocs, docType],
        documentData: {
          ...s.documentData,
          [docType]: {
            generated_at: new Date().toISOString(),
            type: docType,
            content: data.content,
            format,
            download_url: data.download_url,
          }
        }
      }));
    } catch (err) {
      // Fallback: mark as generated even if API fails
      setState(s => ({
        ...s,
        loading: false,
        generatedDocs: s.generatedDocs.includes(docType) ? s.generatedDocs : [...s.generatedDocs, docType],
        documentData: {
          ...s.documentData,
          [docType]: {
            generated_at: new Date().toISOString(),
            type: docType,
          }
        }
      }));
    }
  }, [state.analysisData, state.costEstimate, state.complianceData]);

  const downloadDocument = useCallback((docType: string, format: string = 'md') => {
    try {
      const analysisId = state.analysisId || 'manual';
      const url = `${API_URL}/api/documents/${analysisId}/${format}`;
      window.open(url, '_blank');
    } catch (err) {
      const docData = state.documentData[docType];
      if (docData?.content) {
        const blob = new Blob([docData.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${docType}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    }
  }, [state.analysisId, state.documentData]);

  // ---------------------------------------------------------------------------
  // STEP 7: COMPARE - Contract Comparison
  // ---------------------------------------------------------------------------

  const uploadContract = useCallback(async (file: File) => {
    setState(s => ({ ...s, uploadingContract: true, error: null }));

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('contract_name', file.name);

      const res = await apiFetch(`${API_URL}/api/contract-parser/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      setState(s => ({ ...s, selectedContract: data.contract_id, uploadingContract: false }));
      return data.contract_id;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setState(s => ({ ...s, error: message, uploadingContract: false }));
      return null;
    }
  }, []);

  const uploadMultipleContracts = useCallback(async (files: FileList) => {
    setState(s => ({ ...s, uploadingContract: true, uploadedFiles: Array.from(files), error: null }));

    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('contract_name', file.name);

        await apiFetch(`${API_URL}/api/contract-parser/upload`, {
          method: 'POST',
          body: formData,
        });
      }

      setState(s => ({ ...s, uploadingContract: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setState(s => ({ ...s, error: message, uploadingContract: false }));
    }
  }, []);

  const createDemoContract = useCallback(async () => {
    setState(s => ({ ...s, uploadingContract: true, error: null }));

    try {
      const res = await apiFetch(`${API_URL}/api/contract-parser/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create demo');

      setState(s => ({ ...s, selectedContract: data.id, uploadingContract: false }));
      return data.id;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Demo creation failed';
      setState(s => ({ ...s, error: message, uploadingContract: false }));
      return null;
    }
  }, []);

  const runComparison = useCallback(async () => {
    if (!state.selectedContract || !state.analysisData) {
      setState(s => ({ ...s, error: 'Select a contract first' }));
      return;
    }

    setState(s => ({ ...s, loading: true, error: null }));

    try {
      const res = await apiFetch(`${API_URL}/api/contract-parser/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract_id: state.selectedContract,
          analysis_data: {
            repo_health: state.analysisData.repo_health,
            tech_debt: state.analysisData.tech_debt,
            cost: state.analysisData.cost_estimates || state.analysisData.cost_estimate,
          },
          project_progress: {},
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Comparison failed');

      setState(s => ({ ...s, comparisonData: data, step: WorkflowStep.Complete, loading: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Comparison failed';
      setState(s => ({ ...s, error: message, loading: false }));
    }
  }, [state.selectedContract, state.analysisData]);

  // ---------------------------------------------------------------------------
  // COMPLIANCE COMPONENTS
  // ---------------------------------------------------------------------------

  const addCustomCompliance = useCallback((text: string) => {
    if (!text.trim()) return;
    const newComponent: ComplianceComponent = {
      id: `custom_${Date.now()}`,
      name: text.trim(),
      enabled: true,
      source: 'custom',
    };
    setState(s => ({
      ...s,
      complianceComponents: [...s.complianceComponents, newComponent],
      customPolicyText: '',
    }));
  }, []);

  const toggleComplianceComponent = useCallback((id: string) => {
    setState(s => ({
      ...s,
      complianceComponents: s.complianceComponents.map(c =>
        c.id === id ? { ...c, enabled: !c.enabled } : c
      ),
    }));
  }, []);

  // ---------------------------------------------------------------------------
  // RESET
  // ---------------------------------------------------------------------------

  const resetWorkflow = useCallback(() => {
    // Clear localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEYS.ANALYSIS_ID);
      localStorage.removeItem(STORAGE_KEYS.REPO_URL);
      localStorage.removeItem(STORAGE_KEYS.LOCAL_PATH);
      localStorage.removeItem(STORAGE_KEYS.SOURCE_TYPE);
    }
    setState(INITIAL_STATE);
  }, []);

  // Clear localStorage when analysis completes successfully (to start fresh next time)
  const clearAnalysisFromStorage = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEYS.ANALYSIS_ID);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // RETURN
  // ---------------------------------------------------------------------------

  return {
    // State
    state,

    // Simple setters
    setStep,
    setSourceType,
    setRepoUrl,
    setLocalPath,
    setBranch,
    setSelectedRegion,
    setHourlyRate,
    setComplianceProfile,
    setSelectedContract,
    setShowAllMethodologies,
    setCustomPolicyText,
    setError,
    setComplianceComponents,
    setMethodologiesList,
    setDocumentTemplates,
    setRegionMode,
    setSelectedCollectors,
    toggleCollector,
    setCollectorsList,
    setSelectedProfiles,

    // NEW: Analysis Configuration
    setProjectType,
    setBaselineDocumentId,
    setScoringProfileId,
    setPricingProfileId,
    toggleAnalysisCategory,
    getEnabledCollectors,

    // Helpers
    getRepoSource,

    // Step 1: Setup
    loadCollectors,
    validateSource,
    startAnalysis,

    // Step 2: Readiness
    runReadinessCheck,

    // Step 3: Audit
    pollAnalysis,

    // Step 4: Compliance
    checkCompliance,
    addCustomCompliance,
    toggleComplianceComponent,

    // Step 5: Cost
    getCostEstimate,

    // Step 6: Documents
    loadDocumentsByLevel,
    generateDocument,
    downloadDocument,

    // Step 7: Compare
    uploadContract,
    uploadMultipleContracts,
    createDemoContract,
    runComparison,

    // Reset
    resetWorkflow,
    clearAnalysisFromStorage,
  };
}
