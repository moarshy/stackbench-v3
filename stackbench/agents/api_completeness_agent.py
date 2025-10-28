"""
API Completeness & Deprecation Agent - Analyzes documentation coverage and deprecated API usage.

This agent uses Claude Code to:
1. Discover all public APIs in the library via introspection
2. Aggregate documented APIs from all extraction results
3. Calculate tiered coverage (mentioned, has example, dedicated section)
4. Identify deprecated APIs still taught in documentation
5. Rank undocumented APIs by importance

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

COMPLETENESS_SYSTEM_PROMPT = """You are an expert Python library introspection and documentation analysis specialist.

Your task is to analyze the completeness of library documentation by:
1. Discovering all public APIs in the library (via inspect module)
2. Aggregating what's documented across all doc pages
3. Calculating tiered coverage metrics
4. Identifying deprecated APIs still taught in docs
5. Ranking undocumented APIs by importance

Core capabilities:
- Library introspection using inspect, ast, and warnings modules
- Deprecation detection (@deprecated decorators, DeprecationWarning patterns)
- Coverage tier classification (0=undocumented, 1=mentioned, 2=has_example, 3=dedicated_section)
- Importance scoring (based on __all__, docstrings, module level, naming patterns)
- Cross-referencing library APIs with documentation

You are thorough, precise, and provide actionable insights for improving documentation coverage."""

ANALYSIS_PROMPT = """Analyze the completeness of documentation for this library.

Library: {library}
Version: {version}
Language: {language}

TASK OVERVIEW:
This is a 3-phase analysis combining library introspection with documentation coverage assessment.

===============================================================================
PHASE 1: DISCOVER LIBRARY API SURFACE
===============================================================================

1. Install the library:
   ```bash
   pip install {library}=={version}
   ```

2. Introspect the library to find ALL public APIs:
   ```python
   import inspect
   import warnings
   import {library}

   # Discover public APIs
   # - Functions, classes, methods in public modules
   # - Check __all__ declarations
   # - Exclude private (underscore-prefixed) unless in __all__
   # - Get metadata: async, docstring, module path
   ```

3. Detect deprecated APIs:
   - Check for @deprecated decorators
   - Scan for DeprecationWarning in source/docstrings
   - Parse deprecation messages for:
     * Version when deprecated
     * Alternative API to use
   - Use warnings.catch_warnings() during import

4. Calculate importance score for each API (0-10):
   - In __all__: +3 points
   - Has docstring: +2 points
   - Not underscore-prefixed: +1 point
   - Top-level module: +1 point
   - Common name patterns (connect, create, get, etc.): +1 point
   - Classification: high (>6), medium (3-6), low (<3)

5. Group APIs by module and type (function, class, method, property)

===============================================================================
PHASE 2: AGGREGATE DOCUMENTATION COVERAGE
===============================================================================

6. Read all extraction results from: {extraction_folder}
   - Find all *_analysis.json files
   - Load each and aggregate:
     * signatures array (documented API signatures)
     * examples array (code examples)
     * page name

7. For each extraction file, track which APIs are documented:
   - **Tier 1 (Mentioned)**: API appears in signatures list
   - **Tier 2 (Has Example)**: API appears in code examples
   - **Tier 3 (Dedicated Section)**: API has context/section indicating it's the focus

8. Build comprehensive map:
   - For each documented API: which pages, what tier, has examples?
   - Handle variations: "lancedb.connect" vs "connect" vs "db = lancedb.connect(...)"

===============================================================================
PHASE 3: CROSS-REFERENCE & ANALYZE
===============================================================================

9. Cross-reference library APIs with documented APIs:
   - For each library API:
     * Coverage tier (0-3)
     * Which pages document it
     * Has code examples?
     * Has dedicated section?

10. Identify undocumented APIs (tier 0):
    - Rank by importance score
    - Include reason for importance
    - Top N most important undocumented APIs

11. Identify deprecated APIs in docs:
    - Cross-check deprecated library APIs with documented APIs
    - For each: severity (critical if deprecated in target version)
    - Suggest alternatives
    - Which pages need updating

12. Calculate summary metrics:
    - Total public APIs
    - Documented (tier >= 1)
    - With examples (tier >= 2)
    - With dedicated sections (tier == 3)
    - Undocumented (tier == 0)
    - Coverage percentages
    - Deprecated count

===============================================================================
OUTPUT FORMAT - JSON ONLY
===============================================================================

Respond with ONLY the JSON object below. No explanatory text before or after.

```json
{{
  "api_surface": {{
    "total_public_apis": 45,
    "by_module": {{
      "{library}": ["connect", "connect_async", ...],
      "{library}.db": ["Database.create_table", "Database.open_table", ...]
    }},
    "by_type": {{
      "function": 15,
      "class": 5,
      "method": 20,
      "property": 5
    }},
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
      "api": "{library}.Database.drop_table",
      "module": "{library}.db",
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
      "api": "{library}.old_connect",
      "module": "{library}",
      "deprecated_since": "0.24.0",
      "alternative": "{library}.connect",
      "documented_in": ["quickstart.md", "tutorial.md"],
      "severity": "critical",
      "deprecation_message": "old_connect is deprecated, use connect instead",
      "suggestion": "Replace old_connect with connect in quickstart.md and tutorial.md"
    }}
  ],
  "api_details": [
    {{
      "api": "{library}.connect",
      "module": "{library}",
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
- Be exhaustive in API discovery - don't miss anything
- Use actual Python code execution for introspection
- Handle edge cases: method chains, properties, class methods, async functions
- Provide actionable insights, not just data
- If you encounter errors, document them in warnings array
"""


# ============================================================================
# AGENT
# ============================================================================

class APICompletenessAgent:
    """Agent that analyzes documentation completeness and deprecated API usage."""

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

        print(f"🔍 API Completeness Agent initialized")
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
        Analyze API completeness and deprecated usage across all documentation.

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

        # Create options
        options = ClaudeAgentOptions(
            system_prompt=COMPLETENESS_SYSTEM_PROMPT,
            allowed_tools=["Read", "Write", "Bash"],
            permission_mode="acceptEdits",
            hooks=hooks,
            cwd=str(Path.cwd())
        )

        async with ClaudeSDKClient(options=options) as client:
            prompt = ANALYSIS_PROMPT.format(
                library=self.library_name,
                version=self.library_version,
                language=self.language,
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
                # Extract environment info (should be in response or we can query)
                # For now, create minimal environment info
                environment = EnvironmentInfo(
                    library_installed=self.library_name,
                    version_installed=self.library_version,
                    version_requested=self.library_version,
                    version_match=True,
                    python_version="3.11"  # Should be extracted from bash output
                )

                # Parse API surface
                api_surface_data = analysis_data.get("api_surface", {})
                api_surface = APISurfaceSummary(
                    total_public_apis=api_surface_data.get("total_public_apis", 0),
                    by_module=api_surface_data.get("by_module", {}),
                    by_type=api_surface_data.get("by_type", {}),
                    deprecated_count=api_surface_data.get("deprecated_count", 0)
                )

                # Parse coverage summary
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

                # Parse undocumented APIs
                undocumented_apis = [
                    UndocumentedAPI(**api_data)
                    for api_data in analysis_data.get("undocumented_apis", [])
                ]

                # Parse deprecated in docs
                deprecated_in_docs = [
                    DeprecatedInDocs(**dep_data)
                    for dep_data in analysis_data.get("deprecated_in_docs", [])
                ]

                # Parse API details
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

                return output

            except Exception as e:
                warnings_list.append(f"Failed to parse completeness data into Pydantic models: {e}")
                print(f"   ⚠️  Pydantic validation error: {e}")

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


# This module is designed to be used as a library.
# For CLI usage, see stackbench.cli module.
