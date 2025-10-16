"""
Documentation Clarity & Structure Validation Agent

This agent evaluates documentation quality from a user experience perspective using Claude Code.
It uses an LLM-as-judge approach to assess clarity, logical flow, completeness, and consistency.
"""

import json
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from claude_code_sdk import ClaudeSDKClient, ClaudeAgentOptions

console = Console()


# ============================================================================
# Pydantic Models (Output JSON Schema)
# ============================================================================

class ClarityIssue(BaseModel):
    """A clarity or instructional quality issue found in documentation."""

    type: str = Field(
        description="Issue type: missing_prerequisite, logical_gap, unclear_explanation, "
                    "terminology_inconsistency, ambiguous_reference, missing_context, "
                    "assumption_of_knowledge, incomplete_step"
    )

    severity: str = Field(
        description="Severity: critical (blocks progress), warning (causes confusion), "
                    "info (nice-to-have improvement)"
    )

    line: int = Field(
        description="Approximate line number in original markdown document where issue occurs"
    )

    section: str = Field(
        description="Section or heading where issue appears (e.g., 'Quickstart Guide', 'Configuration')"
    )

    step_number: Optional[int] = Field(
        None,
        description="Step number if this is part of a sequential tutorial (e.g., Step 3 of 5)"
    )

    message: str = Field(
        description="Clear, actionable description of the issue"
    )

    suggested_fix: Optional[str] = Field(
        None,
        description="Specific suggestion for how to improve the documentation"
    )

    affected_code: Optional[str] = Field(
        None,
        description="Code snippet related to this issue (if applicable)"
    )

    context_quote: Optional[str] = Field(
        None,
        description="Quote from documentation showing the problematic text"
    )


class StructuralIssue(BaseModel):
    """A structural or organizational issue in documentation."""

    type: str = Field(
        description="Issue type: missing_prerequisites_section, buried_prerequisites, "
                    "missing_step_numbers, inconsistent_section_organization, "
                    "no_difficulty_indicator, no_time_estimate, missing_toc, "
                    "poor_heading_hierarchy"
    )

    severity: str = Field(
        description="Severity: critical, warning, info"
    )

    location: str = Field(
        description="Where in document this occurs (e.g., 'Prerequisites mentioned in Step 5', "
                    "'No step numbers in Installation section')"
    )

    message: str = Field(
        description="Clear description of the structural problem"
    )

    suggested_fix: Optional[str] = Field(
        None,
        description="How to improve the document structure"
    )


class ClarityScore(BaseModel):
    """Rubric-based clarity evaluation scores (0.0-10.0 scale)."""

    overall_score: float = Field(
        ge=0.0, le=10.0,
        description="Overall clarity score (average of dimension scores)"
    )

    instruction_clarity: float = Field(
        ge=0.0, le=10.0,
        description="How clear and actionable are the instructions? "
                    "10=perfect clarity, 0=completely unclear"
    )

    logical_flow: float = Field(
        ge=0.0, le=10.0,
        description="Do steps build logically on each other? "
                    "10=perfect progression, 0=complete disconnection"
    )

    completeness: float = Field(
        ge=0.0, le=10.0,
        description="Are all necessary details included? "
                    "10=nothing missing, 0=critical gaps everywhere"
    )

    consistency: float = Field(
        ge=0.0, le=10.0,
        description="Is terminology and style consistent throughout? "
                    "10=perfect consistency, 0=constant inconsistencies"
    )

    prerequisite_coverage: float = Field(
        ge=0.0, le=10.0,
        description="Are prerequisites clearly stated and complete? "
                    "10=all prereqs upfront, 0=no prereq info"
    )

    evaluation_criteria: dict = Field(
        description="Explanation of what was measured for each dimension"
    )

    scoring_rationale: Optional[str] = Field(
        None,
        description="Overall explanation of scores"
    )


class BrokenLink(BaseModel):
    """A broken link found in documentation."""
    url: str
    line: int
    link_text: str
    error: str  # "404 Not Found", "Connection timeout", etc.


class MissingAltText(BaseModel):
    """An image without alt text."""
    image_path: str
    line: int


class CodeBlockIssue(BaseModel):
    """A code block without language specification."""
    line: int
    content_preview: str  # First 50 chars


class TechnicalAccessibility(BaseModel):
    """Technical accessibility validation results."""

    broken_links: list[BrokenLink] = Field(
        default_factory=list,
        description="All broken links found (404s, timeouts, etc.)"
    )

    missing_alt_text: list[MissingAltText] = Field(
        default_factory=list,
        description="Images without alt text"
    )

    code_blocks_without_language: list[CodeBlockIssue] = Field(
        default_factory=list,
        description="Code blocks missing language specification"
    )

    total_links_checked: int = Field(
        description="Total number of links validated"
    )

    total_images_checked: int = Field(
        description="Total number of images validated"
    )

    total_code_blocks_checked: int = Field(
        description="Total number of code blocks validated"
    )

    all_validated: bool = Field(
        description="Whether all technical checks passed"
    )


class DocumentClarityAnalysis(BaseModel):
    """Complete clarity and structure analysis for a documentation file."""

    validation_id: str = Field(
        description="Unique UUID for this validation run"
    )

    validated_at: str = Field(
        description="ISO timestamp of when validation occurred"
    )

    source_file: str = Field(
        description="Source extraction file (e.g., 'quickstart_analysis.json')"
    )

    document_page: str = Field(
        description="Original markdown filename (e.g., 'quickstart.md')"
    )

    library: str = Field(
        description="Library being documented"
    )

    version: str = Field(
        description="Library version"
    )

    language: str = Field(
        description="Programming language (python, javascript, etc.)"
    )

    clarity_score: ClarityScore = Field(
        description="Numerical clarity scores across dimensions"
    )

    clarity_issues: list[ClarityIssue] = Field(
        default_factory=list,
        description="All clarity and instructional issues found"
    )

    structural_issues: list[StructuralIssue] = Field(
        default_factory=list,
        description="All structural and organizational issues found"
    )

    technical_accessibility: TechnicalAccessibility = Field(
        description="Technical validation results (links, images, code blocks)"
    )

    summary: dict = Field(
        description="Summary statistics: total_issues, critical_issues, warnings, info, etc."
    )

    processing_time_ms: int = Field(
        description="Time taken to analyze this document in milliseconds"
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings during analysis"
    )


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

Your role is to evaluate documentation from the perspective of a new user trying to follow tutorials and guides. You assess:

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
- Provide actionable suggestions, not just criticism

SCORING RUBRIC (0.0-10.0):
- **10.0**: Perfect clarity, could not be improved
- **8.0-9.0**: Excellent, only minor polish needed
- **6.0-7.0**: Good, some clear improvements needed
- **4.0-5.0**: Acceptable, multiple issues to address
- **2.0-3.0**: Poor, significant problems blocking understanding
- **0.0-1.0**: Unusable, cannot be followed

SEVERITY LEVELS:
- **critical**: Issue blocks user progress entirely (missing prerequisite, broken logical flow)
- **warning**: Issue causes confusion but is workaroundable (terminology inconsistency, unclear wording)
- **info**: Nice-to-have improvement (adding time estimates, difficulty indicators)

Always be thorough, specific, and constructive. Your goal is to help documentation reach a 9+ clarity score."""


def create_clarity_validation_prompt(document_page: str, library: str, version: str, language: str, content: str) -> str:
    """Create the validation prompt for analyzing a specific document."""
    return f"""Analyze the following documentation for clarity, structure, and instructional quality.

**Document Information:**
- Page: {document_page}
- Library: {library} v{version}
- Language: {language}

**Your Task:**
1. **Read through the entire document** as if you're a new user trying to follow it
2. **Identify clarity issues** with specific locations (section, line, step number)
3. **Score the documentation** on 5 dimensions (0.0-10.0 scale)
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
- Use the RUBRIC: Score based on the 0-10 scale defined in your system prompt
- Check ALL links: Validate that internal and external links are not broken
- Validate images: Check for missing alt text
- Check code blocks: Ensure all have language specification (```python, not just ```)

**OUTPUT FORMAT - Respond with ONLY this JSON structure:**

```json
{{
  "clarity_score": {{
    "overall_score": 7.5,
    "instruction_clarity": 8.0,
    "logical_flow": 6.0,
    "completeness": 7.0,
    "consistency": 8.5,
    "prerequisite_coverage": 7.0,
    "evaluation_criteria": {{
      "instruction_clarity": "Measured by: clarity of commands, completeness of examples, explanation of outcomes",
      "logical_flow": "Measured by: whether steps build on each other, absence of gaps, proper sequencing",
      "completeness": "Measured by: all prerequisites mentioned, all details included, edge cases covered",
      "consistency": "Measured by: terminology consistency, code style consistency, similar operations explained similarly",
      "prerequisite_coverage": "Measured by: prerequisites listed upfront, version requirements specified, system requirements mentioned"
    }},
    "scoring_rationale": "Overall strong tutorial with clear instructions, but Step 3 references config.yaml not created earlier (breaks logical flow), and prerequisites are mentioned mid-tutorial instead of at top. Consistency is excellent."
  }},
  "clarity_issues": [
    {{
      "type": "logical_gap",
      "severity": "critical",
      "line": 45,
      "section": "Configuration",
      "step_number": 3,
      "message": "Step 3 references 'config.yaml' but this file was never created or explained in prior steps",
      "suggested_fix": "Add Step 2b: Create config.yaml with example content showing required fields (host, port, database_name)",
      "affected_code": "config = lancedb.Config.from_file('config.yaml')",
      "context_quote": "Now load your configuration: config = lancedb.Config.from_file('config.yaml')"
    }}
  ],
  "structural_issues": [
    {{
      "type": "buried_prerequisites",
      "severity": "warning",
      "location": "Prerequisites mentioned throughout tutorial (lines 87, 102, 156) instead of upfront",
      "message": "Prerequisites are scattered throughout the document rather than consolidated at the beginning",
      "suggested_fix": "Create a 'Prerequisites' section at the top listing all requirements: Python 3.8+, Docker, pip, Git"
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
        "content_preview": "pip install lancedb"
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

**IMPORTANT NOTES:**
- Respond ONLY with the JSON - no explanatory text before or after
- Include line numbers for EVERY issue
- Be specific about sections and steps
- Provide actionable suggested_fix for each issue
- Actually check links if possible (use Read tool to verify internal links)
- Count all links, images, and code blocks accurately
- Overall quality rating: "excellent" (8+), "good" (6-7.9), "needs_improvement" (4-5.9), "poor" (<4)"""


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
        response = await client.send_message(prompt)

        # Log messages if logger provided
        if logger and messages_log_file:
            messages = await client.get_messages()
            with open(messages_log_file, 'a', encoding='utf-8') as f:
                for msg in messages:
                    f.write(json.dumps(msg) + '\n')

        return response

    async def analyze_document(self, extraction_file: Path) -> Optional[DocumentClarityAnalysis]:
        """
        Analyze clarity and structure of a single document.

        Args:
            extraction_file: Path to extraction JSON file

        Returns:
            DocumentClarityAnalysis with all clarity evaluation results, or None if failed
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

            # Create per-document logger
            from stackbench.hooks import create_agent_hooks, AgentLogger

            messages_log_file = None
            if self.validation_log_dir:
                doc_stem = extraction_file.stem.replace('_analysis', '')
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

            # Create options
            options = ClaudeAgentOptions(
                system_prompt=CLARITY_SYSTEM_PROMPT,
                allowed_tools=["Read"],  # Only needs to read files, not execute
                permission_mode="acceptEdits",
                hooks=hooks,
                cwd=str(Path.cwd())
            )

            # Ask Claude to analyze
            async with ClaudeSDKClient(options=options) as client:
                prompt = create_clarity_validation_prompt(
                    document_page=document_page,
                    library=library,
                    version=version,
                    language=language,
                    content=content
                )

                response_text = await self.get_claude_response(client, prompt, logger, messages_log_file)
                clarity_data = self.extract_json_from_response(response_text)

                if not clarity_data:
                    console.print(f"[red]Failed to extract JSON from response for {document_page}[/red]")
                    return None

                # Calculate processing time
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

                # Construct DocumentClarityAnalysis
                analysis = DocumentClarityAnalysis(
                    validation_id=str(uuid4()),
                    validated_at=datetime.utcnow().isoformat() + 'Z',
                    source_file=extraction_file.name,
                    document_page=document_page,
                    library=library,
                    version=version,
                    language=language,
                    clarity_score=ClarityScore(**clarity_data.get('clarity_score', {})),
                    clarity_issues=[ClarityIssue(**issue) for issue in clarity_data.get('clarity_issues', [])],
                    structural_issues=[StructuralIssue(**issue) for issue in clarity_data.get('structural_issues', [])],
                    technical_accessibility=TechnicalAccessibility(**clarity_data.get('technical_accessibility', {})),
                    summary=clarity_data.get('summary', {}),
                    processing_time_ms=processing_time,
                    warnings=clarity_data.get('warnings', [])
                )

                # Save to file
                output_file = self.output_folder / f"{extraction_file.stem.replace('_analysis', '')}_clarity.json"
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
    ) -> Optional[DocumentClarityAnalysis]:
        """
        Worker method for parallel processing with semaphore.

        Args:
            extraction_file: Path to extraction file
            semaphore: Semaphore for limiting concurrent workers
            progress: Optional progress bar
            task: Optional progress task

        Returns:
            DocumentClarityAnalysis or None
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
            r.summary.get('total_clarity_issues', 0) +
            r.summary.get('total_structural_issues', 0) +
            r.summary.get('total_technical_issues', 0)
            for r in successful_results
        )

        critical_issues = sum(
            r.summary.get('critical_clarity_issues', 0) +
            r.summary.get('critical_structural_issues', 0)
            for r in successful_results
        )

        warnings = sum(
            r.summary.get('warning_clarity_issues', 0)
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
