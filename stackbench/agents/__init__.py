"""Agent modules for documentation quality analysis."""

from .extraction_agent import (
    DocumentationExtractionAgent,
    ExtractionSummary,
)

from .api_signature_validation_agent import (
    APISignatureValidationAgent,
)

from .code_example_validation_agent import (
    ValidationAgent as CodeExampleValidationAgent,
)

from .clarity_agent import (
    DocumentationClarityAgent,
    ClarityValidationSummary,
)

from .api_completeness_agent import (
    APICompletenessAgent,
)

# Import schemas from central location for backward compatibility
from stackbench.schemas import (
    SnippetSource,
    APISignature,
    CodeExample,
    DocumentAnalysis,
    DocumentValidationResult,
    APISignatureValidationOutput,
    SignatureValidation,
    ValidationSummary,
    ClarityValidationOutput,
    ClarityIssue,
    StructuralIssue,
    ClarityScore,
    TechnicalAccessibility,
    BrokenLink,
    MissingAltText,
    CodeBlockIssue,
    APICompletenessOutput,
    CoverageSummary,
    UndocumentedAPI,
    DeprecatedInDocs,
)

__all__ = [
    # Extraction
    "DocumentationExtractionAgent",
    "SnippetSource",
    "APISignature",
    "CodeExample",
    "DocumentAnalysis",
    "ExtractionSummary",
    # API Signature Validation
    "APISignatureValidationAgent",
    "APISignatureValidationOutput",
    "SignatureValidation",
    "ValidationSummary",
    # Code Example Validation
    "CodeExampleValidationAgent",
    "DocumentValidationResult",
    # Clarity Validation
    "DocumentationClarityAgent",
    "ClarityValidationOutput",
    "ClarityIssue",
    "StructuralIssue",
    "ClarityScore",
    "TechnicalAccessibility",
    "BrokenLink",
    "MissingAltText",
    "CodeBlockIssue",
    "ClarityValidationSummary",
    # API Completeness & Deprecation
    "APICompletenessAgent",
    "APICompletenessOutput",
    "CoverageSummary",
    "UndocumentedAPI",
    "DeprecatedInDocs",
]
