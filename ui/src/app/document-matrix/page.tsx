'use client';

import { useState } from 'react';
import { DocumentMatrix } from '@/components/DocumentMatrix';
import { ProductLevelBadge } from '@/components/ProductLevelBadge';

const PRODUCT_LEVELS = [
  { key: 'R&D Spike', label: 'R&D Spike', description: 'Experimental / Proof of Concept' },
  { key: 'Prototype', label: 'Prototype', description: 'Working prototype with basic features' },
  { key: 'Internal Tool', label: 'Internal Tool', description: 'Internal use tool or service' },
  { key: 'Platform Module Candidate', label: 'Platform Module', description: 'Candidate for platform integration' },
  { key: 'Near-Product', label: 'Near-Product', description: 'Production-ready or close to it' },
];

export default function DocumentMatrixPage() {
  const [selectedLevel, setSelectedLevel] = useState('Prototype');
  const [isPlatformModule, setIsPlatformModule] = useState(false);
  const [hasDonors, setHasDonors] = useState(false);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Document Matrix</h1>
        <p className="text-slate-600">
          Automatic document package selection based on product level and context
        </p>
      </div>

      {/* Configuration Panel */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Configuration</h2>

        {/* Product Level Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-3">
            Product Level
          </label>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {PRODUCT_LEVELS.map((level) => (
              <button
                key={level.key}
                onClick={() => setSelectedLevel(level.key)}
                className={`p-3 rounded-lg border-2 text-left transition-all ${
                  selectedLevel === level.key
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="font-medium text-slate-900 text-sm">{level.label}</div>
                <div className="text-xs text-slate-500 mt-1">{level.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Context Options */}
        <div className="flex flex-wrap gap-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={isPlatformModule}
              onChange={(e) => setIsPlatformModule(e.target.checked)}
              className="w-5 h-5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <span className="font-medium text-slate-900">Platform Module</span>
              <p className="text-xs text-slate-500">Include platform integration documents</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={hasDonors}
              onChange={(e) => setHasDonors(e.target.checked)}
              className="w-5 h-5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <span className="font-medium text-slate-900">Has Donors</span>
              <p className="text-xs text-slate-500">Include donor reporting documents</p>
            </div>
          </label>
        </div>
      </div>

      {/* Current Selection */}
      <div className="flex items-center gap-4 mb-6">
        <span className="text-sm text-slate-600">Selected:</span>
        <ProductLevelBadge level={selectedLevel} />
        {isPlatformModule && (
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm">
            Platform Module
          </span>
        )}
        {hasDonors && (
          <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
            Has Donors
          </span>
        )}
      </div>

      {/* Document Matrix */}
      <DocumentMatrix
        productLevel={selectedLevel}
        isPlatformModule={isPlatformModule}
        hasDonors={hasDonors}
      />
    </div>
  );
}
