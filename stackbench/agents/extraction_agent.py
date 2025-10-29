"""
Documentation Quality Analyzer - Extracts API signatures and code examples from markdown docs.

This agent uses Claude Code to analyze documentation files and extract structured information
about API signatures, code examples, imports, and usage patterns.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    CLINotFoundError,
    ProcessError,
)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Import centralized schemas
from stackbench.schemas import (
    APISignature,
    CodeExample,
    ExtractionResult,
    DocumentAnalysis,
    ExtractionSummary
)
from stackbench.utils import pydantic_to_json_example



# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are an expert code analyzer specializing in extracting structured information from technical documentation.

Your task is to analyze markdown documentation and extract:
1. API signatures (functions, methods, classes with their parameters) - ONLY for the PRIMARY library being documented
2. Code examples (complete, executable code snippets)
3. Library metadata (name, version, language)

CRITICAL FILTERING RULES:
- Extract ONLY signatures from the PRIMARY library being documented (e.g., if documenting lancedb, ignore pandas/pyarrow/numpy helper functions)
- Helper libraries (pandas, numpy, pyarrow) are used WITH the main library but should NOT have their signatures extracted
- Focus on the library's own API surface, not its dependencies
- If a signature is chained (e.g., db.create_table()), extract it if 'db' is from the primary library

Be thorough and precise for the PRIMARY library's API. Extract ALL of its signatures and examples.
Focus on accuracy - parameter names, types, and default values must be exact.

Always respond with valid JSON matching the requested schema.
"""

UNIFIED_EXTRACTION_PROMPT = """Analyze the following markdown documentation and extract ALL information in a single pass.

IMPORTANT - SNIPPET RESOLUTION:
If you see snippet references like:
- `--8<-- "path/to/file.py:label"` (MkDocs Material)
- `.. literalinclude:: path/to/file.py` (Sphinx)
- `{{{{< readfile file="path" >}}}}` (Hugo)

You MUST:
1. Use the Read tool to open the referenced file at: {repo_root}/<path>
2. Extract the actual code between the snippet markers:
   - For MkDocs: Look for `# --8<-- [start:label]` and `# --8<-- [end:label]`
   - For Sphinx: Read the specified line range
   - If no markers, read the entire file
3. Use the ACTUAL CODE for extraction, not the snippet reference

CRITICAL - PRIMARY LIBRARY FILTERING:
This documentation is for the PRIMARY library: "{library_name}"

You MUST:
1. Extract ONLY signatures/methods/functions from "{library_name}"
2. IGNORE signatures from helper/dependency libraries (pandas, numpy, pyarrow, etc.)
3. Helper libraries may appear in code examples but should NOT have their signatures extracted
4. Exception: If "{library_name}" methods are chained (e.g., db.create_table(), table.search()), extract them

Examples of what TO extract (assuming primary library is "mylib"):
- ✅ mylib.connect(uri)
- ✅ client.create_resource(name, data)  # client is from mylib.connect()
- ✅ resource.query(params)  # resource is from client.get_resource()
- ✅ await mylib.connect_async(uri)

Examples of what NOT to extract (helper/dependency libraries):
- ❌ pd.DataFrame(data)  # pandas helper
- ❌ json.loads(text)  # standard library helper
- ❌ np.array([...])  # numpy helper
- ❌ requests.get(url)  # requests helper

Extract:
1. **Library Information**: Primary library name, version (if mentioned), programming language
2. **API Signatures**: All function/class/method signatures from {library_name} ONLY (from RESOLVED code)
3. **Code Examples**: All executable code snippets (these CAN include helper libraries)

Documentation file location: {doc_path}
Repository root: {repo_root}
Primary library being documented: {library_name}

Documentation to analyze:
```markdown
{content}
```

Respond with a JSON object matching this exact schema:

```json
{{
  "library": "fastapi",
  "version": "0.104.1",
  "language": "python",
  "signatures": [
    {{
      "library": "fastapi",
      "function": "FastAPI",
      "method_chain": null,
      "params": ["title", "version"],
      "param_types": {{"title": "str", "version": "str"}},
      "defaults": {{"title": null, "version": null}},
      "imports": "from fastapi import FastAPI",
      "line": 45,
      "context": "Creating Applications",
      "raw_code": "app = FastAPI(title='My API', version='1.0.0')",
      "section_hierarchy": ["Getting Started", "Creating Applications"],
      "markdown_anchor": "#creating-applications",
      "code_block_index": 0
    }}
  ],
  "examples": [
    {{
      "library": "fastapi",
      "language": "python",
      "code": "from fastapi import FastAPI\\napp = FastAPI()\\n@app.get('/')\\ndef read_root():\\n    return {{'Hello': 'World'}}",
      "imports": "from fastapi import FastAPI",
      "has_main": false,
      "is_executable": true,
      "execution_context": "sync",
      "line": 67,
      "context": "Quick Start",
      "dependencies": ["fastapi"],
      "section_hierarchy": ["Getting Started", "Quick Start"],
      "markdown_anchor": "#quick-start",
      "code_block_index": 1,
      "snippet_source": {{"file": "examples/quickstart.py", "tags": ["hello_world"]}}  // or null if not from snippet
    }}
  ]
}}
```

Critical requirements:
- NEVER include snippet references in the output (no "--8<--", no "literalinclude")
- ALL code must be the actual resolved code from source files
- If you cannot resolve a snippet, note it in warnings but still try to extract what you can
- Extract ALL parameters including optional ones with defaults
- Be comprehensive - extract EVERYTHING, don't skip anything
- For each signature and example, capture its location context:
  - Track the full heading hierarchy (e.g., ["Getting Started", "Quick Start"])
  - Generate the markdown anchor for the section (e.g., "#quick-start")
  - Count code blocks within each section (0 for first, 1 for second, etc.)
  - If code comes from a snippet include (--8<--), set snippet_source to {{"file": "path/to/file.py", "tags": ["tag1", "tag2"]}}, otherwise null
- **IMPORTANT**: code_block_index MUST be an integer (use 0 if you cannot determine the index), NEVER null

**EXECUTION CONTEXT DETECTION (for code examples)**:
Set `execution_context` based on async patterns (Python/JS/TS):

- **"async"** - Contains `await`, `async def/function`, `async with/for`, or `.then()` chains
  - `await client.connect()` → "async"
  - `async function main() {{ }}` → "async"
  - `promise.then(...)` → "async"

- **"sync"** - Regular synchronous code without async patterns
  - `client.connect()` → "sync"
  - `const data = processData()` → "sync"

- **"not_executable"** - Incomplete snippets with `...`, placeholders, or missing context
  - `client.query(...)` → "not_executable"
  - `// ... rest of code` → "not_executable"

**Backwards compatibility**: Set `is_executable: true` if "sync", else `false`
"""


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

# All Pydantic models are now imported from stackbench.schemas
# This eliminates duplication and ensures consistency across all agents


# ============================================================================
# EXTRACTION AGENT
# ============================================================================

class DocumentationExtractionAgent:
    """Agent that extracts API signatures and code examples from markdown docs."""

    def __init__(
        self,
        docs_folder: Path,
        output_folder: Path,
        repo_root: Optional[Path] = None,
        default_version: str = "0.25.2",
        num_workers: int = 5,
        validation_log_dir: Optional[Path] = None
    ):
        """
        Initialize the extraction agent.

        Args:
            docs_folder: Path to the documentation folder
            output_folder: Path to save extraction results
            repo_root: Root directory of the repository (for resolving snippet references)
                      If None, will try to auto-detect from docs_folder
            default_version: Default library version to use if not found in docs (default: "0.25.2")
            num_workers: Number of parallel workers for extraction (default: 5)
            validation_log_dir: Optional directory for validation hook tracking logs
        """
        self.docs_folder = Path(docs_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.default_version = default_version
        self.num_workers = num_workers
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        # Determine repo root
        if repo_root:
            self.repo_root = Path(repo_root)
        else:
            # Try to auto-detect repo root by looking for common markers
            self.repo_root = self._find_repo_root(self.docs_folder)

        print(f"📁 Repository root: {self.repo_root}")
        print(f"📦 Default version: {self.default_version}")
        print(f"👷 Workers: {self.num_workers}")

        # Note: We don't create a logger here anymore - we create one per document
        # This allows us to have separate log files for each document
        if self.validation_log_dir:
            print(f"📋 Per-document logging enabled")
            print(f"   Logs will be saved to: {self.validation_log_dir}")

    def _find_repo_root(self, start_path: Path) -> Path:
        """
        Auto-detect repository root by looking for common markers.

        Args:
            start_path: Path to start searching from

        Returns:
            Path to repository root
        """
        current = start_path.resolve()

        # Look for common repo root markers
        repo_markers = ['.git', 'pyproject.toml', 'package.json', 'setup.py', 'Cargo.toml']

        while current != current.parent:
            for marker in repo_markers:
                if (current / marker).exists():
                    return current
            current = current.parent

        # Fallback to docs folder parent
        return start_path.parent

    
    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Claude's response, handling markdown code blocks."""
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
            print(f"   Response preview: {response_text[:300]}...")
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
    
    async def analyze_document(self, doc_path: Path, library_name: str) -> DocumentAnalysis:
        """
        Analyze a single markdown document and extract structured information.

        Args:
            doc_path: Path to the markdown document
            library_name: Primary library name to extract (required)

        Returns:
            DocumentAnalysis containing extracted signatures and examples
        """
        start_time = datetime.now()

        # Read document content
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        warnings = []

        # Create per-document logger with new directory structure
        from stackbench.hooks import create_agent_hooks, AgentLogger

        messages_log_file = None
        if self.validation_log_dir:
            doc_stem = doc_path.stem
            # New structure: logs/extraction_logs/<doc_name>/
            extraction_logs_dir = self.validation_log_dir / "extraction_logs" / doc_stem
            extraction_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = extraction_logs_dir / "agent.log"
            tools_log = extraction_logs_dir / "tools.jsonl"
            messages_log_file = extraction_logs_dir / "messages.jsonl"
            logger = AgentLogger(agent_log, tools_log)
        else:
            logger = None

        # Create hooks for this document
        hooks = create_agent_hooks(
            agent_type="extraction",
            logger=logger,
            output_dir=self.output_folder,
            validation_log_dir=self.validation_log_dir
        )

        # Create options with per-document hooks
        options = ClaudeAgentOptions(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            hooks=hooks,
            cwd=str(Path.cwd())
        )

        async with ClaudeSDKClient(options=options) as client:
            # Single unified extraction call
            extraction_prompt = UNIFIED_EXTRACTION_PROMPT.format(
                content=content,
                doc_path=str(doc_path),
                repo_root=str(self.repo_root),
                library_name=library_name
            )
            response_text = await self.get_claude_response(client, extraction_prompt, logger, messages_log_file)

            # Parse response
            extracted_data = self.extract_json_from_response(response_text)

            if not extracted_data:
                warnings.append("Failed to parse extraction response")
                # Return minimal result
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return DocumentAnalysis(
                    page=doc_path.name,
                    library="unknown",
                    version=self.default_version,  # Use default version on failure
                    language="unknown",
                    signatures=[],
                    examples=[],
                    processed_at=datetime.now().isoformat(),
                    total_signatures=0,
                    total_examples=0,
                    warnings=warnings,
                    processing_time_ms=processing_time
                )

            # Parse into Pydantic models
            try:
                extraction_result = ExtractionResult(**extracted_data)

                # Use default version if not extracted from docs
                version = extraction_result.version or self.default_version

                # Create analysis result
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

                analysis = DocumentAnalysis(
                    page=doc_path.name,
                    library=extraction_result.library,
                    version=version,  # Use version with default fallback
                    language=extraction_result.language,
                    signatures=extraction_result.signatures,
                    examples=extraction_result.examples,
                    processed_at=datetime.now().isoformat(),
                    total_signatures=len(extraction_result.signatures),
                    total_examples=len(extraction_result.examples),
                    warnings=warnings,
                    processing_time_ms=processing_time
                )
                
                return analysis
                
            except Exception as e:
                warnings.append(f"Failed to parse into Pydantic models: {e}")
                print(f"   ⚠️  Pydantic validation error: {e}")

                # Log validation failure to messages.jsonl
                if messages_log_file:
                    validation_failure_message = {
                        "timestamp": datetime.now().isoformat(),
                        "role": "system",
                        "content": [{
                            "type": "text",
                            "text": f"Pydantic validation failed for extracted data. Falling back to empty result. Error: {str(e)[:500]}"
                        }]
                    }
                    with open(messages_log_file, 'a') as f:
                        f.write(json.dumps(validation_failure_message) + '\n')

                # Fallback to basic parsing
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return DocumentAnalysis(
                    page=doc_path.name,
                    library=extracted_data.get("library", "unknown"),
                    version=extracted_data.get("version") or self.default_version,  # Use default if not found
                    language=extracted_data.get("language", "unknown"),
                    signatures=[],
                    examples=[],
                    processed_at=datetime.now().isoformat(),
                    total_signatures=0,
                    total_examples=0,
                    warnings=warnings,
                    processing_time_ms=processing_time
                )
    
    async def process_document(
        self,
        doc_path: Path,
        library_name: str
    ) -> Optional[DocumentAnalysis]:
        """
        Process a single markdown document (extract signatures and examples).

        This method extracts API signatures and code examples from a single document,
        validates the output, and saves it to disk. Designed for use in worker pool patterns.

        Args:
            doc_path: Path to markdown file to process
            library_name: Primary library name to extract (required)

        Returns:
            DocumentAnalysis if successful, None if extraction failed
        """
        try:
            analysis = await self.analyze_document(doc_path, library_name)

            # Validate JSON before saving
            from stackbench.hooks import validate_extraction_json

            analysis_dict = json.loads(analysis.model_dump_json())
            filename = f"{doc_path.stem}_analysis.json"

            passed, errors = validate_extraction_json(
                analysis_dict,
                filename,
                self.validation_log_dir
            )

            if not passed:
                print(f"⚠️  {doc_path.name} - Validation failed: {errors[:2]}")

            # Save individual result
            output_file = self.output_folder / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(analysis.model_dump_json(indent=2))

            return analysis

        except Exception as e:
            print(f"❌ {doc_path.name} - Extraction failed: {e}")
            return None

    async def _process_document_with_save(
        self,
        doc_path: Path,
        library_name: str,
        semaphore: asyncio.Semaphore,
        progress: Dict[str, int]
    ) -> Optional[DocumentAnalysis]:
        """Process a single document with semaphore control and save results."""
        async with semaphore:
            try:
                analysis = await self.process_document(doc_path, library_name)

                if analysis:
                    progress['completed'] += 1
                    sigs = analysis.total_signatures
                    exs = analysis.total_examples
                    print(f"✅ [{progress['completed']}/{progress['total']}] {doc_path.name} - {sigs} signatures, {exs} examples")
                else:
                    progress['completed'] += 1

                return analysis

            except Exception as e:
                progress['completed'] += 1
                print(f"❌ [{progress['completed']}/{progress['total']}] {doc_path.name} - {e}")
                return None

    async def process_all_documents(self, library_name: str) -> ExtractionSummary:
        """
        Process all markdown files in the docs folder using parallel workers.

        Args:
            library_name: Primary library name to extract (required)

        Returns:
            ExtractionSummary containing results for all processed documents, including timing metrics
        """
        # Track overall extraction time
        extraction_start_time = datetime.now()

        # Find all markdown files
        md_files = list(self.docs_folder.glob("**/*.md"))

        if not md_files:
            print(f"❌ No markdown files found in {self.docs_folder}")
            return ExtractionSummary(
                total_documents=0,
                processed=0,
                total_signatures=0,
                total_examples=0,
                timestamp=datetime.now().isoformat(),
                documents=[]
            )

        print(f"\n📚 Extracting from {len(md_files)} documents ({self.num_workers} workers)")
        if library_name:
            print(f"🎯 Library: {library_name}")

        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self.num_workers)

        # Progress tracking
        progress = {'completed': 0, 'total': len(md_files)}

        # Process all documents in parallel with worker limit
        tasks = [
            self._process_document_with_save(doc_path, library_name, semaphore, progress)
            for doc_path in md_files
        ]

        results = await asyncio.gather(*tasks)

        # Filter out None results (failed extractions)
        results = [r for r in results if r is not None]

        # Calculate extraction duration
        extraction_end_time = datetime.now()
        extraction_duration_seconds = (extraction_end_time - extraction_start_time).total_seconds()

        # Create summary with timing information
        summary = ExtractionSummary(
            total_documents=len(md_files),
            processed=len(results),
            total_signatures=sum(r.total_signatures for r in results),
            total_examples=sum(r.total_examples for r in results),
            timestamp=datetime.now().isoformat(),
            extraction_duration_seconds=round(extraction_duration_seconds, 2),
            num_workers=self.num_workers,
            documents=results
        )

        # Save summary
        summary_file = self.output_folder / "extraction_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary.model_dump_json(indent=2))

        print(f"\n✨ Extraction complete: {summary.processed}/{summary.total_documents} docs, {summary.total_signatures} signatures, {summary.total_examples} examples ({extraction_duration_seconds:.1f}s)")

        return summary


# This module is designed to be used as a library.
# For CLI usage, see stackbench.cli module.