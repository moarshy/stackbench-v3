import type {
  ExtractionOutput,
  ValidationOutput,
  CCAPISignatureValidationOutput,
  CCCodeExampleValidationOutput,
  DSpyAPISignatureValidationOutput,
  DSpyCodeExampleValidationOutput
} from '../types';

interface RepoConfig {
  repoPath: string;
  docsPath: string;
  extractionOutputPath: string;
  validationOutputPath: string;
  ccApiSignatureOutputPath: string;
  ccCodeExampleOutputPath: string;
  dspyApiSignatureOutputPath: string;
  dspyCodeExampleOutputPath: string;
}

export class APIService {
  private config: RepoConfig;

  constructor(config: RepoConfig) {
    this.config = config;
  }

  /**
   * Get list of documentation files
   */
  async getDocumentationFiles(): Promise<string[]> {
    // For now, we'll scan the extraction output directory
    // since each extraction file corresponds to a documentation file
    try {
      const response = await fetch(`/api/files?path=${encodeURIComponent(this.config.extractionOutputPath)}`);
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
      // Return mock data if API fails
      return ['pydantic.md', 'python.md', 'pandas_and_pyarrow.md', 'datafusion.md', 'duckdb.md', 'polars_arrow.md'];
    }
  }

  /**
   * Get documentation content
   */
  async getDocumentationContent(docName: string): Promise<string> {
    try {
      const docPath = `${this.config.docsPath}/${docName}`;
      const response = await fetch(`/api/file?path=${encodeURIComponent(docPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch documentation content');
      }
      return await response.text();
    } catch (error) {
      console.error('Error fetching documentation content:', error);
      return `# ${docName}\n\nUnable to load documentation content.`;
    }
  }

  /**
   * Get extraction output for a documentation file
   */
  async getExtractionOutput(docName: string): Promise<ExtractionOutput | null> {
    try {
      // Convert doc name to extraction file name (e.g., "pydantic.md" -> "pydantic_analysis.json")
      const extractionFile = docName.replace('.md', '_analysis.json');
      const extractionPath = `${this.config.extractionOutputPath}/${extractionFile}`;

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
   * Get validation output for a documentation file (AST validation)
   */
  async getValidationOutput(docName: string): Promise<ValidationOutput | null> {
    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_analysis_ast_validation.json")
      const validationFile = docName.replace('.md', '_analysis_ast_validation.json');
      const validationPath = `${this.config.validationOutputPath}/${validationFile}`;

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch validation output');
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
    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_analysis_validation.json")
      const validationFile = docName.replace('.md', '_analysis_validation.json');
      const validationPath = `${this.config.ccApiSignatureOutputPath}/${validationFile}`;

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch CC API signature validation');
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
    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_validation.json")
      const validationFile = docName.replace('.md', '_validation.json');
      const validationPath = `${this.config.ccCodeExampleOutputPath}/${validationFile}`;

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch CC code example validation');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching CC code example validation:', error);
      return null;
    }
  }

  /**
   * Get DSpy API signature validation output
   */
  async getDSpyApiSignatureValidation(docName: string): Promise<DSpyAPISignatureValidationOutput | null> {
    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_analysis_validation.json")
      const validationFile = docName.replace('.md', '_analysis_validation.json');
      const validationPath = `${this.config.dspyApiSignatureOutputPath}/${validationFile}`;

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch DSpy API signature validation');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching DSpy API signature validation:', error);
      return null;
    }
  }

  /**
   * Get DSpy code example validation output
   */
  async getDSpyCodeExampleValidation(docName: string): Promise<DSpyCodeExampleValidationOutput | null> {
    try {
      // Convert doc name to validation file name (e.g., "pydantic.md" -> "pydantic_analysis_validation.json")
      const validationFile = docName.replace('.md', '_analysis_validation.json');
      const validationPath = `${this.config.dspyCodeExampleOutputPath}/${validationFile}`;

      const response = await fetch(`/api/file?path=${encodeURIComponent(validationPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch DSpy code example validation');
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
}

// Default configuration
export const defaultConfig: RepoConfig = {
  repoPath: '/Users/arshath/play/naptha/stackbench-v2',
  docsPath: '/Users/arshath/play/naptha/stackbench-v2/data/0e8f2207-c510-449b-8478-6a54620aad56/repo/docs/src/python',
  extractionOutputPath: '/Users/arshath/play/naptha/stackbench-v2/cc-agents/extraction_output',
  validationOutputPath: '/Users/arshath/play/naptha/stackbench-v2/cc-agents/ast_validation_output',
  ccApiSignatureOutputPath: '/Users/arshath/play/naptha/stackbench-v2/cc-agents/cc_api_signature_validation_output',
  ccCodeExampleOutputPath: '/Users/arshath/play/naptha/stackbench-v2/cc-agents/cc_code_example_validation_output',
  dspyApiSignatureOutputPath: '/Users/arshath/play/naptha/stackbench-v2/cc-agents/dspy_api_signature_validation_output',
  dspyCodeExampleOutputPath: '/Users/arshath/play/naptha/stackbench-v2/cc-agents/dspy_code_example_validation_output',
};

// Create default API service instance
export const apiService = new APIService(defaultConfig);
