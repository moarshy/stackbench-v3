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

from dotenv import load_dotenv
load_dotenv()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ExampleValidationResult(BaseModel):
    """Validation result for a single code example."""
    example_index: int
    line: int
    context: str
    code: str
    status: str = Field(description="success|failure|skipped")
    error_message: Optional[str] = None
    suggestions: Optional[str] = None
    execution_output: Optional[str] = None
    depends_on_previous: bool = False


class DocumentValidationResult(BaseModel):
    """Validation result for an entire document."""
    page: str
    library: str
    version: str
    language: str
    validation_timestamp: str
    results: List[ExampleValidationResult]
    total_examples: int
    successful: int
    failed: int
    skipped: int


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

VALIDATION_SYSTEM_PROMPT = """You are an expert code validator specializing in validating documentation code examples.

Your task is to:
1. Execute code examples in isolated virtual environments
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
Document: {page}

Examples to validate:
{examples_json}

Instructions:
1. Create a virtual environment
2. Install {library}=={version} and all required dependencies
3. For each example:
   - Check if it depends on previous examples (uses undefined variables)
   - If independent: Execute in fresh namespace
   - If dependent: Execute with accumulated state from previous examples
   - Capture output, errors, and suggestions
4. Clean up the environment when done

For each example, provide a JSON response with:
{{
  "example_index": <int>,
  "status": "success|failure|skipped",
  "error_message": "<error if failed>",
  "suggestions": "<how to fix or improve>",
  "execution_output": "<stdout/stderr>",
  "depends_on_previous": <bool>
}}

Respond with a JSON array of validation results.

IMPORTANT: Actually run the code using Bash tool. Create virtualenv, install packages, execute code, report results."""


# ============================================================================
# VALIDATION AGENT
# ============================================================================

class ValidationAgent:
    """Agent that validates code examples using Claude Code."""

    def __init__(self, extraction_output_folder: Path, validation_output_folder: Path, num_workers: int = 5):
        self.extraction_output_folder = Path(extraction_output_folder)
        self.validation_output_folder = Path(validation_output_folder)
        self.validation_output_folder.mkdir(parents=True, exist_ok=True)
        self.num_workers = num_workers

        print(f"👷 Code Validation Workers: {self.num_workers}")

        self.options = ClaudeAgentOptions(
            system_prompt=VALIDATION_SYSTEM_PROMPT,
            allowed_tools=["Bash", "Write", "Read"],
            permission_mode="acceptEdits",
            cwd=str(Path.cwd())
        )

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
                "is_executable": ex.get("is_executable", False)
            })
        return json.dumps(formatted, indent=2)

    def extract_json_from_response(self, response_text: str) -> Optional[List[Dict]]:
        """Extract JSON array from Claude's response."""
        try:
            # Try to find JSON in markdown code blocks
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
            else:
                # Try parsing the whole response
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            return None

    async def get_claude_response(self, client: ClaudeSDKClient, prompt: str) -> str:
        """Send prompt to Claude and get text response."""
        await client.query(prompt)

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
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

        if not examples:
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
        async with ClaudeSDKClient(options=self.options) as client:
            examples_json = self.format_examples_for_prompt(examples)
            prompt = VALIDATE_EXAMPLES_PROMPT.format(
                library=library,
                version=version,
                page=page,
                examples_json=examples_json
            )

            response_text = await self.get_claude_response(client, prompt)

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
                error_message=val_result.get("error_message"),
                suggestions=val_result.get("suggestions"),
                execution_output=val_result.get("execution_output"),
                depends_on_previous=val_result.get("depends_on_previous", False)
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

        # Save result
        output_file = self.validation_output_folder / f"{Path(page).stem}_validation.json"
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

        print(f"✅ Code validation complete: {total_successful} success, {total_failed} failed, {total_skipped} skipped ({validation_duration_seconds:.1f}s)")

        # Save summary with timing
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_documents": len(results),
            "total_examples": total_examples,
            "successful": total_successful,
            "failed": total_failed,
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
