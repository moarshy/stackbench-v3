"""
API Completeness & Deprecation Agent - Analyzes documentation coverage and deprecated API usage.

This agent uses Claude Code + MCP Server for deterministic analysis:
- Agent (qualitative): Reads extraction files, understands doc structure, runs introspection via Bash
- MCP Server (deterministic): Importance scoring, coverage classification, metrics calculation

Architecture:
- Agent handles: Library installation, introspection (via Bash templates), reading extractions, matching APIs
- MCP Server handles: Importance scoring heuristics, coverage tier classification, metrics calculation
- Introspection templates: Language-specific scripts (Python, JS, TS) that output standardized JSON

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
1. Installing library and running introspection via Bash
2. Reading extraction files to understand what's documented
3. Matching documented APIs to library APIs
4. Using MCP tools for scoring and metrics
5. Building comprehensive completeness reports

**Introspection Templates:**
- Located in `stackbench/introspection_templates/`
- Language-specific scripts (python_introspect.py, js_introspect.js, ts_introspect.ts)
- Output standardized JSON format (apis, by_type, deprecated_count)
- Execute via Bash in your environment (not MCP subprocess)

**Available MCP Tools (computation only):**
- `calculate_importance_score(api_metadata)` - Scores API importance (0-10)
- `classify_coverage(api, documented_in, ...)` - Classifies coverage tier (0-3)
- `calculate_metrics(coverage_data)` - Computes coverage percentages
- `prioritize_undocumented(apis, scores)` - Ranks undocumented APIs

**Your Tasks:**
1. Install library via pip (Bash command)
2. Run introspection template via Bash, read JSON output
3. Read extraction files from {extraction_folder}
4. For each library API, determine if it's documented and how
5. Call MCP to calculate importance scores
6. Call MCP to classify coverage tiers
7. Call MCP to calculate metrics
8. Call MCP to prioritize gaps
9. Build final JSON output

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

You focus on running introspection and understanding documentation structure. Let MCP handle deterministic calculations."""

ANALYSIS_PROMPT = """Analyze documentation completeness for this library.

Library: {library}
Version: {version}
Extraction Folder: {extraction_folder}
Language: {language}

**WORKFLOW:**

STEP 0: Install Library (Bash Command)
=======================================
Use Bash to install the library in your current environment:

For Python:
```bash
pip install {library}=={version}
```

For JavaScript/TypeScript:
```bash
npm install {library}@{version}
```

Wait for successful installation before proceeding to STEP 1.

STEP 1: Introspect Library (Bash + Introspection Template)
===========================================================
**For Python libraries:**

1. Copy the Python introspection template to /tmp:
   ```bash
   cp stackbench/introspection_templates/python_introspect.py /tmp/introspect_{library}.py
   ```

2. Execute the template with your library:
   ```bash
   python /tmp/introspect_{library}.py {library} {version} > /tmp/introspection_result.json
   ```

3. Read the JSON output:
   ```bash
   cat /tmp/introspection_result.json
   ```

The output will be standardized JSON:
{{
  "library": "{library}",
  "version": "{version}",
  "language": "python",
  "total_apis": 118,
  "apis": [
    {{
      "api": "lancedb.connect",
      "module": "lancedb",
      "type": "function",
      "is_async": false,
      "has_docstring": true,
      "in_all": true,
      "is_deprecated": false,
      "signature": "(uri, *, api_key=None, ...)"
    }},
    ...
  ],
  "by_type": {{"function": 5, "class": 11, "method": 102}},
  "deprecated_count": 3
}}

**For JavaScript/TypeScript libraries:**
(Future: Use js_introspect.js or ts_introspect.ts templates)

STEP 2: Read Extraction Files and BUILD RICH REFERENCES
========================================================
Read all *_analysis.json files from: {extraction_folder}

For each file, extract:
- signatures: List of documented API signatures
- examples: List of code examples
- document_page: Page name

For EACH API found, create DocumentationReference objects with rich context:

**From signatures:**
{{
  "document": "pandas_and_pyarrow.md",
  "section_hierarchy": sig["section_hierarchy"],  # e.g., ["Pandas and PyArrow", "Create dataset"]
  "markdown_anchor": sig["markdown_anchor"],       # e.g., "#create-dataset"
  "line_number": sig["line"],                      # e.g., 50
  "context_type": "signature",
  "code_block_index": sig.get("code_block_index"), # e.g., 0
  "raw_context": sig["context"]                    # e.g., "Create dataset - connecting to LanceDB"
}}

**From code examples (parse code to find API calls):**
{{
  "document": "pandas_and_pyarrow.md",
  "section_hierarchy": example["section_hierarchy"],
  "markdown_anchor": example["markdown_anchor"],
  "line_number": example["line"],
  "context_type": "example",
  "code_block_index": example.get("code_block_index"),
  "raw_context": example["context"]
}}

Build a map of:
- api_id → List[DocumentationReference]
- Which APIs appear where (document, line, section, type)

From these references, derive:
- documented_in: unique list of documents
- has_examples: any reference with context_type="example"
- has_dedicated_section: check if section_hierarchy indicates dedicated API section

STEP 3: Calculate Importance Scores (MCP Tool)
===============================================
For each API from Step 1, call the MCP `calculate_importance_score` tool with:
- api: API name (e.g., "lancedb.connect")
- module: Module name (e.g., "lancedb")
- type: function/class/method
- has_docstring: boolean (from introspection JSON)
- in_all: boolean (from introspection JSON)

The MCP tool returns:
{{
  "api": "lancedb.connect",
  "score": 9,
  "tier": "high",
  "reasons": ["In __all__", "Has documentation", "Public API", "Common API pattern: connect"],
  "breakdown": {{"in_all": 3, "has_docstring": 2, "not_private": 1, "common_name": 1}}
}}

Store importance scores for later steps.

STEP 4: Classify Coverage (MCP Tool)
=====================================
For each API, call the MCP `classify_coverage` tool with:
- api: API name
- documented_in: List of pages mentioning it (from Step 2)
- appears_in_examples: boolean (from Step 2)
- has_dedicated_section: boolean (from Step 2)

The MCP tool returns:
{{
  "api": "lancedb.connect",
  "tier": 3,
  "documented_in": ["quickstart.md", "pandas_and_pyarrow.md"],
  "has_examples": true,
  "has_dedicated_section": true
}}

Store coverage tiers for all APIs.

STEP 5: Calculate Metrics (MCP Tool)
=====================================
Call the MCP `calculate_metrics` tool with all coverage tier data:
- coverage_data: Array of coverage tier objects from Step 4

The MCP tool returns:
{{
  "total_apis": 118,
  "documented": 89,
  "with_examples": 75,
  "with_dedicated_sections": 42,
  "undocumented": 29,
  "coverage_percentage": 75.4,
  "example_coverage_percentage": 63.6,
  "complete_coverage_percentage": 35.6
}}

STEP 6: Prioritize Undocumented (MCP Tool)
===========================================
Filter APIs with tier 0, call the MCP `prioritize_undocumented` tool with:
- undocumented_apis: List of undocumented API names (tier 0 from Step 4)
- importance_scores: Map of API name to ImportanceScore from Step 3

The MCP tool returns ranked list (sorted by importance score, descending):
[
  {{
    "api": "lancedb.Database.drop_table",
    "importance": "high",
    "importance_score": 8,
    "reasons": ["In __all__", "Has documentation", "Common CRUD operation"],
    "rank": 1
  }},
  ...
]

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
      "documentation_references": [
        {{
          "document": "pandas_and_pyarrow.md",
          "section_hierarchy": ["Pandas and PyArrow", "Create dataset"],
          "markdown_anchor": "#create-dataset",
          "line_number": 50,
          "context_type": "signature",
          "code_block_index": 0,
          "raw_context": "Create dataset - connecting to LanceDB database"
        }}
      ],
      "documented_in": ["pandas_and_pyarrow.md"],
      "has_examples": true,
      "has_dedicated_section": true,
      "importance": "high",
      "importance_score": 9
    }}
  ]
}}
```

IMPORTANT:
- Install library and run introspection via Bash (not MCP)
- Use MCP tools for ALL calculations (importance, coverage, metrics)
- Your job: Execute introspection, read files, match patterns, orchestrate MCP calls
- Be exhaustive in API discovery - expect 100+ APIs for large libraries
- Verify introspection output shows correct total_apis count before proceeding
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
        from stackbench.hooks import create_agent_hooks, create_logging_hooks, AgentLogger

        messages_log_file = None
        if self.validation_log_dir:
            completeness_logs_dir = self.validation_log_dir / "api_completeness_logs"
            completeness_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = completeness_logs_dir / "agent.log"
            tools_log = completeness_logs_dir / "tools.jsonl"
            messages_log_file = completeness_logs_dir / "messages.jsonl"
            logger = AgentLogger(agent_log, tools_log)

            # Create MCP-specific logging directory
            mcp_log_dir = completeness_logs_dir / "mcp"
            mcp_log_dir.mkdir(parents=True, exist_ok=True)

            mcp_logger = AgentLogger(
                log_file=mcp_log_dir / "mcp_agent.log",
                tools_log_file=mcp_log_dir / "mcp_tools.jsonl"
            )
            mcp_logging_hooks = create_logging_hooks(mcp_logger)
        else:
            logger = None
            mcp_logging_hooks = {'PreToolUse': [], 'PostToolUse': []}

        # Create hooks (combine validation + MCP logging)
        validation_hooks = create_agent_hooks(
            agent_type="api_completeness",
            logger=logger,
            output_dir=self.output_folder,
            validation_log_dir=self.validation_log_dir
        )

        # Merge validation hooks with MCP logging hooks
        hooks = {
            'PreToolUse': validation_hooks['PreToolUse'] + mcp_logging_hooks['PreToolUse'],
            'PostToolUse': validation_hooks['PostToolUse'] + mcp_logging_hooks['PostToolUse']
        }

        # Create options with MCP server
        import sys

        options = ClaudeAgentOptions(
            system_prompt=COMPLETENESS_SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            hooks=hooks,
            cwd=str(Path.cwd()),
            mcp_servers={
                "api-completeness": {
                    "command": sys.executable,  # Use same Python as current process
                    "args": ["-m", "stackbench.mcp_servers.api_completeness_server"],
                }
            }
        )

        async with ClaudeSDKClient(options=options) as client:
            prompt = ANALYSIS_PROMPT.format(
                library=self.library_name,
                version=self.library_version,
                extraction_folder=str(self.extraction_folder),
                language=self.language
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
