'use client';

interface ComplexityBadgeProps {
  complexity: string;
}

export function ComplexityBadge({ complexity }: ComplexityBadgeProps) {
  const getStyles = () => {
    switch (complexity) {
      case 'S':
        return 'bg-emerald-100 text-emerald-800';
      case 'M':
        return 'bg-blue-100 text-blue-800';
      case 'L':
        return 'bg-orange-100 text-orange-800';
      case 'XL':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-slate-100 text-slate-800';
    }
  };

  const getLabel = () => {
    switch (complexity) {
      case 'S':
        return 'Small';
      case 'M':
        return 'Medium';
      case 'L':
        return 'Large';
      case 'XL':
        return 'X-Large';
      default:
        return complexity;
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold ${getStyles()}`}
    >
      {complexity}
      <span className="ml-1 font-normal opacity-75">{getLabel()}</span>
    </span>
  );
}
