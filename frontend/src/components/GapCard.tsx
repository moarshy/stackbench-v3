import { useState } from 'react';
import { AlertCircle, AlertTriangle, Info, ChevronDown, ChevronUp } from 'lucide-react';
import type { GapReport } from '../types';

interface GapCardProps {
  gap: GapReport;
}

export function GapCard({ gap }: GapCardProps) {
  const [expanded, setExpanded] = useState(false);

  const severityConfig = {
    critical: {
      bgColor: 'bg-red-50 dark:bg-red-950/30',
      borderColor: 'border-red-500',
      textColor: 'text-red-900 dark:text-red-100',
      badgeColor: 'bg-red-500/20 text-red-700 dark:text-red-300',
      icon: <AlertCircle className="h-4 w-4" />
    },
    warning: {
      bgColor: 'bg-yellow-50 dark:bg-yellow-950/30',
      borderColor: 'border-yellow-500',
      textColor: 'text-yellow-900 dark:text-yellow-100',
      badgeColor: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300',
      icon: <AlertTriangle className="h-4 w-4" />
    },
    info: {
      bgColor: 'bg-blue-50 dark:bg-blue-950/30',
      borderColor: 'border-blue-400',
      textColor: 'text-blue-900 dark:text-blue-100',
      badgeColor: 'bg-blue-500/20 text-blue-700 dark:text-blue-300',
      icon: <Info className="h-4 w-4" />
    }
  };

  const config = severityConfig[gap.severity];

  // Format gap type for display
  const formatGapType = (type: string) => {
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <div className={`p-3 rounded-md border-l-4 ${config.borderColor} ${config.bgColor}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 flex-1">
          {config.icon}
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.badgeColor}`}>
            {gap.severity}
          </span>
          <span className="text-xs font-medium">
            {formatGapType(gap.gap_type)}
          </span>
        </div>
        <div className={`text-xs ${config.textColor} opacity-70`}>
          Step {gap.step_number}
        </div>
      </div>

      <div className={`text-sm mt-2 ${config.textColor}`}>
        {gap.description}
      </div>

      {(gap.suggested_fix || gap.context) && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className={`flex items-center gap-1 text-xs mt-2 ${config.textColor} opacity-80 hover:opacity-100 transition-opacity`}
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? 'Hide details' : 'Show details'}
          </button>

          {expanded && (
            <div className="mt-2 space-y-2">
              {gap.suggested_fix && (
                <div className={`text-xs p-2 rounded ${config.bgColor} border ${config.borderColor}/30`}>
                  <div className="font-medium mb-1">💡 Suggested Fix:</div>
                  <div className="opacity-90">{gap.suggested_fix}</div>
                </div>
              )}

              {gap.context && (
                <div className={`text-xs p-2 rounded ${config.bgColor} border ${config.borderColor}/30`}>
                  <div className="font-medium mb-1">📋 Context:</div>
                  <pre className="opacity-90 whitespace-pre-wrap font-mono text-xs">{gap.context}</pre>
                </div>
              )}

              <div className={`text-xs ${config.textColor} opacity-60`}>
                Reported at: {new Date(gap.timestamp).toLocaleString()}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
