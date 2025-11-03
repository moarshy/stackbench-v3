#!/usr/bin/env python3
"""
DocuMentor MCP Server

Provides LLM-friendly access to README.LLM knowledge base through standardized tools.
Enables Claude to assist developers by retrieving library documentation, APIs, and examples.

Tools:
1. get_library_overview - Retrieve high-level library information
2. find_api - Search for APIs by query
3. get_examples - Search for code examples
4. report_issue - Collect user feedback on documentation quality

Usage:
    # Start server (stdio mode)
    python -m stackbench.readme_llm.mcp_servers.documentor_server \\
        --knowledge-base-path data/run_123/readme_llm/knowledge_base

    # Or via CLI
    stackbench readme-llm mcp serve \\
        --knowledge-base-path data/run_123/readme_llm/knowledge_base
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field

from stackbench.readme_llm.mcp_servers.retrieval import KeywordRetrieval, HybridRetrieval
from stackbench.readme_llm.schemas import FeedbackIssue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/documentor_mcp_server.log')]
)
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR TOOL ARGUMENTS
# ============================================================================

class GetLibraryOverviewArgs(BaseModel):
    """Arguments for get_library_overview tool."""
    pass  # No arguments needed


class FindAPIArgs(BaseModel):
    """Arguments for find_api tool."""
    query: str = Field(..., description="Search query for API (e.g., 'connect to database')")
    language: Optional[str] = Field(None, description="Filter by programming language (python, typescript, etc.)")
    top_k: int = Field(5, description="Number of results to return (default: 5)")
    min_importance: float = Field(0.0, description="Minimum importance score (0.0-1.0)")


class GetExamplesArgs(BaseModel):
    """Arguments for get_examples tool."""
    query: str = Field(..., description="Search query for examples (e.g., 'vector search')")
    language: Optional[str] = Field(None, description="Filter by programming language")
    complexity: Optional[str] = Field(None, description="Filter by complexity (beginner, intermediate, advanced)")
    top_k: int = Field(5, description="Number of results to return (default: 5)")


class ReportIssueArgs(BaseModel):
    """Arguments for report_issue tool."""
    issue_type: str = Field(..., description="Type of issue (broken_example, incorrect_signature, unclear_docs, missing_info, other)")
    description: str = Field(..., description="Detailed description of the issue")
    api_id: Optional[str] = Field(None, description="Related API ID (if applicable)")
    example_id: Optional[str] = Field(None, description="Related example ID (if applicable)")
    severity: str = Field("medium", description="Severity level (critical, high, medium, low)")


# ============================================================================
# DOCUMENTOR SERVER
# ============================================================================

class DocuMentorServer:
    """
    MCP Server for README.LLM knowledge base access.

    Provides tools for:
    - Library overview retrieval
    - API search
    - Example search
    - Feedback collection
    """

    def __init__(
        self,
        knowledge_base_path: Path,
        search_mode: str = "hybrid",
        vector_model: Optional[str] = None,
    ):
        """
        Initialize DocuMentor server.

        Args:
            knowledge_base_path: Path to knowledge_base/ directory
            search_mode: Search mode - "keyword", "vector", or "hybrid" (default)
            vector_model: Sentence-transformer model name (optional, for vector/hybrid)
        """
        self.kb_path = Path(knowledge_base_path)
        self.server = Server("documentor")
        self.search_mode = search_mode

        # Initialize retrieval system based on mode
        if search_mode == "keyword":
            logger.info(f"Initializing KeywordRetrieval with knowledge base: {self.kb_path}")
            self.retrieval = KeywordRetrieval(self.kb_path)
        elif search_mode == "hybrid":
            logger.info(f"Initializing HybridRetrieval with knowledge base: {self.kb_path}")
            self.retrieval = HybridRetrieval(
                self.kb_path,
                vector_model=vector_model,
                enable_vector=True
            )
        else:
            raise ValueError(f"Invalid search mode: {search_mode}. Must be 'keyword' or 'hybrid'.")

        # Load library overview
        self.library_overview = self._load_library_overview()

        # Feedback storage
        self.feedback_file = self.kb_path.parent / "feedback.jsonl"
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)

        # Register tools
        self._register_tools()

        logger.info("DocuMentor server initialized successfully")

    def _load_library_overview(self) -> Dict:
        """Load library overview from knowledge base."""
        overview_path = self.kb_path / "library_overview.json"
        if not overview_path.exists():
            raise FileNotFoundError(f"Library overview not found: {overview_path}")

        return json.loads(overview_path.read_text(encoding='utf-8'))

    def _register_tools(self):
        """Register all MCP tools."""

        # Tool 1: get_library_overview
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_library_overview",
                    description=(
                        "Get high-level information about the library including name, version, "
                        "supported languages, domain, key concepts, and quickstart summary. "
                        "Use this first to understand what the library does."
                    ),
                    inputSchema=GetLibraryOverviewArgs.model_json_schema()
                ),
                Tool(
                    name="find_api",
                    description=(
                        "Search for library APIs (functions, classes, methods) by keyword query. "
                        "Returns matching APIs with signatures, descriptions, importance scores, "
                        "and related examples. Supports filtering by language and importance."
                    ),
                    inputSchema=FindAPIArgs.model_json_schema()
                ),
                Tool(
                    name="get_examples",
                    description=(
                        "Search for code examples by keyword query. Returns matching examples "
                        "with code snippets, usage descriptions, complexity levels, and related APIs. "
                        "Supports filtering by language and complexity."
                    ),
                    inputSchema=GetExamplesArgs.model_json_schema()
                ),
                Tool(
                    name="report_issue",
                    description=(
                        "Report a documentation issue or provide feedback. Use this when you "
                        "encounter broken examples, incorrect API signatures, unclear documentation, "
                        "or missing information. Issues are logged for library maintainers."
                    ),
                    inputSchema=ReportIssueArgs.model_json_schema()
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> List[TextContent]:
            """Route tool calls to appropriate handlers."""
            logger.info(f"Tool called: {name} with args: {arguments}")

            try:
                if name == "get_library_overview":
                    result = await self._handle_get_library_overview(arguments)
                elif name == "find_api":
                    result = await self._handle_find_api(arguments)
                elif name == "get_examples":
                    result = await self._handle_get_examples(arguments)
                elif name == "report_issue":
                    result = await self._handle_report_issue(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                logger.error(f"Error in tool {name}: {e}", exc_info=True)
                error_result = {
                    "success": False,
                    "error": str(e),
                    "tool": name
                }
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    # ========================================================================
    # TOOL HANDLERS
    # ========================================================================

    async def _handle_get_library_overview(self, args: Dict) -> Dict:
        """
        Handle get_library_overview tool call.

        Returns:
            Library overview with metadata, key concepts, and quickstart info
        """
        # Load metadata for stats
        metadata_path = self.kb_path / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))

        return {
            "success": True,
            "library": {
                "name": self.library_overview.get("name", "Unknown"),
                "version": self.library_overview.get("version", "Unknown"),
                "languages": self.library_overview.get("languages", []),
                "domain": self.library_overview.get("domain"),
                "description": self.library_overview.get("description", ""),
                "architecture": self.library_overview.get("architecture"),
                "key_concepts": self.library_overview.get("key_concepts", []),
                "quickstart_summary": self.library_overview.get("quickstart_summary", ""),
            },
            "statistics": {
                "total_apis": metadata.get("total_apis", 0),
                "total_examples": metadata.get("total_examples", 0),
                "apis_by_language": metadata.get("apis_by_language", {}),
                "examples_by_language": metadata.get("examples_by_language", {}),
                "validated_examples": metadata.get("validated_examples"),
            },
            "generation_info": {
                "mode": metadata.get("generation_mode", "unknown"),
                "timestamp": metadata.get("timestamp", ""),
                "knowledge_base_version": metadata.get("knowledge_base_version", "1.0"),
            }
        }

    async def _handle_find_api(self, args: Dict) -> Dict:
        """
        Handle find_api tool call.

        Args:
            args: Tool arguments (query, language, top_k, min_importance)

        Returns:
            Search results with API details
        """
        # Validate arguments
        validated_args = FindAPIArgs(**args)

        # Perform search
        results = self.retrieval.search_apis(
            query=validated_args.query,
            language=validated_args.language,
            top_k=validated_args.top_k,
            min_importance=validated_args.min_importance
        )

        # Format results
        formatted_results = []
        for result in results:
            api_details = self.retrieval.get_api_details(result.result_id)
            if api_details:
                formatted_results.append({
                    "api_id": result.result_id,
                    "title": result.title,
                    "description": result.description,
                    "signature": api_details.get("signature", ""),
                    "language": result.language,
                    "importance_score": result.metadata.get("importance_score", 0.0),
                    "relevance_score": round(result.score, 3),
                    "parameters": api_details.get("parameters", []),
                    "returns": api_details.get("returns"),
                    "examples": api_details.get("examples", []),
                    "tags": result.metadata.get("tags", []),
                    "related_apis": result.metadata.get("related_apis", []),
                })

        return {
            "success": True,
            "query": validated_args.query,
            "filters": {
                "language": validated_args.language,
                "min_importance": validated_args.min_importance,
            },
            "total_results": len(formatted_results),
            "results": formatted_results,
        }

    async def _handle_get_examples(self, args: Dict) -> Dict:
        """
        Handle get_examples tool call.

        Args:
            args: Tool arguments (query, language, complexity, top_k)

        Returns:
            Search results with example details
        """
        # Validate arguments
        validated_args = GetExamplesArgs(**args)

        # Perform search
        results = self.retrieval.search_examples(
            query=validated_args.query,
            language=validated_args.language,
            complexity=validated_args.complexity,
            top_k=validated_args.top_k
        )

        # Format results
        formatted_results = []
        for result in results:
            example_details = self.retrieval.get_example_details(result.result_id)
            if example_details:
                formatted_results.append({
                    "example_id": result.result_id,
                    "title": result.title,
                    "description": result.description,
                    "code": example_details.get("code", ""),
                    "language": result.language,
                    "complexity": result.metadata.get("complexity", "beginner"),
                    "relevance_score": round(result.score, 3),
                    "apis_used": result.metadata.get("apis_used", []),
                    "use_case": example_details.get("use_case", ""),
                    "tags": result.metadata.get("tags", []),
                    "prerequisites": example_details.get("prerequisites", []),
                    "expected_output": example_details.get("expected_output"),
                    "validated": result.metadata.get("validated", False),
                    "source_file": example_details.get("source_file", ""),
                    "line_number": example_details.get("line_number"),
                })

        return {
            "success": True,
            "query": validated_args.query,
            "filters": {
                "language": validated_args.language,
                "complexity": validated_args.complexity,
            },
            "total_results": len(formatted_results),
            "results": formatted_results,
        }

    async def _handle_report_issue(self, args: Dict) -> Dict:
        """
        Handle report_issue tool call.

        Args:
            args: Tool arguments (issue_type, description, api_id, example_id, severity)

        Returns:
            Confirmation of issue submission
        """
        # Validate arguments
        validated_args = ReportIssueArgs(**args)

        # Create feedback issue
        feedback = FeedbackIssue(
            issue_id=f"issue_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now().isoformat(),
            issue_type=validated_args.issue_type,
            severity=validated_args.severity,
            description=validated_args.description,
            api_id=validated_args.api_id,
            example_id=validated_args.example_id,
            reporter="mcp_user",
            status="open",
            metadata={}
        )

        # Append to feedback file (JSONL format)
        try:
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(feedback.model_dump_json() + '\n')

            logger.info(f"Feedback recorded: {feedback.issue_id}")

            return {
                "success": True,
                "issue_id": feedback.issue_id,
                "message": "Thank you for your feedback! This issue has been logged and will be reviewed by library maintainers.",
                "feedback_file": str(self.feedback_file),
            }

        except Exception as e:
            logger.error(f"Failed to write feedback: {e}")
            return {
                "success": False,
                "error": f"Failed to record feedback: {e}"
            }

    # ========================================================================
    # SERVER LIFECYCLE
    # ========================================================================

    async def run(self):
        """Run the MCP server (stdio mode)."""
        logger.info("Starting DocuMentor MCP server (stdio mode)")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for DocuMentor MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="DocuMentor MCP Server - Provides LLM access to README.LLM knowledge base"
    )
    parser.add_argument(
        "--knowledge-base-path",
        type=Path,
        required=True,
        help="Path to knowledge_base/ directory"
    )
    parser.add_argument(
        "--search-mode",
        type=str,
        default="hybrid",
        choices=["keyword", "hybrid"],
        help="Search mode: keyword (fast, exact) or hybrid (keyword + semantic, default)"
    )
    parser.add_argument(
        "--vector-model",
        type=str,
        default=None,
        help="Sentence-transformer model name (default: all-MiniLM-L6-v2)"
    )

    args = parser.parse_args()

    # Validate knowledge base path
    if not args.knowledge_base_path.exists():
        print(f"Error: Knowledge base not found: {args.knowledge_base_path}", file=sys.stderr)
        sys.exit(1)

    # Create and run server
    try:
        server = DocuMentorServer(
            args.knowledge_base_path,
            search_mode=args.search_mode,
            vector_model=args.vector_model
        )
        import asyncio
        asyncio.run(server.run())
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
