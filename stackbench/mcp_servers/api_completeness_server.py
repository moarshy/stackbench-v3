#!/usr/bin/env python3
"""
API Completeness MCP Server

Provides deterministic API introspection, importance scoring, and coverage analysis
for documentation completeness validation. Separates deterministic operations (this server)
from qualitative analysis (completeness agent).

Tools:
1. introspect_library - Discover all public APIs in a library via inspect module
2. calculate_importance_score - Score API importance based on heuristics
3. classify_coverage - Determine coverage tier for an API
4. calculate_metrics - Compute coverage percentages and summaries
5. prioritize_undocumented - Rank undocumented APIs by importance
"""

import sys
import json
import logging
import subprocess
import tempfile
import importlib
import inspect
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/api_completeness_mcp_server.log')]
)
logger = logging.getLogger(__name__)


# ============================================================================
# SCORING HEURISTICS
# ============================================================================

IMPORTANCE_WEIGHTS = {
    "in_all": 3,              # API is in module's __all__
    "has_docstring": 2,       # API has documentation
    "not_private": 1,         # Not underscore-prefixed
    "top_level": 1,           # Top-level module
    "common_name": 1,         # Common naming patterns
}

COMMON_API_PATTERNS = [
    "connect", "create", "open", "close", "get", "set",
    "read", "write", "update", "delete", "insert", "query",
    "start", "stop", "init", "load", "save", "execute"
]

IMPORTANCE_TIERS = {
    "high": (7, 10),      # Critical APIs users will need
    "medium": (4, 6),     # Useful but not essential
    "low": (0, 3),        # Edge cases or internal
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class APIMetadata(BaseModel):
    """Metadata about a discovered API."""
    api: str
    module: str
    type: str  # function, class, method, property
    is_async: bool = False
    has_docstring: bool = False
    in_all: bool = False
    is_deprecated: bool = False
    deprecation_message: Optional[str] = None
    alternative_api: Optional[str] = None
    deprecated_since: Optional[str] = None


class ImportanceScore(BaseModel):
    """Importance score result."""
    api: str
    score: int  # 0-10
    tier: str  # high, medium, low
    reasons: List[str]
    breakdown: Dict[str, int]


class CoverageTier(BaseModel):
    """Coverage classification for an API."""
    api: str
    tier: int  # 0=undocumented, 1=mentioned, 2=has_example, 3=dedicated_section
    documented_in: List[str]
    has_examples: bool
    has_dedicated_section: bool


class CoverageMetrics(BaseModel):
    """Overall coverage metrics."""
    total_apis: int
    documented: int
    with_examples: int
    with_dedicated_sections: int
    undocumented: int
    coverage_percentage: float
    example_coverage_percentage: float
    complete_coverage_percentage: float


# ============================================================================
# LIBRARY INTROSPECTION
# ============================================================================

def install_library(library_name: str, version: str, venv_path: Path) -> Tuple[bool, str]:
    """
    Install library in isolated virtual environment.

    Args:
        library_name: Name of library to install
        version: Version to install
        venv_path: Path to virtual environment

    Returns:
        Tuple of (success, message)
    """
    try:
        # Create venv if doesn't exist
        if not venv_path.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True,
                text=True
            )

        # Install library
        pip_path = venv_path / "bin" / "pip"
        result = subprocess.run(
            [str(pip_path), "install", f"{library_name}=={version}"],
            check=True,
            capture_output=True,
            text=True
        )

        return True, f"Installed {library_name}=={version}"
    except subprocess.CalledProcessError as e:
        return False, f"Installation failed: {e.stderr}"


def introspect_module(module_name: str, parent_path: str = "") -> List[APIMetadata]:
    """
    Recursively introspect a module to find all public APIs.

    Args:
        module_name: Name of module to introspect
        parent_path: Parent module path for nested modules

    Returns:
        List of APIMetadata objects
    """
    apis = []

    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        logger.error(f"Failed to import {module_name}: {e}")
        return apis

    # Get __all__ if defined
    all_names = getattr(module, '__all__', None)

    # Iterate through module members
    for name, obj in inspect.getmembers(module):
        # Skip private members unless in __all__
        if name.startswith('_') and (not all_names or name not in all_names):
            continue

        full_name = f"{parent_path}.{name}" if parent_path else name
        in_all = all_names is not None and name in all_names

        # Determine type and extract metadata
        if inspect.isfunction(obj):
            apis.append(APIMetadata(
                api=full_name,
                module=module_name,
                type="function",
                is_async=inspect.iscoroutinefunction(obj),
                has_docstring=bool(obj.__doc__),
                in_all=in_all,
                is_deprecated=is_deprecated(obj)
            ))

        elif inspect.isclass(obj):
            # Add class itself
            apis.append(APIMetadata(
                api=full_name,
                module=module_name,
                type="class",
                has_docstring=bool(obj.__doc__),
                in_all=in_all,
                is_deprecated=is_deprecated(obj)
            ))

            # Add class methods
            for method_name, method_obj in inspect.getmembers(obj, inspect.isfunction):
                if not method_name.startswith('_') or method_name in ['__init__', '__call__']:
                    method_full_name = f"{full_name}.{method_name}"
                    apis.append(APIMetadata(
                        api=method_full_name,
                        module=module_name,
                        type="method",
                        is_async=inspect.iscoroutinefunction(method_obj),
                        has_docstring=bool(method_obj.__doc__),
                        in_all=False,  # Methods not in __all__
                        is_deprecated=is_deprecated(method_obj)
                    ))

    return apis


def is_deprecated(obj: Any) -> bool:
    """
    Check if an API is deprecated.

    Args:
        obj: Python object to check

    Returns:
        True if deprecated
    """
    # Check for @deprecated decorator
    if hasattr(obj, '__deprecated__'):
        return True

    # Check docstring for deprecation warning
    docstring = getattr(obj, '__doc__', '')
    if docstring and any(word in docstring.lower() for word in ['deprecated', 'deprecation']):
        return True

    return False


def extract_deprecation_info(obj: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract deprecation message and alternative from object.

    Args:
        obj: Python object

    Returns:
        Tuple of (message, alternative)
    """
    message = None
    alternative = None

    # Check __deprecated__ attribute
    if hasattr(obj, '__deprecated__'):
        message = getattr(obj, '__deprecated__', None)

    # Parse docstring
    docstring = getattr(obj, '__doc__', '')
    if docstring:
        lines = docstring.lower().split('\n')
        for line in lines:
            if 'deprecated' in line:
                message = line.strip()
                # Look for "use X instead"
                if 'use' in line and 'instead' in line:
                    parts = line.split('use')
                    if len(parts) > 1:
                        alternative = parts[1].split('instead')[0].strip()

    return message, alternative


# ============================================================================
# IMPORTANCE SCORING
# ============================================================================

def calculate_importance(api_metadata: APIMetadata) -> ImportanceScore:
    """
    Calculate importance score for an API.

    Args:
        api_metadata: Metadata about the API

    Returns:
        ImportanceScore with tier classification
    """
    score = 0
    reasons = []
    breakdown = {}

    # In __all__
    if api_metadata.in_all:
        score += IMPORTANCE_WEIGHTS["in_all"]
        breakdown["in_all"] = IMPORTANCE_WEIGHTS["in_all"]
        reasons.append("Explicitly listed in __all__")

    # Has docstring
    if api_metadata.has_docstring:
        score += IMPORTANCE_WEIGHTS["has_docstring"]
        breakdown["has_docstring"] = IMPORTANCE_WEIGHTS["has_docstring"]
        reasons.append("Has documentation")

    # Not private
    if not api_metadata.api.split('.')[-1].startswith('_'):
        score += IMPORTANCE_WEIGHTS["not_private"]
        breakdown["not_private"] = IMPORTANCE_WEIGHTS["not_private"]
        reasons.append("Public API (not underscore-prefixed)")

    # Top-level module
    if '.' not in api_metadata.module or api_metadata.module.count('.') == 0:
        score += IMPORTANCE_WEIGHTS["top_level"]
        breakdown["top_level"] = IMPORTANCE_WEIGHTS["top_level"]
        reasons.append("Top-level module")

    # Common name patterns
    api_name = api_metadata.api.split('.')[-1].lower()
    if any(pattern in api_name for pattern in COMMON_API_PATTERNS):
        score += IMPORTANCE_WEIGHTS["common_name"]
        breakdown["common_name"] = IMPORTANCE_WEIGHTS["common_name"]
        reasons.append(f"Common API pattern: {api_name}")

    # Determine tier
    tier = "low"
    for tier_name, (min_score, max_score) in IMPORTANCE_TIERS.items():
        if min_score <= score <= max_score:
            tier = tier_name
            break

    return ImportanceScore(
        api=api_metadata.api,
        score=score,
        tier=tier,
        reasons=reasons,
        breakdown=breakdown
    )


# ============================================================================
# COVERAGE CLASSIFICATION
# ============================================================================

def classify_coverage_tier(
    api: str,
    documented_in: List[str],
    appears_in_examples: bool,
    has_dedicated_section: bool
) -> CoverageTier:
    """
    Classify coverage tier for an API.

    Args:
        api: API name
        documented_in: List of pages mentioning this API
        appears_in_examples: Whether API appears in code examples
        has_dedicated_section: Whether API has dedicated documentation section

    Returns:
        CoverageTier classification
    """
    if not documented_in:
        tier = 0  # Undocumented
    elif has_dedicated_section:
        tier = 3  # Dedicated section
    elif appears_in_examples:
        tier = 2  # Has example
    else:
        tier = 1  # Mentioned only

    return CoverageTier(
        api=api,
        tier=tier,
        documented_in=documented_in,
        has_examples=appears_in_examples,
        has_dedicated_section=has_dedicated_section
    )


# ============================================================================
# METRICS CALCULATION
# ============================================================================

def calculate_coverage_metrics(coverage_data: List[CoverageTier]) -> CoverageMetrics:
    """
    Calculate overall coverage metrics.

    Args:
        coverage_data: List of coverage classifications

    Returns:
        CoverageMetrics summary
    """
    total_apis = len(coverage_data)

    undocumented = sum(1 for c in coverage_data if c.tier == 0)
    documented = sum(1 for c in coverage_data if c.tier >= 1)
    with_examples = sum(1 for c in coverage_data if c.tier >= 2)
    with_dedicated = sum(1 for c in coverage_data if c.tier == 3)

    coverage_pct = (documented / total_apis * 100) if total_apis > 0 else 0.0
    example_pct = (with_examples / total_apis * 100) if total_apis > 0 else 0.0
    complete_pct = (with_dedicated / total_apis * 100) if total_apis > 0 else 0.0

    return CoverageMetrics(
        total_apis=total_apis,
        documented=documented,
        with_examples=with_examples,
        with_dedicated_sections=with_dedicated,
        undocumented=undocumented,
        coverage_percentage=round(coverage_pct, 1),
        example_coverage_percentage=round(example_pct, 1),
        complete_coverage_percentage=round(complete_pct, 1)
    )


# ============================================================================
# PRIORITIZATION
# ============================================================================

def prioritize_undocumented_apis(
    undocumented_apis: List[str],
    importance_scores: Dict[str, ImportanceScore]
) -> List[Dict[str, Any]]:
    """
    Prioritize undocumented APIs by importance.

    Args:
        undocumented_apis: List of undocumented API names
        importance_scores: Map of API name to importance score

    Returns:
        Sorted list of undocumented APIs with priority ranking
    """
    prioritized = []

    for api in undocumented_apis:
        score_data = importance_scores.get(api)
        if score_data:
            prioritized.append({
                "api": api,
                "importance": score_data.tier,
                "importance_score": score_data.score,
                "reasons": score_data.reasons,
                "rank": 0  # Will be set after sorting
            })

    # Sort by importance score (descending)
    prioritized.sort(key=lambda x: x["importance_score"], reverse=True)

    # Assign ranks
    for i, item in enumerate(prioritized, 1):
        item["rank"] = i

    return prioritized


# ============================================================================
# MCP SERVER
# ============================================================================

class APICompletenessMCPServer:
    """MCP Server for API completeness analysis."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("api-completeness-server")
        self._register_tools()
        logger.info("APICompletenessMCPServer initialized")

    def _register_tools(self):
        """Register all MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="introspect_library",
                    description=(
                        "Discover all public APIs in a library via Python introspection. "
                        "Installs the library and uses inspect module to find functions, "
                        "classes, and methods. Returns metadata including deprecation status."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "library_name": {"type": "string", "description": "Library to introspect (e.g., 'lancedb')"},
                            "version": {"type": "string", "description": "Version to install (e.g., '0.25.2')"},
                            "modules": {"type": "array", "items": {"type": "string"}, "description": "Optional list of specific modules to introspect"}
                        },
                        "required": ["library_name", "version"]
                    }
                ),
                Tool(
                    name="calculate_importance_score",
                    description=(
                        "Calculate importance score (0-10) for an API based on heuristics. "
                        "Considers: presence in __all__ (+3), has docstring (+2), not private (+1), "
                        "top-level module (+1), common naming pattern (+1). Returns tier classification."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "api": {"type": "string", "description": "API name (e.g., 'lancedb.connect')"},
                            "module": {"type": "string", "description": "Module name"},
                            "type": {"type": "string", "description": "API type: function, class, method, property"},
                            "has_docstring": {"type": "boolean", "description": "Whether API has docstring"},
                            "in_all": {"type": "boolean", "description": "Whether API is in module's __all__"}
                        },
                        "required": ["api", "module", "type", "has_docstring", "in_all"]
                    }
                ),
                Tool(
                    name="classify_coverage",
                    description=(
                        "Classify coverage tier for an API (0-3). "
                        "0=undocumented, 1=mentioned in signatures, 2=has code example, 3=dedicated section"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "api": {"type": "string", "description": "API name"},
                            "documented_in": {"type": "array", "items": {"type": "string"}, "description": "Pages mentioning this API"},
                            "appears_in_examples": {"type": "boolean", "description": "Whether API appears in code examples"},
                            "has_dedicated_section": {"type": "boolean", "description": "Whether API has dedicated section"}
                        },
                        "required": ["api", "documented_in", "appears_in_examples", "has_dedicated_section"]
                    }
                ),
                Tool(
                    name="calculate_metrics",
                    description=(
                        "Calculate overall coverage metrics from coverage data. "
                        "Returns percentages for documented, with examples, and complete coverage."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "coverage_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "api": {"type": "string"},
                                        "tier": {"type": "integer"},
                                        "documented_in": {"type": "array", "items": {"type": "string"}},
                                        "has_examples": {"type": "boolean"},
                                        "has_dedicated_section": {"type": "boolean"}
                                    }
                                },
                                "description": "Coverage tier data for all APIs"
                            }
                        },
                        "required": ["coverage_data"]
                    }
                ),
                Tool(
                    name="prioritize_undocumented",
                    description=(
                        "Prioritize undocumented APIs by importance score. "
                        "Returns ranked list with top priorities first."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "undocumented_apis": {"type": "array", "items": {"type": "string"}, "description": "List of undocumented API names"},
                            "importance_scores": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "api": {"type": "string"},
                                        "score": {"type": "integer"},
                                        "tier": {"type": "string"},
                                        "reasons": {"type": "array", "items": {"type": "string"}}
                                    }
                                },
                                "description": "Map of API name to importance score data"
                            }
                        },
                        "required": ["undocumented_apis", "importance_scores"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "introspect_library":
                    return await self._handle_introspect_library(arguments)
                elif name == "calculate_importance_score":
                    return await self._handle_calculate_importance(arguments)
                elif name == "classify_coverage":
                    return await self._handle_classify_coverage(arguments)
                elif name == "calculate_metrics":
                    return await self._handle_calculate_metrics(arguments)
                elif name == "prioritize_undocumented":
                    return await self._handle_prioritize_undocumented(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error in {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_introspect_library(self, arguments: Dict) -> list[TextContent]:
        """Handle introspect_library tool call."""
        library_name = arguments["library_name"]
        version = arguments["version"]
        modules = arguments.get("modules", [library_name])

        logger.info(f"Introspecting {library_name}=={version}")

        # Create temporary venv
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"

            # Install library
            success, message = install_library(library_name, version, venv_path)
            if not success:
                return [TextContent(type="text", text=json.dumps({"error": message}))]

            # Add venv to path
            python_path = venv_path / "bin" / "python"

            # Introspect each module
            all_apis = []
            for module_name in modules:
                apis = introspect_module(module_name)
                all_apis.extend(apis)

            # Convert to JSON
            result = {
                "library": library_name,
                "version": version,
                "total_apis": len(all_apis),
                "apis": [api.model_dump() for api in all_apis],
                "by_type": {
                    "function": sum(1 for a in all_apis if a.type == "function"),
                    "class": sum(1 for a in all_apis if a.type == "class"),
                    "method": sum(1 for a in all_apis if a.type == "method")
                },
                "deprecated_count": sum(1 for a in all_apis if a.is_deprecated)
            }

            logger.info(f"Found {len(all_apis)} APIs in {library_name}")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _handle_calculate_importance(self, arguments: Dict) -> list[TextContent]:
        """Handle calculate_importance_score tool call."""
        api_metadata = APIMetadata(**arguments)
        score = calculate_importance(api_metadata)
        return [TextContent(type="text", text=json.dumps(score.model_dump(), indent=2))]

    async def _handle_classify_coverage(self, arguments: Dict) -> list[TextContent]:
        """Handle classify_coverage tool call."""
        tier = classify_coverage_tier(
            api=arguments["api"],
            documented_in=arguments["documented_in"],
            appears_in_examples=arguments["appears_in_examples"],
            has_dedicated_section=arguments["has_dedicated_section"]
        )
        return [TextContent(type="text", text=json.dumps(tier.model_dump(), indent=2))]

    async def _handle_calculate_metrics(self, arguments: Dict) -> list[TextContent]:
        """Handle calculate_metrics tool call."""
        coverage_data = [CoverageTier(**item) for item in arguments["coverage_data"]]
        metrics = calculate_coverage_metrics(coverage_data)
        return [TextContent(type="text", text=json.dumps(metrics.model_dump(), indent=2))]

    async def _handle_prioritize_undocumented(self, arguments: Dict) -> list[TextContent]:
        """Handle prioritize_undocumented tool call."""
        undocumented = arguments["undocumented_apis"]
        importance_scores = {
            k: ImportanceScore(**v) for k, v in arguments["importance_scores"].items()
        }

        prioritized = prioritize_undocumented_apis(undocumented, importance_scores)
        return [TextContent(type="text", text=json.dumps(prioritized, indent=2))]


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    server = APICompletenessMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        logger.info("API Completeness MCP Server started")
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
