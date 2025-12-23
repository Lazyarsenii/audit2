'use client';

import React from 'react';

// Inline CheckIcon to avoid external dependency
const CheckIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
  </svg>
);

interface Step {
  key: string;
  label: string;
  description?: string;
}

interface StepperProps {
  steps: readonly Step[];
  currentStep: string;
  onStepClick: (step: string) => void;
}

export default function Stepper({ steps, currentStep, onStepClick }: StepperProps) {
  const currentStepIndex = steps.findIndex(step => step.key === currentStep);

  const getStepStatus = (index: number): 'completed' | 'current' | 'pending' => {
    if (index < currentStepIndex) return 'completed';
    if (index === currentStepIndex) return 'current';
    return 'pending';
  };

  const getStepStyle = (status: 'completed' | 'current' | 'pending') => {
    switch (status) {
      case 'completed':
        return 'bg-green-500 hover:bg-green-600 cursor-pointer text-white';
      case 'current':
        return 'bg-blue-500 text-white ring-4 ring-blue-200';
      case 'pending':
        return 'bg-gray-300 text-gray-600 cursor-not-allowed';
    }
  };

  const getConnectorStyle = (index: number) => {
    const status = getStepStatus(index);
    if (status === 'completed') {
      return 'bg-green-500';
    }
    if (status === 'current') {
      return 'bg-blue-500';
    }
    return 'bg-gray-300';
  };

  return (
    <div className="w-full px-4 py-8">
      <div className="flex items-center justify-between relative">
        {/* Connectors - hidden on small screens, visible on md and up */}
        <div className="absolute top-5 left-0 right-0 h-1 hidden md:flex items-center">
          {steps.map((_, index) => {
            if (index === steps.length - 1) return null;
            return (
              <div
                key={`connector-${index}`}
                className={`flex-1 h-1 mx-1 transition-colors duration-300 ${getConnectorStyle(index)}`}
              />
            );
          })}
        </div>

        {/* Steps */}
        <div className="flex w-full justify-between gap-2 md:gap-4 relative z-10">
          {steps.map((step, index) => {
            const status = getStepStatus(index);
            const isClickable = status === 'completed' || status === 'current';

            return (
              <div key={step.key} className="flex flex-col items-center flex-1">
                {/* Step Circle */}
                <button
                  onClick={() => isClickable && onStepClick(step.key)}
                  disabled={!isClickable}
                  className={`
                    w-10 h-10 md:w-12 md:h-12 rounded-full flex items-center justify-center
                    font-semibold text-sm md:text-base transition-all duration-300
                    flex-shrink-0
                    ${getStepStyle(status)}
                    ${isClickable ? 'hover:scale-110' : ''}
                    ${status === 'current' ? 'ring-4 ring-blue-200' : ''}
                  `}
                  type="button"
                >
                  {status === 'completed' ? (
                    <CheckIcon className="w-5 h-5 md:w-6 md:h-6" />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </button>

                {/* Step Label */}
                {/* Always show on md and up, show on hover/focus on mobile */}
                <div className="mt-3 md:mt-4 text-center">
                  <p className="hidden md:block text-xs md:text-sm font-medium text-gray-700">
                    {step.label}
                  </p>
                  {step.description && (
                    <p className="hidden lg:block text-xs text-gray-500 mt-1">
                      {step.description}
                    </p>
                  )}

                  {/* Mobile: show label on hover via tooltip */}
                  <div className="md:hidden opacity-0 hover:opacity-100 transition-opacity duration-200 absolute top-full mt-2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap pointer-events-none">
                    {step.label}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
