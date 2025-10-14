import { GitBranch, Package, Calendar, CheckCircle2, Clock } from 'lucide-react';
import type { RunInfo as RunInfoType } from '../types';

interface RunInfoProps {
  runInfo: RunInfoType;
}

export function RunInfo({ runInfo }: RunInfoProps) {
  const { metadata } = runInfo;

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const getStatusBadge = () => {
    const statusConfig = {
      completed: { color: 'bg-green-500/10 text-green-700 border-green-500/20', icon: CheckCircle2 },
      cloned: { color: 'bg-blue-500/10 text-blue-700 border-blue-500/20', icon: Clock },
      initializing: { color: 'bg-yellow-500/10 text-yellow-700 border-yellow-500/20', icon: Clock },
      error: { color: 'bg-red-500/10 text-red-700 border-red-500/20', icon: Clock },
    };

    const config = statusConfig[metadata.status] || statusConfig.initializing;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${config.color}`}>
        <Icon className="h-3 w-3" />
        {metadata.status}
      </span>
    );
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-semibold">Current Run</h3>
        {getStatusBadge()}
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-start gap-2">
          <GitBranch className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted-foreground">Repository</div>
            <div className="font-mono text-xs truncate">{metadata.repo_url}</div>
          </div>
        </div>

        <div className="flex items-start gap-2">
          <Package className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted-foreground">Run ID</div>
            <div className="font-mono text-xs truncate">{metadata.run_id}</div>
          </div>
        </div>

        <div className="flex items-start gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">Created</div>
            <div className="text-xs">{formatDate(metadata.created_at)}</div>
          </div>
        </div>

        {metadata.completed_at && (
          <div className="flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="text-xs text-muted-foreground">Completed</div>
              <div className="text-xs">{formatDate(metadata.completed_at)}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
