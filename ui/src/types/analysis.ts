export interface Analysis {
  analysis_id: string;
  id: string;  // Alias for analysis_id
  repo_url: string;
  repo_name?: string;
  branch?: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  product_level?: string;
  complexity?: string;
  created_at: string;
  finished_at?: string;
  error_message?: string;
  repo_health?: RepoHealth;
  tech_debt?: TechDebt;
  cost_estimates?: CostEstimates;
  historical_estimate?: HistoricalEstimate;
  tasks?: Task[];
}

export interface RepoHealth {
  documentation: number;
  structure: number;
  runability: number;
  commit_history: number;
  total: number;
  max_possible: number;
}

export interface TechDebt {
  architecture: number;
  code_quality: number;
  testing: number;
  infrastructure: number;
  security_deps: number;
  total: number;
  max_possible: number;
}

export interface CostEstimates {
  hours: {
    min: ActivityBreakdown;
    typical: ActivityBreakdown;
    max: ActivityBreakdown;
  };
  cost: {
    eu: CostRange;
    ua: CostRange;
  };
  complexity: string;
  tech_debt_multiplier: number;
}

export interface ActivityBreakdown {
  analysis: number;
  design: number;
  development: number;
  qa: number;
  documentation: number;
  total: number;
}

export interface CostRange {
  min: number;
  max: number;
  currency: string;
  formatted: string;
}

export interface HistoricalEstimate {
  active_days: number;
  hours: {
    min: number;
    max: number;
  };
  person_months: {
    min: number;
    max: number;
  };
  cost: {
    eu: CostRange;
    ua: CostRange;
  };
  confidence: string;
  note: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  category: string;
  priority: string;
  status: string;
  estimate_hours?: number;
  labels: string[];
}

export interface AnalysisListResponse {
  analyses: Analysis[];
  total: number;
  limit: number;
  offset: number;
}
