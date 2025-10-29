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
      className="settings-help-box cursor-pointer transition-all hover:shadow-md"
      style={{ marginBottom: 0 }}
    >
      <div className="settings-help-box-content">
        <FileText className="h-5 w-5 settings-help-box-icon" />
        <div className="settings-help-box-text" style={{ width: '100%' }}>
          {/* Document name and type badge */}
          <div className="flex items-center justify-between gap-3 mb-3">
            <p className="settings-help-box-title" style={{ marginBottom: 0 }}>{reference.document}</p>
            {getContextTypeBadge(reference.context_type)}
          </div>

          {/* Section hierarchy breadcrumb */}
          {reference.section_hierarchy && reference.section_hierarchy.length > 0 && (
            <p className="settings-help-box-description" style={{ marginBottom: '0.75rem' }}>
              {reference.section_hierarchy.join(' › ')}
            </p>
          )}

          {/* Context preview */}
          <div className="settings-code-block" style={{ marginBottom: '0.75rem' }}>
            <div style={{ fontSize: '0.8125rem' }}>
              <span style={{ color: 'hsl(var(--muted-foreground))' }}>Line {reference.line_number}:</span>
              {' '}
              <span style={{ color: 'hsl(var(--foreground))' }}>{reference.raw_context}</span>
            </div>
          </div>

          {/* Additional metadata */}
          {(reference.markdown_anchor || reference.code_block_index !== null) && (
            <div className="flex items-center gap-3 mb-2" style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>
              {reference.markdown_anchor && (
                <code className="settings-help-box-code">{reference.markdown_anchor}</code>
              )}
              {reference.code_block_index !== null && (
                <span className="settings-help-box-code">Block #{reference.code_block_index}</span>
              )}
            </div>
          )}

          {/* Navigation hint */}
          <p className="settings-help-box-description" style={{ marginTop: '0.5rem', fontWeight: 600, color: 'hsl(var(--primary))' }}>
            Click to view in document →
          </p>
        </div>
      </div>
    </div>
  );
}
