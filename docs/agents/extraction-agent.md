# Extraction Agent

## Objective

The Extraction Agent analyzes markdown documentation files to extract structured information about:
- **API signatures**: Functions, methods, and classes with their parameters, types, and defaults
- **Code examples**: Executable code snippets with context and dependencies
- **Library metadata**: Name, version, and programming language

This agent is the **first stage** of the Stackbench pipeline and provides the foundational data that all subsequent validation agents use.

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │ ◄── YOU ARE HERE
│  (Parallel Workers)     │
└─────────────────────────┘
            ↓
            ↓ (Produces structured JSON)
            ↓
┌─────────────────────────┐
│ API Validation Agent    │
│ Code Validation Agent   │
│ Clarity Validation Agent│
│ API Completeness Agent  │
└─────────────────────────┘
```

**Stage**: 1 (First)
**Runs**: In parallel across multiple documents (default: 5 workers)
**Dependencies**: None (no dependencies on other agents)
**Consumers**: All validation agents depend on this agent's output

## Inputs

### Required
- **`docs_folder`** (Path): Directory containing markdown documentation files
- **`output_folder`** (Path): Directory to save extraction results
- **`library_name`** (str): Name of the primary library being documented (e.g., "lancedb", "fastapi")

### Optional
- **`repo_root`** (Path): Repository root for resolving snippet references (`--8<--` directives). Auto-detected if not provided.
- **`default_version`** (str): Library version to use if not found in docs (default: "0.25.2")
- **`num_workers`** (int): Number of parallel workers for extraction (default: 5)
- **`validation_log_dir`** (Path): Directory for validation hooks and tool logs

### Environment
- Markdown files (`.md`) in `docs_folder`
- Optional: Source files for snippet resolution (e.g., `python/tests/test_*.py`)

## Expected Output

### Output Files

For each markdown file `{doc_name}.md`, produces:
```
output_folder/
├── {doc_name}_analysis.json       # Structured extraction data
└── extraction_summary.json        # Aggregate statistics
```

### Output Schema (`{doc_name}_analysis.json`)

```json
{
  "page": "quickstart.md",
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",
  "signatures": [
    {
      "library": "lancedb",
      "function": "connect",
      "method_chain": null,
      "params": ["uri", "read_consistency_interval"],
      "param_types": {
        "uri": "str",
        "read_consistency_interval": "Optional[timedelta]"
      },
      "defaults": {
        "read_consistency_interval": null
      },
      "imports": "import lancedb",
      "line": 45,
      "context": "Creating a Database",
      "raw_code": "db = lancedb.connect(\"./data/sample-lancedb\")",
      "section_hierarchy": ["Getting Started", "Creating a Database"],
      "markdown_anchor": "#creating-a-database",
      "code_block_index": 0
    }
  ],
  "examples": [
    {
      "library": "lancedb",
      "language": "python",
      "code": "import lancedb\ndb = lancedb.connect(\"./data/sample-lancedb\")",
      "imports": "import lancedb",
      "has_main": false,
      "is_executable": true,
      "execution_context": "sync",
      "line": 45,
      "context": "Quick Start",
      "dependencies": ["lancedb"],
      "section_hierarchy": ["Getting Started", "Quick Start"],
      "markdown_anchor": "#quick-start",
      "code_block_index": 0,
      "snippet_source": null
    }
  ],
  "processed_at": "2025-01-15T10:30:00Z",
  "total_signatures": 5,
  "total_examples": 3,
  "warnings": [],
  "processing_time_ms": 2500
}
```

### Summary File (`extraction_summary.json`)

```json
{
  "total_documents": 7,
  "processed": 7,
  "total_signatures": 35,
  "total_examples": 28,
  "timestamp": "2025-01-15T10:35:00Z",
  "extraction_duration_seconds": 15.3,
  "num_workers": 5,
  "documents": [...]
}
```

## Pseudocode

```python
# High-level algorithm
async def process_all_documents(docs_folder, library_name):
    """Process all markdown files in parallel."""

    # 1. Discovery phase
    md_files = glob(docs_folder, "**/*.md")

    # 2. Parallel processing with worker pool
    semaphore = Semaphore(num_workers)
    tasks = [
        process_document(doc_path, library_name, semaphore)
        for doc_path in md_files
    ]

    results = await gather(*tasks)

    # 3. Aggregate and save summary
    save_summary(results)

    return results


async def process_document(doc_path, library_name):
    """Extract from a single document."""

    # 1. Read markdown content
    content = read_file(doc_path)

    # 2. Create Claude agent with hooks
    hooks = create_validation_hooks() + create_logging_hooks()

    # 3. Ask Claude to extract structured data
    prompt = f"""
    Analyze this documentation for {library_name}.
    Extract:
    - API signatures (from {library_name} ONLY)
    - Code examples
    - Library metadata

    IMPORTANT:
    - Resolve snippet references (--8<-- "path/to/file.py:label")
    - Extract location context (section hierarchy, line numbers)
    - Detect execution context (sync vs async vs not_executable)

    Documentation: {content}
    """

    response = await claude.query(prompt)

    # 4. Parse and validate JSON response
    extracted_data = parse_json(response)
    validate_against_schema(extracted_data)  # Via hook

    # 5. Save individual result
    save_json(output_folder / f"{doc_name}_analysis.json", extracted_data)

    return extracted_data


# Key extraction logic within Claude's processing
def claude_extraction_logic(content, library_name, repo_root):
    """What Claude does internally."""

    # 1. Identify code blocks
    code_blocks = extract_code_blocks(content)

    # 2. For each code block:
    for block in code_blocks:
        # a. Check for snippet references
        if "--8<--" in block:
            # Use Read tool to resolve
            actual_code = read_snippet_from_source(repo_root, block)
        else:
            actual_code = block

        # b. Classify: signature or example?
        if is_api_signature(actual_code, library_name):
            # Extract function name, params, types, defaults
            signatures.append(extract_signature(actual_code))

        if is_executable_example(actual_code):
            # Extract imports, dependencies, execution context
            examples.append(extract_example(actual_code))

    # 3. Extract library metadata
    library_version = find_version_in_content(content)

    # 4. Return structured JSON
    return {
        "library": library_name,
        "version": library_version,
        "signatures": signatures,
        "examples": examples,
        ...
    }
```

## Key Features

### 1. **Primary Library Filtering**
Only extracts signatures from the primary library being documented. Ignores helper libraries (pandas, numpy, pyarrow).

```python
# ✅ Extracted for lancedb
lancedb.connect(uri)
db.create_table(name, data)  # db is from lancedb.connect()

# ❌ Ignored for lancedb (helper libraries)
pd.DataFrame(data)  # pandas helper
pa.schema([...])     # pyarrow helper
```

### 2. **Snippet Resolution**
Automatically resolves MkDocs Material snippet includes:

```markdown
--8<-- "python/tests/test_file.py:example"
```

Agent uses Read tool to:
1. Open `repo_root/python/tests/test_file.py`
2. Find markers: `# --8<-- [start:example]` and `# --8<-- [end:example]`
3. Extract actual code between markers
4. Use ACTUAL CODE for extraction

### 3. **Location Context Tracking**
Captures rich location metadata for better association:

```json
{
  "section_hierarchy": ["Getting Started", "Quick Start", "Sync API"],
  "markdown_anchor": "#quick-start",
  "code_block_index": 0,
  "line": 45,
  "snippet_source": {
    "file": "python/tests/test_pydantic.py",
    "tags": ["pydantic_schema"]
  }
}
```

### 4. **Execution Context Detection**
Classifies code examples by their async requirements:

- **`"sync"`**: Regular Python code that runs as-is
- **`"async"`**: Contains `await`/`async def` (needs async context)
- **`"not_executable"`**: Incomplete snippets or pseudocode

This enables the Code Validation Agent to execute examples correctly.

### 5. **Validation Hooks**
Uses programmatic hooks to validate JSON before writing:

```python
@PreToolUse hook
def validate_extraction_json(json_data):
    """Validate against ExtractionResult schema."""
    try:
        ExtractionResult(**json_data)
        return True  # Allow write
    except ValidationError as e:
        send_error_to_claude(e)
        return False  # Block write, agent must fix
```

## Logging & Debugging

### Per-Document Logs
```
validation_log_dir/extraction_logs/{doc_name}/
├── agent.log           # Human-readable log
├── tools.jsonl         # Tool calls (Read, Write)
└── messages.jsonl      # Full Claude conversation
```

### Log Contents
- All Read tool calls (snippet resolution)
- All Write tool calls (JSON output)
- Validation hook failures
- Pydantic schema errors
- Processing time per document

## Performance

- **Parallel workers**: Default 5, configurable via `--num-workers`
- **Typical throughput**:
  - ~7 documents in ~15 seconds (LanceDB Python docs)
  - ~1.5-3 seconds per document
- **Scales linearly** with worker count

## Common Issues & Solutions

### Issue: Agent extracts pandas/numpy functions
**Cause**: Prompt filtering not working
**Solution**: Check `library_name` parameter matches exactly

### Issue: Snippet references not resolved
**Cause**: Incorrect `repo_root` path
**Solution**: Verify `repo_root` points to repository root with source files

### Issue: Validation hook failures
**Cause**: Missing required fields (e.g., `code_block_index`)
**Solution**: Check `validation_logs/` for specific Pydantic errors

### Issue: Missing async detection
**Cause**: Example has `await` but marked as `sync`
**Solution**: Update prompt to detect `await` keyword patterns

## Implementation Notes

### Parallel Processing Strategy
```python
# Worker pool pattern
semaphore = asyncio.Semaphore(num_workers)

async with semaphore:
    # Each worker:
    # 1. Creates own Claude client
    # 2. Has own logger/hooks
    # 3. Processes one document
    # 4. Saves own output
    pass
```

### Hook Registration
```python
hooks = create_agent_hooks(
    agent_type="extraction",
    logger=per_doc_logger,
    output_dir=output_folder,
    validation_log_dir=validation_log_dir
)

options = ClaudeAgentOptions(
    system_prompt=EXTRACTION_SYSTEM_PROMPT,
    allowed_tools=["Read", "Write"],
    hooks=hooks
)
```

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `ExtractionResult`, `APISignature`, `CodeExample`
- **Hooks**: `stackbench/hooks/validation.py` - `validate_extraction_json()`
- **CLI**: `stackbench run --library <name> --version <ver> --docs-path <path>`

## See Also

- [API Signature Validation Agent](./api-signature-validation-agent.md) - Validates extracted signatures
- [Code Example Validation Agent](./code-example-validation-agent.md) - Executes extracted examples
- [Clarity Agent](./clarity-agent.md) - Uses extraction metadata for context
