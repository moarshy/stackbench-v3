import { useState, useEffect } from 'react';
import { FileText, CheckCircle2, Search, Settings as SettingsIcon, ChevronLeft, ChevronRight, Code, Play, BookOpen, Route, PieChart } from 'lucide-react';
import type {
  ExtractionOutput,
  ValidationOutput,
  CCAPISignatureValidationOutput,
  CCCodeExampleValidationOutput,
  CCClarityValidationOutput,
  RunInfo as RunInfoType,
  WalkthroughData,
  APICompletenessOutput
} from './types';
import { apiService, configInitialized } from './services/api';
import { Settings } from './components/Settings';
import { MarkdownViewer } from './components/MarkdownViewer';
import { Tabs, TabPanel } from './components/Tabs';
import { RunSelector } from './components/RunSelector';
import { RunInfo } from './components/RunInfo';
import { WalkthroughViewer } from './components/WalkthroughViewer';
import { APICoverageViewer } from './components/APICoverageViewer';

function App() {
  const [configReady, setConfigReady] = useState(false);
  const [selectedRun, setSelectedRun] = useState<RunInfoType | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [docs, setDocs] = useState<string[]>([]);
  const [docContent, setDocContent] = useState<string>('');
  const [extraction, setExtraction] = useState<ExtractionOutput | null>(null);
  const [validation, setValidation] = useState<ValidationOutput | null>(null);
  const [ccApiSigValidation, setCCApiSigValidation] = useState<CCAPISignatureValidationOutput | null>(null);
  const [ccCodeExValidation, setCCCodeExValidation] = useState<CCCodeExampleValidationOutput | null>(null);
  const [ccClarityValidation, setCCClarityValidation] = useState<CCClarityValidationOutput | null>(null);
  const [walkthroughs, setWalkthroughs] = useState<string[]>([]);
  const [walkthroughTitles, setWalkthroughTitles] = useState<Map<string, string>>(new Map());
  const [walkthroughSources, setWalkthroughSources] = useState<Map<string, string>>(new Map());
  const [selectedWalkthrough, setSelectedWalkthrough] = useState<string | null>(null);
  const [walkthroughData, setWalkthroughData] = useState<WalkthroughData | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState('extraction');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [docPaneCollapsed, setDocPaneCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState<'documents' | 'walkthroughs' | 'api-coverage'>('documents');
  const [apiCompleteness, setApiCompleteness] = useState<APICompletenessOutput | null>(null);
  const [showAllUndocumented, setShowAllUndocumented] = useState(false);

  // Wait for config to be initialized from backend
  useEffect(() => {
    configInitialized.then(() => {
      setConfigReady(true);
    });
  }, []);

  // Parse URL parameters on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const docName = params.get('doc');
    const tab = params.get('tab');
    const viewModeParam = params.get('viewMode');

    // If run ID in URL, we'll let RunSelector handle loading it
    // This is just for updating the doc and tab after the run loads
    if (docName) {
      setSelectedDoc(docName);
    }
    if (tab) {
      setActiveTab(tab);
    }
    // Restore viewMode from URL, validate it's a valid value
    if (viewModeParam && ['documents', 'walkthroughs', 'api-coverage'].includes(viewModeParam)) {
      setViewMode(viewModeParam as 'documents' | 'walkthroughs' | 'api-coverage');
    }
  }, []);

  // Update URL when selections change
  useEffect(() => {
    if (selectedRun || selectedDoc || activeTab !== 'extraction' || viewMode !== 'documents') {
      const params = new URLSearchParams();
      if (selectedRun) {
        params.set('run', selectedRun.run_id);
      }
      if (selectedDoc) {
        params.set('doc', selectedDoc);
      }
      if (activeTab !== 'extraction') {
        params.set('tab', activeTab);
      }
      // Always persist viewMode to URL
      params.set('viewMode', viewMode);
      const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
      window.history.replaceState({}, '', newUrl);
    }
  }, [selectedRun, selectedDoc, activeTab, viewMode]);

  // Load documentation files when run is selected
  useEffect(() => {
    if (selectedRun) {
      apiService.setRunId(selectedRun.run_id);
      // Reset state immediately to avoid showing stale data
      setDocs([]);
      setWalkthroughs([]);
      setApiCompleteness(null);
      setSelectedDoc(null);
      setSelectedWalkthrough(null);
      // Load new data
      loadDocs();
      loadWalkthroughs();
      loadAPICompleteness();
    } else {
      // Clear everything if no run selected
      setDocs([]);
      setWalkthroughs([]);
      setApiCompleteness(null);
    }
  }, [selectedRun]);

  // Load data when document is selected
  useEffect(() => {
    if (selectedDoc && selectedRun) {
      loadDocumentData(selectedDoc);
    }
  }, [selectedDoc, selectedRun]);

  // Load walkthrough data when walkthrough is selected
  useEffect(() => {
    if (selectedWalkthrough && selectedRun) {
      loadWalkthroughData(selectedWalkthrough);
    }
  }, [selectedWalkthrough, selectedRun]);

  const loadDocs = async () => {
    try {
      const files = await apiService.getDocumentationFiles();
      console.log(`✅ Loaded ${files.length} documentation files for run ${selectedRun?.run_id}`);
      setDocs(files);
      if (files.length === 0) {
        console.warn('⚠️ No extraction files found. Check that results/extraction/ directory exists and contains *_analysis.json files');
      }
    } catch (error) {
      console.error('❌ Failed to load documentation files:', error);
      setDocs([]);
    }
  };

  const loadWalkthroughs = async () => {
    try {
      const wtIds = await apiService.getWalkthroughs();
      setWalkthroughs(wtIds);

      // Fetch titles and source docs for all walkthroughs
      const titles = new Map<string, string>();
      const sources = new Map<string, string>();
      for (const wtId of wtIds) {
        try {
          const data = await apiService.getWalkthroughData(wtId);
          if (data) {
            titles.set(wtId, data.walkthrough.walkthrough.title);
            // Extract source doc from metadata
            if (data.walkthrough.metadata?.originalDocPath) {
              // Extract just the filename from the path
              const sourcePath = data.walkthrough.metadata.originalDocPath;
              const filename = sourcePath.split('/').pop() || sourcePath;
              sources.set(wtId, filename);
            }
          }
        } catch (err) {
          console.error(`Failed to fetch metadata for ${wtId}:`, err);
          titles.set(wtId, wtId); // Fallback to ID
        }
      }
      setWalkthroughTitles(titles);
      setWalkthroughSources(sources);

      // Auto-select first walkthrough if available
      if (wtIds.length > 0 && !selectedWalkthrough) {
        setSelectedWalkthrough(wtIds[0]);
      }
    } catch (error) {
      console.error('Failed to load walkthroughs:', error);
    }
  };

  const loadAPICompleteness = async () => {
    try {
      const data = await apiService.getAPICompleteness();
      setApiCompleteness(data);
    } catch (error) {
      console.error('Failed to load API completeness:', error);
      setApiCompleteness(null);
    }
  };

  const loadDocumentData = async (docName: string) => {
    setLoading(true);
    try {
      const [
        content,
        extractionData,
        validationData,
        ccApiSigData,
        ccCodeExData,
        ccClarityData
      ] = await Promise.all([
        apiService.getDocumentationContent(docName),
        apiService.getExtractionOutput(docName),
        apiService.getValidationOutput(docName),
        apiService.getCCApiSignatureValidation(docName),
        apiService.getCCCodeExampleValidation(docName),
        apiService.getCCClarityValidation(docName),
      ]);

      setDocContent(content);
      setExtraction(extractionData);
      setValidation(validationData);
      setCCApiSigValidation(ccApiSigData);
      setCCCodeExValidation(ccCodeExData);
      setCCClarityValidation(ccClarityData);
    } catch (error) {
      console.error('Failed to load document data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadWalkthroughData = async (walkthroughId: string) => {
    setLoading(true);
    try {
      const data = await apiService.getWalkthroughData(walkthroughId);
      setWalkthroughData(data);
    } catch (error) {
      console.error('Failed to load walkthrough data:', error);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'extraction', label: 'Extraction', icon: <Search className="h-4 w-4" /> },
    { id: 'cc-api-sig', label: 'API Signature', icon: <CheckCircle2 className="h-4 w-4" /> },
    { id: 'cc-code-ex', label: 'Code Examples', icon: <Code className="h-4 w-4" /> },
    { id: 'cc-clarity', label: 'Clarity', icon: <BookOpen className="h-4 w-4" /> },
  ];

  return (
    <div className="flex h-screen bg-background relative">
      {/* Sidebar - Doc List */}
      <div
        className={`border-r border-border bg-card transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? 'w-0 opacity-0' : 'w-64 opacity-100'
        } flex-shrink-0 relative`}
      >
        <div className="w-64 h-full flex flex-col">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Documentation Files
            </h2>
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="p-1.5 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>
          <div className="p-2 flex-1 overflow-auto flex flex-col gap-3">
            {/* Run Info Card */}
            {selectedRun && <RunInfo runInfo={selectedRun} />}

            {/* Doc Search and List */}
            <div className="relative mb-2">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search docs..."
                className="w-full pl-8 pr-2 py-2 text-sm rounded-md border border-input bg-background"
              />
            </div>
            <div className="space-y-1">
              {docs.length === 0 && selectedRun && (
                <div className="px-3 py-2 text-sm text-muted-foreground">
                  No documentation files found in this run.
                </div>
              )}
              {docs.map((doc) => (
                <button
                  key={doc}
                  onClick={() => setSelectedDoc(doc)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-all cursor-pointer flex items-center gap-2 ${
                    selectedDoc === doc
                      ? 'bg-primary text-primary-foreground font-medium shadow-sm ring-2 ring-primary/20'
                      : 'hover:bg-accent hover:text-accent-foreground'
                  }`}
                >
                  {selectedDoc === doc && (
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-foreground flex-shrink-0"></span>
                  )}
                  <span className="truncate">{doc}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-border bg-card px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-1">
              {/* Expand Button (when collapsed) */}
              {sidebarCollapsed && (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setSidebarCollapsed(false);
                  }}
                  className="relative z-50 p-2 rounded-md bg-background border border-border shadow-sm hover:bg-accent hover:shadow-md transition-all flex items-center gap-2 cursor-pointer"
                  title="Expand sidebar"
                  type="button"
                >
                  <ChevronRight className="h-5 w-5 pointer-events-none" />
                  <span className="text-sm font-medium pointer-events-none">Docs</span>
                </button>
              )}
              <div className="flex-1">
                <h1 className="text-2xl font-bold">StackBench Documentation Validator</h1>
                <p className="text-sm text-muted-foreground">
                  {viewMode === 'documents'
                    ? 'View documentation, extraction results, and validation'
                    : viewMode === 'walkthroughs'
                    ? 'View walkthrough tutorials and audit results'
                    : 'View API coverage analysis and completeness metrics'}
                </p>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center gap-1 p-1 bg-muted rounded-lg">
                <button
                  onClick={() => setViewMode('documents')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 cursor-pointer ${
                    viewMode === 'documents'
                      ? 'bg-background shadow-sm text-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                  }`}
                >
                  <FileText className="h-4 w-4" />
                  Documents
                </button>
                <button
                  onClick={() => setViewMode('walkthroughs')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 cursor-pointer ${
                    viewMode === 'walkthroughs'
                      ? 'bg-background shadow-sm text-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                  }`}
                >
                  <Route className="h-4 w-4" />
                  Walkthroughs
                  {walkthroughs.length > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground text-xs">
                      {walkthroughs.length}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setViewMode('api-coverage')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 cursor-pointer ${
                    viewMode === 'api-coverage'
                      ? 'bg-background shadow-sm text-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                  }`}
                >
                  <PieChart className="h-4 w-4" />
                  API Coverage
                  {apiCompleteness?.coverage_summary && (
                    <span className="px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground text-xs">
                      {apiCompleteness.coverage_summary.coverage_percentage.toFixed(0)}%
                    </span>
                  )}
                </button>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {/* Run Selector - wait for config to be ready */}
              {configReady ? (
                <RunSelector
                  selectedRun={selectedRun}
                  onRunSelect={setSelectedRun}
                  baseDataDir={apiService.getBaseDataDir()}
                />
              ) : (
                <div className="px-4 py-2 bg-muted rounded-md text-sm text-muted-foreground">
                  Initializing...
                </div>
              )}
              {selectedDoc && (
                <div className="flex items-center gap-2 text-sm px-3 py-1.5 bg-accent rounded-md">
                  <FileText className="h-4 w-4" />
                  <span className="font-medium">{selectedDoc}</span>
                </div>
              )}
              <button
                onClick={() => setShowSettings(true)}
                className="p-2 rounded-md hover:bg-accent hover:text-accent-foreground"
                title="Settings"
              >
                <SettingsIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Content Area - Documents or Walkthroughs */}
        {!selectedRun ? (
          <div className="flex-1 flex items-center justify-center text-center p-6">
            <div>
              <Play className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-xl font-semibold mb-2">No Run Selected</h3>
              <p className="text-muted-foreground max-w-md">
                Select a validation run from the dropdown above, or run the stackbench CLI first:<br />
                <code className="mt-2 inline-block px-2 py-1 bg-muted rounded text-sm">stackbench run --repo ...</code>
              </p>
            </div>
          </div>
        ) : viewMode === 'walkthroughs' ? (
          /* WALKTHROUGHS MODE */
          <div className="flex-1 overflow-hidden">
            {walkthroughs.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-center p-6">
                <div>
                  <Route className="h-16 w-16 mx-auto text-muted-foreground mb-4 opacity-50" />
                  <h3 className="text-xl font-semibold mb-2">No Walkthroughs Available</h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                    This run doesn't have any walkthroughs yet. Generate a walkthrough from documentation:
                  </p>
                  <code className="block px-3 py-2 bg-muted rounded text-xs">
                    stackbench walkthrough generate --repo ... --doc-path docs/quickstart.md
                  </code>
                </div>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                {/* Walkthrough selector - always visible */}
                <div className="p-4 border-b border-border bg-card">
                  <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                    <Route className="h-4 w-4" />
                    {walkthroughs.length > 1 ? (
                      <span>Select Walkthrough ({walkthroughs.length} available)</span>
                    ) : (
                      <span>Walkthrough</span>
                    )}
                  </label>
                  {walkthroughs.length > 1 ? (
                    <select
                      value={selectedWalkthrough || ''}
                      onChange={(e) => setSelectedWalkthrough(e.target.value)}
                      className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm hover:bg-accent transition-colors cursor-pointer"
                    >
                      {walkthroughs.map((wtId) => {
                        const title = walkthroughTitles.get(wtId) || wtId;
                        const source = walkthroughSources.get(wtId);
                        return (
                          <option key={wtId} value={wtId}>
                            {title}{source ? ` • from ${source}` : ''}
                          </option>
                        );
                      })}
                    </select>
                  ) : (
                    <div className="space-y-1">
                      <div className="px-3 py-2 rounded-md border border-input bg-muted text-sm font-medium">
                        {walkthroughTitles.get(selectedWalkthrough || '') || selectedWalkthrough || 'Loading...'}
                      </div>
                      {selectedWalkthrough && walkthroughSources.get(selectedWalkthrough) && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
                          <FileText className="h-3 w-3" />
                          <span>Based on: {walkthroughSources.get(selectedWalkthrough)}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Walkthrough viewer */}
                <div className="flex-1 overflow-hidden">
                  {walkthroughData ? (
                    <WalkthroughViewer data={walkthroughData} />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center p-6">
                        <Route className="h-12 w-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                        <p className="text-sm text-muted-foreground">
                          {loading ? 'Loading walkthrough...' : 'Select a walkthrough to view details'}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : viewMode === 'api-coverage' ? (
          /* API COVERAGE MODE */
          <div className="flex-1 overflow-auto p-6">
            {!apiCompleteness ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <PieChart className="h-16 w-16 mx-auto text-muted-foreground mb-4 opacity-50" />
                  <h3 className="text-xl font-semibold mb-2">No API Coverage Data</h3>
                  <p className="text-sm text-muted-foreground">
                    API completeness analysis not available for this run
                  </p>
                </div>
              </div>
            ) : (
              <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div>
                  <h2 className="text-2xl font-bold mb-2">API Coverage Analysis</h2>
                  <p className="text-muted-foreground">
                    {apiCompleteness.library} v{apiCompleteness.version} • Analyzed {new Date(apiCompleteness.analyzed_at).toLocaleString()}
                  </p>
                </div>

                {/* Coverage Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="p-4 border border-border rounded-lg bg-card">
                    <div className="text-sm text-muted-foreground mb-1">Coverage</div>
                    <div className={`text-3xl font-bold ${
                      apiCompleteness.coverage_summary.coverage_percentage >= 80 ? 'text-green-600' :
                      apiCompleteness.coverage_summary.coverage_percentage >= 50 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {apiCompleteness.coverage_summary.coverage_percentage.toFixed(1)}%
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {apiCompleteness.coverage_summary.documented}/{apiCompleteness.coverage_summary.total_apis} APIs
                    </div>
                  </div>

                  <div className="p-4 border border-border rounded-lg bg-card">
                    <div className="text-sm text-muted-foreground mb-1">With Examples</div>
                    <div className="text-3xl font-bold text-blue-600">
                      {apiCompleteness.coverage_summary.with_examples ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {(apiCompleteness.coverage_summary.example_coverage_percentage ?? 0).toFixed(1)}% have code examples
                    </div>
                  </div>

                  <div className="p-4 border border-border rounded-lg bg-card">
                    <div className="text-sm text-muted-foreground mb-1">Complete Docs</div>
                    <div className="text-3xl font-bold text-purple-600">
                      {apiCompleteness.coverage_summary.with_dedicated_sections ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {(apiCompleteness.coverage_summary.complete_coverage_percentage ?? 0).toFixed(1)}% with dedicated sections
                    </div>
                  </div>

                  <div className="p-4 border border-border rounded-lg bg-card">
                    <div className="text-sm text-muted-foreground mb-1">Undocumented</div>
                    <div className="text-3xl font-bold text-orange-600">
                      {apiCompleteness.coverage_summary.undocumented}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {(Array.isArray(apiCompleteness.undocumented_apis)
                        ? apiCompleteness.undocumented_apis.filter(api => api.importance === 'high').length
                        : (apiCompleteness.undocumented_apis?.high_priority || []).length
                      )} high priority
                    </div>
                  </div>
                </div>

                {/* Deprecated APIs Warning */}
                {(apiCompleteness.deprecated_in_docs || []).length > 0 && (
                  <div className="p-4 border border-red-200 dark:border-red-900 rounded-lg bg-red-50 dark:bg-red-950">
                    <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
                      ⚠️ Deprecated APIs in Documentation
                    </h3>
                    <p className="text-sm text-red-800 dark:text-red-200 mb-3">
                      Found {(apiCompleteness.deprecated_in_docs || []).length} deprecated API(s) still being taught in docs
                    </p>
                    <div className="space-y-2">
                      {(apiCompleteness.deprecated_in_docs || []).map((dep, idx) => (
                        <div key={idx} className="p-3 bg-white dark:bg-gray-900 rounded border border-red-200 dark:border-red-800">
                          <code className="text-sm font-mono">{dep.api}</code>
                          <p className="text-xs text-muted-foreground mt-1">{dep.suggestion}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Enhanced API Coverage Viewer */}
                <APICoverageViewer
                  apiCompleteness={apiCompleteness}
                  onNavigateToDoc={(docName, lineNumber, anchor) => {
                    // Switch to documents mode
                    setViewMode('documents');
                    // Select the document
                    setSelectedDoc(docName);
                    // Scroll to line after a brief delay to allow document to load
                    setTimeout(() => {
                      // Implementation would scroll to line/anchor in the MarkdownViewer
                      // For now, just switching docs is a good start
                    }, 200);
                  }}
                />
              </div>
            )}
          </div>
        ) : !selectedDoc ? (
          /* DOCUMENTS MODE - No document selected */
          <div className="flex-1 flex items-center justify-center text-center p-6">
            <div>
              <FileText className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-xl font-semibold mb-2">No Document Selected</h3>
              <p className="text-muted-foreground">
                Select a documentation file from the sidebar to view extraction and validation results
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Pane - Documentation Viewer */}
            <div
              className={`border-r border-border overflow-auto transition-all duration-300 ${
                docPaneCollapsed ? 'w-0 opacity-0' : 'flex-1 opacity-100'
              }`}
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Documentation
                  </h3>
                  <button
                    onClick={() => setDocPaneCollapsed(true)}
                    className="p-1.5 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                    title="Collapse documentation pane"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>

                {/* Validation Summary Badge */}
                {ccCodeExValidation && (
                  <div className="mb-4 p-3 bg-muted rounded-lg flex items-center gap-3 text-sm">
                    <div className="flex items-center gap-3 flex-wrap">
                      {ccCodeExValidation.successful > 0 && (
                        <span className="text-green-600 dark:text-green-400 font-semibold flex items-center gap-1">
                          ✅ {ccCodeExValidation.successful} passed
                        </span>
                      )}
                      {(() => {
                        const errorCount = ccCodeExValidation.results.filter(r => r.status === 'failure' && r.severity === 'error').length;
                        const warningCount = ccCodeExValidation.results.filter(r => r.status === 'failure' && r.severity === 'warning').length;
                        const infoCount = ccCodeExValidation.results.filter(r => r.status === 'failure' && r.severity === 'info').length;

                        return (
                          <>
                            {errorCount > 0 && (
                              <span className="text-red-600 dark:text-red-400 font-semibold flex items-center gap-1">
                                ⚠️ {errorCount} error{errorCount > 1 ? 's' : ''}
                              </span>
                            )}
                            {warningCount > 0 && (
                              <span className="text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1">
                                ⚡ {warningCount} warning{warningCount > 1 ? 's' : ''}
                              </span>
                            )}
                            {infoCount > 0 && (
                              <span className="text-blue-600 dark:text-blue-400 flex items-center gap-1">
                                ℹ️ {infoCount} info
                              </span>
                            )}
                          </>
                        );
                      })()}
                      {ccCodeExValidation.skipped > 0 && (
                        <span className="text-gray-600 dark:text-gray-400 flex items-center gap-1">
                          ⏭️ {ccCodeExValidation.skipped} skipped
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground ml-auto">
                      {ccCodeExValidation.total_examples} total examples
                    </div>
                  </div>
                )}

                {loading ? (
                  <div className="text-sm text-muted-foreground">Loading...</div>
                ) : (
                  <MarkdownViewer
                    content={docContent}
                    baseImagePath={selectedRun ? `${apiService.getBaseDataDir()}/${selectedRun.run_id}/repository` : ''}
                    codeValidation={ccCodeExValidation}
                    onExampleClick={(exampleIndex) => {
                      // Scroll to the example with this index
                      const element = document.querySelector(`[data-example-index="${exampleIndex}"]`);
                      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      // Highlight briefly
                      element?.classList.add('ring-2', 'ring-primary');
                      setTimeout(() => element?.classList.remove('ring-2', 'ring-primary'), 2000);
                    }}
                    onViewInValidationTab={(exampleIndex) => {
                      // Switch to code validation tab
                      setActiveTab('cc-code-ex');
                      // Scroll to result after tab switch and highlight it
                      setTimeout(() => {
                        const element = document.querySelector(`[data-result-index="${exampleIndex}"]`);
                        element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        // Highlight briefly
                        element?.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
                        setTimeout(() => element?.classList.remove('ring-2', 'ring-primary', 'ring-offset-2'), 2000);
                      }, 100);
                    }}
                  />
                )}
              </div>
            </div>

            {/* Right Pane - Results with Tabs */}
            <div className="flex-1 flex flex-col overflow-hidden relative">
              {/* Expand button when doc pane is collapsed */}
              {docPaneCollapsed && (
                <button
                  onClick={() => setDocPaneCollapsed(false)}
                  className="absolute left-2 top-2 z-10 p-2 rounded-md bg-background border border-border shadow-sm hover:bg-accent hover:shadow-md transition-all flex items-center gap-2"
                  title="Expand documentation pane"
                >
                  <ChevronRight className="h-4 w-4" />
                  <span className="text-sm font-medium">Show Docs</span>
                </button>
              )}
              <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
                {/* Extraction Tab */}
                <TabPanel value="extraction" activeTab={activeTab}>
                  {loading ? (
                    <div className="text-sm text-muted-foreground">Loading...</div>
                  ) : extraction ? (
                    <div className="space-y-4">
                      <div className="p-4 rounded-md bg-muted">
                        <div className="text-sm font-medium mb-2">Summary</div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-xs text-muted-foreground">Signatures</div>
                            <div className="text-2xl font-bold">{extraction.total_signatures}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">Examples</div>
                            <div className="text-2xl font-bold">{extraction.total_examples}</div>
                          </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-border/50">
                          <div className="text-xs text-muted-foreground">
                            Library: <span className="font-medium text-foreground">{extraction.library}</span> ({extraction.version})
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Language: <span className="font-medium text-foreground">{extraction.language}</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-semibold mb-3">API Signatures</h4>
                        <div className="space-y-2">
                          {extraction.signatures.map((sig, idx) => (
                            <div key={idx} className="p-3 rounded-md bg-card border border-border">
                              <div className="flex items-start justify-between mb-2">
                                <div className="font-mono text-sm font-semibold">{sig.function}</div>
                                <div className="text-xs text-muted-foreground">Line {sig.line}</div>
                              </div>
                              {sig.method_chain && (
                                <div className="text-xs text-muted-foreground mb-2">
                                  Chain: {sig.method_chain}
                                </div>
                              )}
                              <div className="text-xs">
                                <span className="text-muted-foreground">Parameters: </span>
                                {sig.params.length > 0 ? (
                                  <span className="font-mono">{sig.params.join(', ')}</span>
                                ) : (
                                  <span className="text-muted-foreground italic">none</span>
                                )}
                              </div>
                              {Object.keys(sig.param_types).length > 0 && (
                                <div className="text-xs mt-1">
                                  <span className="text-muted-foreground">Types: </span>
                                  <span className="font-mono">
                                    {Object.entries(sig.param_types).map(([k, v]) => `${k}: ${v}`).join(', ')}
                                  </span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {extraction.examples.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold mb-3">Code Examples</h4>
                          <div className="space-y-2">
                            {extraction.examples.map((ex, idx) => (
                              <div key={idx} className="p-3 rounded-md bg-card border border-border">
                                <div className="flex items-center justify-between mb-2">
                                  <div className="text-xs font-medium">{ex.language}</div>
                                  <div className="flex gap-2 text-xs">
                                    {ex.is_executable && (
                                      <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-600">
                                        Executable
                                      </span>
                                    )}
                                    {ex.has_main && (
                                      <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-600">
                                        Has Main
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                                  <code>{ex.code}</code>
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No extraction data available
                    </p>
                  )}
                </TabPanel>

                {/* Validation Tab */}
                <TabPanel value="validation" activeTab={activeTab}>
                  {loading ? (
                    <div className="text-sm text-muted-foreground">Loading...</div>
                  ) : validation ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-4 rounded-md bg-green-500/10 border border-green-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Valid</div>
                          <div className="text-3xl font-bold text-green-600">{validation.summary.valid}</div>
                        </div>
                        <div className="p-4 rounded-md bg-yellow-500/10 border border-yellow-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Partial Match</div>
                          <div className="text-3xl font-bold text-yellow-600">{validation.summary.partial_match}</div>
                        </div>
                        <div className="p-4 rounded-md bg-red-500/10 border border-red-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Mismatch</div>
                          <div className="text-3xl font-bold text-red-600">{validation.summary.mismatch}</div>
                        </div>
                        <div className="p-4 rounded-md bg-blue-500/10 border border-blue-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Not Found</div>
                          <div className="text-3xl font-bold text-blue-600">{validation.summary.not_found}</div>
                        </div>
                      </div>

                      <div className="p-4 rounded-md bg-muted">
                        <div className="text-sm font-medium mb-2">Accuracy Score</div>
                        <div className="text-4xl font-bold">
                          {(validation.summary.accuracy_score * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground mt-2">
                          {validation.summary.total_signatures} total signatures validated
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-semibold mb-3">Validation Details</h4>
                        <div className="space-y-2">
                          {validation.validations.map((v, idx) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-md border ${
                                v.status === 'valid'
                                  ? 'bg-green-500/5 border-green-500/20'
                                  : v.status === 'partial_match'
                                    ? 'bg-yellow-500/5 border-yellow-500/20'
                                    : v.status === 'mismatch'
                                      ? 'bg-red-500/5 border-red-500/20'
                                      : 'bg-blue-500/5 border-blue-500/20'
                              }`}
                            >
                              <div className="flex items-start justify-between mb-2">
                                <div className="font-mono text-sm font-semibold">{v.function_name}</div>
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    v.status === 'valid'
                                      ? 'bg-green-500/20 text-green-700'
                                      : v.status === 'partial_match'
                                        ? 'bg-yellow-500/20 text-yellow-700'
                                        : v.status === 'mismatch'
                                          ? 'bg-red-500/20 text-red-700'
                                          : 'bg-blue-500/20 text-blue-700'
                                  }`}
                                >
                                  {v.status.replace('_', ' ')}
                                </span>
                              </div>
                              {v.code_location && (
                                <div className="text-xs text-muted-foreground mb-2">
                                  Location: {v.code_location}
                                </div>
                              )}
                              <div className="text-xs mb-1">
                                Confidence: <span className="font-semibold">{(v.match_confidence * 100).toFixed(0)}%</span>
                              </div>
                              {v.parameter_mismatches.length > 0 && (() => {
                                // Group mismatches by severity
                                const critical = v.parameter_mismatches.filter(pm => pm.severity === 'critical');
                                const medium = v.parameter_mismatches.filter(pm => pm.severity === 'medium');
                                const low = v.parameter_mismatches.filter(pm => pm.severity === 'low');
                                const info = v.parameter_mismatches.filter(pm => pm.severity === 'info');

                                return (
                                  <div className="mt-2 pt-2 border-t border-border/50">
                                    <div className="text-xs font-medium mb-2">Parameter Issues:</div>

                                    {/* Critical Issues */}
                                    {critical.length > 0 && (
                                      <div className="mb-2">
                                        <div className="text-xs font-semibold text-red-700 mb-1 flex items-center gap-1">
                                          <span className="inline-block w-2 h-2 bg-red-500 rounded-full"></span>
                                          Critical ({critical.length})
                                        </div>
                                        <div className="space-y-1">
                                          {critical.map((pm, pmIdx) => (
                                            <div key={pmIdx} className="text-xs bg-red-50 border-l-4 border-red-500 p-2 rounded">
                                              <div className="font-medium text-red-900">{pm.parameter_name}</div>
                                              <div className="text-red-700 text-xs mt-0.5">
                                                {pm.issue_type.replace(/_/g, ' ')}
                                              </div>
                                              <div className="text-red-600 italic text-xs mt-1">{pm.description}</div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Medium Issues */}
                                    {medium.length > 0 && (
                                      <div className="mb-2">
                                        <div className="text-xs font-semibold text-orange-700 mb-1 flex items-center gap-1">
                                          <span className="inline-block w-2 h-2 bg-orange-500 rounded-full"></span>
                                          Medium ({medium.length})
                                        </div>
                                        <div className="space-y-1">
                                          {medium.map((pm, pmIdx) => (
                                            <div key={pmIdx} className="text-xs bg-orange-50 border-l-4 border-orange-500 p-2 rounded">
                                              <div className="font-medium text-orange-900">{pm.parameter_name}</div>
                                              <div className="text-orange-700 text-xs mt-0.5">
                                                {pm.issue_type.replace(/_/g, ' ')}
                                              </div>
                                              <div className="text-orange-600 italic text-xs mt-1">{pm.description}</div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Low Issues */}
                                    {low.length > 0 && (
                                      <div className="mb-2">
                                        <div className="text-xs font-semibold text-yellow-700 mb-1 flex items-center gap-1">
                                          <span className="inline-block w-2 h-2 bg-yellow-500 rounded-full"></span>
                                          Low ({low.length})
                                        </div>
                                        <div className="space-y-1">
                                          {low.map((pm, pmIdx) => (
                                            <div key={pmIdx} className="text-xs bg-yellow-50 border-l-4 border-yellow-500 p-2 rounded">
                                              <div className="font-medium text-yellow-900">{pm.parameter_name}</div>
                                              <div className="text-yellow-700 text-xs mt-0.5">
                                                {pm.issue_type.replace(/_/g, ' ')}
                                              </div>
                                              <div className="text-yellow-600 italic text-xs mt-1">{pm.description}</div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Info Items */}
                                    {info.length > 0 && (
                                      <div className="mb-2">
                                        <div className="text-xs font-semibold text-blue-700 mb-1 flex items-center gap-1">
                                          <span className="inline-block w-2 h-2 bg-blue-400 rounded-full"></span>
                                          Info ({info.length}) - Optional parameters OK to skip
                                        </div>
                                        <div className="space-y-1">
                                          {info.map((pm, pmIdx) => (
                                            <div key={pmIdx} className="text-xs bg-blue-50 border-l-4 border-blue-300 p-2 rounded">
                                              <div className="font-medium text-blue-900">{pm.parameter_name}</div>
                                              <div className="text-blue-700 text-xs mt-0.5">
                                                {pm.issue_type.replace(/_/g, ' ')}
                                              </div>
                                              <div className="text-blue-600 italic text-xs mt-1">{pm.description}</div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })()}
                              {v.suggested_fixes.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-border/50">
                                  <div className="text-xs font-medium mb-1">Suggested Fixes:</div>
                                  <ul className="text-xs text-muted-foreground space-y-0.5 list-disc list-inside">
                                    {v.suggested_fixes.map((fix, fixIdx) => (
                                      <li key={fixIdx}>{fix}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No validation data available
                    </p>
                  )}
                </TabPanel>

                {/* CC API Signature Tab */}
                <TabPanel value="cc-api-sig" activeTab={activeTab}>
                  {loading ? (
                    <div className="text-sm text-muted-foreground">Loading...</div>
                  ) : ccApiSigValidation ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-4 rounded-md bg-green-500/10 border border-green-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Valid</div>
                          <div className="text-3xl font-bold text-green-600">{ccApiSigValidation.summary.valid}</div>
                        </div>
                        <div className="p-4 rounded-md bg-red-500/10 border border-red-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Invalid</div>
                          <div className="text-3xl font-bold text-red-600">{ccApiSigValidation.summary.invalid}</div>
                        </div>
                        <div className="p-4 rounded-md bg-blue-500/10 border border-blue-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Not Found</div>
                          <div className="text-3xl font-bold text-blue-600">{ccApiSigValidation.summary.not_found}</div>
                        </div>
                        <div className="p-4 rounded-md bg-yellow-500/10 border border-yellow-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Warnings</div>
                          <div className="text-3xl font-bold text-yellow-600">{ccApiSigValidation.summary.warnings}</div>
                        </div>
                      </div>

                      <div className="p-4 rounded-md bg-muted">
                        <div className="text-sm font-medium mb-2">Accuracy Score</div>
                        <div className="text-4xl font-bold">
                          {(ccApiSigValidation.summary.accuracy_score * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground mt-2">
                          {ccApiSigValidation.summary.total_signatures} total signatures validated
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-semibold mb-3">Validation Details</h4>
                        <div className="space-y-2">
                          {ccApiSigValidation.validations.map((v, idx) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-md border ${
                                v.status === 'valid'
                                  ? 'bg-green-500/5 border-green-500/20'
                                  : v.status === 'invalid'
                                    ? 'bg-red-500/5 border-red-500/20'
                                    : v.status === 'not_found'
                                      ? 'bg-blue-500/5 border-blue-500/20'
                                      : 'bg-gray-500/5 border-gray-500/20'
                              }`}
                            >
                              <div className="flex items-start justify-between mb-2">
                                <div className="font-mono text-sm font-semibold">{v.function}</div>
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    v.status === 'valid'
                                      ? 'bg-green-500/20 text-green-700'
                                      : v.status === 'invalid'
                                        ? 'bg-red-500/20 text-red-700'
                                        : v.status === 'not_found'
                                          ? 'bg-blue-500/20 text-blue-700'
                                          : 'bg-gray-500/20 text-gray-700'
                                  }`}
                                >
                                  {v.status.replace('_', ' ')}
                                </span>
                              </div>
                              <div className="text-xs mb-1">
                                Confidence: <span className="font-semibold">{(v.confidence * 100).toFixed(0)}%</span>
                              </div>
                              {v.issues.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-border/50">
                                  <div className="text-xs font-medium mb-2">Issues:</div>
                                  <div className="space-y-1">
                                    {v.issues.map((issue, issueIdx) => (
                                      <div
                                        key={issueIdx}
                                        className={`text-xs p-2 rounded border-l-4 ${
                                          issue.severity === 'critical'
                                            ? 'bg-red-50 border-red-500 text-red-700'
                                            : issue.severity === 'warning'
                                              ? 'bg-yellow-50 border-yellow-500 text-yellow-700'
                                              : 'bg-blue-50 border-blue-300 text-blue-700'
                                        }`}
                                      >
                                        <div className="font-medium">{issue.type.replace(/_/g, ' ')}</div>
                                        <div className="mt-0.5">{issue.message}</div>
                                        {issue.suggested_fix && (
                                          <div className="mt-1 italic">Fix: {issue.suggested_fix}</div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No CC API signature validation data available
                    </p>
                  )}
                </TabPanel>

                {/* CC Code Examples Tab */}
                <TabPanel value="cc-code-ex" activeTab={activeTab}>
                  {loading ? (
                    <div className="text-sm text-muted-foreground">Loading...</div>
                  ) : ccCodeExValidation ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-4 gap-3">
                        <div className="p-4 rounded-md bg-green-500/10 border border-green-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Successful</div>
                          <div className="text-3xl font-bold text-green-600">{ccCodeExValidation.successful}</div>
                        </div>
                        <div className="p-4 rounded-md bg-red-500/10 border border-red-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Doc Errors</div>
                          <div className="text-3xl font-bold text-red-600">
                            {ccCodeExValidation.results.filter(r => r.status === 'failure' && r.severity === 'error').length}
                          </div>
                        </div>
                        <div className="p-4 rounded-md bg-amber-500/10 border border-amber-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Warnings</div>
                          <div className="text-3xl font-bold text-amber-600">
                            {ccCodeExValidation.results.filter(r => r.status === 'failure' && r.severity === 'warning').length}
                          </div>
                        </div>
                        <div className="p-4 rounded-md bg-gray-500/10 border border-gray-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Skipped</div>
                          <div className="text-3xl font-bold text-gray-600">{ccCodeExValidation.skipped}</div>
                        </div>
                      </div>

                      <div className="p-4 rounded-md bg-muted">
                        <div className="text-sm font-medium mb-2">Total Examples</div>
                        <div className="text-4xl font-bold">{ccCodeExValidation.total_examples}</div>
                        <div className="text-xs text-muted-foreground mt-2">
                          Success Rate: {ccCodeExValidation.total_examples > 0
                            ? ((ccCodeExValidation.successful / ccCodeExValidation.total_examples) * 100).toFixed(1)
                            : 0}%
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-semibold mb-3">Example Results</h4>
                        <div className="space-y-2">
                          {ccCodeExValidation.results.map((result, idx) => {
                            // Determine colors based on severity for failures
                            const getBgBorderClass = () => {
                              if (result.status === 'success') return 'bg-green-500/5 border-green-500/20';
                              if (result.status === 'skipped') return 'bg-gray-500/5 border-gray-500/20';
                              if (result.severity === 'error') return 'bg-red-500/5 border-red-500/20';
                              if (result.severity === 'warning') return 'bg-amber-500/5 border-amber-500/20';
                              if (result.severity === 'info') return 'bg-blue-500/5 border-blue-500/20';
                              return 'bg-red-500/5 border-red-500/20'; // default for failures
                            };

                            return (
                              <div
                                key={idx}
                                data-result-index={result.example_index}
                                className={`p-3 rounded-md border ${getBgBorderClass()}`}
                              >
                                <div className="flex items-start justify-between mb-2 gap-2">
                                  <div className="font-mono text-sm font-semibold">Example {result.example_index}</div>
                                  <div className="flex items-center gap-2 flex-shrink-0">
                                    <span
                                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                                        result.status === 'success'
                                          ? 'bg-green-500/20 text-green-700'
                                          : result.status === 'failure'
                                            ? 'bg-red-500/20 text-red-700'
                                            : 'bg-gray-500/20 text-gray-700'
                                      }`}
                                    >
                                      {result.status}
                                    </span>
                                    {/* Severity Badge */}
                                    {result.status === 'failure' && result.severity && (
                                      <span className={`severity-badge severity-badge-${result.severity}`}>
                                        {result.severity === 'error' && '⚠️'}
                                        {result.severity === 'warning' && '⚡'}
                                        {result.severity === 'info' && 'ℹ️'}
                                        {result.severity}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              <div className="text-xs text-muted-foreground mb-2">
                                Context: {result.context} (Line {result.line})
                              </div>
                              {result.error_message && (
                                <div className={`mt-2 p-2 rounded text-xs ${
                                  result.severity === 'error'
                                    ? 'bg-red-50 border border-red-200 text-red-700 dark:bg-red-950/50 dark:border-red-800 dark:text-red-100'
                                    : result.severity === 'warning'
                                    ? 'bg-amber-50 border border-amber-200 text-amber-700 dark:bg-amber-950/50 dark:border-amber-800 dark:text-amber-100'
                                    : result.severity === 'info'
                                    ? 'bg-blue-50 border border-blue-200 text-blue-700 dark:bg-blue-950/50 dark:border-blue-800 dark:text-blue-100'
                                    : 'bg-red-50 border border-red-200 text-red-700 dark:bg-red-950/50 dark:border-red-800 dark:text-red-100'
                                }`}>
                                  <div className="font-medium">
                                    {result.severity === 'error' && '⚠️ Documentation Error:'}
                                    {result.severity === 'warning' && '⚡ Environment Issue:'}
                                    {result.severity === 'info' && 'ℹ️ Info:'}
                                    {!result.severity && 'Error:'}
                                  </div>
                                  <div className="mt-1">{result.error_message}</div>
                                </div>
                              )}
                              {result.suggestions && (
                                <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                                  <div className="font-medium">Suggestions:</div>
                                  <div className="mt-1">{result.suggestions}</div>
                                </div>
                              )}
                              {result.execution_output && (
                                <div className="mt-2">
                                  <div className="text-xs font-medium mb-1">Output:</div>
                                  <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-32">
                                    {result.execution_output}
                                  </pre>
                                </div>
                              )}
                            </div>
                          );
                        })}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No CC code example validation data available
                    </p>
                  )}
                </TabPanel>

                {/* CC Clarity Tab */}
                <TabPanel value="cc-clarity" activeTab={activeTab}>
                  {loading ? (
                    <div className="text-sm text-muted-foreground">Loading...</div>
                  ) : ccClarityValidation ? (
                    <div className="space-y-4">
                      {/* Overall Clarity Score */}
                      <div className={`p-6 rounded-lg border ${
                        ccClarityValidation.clarity_score.overall_score >= 8
                          ? 'bg-green-500/10 border-green-500/20'
                          : ccClarityValidation.clarity_score.overall_score >= 6
                            ? 'bg-yellow-500/10 border-yellow-500/20'
                            : 'bg-red-500/10 border-red-500/20'
                      }`}>
                        <div className="flex items-start justify-between mb-2">
                          <div className="text-sm font-medium">Overall Clarity Score</div>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            ccClarityValidation.summary.overall_quality_rating === 'excellent'
                              ? 'bg-green-500/20 text-green-700'
                              : ccClarityValidation.summary.overall_quality_rating === 'good'
                                ? 'bg-yellow-500/20 text-yellow-700'
                                : ccClarityValidation.summary.overall_quality_rating === 'needs_improvement'
                                  ? 'bg-orange-500/20 text-orange-700'
                                  : 'bg-red-500/20 text-red-700'
                          }`}>
                            {ccClarityValidation.summary.overall_quality_rating.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <div className={`text-5xl font-bold ${
                          ccClarityValidation.clarity_score.overall_score >= 8
                            ? 'text-green-600'
                            : ccClarityValidation.clarity_score.overall_score >= 6
                              ? 'text-yellow-600'
                              : 'text-red-600'
                        }`}>
                          {ccClarityValidation.clarity_score.overall_score.toFixed(1)}/10
                        </div>
                        {ccClarityValidation.clarity_score.scoring_rationale && (
                          <div className="text-sm mt-3 opacity-90">
                            {ccClarityValidation.clarity_score.scoring_rationale}
                          </div>
                        )}
                      </div>

                      {/* Dimension Scores */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 rounded-md bg-muted">
                          <div className="text-xs text-muted-foreground mb-1">Instruction Clarity</div>
                          <div className="text-2xl font-bold">{ccClarityValidation.clarity_score.instruction_clarity.toFixed(1)}</div>
                        </div>
                        <div className="p-3 rounded-md bg-muted">
                          <div className="text-xs text-muted-foreground mb-1">Logical Flow</div>
                          <div className="text-2xl font-bold">{ccClarityValidation.clarity_score.logical_flow.toFixed(1)}</div>
                        </div>
                        <div className="p-3 rounded-md bg-muted">
                          <div className="text-xs text-muted-foreground mb-1">Completeness</div>
                          <div className="text-2xl font-bold">{ccClarityValidation.clarity_score.completeness.toFixed(1)}</div>
                        </div>
                        <div className="p-3 rounded-md bg-muted">
                          <div className="text-xs text-muted-foreground mb-1">Consistency</div>
                          <div className="text-2xl font-bold">{ccClarityValidation.clarity_score.consistency.toFixed(1)}</div>
                        </div>
                        <div className="p-3 rounded-md bg-muted col-span-2">
                          <div className="text-xs text-muted-foreground mb-1">Prerequisite Coverage</div>
                          <div className="text-2xl font-bold">{ccClarityValidation.clarity_score.prerequisite_coverage.toFixed(1)}</div>
                        </div>
                      </div>

                      {/* Summary Stats */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className="p-4 rounded-md bg-red-500/10 border border-red-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Critical Issues</div>
                          <div className="text-3xl font-bold text-red-600">
                            {ccClarityValidation.summary.critical_clarity_issues + ccClarityValidation.summary.critical_structural_issues}
                          </div>
                        </div>
                        <div className="p-4 rounded-md bg-yellow-500/10 border border-yellow-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Warnings</div>
                          <div className="text-3xl font-bold text-yellow-600">
                            {ccClarityValidation.summary.warning_clarity_issues}
                          </div>
                        </div>
                        <div className="p-4 rounded-md bg-blue-500/10 border border-blue-500/20">
                          <div className="text-xs text-muted-foreground mb-1">Info</div>
                          <div className="text-3xl font-bold text-blue-600">
                            {ccClarityValidation.summary.info_clarity_issues}
                          </div>
                        </div>
                      </div>

                      {/* Clarity Issues */}
                      {ccClarityValidation.clarity_issues.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold mb-3">Clarity Issues</h4>
                          <div className="space-y-2">
                            {ccClarityValidation.clarity_issues.map((issue, idx) => (
                              <div
                                key={idx}
                                className={`p-3 rounded-md border-l-4 ${
                                  issue.severity === 'critical'
                                    ? 'bg-red-50 border-red-500'
                                    : issue.severity === 'warning'
                                      ? 'bg-yellow-50 border-yellow-500'
                                      : 'bg-blue-50 border-blue-300'
                                }`}
                              >
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                      issue.severity === 'critical'
                                        ? 'bg-red-500/20 text-red-700'
                                        : issue.severity === 'warning'
                                          ? 'bg-yellow-500/20 text-yellow-700'
                                          : 'bg-blue-500/20 text-blue-700'
                                    }`}>
                                      {issue.severity}
                                    </span>
                                    <span className="text-xs font-medium">
                                      {issue.type.replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    Line {issue.line} | {issue.section}
                                    {issue.step_number && ` | Step ${issue.step_number}`}
                                  </div>
                                </div>
                                <div className="text-sm mb-2">{issue.message}</div>
                                {issue.context_quote && (
                                  <div className="text-xs bg-white/50 p-2 rounded italic mb-2">
                                    "{issue.context_quote}"
                                  </div>
                                )}
                                {issue.affected_code && (
                                  <pre className="text-xs bg-white/50 p-2 rounded mb-2 overflow-x-auto">
                                    <code>{issue.affected_code}</code>
                                  </pre>
                                )}
                                {issue.suggested_fix && (
                                  <div className="text-xs mt-2 pt-2 border-t border-border/50">
                                    <span className="font-medium">💡 Suggested Fix:</span> {issue.suggested_fix}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Structural Issues */}
                      {ccClarityValidation.structural_issues.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold mb-3">Structural Issues</h4>
                          <div className="space-y-2">
                            {ccClarityValidation.structural_issues.map((issue, idx) => (
                              <div
                                key={idx}
                                className={`p-3 rounded-md border-l-4 ${
                                  issue.severity === 'critical'
                                    ? 'bg-red-50 border-red-500'
                                    : issue.severity === 'warning'
                                      ? 'bg-yellow-50 border-yellow-500'
                                      : 'bg-blue-50 border-blue-300'
                                }`}
                              >
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                      issue.severity === 'critical'
                                        ? 'bg-red-500/20 text-red-700'
                                        : issue.severity === 'warning'
                                          ? 'bg-yellow-500/20 text-yellow-700'
                                          : 'bg-blue-500/20 text-blue-700'
                                    }`}>
                                      {issue.severity}
                                    </span>
                                    <span className="text-xs font-medium">
                                      {issue.type.replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                </div>
                                <div className="text-xs text-muted-foreground mb-2">{issue.location}</div>
                                <div className="text-sm mb-2">{issue.message}</div>
                                {issue.suggested_fix && (
                                  <div className="text-xs mt-2 pt-2 border-t border-border/50">
                                    <span className="font-medium">💡 Suggested Fix:</span> {issue.suggested_fix}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Technical Accessibility */}
                      {(ccClarityValidation.technical_accessibility.broken_links.length > 0 ||
                        ccClarityValidation.technical_accessibility.missing_alt_text.length > 0 ||
                        ccClarityValidation.technical_accessibility.code_blocks_without_language.length > 0) && (
                        <div>
                          <h4 className="text-sm font-semibold mb-3">Technical Accessibility</h4>
                          <div className="space-y-3">
                            {ccClarityValidation.technical_accessibility.broken_links.length > 0 && (
                              <div className="p-3 rounded-md bg-red-50 border border-red-200">
                                <div className="text-xs font-medium mb-2 text-red-700">
                                  🔗 Broken Links ({ccClarityValidation.technical_accessibility.broken_links.length})
                                </div>
                                {ccClarityValidation.technical_accessibility.broken_links.map((link, idx) => (
                                  <div key={idx} className="text-xs mb-1">
                                    <span className="font-mono">{link.url}</span> (Line {link.line}): {link.error}
                                  </div>
                                ))}
                              </div>
                            )}
                            {ccClarityValidation.technical_accessibility.missing_alt_text.length > 0 && (
                              <div className="p-3 rounded-md bg-yellow-50 border border-yellow-200">
                                <div className="text-xs font-medium mb-2 text-yellow-700">
                                  🖼️ Missing Alt Text ({ccClarityValidation.technical_accessibility.missing_alt_text.length})
                                </div>
                                {ccClarityValidation.technical_accessibility.missing_alt_text.map((img, idx) => (
                                  <div key={idx} className="text-xs mb-1">
                                    {img.image_path} (Line {img.line})
                                  </div>
                                ))}
                              </div>
                            )}
                            {ccClarityValidation.technical_accessibility.code_blocks_without_language.length > 0 && (
                              <div className="p-3 rounded-md bg-blue-50 border border-blue-200">
                                <div className="text-xs font-medium mb-2 text-blue-700">
                                  💻 Code Blocks Without Language ({ccClarityValidation.technical_accessibility.code_blocks_without_language.length})
                                </div>
                                {ccClarityValidation.technical_accessibility.code_blocks_without_language.map((block, idx) => (
                                  <div key={idx} className="text-xs mb-1">
                                    Line {block.line}: <span className="font-mono">{block.content_preview}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No CC clarity validation data available
                    </p>
                  )}
                </TabPanel>
              </Tabs>
            </div>
          </div>
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && <Settings onClose={() => setShowSettings(false)} />}
    </div>
  );
}

export default App;
