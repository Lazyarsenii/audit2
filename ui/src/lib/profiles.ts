export type CostMethodology = {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  confidence?: 'High' | 'Medium' | 'Low';
  formula?: string;
  source?: string;
};

export type RegionalRate = {
  id: string;
  name: string;
  currency: string;
  hourlyRate: number;
};

const METHODOLOGY_STORAGE_KEY = 'auditor_methodologies';

const DEFAULT_METHODOLOGIES: CostMethodology[] = [
  {
    id: 'cocomo',
    name: 'COCOMO II',
    description: 'Constructive Cost Model',
    enabled: true,
    confidence: 'High',
    formula: 'Staff months = 2.94 × (KLOC)^1.099',
    source: 'Barry Boehm',
  },
  {
    id: 'gartner',
    name: 'Gartner',
    description: 'Enterprise IT benchmarks',
    enabled: true,
    confidence: 'Medium',
    formula: 'Words ÷ 650 × complexity',
    source: 'Gartner IT Research',
  },
  {
    id: 'ieee',
    name: 'IEEE 1063',
    description: 'Documentation standards',
    enabled: true,
    confidence: 'Medium',
    formula: 'Pages ÷ 1.5 × complexity',
    source: 'IEEE 1063',
  },
  {
    id: 'google',
    name: 'Google UX',
    description: 'UX-driven estimation',
    enabled: true,
    confidence: 'Medium',
    formula: 'Pages × 4 hours × complexity',
    source: 'Google Technical Writing',
  },
  {
    id: 'pmi',
    name: 'PMI',
    description: 'Project management weighting',
    enabled: true,
    confidence: 'Medium',
    formula: 'Pages × 0.25 × complexity',
    source: 'PMI Standards',
  },
  {
    id: 'function_points',
    name: 'Function Points',
    description: 'Feature-based sizing',
    enabled: true,
    confidence: 'Medium',
    formula: '(LOC ÷ 50) × 0.25 × 0.5 × complexity',
    source: 'ISO/IEC 20926',
  },
];

const DEFAULT_RATES: RegionalRate[] = [
  { id: 'eu', name: 'EU (EUR)', currency: 'EUR', hourlyRate: 70 },
  { id: 'ua', name: 'Ukraine (UAH)', currency: 'UAH', hourlyRate: 1200 },
  { id: 'us', name: 'US (USD)', currency: 'USD', hourlyRate: 120 },
];

const withLocalStorage = <T,>(fallback: T, parser: () => T): T => {
  if (typeof window === 'undefined') return fallback;
  try {
    return parser();
  } catch (err) {
    console.warn('Failed to read from localStorage', err);
    return fallback;
  }
};

export const getMethodologies = (): CostMethodology[] =>
  withLocalStorage(DEFAULT_METHODOLOGIES, () => {
    const stored = localStorage.getItem(METHODOLOGY_STORAGE_KEY);
    if (!stored) return DEFAULT_METHODOLOGIES;
    const parsed = JSON.parse(stored) as CostMethodology[];
    return parsed.length ? parsed : DEFAULT_METHODOLOGIES;
  });

export const setMethodologyEnabled = (id: string, enabled: boolean) => {
  if (typeof window === 'undefined') return;
  const current = getMethodologies().map((m) =>
    m.id === id ? { ...m, enabled } : m,
  );
  localStorage.setItem(METHODOLOGY_STORAGE_KEY, JSON.stringify(current));
};

export const getRegionalRates = (): RegionalRate[] => DEFAULT_RATES;
