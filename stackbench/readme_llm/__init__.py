"""
README.LLM System - Standalone documentation transformation for LLMs.

This module implements the README.LLM framework (Wijaya et al., 2025) to transform
library documentation into LLM-optimized format. It operates independently from
Stackbench's validation pipeline but can optionally integrate with validated results.

Main Components:
- Extractors: Language detection, code extraction, snippet resolution
- Introspection: Wrapper for language-specific introspection templates
- Matchers: Link code examples to APIs
- Formatters: Generate README.LLM (XML) and knowledge base (JSON)
- Generator: Orchestrates the entire generation process

Usage:
    from stackbench.readme_llm import ReadMeLLMGenerator
    from pathlib import Path

    # Standalone mode
    generator = ReadMeLLMGenerator(
        docs_path=Path("docs/"),
        library_name="lancedb",
        library_version="0.25.2"
    )
    result = generator.generate()

Architecture follows the walkthroughs/ pattern for standalone operation.
"""

from .schemas import (
    # Extraction
    CodeExample,
    IntrospectionResult,
    Parameter,

    # Knowledge Base
    APIEntry,
    ExampleEntry,
    LibraryOverview,
    KnowledgeBase,

    # MCP Server
    FeedbackIssue,
    SearchResult,

    # Output
    ReadMeLLMOutput,
)

from .generator import ReadMeLLMGenerator

__all__ = [
    # Main generator
    "ReadMeLLMGenerator",

    # Extraction schemas
    "CodeExample",
    "IntrospectionResult",
    "Parameter",

    # Knowledge base schemas
    "APIEntry",
    "ExampleEntry",
    "LibraryOverview",
    "KnowledgeBase",

    # MCP server schemas
    "FeedbackIssue",
    "SearchResult",

    # Output schemas
    "ReadMeLLMOutput",
]

__version__ = "0.1.0"
