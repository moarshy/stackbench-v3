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
      <span className={`run-info-status-badge ${config.color}`}>
        <Icon className="h-3 w-3" />
        {metadata.status}
      </span>
    );
  };

  return (
    <div className="run-info-card">
      <div className="run-info-header">
        <h3 className="run-info-title">Current Run</h3>
        {getStatusBadge()}
      </div>

      <div>
        <div className="run-info-item">
          <GitBranch className="run-info-icon" />
          <div className="run-info-item-content">
            <div className="run-info-item-label">Repository</div>
            <div className="run-info-item-value run-info-item-value-mono">{metadata.repo_url}</div>
          </div>
        </div>

        <div className="run-info-item">
          <Package className="run-info-icon" />
          <div className="run-info-item-content">
            <div className="run-info-item-label">Run ID</div>
            <div className="run-info-item-value run-info-item-value-mono">{metadata.run_id}</div>
          </div>
        </div>

        <div className="run-info-item">
          <Calendar className="run-info-icon" />
          <div className="run-info-item-content">
            <div className="run-info-item-label">Created</div>
            <div className="run-info-item-value">{formatDate(metadata.created_at)}</div>
          </div>
        </div>

        {metadata.completed_at && (
          <div className="run-info-item">
            <CheckCircle2 className="run-info-icon" />
            <div className="run-info-item-content">
              <div className="run-info-item-label">Completed</div>
              <div className="run-info-item-value">{formatDate(metadata.completed_at)}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
