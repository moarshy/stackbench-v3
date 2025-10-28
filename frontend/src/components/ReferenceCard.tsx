import { FileText } from 'lucide-react';
import type { DocumentationReference } from '../types';

interface ReferenceCardProps {
  reference: DocumentationReference;
  onClick: () => void;
}

/**
 * Display card for a single documentation reference showing where an API appears.
 */
export function ReferenceCard({ reference, onClick }: ReferenceCardProps) {
  // Context type badge styling
  const getContextTypeBadge = (type: string) => {
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      signature: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-800 dark:text-blue-200', label: 'Signature' },
      example: { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-800 dark:text-green-200', label: 'Example' },
      mention: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-800 dark:text-gray-200', label: 'Mention' }
    };
    const badge = badges[type] || badges.mention;
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    );
  };

  return (
    <div
      onClick={onClick}
      className="p-4 border border-border rounded-lg hover:shadow-md hover:border-primary transition-all cursor-pointer bg-card"
    >
      {/* Document name and type badge */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <span className="font-medium truncate">{reference.document}</span>
        </div>
        {getContextTypeBadge(reference.context_type)}
      </div>

      {/* Section hierarchy breadcrumb */}
      {reference.section_hierarchy.length > 0 && (
        <div className="text-sm text-muted-foreground mb-2 truncate">
          {reference.section_hierarchy.join(' › ')}
        </div>
      )}

      {/* Context preview */}
      <div className="text-xs bg-muted p-2 rounded mb-2">
        <div className="flex items-start gap-2">
          <span className="text-muted-foreground">Line {reference.line_number}:</span>
          <span className="flex-1">{reference.raw_context}</span>
        </div>
      </div>

      {/* Additional metadata */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {reference.markdown_anchor && (
          <span className="font-mono">{reference.markdown_anchor}</span>
        )}
        {reference.code_block_index !== null && (
          <span>Block #{reference.code_block_index}</span>
        )}
      </div>

      {/* Navigation hint */}
      <div className="text-xs text-primary mt-2 flex items-center gap-1">
        <span>Click to view in document</span>
        <span>→</span>
      </div>
    </div>
  );
}
