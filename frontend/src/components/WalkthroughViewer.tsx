import { useState } from 'react';
import { CheckCircle2, Clock, Tag, AlertTriangle } from 'lucide-react';
import type { WalkthroughData, WalkthroughStep, GapReport } from '../types';
import { GapCard } from './GapCard';
import { MarkdownViewer } from './MarkdownViewer';

interface WalkthroughViewerProps {
  data: WalkthroughData;
}

export function WalkthroughViewer({ data }: WalkthroughViewerProps) {
  const { walkthrough, session } = data;
  const [selectedStepIndex, setSelectedStepIndex] = useState<number>(0);

  // Group gaps by step number
  const gapsByStep = new Map<number, GapReport[]>();
  if (session) {
    session.gaps.forEach(gap => {
      const existing = gapsByStep.get(gap.step_number) || [];
      gapsByStep.set(gap.step_number, [...existing, gap]);
    });
  }

  // Count gaps by severity
  const gapCounts = {
    critical: session?.gaps.filter(g => g.severity === 'critical').length || 0,
    warning: session?.gaps.filter(g => g.severity === 'warning').length || 0,
    info: session?.gaps.filter(g => g.severity === 'info').length || 0,
  };

  const selectedStep = walkthrough.steps[selectedStepIndex];
  const selectedStepGaps = gapsByStep.get(selectedStep.displayOrder + 1) || [];

  const isStepCompleted = (step: WalkthroughStep): boolean => {
    if (!session) return false;
    return (step.displayOrder + 1) <= session.completed_steps;
  };

  const hasGaps = (step: WalkthroughStep): boolean => {
    return gapsByStep.has(step.displayOrder + 1);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border bg-card">
        <h2 className="text-2xl font-bold mb-2">{walkthrough.walkthrough.title}</h2>
        <p className="text-sm text-muted-foreground mb-4">{walkthrough.walkthrough.description}</p>

        <div className="flex flex-wrap items-center gap-4 text-sm">
          {/* Completion Status */}
          {session && (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="font-medium">
                {session.completed_steps}/{session.total_steps} steps
              </span>
              {session.is_complete && (
                <span className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-700">
                  Complete
                </span>
              )}
            </div>
          )}

          {/* Duration */}
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>{walkthrough.walkthrough.estimatedDurationMinutes} min</span>
          </div>

          {/* Gap Summary */}
          {session && session.gaps.length > 0 && (
            <div className="flex items-center gap-3">
              {gapCounts.critical > 0 && (
                <span className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-700">
                  {gapCounts.critical} critical
                </span>
              )}
              {gapCounts.warning > 0 && (
                <span className="px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-700">
                  {gapCounts.warning} warning
                </span>
              )}
              {gapCounts.info > 0 && (
                <span className="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-700">
                  {gapCounts.info} info
                </span>
              )}
            </div>
          )}

          {/* Tags */}
          <div className="flex items-center gap-2 ml-auto">
            <Tag className="h-4 w-4 text-muted-foreground" />
            <div className="flex flex-wrap gap-1">
              {walkthrough.walkthrough.tags.slice(0, 5).map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded text-xs bg-accent text-accent-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Two-pane layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Pane - Steps List */}
        <div className="w-80 border-r border-border overflow-y-auto bg-card">
          <div className="p-4">
            <h3 className="text-sm font-semibold mb-3">Steps ({walkthrough.steps.length})</h3>
            <div className="space-y-1">
              {walkthrough.steps.map((step, idx) => {
                const completed = isStepCompleted(step);
                const gaps = gapsByStep.get(step.displayOrder + 1) || [];
                const criticalGaps = gaps.filter(g => g.severity === 'critical').length;
                const warningGaps = gaps.filter(g => g.severity === 'warning').length;

                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedStepIndex(idx)}
                    className={`w-full text-left p-3 rounded-md transition-all ${
                      selectedStepIndex === idx
                        ? 'bg-primary text-primary-foreground font-medium shadow-sm'
                        : 'hover:bg-accent hover:text-accent-foreground'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-shrink-0 mt-0.5">
                        {completed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        ) : hasGaps(step) ? (
                          <AlertTriangle className="h-4 w-4 text-yellow-600" />
                        ) : (
                          <div className="h-4 w-4 rounded-full border-2 border-current opacity-50" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs opacity-70 mb-1">Step {step.displayOrder + 1}</div>
                        <div className="text-sm truncate">{step.title}</div>
                        {(criticalGaps > 0 || warningGaps > 0) && (
                          <div className="flex gap-1 mt-1">
                            {criticalGaps > 0 && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-700">
                                {criticalGaps}
                              </span>
                            )}
                            {warningGaps > 0 && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-700">
                                {warningGaps}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Pane - Step Details */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedStep && (
            <div className="max-w-4xl">
              <div className="mb-4">
                <div className="text-sm text-muted-foreground mb-1">
                  Step {selectedStep.displayOrder + 1} of {walkthrough.steps.length}
                </div>
                <h3 className="text-xl font-bold">{selectedStep.title}</h3>
              </div>

              {/* Step Content */}
              <div className="prose prose-sm dark:prose-invert max-w-none mb-6">
                <MarkdownViewer
                  content={selectedStep.contentFields.contentForUser}
                  baseImagePath=""
                />
              </div>

              {/* Gaps Section */}
              {selectedStepGaps.length > 0 && (
                <div className="mt-6 pt-6 border-t border-border">
                  <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    Issues Found ({selectedStepGaps.length})
                  </h4>
                  <div className="space-y-2">
                    {/* Group by severity */}
                    {['critical', 'warning', 'info'].map(severity => {
                      const gaps = selectedStepGaps.filter(g => g.severity === severity);
                      if (gaps.length === 0) return null;

                      return (
                        <div key={severity} className="space-y-2">
                          {gaps.map((gap, idx) => (
                            <GapCard key={idx} gap={gap} />
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* No Audit Message */}
              {!session && (
                <div className="mt-6 p-4 rounded-md bg-muted border border-border">
                  <div className="text-sm text-muted-foreground">
                    <div className="font-medium mb-1">No audit results available</div>
                    <div>This walkthrough hasn't been audited yet. Run the audit command to test this walkthrough:</div>
                    <code className="block mt-2 px-2 py-1 bg-background rounded text-xs">
                      stackbench walkthrough audit --walkthrough {data.walkthrough.walkthrough.title}
                    </code>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
