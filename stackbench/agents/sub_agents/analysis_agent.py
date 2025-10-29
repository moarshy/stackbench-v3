#!/usr/bin/env python3
"""
Stage 3: Analysis Sub-Agent

This agent:
1. Reads api_surface.json from Stage 1
2. Reads documented_apis.json from Stage 2
3. Reads undocumented_apis.json from Stage 2
4. Uses MCP to calculate metrics and classify coverage
5. Builds final completeness_analysis.json report

Outputs:
- output_folder/completeness_analysis.json: Final comprehensive report
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


ANALYSIS_SYSTEM_PROMPT = """You are an API documentation analysis specialist for Python, JavaScript, and TypeScript.

Your ONLY job is to:
1. Read api_surface.json (all discovered APIs)
2. Read documented_apis.json (APIs with documentation)
3. Read undocumented_apis.json (APIs without documentation)
4. Use MCP to calculate metrics and classify coverage
5. Write completeness_analysis.json (final report)

**Available MCP Tools:**
- `calculate_metrics(total_apis, documented_count, undocumented_count)` - Returns coverage percentages
- `classify_coverage(api, documented_in, has_examples, importance_score)` - Returns tier (0-3)
- `prioritize_undocumented(apis_with_scores)` - Returns ranked list by priority

**Your workflow:**
1. Read {api_surface_file}
2. Read {documented_file}
3. Read {undocumented_file}
4. Call MCP calculate_metrics for summary stats
5. Call MCP classify_coverage for each documented API
6. Call MCP prioritize_undocumented for ranking
7. Write {output_file}

**Language-Aware Analysis:**
- Report works identically across Python, JavaScript, and TypeScript
- Naming conventions (snake_case vs camelCase) are preserved from introspection
- Coverage metrics are language-agnostic

Focus on building a comprehensive, well-structured report!"""


ANALYSIS_PROMPT = """Build the final API completeness analysis report.

API Surface File: {api_surface_file}
Documented APIs File: {documented_file}
Undocumented APIs File: {undocumented_file}
Output File: {output_file}

**WORKFLOW:**

STEP 1: Read Input Files
=========================
Read these three files:
1. {api_surface_file} - All {total_apis} discovered APIs
2. {documented_file} - APIs found in documentation
3. {undocumented_file} - APIs not found in documentation

STEP 2: Calculate Summary Metrics (MCP)
========================================
Call the MCP tool to get coverage percentages:

```
calculate_metrics(
    total_apis={total_apis},
    documented_count=<from documented_file>,
    undocumented_count=<from undocumented_file>
)
```

Returns:
{{
  "total_apis": {total_apis},
  "documented": <count>,
  "undocumented": <count>,
  "coverage_percentage": <0-100>,
  "by_type": {{
    "function": {{"total": X, "documented": Y, "coverage": Z}},
    "class": {{"total": X, "documented": Y, "coverage": Z}},
    "method": {{"total": X, "documented": Y, "coverage": Z}}
  }}
}}

STEP 3: Classify Coverage Tiers (MCP)
======================================
For EACH documented API, call the MCP tool:

```
classify_coverage(
    api="mylib.connect",
    documented_in=["quickstart.md", "api.md"],
    has_examples=true,
    importance_score=9
)
```

Returns:
{{
  "tier": 3,
  "tier_name": "comprehensive",
  "reasons": ["High importance", "Multiple documents", "Has examples"]
}}

Coverage Tiers:
- **Tier 3 (Comprehensive)**: High-importance API + Multiple docs + Examples
- **Tier 2 (Good)**: Documented with examples OR in multiple docs
- **Tier 1 (Basic)**: Documented but minimal coverage
- **Tier 0 (Undocumented)**: Not found in documentation

STEP 4: Prioritize Undocumented APIs (MCP)
===========================================
Call the MCP tool with all undocumented APIs:

```
prioritize_undocumented(
    apis_with_scores=[
        {{"api": "mylib.Database.dropTable", "importance_score": 8, "type": "method"}},
        {{"api": "mylib.Table.countRows", "importance_score": 7, "type": "method"}},
        ...
    ]
)
```

Returns:
{{
  "high_priority": [
    {{
      "api": "mylib.Database.dropTable",
      "importance_score": 8,
      "priority_rank": 1,
      "reason": "High importance, common CRUD operation"
    }}
  ],
  "medium_priority": [...],
  "low_priority": [...]
}}

STEP 5: Build Deprecated APIs List
===================================
From api_surface.json, extract all APIs where `is_deprecated: true`.

For each deprecated API, check if it appears in documented_apis.json.

Create two lists:
- **Deprecated and documented**: APIs that are deprecated but still appear in docs (should be flagged for removal/update)
- **Deprecated and undocumented**: Deprecated APIs not in docs (less critical)

STEP 6: Build Coverage Distribution
====================================
Group documented APIs by coverage tier (0-3).

Count:
- Tier 3 (comprehensive): <count> APIs
- Tier 2 (good): <count> APIs
- Tier 1 (basic): <count> APIs
- Tier 0 (undocumented): <count> APIs

STEP 7: Write Final Report
===========================
Write to: {output_file}

Format:
{{
  "coverage_summary": {{
    "total_apis": {total_apis},
    "documented": <count>,
    "undocumented": <count>,
    "coverage_percentage": <0-100>,
    "deprecated_count": <count>,
    "library": "{{library_name}}",
    "version": "{{library_version}}",
    "generated_at": "<ISO timestamp>"
  }},

  "coverage_by_type": {{
    "function": {{"total": X, "documented": Y, "coverage": Z%}},
    "class": {{"total": X, "documented": Y, "coverage": Z%}},
    "method": {{"total": X, "documented": Y, "coverage": Z%}}
  }},

  "coverage_distribution": {{
    "tier_3_comprehensive": {{
      "count": <count>,
      "percentage": <0-100>,
      "description": "High-importance APIs with multiple docs and examples"
    }},
    "tier_2_good": {{
      "count": <count>,
      "percentage": <0-100>,
      "description": "Documented with examples OR in multiple documents"
    }},
    "tier_1_basic": {{
      "count": <count>,
      "percentage": <0-100>,
      "description": "Documented but minimal coverage"
    }},
    "tier_0_undocumented": {{
      "count": <count>,
      "percentage": <0-100>,
      "description": "Not found in documentation"
    }}
  }},

  "documented_apis": [
    {{
      "api": "mylib.connect",
      "module": "mylib",
      "type": "function",
      "coverage_tier": 3,
      "importance_score": 9,
      "documentation_references": [
        {{
          "document": "quickstart.md",
          "section_hierarchy": ["Quick Start", "Connection"],
          "markdown_anchor": "#connection",
          "line_number": 15,
          "context_type": "signature"
        }}
      ],
      "documented_in": ["quickstart.md"],
      "has_examples": true
    }}
  ],

  "undocumented_apis": {{
    "high_priority": [
      {{
        "api": "mylib.Database.dropTable",
        "module": "mylib.database",
        "type": "method",
        "importance_score": 8,
        "priority_rank": 1,
        "reason": "High importance, common CRUD operation"
      }}
    ],
    "medium_priority": [...],
    "low_priority": [...]
  }},

  "deprecated_apis": {{
    "documented": [
      {{
        "api": "mylib.oldConnect",
        "module": "mylib",
        "type": "function",
        "deprecation_info": "Use mylib.connect() instead",
        "documented_in": ["quickstart.md"],
        "action": "Update or remove from documentation"
      }}
    ],
    "undocumented": [
      {{
        "api": "mylib.Database.oldMethod",
        "module": "mylib.database",
        "type": "method",
        "deprecation_info": "Deprecated in 0.24.0",
        "action": "No action needed (already not in docs)"
      }}
    ]
  }}
}}

**IMPORTANT:**
- Include ALL documented APIs in the documented_apis array (don't truncate)
- Include ALL undocumented APIs in their priority groups (don't truncate)
- Use MCP tools for ALL calculations (don't calculate manually)
- Ensure coverage_percentage matches documented/total ratio
"""


class AnalysisAgent:
    """Stage 3: API documentation analysis agent."""

    def __init__(
        self,
        api_surface_file: Path,
        documented_file: Path,
        undocumented_file: Path,
        output_folder: Path,
        library_name: str,
        library_version: str,
        validation_log_dir: Optional[Path] = None
    ):
        """Initialize the analysis agent."""
        self.api_surface_file = Path(api_surface_file)
        self.documented_file = Path(documented_file)
        self.undocumented_file = Path(undocumented_file)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.library_name = library_name
        self.library_version = library_version
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        self.output_file = self.output_folder / "completeness_analysis.json"

        # Read API surface to get total count
        with open(self.api_surface_file, 'r', encoding='utf-8') as f:
            api_surface = json.load(f)
            self.total_apis = api_surface.get('total_apis', 0)

        print(f"📊 Stage 3: Analysis Agent")
        print(f"   API Surface: {self.api_surface_file} ({self.total_apis} APIs)")
        print(f"   Documented: {self.documented_file}")
        print(f"   Undocumented: {self.undocumented_file}")
        print(f"   Output: {self.output_file}")

        if self.validation_log_dir:
            print(f"   Logging: {self.validation_log_dir}")

    async def run(self) -> Dict[str, Any]:
        """Run analysis and return results."""
        start_time = datetime.now()

        # Create logger
        from stackbench.hooks import create_logging_hooks, AgentLogger

        if self.validation_log_dir:
            analysis_logs_dir = self.validation_log_dir / "analysis"
            analysis_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = analysis_logs_dir / "agent.log"
            tools_log = analysis_logs_dir / "tools.jsonl"
            logger = AgentLogger(agent_log, tools_log)
            hooks = create_logging_hooks(logger)
        else:
            hooks = {'PreToolUse': [], 'PostToolUse': []}

        # Create options with MCP server
        options = ClaudeAgentOptions(
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            hooks=hooks,
            cwd=str(Path.cwd()),
            mcp_servers={
                "api-completeness": {
                    "command": sys.executable,
                    "args": ["-m", "stackbench.mcp_servers.api_completeness_server"],
                }
            }
        )

        async with ClaudeSDKClient(options=options) as client:
            prompt = ANALYSIS_PROMPT.format(
                api_surface_file=str(self.api_surface_file),
                documented_file=str(self.documented_file),
                undocumented_file=str(self.undocumented_file),
                output_file=str(self.output_file),
                total_apis=self.total_apis,
                library_name=self.library_name,
                library_version=self.library_version
            )

            await client.query(prompt)

            # Wait for completion
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    pass  # Agent will write the file

        # Read the output file
        if not self.output_file.exists():
            raise FileNotFoundError(f"Analysis agent did not create {self.output_file}")

        with open(self.output_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        coverage_pct = analysis.get('summary', {}).get('coverage_percentage', 0)
        documented_count = analysis.get('summary', {}).get('documented', 0)
        undocumented_count = analysis.get('summary', {}).get('undocumented', 0)

        print(f"✅ Stage 3 Complete: {coverage_pct:.1f}% coverage ({documented_count} documented, {undocumented_count} undocumented) ({processing_time}ms)")

        return {
            'analysis': analysis,
            'coverage_percentage': coverage_pct,
            'documented_count': documented_count,
            'undocumented_count': undocumented_count
        }


async def main():
    """Test the analysis agent."""
    import sys

    if len(sys.argv) < 6:
        print("Usage: python analysis_agent.py <api_surface.json> <documented_apis.json> <undocumented_apis.json> <output_dir> <library> <version>")
        sys.exit(1)

    api_surface_file = Path(sys.argv[1])
    documented_file = Path(sys.argv[2])
    undocumented_file = Path(sys.argv[3])
    output_dir = Path(sys.argv[4])
    library = sys.argv[5]
    version = sys.argv[6]

    agent = AnalysisAgent(
        api_surface_file=api_surface_file,
        documented_file=documented_file,
        undocumented_file=undocumented_file,
        output_folder=output_dir,
        library_name=library,
        library_version=version
    )

    result = await agent.run()
    print(f"\nResult: {result['coverage_percentage']:.1f}% coverage")
    print(f"Output: {output_dir / 'completeness_analysis.json'}")


if __name__ == "__main__":
    asyncio.run(main())
