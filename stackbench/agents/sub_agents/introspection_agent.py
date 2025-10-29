#!/usr/bin/env python3
"""
Stage 1: Introspection Sub-Agent

This agent:
1. Installs the target library via pip (Bash)
2. Runs the language-specific introspection template (Bash)
3. Reads the JSON output
4. Writes api_surface.json to output folder

Outputs:
- output_folder/api_surface.json: Complete API surface with metadata
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


INTROSPECTION_SYSTEM_PROMPT = """You are an API introspection specialist.

Your ONLY job is to:
1. Install a library via pip
2. Run the introspection template
3. Read the JSON output
4. Write it to the output file

**You do NOT:**
- Match APIs to documentation
- Calculate importance scores
- Analyze coverage
- Build complex reports

**Your workflow:**
1. `pip install {library}=={version}`
2. `cp stackbench/introspection_templates/python_introspect.py /tmp/introspect_{library}.py`
3. `python /tmp/introspect_{library}.py {library} {version} > /tmp/introspection_result.json`
4. Read `/tmp/introspection_result.json`
5. Write exact contents to `{output_file}`

Keep it simple and focused!"""


INTROSPECTION_PROMPT = """Introspect the library API surface.

Library: {library}
Version: {version}
Language: {language}
Output File: {output_file}

**WORKFLOW:**

STEP 1: Install Library
========================
```bash
pip install {library}=={version}
```

STEP 2: Copy Introspection Template
====================================
```bash
cp stackbench/introspection_templates/python_introspect.py /tmp/introspect_{library}.py
```

STEP 3: Run Introspection
==========================
```bash
python /tmp/introspect_{library}.py {library} {version} > /tmp/introspection_result.json
```

STEP 4: Read Result
===================
```bash
cat /tmp/introspection_result.json
```

STEP 5: Write Output
====================
Write the exact JSON contents to: {output_file}

The JSON should have this structure:
{{
  "library": "{library}",
  "version": "{version}",
  "language": "{language}",
  "total_apis": <number>,
  "apis": [
    {{
      "api": "library.function",
      "module": "library",
      "type": "function",
      "is_async": false,
      "has_docstring": true,
      "in_all": true,
      "is_deprecated": false,
      "signature": "(...)"
    }}
  ],
  "by_type": {{...}},
  "deprecated_count": <number>
}}

**IMPORTANT:**
- Do NOT modify the JSON structure
- Do NOT add extra fields
- Write EXACTLY what the introspection template outputs
"""


class IntrospectionAgent:
    """Stage 1: Library introspection agent."""

    def __init__(
        self,
        output_folder: Path,
        library_name: str,
        library_version: str,
        language: str = "python",
        validation_log_dir: Optional[Path] = None
    ):
        """Initialize the introspection agent."""
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.library_name = library_name
        self.library_version = library_version
        self.language = language
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        self.output_file = self.output_folder / "api_surface.json"

        print(f"📋 Stage 1: Introspection Agent")
        print(f"   Library: {library_name} v{library_version}")
        print(f"   Output: {self.output_file}")

        if self.validation_log_dir:
            print(f"   Logging: {self.validation_log_dir}")

    async def run(self) -> dict:
        """Run introspection and return API surface data."""
        start_time = datetime.now()

        # Create logger
        from stackbench.hooks import create_logging_hooks, AgentLogger

        if self.validation_log_dir:
            introspection_logs_dir = self.validation_log_dir / "introspection"
            introspection_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = introspection_logs_dir / "agent.log"
            tools_log = introspection_logs_dir / "tools.jsonl"
            logger = AgentLogger(agent_log, tools_log)
            hooks = create_logging_hooks(logger)
        else:
            hooks = {'PreToolUse': [], 'PostToolUse': []}

        # Create options
        options = ClaudeAgentOptions(
            system_prompt=INTROSPECTION_SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            hooks=hooks,
            cwd=str(Path.cwd())
        )

        async with ClaudeSDKClient(options=options) as client:
            prompt = INTROSPECTION_PROMPT.format(
                library=self.library_name,
                version=self.library_version,
                language=self.language,
                output_file=str(self.output_file)
            )

            await client.query(prompt)

            # Wait for completion
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    pass  # Agent will write the file

        # Read the output file
        if not self.output_file.exists():
            raise FileNotFoundError(f"Introspection agent did not create {self.output_file}")

        with open(self.output_file, 'r', encoding='utf-8') as f:
            api_surface = json.load(f)

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        print(f"✅ Stage 1 Complete: {api_surface['total_apis']} APIs found ({processing_time}ms)")

        return api_surface


async def main():
    """Test the introspection agent."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python introspection_agent.py <library> <version> [output_dir]")
        sys.exit(1)

    library = sys.argv[1]
    version = sys.argv[2]
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/introspection_test")

    agent = IntrospectionAgent(
        output_folder=output_dir,
        library_name=library,
        library_version=version,
        language="python"
    )

    result = await agent.run()
    print(f"\nResult: {result['total_apis']} APIs")
    print(f"Output: {output_dir / 'api_surface.json'}")


if __name__ == "__main__":
    asyncio.run(main())
