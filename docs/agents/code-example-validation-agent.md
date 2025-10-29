# Code Example Validation Agent

## Objective

The Code Example Validation Agent validates that code examples in documentation actually work by **executing them in isolated environments** for **Python, JavaScript, and TypeScript**. It:
- Creates isolated environments (Python: virtualenv, JS/TS: npm project)
- Installs exact library version + dependencies
- Executes code examples and captures output/errors
- Handles sequential dependencies (examples that build on each other)
- Handles async/await code properly (Python: asyncio, JS/TS: async IIFE)
- Classifies failures by severity (error vs warning vs info)

This agent catches **broken code examples** - the most frustrating documentation issue for developers.

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │
└─────────────────────────┘
            ↓
            ↓ (extraction/{doc}_analysis.json)
            ↓
┌─────────────────────────┐
│ CODE VALIDATION AGENT   │ ◄── YOU ARE HERE
│  (Sequential)           │
└─────────────────────────┘
            ↓
            ↓ (code_validation/{doc}_validation.json)
            ↓
┌─────────────────────────┐
│ Clarity Validation Agent│ (reads code validation results)
└─────────────────────────┘
```

**Stage**: 2 (Second, runs in parallel with API Validation)
**Runs**: Sequential per document (not parallel)
**Dependencies**: Extraction Agent output
**Consumers**: Clarity Agent (for correlation)

## Inputs

### Required
- **`extraction_output_folder`** (Path): Folder with extraction results (`*_analysis.json`)
- **`validation_output_folder`** (Path): Folder to save validation results

### Optional
- **`num_workers`** (int): Number of parallel workers (default: 5)
- **`validation_log_dir`** (Path): Directory for validation hooks and logs

### Environment
- **Python**: Environment with `pip` and `virtualenv`
- **JavaScript/TypeScript**: Environment with `npm`/`yarn` and `node`/`ts-node`
- Bash access for running commands
- Network access for package installation

## Expected Output

### Output Files

For each extraction file `{doc_name}_analysis.json`, produces:
```
output_folder/
├── {doc_name}_validation.json   # Per-document validation results
└── validation_summary.json      # Aggregate statistics
```

### Output Schema (`{doc_name}_validation.json`)

```json
{
  "page": "quickstart.md",
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",
  "validation_timestamp": "2025-01-15T10:45:00Z",

  "results": [
    {
      "example_index": 0,
      "line": 45,
      "context": "Quick Start",
      "code": "import lancedb\ndb = lancedb.connect(\"./data\")",
      "status": "success",
      "severity": null,
      "error_message": null,
      "suggestions": null,
      "execution_output": "Connected to database at ./data",
      "depends_on_previous": false,
      "depends_on_example_indices": [],
      "actual_code_executed": "import lancedb\ndb = lancedb.connect(\"./data\")"
    },
    {
      "example_index": 1,
      "line": 67,
      "context": "Creating Tables",
      "code": "table = db.create_table('my_table', data)",
      "status": "failure",
      "severity": "error",
      "error_message": "NameError: name 'data' is not defined",
      "suggestions": "Define 'data' before using it, or merge with previous example that defines data",
      "execution_output": "Traceback (most recent call last):\n  ...",
      "depends_on_previous": true,
      "depends_on_example_indices": [0],
      "actual_code_executed": "import lancedb\ndb = lancedb.connect(\"./data\")\ntable = db.create_table('my_table', data)"
    },
    {
      "example_index": 2,
      "line": 89,
      "context": "Async Operations",
      "code": "async_db = await lancedb.connect_async(uri)",
      "status": "success",
      "severity": null,
      "error_message": null,
      "suggestions": null,
      "execution_output": "Connected asynchronously",
      "depends_on_previous": false,
      "depends_on_example_indices": [],
      "actual_code_executed": "import asyncio\nimport lancedb\n\nasync def main():\n    uri = \"./data\"\n    async_db = await lancedb.connect_async(uri)\n    return async_db\n\nasyncio.run(main())"
    }
  ],

  "total_examples": 3,
  "successful": 2,
  "failed": 1,
  "skipped": 0
}
```

### Summary File

```json
{
  "timestamp": "2025-01-15T10:50:00Z",
  "total_documents": 7,
  "total_examples": 28,
  "successful": 23,
  "failed": 5,
  "failed_by_severity": {
    "error": 3,
    "warning": 2,
    "info": 0
  },
  "validation_duration_seconds": 45.2,
  "num_workers": 5,
  "documents": [...]
}
```

## Pseudocode

```python
async def validate_all_documents(extraction_folder):
    """Validate all extraction files."""

    # 1. Find extraction files
    extraction_files = glob(extraction_folder, "*_analysis.json")

    # 2. Sequential validation per document
    results = []
    for extraction_file in extraction_files:
        result = await validate_document(extraction_file)
        results.append(result)

    # 3. Calculate severity breakdown
    summary = calculate_summary_with_severity(results)
    save_summary(summary)

    return results


async def validate_document(extraction_file):
    """Validate code examples in a single document."""

    # 1. Load extraction data
    data = load_json(extraction_file)
    library = data["library"]
    version = data["version"]
    examples = data["examples"]

    # 2. Create Claude agent with Bash access
    hooks = create_validation_hooks() + create_logging_hooks()

    # 3. Ask Claude to validate
    prompt = f"""
    Validate code examples for {library} version {version}.

    Examples: {json.dumps(examples, indent=2)}

    TASK:
    1. Create isolated environment based on language:
       - Python: Virtual environment
       - JavaScript/TypeScript: npm project
    2. Install library:
       - Python: pip install {library}=={version}
       - JS/TS: npm install {library}@{version}
    3. For each example:
       a. Check execution_context: sync/async/not_executable
       b. If sync: Execute as-is
       c. If async:
          - Python: Wrap in asyncio.run()
          - JS/TS: Wrap in async IIFE
       d. If not_executable: Skip with reason
       e. Track dependencies (which examples it depends on)
       f. Save FULL code executed (including merged dependencies)
       g. If failure: Classify severity (error/warning/info)

    SEVERITY CLASSIFICATION:
    - "error": Clear doc mistake
      * Python: SyntaxError, NameError, ImportError
      * JS/TS: SyntaxError, ReferenceError, Cannot find module
    - "warning": Environment issue (deep library errors, version conflicts)
    - "info": Non-blocking (DeprecationWarning, format differences)

    Output JSON array ONLY.
    """

    response = await claude.query(prompt)

    # 4. Parse and validate
    validation_results = parse_json_array(response)

    # 5. Create document result
    doc_result = create_document_validation_result(
        page=data["page"],
        library=library,
        version=version,
        results=validation_results
    )

    # 6. Save result
    save_json(output_folder / f"{doc_name}_validation.json", doc_result)

    return doc_result


# What Claude does internally
def claude_validation_logic(library, version, language, examples):
    """Claude's execution process."""

    # 1. Create isolated environment (language-specific)
    if language == "python":
        run_bash("python -m venv /tmp/validation_env")
        run_bash("source /tmp/validation_env/bin/activate")
    elif language in ["javascript", "typescript"]:
        run_bash("mkdir /tmp/validation_project && cd /tmp/validation_project")
        run_bash("npm init -y")

    # 2. Install library (language-specific)
    if language == "python":
        run_bash(f"pip install {library}=={version}")
    elif language in ["javascript", "typescript"]:
        run_bash(f"npm install {library}@{version}")

    validation_results = []
    accumulated_state = {}  # Track variables from previous examples

    # 3. For each example
    for i, example in enumerate(examples):
        code = example["code"]
        execution_context = example.get("execution_context", "sync")

        # 4. Check if executable
        if execution_context == "not_executable":
            validation_results.append({
                "example_index": i,
                "status": "skipped",
                "error_message": "Example marked as not executable",
                "actual_code_executed": code
            })
            continue

        # 5. Check for dependencies
        undefined_vars = find_undefined_variables(code, accumulated_state)

        depends_on_indices = []
        if undefined_vars:
            # Merge with previous examples that define these vars
            depends_on_indices = find_defining_examples(undefined_vars, examples[:i])
            for dep_idx in depends_on_indices:
                accumulated_state.update(examples[dep_idx]["code"])

        # 6. Prepare code for execution (language-specific)
        if execution_context == "async":
            # Wrap async code
            if language == "python":
                actual_code = f"""
import asyncio
{accumulated_state}

async def main():
    {indent(code, '    ')}

asyncio.run(main())
"""
            elif language in ["javascript", "typescript"]:
                actual_code = f"""
{accumulated_state}

(async () => {{
    {indent(code, '    ')}
}})();
"""
        else:
            # Sync code
            actual_code = f"{accumulated_state}\n{code}"

        # 7. Execute (language-specific)
        try:
            if language == "python":
                result = run_bash(f"python -c '{escape(actual_code)}'")
            elif language in ["javascript", "typescript"]:
                # Write to temp file and execute
                write_file("/tmp/example.js", actual_code)
                result = run_bash("node /tmp/example.js")

            validation_results.append({
                "example_index": i,
                "status": "success",
                "severity": null,
                "execution_output": result.stdout,
                "depends_on_previous": len(depends_on_indices) > 0,
                "depends_on_example_indices": depends_on_indices,
                "actual_code_executed": actual_code
            })

            # Update state
            accumulated_state[i] = code

        except BashError as e:
            # 8. Classify failure severity
            severity = classify_error_severity(e.stderr)

            validation_results.append({
                "example_index": i,
                "status": "failure",
                "severity": severity,
                "error_message": e.stderr,
                "suggestions": generate_fix_suggestion(e.stderr, code),
                "execution_output": e.stdout,
                "depends_on_previous": len(depends_on_indices) > 0,
                "depends_on_example_indices": depends_on_indices,
                "actual_code_executed": actual_code
            })

    # 9. Cleanup
    run_bash("deactivate")

    return validation_results


def classify_error_severity(error_message, language):
    """Classify error by analyzing error type and stack trace."""

    # Error indicators (clear doc mistake) - language-specific
    if language == "python":
        error_patterns = [
            "SyntaxError",
            "IndentationError",
            "NameError.*in user code",
            "ImportError",
            "ModuleNotFoundError",
            "AttributeError.*in documented API call"
        ]
    elif language in ["javascript", "typescript"]:
        error_patterns = [
            "SyntaxError",
            "ReferenceError",
            "Cannot find module",
            "TypeError.*in user code"
        ]

    # Warning indicators (environment/compatibility issue)
    if language == "python":
        warning_patterns = [
            ".*in _.*_impl",  # Internal library functions
            "version conflict",
            "TypeError.*in library internals"
        ]
    elif language in ["javascript", "typescript"]:
        warning_patterns = [
            ".*in node_modules",  # Errors in dependencies
            "version conflict",
            "TypeError.*in library code"
        ]

    # Info indicators (non-blocking)
    info_patterns = [
        "DeprecationWarning",
        "FutureWarning",
        "deprecated",
        "output format difference"
    ]

    if any(re.match(pattern, error_message) for pattern in error_patterns):
        return "error"
    elif any(re.match(pattern, error_message) for pattern in warning_patterns):
        return "warning"
    elif any(re.match(pattern, error_message) for pattern in info_patterns):
        return "info"
    else:
        return "error"  # Default to error if unsure
```

## Key Features

### 1. **Async Code Handling**

Automatically detects and wraps async code (language-specific):

**Python:**
```python
# Input (execution_context: "async")
async_db = await lancedb.connect_async(uri)

# Executed as:
import asyncio

async def main():
    uri = "./data"
    async_db = await lancedb.connect_async(uri)
    return async_db

asyncio.run(main())
```

**JavaScript/TypeScript:**
```javascript
// Input (execution_context: "async")
const data = await client.fetch();

// Executed as:
(async () => {
    const client = require('mylib');
    const data = await client.fetch();
    console.log(data);
})();
```

### 2. **Dependency Tracking**

Tracks which examples depend on previous ones:

```json
{
  "example_index": 2,
  "depends_on_previous": true,
  "depends_on_example_indices": [0, 1],
  "actual_code_executed": "import lancedb\ndb = lancedb.connect(...)\ntable = db.create_table(...)\nresults = table.search(...)"
}
```

### 3. **Severity Classification**

**Error** (Clear doc mistake) - language-specific:
- **Python**: SyntaxError, IndentationError, NameError, ImportError, ModuleNotFoundError
- **JS/TS**: SyntaxError, ReferenceError, Cannot find module
- **All**: AttributeError/TypeError in documented API calls

**Warning** (Environment issue) - language-specific:
- **Python**: Errors in library internals (`_scan_pyarrow_dataset_impl`)
- **JS/TS**: Errors in node_modules
- **All**: Version compatibility errors, TypeError in internal functions

**Info** (Non-blocking):
- DeprecationWarning, FutureWarning
- Output format differences

### 4. **Full Code Tracking**

Saves the complete code that was executed, including merged dependencies:

```json
{
  "code": "table.search([1.0, 2.0]).limit(5)",
  "actual_code_executed": "import lancedb\ndb = lancedb.connect('./data')\ntable = db.open_table('my_table')\ntable.search([1.0, 2.0]).limit(5)"
}
```

## Logging & Debugging

### Per-Document Logs
```
validation_log_dir/code_example_logs/{doc_name}/
├── agent.log       # Human-readable log
├── tools.jsonl     # Bash execution logs
└── messages.jsonl  # Full Claude conversation
```

### Log Contents
- virtualenv creation commands
- pip install output
- All bash executions (with exit codes)
- Full error messages and stack traces
- Validation hook failures

## Performance

- **Sequential per document**: Avoids venv conflicts
- **Typical throughput**:
  - ~7 documents with 28 examples in ~45 seconds
  - ~6-7 seconds per document
- **Bottlenecks**: pip install, example execution time

## Common Issues & Solutions

### Issue: All examples marked "failure" with ImportError
**Cause**: Library installation failed
**Solution**: Check `validation_summary.json` for pip errors

### Issue: False "NameError" for variables defined earlier
**Cause**: Dependency tracking not detecting definition
**Solution**: Check if variable is defined in different scope/section

### Issue: Async examples fail with "await outside async function"
**Cause**: `execution_context` not set to "async"
**Solution**: Update Extraction Agent to detect async patterns

### Issue: Severity "error" for library internal errors
**Cause**: Classification not detecting internal stack frames
**Solution**: Review error message patterns in classification logic

## Implementation Notes

### Why Sequential?
```python
# Parallel would cause:
# - Multiple virtualenvs consuming resources
# - Disk I/O contention
# - Harder to track state

# Sequential ensures:
# - Clean environment per document
# - Easier debugging
# - Predictable resource usage
```

### Validation Hook

```python
@PreToolUse hook (on Write)
def validate_code_validation_json(json_data):
    """Validate before saving."""
    try:
        DocumentValidationResult(**json_data)
        return True
    except ValidationError as e:
        send_error_to_claude(e)
        return False
```

### Environment Isolation

Each document gets a fresh isolated environment:

**Python:**
```bash
python -m venv /tmp/stackbench_validation_{uuid}
source /tmp/stackbench_validation_{uuid}/bin/activate
pip install {library}=={version}
# ... run examples ...
deactivate
rm -rf /tmp/stackbench_validation_{uuid}
```

**JavaScript/TypeScript:**
```bash
mkdir /tmp/stackbench_validation_{uuid}
cd /tmp/stackbench_validation_{uuid}
npm init -y
npm install {library}@{version}
# ... run examples ...
cd .. && rm -rf /tmp/stackbench_validation_{uuid}
```

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `DocumentValidationResult`, `ExampleValidationResult`
- **Hooks**: `stackbench/hooks/validation.py` - `validate_validation_output_json()`
- **CLI**: Results displayed in `stackbench run` summary with severity breakdown

## See Also

- [Extraction Agent](./extraction-agent.md) - Provides input examples
- [API Signature Validation Agent](./api-signature-validation-agent.md) - Validates API signatures
- [Clarity Agent](./clarity-agent.md) - Correlates execution failures with clarity issues
