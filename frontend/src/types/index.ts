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
  error_message: string | null;
  suggestions: string | null;
  execution_output: string | null;
  depends_on_previous: boolean;
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
