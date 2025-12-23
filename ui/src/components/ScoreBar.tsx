'use client';

interface ScoreBarProps {
  score: number;
  maxScore: number;
  label: string;
  showValue?: boolean;
}

export function ScoreBar({ score, maxScore, label, showValue = true }: ScoreBarProps) {
  const percentage = (score / maxScore) * 100;

  const getColor = () => {
    const ratio = score / maxScore;
    if (ratio >= 0.75) return 'bg-green-500';
    if (ratio >= 0.5) return 'bg-yellow-500';
    if (ratio >= 0.25) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        {showValue && (
          <span className="font-medium text-slate-900">
            {score}/{maxScore}
          </span>
        )}
      </div>
      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full score-bar rounded-full ${getColor()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
