"""Agent modules for documentation quality analysis."""

from .extraction_agent import (
    DocumentationExtractionAgent,
    APISignature,
    CodeExample,
    DocumentAnalysis,
    ExtractionSummary,
)

from .api_signature_validation_agent import (
    APISignatureValidationAgent,
    ValidationOutput,
    SignatureValidation,
    ValidationSummary,
)

from .code_example_validation_agent import (
    ValidationAgent as CodeExampleValidationAgent,
    DocumentValidationResult,
)

from .clarity_agent import (
    DocumentationClarityAgent,
    DocumentClarityAnalysis,
    ClarityIssue,
    StructuralIssue,
    ClarityScore,
    TechnicalAccessibility,
    BrokenLink,
    MissingAltText,
    CodeBlockIssue,
    ClarityValidationSummary,
)

__all__ = [
    # Extraction
    "DocumentationExtractionAgent",
    "APISignature",
    "CodeExample",
    "DocumentAnalysis",
    "ExtractionSummary",
    # API Signature Validation
    "APISignatureValidationAgent",
    "ValidationOutput",
    "SignatureValidation",
    "ValidationSummary",
    # Code Example Validation
    "CodeExampleValidationAgent",
    "DocumentValidationResult",
    # Clarity Validation
    "DocumentationClarityAgent",
    "DocumentClarityAnalysis",
    "ClarityIssue",
    "StructuralIssue",
    "ClarityScore",
    "TechnicalAccessibility",
    "BrokenLink",
    "MissingAltText",
    "CodeBlockIssue",
    "ClarityValidationSummary",
]
