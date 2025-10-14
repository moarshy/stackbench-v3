import type {
  ExtractionOutput,
  ValidationOutput,
  CCAPISignatureValidationOutput,
  CCCodeExampleValidationOutput,
  DSpyAPISignatureValidationOutput,
  DSpyCodeExampleValidationOutput
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
      const response = await fetch(`/api/files?path=${encodeURIComponent(extractionPath)}`);
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
   * Update repository configuration
   */
  updateConfig(newConfig: Partial<RepoConfig>) {
    this.config = { ...this.config, ...newConfig };
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

// Default configuration - points to stackbench-v3 data directory
export const defaultConfig: RepoConfig = {
  baseDataDir: '/Users/arshath/play/naptha/stackbench-v2/stackbench-v3/data',
};

// Create default API service instance
export const apiService = new APIService(defaultConfig);
