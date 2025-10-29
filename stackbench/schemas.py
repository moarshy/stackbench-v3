"""
Centralized Pydantic schemas for all StackBench agents.

This module is the single source of truth for all data models used across
extraction, validation, and analysis agents. All schemas are defined here
to avoid duplication and ensure consistency.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional


# ============================================================================
# EXTRACTION SCHEMAS
# ============================================================================

class SnippetSource(BaseModel):
    """Source information for snippet includes (--8<-- directives)."""
    file: str = Field(description="Source file path, e.g., 'python/python/test_file.py'")
    tags: List[str] = Field(default_factory=list, description="Snippet tags/labels, e.g., ['connect_to_lancedb']")


class APISignature(BaseModel):
    """Represents an API signature found in documentation."""
    library: str = Field(description="Library/package name")
    function: str = Field(description="Function/class/method name")
    method_chain: Optional[str] = Field(None, description="Chained method calls if applicable")
    params: List[str] = Field(default_factory=list, description="Parameter names")
    param_types: Dict[str, str] = Field(default_factory=dict, description="Parameter types")
    defaults: Dict[str, Any] = Field(default_factory=dict, description="Default values")
    imports: Optional[str] = Field(None, description="Import statement needed")
    line: int = Field(description="Approximate line number in document")
    context: str = Field(description="Section/heading this appears under")
    raw_code: Optional[str] = Field(None, description="Exact code snippet showing the signature")

    # Location metadata for better association
    section_hierarchy: List[str] = Field(default_factory=list, description="Hierarchical section path, e.g., ['Create & Query', 'From Polars DataFrame', 'Sync API']")
    markdown_anchor: Optional[str] = Field(None, description="Markdown heading anchor/ID, e.g., '#from-polars-dataframe'")
    code_block_index: int = Field(default=0, description="Index of code block within the section (0, 1, 2...)")

    @field_validator('method_chain', mode='before')
    @classmethod
    def convert_method_chain_list_to_string(cls, v):
        """Convert list of method names to dot-separated string (handles agent mistakes)."""
        if isinstance(v, list):
            return '.'.join(v) if v else None
        return v


class CodeExample(BaseModel):
    """Represents a code example found in documentation."""
    library: str = Field(description="Primary library being demonstrated")
    language: str = Field(description="Programming language")
    code: str = Field(description="Complete code example")
    imports: Optional[str] = Field(None, description="All import statements")
    has_main: bool = Field(description="Whether example has a main/entry point")
    is_executable: bool = Field(description="Whether example can run standalone (DEPRECATED - use execution_context)")
    execution_context: str = Field(
        default="sync",
        description=(
            "Execution context required for this code: "
            "'sync' = runs as-is in normal Python context, "
            "'async' = contains async/await and needs async context, "
            "'not_executable' = incomplete snippet or pseudocode"
        )
    )
    line: int = Field(description="Approximate line number in document")
    context: str = Field(description="Section/heading this appears under")
    dependencies: List[str] = Field(default_factory=list, description="External dependencies needed")

    # Location metadata for better association
    section_hierarchy: List[str] = Field(default_factory=list, description="Hierarchical section path, e.g., ['Create & Query', 'From Polars DataFrame', 'Sync API']")
    markdown_anchor: Optional[str] = Field(None, description="Markdown heading anchor/ID, e.g., '#from-polars-dataframe'")
    code_block_index: int = Field(default=0, description="Index of code block within the section (0, 1, 2...)")
    snippet_source: Optional[SnippetSource] = Field(None, description="If from snippet include (--8<--), the source file and tags")


class ExtractionResult(BaseModel):
    """Result of extracting information from documentation."""
    library: str = Field(description="Primary library/framework name")
    version: Optional[str] = Field(None, description="Library version if mentioned")
    language: str = Field(description="Programming language")
    signatures: List[APISignature] = Field(default_factory=list, description="All API signatures found")
    examples: List[CodeExample] = Field(default_factory=list, description="All code examples found")


class DocumentAnalysis(BaseModel):
    """Complete analysis of a documentation file."""
    page: str = Field(description="Filename of the documentation page")
    library: str = Field(description="Primary library name")
    version: Optional[str] = Field(None, description="Library version")
    language: str = Field(description="Programming language")
    signatures: List[APISignature] = Field(default_factory=list, description="API signatures")
    examples: List[CodeExample] = Field(default_factory=list, description="Code examples")
    processed_at: str = Field(description="ISO timestamp of processing")
    total_signatures: int = Field(description="Count of signatures found")
    total_examples: int = Field(description="Count of examples found")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or issues")
    processing_time_ms: Optional[int] = Field(None, description="Time taken to process")


class ExtractionSummary(BaseModel):
    """Summary of all extraction results."""
    total_documents: int = Field(description="Total markdown files found")
    processed: int = Field(description="Successfully processed documents")
    total_signatures: int = Field(description="Total signatures across all docs")
    total_examples: int = Field(description="Total examples across all docs")
    timestamp: str = Field(description="ISO timestamp of summary generation")
    extraction_duration_seconds: Optional[float] = Field(None, description="Total time taken for extraction in seconds")
    num_workers: Optional[int] = Field(None, description="Number of parallel workers used")
    documents: List[DocumentAnalysis] = Field(default_factory=list, description="All document analyses")


# ============================================================================
# CODE VALIDATION SCHEMAS
# ============================================================================

class ExampleValidationResult(BaseModel):
    """Validation result for a single code example."""
    example_index: int
    line: int
    context: str
    code: str
    status: str = Field(description="success|failure|skipped")
    severity: Optional[str] = Field(None, description="error|warning|info - Classification of issue severity. 'error' = clear doc mistake, 'warning' = environment/compatibility issue, 'info' = non-blocking (deprecations, etc). Only set when status is 'failure'")
    error_message: Optional[str] = None
    suggestions: Optional[str] = None
    execution_output: Optional[str] = None
    depends_on_previous: bool = False

    # Dependency tracking for better association
    depends_on_example_indices: List[int] = Field(default_factory=list, description="Specific example indices this depends on, e.g., [0, 2]")
    actual_code_executed: Optional[str] = Field(None, description="Full code that was executed, including merged dependencies")


class DocumentValidationResult(BaseModel):
    """Validation result for an entire document."""
    page: str
    library: str
    version: str
    language: str
    validation_timestamp: str
    results: List[ExampleValidationResult]
    total_examples: int
    successful: int
    failed: int
    skipped: int


# ============================================================================
# API SIGNATURE VALIDATION SCHEMAS
# ============================================================================

class DocumentedSignature(BaseModel):
    """Signature as documented."""
    params: List[str]
    param_types: Dict[str, str]
    defaults: Dict[str, Any]
    imports: str
    raw_code: str
    line: int
    context: str


class ActualSignature(BaseModel):
    """Actual signature from code introspection."""
    params: List[str]
    param_types: Dict[str, str]
    defaults: Dict[str, Any]
    required_params: List[str]
    optional_params: List[str]
    return_type: Optional[str] = None
    is_async: bool
    is_method: bool
    verified_by: str


class ValidationIssue(BaseModel):
    """A validation issue found."""
    type: str
    severity: str  # 'critical' | 'warning' | 'info'
    message: str
    suggested_fix: Optional[str] = None


class SignatureValidation(BaseModel):
    """Validation result for a single signature."""
    signature_id: str
    function: str
    method_chain: Optional[str] = None
    library: str
    status: str  # 'valid' | 'invalid' | 'not_found' | 'error'
    documented: DocumentedSignature
    actual: Optional[ActualSignature] = None
    issues: List[ValidationIssue]
    confidence: float


class ValidationSummary(BaseModel):
    """Summary of validation results."""
    total_signatures: int
    valid: int
    invalid: int
    not_found: int
    error: int
    accuracy_score: float
    critical_issues: int
    warnings: int


class EnvironmentInfo(BaseModel):
    """Information about the validation environment."""
    library_installed: str
    version_installed: str
    version_requested: str
    version_match: bool
    runtime_version: str  # Python 3.x.y OR Node.js vX.Y.Z
    installation_output: Optional[str] = None


class APISignatureValidationOutput(BaseModel):
    """Complete API signature validation output."""
    validation_id: str
    validated_at: str
    source_file: str
    document_page: str
    library: str
    version: str
    language: str
    summary: ValidationSummary
    validations: List[SignatureValidation]
    environment: EnvironmentInfo
    processing_time_ms: int
    warnings: List[str]


# ============================================================================
# CLARITY VALIDATION SCHEMAS
# ============================================================================

class ClarityIssue(BaseModel):
    """A clarity or UX issue found in documentation."""
    type: str  # missing_prerequisite, logical_gap, unclear_explanation, etc.
    severity: str  # 'critical' | 'warning' | 'info'
    line: int
    section: str
    step_number: Optional[int] = None
    message: str
    suggested_fix: Optional[str] = None
    affected_code: Optional[str] = None
    context_quote: Optional[str] = None


class StructuralIssue(BaseModel):
    """A structural issue in documentation."""
    type: str  # buried_prerequisites, missing_step_numbers, etc.
    severity: str  # 'critical' | 'warning' | 'info'
    location: str
    message: str
    suggested_fix: Optional[str] = None


class ClarityScore(BaseModel):
    """Clarity scoring metrics."""
    overall_score: float  # 0-10
    tier: str  # S/A/B/C/D/F
    instruction_clarity: float
    logical_flow: float
    completeness: float
    consistency: float
    prerequisite_coverage: float


class BrokenLink(BaseModel):
    """A broken link found in documentation."""
    url: str
    line: int
    link_text: str
    error: str


class MissingAltText(BaseModel):
    """An image missing alt text."""
    image_path: str
    line: int


class CodeBlockIssue(BaseModel):
    """A code block without language specification."""
    line: int
    content_preview: str


class TechnicalAccessibility(BaseModel):
    """Technical accessibility validation results."""
    broken_links: List[BrokenLink]
    missing_alt_text: List[MissingAltText]
    code_blocks_without_language: List[CodeBlockIssue]
    total_links_checked: int
    total_images_checked: int
    total_code_blocks_checked: int
    all_validated: bool


class ClaritySummary(BaseModel):
    """Summary of clarity validation."""
    total_clarity_issues: int
    critical_clarity_issues: int
    warning_clarity_issues: int
    info_clarity_issues: int
    total_structural_issues: int
    critical_structural_issues: int
    total_technical_issues: int
    overall_quality_rating: str  # 'excellent' | 'good' | 'needs_improvement' | 'poor'


class PrioritizedFix(BaseModel):
    """A single improvement action from the roadmap."""
    priority: str  # 'critical' | 'high' | 'medium' | 'low'
    category: str
    description: str
    location: str
    impact: str  # 'high' | 'medium' | 'low'
    effort: str  # 'low' | 'medium' | 'high'
    projected_score_change: float


class ImprovementRoadmap(BaseModel):
    """Prioritized list of improvements with projections."""
    current_overall_score: float
    projected_score_after_critical_fixes: float
    projected_score_after_all_fixes: float
    prioritized_fixes: List[PrioritizedFix]
    quick_wins: List[PrioritizedFix]  # High impact + low effort


class ScoreBreakdown(BaseModel):
    """Detailed score calculation breakdown."""
    base_score: float
    critical_issues_penalty: float
    warning_issues_penalty: float
    info_issues_penalty: float
    failed_examples_penalty: float
    invalid_api_penalty: float
    missing_api_penalty: float
    final_score: float


class TierRequirements(BaseModel):
    """Requirements to reach next tier."""
    current_tier: str
    next_tier: Optional[str]
    requirements_for_next_tier: Optional[Dict[str, Any]]
    current_status: Dict[str, int]


class PrimaryIssue(BaseModel):
    """Summary of issues by category."""
    category: str
    critical: int
    warning: int
    info: int
    example: str


class ScoreExplanation(BaseModel):
    """Human-readable score explanation."""
    score: float
    tier: str
    tier_description: str
    score_breakdown: ScoreBreakdown
    tier_requirements: TierRequirements
    primary_issues: List[PrimaryIssue]
    summary: str


class ClarityValidationOutput(BaseModel):
    """Complete clarity validation output."""
    validation_id: str
    validated_at: str
    source_file: str
    document_page: str
    library: str
    version: str
    language: str
    clarity_score: ClarityScore
    clarity_issues: List[ClarityIssue]
    structural_issues: List[StructuralIssue]
    technical_accessibility: TechnicalAccessibility
    improvement_roadmap: ImprovementRoadmap
    score_explanation: ScoreExplanation
    summary: ClaritySummary
    processing_time_ms: int
    warnings: List[str]


# ============================================================================
# API COMPLETENESS & DEPRECATION SCHEMAS
# ============================================================================

class APIMetadata(BaseModel):
    """Metadata about a discovered API."""
    api: str = Field(description="Full API identifier, e.g., 'lancedb.connect', 'Database.create_table'")
    module: str = Field(description="Module path, e.g., 'lancedb', 'lancedb.db'")
    type: str = Field(description="Type of API: 'function', 'class', 'method', 'property'")
    is_async: bool = Field(default=False, description="Whether API is async")
    has_docstring: bool = Field(default=False, description="Whether API has docstring")
    in_all: bool = Field(default=False, description="Whether API is in module's __all__")
    is_deprecated: bool = Field(default=False, description="Whether API is deprecated")
    deprecation_message: Optional[str] = Field(None, description="Deprecation warning message if deprecated")
    alternative_api: Optional[str] = Field(None, description="Suggested alternative API if deprecated")
    deprecated_since: Optional[str] = Field(None, description="Version when deprecated")


class UndocumentedAPI(BaseModel):
    """An API that lacks documentation."""
    api: str = Field(description="Full API identifier")
    module: str = Field(description="Module path")
    type: str = Field(description="API type: function/class/method/property")
    importance: str = Field(description="Importance ranking: 'high', 'medium', 'low'")
    importance_score: int = Field(description="Numeric importance score (0-10)")
    reason: str = Field(description="Why this API is considered important")
    has_docstring: bool = Field(description="Whether API has Python docstring")
    is_async: bool = Field(default=False, description="Whether API is async")


class DeprecatedInDocs(BaseModel):
    """A deprecated API still taught in documentation."""
    api: str = Field(description="Deprecated API identifier")
    module: str = Field(description="Module path")
    deprecated_since: Optional[str] = Field(None, description="Version when deprecated")
    alternative: Optional[str] = Field(None, description="Suggested alternative API")
    documented_in: List[str] = Field(default_factory=list, description="List of doc pages teaching this API")
    severity: str = Field(description="'critical' if deprecated in target version, 'warning' otherwise")
    deprecation_message: Optional[str] = Field(None, description="Full deprecation warning")
    suggestion: str = Field(description="Actionable suggestion for fixing docs")


class DocumentationReference(BaseModel):
    """Rich reference to where an API appears in documentation."""
    document: str = Field(description="Document filename, e.g., 'pandas_and_pyarrow.md'")
    section_hierarchy: List[str] = Field(default_factory=list, description="Section path, e.g., ['Pandas and PyArrow', 'Create dataset']")
    markdown_anchor: Optional[str] = Field(None, description="Markdown anchor, e.g., '#create-dataset'")
    line_number: int = Field(description="Line number in the document")
    context_type: str = Field(description="How API appears: 'signature', 'example', or 'mention'")
    code_block_index: Optional[int] = Field(None, description="Index of code block in section (0-based)")
    raw_context: str = Field(description="Human-readable context description")


class APIDetail(BaseModel):
    """Detailed coverage information for a single API."""
    api: str = Field(description="Full API identifier")
    module: str = Field(description="Module path")
    type: str = Field(description="API type: function/class/method/property")
    is_deprecated: bool = Field(default=False, description="Whether deprecated")
    coverage_tier: int = Field(description="0=undocumented, 1=mentioned, 2=has_example, 3=dedicated_section")

    # Rich documentation references (NEW)
    documentation_references: List[DocumentationReference] = Field(
        default_factory=list,
        description="Detailed references to where this API is documented"
    )

    # Backward compatible fields (derived from documentation_references)
    documented_in: List[str] = Field(default_factory=list, description="Pages that document this API")
    has_examples: bool = Field(default=False, description="Whether API appears in code examples")
    has_dedicated_section: bool = Field(default=False, description="Whether API has its own section")
    importance: str = Field(description="Importance: high/medium/low")
    importance_score: int = Field(description="Numeric importance score")


class APISurfaceSummary(BaseModel):
    """Summary of discovered library API surface."""
    total_public_apis: int = Field(description="Total count of public APIs")
    by_module: Dict[str, List[str]] = Field(default_factory=dict, description="APIs grouped by module")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by type: functions, classes, methods")
    deprecated_count: int = Field(default=0, description="Count of deprecated APIs in library")


class CoverageSummary(BaseModel):
    """Summary of documentation coverage metrics."""
    documented: int = Field(description="APIs with any documentation (tier >= 1)")
    with_examples: int = Field(description="APIs with code examples (tier >= 2)")
    with_dedicated_sections: int = Field(description="APIs with dedicated sections (tier == 3)")
    undocumented: int = Field(description="APIs with no documentation (tier == 0)")
    total_apis: int = Field(description="Total public APIs in library")
    coverage_percentage: float = Field(description="Percentage of documented APIs")
    example_coverage_percentage: float = Field(description="Percentage with examples")
    complete_coverage_percentage: float = Field(description="Percentage with dedicated sections")


class APICompletenessOutput(BaseModel):
    """Complete API coverage and deprecation analysis output."""
    analysis_id: str = Field(description="Unique analysis ID")
    analyzed_at: str = Field(description="ISO timestamp")
    library: str = Field(description="Library name")
    version: str = Field(description="Library version")
    language: str = Field(description="Programming language")

    # API Surface
    api_surface: APISurfaceSummary = Field(description="Discovered API surface")

    # Coverage Metrics
    coverage_summary: CoverageSummary = Field(description="Coverage statistics")

    # Gaps and Issues
    undocumented_apis: List[UndocumentedAPI] = Field(default_factory=list, description="APIs lacking documentation")
    deprecated_in_docs: List[DeprecatedInDocs] = Field(default_factory=list, description="Deprecated APIs in docs")

    # Detailed Information
    api_details: List[APIDetail] = Field(default_factory=list, description="Per-API coverage details")

    # Metadata
    environment: EnvironmentInfo = Field(description="Environment information")
    processing_time_ms: int = Field(description="Time taken for analysis")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or issues")
