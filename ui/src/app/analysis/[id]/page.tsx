import { AnalysisClient } from './AnalysisClient';

// Required for static export - generates at least one placeholder
export function generateStaticParams() {
  return [{ id: 'placeholder' }];
}

export default function AnalysisPage() {
  return <AnalysisClient />;
}
