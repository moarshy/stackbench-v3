import { useState, useMemo } from 'react';
import type { APIDetail, DocumentationReference } from '../types';

interface CoverageHeatmapProps {
  apiDetails: APIDetail[];
  onCellClick?: (api: APIDetail, document: string) => void;
}

/**
 * Coverage heatmap showing which documents cover which APIs.
 * Displays a 2D grid: APIs (rows) × Documents (columns).
 */
export function CoverageHeatmap({ apiDetails, onCellClick }: CoverageHeatmapProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Get unique list of all documents
  const allDocuments = useMemo(() => {
    const docs = new Set<string>();
    apiDetails.forEach(api => {
      api.documentation_references.forEach(ref => {
        docs.add(ref.document);
      });
    });
    return Array.from(docs).sort();
  }, [apiDetails]);

  // Filter APIs by search query
  const filteredAPIs = useMemo(() => {
    if (!searchQuery) return apiDetails;
    const query = searchQuery.toLowerCase();
    return apiDetails.filter(api =>
      api.api.toLowerCase().includes(query) ||
      api.module.toLowerCase().includes(query)
    );
  }, [apiDetails, searchQuery]);

  // Get references for a specific API and document
  const getReferences = (api: APIDetail, doc: string): DocumentationReference[] => {
    return api.documentation_references.filter(ref => ref.document === doc);
  };

  // Get cell styling based on number of references
  const getCellStyle = (refCount: number) => {
    if (refCount === 0) {
      return 'bg-gray-50 dark:bg-gray-900 text-gray-400';
    } else if (refCount === 1) {
      return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 hover:bg-green-200 dark:hover:bg-green-800';
    } else if (refCount === 2) {
      return 'bg-green-200 dark:bg-green-800 text-green-900 dark:text-green-100 hover:bg-green-300 dark:hover:bg-green-700';
    } else {
      return 'bg-green-300 dark:bg-green-700 text-green-950 dark:text-green-50 hover:bg-green-400 dark:hover:bg-green-600';
    }
  };

  // Get tooltip text for a cell
  const getTooltip = (api: APIDetail, doc: string, refs: DocumentationReference[]): string => {
    if (refs.length === 0) {
      return `${api.api} not documented in ${doc}`;
    }
    const types = refs.map(r => r.context_type).join(', ');
    return `${api.api} in ${doc}: ${refs.length} reference(s) (${types})`;
  };

  if (allDocuments.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No documentation references found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="flex items-center gap-4">
        <input
          type="text"
          placeholder="Search APIs..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-2 rounded-md border border-input bg-background text-sm"
        />
        <div className="text-sm text-muted-foreground">
          {filteredAPIs.length} API{filteredAPIs.length !== 1 ? 's' : ''} × {allDocuments.length} doc{allDocuments.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="font-medium">Coverage:</span>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-gray-100 dark:bg-gray-900 border border-border rounded"></div>
          <span>None</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-100 dark:bg-green-900 border border-border rounded"></div>
          <span>1 ref</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-200 dark:bg-green-800 border border-border rounded"></div>
          <span>2 refs</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-300 dark:bg-green-700 border border-border rounded"></div>
          <span>3+ refs</span>
        </div>
      </div>

      {/* Heatmap table */}
      <div className="overflow-auto border border-border rounded-lg">
        <table className="w-full text-xs">
          <thead className="bg-muted sticky top-0 z-10">
            <tr>
              <th className="px-3 py-2 text-left font-medium border-r border-border sticky left-0 bg-muted z-20">
                API
              </th>
              {allDocuments.map(doc => (
                <th
                  key={doc}
                  className="px-2 py-2 text-center font-medium border-l border-border min-w-[100px]"
                >
                  <div className="transform -rotate-45 origin-left whitespace-nowrap" style={{ width: '100px' }}>
                    {doc}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredAPIs.map((api, idx) => (
              <tr
                key={api.api}
                className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/30'}
              >
                <td className="px-3 py-2 font-mono text-xs border-r border-border sticky left-0 bg-inherit z-10">
                  {api.api}
                </td>
                {allDocuments.map(doc => {
                  const refs = getReferences(api, doc);
                  const refCount = refs.length;
                  return (
                    <td
                      key={doc}
                      className={`text-center border-l border-border cursor-pointer transition-colors ${getCellStyle(refCount)}`}
                      onClick={() => refCount > 0 && onCellClick?.(api, doc)}
                      title={getTooltip(api, doc, refs)}
                    >
                      {refCount > 0 && (
                        <span className="font-semibold">{refCount}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
