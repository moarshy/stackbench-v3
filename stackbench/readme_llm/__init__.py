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
- Generator Agent: Orchestrates the entire generation process

Usage:
    from stackbench.readme_llm import ReadMeLLMGeneratorAgent, KnowledgeBase

    # Standalone mode
    agent = ReadMeLLMGeneratorAgent(
        docs_path="docs/",
        library_name="lancedb",
        library_version="0.25.2"
    )
    result = agent.generate()

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

__all__ = [
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
