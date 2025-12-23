'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE } from '@/lib/api';

interface CollectorProgress {
  name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  metrics_collected: number;
}

interface ProgressData {
  analysis_id: string;
  stage: string;
  stage_progress: number;
  overall_progress: number;
  current_step: string;
  collectors: Record<string, CollectorProgress>;
  collectors_completed: number;
  collectors_total: number;
  started_at?: string;
  estimated_remaining_seconds?: number;
  error?: string;
}

interface AnalysisProgressProps {
  analysisId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

const STAGE_LABELS: Record<string, string> = {
  queued: 'Queued',
  fetching: 'Fetching Repository',
  collecting: 'Collecting Metrics',
  scoring: 'Calculating Scores',
  storing: 'Saving Results',
  reporting: 'Generating Reports',
  completed: 'Completed',
  failed: 'Failed',
};

const STAGE_ICONS: Record<string, string> = {
  queued: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  fetching: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
  collecting: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  scoring: 'M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z',
  storing: 'M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4',
  reporting: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  completed: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  failed: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
};

const STAGES_ORDER = ['queued', 'fetching', 'collecting', 'scoring', 'storing', 'reporting', 'completed'];

function formatTime(seconds?: number): string {
  if (!seconds || seconds <= 0) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDuration(startTime?: string): string {
  if (!startTime) return '0:00';
  const start = new Date(startTime);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function AnalysisProgress({ analysisId, onComplete, onError }: AnalysisProgressProps) {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [elapsed, setElapsed] = useState('0:00');
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connectWebSocket = useCallback(() => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = API_BASE.replace('http', 'ws') + `/api/ws/analysis/${analysisId}/progress`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'heartbeat') return;

        setProgress(data);

        if (data.stage === 'completed' && onComplete) {
          onComplete();
        }

        if (data.stage === 'failed' && data.error && onError) {
          onError(data.error);
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      // Reconnect after 2 seconds if not completed/failed
      if (progress?.stage !== 'completed' && progress?.stage !== 'failed') {
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
      }
    };

    ws.onerror = () => {
      setConnectionStatus('disconnected');
    };

    wsRef.current = ws;
  }, [analysisId, onComplete, onError, progress?.stage]);

  // Connect on mount
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);

  // Update elapsed time
  useEffect(() => {
    if (!progress?.started_at || progress.stage === 'completed' || progress.stage === 'failed') {
      return;
    }

    const interval = setInterval(() => {
      setElapsed(formatDuration(progress.started_at));
    }, 1000);

    return () => clearInterval(interval);
  }, [progress?.started_at, progress?.stage]);

  // Fallback to REST polling if WebSocket fails
  useEffect(() => {
    if (connectionStatus === 'connected') return;

    const pollProgress = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analysis/${analysisId}/progress`);
        if (res.ok) {
          const data = await res.json();
          setProgress(data);
        }
      } catch {
        // Ignore errors
      }
    };

    const interval = setInterval(pollProgress, 2000);
    pollProgress(); // Initial poll

    return () => clearInterval(interval);
  }, [analysisId, connectionStatus]);

  const currentStageIndex = STAGES_ORDER.indexOf(progress?.stage || 'queued');
  const isCompleted = progress?.stage === 'completed';
  const isFailed = progress?.stage === 'failed';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isFailed ? 'bg-red-100' :
            isCompleted ? 'bg-green-100' :
            'bg-primary-100'
          }`}>
            <svg
              className={`w-6 h-6 ${
                isFailed ? 'text-red-600' :
                isCompleted ? 'text-green-600' :
                'text-primary-600 animate-pulse'
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={STAGE_ICONS[progress?.stage || 'queued']}
              />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">
              {STAGE_LABELS[progress?.stage || 'queued']}
            </h3>
            <p className="text-sm text-slate-500">
              {progress?.current_step || 'Initializing...'}
            </p>
          </div>
        </div>

        {/* Connection indicator */}
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${
          connectionStatus === 'connected' ? 'bg-green-100 text-green-700' :
          connectionStatus === 'connecting' ? 'bg-amber-100 text-amber-700' :
          'bg-slate-100 text-slate-500'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            connectionStatus === 'connected' ? 'bg-green-500' :
            connectionStatus === 'connecting' ? 'bg-amber-500 animate-pulse' :
            'bg-slate-400'
          }`} />
          {connectionStatus === 'connected' ? 'Live' : connectionStatus === 'connecting' ? 'Connecting' : 'Polling'}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-slate-600">Overall Progress</span>
          <span className="font-medium text-slate-900">
            {Math.round(progress?.overall_progress || 0)}%
          </span>
        </div>
        <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              isFailed ? 'bg-red-500' :
              isCompleted ? 'bg-green-500' :
              'bg-primary-500'
            }`}
            style={{ width: `${progress?.overall_progress || 0}%` }}
          />
        </div>
      </div>

      {/* Time info */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="text-xs text-slate-500 mb-1">Elapsed Time</div>
          <div className="text-lg font-mono font-semibold text-slate-900">{elapsed}</div>
        </div>
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="text-xs text-slate-500 mb-1">Estimated Remaining</div>
          <div className="text-lg font-mono font-semibold text-slate-900">
            {formatTime(progress?.estimated_remaining_seconds)}
          </div>
        </div>
      </div>

      {/* Stage timeline */}
      <div className="relative">
        <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
          Pipeline Stages
        </div>
        <div className="flex items-center justify-between">
          {STAGES_ORDER.slice(0, -1).map((stage, idx) => {
            const isActive = idx === currentStageIndex;
            const isDone = idx < currentStageIndex || isCompleted;
            const isCurrent = isActive && !isCompleted && !isFailed;

            return (
              <div key={stage} className="flex flex-col items-center flex-1">
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium
                  ${isDone ? 'bg-green-500 text-white' :
                    isCurrent ? 'bg-primary-500 text-white ring-4 ring-primary-100' :
                    'bg-slate-200 text-slate-500'}
                `}>
                  {isDone ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </div>
                <div className={`mt-2 text-xs text-center ${
                  isCurrent ? 'text-primary-600 font-medium' :
                  isDone ? 'text-green-600' :
                  'text-slate-400'
                }`}>
                  {STAGE_LABELS[stage].split(' ')[0]}
                </div>
              </div>
            );
          })}
        </div>

        {/* Progress line between stages */}
        <div className="absolute top-4 left-4 right-4 h-0.5 bg-slate-200 -z-10">
          <div
            className={`h-full transition-all duration-500 ${
              isFailed ? 'bg-red-500' : 'bg-green-500'
            }`}
            style={{
              width: `${Math.min(100, (currentStageIndex / (STAGES_ORDER.length - 2)) * 100)}%`
            }}
          />
        </div>
      </div>

      {/* Collectors progress (collapsed by default) */}
      {progress?.collectors && Object.keys(progress.collectors).length > 0 && (
        <details className="mt-6 group">
          <summary className="cursor-pointer text-sm text-slate-600 hover:text-slate-900 flex items-center gap-2">
            <svg className="w-4 h-4 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Collectors ({progress.collectors_completed}/{progress.collectors_total})
          </summary>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {Object.values(progress.collectors).map((collector) => (
              <div
                key={collector.name}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                  collector.status === 'completed' ? 'bg-green-50 text-green-700' :
                  collector.status === 'running' ? 'bg-primary-50 text-primary-700' :
                  collector.status === 'failed' ? 'bg-red-50 text-red-700' :
                  'bg-slate-50 text-slate-500'
                }`}
              >
                {collector.status === 'completed' && (
                  <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {collector.status === 'running' && (
                  <div className="w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                )}
                {collector.status === 'failed' && (
                  <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                {collector.status === 'pending' && (
                  <div className="w-4 h-4 rounded-full bg-slate-300" />
                )}
                <span className="capitalize">{collector.name.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Error message */}
      {progress?.error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <div className="font-medium text-red-800">Analysis Failed</div>
              <div className="text-sm text-red-600 mt-1">{progress.error}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
