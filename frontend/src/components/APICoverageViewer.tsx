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

  // Filter API details (with fallback for legacy/incomplete data)
  const apiDetails = apiCompleteness.api_details || [];
  const filteredAPIs = apiDetails.filter(api => {
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
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-all cursor-pointer ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-primary/50 hover:bg-accent'
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
          {/* Coverage by Type */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Coverage by Type</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {apiCompleteness.coverage_by_type && Object.entries(apiCompleteness.coverage_by_type).map(([type, stats]: [string, any]) => (
                <div key={type} className="p-4 border border-border rounded-lg bg-card">
                  <div className="text-sm font-medium text-muted-foreground mb-2 capitalize">{type}s</div>
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-2xl font-bold">{stats.documented}/{stats.total}</span>
                    <span className="text-sm text-muted-foreground">documented</span>
                  </div>
                  <div className="text-lg font-semibold text-primary">{stats.coverage.toFixed(1)}%</div>
                  <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${stats.coverage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Coverage Distribution by Tier */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Coverage Distribution by Quality</h3>
            <p className="text-sm text-muted-foreground mb-4">
              How well are the documented APIs covered? Higher tiers indicate better documentation quality.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {apiCompleteness.coverage_distribution && Object.entries(apiCompleteness.coverage_distribution).map(([tier, data]: [string, any]) => {
                const tierColors: Record<string, { bg: string; border: string; bar: string; text: string; count: string }> = {
                  tier_3_comprehensive: {
                    bg: 'bg-emerald-50 dark:bg-emerald-950/30',
                    border: 'border-emerald-200 dark:border-emerald-800',
                    bar: 'bg-emerald-500',
                    text: 'text-emerald-900 dark:text-emerald-100',
                    count: 'text-emerald-600 dark:text-emerald-400'
                  },
                  tier_2_good: {
                    bg: 'bg-blue-50 dark:bg-blue-950/30',
                    border: 'border-blue-200 dark:border-blue-800',
                    bar: 'bg-blue-500',
                    text: 'text-blue-900 dark:text-blue-100',
                    count: 'text-blue-600 dark:text-blue-400'
                  },
                  tier_1_basic: {
                    bg: 'bg-amber-50 dark:bg-amber-950/30',
                    border: 'border-amber-200 dark:border-amber-800',
                    bar: 'bg-amber-500',
                    text: 'text-amber-900 dark:text-amber-100',
                    count: 'text-amber-600 dark:text-amber-400'
                  },
                  tier_0_undocumented: {
                    bg: 'bg-rose-50 dark:bg-rose-950/30',
                    border: 'border-rose-200 dark:border-rose-800',
                    bar: 'bg-rose-500',
                    text: 'text-rose-900 dark:text-rose-100',
                    count: 'text-rose-600 dark:text-rose-400'
                  }
                };
                const colors = tierColors[tier] || tierColors.tier_1_basic;
                const tierName = tier.replace('tier_', 'Tier ').replace('_', ' - ').split(' - ').map(word =>
                  word.charAt(0).toUpperCase() + word.slice(1)
                ).join(' - ');

                return (
                  <div key={tier} className={`p-5 border ${colors.border} rounded-lg ${colors.bg} transition-all hover:shadow-md`}>
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className={`text-base font-bold mb-1 ${colors.text}`}>{tierName}</div>
                        <div className="text-xs text-muted-foreground leading-relaxed">{data.description}</div>
                      </div>
                      <div className="text-right ml-4">
                        <div className={`text-3xl font-bold ${colors.count}`}>{data.count}</div>
                        <div className={`text-sm font-medium ${colors.count}`}>{data.percentage.toFixed(1)}%</div>
                      </div>
                    </div>
                    <div className="h-2.5 bg-white dark:bg-gray-900 rounded-full overflow-hidden shadow-inner">
                      <div
                        className={`h-full ${colors.bar} transition-all duration-500 ease-out`}
                        style={{ width: `${data.percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Deprecated APIs */}
          {apiCompleteness.coverage_summary?.deprecated_count > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Deprecated APIs</h3>
              <div className="p-5 border border-amber-200 dark:border-amber-800 rounded-lg bg-amber-50 dark:bg-amber-950/30 hover:shadow-md transition-all">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 w-16 h-16 rounded-full bg-amber-100 dark:bg-amber-900 flex items-center justify-center">
                    <div className="text-3xl font-bold text-amber-700 dark:text-amber-300">
                      {apiCompleteness.coverage_summary.deprecated_count}
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="text-base font-bold text-amber-900 dark:text-amber-100 mb-1">Deprecated APIs Found</div>
                    <div className="text-sm text-amber-800 dark:text-amber-200">
                      These APIs are marked as deprecated and may need documentation updates or removal warnings.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
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

                {api.documentation_references && api.documentation_references.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    Documented in {api.documentation_references.length} location{api.documentation_references.length !== 1 ? 's' : ''}: {' '}
                    {api.documented_in && api.documented_in.join(', ')}
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
        <div className="settings-modal-backdrop" onClick={() => setSelectedAPI(null)}>
          <div className="settings-modal-container" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="settings-modal-header">
              <div className="flex-1">
                <h2 className="settings-modal-title font-mono">
                  {selectedAPI.api}
                </h2>
                <div className="flex items-center gap-3 flex-wrap mt-2">
                  <span className="text-sm text-muted-foreground">{selectedAPI.module}</span>
                  <span className="text-muted-foreground">•</span>
                  <span className="text-sm px-2 py-0.5 rounded bg-muted text-foreground font-medium">{selectedAPI.type}</span>
                  {getTierBadge(selectedAPI.coverage_tier)}
                  {getImportanceBadge(selectedAPI.importance)}
                </div>
              </div>
              <button
                onClick={() => setSelectedAPI(null)}
                className="settings-modal-close-btn"
                aria-label="Close API details"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="settings-modal-content">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="settings-help-box" style={{ marginBottom: 0 }}>
                  <div className="settings-help-box-text">
                    <p className="settings-subsection-title" style={{ marginBottom: '0.5rem' }}>Importance Score</p>
                    <div className="text-3xl font-bold" style={{ color: 'hsl(var(--foreground))' }}>{selectedAPI.importance_score}/10</div>
                  </div>
                </div>
                <div className="settings-help-box" style={{ marginBottom: 0 }}>
                  <div className="settings-help-box-text">
                    <p className="settings-subsection-title" style={{ marginBottom: '0.5rem' }}>Documents</p>
                    <div className="text-3xl font-bold" style={{ color: 'hsl(var(--foreground))' }}>{selectedAPI.documented_in?.length || 0}</div>
                  </div>
                </div>
                <div className="settings-help-box" style={{ marginBottom: 0 }}>
                  <div className="settings-help-box-text">
                    <p className="settings-subsection-title" style={{ marginBottom: '0.5rem' }}>References</p>
                    <div className="text-3xl font-bold" style={{ color: 'hsl(var(--foreground))' }}>{selectedAPI.documentation_references?.length || 0}</div>
                  </div>
                </div>
              </div>

              {/* Documentation References */}
              <div className="settings-divider">
                <h3 className="settings-label">
                  <ExternalLink className="settings-label-icon" />
                  Documentation References
                </h3>
                {selectedAPI.documentation_references && selectedAPI.documentation_references.length > 0 ? (
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
                  <p className="settings-input-hint">
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
