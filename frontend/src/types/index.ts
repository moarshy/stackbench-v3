// Extraction Output Types
export interface APISignature {
  library: string;
  function: string;
  method_chain: string | null;
  params: string[];
  param_types: Record<string, string>;
  defaults: Record<string, any>;
  imports: string;
  line: number;
  context: string;
  raw_code: string;

  // NEW FIELDS - Better association
  section_hierarchy?: string[];
  markdown_anchor?: string | null;
  code_block_index?: number;
}

export interface CodeExample {
  library: string;
  language: string;
  code: string;
  imports: string;
  has_main: boolean;
  is_executable: boolean;
  line: number;
  context: string;
  dependencies: string[];

  // NEW FIELDS - Better association
  section_hierarchy?: string[];
  markdown_anchor?: string | null;
  code_block_index?: number;
  snippet_source?: string | null;
}

export interface ExtractionOutput {
  page: string;
  library: string;
  version: string;
  language: string;
  signatures: APISignature[];
  examples: CodeExample[];
  processed_at: string;
  total_signatures: number;
  total_examples: number;
  warnings: string[];
  processing_time_ms: number;
}

// Validation Output Types
export interface ParameterMismatch {
  parameter_name: string;
  issue_type: "missing_in_docs" | "missing_in_code" | "type_mismatch" | "default_mismatch";
  severity: "critical" | "medium" | "low" | "info";
  doc_value: string | null;
  code_value: string | null;
  description: string;
}

export interface Parameter {
  name: string;
  type: string | null;
  default: string | null;
  required: boolean;
}

export interface CodeSignature {
  name: string;
  full_name: string;
  module: string;
  class_name: string | null;
  parameters: Parameter[];
  return_type: string | null;
  is_async: boolean;
}

export interface SignatureValidationResult {
  signature_id: string;
  function_name: string;
  library: string;
  status: "valid" | "partial_match" | "mismatch" | "not_found";
  match_confidence: number;
  doc_signature: APISignature;
  code_signature: CodeSignature | null;
  code_location: string | null;
  parameter_mismatches: ParameterMismatch[];
  issues: string[];
  suggested_fixes: string[];
}

export interface ValidationSummary {
  total_signatures: number;
  valid: number;
  partial_match: number;
  mismatch: number;
  not_found: number;
  accuracy_score: number;
}

export interface ValidationOutput {
  validation_id: string;
  validated_at: string;
  validation_method: string;
  extraction_file: string;
  repository_path: string;
  library: string;
  version: string;
  language: string;
  summary: ValidationSummary;
  validations: SignatureValidationResult[];
  processing_time_ms: number;
  total_files_parsed: number;
  total_code_signatures: number;
  warnings: string[];
}

// Combined view type
export interface DocView {
  docFile: string;
  extraction: ExtractionOutput | null;
  validation: ValidationOutput | null;
}

// ============================================================================
// Claude Code API Signature Validation Types
// ============================================================================

export interface CCDocumentedSignature {
  params: string[];
  param_types: Record<string, string>;
  defaults: Record<string, any>;
  imports: string;
  raw_code: string;
  line: number;
  context: string;
}

export interface CCActualSignature {
  params: string[];
  param_types: Record<string, string>;
  defaults: Record<string, any>;
  required_params: string[];
  optional_params: string[];
  return_type: string | null;
  is_async: boolean;
  is_method: boolean;
  verified_by: string;
}

export interface CCValidationIssue {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  suggested_fix: string | null;
}

export interface CCSignatureValidation {
  signature_id: string;
  function: string;
  method_chain: string | null;
  library: string;
  status: 'valid' | 'invalid' | 'not_found' | 'error';
  documented: CCDocumentedSignature;
  actual: CCActualSignature | null;
  issues: CCValidationIssue[];
  confidence: number;
}

export interface CCValidationSummary {
  total_signatures: number;
  valid: number;
  invalid: number;
  not_found: number;
  error: number;
  accuracy_score: number;
  critical_issues: number;
  warnings: number;
}

export interface CCEnvironmentInfo {
  library_installed: string;
  version_installed: string;
  version_requested: string;
  version_match: boolean;
  python_version: string;
  installation_output?: string;
}

export interface CCAPISignatureValidationOutput {
  validation_id: string;
  validated_at: string;
  source_file: string;
  document_page: string;
  library: string;
  version: string;
  language: string;
  summary: CCValidationSummary;
  validations: CCSignatureValidation[];
  environment: CCEnvironmentInfo;
  processing_time_ms: number;
  warnings: string[];
}

// ============================================================================
// Claude Code Code Example Validation Types
// ============================================================================

export interface CCExampleValidationResult {
  example_index: number;
  line: number;
  context: string;
  code: string;
  status: 'success' | 'failure' | 'skipped';
  severity?: 'error' | 'warning' | 'info' | null; // NEW: Severity classification (only for failures)
  error_message: string | null;
  suggestions: string | null;
  execution_output: string | null;
  depends_on_previous: boolean;

  // NEW FIELDS - Better dependency tracking
  depends_on_example_indices?: number[];
  actual_code_executed?: string | null;
}

export interface CCCodeExampleValidationOutput {
  page: string;
  library: string;
  version: string;
  language: string;
  validation_timestamp: string;
  results: CCExampleValidationResult[];
  total_examples: number;
  successful: number;
  failed: number;
  skipped: number;
}

// ============================================================================
// DSpy API Signature Validation Types
// ============================================================================

export interface DSpyValidationIssue {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  suggested_fix: string;
}

export interface DSpySignatureValidation {
  signature_index: number;
  signature_id: string;
  function: string;
  method_chain: string | null;
  library: string;
  status: 'valid' | 'invalid' | 'not_found' | 'error';
  documented: CCDocumentedSignature; // Same structure
  actual: CCActualSignature | null; // Same structure
  issues: DSpyValidationIssue[];
}

export interface DSpyAPISignatureValidationOutput {
  page: string;
  library: string;
  version: string;
  language: string;
  total_signatures: number;
  valid: number;
  invalid: number;
  not_found: number;
  error: number;
  signatures: DSpySignatureValidation[];
}

// ============================================================================
// DSpy Code Example Validation Types
// ============================================================================

export interface DSpyExampleValidation {
  example_index: number;
  line: number;
  context: string;
  code: string;
  status: 'success' | 'failure' | 'skipped';
  depends_on_previous: boolean;
  error_message: string | null;
  execution_output: string | null;
  execution_time_ms: number;
  dependencies_installed: string[];
  trajectory: any | null;
}

export interface DSpyCodeExampleValidationOutput {
  page: string;
  library: string;
  version: string;
  language: string;
  total_examples: number;
  passed: number;
  failed: number;
  skipped: number;
  examples: DSpyExampleValidation[];
  summary: string;
  validation_time_ms: number;
  validated_at: string;
  venv_path: string;
  warnings: string[];
}

// ============================================================================
// Claude Code Clarity Validation Types
// ============================================================================

export interface ClarityIssue {
  type: string; // missing_prerequisite, logical_gap, unclear_explanation, etc.
  severity: 'critical' | 'warning' | 'info';
  line: number;
  section: string;
  step_number: number | null;
  message: string;
  suggested_fix: string | null;
  affected_code: string | null;
  context_quote: string | null;
}

export interface StructuralIssue {
  type: string; // buried_prerequisites, missing_step_numbers, etc.
  severity: 'critical' | 'warning' | 'info';
  location: string;
  message: string;
  suggested_fix: string | null;
}

export interface ClarityScore {
  overall_score: number; // 0-10
  instruction_clarity: number;
  logical_flow: number;
  completeness: number;
  consistency: number;
  prerequisite_coverage: number;
  evaluation_criteria: Record<string, string>;
  scoring_rationale: string | null;
}

export interface BrokenLink {
  url: string;
  line: number;
  link_text: string;
  error: string;
}

export interface MissingAltText {
  image_path: string;
  line: number;
}

export interface CodeBlockIssue {
  line: number;
  content_preview: string;
}

export interface TechnicalAccessibility {
  broken_links: BrokenLink[];
  missing_alt_text: MissingAltText[];
  code_blocks_without_language: CodeBlockIssue[];
  total_links_checked: number;
  total_images_checked: number;
  total_code_blocks_checked: number;
  all_validated: boolean;
}

export interface ClaritySummary {
  total_clarity_issues: number;
  critical_clarity_issues: number;
  warning_clarity_issues: number;
  info_clarity_issues: number;
  total_structural_issues: number;
  critical_structural_issues: number;
  total_technical_issues: number;
  overall_quality_rating: 'excellent' | 'good' | 'needs_improvement' | 'poor';
}

export interface CCClarityValidationOutput {
  validation_id: string;
  validated_at: string;
  source_file: string;
  document_page: string;
  library: string;
  version: string;
  language: string;
  clarity_score: ClarityScore;
  clarity_issues: ClarityIssue[];
  structural_issues: StructuralIssue[];
  technical_accessibility: TechnicalAccessibility;
  summary: ClaritySummary;
  processing_time_ms: number;
  warnings: string[];
}

// ============================================================================
// Walkthrough Types
// ============================================================================

export interface WalkthroughContentFields {
  version: string;
  contentForUser: string;
  contextForAgent: string;
  operationsForAgent: string;
  introductionForAgent: string;
}

export interface WalkthroughStep {
  title: string;
  contentFields: WalkthroughContentFields;
  displayOrder: number;
  createdAt: number;
  updatedAt: number;
  metadata: any;
  nextStepReference: number | null;
}

export interface WalkthroughMetadata {
  title: string;
  description: string;
  type: string;
  status: string;
  createdAt: number;
  updatedAt: number;
  estimatedDurationMinutes: number;
  tags: string[];
  metadata: any;
}

export interface WalkthroughExportMetadata {
  originalDocPath?: string;
  generatedBy?: string;
  [key: string]: any;
}

export interface WalkthroughExport {
  version: string;
  exportedAt: string;
  walkthrough: WalkthroughMetadata;
  steps: WalkthroughStep[];
  metadata?: WalkthroughExportMetadata;
}

export interface GapReport {
  step_number: number;
  step_title: string;
  gap_type: 'clarity' | 'prerequisite' | 'logical_flow' | 'execution_error' | 'completeness' | 'cross_reference';
  severity: 'critical' | 'warning' | 'info';
  description: string;
  suggested_fix: string | null;
  context: string | null;
  timestamp: string;
}

export interface WalkthroughSession {
  walkthrough_id: string;
  current_step: number;
  total_steps: number;
  completed_steps: number;
  is_complete: boolean;
  gaps: GapReport[];
  last_updated: string;
}

export interface WalkthroughData {
  walkthrough: WalkthroughExport;
  session: WalkthroughSession | null; // null if not audited yet
}

// ============================================================================
// Run Management Types
// ============================================================================

export interface RunMetadata {
  run_id: string;
  repo_url: string;
  analysis_type: string;
  created_at: string;
  completed_at: string | null;
  status: 'initializing' | 'cloned' | 'completed' | 'error';
}

export interface RunInfo {
  run_id: string;
  metadata: RunMetadata;
  display_name: string; // Formatted for display
  created_date: Date;
}

// ============================================================================
// API Completeness Types
// ============================================================================

export interface APISurfaceSummary {
  total_public_apis: number;
  by_module: Record<string, string[]>;
  by_type: Record<string, number>;
  deprecated_count: number;
}

export interface CoverageSummary {
  documented: number;
  with_examples: number;
  with_dedicated_sections: number;
  undocumented: number;
  total_apis: number;
  coverage_percentage: number;
  example_coverage_percentage: number;
  complete_coverage_percentage: number;
}

export interface UndocumentedAPI {
  api: string;
  module: string;
  type: string;
  importance: 'high' | 'medium' | 'low';
  importance_score: number;
  reason: string;
  has_docstring: boolean;
  is_async: boolean;
}

export interface DeprecatedInDocs {
  api: string;
  module: string;
  deprecated_since: string | null;
  alternative: string | null;
  documented_in: string[];
  severity: 'critical' | 'warning' | 'info';
  deprecation_message: string | null;
  suggestion: string;
}

export interface DocumentationReference {
  document: string;
  line_number: number;
  context: string;
  match_type: 'import' | 'function_call' | 'method_call' | 'type_annotation' | 'class_instantiation' | 'mention';
  matched_variant?: string;
  in_code_block?: boolean;

  // Optional: from extraction metadata enrichment
  section_hierarchy?: string[];
  markdown_anchor?: string | null;
  code_block_index?: number | null;
}

export interface APIDetail {
  api: string;
  module: string;
  type: string;
  is_async: boolean;
  has_docstring: boolean;
  in_all: boolean;
  is_deprecated: boolean;
  signature: string;
  coverage_tier: number;

  // Rich documentation references
  documentation_references: DocumentationReference[];
  reference_count: number; // NEW: Total number of references found

  // Derived from documentation_references
  documented_in: string[];
  has_examples: boolean;
  has_dedicated_section?: boolean;
  importance: 'high' | 'medium' | 'low';
  importance_score: number;
}

export interface EnvironmentInfo {
  python_version: string;
  platform: string;
  venv_path: string;
}

export interface APICompletenessOutput {
  analysis_id: string;
  analyzed_at: string;
  library: string;
  version: string;
  language: string;
  api_surface: APISurfaceSummary;
  coverage_summary: CoverageSummary;
  undocumented_apis: UndocumentedAPI[];
  deprecated_in_docs: DeprecatedInDocs[];
  api_details: APIDetail[];
  environment: EnvironmentInfo;
  processing_time_ms: number;
  warnings: string[];
}
