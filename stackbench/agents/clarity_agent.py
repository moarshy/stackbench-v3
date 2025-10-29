"""
Documentation Clarity & Structure Validation Agent

This agent evaluates documentation quality from a user experience perspective using Claude Code.
It uses an LLM-as-judge approach to assess clarity, logical flow, completeness, and consistency.
"""

import json
import re
import asyncio
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

# Import centralized schemas
from stackbench.schemas import (
    ClarityValidationOutput,
    ClarityIssue,
    StructuralIssue,
    ClarityScore,
    ClaritySummary,
    TechnicalAccessibility,
    BrokenLink,
    MissingAltText,
    CodeBlockIssue,
    ImprovementRoadmap,
    ScoreExplanation
)

# Note: get_content_metrics_from_validation no longer needed - agent calls MCP tools directly
# from stackbench.agents.clarity_helpers import get_content_metrics_from_validation
# AgentLogger and create_logging_hooks no longer needed for separate MCP calls

console = Console()


# ============================================================================
# All Pydantic models are now imported from stackbench.schemas
# This eliminates duplication and ensures consistency across all agents
# ============================================================================

# Note: ClarityValidationSummary is a summary across documents, used only in this agent
# (not part of the output schema for individual documents)
class ClarityValidationSummary(BaseModel):
    """Summary of clarity validation across all documents."""

    validation_timestamp: str = Field(
        description="ISO timestamp of summary generation"
    )

    total_documents: int = Field(
        description="Total documents analyzed"
    )

    average_clarity_score: float = Field(
        description="Average overall clarity score across all documents"
    )

    total_issues_found: int = Field(
        description="Total issues across all documents (clarity + structural + technical)"
    )

    critical_issues: int = Field(
        description="Total critical issues"
    )

    warnings: int = Field(
        description="Total warnings"
    )

    validation_duration_seconds: float = Field(
        description="Total time taken for all validations"
    )

    num_workers: int = Field(
        description="Number of parallel workers used"
    )

    documents: list[dict] = Field(
        description="Per-document summary statistics"
    )


# ============================================================================
# Prompts
# ============================================================================

CLARITY_SYSTEM_PROMPT = """You are an expert documentation quality analyst specializing in evaluating instructional clarity and structure.

Your role is to evaluate documentation from the perspective of a new user trying to follow tutorials and guides. You identify specific issues across 5 dimensions:

1. **Instructional Clarity**
   - Are instructions clear and actionable?
   - Is it obvious what to do at each step?
   - Are commands/code examples complete and correct?
   - Is the expected outcome explained?

2. **Logical Flow**
   - Do steps build on each other properly?
   - Are there gaps in reasoning?
   - Does Step N reference something not created in Steps 1 through N-1?
   - Is the progression natural and intuitive?

3. **Completeness**
   - Are all prerequisites mentioned upfront?
   - Are all necessary details included?
   - Are configuration files/environment variables explained?
   - Is error handling mentioned when relevant?

4. **Consistency**
   - Is terminology used consistently?
   - Are code examples in a consistent style?
   - Are similar operations explained similarly?
   - Are variable/function names consistent?

5. **Prerequisite Coverage**
   - Are prerequisites stated at the beginning?
   - Is everything required actually listed?
   - Are version requirements specified?
   - Are system requirements (OS, tools) mentioned?

EVALUATION APPROACH:
- Walk through the documentation as if you're a developer trying to use this library for the first time
- At each step, ask: "Would I know what to do? Would I have all the information I need?"
- Identify SPECIFIC issues with SPECIFIC locations (section, line number, step number)
- Provide actionable suggestions for each issue

SEVERITY LEVELS:
- **critical**: Issue blocks user progress entirely (missing prerequisite, broken logical flow, step references undefined resource)
- **warning**: Issue causes confusion but is workaroundable (terminology inconsistency, unclear wording, missing context)
- **info**: Nice-to-have improvement (adding time estimates, difficulty indicators, better examples)

CODE BLOCK FORMATTING - DO NOT FLAG RENDERING ARTIFACTS:
- **IGNORE INDENTATION ENTIRELY**: Code blocks are extracted from test files and normalized. Indentation is a rendering artifact, not a documentation issue
- **DO NOT** flag: "inconsistent indentation", "extra spaces", "wrong indentation", "should be at module level", etc.
- **ONLY flag indentation** if it would cause actual syntax errors when executed (Python: IndentationError, JS/TS: block scope issues)
- **Focus on CONTENT**: undefined variables, missing imports/requires, wrong APIs, logical errors
- **Ignore formatting**: whitespace, blank lines, indentation style are all rendering artifacts from the build system
- **Language-specific considerations**:
  - Python: imports, async/await, type hints
  - JavaScript/TypeScript: require/import, promises/async, JSDoc annotations

VARIABLE SCOPE ANALYSIS:
- Before flagging "undefined variable", check if it's defined ANYWHERE in the document (not just current section)
- If variable is defined in an earlier section:
  * Type: "cross_section_variable_reference"
  * Severity: "info"
  * Message: "Variable 'X' used here was defined in section 'Y' above. Consider adding a note for users who jump directly to this section."
- Only use "undefined_variable" with "critical" severity if the variable is truly missing from the entire document

**Available MCP Tools for Scoring:**
After finding issues, you have access to these MCP tools for deterministic scoring:
- `calculate_clarity_score(issues, metrics)` - Returns overall score, tier, and dimension scores
- `get_improvement_roadmap(issues, metrics, current_score)` - Returns prioritized fix list with impact/effort
- `explain_score(score, breakdown, issues, metrics)` - Returns human-readable explanation

**Your Workflow:**
1. Analyze documentation and identify issues (clarity, structural, technical)
2. Call `calculate_clarity_score` to get scores
3. Call `get_improvement_roadmap` to prioritize fixes
4. Call `explain_score` to generate explanation
5. Return complete JSON with all results

Focus on finding issues accurately - the MCP tools will handle scoring deterministically."""


def create_clarity_validation_prompt(
    document_page: str,
    markdown_file_path: str,
    repository_root: str,
    library: str,
    version: str,
    language: str,
    content: str,
    api_validation: Optional[Dict[str, Any]] = None,
    code_validation: Optional[Dict[str, Any]] = None
) -> str:
    """Create the validation prompt for analyzing a specific document."""

    # Format validation context
    api_summary = ""
    code_summary = ""

    if api_validation:
        results = api_validation.get('validation_results', [])
        valid = [r for r in results if r.get('status') == 'valid']
        invalid = [r for r in results if r.get('status') == 'invalid']
        not_found = [r for r in results if r.get('status') == 'not_found']

        api_summary = f"""
**API Signature Validation Results (from previous agent):**
- Total signatures validated: {len(results)}
- ✅ Valid: {len(valid)} - these signatures match the actual library API
- ❌ Invalid: {len(invalid)} - parameter mismatches or wrong defaults
- ⚠️  Not Found: {len(not_found)} - documented APIs that don't exist in the library

{"Invalid signatures: " + ', '.join(f"{r.get('function', 'unknown')}()" for r in invalid[:5]) if invalid else ""}
{"Not found: " + ', '.join(f"{r.get('function', 'unknown')}()" for r in not_found[:5]) if not_found else ""}
"""
    else:
        api_summary = "**API Validation:** Not available for this document"

    if code_validation:
        results = code_validation.get('validation_results', [])
        successful = [r for r in results if r.get('status') == 'success']
        failed = [r for r in results if r.get('status') == 'failed']

        failed_details = ""
        if failed:
            failed_details = "\nFailed examples (first 3):\n" + "\n".join(
                f"  - Line {r.get('line', 'N/A')}: {r.get('error_type', 'Error')} - {r.get('error_message', '')[:60]}"
                for r in failed[:3]
            )

        code_summary = f"""
**Code Example Validation Results (from previous agent):**
- Total examples validated: {len(results)}
- ✅ Successful: {len(successful)} - these examples run without errors
- ❌ Failed: {len(failed)} - runtime errors, syntax errors, or import issues
{failed_details}
"""
    else:
        code_summary = "**Code Validation:** Not available for this document"

    return f"""Analyze the following documentation for clarity, structure, and instructional quality.

**Document Information:**
- Page: {document_page}
- Library: {library} v{version}
- Language: {language}

**Document Location:**
- Markdown file: {markdown_file_path}
- Repository root: {repository_root}
- You have access to the Read tool - use it to resolve snippet references and verify links

**IMPORTANT - Documentation Build Directives:**

This markdown may contain build-time directives that reference external files. These are NOT errors:

1. **MkDocs Material snippets:**
   ```
   --8<-- "python/tests/test_file.py:label"
   ```
   To resolve: Use Read tool on `{repository_root}/python/tests/test_file.py`
   Extract code between `# --8<-- [start:label]` and `# --8<-- [end:label]` markers

2. **Sphinx literalinclude:**
   ```
   .. literalinclude:: path/to/file.py
      :lines: 10-20
   ```
   To resolve: Use Read tool and extract specified lines

3. **Other include patterns:**
   Any file path references in special syntax should be resolved using Read tool

**How to handle snippet directives:**
- ✅ DO use Read tool to resolve and view the actual code
- ✅ DO evaluate clarity based on the RESOLVED code content
- ❌ DO NOT flag snippet directives as "incomplete code examples"
- ❌ DO NOT penalize documentation for using build-time includes (this is best practice!)

**How to handle relative links:**
- Internal markdown links (`./file.md`, `../folder/file.md`) are documentation cross-references
- Use Read tool to verify the target file exists: check `{repository_root}/docs/path/to/file.md`
- Only flag as broken if:
  - Target file doesn't exist in the repository, OR
  - External URL (http/https) returns 404 or times out

{api_summary}

{code_summary}

**Use validation results to enhance your analysis:**
- Don't flag code examples as "unclear" if they already passed validation
- DO flag examples that failed validation AND explain how clarity issues may have contributed
- DO note when documented APIs don't exist (correlate with "not found" from API validation)
- Provide richer insights by connecting clarity problems to actual validation failures

**Your Task:**
1. **Read through the entire document** as if you're a new user trying to follow it
2. **Resolve any snippet references** using the Read tool if needed
3. **Identify clarity issues** with specific locations (section, line, step number)
4. **Check technical accessibility** (broken links, missing alt text, code blocks)
5. **Provide actionable suggestions** for each issue

**Document Content:**
```markdown
{content}
```

**CRITICAL REQUIREMENTS:**
- Report SPECIFIC locations: Include section name, line number, and step number (if applicable)
- Be GRANULAR: Not just "unclear" but "Step 3 at line 45 in section 'Configuration' references config.yaml never created"
- Provide ACTIONABLE suggestions: Tell exactly how to fix each issue
- Check ALL links: Use Read tool to verify internal links, check external URLs
- Validate images: Check for missing alt text
- Check code blocks: Ensure all have language specification (```python, ```javascript, ```typescript, ```js, ```ts, ```bash, not just ```)
- Consider validation results: Correlate clarity issues with validation failures when relevant
- Categorize each issue by dimension: instruction_clarity, logical_flow, completeness, consistency, or prerequisite_coverage
- Language-aware evaluation: For {language} documentation, verify appropriate syntax patterns (imports/requires, async patterns, etc.)

**OUTPUT FORMAT - Respond with ONLY this JSON structure:**

```json
{{
  "clarity_issues": [
    {{
      "type": "logical_gap",
      "severity": "critical",
      "line": 45,
      "section": "Configuration",
      "step_number": 3,
      "message": "Step 3 references 'config.yaml' but this file was never created or explained in prior steps",
      "suggested_fix": "Add Step 2b: Create config.yaml with example content showing required fields",
      "affected_code": "config = Config.from_file('config.yaml')",
      "context_quote": "Now load your configuration: config = Config.from_file('config.yaml')"
    }},
    {{
      "type": "cross_section_variable_reference",
      "severity": "info",
      "line": 133,
      "section": "From Pydantic Models",
      "step_number": 2,
      "message": "Variable 'data' used here was defined in section 'From Polars DataFrame' above. Consider adding a note for users who jump directly to this section.",
      "suggested_fix": "Add comment before line 133: '# Using the same data defined in the previous section' or redefine data for this section",
      "affected_code": "df = pl.DataFrame(data)",
      "context_quote": "table = db.create_table('pydantic_table', schema=Item)\ndf = pl.DataFrame(data)"
    }}
  ],
  "structural_issues": [
    {{
      "type": "buried_prerequisites",
      "severity": "warning",
      "location": "Prerequisites mentioned throughout tutorial (lines 87, 102, 156) instead of upfront",
      "message": "Prerequisites are scattered throughout the document rather than consolidated at the beginning",
      "suggested_fix": "Create a 'Prerequisites' section at the top listing all requirements with versions"
    }}
  ],
  "technical_accessibility": {{
    "broken_links": [
      {{
        "url": "https://example.com/old-docs",
        "line": 34,
        "link_text": "See configuration guide",
        "error": "404 Not Found"
      }}
    ],
    "missing_alt_text": [
      {{
        "image_path": "images/architecture.png",
        "line": 67
      }}
    ],
    "code_blocks_without_language": [
      {{
        "line": 23,
        "content_preview": "npm install mylib",
        "message": "Code block missing language specifier (should be ```bash or ```shell)"
      }}
    ],
    "total_links_checked": 15,
    "total_images_checked": 3,
    "total_code_blocks_checked": 12,
    "all_validated": false
  }},
  "summary": {{
    "total_clarity_issues": 2,
    "critical_clarity_issues": 1,
    "warning_clarity_issues": 1,
    "info_clarity_issues": 0,
    "total_structural_issues": 1,
    "critical_structural_issues": 0,
    "total_technical_issues": 3,
    "overall_quality_rating": "good"
  }}
}}
```

**STEP 2: CALL MCP TOOLS FOR SCORING**

After identifying issues, use the MCP tools to calculate scores:

1. First, call `calculate_clarity_score` with the issues and metrics:
```
calculate_clarity_score({{
  "issues": [<your clarity_issues array>],
  "metrics": {{
    "total_code_blocks": <from technical_accessibility>,
    "successful_examples": <from code validation context>,
    "failed_examples": <from code validation context>,
    "total_api_signatures": <from API validation context>,
    "valid_api_signatures": <from API validation context>,
    "invalid_api_signatures": <from API validation context>,
    "missing_api_signatures": 0,
    "api_accuracy_score": <from API validation context or 0.0>
  }}
}})
```

2. Then, call `get_improvement_roadmap` with the score:
```
get_improvement_roadmap({{
  "issues": [<your clarity_issues array>],
  "metrics": <same metrics object>,
  "current_score": <overall_score from calculate_clarity_score>
}})
```

3. Finally, call `explain_score`:
```
explain_score({{
  "score": <overall_score>,
  "breakdown": <breakdown from calculate_clarity_score>,
  "issues": [<your clarity_issues array>],
  "metrics": <same metrics object>
}})
```

**FINAL OUTPUT FORMAT:**

Return a complete JSON object with ALL fields (including MCP results):

```json
{{
  "clarity_issues": [<your issues>],
  "structural_issues": [<your issues>],
  "technical_accessibility": {{<your results>}},
  "summary": {{<your counts>}},
  "clarity_score": {{<from calculate_clarity_score>}},
  "breakdown": {{<from calculate_clarity_score>}},
  "improvement_roadmap": {{<from get_improvement_roadmap>}},
  "score_explanation": {{<from explain_score>}}
}}
```

**IMPORTANT NOTES:**
- Include line numbers for EVERY issue
- Be specific about sections and steps
- Provide actionable suggested_fix for each issue
- Actually check links if possible (use Read tool to verify internal links)
- Count all links, images, and code blocks accurately
- Call ALL THREE MCP tools in order
- Return complete JSON with both your analysis AND MCP results

**CRITICAL: YOU MUST CALL THE MCP TOOLS!**

Do NOT try to calculate scores yourself. Do NOT return a response without calling all three MCP tools:
1. `calculate_clarity_score` - REQUIRED
2. `get_improvement_roadmap` - REQUIRED
3. `explain_score` - REQUIRED

If you don't call these tools, your response will be rejected and the document will fail validation.
The MCP tools are available and ready to use - simply call them with the correct parameters as shown above."""


# ============================================================================
# Agent Implementation
# ============================================================================

class DocumentationClarityAgent:
    """Agent that evaluates documentation clarity and structure using Claude Code."""

    def __init__(
        self,
        extraction_folder: Path,
        output_folder: Path,
        repository_folder: Path,
        num_workers: int = 5,
        validation_log_dir: Optional[Path] = None
    ):
        """
        Initialize the clarity validation agent.

        Args:
            extraction_folder: Path to extraction output folder
            output_folder: Path to save clarity validation results
            repository_folder: Path to cloned repository with original markdown files
            num_workers: Number of parallel workers (default: 5)
            validation_log_dir: Optional directory for logs
        """
        self.extraction_folder = Path(extraction_folder)
        self.output_folder = Path(output_folder)
        self.repository_folder = Path(repository_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.num_workers = num_workers
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        print(f"👷 Clarity Validation Workers: {self.num_workers}")

        if self.validation_log_dir:
            print(f"📋 Per-document logging enabled")
            print(f"   Logs will be saved to: {self.validation_log_dir}/clarity_logs/")

    def _load_validation_results(
        self,
        doc_stem: str
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Load API signature and code validation results if they exist.

        Args:
            doc_stem: Document stem (e.g., 'pydantic' from 'pydantic_analysis.json')

        Returns:
            Tuple of (api_validation_dict, code_validation_dict)
            Either can be None if file doesn't exist
        """
        api_validation = None
        code_validation = None

        # API validation file
        api_file = self.output_folder.parent / "api_validation" / f"{doc_stem}_validation.json"
        if api_file.exists():
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    api_validation = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load API validation for {doc_stem}: {e}[/yellow]")

        # Code validation file
        code_file = self.output_folder.parent / "code_validation" / f"{doc_stem}_validation.json"
        if code_file.exists():
            try:
                with open(code_file, 'r', encoding='utf-8') as f:
                    code_validation = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load code validation for {doc_stem}: {e}[/yellow]")

        return api_validation, code_validation

    def _preprocess_markdown_snippets(
        self,
        content: str,
        markdown_path: Path,
        repo_root: Path
    ) -> tuple[str, list[str]]:
        """
        Pre-resolve common documentation snippet patterns (Level 2 - Fast Path).

        This is an optimization to reduce agent tool calls. Deterministically resolves
        common snippet patterns like MkDocs Material --8<-- includes. Falls back to
        agent resolution for complex cases.

        Args:
            content: Raw markdown content
            markdown_path: Path to the markdown file (for relative path resolution)
            repo_root: Repository root directory

        Returns:
            Tuple of (processed_content, warnings)
            - processed_content: Markdown with resolved snippets
            - warnings: List of resolution warnings/failures
        """
        warnings = []
        processed = content

        # Pattern 1: MkDocs Material snippets --8<-- "path/to/file.py:label"
        snippet_pattern = r'--8<--\s+"([^"]+)"'
        matches = list(re.finditer(snippet_pattern, processed))

        if not matches:
            return processed, warnings

        replacements = []  # Collect replacements to apply all at once

        for match in matches:
            reference = match.group(1)  # e.g., "python/tests/test_file.py:imports"

            try:
                # Parse reference
                if ':' in reference:
                    file_path, label = reference.rsplit(':', 1)
                else:
                    file_path, label = reference, None

                # Resolve path relative to repo root
                full_path = repo_root / file_path

                if not full_path.exists():
                    warnings.append(f"Snippet reference not found: {reference}")
                    continue

                # Read source file
                with open(full_path, 'r', encoding='utf-8') as f:
                    source_content = f.read()

                # Extract snippet
                snippet_code = None
                if label:
                    # Look for --8<-- [start:label] and [end:label] markers
                    start_marker = f"# --8<-- [start:{label}]"
                    end_marker = f"# --8<-- [end:{label}]"

                    start_idx = source_content.find(start_marker)
                    end_idx = source_content.find(end_marker)

                    if start_idx != -1 and end_idx != -1:
                        snippet_code = source_content[start_idx + len(start_marker):end_idx].strip()
                    else:
                        warnings.append(f"Snippet markers not found for: {reference}")
                        continue
                else:
                    # No label - include entire file
                    snippet_code = source_content

                if snippet_code:
                    # Dedent to normalize indentation from source context
                    # (snippets from test files may have function-level indentation)
                    snippet_code = textwrap.dedent(snippet_code)

                    # AGGRESSIVE NORMALIZATION: Strip ALL leading whitespace from each line
                    # This ensures code from test functions appears as top-level code
                    # (clarity agent should focus on content, not rendering artifacts)
                    snippet_lines = snippet_code.split('\n')
                    snippet_lines = [line.lstrip() if line.strip() else line for line in snippet_lines]
                    snippet_code = '\n'.join(snippet_lines)

                    # Store replacement (match, snippet_code)
                    replacements.append((match, snippet_code))

            except Exception as e:
                warnings.append(f"Failed to resolve snippet {reference}: {e}")

        # Apply all replacements (in reverse order to preserve match positions)
        for match, snippet_code in reversed(replacements):
            processed = processed[:match.start()] + snippet_code + processed[match.end():]

        if replacements:
            console.print(f"[dim]Pre-resolved and dedented {len(replacements)} snippet(s)[/dim]")

        if warnings:
            for warning in warnings:
                console.print(f"[yellow]Snippet warning: {warning}[/yellow]")

        return processed, warnings

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from Claude's response, handling markdown code blocks.

        Args:
            response_text: Raw response text from Claude

        Returns:
            Parsed JSON dict or None if parsing failed
        """
        # Try to find JSON in markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # No code block, try to parse entire response
            json_str = response_text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            console.print(f"[red]Failed to parse JSON response: {e}[/red]")
            console.print(f"[yellow]Response preview:[/yellow] {response_text[:200]}...")
            return None

    async def get_claude_response(
        self,
        client: ClaudeSDKClient,
        prompt: str,
        logger: Optional[Any],
        messages_log_file: Optional[Path]
    ) -> str:
        """
        Get response from Claude and log messages.

        Args:
            client: Claude SDK client
            prompt: User prompt
            logger: Optional logger instance
            messages_log_file: Optional path to messages log file

        Returns:
            Response text from Claude
        """
        # Log the user prompt
        if messages_log_file:
            user_message_entry = {
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": prompt
            }
            with open(messages_log_file, 'a', encoding='utf-8') as f:
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
                    with open(messages_log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(assistant_message_entry) + '\n')
                else:
                    # Original behavior when no logger
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

        return response_text

    async def analyze_document(self, extraction_file: Path) -> Optional[ClarityValidationOutput]:
        """
        Analyze clarity and structure of a single document.

        Args:
            extraction_file: Path to extraction JSON file

        Returns:
            ClarityValidationOutput with all clarity evaluation results, or None if failed
        """
        start_time = datetime.now()

        try:
            # Load extraction data
            with open(extraction_file, 'r', encoding='utf-8') as f:
                extraction_data = json.load(f)

            document_page = extraction_data.get("page", "unknown")
            library = extraction_data.get("library", "unknown")
            version = extraction_data.get("version", "latest")
            language = extraction_data.get("language", "python")

            # Read original markdown content
            # Try to find the markdown file in the repository
            markdown_path = self.repository_folder / document_page
            if not markdown_path.exists():
                # Try searching for the file
                possible_paths = list(self.repository_folder.rglob(document_page))
                if possible_paths:
                    markdown_path = possible_paths[0]
                else:
                    console.print(f"[yellow]Warning: Could not find markdown file {document_page}[/yellow]")
                    return None

            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Load validation results from previous agents
            doc_stem = extraction_file.stem.replace('_analysis', '')
            api_validation, code_validation = self._load_validation_results(doc_stem)

            # Pre-process snippets (Level 2 - deterministic fast path)
            processed_content, snippet_warnings = self._preprocess_markdown_snippets(
                content,
                markdown_path,
                self.repository_folder
            )

            # Create per-document logger
            from stackbench.hooks import create_agent_hooks, AgentLogger

            messages_log_file = None
            if self.validation_log_dir:
                clarity_logs_dir = self.validation_log_dir / "clarity_logs" / doc_stem
                clarity_logs_dir.mkdir(parents=True, exist_ok=True)

                agent_log = clarity_logs_dir / "agent.log"
                tools_log = clarity_logs_dir / "tools.jsonl"
                messages_log_file = clarity_logs_dir / "messages.jsonl"
                logger = AgentLogger(agent_log, tools_log)
            else:
                logger = None

            # Create hooks
            hooks = create_agent_hooks(
                agent_type="clarity_validation",
                logger=logger,
                output_dir=self.output_folder,
                validation_log_dir=self.validation_log_dir
            )

            # Create options with MCP server configured
            import sys
            options = ClaudeAgentOptions(
                system_prompt=CLARITY_SYSTEM_PROMPT,
                allowed_tools=["Read"],  # Read tool + MCP tools
                permission_mode="bypassPermissions",  # Required for MCP tools to work without prompting
                # Note: Validation hooks will still work because they intercept Write calls before execution
                hooks=hooks,
                cwd=str(Path.cwd()),
                mcp_servers={
                    "clarity-scoring": {
                        "command": sys.executable,
                        "args": ["-m", "stackbench.mcp_servers.clarity_scoring_server"],
                    }
                }
            )

            # Ask Claude to analyze
            async with ClaudeSDKClient(options=options) as client:
                prompt = create_clarity_validation_prompt(
                    document_page=document_page,
                    markdown_file_path=str(markdown_path.absolute()),
                    repository_root=str(self.repository_folder.absolute()),
                    library=library,
                    version=version,
                    language=language,
                    content=processed_content,  # Use pre-processed content with resolved snippets
                    api_validation=api_validation,
                    code_validation=code_validation
                )

                response_text = await self.get_claude_response(client, prompt, logger, messages_log_file)
                clarity_data = self.extract_json_from_response(response_text)

                if not clarity_data:
                    console.print(f"[red]Failed to extract JSON from response for {document_page}[/red]")
                    return None

            # Agent now returns complete analysis including MCP results
            console.print(f"[dim]Agent completed analysis with MCP scoring[/dim]")

            # Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Combine snippet warnings with agent warnings
            all_warnings = snippet_warnings + clarity_data.get('warnings', [])

            # Extract data from agent response (which includes MCP tool call results)
            issues = clarity_data.get('clarity_issues', [])
            clarity_score_data = clarity_data.get('clarity_score', {})
            roadmap_result = clarity_data.get('improvement_roadmap', {})
            explanation_result = clarity_data.get('score_explanation', {})

            # Validate required fields are present
            if not clarity_score_data:
                console.print(f"[red]Agent response missing clarity_score (MCP tool not called?)[/red]")
                return None
            if not roadmap_result:
                console.print(f"[red]Agent response missing improvement_roadmap (MCP tool not called?)[/red]")
                return None
            if not explanation_result:
                console.print(f"[red]Agent response missing score_explanation (MCP tool not called?)[/red]")
                return None

            # Validate clarity_score has required fields (detect if agent returned wrong structure)
            required_score_fields = ['overall_score', 'tier', 'instruction_clarity', 'logical_flow',
                                      'completeness', 'consistency', 'prerequisite_coverage']
            missing_fields = [f for f in required_score_fields if f not in clarity_score_data]
            if missing_fields:
                console.print(f"[red]Agent returned invalid clarity_score structure. Missing fields: {missing_fields}[/red]")
                console.print(f"[dim]Received: {list(clarity_score_data.keys())}[/dim]")
                console.print(f"[yellow]Agent may have hallucinated a response instead of calling MCP tools properly.[/yellow]")
                console.print(f"[yellow]This is likely due to:[/yellow]")
                console.print(f"[yellow]  1. Prompt too complex/long for the agent to follow[/yellow]")
                console.print(f"[yellow]  2. Agent not understanding it should call MCP tools[/yellow]")
                console.print(f"[yellow]  3. MCP tools not recognized (check server configuration)[/yellow]")
                console.print(f"[yellow]Skipping this document. Check agent logs for details.[/yellow]")
                return None

            # Construct ClarityValidationOutput from agent response
            analysis = ClarityValidationOutput(
                validation_id=str(uuid4()),
                validated_at=datetime.utcnow().isoformat() + 'Z',
                source_file=extraction_file.name,
                document_page=document_page,
                library=library,
                version=version,
                language=language,
                clarity_score=ClarityScore(**clarity_score_data),
                clarity_issues=[ClarityIssue(**issue) for issue in issues],
                structural_issues=[StructuralIssue(**issue) for issue in clarity_data.get('structural_issues', [])],
                technical_accessibility=TechnicalAccessibility(**clarity_data.get('technical_accessibility', {})),
                improvement_roadmap=ImprovementRoadmap(**roadmap_result),
                score_explanation=ScoreExplanation(**explanation_result),
                summary=clarity_data.get('summary', {}),
                processing_time_ms=processing_time,
                warnings=all_warnings
            )

            # Validate JSON before saving
            from stackbench.hooks import validate_validation_output_json

            analysis_dict = json.loads(analysis.model_dump_json())
            filename = f"{extraction_file.stem.replace('_analysis', '')}_clarity.json"

            passed, errors = validate_validation_output_json(
                analysis_dict,
                filename,
                self.validation_log_dir,
                validation_type="clarity_validation"
            )

            if not passed:
                console.print(f"⚠️  {extraction_file.stem.replace('_analysis', '')} - Clarity validation failed: {errors[:2]}")

            # Save to file
            output_file = self.output_folder / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(analysis.model_dump_json(indent=2))

            return analysis

        except Exception as e:
            console.print(f"[red]Error analyzing {extraction_file.name}: {e}[/red]")
            import traceback
            traceback.print_exc()
            return None

    async def _analyze_document_with_save(
        self,
        extraction_file: Path,
        semaphore: asyncio.Semaphore,
        progress: Optional[Progress] = None,
        task: Optional[Any] = None
    ) -> Optional[ClarityValidationOutput]:
        """
        Worker method for parallel processing with semaphore.

        Args:
            extraction_file: Path to extraction file
            semaphore: Semaphore for limiting concurrent workers
            progress: Optional progress bar
            task: Optional progress task

        Returns:
            ClarityValidationOutput or None
        """
        async with semaphore:
            result = await self.analyze_document(extraction_file)
            if progress and task:
                progress.advance(task)
            return result

    async def analyze_all_documents(self) -> Dict[str, Any]:
        """
        Analyze all extraction files using parallel workers.

        Returns:
            Summary dictionary with overall statistics
        """
        start_time = datetime.now()

        # Find all extraction files
        extraction_files = sorted(self.extraction_folder.glob("*_analysis.json"))

        if not extraction_files:
            console.print("[yellow]No extraction files found to validate[/yellow]")
            return {
                "validation_timestamp": datetime.utcnow().isoformat() + 'Z',
                "total_documents": 0,
                "average_clarity_score": 0.0,
                "total_issues_found": 0,
                "critical_issues": 0,
                "warnings": 0,
                "validation_duration_seconds": 0.0,
                "num_workers": self.num_workers,
                "documents": []
            }

        console.print(f"\n📊 Analyzing {len(extraction_files)} documents for clarity...")

        # Create semaphore for worker limit
        semaphore = asyncio.Semaphore(self.num_workers)

        # Process in parallel with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Analyzing clarity ({self.num_workers} workers)...",
                total=len(extraction_files)
            )

            tasks = [
                self._analyze_document_with_save(f, semaphore, progress, task)
                for f in extraction_files
            ]
            results = await asyncio.gather(*tasks)

        # Filter out None results (failures)
        successful_results = [r for r in results if r is not None]

        if not successful_results:
            console.print("[red]All clarity validations failed[/red]")
            return {
                "validation_timestamp": datetime.utcnow().isoformat() + 'Z',
                "total_documents": len(extraction_files),
                "average_clarity_score": 0.0,
                "total_issues_found": 0,
                "critical_issues": 0,
                "warnings": 0,
                "validation_duration_seconds": (datetime.now() - start_time).total_seconds(),
                "num_workers": self.num_workers,
                "documents": []
            }

        # Aggregate statistics
        total_score = sum(r.clarity_score.overall_score for r in successful_results)
        avg_score = total_score / len(successful_results)

        total_issues = sum(
            r.summary.total_clarity_issues +
            r.summary.total_structural_issues +
            r.summary.total_technical_issues
            for r in successful_results
        )

        critical_issues = sum(
            r.summary.critical_clarity_issues +
            r.summary.critical_structural_issues
            for r in successful_results
        )

        warnings = sum(
            r.summary.warning_clarity_issues
            for r in successful_results
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Create per-document summaries
        doc_summaries = [
            {
                "document_page": r.document_page,
                "overall_score": r.clarity_score.overall_score,
                "total_issues": (
                    r.summary.get('total_clarity_issues', 0) +
                    r.summary.get('total_structural_issues', 0) +
                    r.summary.get('total_technical_issues', 0)
                ),
                "critical_issues": (
                    r.summary.get('critical_clarity_issues', 0) +
                    r.summary.get('critical_structural_issues', 0)
                ),
                "quality_rating": r.summary.get('overall_quality_rating', 'unknown')
            }
            for r in successful_results
        ]

        # Create summary
        summary = ClarityValidationSummary(
            validation_timestamp=datetime.utcnow().isoformat() + 'Z',
            total_documents=len(successful_results),
            average_clarity_score=avg_score,
            total_issues_found=total_issues,
            critical_issues=critical_issues,
            warnings=warnings,
            validation_duration_seconds=duration,
            num_workers=self.num_workers,
            documents=doc_summaries
        )

        # Save summary
        summary_file = self.output_folder / "validation_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary.model_dump_json(indent=2))

        console.print(f"[green]✓[/green] Clarity validation complete!")
        console.print(f"  Average Score: {avg_score:.1f}/10")
        console.print(f"  Critical Issues: {critical_issues}")
        console.print(f"  Warnings: {warnings}")
        console.print(f"  Duration: {duration:.1f}s")

        return summary.model_dump()
