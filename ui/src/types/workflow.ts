// Workflow step definitions
export enum WorkflowStep {
  SETUP = 'setup',
  READINESS = 'readiness',
  AUDIT = 'audit',
  COMPLIANCE = 'compliance',
  COST = 'cost',
  DOCUMENTS = 'documents',
  COMPARE = 'compare',
  COMPLETE = 'complete',
}

// Source repository types
export type SourceType = 'github' | 'gitlab' | 'local';

// Analysis stage status and information
export interface AnalysisStage {
  id: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  detail?: string;
}

// Compliance component configuration
export interface ComplianceComponent {
  id: string;
  name: string;
  enabled: boolean;
  source?: string;
}

// Readiness assessment data
export interface ReadinessData {
  readiness_score: number;
  readiness_level: 'low' | 'medium' | 'high' | 'critical';
  passed_checks: number;
  blockers_count: number;
  summary: string;
  next_steps: string[];
}

// Compliance check results
export interface ComplianceData {
  verdict: 'pass' | 'fail' | 'warning';
  compliance_percent: number;
  passed: number;
  failed: number;
  critical_failed: number;
}

// Cost estimation data
export interface CostEstimateData {
  summary: {
    average_cost: number;
    hours: number;
    range: {
      min: number;
      max: number;
    };
  };
  methodologies: Array<{
    name: string;
    cost: number;
    hours: number;
  }>;
  ai_efficiency: number;
}

// Comparison analysis results
export interface ComparisonData {
  overall_status: 'pass' | 'fail' | 'warning';
  overall_score: number;
  work_plan: Array<{
    task: string;
    duration: number;
  }>;
  budget: Array<{
    category: string;
    amount: number;
  }>;
  recommendations: string[];
}

// Parsed contract information
export interface ParsedContract {
  id: string;
  filename: string;
  contract_title: string;
  work_plan: Array<{
    phase: string;
    description: string;
    duration: number;
  }>;
  budget: Array<{
    category: string;
    amount: number;
    description: string;
  }>;
}

// Generated document data
export interface DocumentData {
  generated_at: string;
  type: 'report' | 'summary' | 'audit' | 'comparison';
  content: string;
  format: 'pdf' | 'markdown' | 'html' | 'word' | 'excel';
  download_url: string;
}

// Props for Setup Step component
export interface SetupStepProps {
  onNext: (data: { source: SourceType; repository: string }) => void;
  isLoading?: boolean;
}

// Props for Readiness Step component
export interface ReadinessStepProps {
  data: ReadinessData;
  isLoading?: boolean;
  onNext: () => void;
}

// Props for Audit Step component
export interface AuditStepProps {
  stages: AnalysisStage[];
  isLoading?: boolean;
  onNext: () => void;
}

// Props for Compliance Step component
export interface ComplianceStepProps {
  data: ComplianceData;
  components: ComplianceComponent[];
  isLoading?: boolean;
  onNext: () => void;
}

// Props for Cost Step component
export interface CostStepProps {
  data: CostEstimateData;
  isLoading?: boolean;
  onNext: () => void;
}

// Props for Documents Step component
export interface DocumentsStepProps {
  documents: DocumentData[];
  contracts: ParsedContract[];
  isLoading?: boolean;
  onNext: () => void;
}

// Props for Compare Step component
export interface CompareStepProps {
  data: ComparisonData;
  isLoading?: boolean;
  onNext: () => void;
}

// Props for Complete Step component
export interface CompleteStepProps {
  projectName: string;
  summaryUrl: string;
  onRestart: () => void;
}
