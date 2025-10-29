#!/usr/bin/env python3
"""
Stage 2: Matching Sub-Agent

This agent:
1. Reads api_surface.json from Stage 1
2. Reads ALL extraction files from extraction folder
3. Matches APIs to documentation (pattern matching)
4. Uses MCP to calculate importance scores
5. Writes documented_apis.json and undocumented_apis.json

Outputs:
- output_folder/documented_apis.json: APIs found in docs with references
- output_folder/undocumented_apis.json: APIs not found in docs with importance scores
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


MATCHING_SYSTEM_PROMPT = """You are an API documentation matching specialist for Python, JavaScript, and TypeScript.

Your job is to:
1. Read api_surface.json (all discovered APIs)
2. Run deterministic markdown_api_matcher.py script to find API mentions
3. Read api_matches.json (script output with fuzzy matches)
4. Use MCP to calculate importance scores for each API
5. Enrich documented APIs with extraction metadata (if available)
6. Write documented_apis.json and undocumented_apis.json

**Available MCP Tool:**
- `calculate_importance_score(api, module, type, has_docstring, in_all)` - Returns importance score (0-10) and tier (high/medium/low)

**Your workflow:**
1. Read {api_surface_file}
2. Run script: `python stackbench/introspection_templates/markdown_api_matcher.py {docs_folder} {api_surface_file} /tmp/api_matches.json {language}`
3. Read /tmp/api_matches.json
4. For each API, call MCP calculate_importance_score
5. Enrich documented APIs with extraction metadata (if available from {extraction_folder})
6. Write {documented_output_file}
7. Write {undocumented_output_file}

**The script handles:**
- Scanning ALL .md files in docs folder (fast, deterministic)
- Fuzzy matching (snake_case ↔ camelCase)
- Multi-language pattern matching

**You handle:**
- MCP importance scoring
- Metadata enrichment
- JSON output formatting

**Pattern Matching Tips (Multi-Language):**

**Python:**
- Exact API names: "mylib.connect()"
- Import patterns: "import mylib", "from mylib import connect"
- Method calls: "db.create_table()", "client.query()"
- Flexible with module prefixes

**JavaScript:**
- Require patterns: "const mylib = require('mylib')", "const {{ connect }} = require('mylib')"
- Method calls: "mylib.connect()", "db.createTable()"
- Property access: "client.database"

**TypeScript:**
- Import patterns: "import mylib from 'mylib'", "import {{ connect }} from 'mylib'"
- Type annotations: "const db: Database = ...", "function foo(client: Client)"
- Method calls with types: "db.createTable<T>()"

**Common Patterns:**
- Check class names, method names, function names
- Be flexible with naming conventions (snake_case in Python, camelCase in JS/TS)
- Look for both "Table.search" and "Table.search()" patterns
- Match partial names (e.g., "connect" matches "mylib.connect")

Focus on accurate matching and comprehensive coverage!"""


MATCHING_PROMPT = """Match discovered APIs to documentation.

API Surface File: {api_surface_file}
Documentation Folder: {docs_folder}
Extraction Folder: {extraction_folder} (optional - for enrichment)
Language: {language}
Documented Output: {documented_output_file}
Undocumented Output: {undocumented_output_file}

**WORKFLOW:**

STEP 1: Read API Surface
=========================
Read the file: {api_surface_file}

This contains all {total_apis} APIs discovered via introspection.

STEP 2: Run Deterministic Matching Script
==========================================
```bash
python stackbench/introspection_templates/markdown_api_matcher.py \\
    {docs_folder} \\
    {api_surface_file} \\
    /tmp/api_matches.json \\
    {language}
```

This script will:
- Scan ALL .md files in {docs_folder} recursively
- Find API mentions using fuzzy pattern matching (snake_case ↔ camelCase)
- Output: /tmp/api_matches.json with reference details

STEP 3: Read Script Output
===========================
Read /tmp/api_matches.json

This contains:
- For each API: documented (true/false), references (list), files (list), reference_count (int)
- Reference details: file, line, context, match_type, matched_variant, in_code_block

STEP 4: Calculate Importance Scores (MCP)
==========================================
For EACH API (both documented and undocumented), call the MCP tool:

```
calculate_importance_score(
    api="mylib.connect",
    module="mylib",
    type="function",
    has_docstring=true,
    in_all=true
)
```

Returns:
{{
  "api": "mylib.connect",
  "score": 9,
  "tier": "high",
  "reasons": ["In __all__", "Has documentation", "Public API", "Common pattern"],
  "breakdown": {{"in_all": 3, "has_docstring": 2, "not_private": 1, "common_name": 1}}
}}

STEP 5: Enrich with Extraction Metadata (Optional)
===================================================
If {extraction_folder} exists and is provided:
- Read *_analysis.json files from {extraction_folder}
- Look for APIs that match documented APIs from script output
- Add section_hierarchy, markdown_anchor from extraction metadata
- This enriches the references with additional context

Example enrichment:
- Script found: "mylib.connect" in quickstart.md line 42
- Extraction has: quickstart_analysis.json with section "Quick Start > Connection"
- Enrich reference with: section_hierarchy: ["Quick Start", "Connection"], markdown_anchor: "#connection"

If extraction_folder is not provided or doesn't exist, skip this step.

STEP 6: Write Documented APIs
==============================
Write to: {documented_output_file}

Format:
{{
  "total_documented": <count>,
  "apis": [
    {{
      "api": "mylib.connect",
      "module": "mylib",
      "type": "function",
      "is_async": false,
      "has_docstring": true,
      "in_all": true,
      "is_deprecated": false,
      "signature": "(...)",
      "importance": "high",
      "importance_score": 9,
      "reference_count": 5,
      "documentation_references": [
        {{
          "document": "quickstart.md",
          "line_number": 15,
          "context": "import mylib",
          "match_type": "import",
          "matched_variant": "mylib",
          "in_code_block": true,
          "section_hierarchy": ["Quick Start", "Installation"],  # Optional: from extraction
          "markdown_anchor": "#installation"  # Optional: from extraction
        }},
        {{
          "document": "quickstart.md",
          "line_number": 42,
          "context": "db = mylib.connect('./data')",
          "match_type": "function_call",
          "matched_variant": "mylib.connect",
          "in_code_block": true,
          "section_hierarchy": ["Quick Start", "Basic Usage"],  # Optional: from extraction
          "markdown_anchor": "#basic-usage"  # Optional: from extraction
        }}
      ],
      "documented_in": ["quickstart.md"],
      "has_examples": true
    }}
  ]
}}

STEP 7: Write Undocumented APIs
================================
Write to: {undocumented_output_file}

Format:
{{
  "total_undocumented": <count>,
  "apis": [
    {{
      "api": "mylib.Database.dropTable",
      "module": "mylib.database",
      "type": "method",
      "is_async": false,
      "has_docstring": true,
      "in_all": false,
      "is_deprecated": false,
      "signature": "(...)",
      "importance": "high",
      "importance_score": 8,
      "reason": "In __all__, has docstring, common CRUD operation"
    }}
  ]
}}

**IMPORTANT:**
- Use script output as source of truth for which files mention each API
- Call MCP for importance scores on EVERY API
- Enrich with extraction metadata if available
- Record ALL references from script output (don't truncate)
- Include reference_count for documented APIs
- Documented APIs should have documentation_references array with match_type, context, etc.
- Undocumented APIs should have importance score and reason
"""


class MatchingAgent:
    """Stage 2: API-to-documentation matching agent."""

    def __init__(
        self,
        api_surface_file: Path,
        docs_folder: Path,
        output_folder: Path,
        language: str = "python",
        extraction_folder: Optional[Path] = None,
        validation_log_dir: Optional[Path] = None
    ):
        """Initialize the matching agent."""
        self.api_surface_file = Path(api_surface_file)
        self.docs_folder = Path(docs_folder)
        self.extraction_folder = Path(extraction_folder) if extraction_folder else None
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.language = language
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        self.documented_output = self.output_folder / "documented_apis.json"
        self.undocumented_output = self.output_folder / "undocumented_apis.json"

        # Read API surface to get total count
        with open(self.api_surface_file, 'r', encoding='utf-8') as f:
            api_surface = json.load(f)
            self.total_apis = api_surface.get('total_apis', 0)

        print(f"🔍 Stage 2: Matching Agent")
        print(f"   API Surface: {self.api_surface_file} ({self.total_apis} APIs)")
        print(f"   Documentation Folder: {self.docs_folder}")
        if self.extraction_folder:
            print(f"   Extraction Folder: {self.extraction_folder} (for enrichment)")
        print(f"   Language: {self.language}")
        print(f"   Documented Output: {self.documented_output}")
        print(f"   Undocumented Output: {self.undocumented_output}")

        if self.validation_log_dir:
            print(f"   Logging: {self.validation_log_dir}")

    async def run(self) -> Dict[str, Any]:
        """Run matching and return results."""
        start_time = datetime.now()

        # Create logger
        from stackbench.hooks import create_logging_hooks, AgentLogger

        if self.validation_log_dir:
            matching_logs_dir = self.validation_log_dir / "matching"
            matching_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = matching_logs_dir / "agent.log"
            tools_log = matching_logs_dir / "tools.jsonl"
            logger = AgentLogger(agent_log, tools_log)
            hooks = create_logging_hooks(logger)
        else:
            hooks = {'PreToolUse': [], 'PostToolUse': []}

        # Create options with MCP server
        options = ClaudeAgentOptions(
            system_prompt=MATCHING_SYSTEM_PROMPT,
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
            prompt = MATCHING_PROMPT.format(
                api_surface_file=str(self.api_surface_file),
                docs_folder=str(self.docs_folder),
                extraction_folder=str(self.extraction_folder) if self.extraction_folder else "None (optional)",
                language=self.language,
                documented_output_file=str(self.documented_output),
                undocumented_output_file=str(self.undocumented_output),
                total_apis=self.total_apis
            )

            await client.query(prompt)

            # Wait for completion
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    pass  # Agent will write the files

        # Read the output files
        if not self.documented_output.exists():
            raise FileNotFoundError(f"Matching agent did not create {self.documented_output}")
        if not self.undocumented_output.exists():
            raise FileNotFoundError(f"Matching agent did not create {self.undocumented_output}")

        with open(self.documented_output, 'r', encoding='utf-8') as f:
            documented = json.load(f)

        with open(self.undocumented_output, 'r', encoding='utf-8') as f:
            undocumented = json.load(f)

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        documented_count = documented.get('total_documented', 0)
        undocumented_count = undocumented.get('total_undocumented', 0)

        print(f"✅ Stage 2 Complete: {documented_count} documented, {undocumented_count} undocumented ({processing_time}ms)")

        return {
            'documented': documented,
            'undocumented': undocumented,
            'documented_count': documented_count,
            'undocumented_count': undocumented_count
        }


async def main():
    """Test the matching agent."""
    import sys

    if len(sys.argv) < 4:
        print("Usage: python matching_agent.py <api_surface.json> <docs_folder> <output_dir> [language] [extraction_folder]")
        sys.exit(1)

    api_surface_file = Path(sys.argv[1])
    docs_folder = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    language = sys.argv[4] if len(sys.argv) > 4 else "python"
    extraction_folder = Path(sys.argv[5]) if len(sys.argv) > 5 else None

    agent = MatchingAgent(
        api_surface_file=api_surface_file,
        docs_folder=docs_folder,
        output_folder=output_dir,
        language=language,
        extraction_folder=extraction_folder
    )

    result = await agent.run()
    print(f"\nResult: {result['documented_count']} documented, {result['undocumented_count']} undocumented")
    print(f"Outputs:")
    print(f"  - {output_dir / 'documented_apis.json'}")
    print(f"  - {output_dir / 'undocumented_apis.json'}")


if __name__ == "__main__":
    asyncio.run(main())
