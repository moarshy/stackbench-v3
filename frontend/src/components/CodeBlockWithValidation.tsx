import { useState } from 'react';
import { CheckCircle2, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import type { CCExampleValidationResult } from '../types';

interface CodeBlockWithValidationProps {
  code: string;
  className?: string;
  validation: CCExampleValidationResult;
  onDependencyClick?: (exampleIndex: number) => void;
  onViewInTab?: (exampleIndex: number) => void;
}

export function CodeBlockWithValidation({
  code,
  className,
  validation,
  onDependencyClick,
  onViewInTab
}: CodeBlockWithValidationProps) {
  const [expanded, setExpanded] = useState(false);

  // Determine border color based on severity for failures, or status for success/skip
  const getBorderColor = () => {
    if (validation.status === 'success') return 'border-green-500';
    if (validation.status === 'skipped') return 'border-gray-400';
    // For failures, use severity if available
    if (validation.severity === 'error') return 'border-red-500';
    if (validation.severity === 'warning') return 'border-amber-500';
    if (validation.severity === 'info') return 'border-blue-500';
    return 'border-red-500'; // Default to red for failures without severity
  };

  const getBgColor = () => {
    if (validation.status === 'success') return 'bg-green-50/30 dark:bg-green-950/20';
    if (validation.status === 'skipped') return 'bg-gray-50/30 dark:bg-gray-950/20';
    // For failures, use severity if available
    if (validation.severity === 'error') return 'bg-red-50/30 dark:bg-red-950/20';
    if (validation.severity === 'warning') return 'bg-amber-50/30 dark:bg-amber-950/20';
    if (validation.severity === 'info') return 'bg-blue-50/30 dark:bg-blue-950/20';
    return 'bg-red-50/30 dark:bg-red-950/20'; // Default to red
  };

  const borderColor = getBorderColor();
  const bgColor = getBgColor();

  return (
    <div
      className={`rounded-lg border-2 ${borderColor} ${bgColor} p-4 my-4`}
      data-example-index={validation.example_index}
    >
      {/* Status Header */}
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {validation.status === 'success' ? (
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          ) : validation.status === 'failure' ? (
            <XCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          ) : (
            <div className="h-5 w-5 rounded-full bg-gray-400 flex-shrink-0" />
          )}
          <span className="font-semibold">
            {validation.status === 'success' ? 'CODE VALIDATED' :
             validation.status === 'failure' ? 'VALIDATION FAILED' :
             'VALIDATION SKIPPED'}
          </span>

          {/* Severity Badge for Failures */}
          {validation.status === 'failure' && validation.severity && (
            <span className={`severity-badge severity-badge-${validation.severity}`}>
              {validation.severity === 'error' && '⚠️ Doc Error'}
              {validation.severity === 'warning' && '⚡ Environment Issue'}
              {validation.severity === 'info' && 'ℹ️ Info'}
            </span>
          )}

          {validation.depends_on_previous && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              (depends on example{validation.depends_on_example_indices && validation.depends_on_example_indices.length > 1 ? 's' : ''} above)
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
          📍 Line {validation.line}
        </span>
      </div>

      {/* Code Block */}
      <pre className={`${className} bg-muted p-3 rounded-md overflow-x-auto mb-3 text-sm`}>
        <code>{code}</code>
      </pre>

      {/* Validation Info */}
      <div className="space-y-2">
        <div className="flex items-center gap-4 text-sm flex-wrap">
          <span className={`font-medium ${validation.status === 'success' ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
            📊 Validation: {validation.status.toUpperCase()}
          </span>

          {/* Dependency Links */}
          {validation.depends_on_example_indices && validation.depends_on_example_indices.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">🔗 Depends on:</span>
              {validation.depends_on_example_indices.map(idx => (
                <button
                  key={idx}
                  onClick={() => onDependencyClick?.(idx)}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  Example {idx} ↑
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Error Preview (if failed) */}
        {validation.status === 'failure' && validation.error_message && (
          <div className={`rounded p-3 text-sm ${
            validation.severity === 'error'
              ? 'bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800'
              : validation.severity === 'warning'
              ? 'bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800'
              : validation.severity === 'info'
              ? 'bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800'
              : 'bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800'
          }`}>
            <div className={`font-semibold mb-1.5 ${
              validation.severity === 'error'
                ? 'text-red-900 dark:text-red-200'
                : validation.severity === 'warning'
                ? 'text-amber-900 dark:text-amber-200'
                : validation.severity === 'info'
                ? 'text-blue-900 dark:text-blue-200'
                : 'text-red-900 dark:text-red-200'
            }`}>
              {validation.severity === 'error' && '⚠️ Documentation Error:'}
              {validation.severity === 'warning' && '⚡ Environment/Compatibility Issue:'}
              {validation.severity === 'info' && 'ℹ️ Informational:'}
              {!validation.severity && '⚠️ Error:'}
            </div>
            <div className={`font-mono text-xs whitespace-pre-wrap break-words ${
              validation.severity === 'error'
                ? 'text-red-950 dark:text-red-100'
                : validation.severity === 'warning'
                ? 'text-amber-950 dark:text-amber-100'
                : validation.severity === 'info'
                ? 'text-blue-950 dark:text-blue-100'
                : 'text-red-950 dark:text-red-100'
            }`}>
              {validation.error_message.split('\n').slice(0, 2).join('\n')}
              {validation.error_message.split('\n').length > 2 && '...'}
            </div>
          </div>
        )}

        {/* Suggestions Preview (if failed) */}
        {validation.status === 'failure' && validation.suggestions && (
          <div className="bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 rounded p-3 text-sm">
            <div className="font-semibold text-blue-900 dark:text-blue-200 mb-1.5">💡 Suggestions:</div>
            <div className="text-blue-950 dark:text-blue-100 text-xs whitespace-pre-wrap break-words">
              {validation.suggestions}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs px-3 py-1 bg-background border rounded hover:bg-accent flex items-center gap-1"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? 'Hide' : 'View'} Details
          </button>

          <button
            onClick={() => onViewInTab?.(validation.example_index)}
            className="text-xs px-3 py-1 bg-background border rounded hover:bg-accent"
          >
            View in Validation Tab →
          </button>
        </div>

        {/* Expandable Details */}
        {expanded && (
          <div className="mt-3 space-y-2 bg-background p-3 rounded border">
            {/* Full Error */}
            {validation.error_message && (
              <div>
                <div className="text-xs font-medium mb-1">Full Error:</div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-48 whitespace-pre-wrap break-words">
                  {validation.error_message}
                </pre>
              </div>
            )}

            {/* Execution Output */}
            {validation.execution_output && (
              <div>
                <div className="text-xs font-medium mb-1">Output:</div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-48 whitespace-pre-wrap break-words">
                  {validation.execution_output}
                </pre>
              </div>
            )}

            {/* Actual Code Executed (if different) */}
            {validation.actual_code_executed && validation.actual_code_executed !== code && (
              <div>
                <div className="text-xs font-medium mb-1">
                  ⚙️ Actual Code Executed (with dependencies):
                </div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-48">
                  <code>{validation.actual_code_executed}</code>
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
