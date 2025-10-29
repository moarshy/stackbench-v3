import type {
  ExtractionOutput,
  ValidationOutput,
  CCAPISignatureValidationOutput,
  CCCodeExampleValidationOutput,
  CCClarityValidationOutput,
  DSpyAPISignatureValidationOutput,
  DSpyCodeExampleValidationOutput,
  WalkthroughData,
  WalkthroughExport,
  WalkthroughSession,
  APICompletenessOutput
} from '../types';

interface RepoConfig {
  baseDataDir: string; // Base directory for all runs (e.g., "./data")
}

export class APIService {
  private config: RepoConfig;
  private currentRunId: string | null = null;

  constructor(config: RepoConfig) {
    this.config = config;
  }

  /**
   * Set the current run ID to load data from
   */
  setRunId(runId: string | null) {
    this.currentRunId = runId;
  }

  /**
   * Get the current run ID
   */
  getRunId(): string | null {
    return this.currentRunId;
  }

  /**
   * Build path for current run
   */
  private getRunPath(subPath: string = ''): string {
    if (!this.currentRunId) {
      throw new Error('No run selected');
    }
    return `${this.config.baseDataDir}/${this.currentRunId}${subPath ? '/' + subPath : ''}`;
  }

  /**
   * Get list of documentation files
   */
  async getDocumentationFiles(): Promise<string[]> {
    if (!this.currentRunId) {
      return [];
    }

    // Scan the extraction output directory for the current run
    // since each extraction file corresponds to a documentation file
    try {
      const extractionPath = this.getRunPath('results/extraction');
      const response = await fetch(`/api/files?path=${encodeURIComponent(extractionPath)}&type=files`);
      if (!response.ok) {
        throw new Error('Failed to fetch documentation files');
      }
      const files: string[] = await response.json();

      // Extract doc names from extraction files (e.g., "pydantic_analysis.json" -> "pydantic.md")
      return files
        .filter(f => f.endsWith('_analysis.json'))
        .map(f => f.replace('_analysis.json', '.md'));
    } catch (error) {
      console.error('Error fetching documentation files:', error);
      return [];
    }
  }

  /**
   * Get documentation content
   */
  async getDocumentationContent(docName: string): Promise<string> {
    if (!this.currentRunId) {
      return `# ${docName}\n\nNo run selected.`;
    }

    try {
      // First, try to determine the doc path from extraction metadata
      const extractionFile = docName.replace('.md', '_analysis.json');
      const extractionPath = this.getRunPath(`results/extraction/${extractionFile}`);

      const extractionResponse = await fetch(`/api/file?path=${encodeURIComponent(extractionPath)}`);
      if (extractionResponse.ok) {
        const extraction = await extractionResponse.json();
        // The extraction file contains the original page path
        if (extraction.page) {
          // Build full path from repository
          const docPath = this.getRunPath(`repository/${extraction.page}`);
          const docResponse = await fetch(`/api/file?path=${encodeURIComponent(docPath)}`);
          if (docResponse.ok) {
            return await docResponse.text();
          }
        }
      }

      // Fallback: try common doc locations
      const commonPaths = [
        `repository/docs/${docName}`,
        `repository/docs/src/${docName}`,
        `repository/docs/src/python/${docName}`,
        `repository/${docName}`,
      ];

      for (const subPath of commonPaths) {
        const docPath = this.getRunPath(subPath);
        const response = await fetch(`/api/file?path=${encodeURIComponent(docPath)}`);
        if (response.ok) {
          return await response.text();
        }
      }

      throw new Error('Documentation file not found');
    } catch (error) {
      console.error('Error fetching documentation content:', error);
      return `# ${docName}\n\nUnable to load documentation content.`;
    }
  }

  /**
   * Get extraction output for a documentation file
   */
  async getExtractionOutput(docName: string): Promise<ExtractionOutput | null> {
    if (!this.currentRunId) {
      return null;
    }

    try {
      // Convert doc name to extraction file name (e.g., "pydantic.md" -> "pydantic_analysis.json")
      const extractionFile = docName.replace('.md', '_analysis.json');
      const extractionPath = this.getRunPath(`results/extraction/${extractionFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(extractionPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch extraction output');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching extraction output:', error);
      return null;
    }
  }

  /**
   * Get validation output for a documentation file (AST validation - legacy)
   */
  async getValidationOutput(docName: string): Promise<ValidationOutput | null> {
    // This is legacy AST validation - may not exist in new runs
    if (!this.currentRunId) {
      return null;
    }

    try {
      const validationFile = docName.replace('.md', '_analysis_ast_validation.json');
      const validationPath = this.getRunPath(`results/api_validation/${validationFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        return null; // Not an error, just not available
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching validation output:', error);
      return null;
    }
  }

  /**
   * Get Claude Code API signature validation output
   */
  async getCCApiSignatureValidation(docName: string): Promise<CCAPISignatureValidationOutput | null> {
    if (!this.currentRunId) {
      return null;
    }

    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_analysis_validation.json")
      const validationFile = docName.replace('.md', '_analysis_validation.json');
      const validationPath = this.getRunPath(`results/api_validation/${validationFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching CC API signature validation:', error);
      return null;
    }
  }

  /**
   * Get Claude Code code example validation output
   */
  async getCCCodeExampleValidation(docName: string): Promise<CCCodeExampleValidationOutput | null> {
    if (!this.currentRunId) {
      return null;
    }

    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_validation.json")
      const validationFile = docName.replace('.md', '_validation.json');
      const validationPath = this.getRunPath(`results/code_validation/${validationFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching CC code example validation:', error);
      return null;
    }
  }

  /**
   * Get Claude Code clarity validation output
   */
  async getCCClarityValidation(docName: string): Promise<CCClarityValidationOutput | null> {
    if (!this.currentRunId) {
      return null;
    }

    try {
      // Convert doc name to clarity file name (e.g., "pydantic.md" -> "pydantic_clarity.json")
      const clarityFile = docName.replace('.md', '_clarity.json');
      const clarityPath = this.getRunPath(`results/clarity_validation/${clarityFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(clarityPath)}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching CC clarity validation:', error);
      return null;
    }
  }

  /**
   * Get DSpy API signature validation output (legacy - may not exist)
   */
  async getDSpyApiSignatureValidation(docName: string): Promise<DSpyAPISignatureValidationOutput | null> {
    // DSpy validation may not be part of new pipeline
    if (!this.currentRunId) {
      return null;
    }

    try {
      const validationFile = docName.replace('.md', '_analysis_validation.json');
      const validationPath = this.getRunPath(`results/dspy_api_validation/${validationFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching DSpy API signature validation:', error);
      return null;
    }
  }

  /**
   * Get DSpy code example validation output (legacy - may not exist)
   */
  async getDSpyCodeExampleValidation(docName: string): Promise<DSpyCodeExampleValidationOutput | null> {
    // DSpy validation may not be part of new pipeline
    if (!this.currentRunId) {
      return null;
    }

    try {
      const validationFile = docName.replace('.md', '_analysis_validation.json');
      const validationPath = this.getRunPath(`results/dspy_code_validation/${validationFile}`);

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching DSpy code example validation:', error);
      return null;
    }
  }

  /**
   * Get list of walkthroughs for the current run
   */
  async getWalkthroughs(): Promise<string[]> {
    if (!this.currentRunId) {
      return [];
    }

    try {
      const walkthroughsPath = this.getRunPath('walkthroughs');
      const response = await fetch(`/api/files?path=${encodeURIComponent(walkthroughsPath)}&type=dirs`);
      if (!response.ok) {
        return [];
      }
      const folders: string[] = await response.json();

      // Return walkthrough IDs (folder names starting with wt_)
      return folders.filter(f => f.startsWith('wt_'));
    } catch (error) {
      console.error('Error fetching walkthroughs:', error);
      return [];
    }
  }

  /**
   * Get walkthrough data (main walkthrough + session if exists)
   */
  async getWalkthroughData(walkthroughId: string): Promise<WalkthroughData | null> {
    if (!this.currentRunId) {
      return null;
    }

    try {
      // Fetch main walkthrough file
      const walkthroughPath = this.getRunPath(`walkthroughs/${walkthroughId}/${walkthroughId}.json`);
      const walkthroughResponse = await fetch(`/api/file?path=${encodeURIComponent(walkthroughPath)}`);

      if (!walkthroughResponse.ok) {
        return null;
      }

      const walkthrough: WalkthroughExport = await walkthroughResponse.json();

      // Try to fetch session file (audit results)
      let session: WalkthroughSession | null = null;
      try {
        const sessionPath = this.getRunPath(`walkthroughs/${walkthroughId}/${walkthroughId}_session.json`);
        const sessionResponse = await fetch(`/api/file?path=${encodeURIComponent(sessionPath)}`);

        if (sessionResponse.ok) {
          session = await sessionResponse.json();
        }
      } catch (sessionError) {
        // Session file doesn't exist - that's OK, walkthrough might not have been audited
        console.log('No session file found for', walkthroughId);
      }

      return {
        walkthrough,
        session
      };
    } catch (error) {
      console.error('Error fetching walkthrough data:', error);
      return null;
    }
  }

  /**
   * Get API completeness analysis (run-level, not per-document)
   */
  async getAPICompleteness(): Promise<APICompletenessOutput | null> {
    if (!this.currentRunId) {
      return null;
    }

    try {
      const completenessPath = this.getRunPath('results/api_completeness/completeness_analysis.json');
      const response = await fetch(`/api/file?path=${encodeURIComponent(completenessPath)}`);

      if (!response.ok) {
        return null;
      }

      const data = await response.json();

      // Backwards compatibility: handle legacy format with "summary" instead of "coverage_summary"
      if (data && data.summary && !data.coverage_summary) {
        data.coverage_summary = data.summary;

        // Extract top-level fields from summary
        if (!data.library) data.library = data.summary.library;
        if (!data.version) data.version = data.summary.version;
        if (!data.analyzed_at) data.analyzed_at = data.summary.generated_at;

        delete data.summary;
      }

      // Calculate missing fields from documented_apis if needed
      if (data && data.documented_apis && data.coverage_summary) {
        const documentedApis = Array.isArray(data.documented_apis) ? data.documented_apis : [];

        // Calculate with_examples if missing
        if (data.coverage_summary.with_examples === undefined) {
          data.coverage_summary.with_examples = documentedApis.filter(api => api.has_examples).length;
        }

        // Calculate with_dedicated_sections (tier 3) if missing
        if (data.coverage_summary.with_dedicated_sections === undefined) {
          data.coverage_summary.with_dedicated_sections = documentedApis.filter(api => api.coverage_tier === 3).length;
        }

        // Calculate percentages if missing
        const total = data.coverage_summary.total_apis || 0;
        if (total > 0) {
          if (data.coverage_summary.example_coverage_percentage === undefined) {
            data.coverage_summary.example_coverage_percentage = (data.coverage_summary.with_examples / total) * 100;
          }
          if (data.coverage_summary.complete_coverage_percentage === undefined) {
            data.coverage_summary.complete_coverage_percentage = (data.coverage_summary.with_dedicated_sections / total) * 100;
          }
        }
      }

      // Merge documented_apis and undocumented_apis into api_details for frontend compatibility
      if (data && !data.api_details) {
        const undocumentedAPIs = [];

        // undocumented_apis is an object with priority categories, flatten it
        if (data.undocumented_apis) {
          if (Array.isArray(data.undocumented_apis.high_priority)) {
            undocumentedAPIs.push(...data.undocumented_apis.high_priority);
          }
          if (Array.isArray(data.undocumented_apis.medium_priority)) {
            undocumentedAPIs.push(...data.undocumented_apis.medium_priority);
          }
          if (Array.isArray(data.undocumented_apis.low_priority)) {
            undocumentedAPIs.push(...data.undocumented_apis.low_priority);
          }
        }

        // Add missing fields to undocumented APIs to match the structure
        const normalizedUndocumented = undocumentedAPIs.map(api => ({
          ...api,
          coverage_tier: 0,
          reference_count: 0,
          documentation_references: [],
          documented_in: [],
          has_examples: false,
          has_dedicated_section: false
        }));

        data.api_details = [
          ...(data.documented_apis || []),
          ...normalizedUndocumented
        ];
      }

      return data;
    } catch (error) {
      console.error('Error fetching API completeness data:', error);
      return null;
    }
  }

  /**
   * Update repository configuration and persist to localStorage
   */
  updateConfig(newConfig: Partial<RepoConfig>) {
    this.config = { ...this.config, ...newConfig };

    // Persist baseDataDir to localStorage
    if (newConfig.baseDataDir) {
      localStorage.setItem('stackbench_base_data_dir', newConfig.baseDataDir);
    }
  }

  /**
   * Get current configuration
   */
  getConfig(): RepoConfig {
    return { ...this.config };
  }

  /**
   * Get base data directory
   */
  getBaseDataDir(): string {
    return this.config.baseDataDir;
  }
}

/**
 * Fetch base data directory from backend API
 * The backend knows the absolute path to the project directory
 */
async function fetchBaseDataDirFromBackend(): Promise<string> {
  try {
    const response = await fetch('/api/config');
    if (response.ok) {
      const config = await response.json();
      return config.baseDataDir;
    }
  } catch (error) {
    console.error('Failed to fetch config from backend:', error);
  }
  return '';
}

/**
 * Infer base data directory from localStorage or fetch from backend
 *
 * Note: The backend API requires absolute paths to access files.
 * We fetch the path from the backend which knows where it's running from.
 */
function inferBaseDataDir(): string {
  // Check localStorage first (user preference overrides)
  const storedPath = localStorage.getItem('stackbench_base_data_dir');
  if (storedPath) {
    return storedPath;
  }

  // Try fetching from backend (will be set asynchronously)
  // For now, return empty string and it will be updated when the app initializes
  return '';
}

// Default configuration - will be updated after fetching from backend
export const defaultConfig: RepoConfig = {
  baseDataDir: inferBaseDataDir(),
};

// Create default API service instance
export const apiService = new APIService(defaultConfig);

// Initialize config from backend on app startup
// This Promise can be awaited by the app before rendering
export const configInitialized = fetchBaseDataDirFromBackend().then(baseDataDir => {
  if (baseDataDir && !localStorage.getItem('stackbench_base_data_dir')) {
    // Update config with backend path if user hasn't set a custom path
    apiService.updateConfig({ baseDataDir });
    console.log('✅ Base data directory auto-detected:', baseDataDir);
  }
  return baseDataDir;
});
