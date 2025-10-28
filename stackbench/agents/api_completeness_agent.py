"""
API Completeness & Deprecation Agent - Analyzes documentation coverage and deprecated API usage.

This agent uses Claude Code + MCP Server for deterministic analysis:
- Agent (qualitative): Reads extraction files, understands doc structure
- MCP Server (deterministic): Library introspection, importance scoring, coverage calculation

Architecture:
- MCP Server handles: pip install, inspect module, importance heuristics
- Agent handles: Reading extractions, matching APIs to docs, building output

Key difference from other agents: Takes entire doc folder as input, not individual docs.
"""

import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Import centralized schemas
from stackbench.schemas import (
    APICompletenessOutput,
    APISurfaceSummary,
    CoverageSummary,
    UndocumentedAPI,
    DeprecatedInDocs,
    APIDetail,
    APIMetadata,
    EnvironmentInfo
)


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

COMPLETENESS_SYSTEM_PROMPT = """You are an expert documentation completeness analyzer with access to deterministic API analysis tools.

Your role is to assess documentation coverage by:
1. Using MCP tools to discover library APIs (deterministic introspection)
2. Reading extraction files to understand what's documented
3. Matching documented APIs to library APIs
4. Building comprehensive completeness reports

**Available MCP Tools:**
- `introspect_library(library, version)` - Returns all public APIs via inspect module
- `calculate_importance_score(api_metadata)` - Scores API importance (0-10)
- `classify_coverage(api, documented_in, ...)` - Classifies coverage tier (0-3)
- `calculate_metrics(coverage_data)` - Computes coverage percentages
- `prioritize_undocumented(apis, scores)` - Ranks undocumented APIs

**Your Tasks:**
1. Call MCP to introspect the library (get all APIs)
2. Read extraction files from {extraction_folder}
3. For each library API, determine if it's documented and how
4. Call MCP to calculate importance scores
5. Call MCP to classify coverage tiers
6. Call MCP to calculate metrics
7. Call MCP to prioritize gaps
8. Build final JSON output

**Coverage Tiers:**
- Tier 0: Undocumented (not mentioned anywhere)
- Tier 1: Mentioned (appears in signature lists)
- Tier 2: Has Example (appears in code examples)
- Tier 3: Dedicated Section (has its own heading/context)

**Importance Scoring (done by MCP):**
- In __all__: +3 points
- Has docstring: +2 points
- Not underscore-prefixed: +1 point
- Top-level module: +1 point
- Common naming pattern: +1 point
- Tiers: high (7-10), medium (4-6), low (0-3)

You focus on understanding documentation structure. Let MCP handle deterministic calculations."""

ANALYSIS_PROMPT = """Analyze documentation completeness for this library.

Library: {library}
Version: {version}
Extraction Folder: {extraction_folder}

**WORKFLOW:**

STEP 1: Introspect Library (MCP)
================================
Call the `introspect_library` MCP tool to get all public APIs:
- library_name: "{library}"
- version: "{version}"
- modules: ["{library}"]  # Add more if multi-module

This returns:
{{
  "apis": [
    {{"api": "lancedb.connect", "module": "lancedb", "type": "function", ...}},
    ...
  ],
  "deprecated_count": N
}}

STEP 2: Read Extraction Files
==============================
Read all *_analysis.json files from: {extraction_folder}

For each file, extract:
- signatures: List of documented API signatures
- examples: List of code examples
- document_page: Page name

Build a map of:
- Which APIs appear in signatures (tier 1)
- Which APIs appear in code examples (tier 2)
- Which APIs have dedicated context/sections (tier 3)

Look for patterns like:
- Signature in list: "lancedb.connect(uri, ...)" → mentioned
- In code example: "db = lancedb.connect(...)" → has example
- Has section heading: "## Connecting to LanceDB" with content about connect() → dedicated

STEP 3: Calculate Importance Scores (MCP)
==========================================
For each API from Step 1, call `calculate_importance_score` with:
- api: API name
- module: Module name
- type: function/class/method
- has_docstring: boolean
- in_all: boolean

Store importance scores for later.

STEP 4: Classify Coverage (MCP)
================================
For each API, call `classify_coverage` with:
- api: API name
- documented_in: List of pages mentioning it
- appears_in_examples: boolean
- has_dedicated_section: boolean

Store coverage tiers.

STEP 5: Calculate Metrics (MCP)
================================
Call `calculate_metrics` with all coverage tier data:
- coverage_data: Array of {{"api": "...", "tier": N, ...}}

This returns overall percentages.

STEP 6: Prioritize Undocumented (MCP)
======================================
Filter APIs with tier 0, call `prioritize_undocumented` with:
- undocumented_apis: List of undocumented API names
- importance_scores: Map of scores from Step 3

This returns ranked list of what to document next.

STEP 7: Build Output JSON
==========================
Respond with ONLY this JSON structure (no explanatory text):

```json
{{
  "api_surface": {{
    "total_public_apis": 45,
    "by_module": {{"lancedb": [...], "lancedb.db": [...]}},
    "by_type": {{"function": 15, "class": 5, "method": 20}},
    "deprecated_count": 3
  }},
  "coverage_summary": {{
    "total_apis": 45,
    "documented": 32,
    "with_examples": 28,
    "with_dedicated_sections": 15,
    "undocumented": 13,
    "coverage_percentage": 71.1,
    "example_coverage_percentage": 62.2,
    "complete_coverage_percentage": 33.3
  }},
  "undocumented_apis": [
    {{
      "api": "lancedb.Database.drop_table",
      "module": "lancedb.db",
      "type": "method",
      "importance": "high",
      "importance_score": 8,
      "reason": "In __all__, has docstring, common CRUD operation",
      "has_docstring": true,
      "is_async": false
    }}
  ],
  "deprecated_in_docs": [
    {{
      "api": "lancedb.old_connect",
      "module": "lancedb",
      "deprecated_since": "0.24.0",
      "alternative": "lancedb.connect",
      "documented_in": ["quickstart.md"],
      "severity": "critical",
      "deprecation_message": "old_connect is deprecated, use connect instead",
      "suggestion": "Replace old_connect with connect in quickstart.md"
    }}
  ],
  "api_details": [
    {{
      "api": "lancedb.connect",
      "module": "lancedb",
      "type": "function",
      "is_deprecated": false,
      "coverage_tier": 3,
      "documented_in": ["quickstart.md", "api-reference.md"],
      "has_examples": true,
      "has_dedicated_section": true,
      "importance": "high",
      "importance_score": 9
    }}
  ]
}}
```

IMPORTANT:
- Use MCP tools for ALL calculations (importance, coverage, metrics)
- Your job: Read files, match patterns, orchestrate MCP calls
- Be exhaustive in API discovery
- Document any warnings/errors encountered
"""


# ============================================================================
# AGENT
# ============================================================================

class APICompletenessAgent:
    """Agent that analyzes documentation completeness using MCP server."""

    def __init__(
        self,
        extraction_folder: Path,
        output_folder: Path,
        library_name: str,
        library_version: str,
        language: str = "python",
        validation_log_dir: Optional[Path] = None
    ):
        """
        Initialize the completeness agent.

        Args:
            extraction_folder: Path to folder with all extraction results
            output_folder: Path to save completeness analysis
            library_name: Name of library to analyze
            library_version: Version to install and analyze
            language: Programming language (default: python)
            validation_log_dir: Optional directory for validation hook tracking logs
        """
        self.extraction_folder = Path(extraction_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.library_name = library_name
        self.library_version = library_version
        self.language = language
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        print(f"🔍 API Completeness Agent initialized (with MCP)")
        print(f"   Library: {library_name} v{library_version}")
        print(f"   Extraction files: {extraction_folder}")

        if self.validation_log_dir:
            print(f"   Logging enabled: {self.validation_log_dir}")

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Claude's response, handling markdown code blocks."""
        try:
            # Strategy 1: Try to find JSON in markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
                return json.loads(json_text)
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
                return json.loads(json_text)

            # Strategy 2: Look for JSON object markers
            start_idx = response_text.find('{')
            if start_idx != -1:
                brace_count = 0
                in_string = False
                escape_next = False

                for i in range(start_idx, len(response_text)):
                    char = response_text[i]

                    if escape_next:
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        continue

                    if char == '"':
                        in_string = not in_string
                        continue

                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_text = response_text[start_idx:i+1]
                                return json.loads(json_text)

            # Strategy 3: Try parsing the whole response
            return json.loads(response_text.strip())

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            return None

    async def get_claude_response(self, client: ClaudeSDKClient, prompt: str, messages_log_file=None) -> str:
        """Send prompt to Claude and get text response, logging all messages."""
        # Log the user prompt
        if messages_log_file:
            user_message_entry = {
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": prompt
            }
            with open(messages_log_file, 'a') as f:
                f.write(json.dumps(user_message_entry) + '\n')

        await client.query(prompt)

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                # Log the full assistant message
                if messages_log_file:
                    message_content = []
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            message_content.append({
                                "type": "text",
                                "text": block.text
                            })
                            response_text += block.text
                        else:
                            message_content.append({
                                "type": type(block).__name__,
                                "data": str(block)
                            })

                    assistant_message_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "role": "assistant",
                        "content": message_content
                    }
                    with open(messages_log_file, 'a') as f:
                        f.write(json.dumps(assistant_message_entry) + '\n')
                else:
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

        return response_text

    async def analyze_completeness(self) -> APICompletenessOutput:
        """
        Analyze API completeness using MCP server for deterministic operations.

        Returns:
            APICompletenessOutput with coverage metrics and deprecated API warnings
        """
        start_time = datetime.now()
        warnings_list = []

        # Create logger
        from stackbench.hooks import create_agent_hooks, AgentLogger

        messages_log_file = None
        if self.validation_log_dir:
            completeness_logs_dir = self.validation_log_dir / "api_completeness_logs"
            completeness_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = completeness_logs_dir / "agent.log"
            tools_log = completeness_logs_dir / "tools.jsonl"
            messages_log_file = completeness_logs_dir / "messages.jsonl"
            logger = AgentLogger(agent_log, tools_log)
        else:
            logger = None

        # Create hooks
        hooks = create_agent_hooks(
            agent_type="api_completeness",
            logger=logger,
            output_dir=self.output_folder,
            validation_log_dir=self.validation_log_dir
        )

        # Create options with MCP server
        options = ClaudeAgentOptions(
            system_prompt=COMPLETENESS_SYSTEM_PROMPT,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            hooks=hooks,
            cwd=str(Path.cwd()),
            mcp_servers={
                "api-completeness": {
                    "command": "python",
                    "args": ["-m", "stackbench.mcp_servers.api_completeness_server"],
                }
            }
        )

        async with ClaudeSDKClient(options=options) as client:
            prompt = ANALYSIS_PROMPT.format(
                library=self.library_name,
                version=self.library_version,
                extraction_folder=str(self.extraction_folder)
            )

            response_text = await self.get_claude_response(client, prompt, messages_log_file)
            analysis_data = self.extract_json_from_response(response_text)

            if not analysis_data:
                warnings_list.append("Failed to parse completeness analysis response")
                # Return minimal result
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return APICompletenessOutput(
                    analysis_id=str(uuid.uuid4()),
                    analyzed_at=datetime.now().isoformat(),
                    library=self.library_name,
                    version=self.library_version,
                    language=self.language,
                    api_surface=APISurfaceSummary(
                        total_public_apis=0,
                        by_module={},
                        by_type={},
                        deprecated_count=0
                    ),
                    coverage_summary=CoverageSummary(
                        total_apis=0,
                        documented=0,
                        with_examples=0,
                        with_dedicated_sections=0,
                        undocumented=0,
                        coverage_percentage=0.0,
                        example_coverage_percentage=0.0,
                        complete_coverage_percentage=0.0
                    ),
                    undocumented_apis=[],
                    deprecated_in_docs=[],
                    api_details=[],
                    environment=EnvironmentInfo(
                        library_installed=self.library_name,
                        version_installed="unknown",
                        version_requested=self.library_version,
                        version_match=False,
                        python_version="unknown"
                    ),
                    processing_time_ms=processing_time,
                    warnings=warnings_list
                )

            # Parse into Pydantic models
            try:
                environment = EnvironmentInfo(
                    library_installed=self.library_name,
                    version_installed=self.library_version,
                    version_requested=self.library_version,
                    version_match=True,
                    python_version="3.11"
                )

                api_surface_data = analysis_data.get("api_surface", {})
                api_surface = APISurfaceSummary(
                    total_public_apis=api_surface_data.get("total_public_apis", 0),
                    by_module=api_surface_data.get("by_module", {}),
                    by_type=api_surface_data.get("by_type", {}),
                    deprecated_count=api_surface_data.get("deprecated_count", 0)
                )

                coverage_data = analysis_data.get("coverage_summary", {})
                coverage_summary = CoverageSummary(
                    total_apis=coverage_data.get("total_apis", 0),
                    documented=coverage_data.get("documented", 0),
                    with_examples=coverage_data.get("with_examples", 0),
                    with_dedicated_sections=coverage_data.get("with_dedicated_sections", 0),
                    undocumented=coverage_data.get("undocumented", 0),
                    coverage_percentage=coverage_data.get("coverage_percentage", 0.0),
                    example_coverage_percentage=coverage_data.get("example_coverage_percentage", 0.0),
                    complete_coverage_percentage=coverage_data.get("complete_coverage_percentage", 0.0)
                )

                undocumented_apis = [
                    UndocumentedAPI(**api_data)
                    for api_data in analysis_data.get("undocumented_apis", [])
                ]

                deprecated_in_docs = [
                    DeprecatedInDocs(**dep_data)
                    for dep_data in analysis_data.get("deprecated_in_docs", [])
                ]

                api_details = [
                    APIDetail(**detail_data)
                    for detail_data in analysis_data.get("api_details", [])
                ]

                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

                output = APICompletenessOutput(
                    analysis_id=str(uuid.uuid4()),
                    analyzed_at=datetime.now().isoformat(),
                    library=self.library_name,
                    version=self.library_version,
                    language=self.language,
                    api_surface=api_surface,
                    coverage_summary=coverage_summary,
                    undocumented_apis=undocumented_apis,
                    deprecated_in_docs=deprecated_in_docs,
                    api_details=api_details,
                    environment=environment,
                    processing_time_ms=processing_time,
                    warnings=warnings_list
                )

                # Save output
                output_file = self.output_folder / "completeness_analysis.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output.model_dump_json(indent=2))

                print(f"✅ Analysis complete: {output_file}")
                return output

            except Exception as e:
                warnings_list.append(f"Failed to parse completeness data into Pydantic models: {e}")
                print(f"   ⚠️  Pydantic validation error: {e}")

                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return APICompletenessOutput(
                    analysis_id=str(uuid.uuid4()),
                    analyzed_at=datetime.now().isoformat(),
                    library=self.library_name,
                    version=self.library_version,
                    language=self.language,
                    api_surface=APISurfaceSummary(
                        total_public_apis=0,
                        by_module={},
                        by_type={},
                        deprecated_count=0
                    ),
                    coverage_summary=CoverageSummary(
                        total_apis=0,
                        documented=0,
                        with_examples=0,
                        with_dedicated_sections=0,
                        undocumented=0,
                        coverage_percentage=0.0,
                        example_coverage_percentage=0.0,
                        complete_coverage_percentage=0.0
                    ),
                    undocumented_apis=[],
                    deprecated_in_docs=[],
                    api_details=[],
                    environment=EnvironmentInfo(
                        library_installed=self.library_name,
                        version_installed="unknown",
                        version_requested=self.library_version,
                        version_match=False,
                        python_version="unknown"
                    ),
                    processing_time_ms=processing_time,
                    warnings=warnings_list
                )


# This module is designed to be used as a library.
# For CLI usage, see stackbench.cli module.
