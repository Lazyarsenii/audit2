'use client';

interface ProductLevelBadgeProps {
  level: string;
}

export function ProductLevelBadge({ level }: ProductLevelBadgeProps) {
  const getStyles = () => {
    switch (level) {
      case 'R&D Spike':
        return 'bg-slate-100 text-slate-700 border-slate-300';
      case 'Prototype':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'Internal Tool':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'Platform Module Candidate':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'Near-Product':
        return 'bg-green-100 text-green-800 border-green-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  const getIcon = () => {
    switch (level) {
      case 'R&D Spike':
        return '🔬';
      case 'Prototype':
        return '🧪';
      case 'Internal Tool':
        return '🔧';
      case 'Platform Module Candidate':
        return '📦';
      case 'Near-Product':
        return '🚀';
      default:
        return '📋';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-sm font-medium border ${getStyles()}`}
    >
      <span>{getIcon()}</span>
      {level}
    </span>
  );
}
