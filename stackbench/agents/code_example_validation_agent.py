"""
Code Example Validation Agent - Uses Claude Code to validate extracted code examples.

Simple approach: Let Claude Code do the work.
- Read extraction JSON
- Ask Claude to validate each example
- Claude creates virtualenv, installs deps, runs code
- Claude reports back success/failure with suggestions
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

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
from stackbench.schemas import ExampleValidationResult, DocumentValidationResult


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

# All Pydantic models are now imported from stackbench.schemas
# This eliminates duplication and ensures consistency across all agents


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

VALIDATION_SYSTEM_PROMPT = """You are an expert code validator specializing in validating documentation code examples across Python, JavaScript, and TypeScript.

Your task is to:
1. Execute code examples in isolated environments (virtualenv for Python, npm/node for JS/TS)
2. Install required dependencies with exact versions
3. Handle sequential dependencies (where examples depend on previous ones)
4. Report success/failure with actionable suggestions

For sequential examples:
- Track variables/state from previous examples
- Execute examples in order within the same environment
- Identify when an example needs context from previous examples

Always be thorough and provide clear, actionable suggestions for failures."""


VALIDATE_EXAMPLES_PROMPT = """Validate the following code examples from documentation.

Library: {library}
Version: {version}
Language: {language}
Document: {page}

Examples to validate:
{examples_json}

TASK:
1. Create an isolated environment based on language:
   - **Python**: Create virtualenv using Bash tool
   - **JavaScript/TypeScript**: Create npm project or use temporary directory

2. Install library and dependencies:
   - **Python**: `pip install {library}=={version}`
   - **JavaScript/TypeScript**: `npm install {library}@{version}` or `yarn add {library}@{version}`

3. For each example:
   - Check if it depends on previous examples (uses undefined variables)
   - If independent: Execute in fresh namespace
   - If dependent: Execute with accumulated state from previous examples
   - **Track WHICH specific examples it depends on** (e.g., depends on examples [0, 2])
   - **Save the FULL CODE that was actually executed** (including merged dependencies)
   - **Handle async code appropriately** (see ASYNC CODE HANDLING below)
   - Capture output, errors, and suggestions
   - **Classify severity** if the example fails (see SEVERITY CLASSIFICATION below)
4. Clean up the environment when done

ASYNC CODE HANDLING:
Examples may have an "execution_context" field indicating if they need async handling:

**"async"** - Code contains async/await patterns:

  **Python**:
  - Wrap the code in an async function and run with asyncio
  - Template:
    ```python
    import asyncio

    async def main():
        # ... original code here ...

    asyncio.run(main())
    ```
  - Example: If code is `async_db = await lancedb.connect_async(uri)`, execute as:
    ```python
    import asyncio
    import lancedb

    async def main():
        uri = "data/sample-lancedb"
        async_db = await lancedb.connect_async(uri)
        return async_db

    asyncio.run(main())
    ```

  **JavaScript/TypeScript**:
  - Wrap in an async IIFE (Immediately Invoked Function Expression) or use top-level await (if supported)
  - Template:
    ```javascript
    (async () => {{
        // ... original code here ...
    }})();
    ```
  - Example: If code is `const data = await client.fetch()`, execute as:
    ```javascript
    (async () => {{
        const client = require('{{library}}');
        const data = await client.fetch();
        console.log(data);
    }})();
    ```

**"sync"** - Regular code:
  - Execute as-is without any wrapping

**"not_executable"** - Incomplete/pseudocode:
  - Skip execution and mark as "skipped" with reason

SEVERITY CLASSIFICATION (for failed examples only):
Classify each failure by analyzing the error type and context:

**"error"** - Clear documentation mistake that needs fixing:
  * **Python**: SyntaxError, IndentationError (malformed code)
  * **JS/TS**: SyntaxError, ReferenceError for undefined variables
  * **All languages**: Missing imports/requires in docs, wrong API method names
  * **Python**: NameError for undefined variables (not from dependencies)
  * **Python**: ImportError, ModuleNotFoundError (missing imports)
  * **JS/TS**: Cannot find module, ReferenceError
  * **All languages**: AttributeError/TypeError on documented API calls (wrong method/property name)
  * **All languages**: Type errors from wrong argument types in user code
  * Any error that occurs in the first few lines of user code

**"warning"** - Likely environment/compatibility issue (not a doc error):
  * Errors deep inside library internals (error in library's internal functions)
  * Version compatibility errors (error message mentions version conflicts)
  * **Python**: TypeError in internal library functions (e.g., "_scan_pyarrow_dataset_impl")
  * **JS/TS**: TypeErrors in node_modules code
  * Dependency conflicts between libraries
  * Errors that occur several stack frames deep into library code
  * Errors with message suggesting updating library versions

**"info"** - Non-blocking informational issues:
  * **Python**: DeprecationWarning, FutureWarning
  * **JS/TS**: Deprecation warnings in console
  * Output format differences (not errors, just different formatting)
  * Performance warnings

CRITICAL: Respond with ONLY the JSON array below. No explanatory text before or after. Just the JSON.

RESPONSE FORMAT - JSON ONLY:

```json
[
  {{
    "example_index": 0,
    "status": "success|failure|skipped",
    "severity": "error|warning|info",
    "error_message": "error details if failed",
    "suggestions": "how to fix or improve",
    "execution_output": "stdout/stderr output",
    "depends_on_previous": false,
    "depends_on_example_indices": [],
    "actual_code_executed": "Python: import mylib\\nclient = mylib.connect() | JS: const mylib = require('mylib'); const client = mylib.connect();"
  }},
  {{
    "example_index": 2,
    "status": "failure",
    "severity": "error",
    "error_message": "Python: NameError: name 'client' is not defined | JS: ReferenceError: client is not defined",
    "suggestions": "Missing import statement. Add: Python: import mylib\\nclient = mylib.connect() | JS: const {{ connect }} = require('mylib'); const client = connect();",
    "execution_output": "...",
    "depends_on_previous": true,
    "depends_on_example_indices": [0],
    "actual_code_executed": "Full code that was executed, including dependencies from previous examples"
  }}
]
```

IMPORTANT:
- Use actual Bash tool execution to run the code
- **Python**: Create virtualenv, install packages with pip, run with python
- **JavaScript/TypeScript**: Create npm project, install with npm/yarn, run with node/ts-node
- Report actual execution results
- For dependency tracking:
  - `depends_on_example_indices` must list specific example numbers (e.g., [0, 1] means depends on examples 0 and 1)
  - `actual_code_executed` must show the COMPLETE code that was run (if you merged multiple examples, include all of them)
- For severity classification:
  - `severity` is REQUIRED for all failures (status="failure")
  - `severity` should be null for success/skipped
  - Carefully analyze the error to distinguish doc errors from environment issues
  - Use language-specific error patterns (Python: NameError, ImportError | JS/TS: ReferenceError, Cannot find module)
- Respond with ONLY the JSON array, no other text"""


# ============================================================================
# VALIDATION AGENT
# ============================================================================

class ValidationAgent:
    """Agent that validates code examples using Claude Code."""

    def __init__(
        self,
        extraction_output_folder: Path,
        validation_output_folder: Path,
        num_workers: int = 5,
        validation_log_dir: Optional[Path] = None
    ):
        self.extraction_output_folder = Path(extraction_output_folder)
        self.validation_output_folder = Path(validation_output_folder)
        self.validation_output_folder.mkdir(parents=True, exist_ok=True)
        self.num_workers = num_workers
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        print(f"👷 Code Validation Workers: {self.num_workers}")

        # Note: We don't create a global logger here anymore - we create one per document
        # This allows us to have separate log files for each document
        if self.validation_log_dir:
            print(f"📋 Per-document logging enabled")
            print(f"   Logs will be saved to: {self.validation_log_dir}/code_example_logs/")

    def format_examples_for_prompt(self, examples: List[Dict]) -> str:
        """Format examples as JSON for the prompt."""
        formatted = []
        for i, ex in enumerate(examples):
            formatted.append({
                "index": i,
                "line": ex.get("line", 0),
                "context": ex.get("context", ""),
                "code": ex.get("code", ""),
                "dependencies": ex.get("dependencies", []),
                "is_executable": ex.get("is_executable", False),
                "execution_context": ex.get("execution_context", "sync")  # New field
            })
        return json.dumps(formatted, indent=2)

    def extract_json_from_response(self, response_text: str) -> Optional[List[Dict]]:
        """Extract JSON array from Claude's response."""
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

            # Strategy 2: Look for JSON array markers [ ]
            # Find the first [ and try to parse from there
            start_idx = response_text.find('[')
            if start_idx != -1:
                # Try to parse from this point
                try:
                    # Find matching closing bracket by counting
                    bracket_count = 0
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
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    # Found complete JSON array
                                    json_text = response_text[start_idx:i+1]
                                    return json.loads(json_text)

                except Exception:
                    pass

            # Strategy 3: Try parsing the whole response
            return json.loads(response_text.strip())

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            # Try to show where the JSON might be
            if '[' in response_text:
                json_start = response_text.find('[')
                print(f"   Found '[' at position {json_start}")
                print(f"   Context: ...{response_text[max(0, json_start-50):json_start+100]}...")
            return None

    async def get_claude_response(self, client: ClaudeSDKClient, prompt: str, logger=None, messages_log_file=None) -> str:
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
                    # Convert message blocks to serializable format
                    message_content = []
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            message_content.append({
                                "type": "text",
                                "text": block.text
                            })
                            response_text += block.text
                        else:
                            # Handle other block types
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
                    # Original behavior when no logger
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

        return response_text

    async def validate_document(self, extraction_file: Path) -> DocumentValidationResult:
        """Validate all examples in a document."""
        # Load extraction data
        with open(extraction_file, 'r') as f:
            data = json.load(f)

        page = data["page"]
        library = data["library"]
        version = data["version"]
        language = data["language"]
        examples = data.get("examples", [])

        # Create per-document logger with new directory structure
        from stackbench.hooks import create_agent_hooks, AgentLogger

        messages_log_file = None
        if self.validation_log_dir:
            doc_stem = extraction_file.stem.replace('_analysis', '')
            # New structure: logs/code_example_logs/<doc_name>/
            code_logs_dir = self.validation_log_dir / "code_example_logs" / doc_stem
            code_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = code_logs_dir / "agent.log"
            tools_log = code_logs_dir / "tools.jsonl"
            messages_log_file = code_logs_dir / "messages.jsonl"
            logger = AgentLogger(agent_log, tools_log)
        else:
            logger = None

        # Create hooks for this document
        hooks = create_agent_hooks(
            agent_type="code_validation",
            logger=logger,
            output_dir=self.validation_output_folder,
            validation_log_dir=self.validation_log_dir
        )

        # Create options with per-document hooks
        options = ClaudeAgentOptions(
            system_prompt=VALIDATION_SYSTEM_PROMPT,
            allowed_tools=["Bash", "Write", "Read"],
            permission_mode="acceptEdits",
            hooks=hooks,
            cwd=str(Path.cwd())
        )

        if not examples:
            # Log early return decision
            if messages_log_file:
                early_return_message = {
                    "timestamp": datetime.now().isoformat(),
                    "role": "system",
                    "content": [{
                        "type": "text",
                        "text": f"Document '{page}' has 0 code examples. Skipping Claude invocation and returning empty validation result."
                    }]
                }
                with open(messages_log_file, 'w') as f:
                    f.write(json.dumps(early_return_message) + '\n')

            return DocumentValidationResult(
                page=page,
                library=library,
                version=version,
                language=language,
                validation_timestamp=datetime.now().isoformat(),
                results=[],
                total_examples=0,
                successful=0,
                failed=0,
                skipped=0
            )

        # Ask Claude to validate
        async with ClaudeSDKClient(options=options) as client:
            examples_json = self.format_examples_for_prompt(examples)
            prompt = VALIDATE_EXAMPLES_PROMPT.format(
                library=library,
                version=version,
                language=language,
                page=page,
                examples_json=examples_json
            )

            response_text = await self.get_claude_response(client, prompt, logger, messages_log_file)

            # Parse results
            validation_results = self.extract_json_from_response(response_text)

            if not validation_results:
                # Create skipped results
                validation_results = [
                    {
                        "example_index": i,
                        "status": "skipped",
                        "error_message": "Failed to parse Claude response",
                        "suggestions": None,
                        "execution_output": None,
                        "depends_on_previous": False
                    }
                    for i in range(len(examples))
                ]

        # Build results
        results = []
        for i, val_result in enumerate(validation_results):
            example = examples[i] if i < len(examples) else {}
            results.append(ExampleValidationResult(
                example_index=val_result.get("example_index", i),
                line=example.get("line", 0),
                context=example.get("context", ""),
                code=example.get("code", ""),
                status=val_result.get("status", "skipped"),
                severity=val_result.get("severity"),  # NEW: Include severity
                error_message=val_result.get("error_message"),
                suggestions=val_result.get("suggestions"),
                execution_output=val_result.get("execution_output"),
                depends_on_previous=val_result.get("depends_on_previous", False),
                depends_on_example_indices=val_result.get("depends_on_example_indices", []),
                actual_code_executed=val_result.get("actual_code_executed")
            ))

        # Count results
        successful = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failure")
        skipped = sum(1 for r in results if r.status == "skipped")

        # Create result
        doc_result = DocumentValidationResult(
            page=page,
            library=library,
            version=version,
            language=language,
            validation_timestamp=datetime.now().isoformat(),
            results=results,
            total_examples=len(examples),
            successful=successful,
            failed=failed,
            skipped=skipped
        )

        # Validate JSON before saving
        from stackbench.hooks import validate_validation_output_json

        validation_dict = json.loads(doc_result.model_dump_json())
        filename = f"{Path(page).stem}_validation.json"

        passed, errors = validate_validation_output_json(
            validation_dict,
            filename,
            self.validation_log_dir,
            validation_type="code_example_validation"
        )

        if not passed:
            print(f"⚠️  {filename} - Validation failed: {errors[:2] if errors else 'Unknown error'}")

        # Save result
        output_file = self.validation_output_folder / filename
        with open(output_file, 'w') as f:
            f.write(doc_result.model_dump_json(indent=2))

        return doc_result

    async def _validate_document_with_save(
        self,
        extraction_file: Path,
        semaphore: asyncio.Semaphore,
        progress: Dict[str, int]
    ) -> Optional[DocumentValidationResult]:
        """Validate a single document with semaphore control (already saves internally)."""
        async with semaphore:
            try:
                result = await self.validate_document(extraction_file)
                progress['completed'] += 1
                # Show meaningful stats: success/failed/skipped
                s = result.successful
                f = result.failed
                sk = result.skipped
                print(f"✅ [{progress['completed']}/{progress['total']}] {extraction_file.stem.replace('_analysis', '')} - {s} success, {f} failed, {sk} skipped")
                return result
            except Exception as e:
                progress['completed'] += 1
                print(f"❌ [{progress['completed']}/{progress['total']}] Error: {extraction_file.stem.replace('_analysis', '')} - {e}")
                import traceback
                traceback.print_exc()
                return None

    async def validate_all_documents(self) -> Dict[str, Any]:
        """Validate all extraction files using parallel workers."""
        # Track overall validation time
        validation_start_time = datetime.now()

        extraction_files = list(self.extraction_output_folder.glob("*_analysis.json"))

        # Filter out summary file
        extraction_files = [f for f in extraction_files if f.name != "extraction_summary.json"]

        print(f"📝 Validating code examples for {len(extraction_files)} documents ({self.num_workers} workers)")

        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self.num_workers)

        # Progress tracking
        progress = {'completed': 0, 'total': len(extraction_files)}
        tasks = [
            self._validate_document_with_save(extraction_file, semaphore, progress)
            for extraction_file in extraction_files
        ]

        results = await asyncio.gather(*tasks)

        # Filter out None results (failed validations)
        results = [r for r in results if r is not None]

        # Calculate validation duration
        validation_end_time = datetime.now()
        validation_duration_seconds = (validation_end_time - validation_start_time).total_seconds()

        # Overall summary
        total_examples = sum(r.total_examples for r in results)
        total_successful = sum(r.successful for r in results)
        total_failed = sum(r.failed for r in results)
        total_skipped = sum(r.skipped for r in results)

        # Calculate severity breakdown
        total_errors = 0
        total_warnings = 0
        total_info = 0
        for r in results:
            for example_result in r.results:
                if example_result.status == "failure" and example_result.severity:
                    if example_result.severity == "error":
                        total_errors += 1
                    elif example_result.severity == "warning":
                        total_warnings += 1
                    elif example_result.severity == "info":
                        total_info += 1

        print(f"✅ Code validation complete: {total_successful} success, {total_failed} failed ({total_errors} errors, {total_warnings} warnings, {total_info} info), {total_skipped} skipped ({validation_duration_seconds:.1f}s)")

        # Save summary with timing
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_documents": len(results),
            "total_examples": total_examples,
            "successful": total_successful,
            "failed": total_failed,
            "failed_by_severity": {
                "error": total_errors,
                "warning": total_warnings,
                "info": total_info
            },
            "validation_duration_seconds": round(validation_duration_seconds, 2),
            "num_workers": self.num_workers,
            "documents": [
                {
                    "page": r.page,
                    "library": r.library,
                    "version": r.version,
                    "total_examples": r.total_examples,
                    "successful": r.successful,
                    "failed": r.failed
                }
                for r in results
            ]
        }

        summary_file = self.validation_output_folder / "validation_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"💾 Summary saved to {summary_file}")

        return summary


# This module is designed to be used as a library.
# For CLI usage, see stackbench.cli module.
