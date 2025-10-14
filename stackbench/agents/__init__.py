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
]
