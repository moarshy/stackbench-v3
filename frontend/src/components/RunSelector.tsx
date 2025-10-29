import { useState, useEffect } from 'react';
import { Play, ChevronDown, Check, Loader2, RefreshCw } from 'lucide-react';
import type { RunInfo } from '../types';

interface RunSelectorProps {
  selectedRun: RunInfo | null;
  onRunSelect: (run: RunInfo) => void;
  baseDataDir: string;
}

export function RunSelector({ selectedRun, onRunSelect, baseDataDir }: RunSelectorProps) {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      // List directories in data folder
      const response = await fetch(`/api/files?path=${encodeURIComponent(baseDataDir)}&type=dirs`);
      if (!response.ok) {
        throw new Error('Failed to fetch runs');
      }
      const runIds: string[] = await response.json();

      // Load metadata for each run
      const runInfos: RunInfo[] = [];
      for (const runId of runIds) {
        try {
          const metadataPath = `${baseDataDir}/${runId}/metadata.json`;
          const metadataResponse = await fetch(`/api/file?path=${encodeURIComponent(metadataPath)}`);
          if (metadataResponse.ok) {
            const metadata = await metadataResponse.json();
            const createdDate = new Date(metadata.created_at);
            runInfos.push({
              run_id: runId,
              metadata,
              display_name: formatRunDisplayName(metadata),
              created_date: createdDate,
            });
          }
        } catch (err) {
          console.error(`Failed to load metadata for ${runId}:`, err);
        }
      }

      // Sort by creation date (newest first)
      runInfos.sort((a, b) => b.created_date.getTime() - a.created_date.getTime());

      setRuns(runInfos);

      // Auto-select first run if none selected
      if (!selectedRun && runInfos.length > 0) {
        onRunSelect(runInfos[0]);
      }
    } catch (err) {
      console.error('Error loading runs:', err);
      setError('Failed to load runs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [baseDataDir]);

  // Support URL parameter for initial run selection
  useEffect(() => {
    if (runs.length > 0 && !selectedRun) {
      const params = new URLSearchParams(window.location.search);
      const runIdFromUrl = params.get('run');

      if (runIdFromUrl) {
        const runFromUrl = runs.find(r => r.run_id === runIdFromUrl);
        if (runFromUrl) {
          onRunSelect(runFromUrl);
        }
      }
    }
  }, [runs, selectedRun, onRunSelect]);

  const formatRunDisplayName = (metadata: any): string => {
    const repoName = metadata.repo_url?.split('/').pop()?.replace('.git', '') || 'Unknown';
    const date = new Date(metadata.created_at);
    const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    return `${repoName} - ${dateStr}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'cloned':
        return 'text-blue-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    if (status === 'completed') return <Check className="h-3 w-3" />;
    if (status === 'initializing' || status === 'cloned') return <Loader2 className="h-3 w-3 animate-spin" />;
    return null;
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-muted rounded-md">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-muted-foreground">Loading runs...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-md">
        <span className="text-sm text-red-700">{error}</span>
        <button
          onClick={loadRuns}
          className="ml-auto p-1 hover:bg-red-100 rounded"
          title="Retry"
        >
          <RefreshCw className="h-4 w-4 text-red-600" />
        </button>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-md">
        <p className="text-sm text-yellow-800">
          No runs found. Run <code className="px-1 py-0.5 bg-yellow-100 rounded">stackbench run ...</code> first.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-md hover:bg-accent transition-colors min-w-[300px]"
      >
        <Play className="h-4 w-4 text-primary" />
        <div className="flex-1 text-left">
          <div className="text-sm font-medium">
            {selectedRun ? selectedRun.display_name : 'Select a run'}
          </div>
          {selectedRun && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className={getStatusColor(selectedRun.metadata.status)}>
                {selectedRun.metadata.status}
              </span>
              {getStatusIcon(selectedRun.metadata.status)}
            </div>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute top-full left-0 mt-1 w-full max-w-[500px] bg-card border border-border rounded-md shadow-lg z-20 max-h-[400px] overflow-auto">
            {runs.map((run) => (
              <button
                key={run.run_id}
                onClick={() => {
                  onRunSelect(run);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-4 py-3 hover:bg-accent border-b border-border last:border-b-0 transition-colors ${
                  selectedRun?.run_id === run.run_id ? 'bg-accent' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {run.display_name}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 truncate">
                      {run.run_id}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs ${getStatusColor(run.metadata.status)}`}>
                        {run.metadata.status}
                      </span>
                      {getStatusIcon(run.metadata.status)}
                    </div>
                  </div>
                  {selectedRun?.run_id === run.run_id && (
                    <Check className="h-4 w-4 text-primary flex-shrink-0" />
                  )}
                </div>
              </button>
            ))}

            <button
              onClick={() => {
                loadRuns();
                setIsOpen(false);
              }}
              className="w-full text-left px-4 py-2 hover:bg-accent text-sm text-muted-foreground flex items-center gap-2 border-t border-border"
            >
              <RefreshCw className="h-3 w-3" />
              Refresh runs
            </button>
          </div>
        </>
      )}
    </div>
  );
}
