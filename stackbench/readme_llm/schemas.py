"""
Pydantic schemas for the README.LLM system.

This module defines all data models used in the README.LLM generation and
DocuMentor MCP server. These schemas are independent from the core Stackbench
validation schemas to support standalone operation.

Architecture:
- CodeExample: Raw extracted code blocks from documentation
- IntrospectionResult: Output from language-specific introspection templates
- Parameter: Function/method parameter definition
- APIEntry: Enhanced API catalog entry for knowledge base
- ExampleEntry: Enhanced example with API matching metadata
- LibraryOverview: High-level library information
- KnowledgeBase: Complete structured knowledge base for MCP server
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any


# ============================================================================
# EXTRACTION SCHEMAS
# ============================================================================

class CodeExample(BaseModel):
    """
    Extracted code example from documentation.

    Used during extraction phase before matching to APIs.
    Supports multiple programming languages and snippet resolution.
    """
    example_id: str = Field(description="Generated hash or sequential ID")
    code: str = Field(description="Complete code text")
    language: str = Field(description="Programming language (python, typescript, javascript, go, rust)")
    source_file: str = Field(description="Path to documentation file")
    line_number: int = Field(description="Location in source file")
    is_complete: bool = Field(description="Whether this is a full program vs snippet")
    is_snippet: bool = Field(description="True if from external file (MkDocs --8<--)")
    apis_mentioned: List[str] = Field(
        default_factory=list,
        description="Detected API calls (may be incomplete before matching)"
    )

    # Optional context information
    section_hierarchy: List[str] = Field(
        default_factory=list,
        description="Hierarchical section path where example appears"
    )
    markdown_anchor: Optional[str] = Field(
        None,
        description="Markdown heading anchor/ID"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "example_id": "quickstart_ex1",
                "code": "import lancedb\ndb = lancedb.connect('./my_db')",
                "language": "python",
                "source_file": "docs/quickstart.md",
                "line_number": 42,
                "is_complete": True,
                "is_snippet": False,
                "apis_mentioned": ["lancedb.connect"],
                "section_hierarchy": ["Quick Start", "Basic Setup"],
                "markdown_anchor": "#basic-setup"
            }
        }


# ============================================================================
# INTROSPECTION SCHEMAS
# ============================================================================

class Parameter(BaseModel):
    """Function or method parameter definition."""
    name: str = Field(description="Parameter name")
    type: str = Field(description="Type annotation or inferred type")
    required: bool = Field(description="Whether parameter is required")
    default: Optional[str] = Field(None, description="Default value if any")
    description: str = Field(description="Parameter description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "uri",
                "type": "str",
                "required": True,
                "default": None,
                "description": "Path or URI to database"
            }
        }


class IntrospectionResult(BaseModel):
    """
    Result from running introspection template on a library.

    Output of stackbench/introspection_templates/<language>_introspect.py
    Provides the ground truth API surface for matching.
    """
    language: str = Field(description="Programming language")
    library_name: str = Field(description="Library name")
    library_version: str = Field(description="Library version introspected")
    apis: List[Dict[str, Any]] = Field(description="Raw API data from introspection")
    timestamp: str = Field(description="ISO timestamp of introspection")
    introspection_method: str = Field(
        description="Method used (e.g., 'inspect.signature', 'typescript-parser')"
    )

    # Statistics
    total_functions: int = Field(default=0, description="Count of functions found")
    total_classes: int = Field(default=0, description="Count of classes found")
    total_methods: int = Field(default=0, description="Count of methods found")

    class Config:
        json_schema_extra = {
            "example": {
                "language": "python",
                "library_name": "lancedb",
                "library_version": "0.25.2",
                "apis": [],
                "timestamp": "2025-01-15T10:30:00Z",
                "introspection_method": "inspect.signature",
                "total_functions": 42,
                "total_classes": 8,
                "total_methods": 156
            }
        }


# ============================================================================
# KNOWLEDGE BASE SCHEMAS
# ============================================================================

class APIEntry(BaseModel):
    """
    API catalog entry for knowledge base.

    Enhanced with examples, importance scores, and search metadata.
    Used by DocuMentor MCP server for retrieval.
    """
    api_id: str = Field(description="Fully qualified name (e.g., 'lancedb.connect')")
    language: str = Field(description="Programming language")
    signature: str = Field(description="Full function signature")
    description: str = Field(description="What this API does")
    parameters: List[Parameter] = Field(default_factory=list, description="Parameter definitions")
    returns: Optional[Dict[str, str]] = Field(
        None,
        description="Return type and description"
    )
    examples: List[str] = Field(
        default_factory=list,
        description="References to example IDs"
    )
    importance_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="Importance score (0-1) for ranking"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Semantic tags (e.g., 'connection', 'initialization')"
    )
    related_apis: List[str] = Field(
        default_factory=list,
        description="Other APIs often used together"
    )
    search_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords for search optimization"
    )
    source: Literal["introspection", "documentation", "hybrid"] = Field(
        "introspection",
        description="Where API definition came from"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "api_id": "lancedb.connect",
                "language": "python",
                "signature": "connect(uri: str, **kwargs) -> Connection",
                "description": "Connect to a LanceDB instance",
                "parameters": [
                    {
                        "name": "uri",
                        "type": "str",
                        "required": True,
                        "description": "Path or URI to database"
                    }
                ],
                "returns": {
                    "type": "Connection",
                    "description": "Connection object"
                },
                "examples": ["quickstart_ex1", "connection_ex2"],
                "importance_score": 0.95,
                "tags": ["connection", "initialization"],
                "related_apis": ["Connection.close"],
                "search_keywords": ["connect", "database", "initialize"],
                "source": "introspection"
            }
        }


class ExampleEntry(BaseModel):
    """
    Examples database entry for knowledge base.

    Enhanced CodeExample with API matching, use case classification,
    and validation status.
    """
    example_id: str = Field(description="Unique identifier")
    title: str = Field(description="Human-readable title")
    code: str = Field(description="Complete code")
    language: str = Field(description="Programming language")
    apis_used: List[str] = Field(
        default_factory=list,
        description="APIs used (after matching to introspection)"
    )
    use_case: str = Field(description="Primary use case (initialization, search, etc.)")
    complexity: Literal["beginner", "intermediate", "advanced"] = Field(
        description="Complexity level"
    )
    tags: List[str] = Field(default_factory=list, description="Semantic tags")
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Prerequisites (e.g., 'pip install lancedb')"
    )
    expected_output: Optional[str] = Field(None, description="Expected output if any")
    validated: bool = Field(
        description="True if passed Stackbench validation, False if standalone"
    )
    execution_context: Dict[str, Any] = Field(
        description="Version, timestamp, validation method"
    )
    source_file: str = Field(description="Documentation file path")
    line_number: int = Field(description="Location in file")

    class Config:
        json_schema_extra = {
            "example": {
                "example_id": "quickstart_ex1",
                "title": "Connect to database and create table",
                "code": "import lancedb\ndb = lancedb.connect('./my_db')",
                "language": "python",
                "apis_used": ["lancedb.connect"],
                "use_case": "initialization",
                "complexity": "beginner",
                "tags": ["quickstart", "setup"],
                "prerequisites": ["pip install lancedb"],
                "expected_output": None,
                "validated": False,
                "execution_context": {
                    "library_version": "0.25.2",
                    "generation_method": "standalone",
                    "timestamp": "2025-01-15T10:30:00Z"
                },
                "source_file": "docs/quickstart.md",
                "line_number": 42
            }
        }


class LibraryOverview(BaseModel):
    """High-level library information for context."""
    name: str = Field(description="Library name")
    version: str = Field(description="Library version")
    languages: List[str] = Field(description="Supported programming languages")
    domain: Optional[str] = Field(
        None,
        description="Domain/category (e.g., 'vector database', 'web framework')"
    )
    description: str = Field(description="Brief library description")
    architecture: Optional[str] = Field(None, description="Architecture overview")
    key_concepts: List[str] = Field(
        default_factory=list,
        description="Core concepts users should understand"
    )
    quickstart_summary: str = Field(description="Quick start summary")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "lancedb",
                "version": "0.25.2",
                "languages": ["python", "typescript", "javascript"],
                "domain": "vector database",
                "description": "Fast vector database for AI applications",
                "architecture": "Built on Lance columnar format",
                "key_concepts": ["vector search", "ANN indexes", "columnar storage"],
                "quickstart_summary": "Install, connect, create table, search"
            }
        }


class KnowledgeBase(BaseModel):
    """
    Complete knowledge base structure for MCP server.

    Generated by both standalone and integration modes.
    Provides structured, searchable documentation data.
    """
    library_overview: LibraryOverview = Field(description="High-level library info")
    api_catalog: Dict[str, Dict[str, APIEntry]] = Field(
        description="APIs grouped by language: {language: {api_id: entry}}"
    )
    examples_db: Dict[str, Dict[str, ExampleEntry]] = Field(
        description="Examples grouped by language: {language: {example_id: entry}}"
    )
    concept_graph: Optional[Dict[str, Any]] = Field(
        None,
        description="Future: relationship graph between concepts"
    )
    metadata: Dict[str, Any] = Field(description="Generation metadata and stats")

    class Config:
        json_schema_extra = {
            "example": {
                "library_overview": {
                    "name": "lancedb",
                    "version": "0.25.2",
                    "languages": ["python"],
                    "domain": "vector database",
                    "description": "Fast vector database for AI apps",
                    "key_concepts": ["vector search", "ANN indexes"],
                    "quickstart_summary": "Install, connect, create table, search"
                },
                "api_catalog": {
                    "python": {
                        "lancedb.connect": {}
                    }
                },
                "examples_db": {
                    "python": {
                        "quickstart_ex1": {}
                    }
                },
                "metadata": {
                    "generation_mode": "standalone",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "total_apis": 42,
                    "total_examples": 87,
                    "languages": ["python"]
                }
            }
        }


# ============================================================================
# MCP SERVER SCHEMAS
# ============================================================================

class FeedbackIssue(BaseModel):
    """User-reported issue for continuous improvement."""
    timestamp: str = Field(description="ISO timestamp")
    query: str = Field(description="What user was trying to do")
    apis_tried: List[str] = Field(default_factory=list, description="APIs attempted")
    error_message: Optional[str] = Field(None, description="Error received")
    code_attempted: Optional[str] = Field(None, description="Code that didn't work")
    issue_type: Literal["error", "unclear_docs", "missing_example", "wrong_signature"] = Field(
        description="Issue category"
    )
    session_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recent tool calls and context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-15T14:30:00Z",
                "query": "How do I search for similar vectors?",
                "apis_tried": ["Table.search"],
                "error_message": "AttributeError: no attribute 'to_list'",
                "code_attempted": "results = table.search([1,2,3]).to_list()",
                "issue_type": "error",
                "session_context": {}
            }
        }


class SearchResult(BaseModel):
    """Search result from retrieval system."""
    item_id: str = Field(description="API ID or example ID")
    item_type: Literal["api", "example"] = Field(description="Type of result")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance to query")
    importance_score: float = Field(ge=0.0, le=1.0, description="Inherent importance")
    final_score: float = Field(ge=0.0, le=1.0, description="Combined score")
    content: Dict[str, Any] = Field(description="Full API or example data")


# ============================================================================
# GENERATION OUTPUT SCHEMAS
# ============================================================================

class ReadMeLLMOutput(BaseModel):
    """Output metadata for README.LLM generation."""
    run_id: str = Field(description="Unique run identifier")
    library_name: str = Field(description="Library name")
    library_version: str = Field(description="Library version")
    languages: List[str] = Field(description="Languages processed")
    generation_mode: Literal["standalone", "integration"] = Field(
        description="How README.LLM was generated"
    )
    timestamp: str = Field(description="ISO timestamp")

    # Output paths
    readme_llm_path: str = Field(description="Path to monolithic README.LLM file")
    knowledge_base_path: str = Field(description="Path to knowledge_base/ directory")

    # Statistics
    total_apis: int = Field(description="Total APIs in catalog")
    total_examples: int = Field(description="Total examples in database")
    apis_by_language: Dict[str, int] = Field(
        default_factory=dict,
        description="API count per language"
    )
    examples_by_language: Dict[str, int] = Field(
        default_factory=dict,
        description="Example count per language"
    )

    # Quality metrics (if integration mode)
    validated_examples: Optional[int] = Field(
        None,
        description="Number of validated examples (integration mode only)"
    )
    validation_pass_rate: Optional[float] = Field(
        None,
        description="Percentage of examples that passed validation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "abc-123-def",
                "library_name": "lancedb",
                "library_version": "0.25.2",
                "languages": ["python", "typescript"],
                "generation_mode": "standalone",
                "timestamp": "2025-01-15T10:30:00Z",
                "readme_llm_path": "data/abc-123-def/readme_llm/README.LLM",
                "knowledge_base_path": "data/abc-123-def/readme_llm/knowledge_base/",
                "total_apis": 42,
                "total_examples": 87,
                "apis_by_language": {"python": 42},
                "examples_by_language": {"python": 87}
            }
        }
