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

  const borderColor =
    validation.status === 'success' ? 'border-green-500' :
    validation.status === 'failure' ? 'border-red-500' :
    'border-gray-400';

  const bgColor =
    validation.status === 'success' ? 'bg-green-50/30 dark:bg-green-950/20' :
    validation.status === 'failure' ? 'bg-red-50/30 dark:bg-red-950/20' :
    'bg-gray-50/30 dark:bg-gray-950/20';

  return (
    <div
      className={`rounded-lg border-2 ${borderColor} ${bgColor} p-4 my-4`}
      data-example-index={validation.example_index}
    >
      {/* Status Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {validation.status === 'success' ? (
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
          ) : validation.status === 'failure' ? (
            <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
          ) : (
            <div className="h-5 w-5 rounded-full bg-gray-400" />
          )}
          <span className="font-semibold">
            {validation.status === 'success' ? 'CODE VALIDATED' :
             validation.status === 'failure' ? 'VALIDATION FAILED' :
             'VALIDATION SKIPPED'}
          </span>
          {validation.depends_on_previous && (
            <span className="text-xs text-muted-foreground">
              (depends on example{validation.depends_on_example_indices && validation.depends_on_example_indices.length > 1 ? 's' : ''} above)
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
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
          <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded p-2 text-sm">
            <div className="font-medium text-red-900 dark:text-red-300">⚠️ Error:</div>
            <div className="text-red-800 dark:text-red-400 font-mono text-xs mt-1">
              {validation.error_message.split('\n').slice(0, 2).join('\n')}
              {validation.error_message.split('\n').length > 2 && '...'}
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
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-48">
                  {validation.error_message}
                </pre>
              </div>
            )}

            {/* Execution Output */}
            {validation.execution_output && (
              <div>
                <div className="text-xs font-medium mb-1">Output:</div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-48">
                  {validation.execution_output}
                </pre>
              </div>
            )}

            {/* Suggestions */}
            {validation.suggestions && (
              <div>
                <div className="text-xs font-medium mb-1">💡 Suggestions:</div>
                <div className="text-xs">{validation.suggestions}</div>
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
