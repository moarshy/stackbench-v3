import { useState } from 'react';
import { X, ExternalLink, Search } from 'lucide-react';
import type { APICompletenessOutput, APIDetail } from '../types';
import { ReferenceCard } from './ReferenceCard';
import { CoverageHeatmap } from './CoverageHeatmap';

interface APICoverageViewerProps {
  apiCompleteness: APICompletenessOutput;
  onNavigateToDoc: (docName: string, lineNumber: number, anchor: string | null) => void;
}

/**
 * Enhanced API Coverage viewer with rich documentation references.
 * Shows all APIs, their coverage details, and where they're documented.
 */
export function APICoverageViewer({ apiCompleteness, onNavigateToDoc }: APICoverageViewerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'all-apis' | 'heatmap'>('overview');
  const [selectedAPI, setSelectedAPI] = useState<APIDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTier, setFilterTier] = useState<number | 'all'>('all');
  const [filterImportance, setFilterImportance] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  // Filter API details
  const filteredAPIs = apiCompleteness.api_details.filter(api => {
    const matchesSearch = !searchQuery ||
      api.api.toLowerCase().includes(searchQuery.toLowerCase()) ||
      api.module.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTier = filterTier === 'all' || api.coverage_tier === filterTier;
    const matchesImportance = filterImportance === 'all' || api.importance === filterImportance;

    return matchesSearch && matchesTier && matchesImportance;
  });

  // Get coverage tier badge styling
  const getTierBadge = (tier: number) => {
    const badges: Record<number, { label: string; bg: string; text: string }> = {
      0: { label: 'Undocumented', bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-800 dark:text-red-200' },
      1: { label: 'Mentioned', bg: 'bg-yellow-100 dark:bg-yellow-900', text: 'text-yellow-800 dark:text-yellow-200' },
      2: { label: 'Has Examples', bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-800 dark:text-blue-200' },
      3: { label: 'Complete', bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-800 dark:text-green-200' }
    };
    const badge = badges[tier] || badges[0];
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    );
  };

  // Get importance badge styling
  const getImportanceBadge = (importance: string) => {
    const badges: Record<string, { bg: string; text: string }> = {
      high: { bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-800 dark:text-red-200' },
      medium: { bg: 'bg-yellow-100 dark:bg-yellow-900', text: 'text-yellow-800 dark:text-yellow-200' },
      low: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-800 dark:text-gray-200' }
    };
    const badge = badges[importance] || badges.low;
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
        {importance}
      </span>
    );
  };

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'all-apis' as const, label: 'All APIs' },
    { id: 'heatmap' as const, label: 'Coverage Heatmap' },
  ];

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex gap-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Keep existing summary cards */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Coverage Summary</h3>
            <p className="text-sm text-muted-foreground mb-4">
              This view shows the existing overview. All APIs tab now includes rich documentation references.
            </p>
          </div>
        </div>
      )}

      {/* All APIs Tab */}
      {activeTab === 'all-apis' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search APIs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-md border border-input bg-background text-sm"
                />
              </div>
            </div>

            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="px-3 py-2 rounded-md border border-input bg-background text-sm"
            >
              <option value="all">All Tiers</option>
              <option value="0">Undocumented</option>
              <option value="1">Mentioned</option>
              <option value="2">Has Examples</option>
              <option value="3">Complete</option>
            </select>

            <select
              value={filterImportance}
              onChange={(e) => setFilterImportance(e.target.value as any)}
              className="px-3 py-2 rounded-md border border-input bg-background text-sm"
            >
              <option value="all">All Importance</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <div className="text-sm text-muted-foreground">
              {filteredAPIs.length} API{filteredAPIs.length !== 1 ? 's' : ''}
            </div>
          </div>

          {/* API List */}
          <div className="space-y-2">
            {filteredAPIs.map(api => (
              <div
                key={api.api}
                onClick={() => setSelectedAPI(api)}
                className="p-4 border border-border rounded-lg hover:border-primary hover:shadow-md transition-all cursor-pointer bg-card"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h4 className="font-mono text-sm font-semibold mb-1">{api.api}</h4>
                    <div className="text-xs text-muted-foreground">{api.module} • {api.type}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getTierBadge(api.coverage_tier)}
                    {getImportanceBadge(api.importance)}
                  </div>
                </div>

                {api.documentation_references.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    Documented in {api.documentation_references.length} location{api.documentation_references.length !== 1 ? 's' : ''}: {' '}
                    {api.documented_in.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Heatmap Tab */}
      {activeTab === 'heatmap' && (
        <div>
          <h3 className="text-lg font-semibold mb-4">Coverage Heatmap</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Visual representation of which documents cover which APIs. Click cells to see details.
          </p>
          <CoverageHeatmap
            apiDetails={apiCompleteness.api_details}
            onCellClick={(api, doc) => setSelectedAPI(api)}
          />
        </div>
      )}

      {/* API Detail Modal */}
      {selectedAPI && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-background border border-border rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-border flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-xl font-mono font-bold mb-2">{selectedAPI.api}</h3>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">{selectedAPI.module}</span>
                  <span className="text-muted-foreground">•</span>
                  <span className="text-sm px-2 py-0.5 rounded bg-muted">{selectedAPI.type}</span>
                  {getTierBadge(selectedAPI.coverage_tier)}
                  {getImportanceBadge(selectedAPI.importance)}
                </div>
              </div>
              <button
                onClick={() => setSelectedAPI(null)}
                className="p-2 rounded-md hover:bg-accent"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6 space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground mb-1">Importance Score</div>
                  <div className="text-2xl font-bold">{selectedAPI.importance_score}/10</div>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground mb-1">Documents</div>
                  <div className="text-2xl font-bold">{selectedAPI.documented_in.length}</div>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground mb-1">References</div>
                  <div className="text-2xl font-bold">{selectedAPI.documentation_references.length}</div>
                </div>
              </div>

              {/* Documentation References */}
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <ExternalLink className="h-4 w-4" />
                  Documentation References
                </h4>
                {selectedAPI.documentation_references.length > 0 ? (
                  <div className="space-y-3">
                    {selectedAPI.documentation_references.map((ref, idx) => (
                      <ReferenceCard
                        key={`${ref.document}-${ref.line_number}-${idx}`}
                        reference={ref}
                        onClick={() => {
                          setSelectedAPI(null);
                          onNavigateToDoc(ref.document, ref.line_number, ref.markdown_anchor);
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    This API is not documented anywhere.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
