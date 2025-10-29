# API Signature Validation Agent

## Objective

The API Signature Validation Agent validates that documented API signatures match the actual library implementation through **dynamic code introspection** for **Python, JavaScript, and TypeScript**. It:
- Installs the exact library version mentioned in documentation
- Uses language-specific introspection tools (Python: `inspect`, JS/TS: runtime/compiler API)
- Compares documented vs actual parameters, types, and defaults
- Reports mismatches with actionable suggestions

This agent catches **API documentation drift** - when code evolves but docs don't.

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │
└─────────────────────────┘
            ↓
            ↓ (extraction/{doc}_analysis.json)
            ↓
┌─────────────────────────┐
│ API VALIDATION AGENT    │ ◄── YOU ARE HERE
│  (Sequential)           │
└─────────────────────────┘
            ↓
            ↓ (api_validation/{doc}_validation.json)
            ↓
┌─────────────────────────┐
│ Clarity Validation Agent│ (reads API validation results)
└─────────────────────────┘
```

**Stage**: 2 (Second)
**Runs**: Sequential (not parallel)
**Dependencies**: Extraction Agent output
**Consumers**: Clarity Agent (for correlation)

## Inputs

### Required
- **`extraction_folder`** (Path): Folder containing extraction results (`*_analysis.json`)
- **`output_folder`** (Path): Folder to save validation results

### Optional
- **`num_workers`** (int): Number of parallel workers (default: 5)
- **`validation_log_dir`** (Path): Directory for validation hooks and logs

### Environment
- **Python**: Environment with `pip` and `inspect` module
- **JavaScript/TypeScript**: Environment with `npm`/`yarn` and `node`
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
  "validation_id": "uuid-here",
  "validated_at": "2025-01-15T10:40:00Z",
  "source_file": "quickstart_analysis.json",
  "document_page": "quickstart.md",
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",

  "summary": {
    "total_signatures": 5,
    "valid": 4,
    "invalid": 0,
    "not_found": 1,
    "error": 0,
    "accuracy_score": 0.800,
    "critical_issues": 1,
    "warnings": 2
  },

  "validations": [
    {
      "signature_id": "lancedb.connect",
      "function": "connect",
      "method_chain": null,
      "library": "lancedb",
      "status": "valid",

      "documented": {
        "params": ["uri", "read_consistency_interval"],
        "param_types": {"uri": "str"},
        "defaults": {"read_consistency_interval": null},
        "imports": "import lancedb",
        "raw_code": "db = lancedb.connect(\"./data\")",
        "line": 45,
        "context": "Quick Start"
      },

      "actual": {
        "params": ["uri", "read_consistency_interval", "storage_options"],
        "param_types": {
          "uri": "str",
          "read_consistency_interval": "Optional[timedelta]",
          "storage_options": "Optional[Dict[str, str]]"
        },
        "defaults": {
          "read_consistency_interval": "None",
          "storage_options": "None"
        },
        "required_params": ["uri"],
        "optional_params": ["read_consistency_interval", "storage_options"],
        "return_type": "Database",
        "is_async": false,
        "is_method": false,
        "verified_by": "inspect.signature"
      },

      "issues": [
        {
          "type": "missing_param_in_docs",
          "severity": "info",
          "message": "Optional parameter 'storage_options' not shown in docs",
          "suggested_fix": "This is acceptable for simplified examples. Consider adding to API reference."
        }
      ],

      "confidence": 0.95
    },
    {
      "signature_id": "lancedb.old_connect",
      "function": "old_connect",
      "status": "not_found",
      "documented": {...},
      "actual": null,
      "issues": [
        {
          "type": "api_not_found",
          "severity": "critical",
          "message": "Function 'old_connect' does not exist in lancedb 0.25.2",
          "suggested_fix": "Remove this from documentation or check if it was renamed"
        }
      ],
      "confidence": 1.0
    }
  ],

  "environment": {
    "library_installed": "lancedb",
    "version_installed": "0.25.2",
    "version_requested": "0.25.2",
    "version_match": true,
    "runtime_version": "Python 3.11.5",
    "installation_output": "Successfully installed lancedb-0.25.2 ..."
  },

  "processing_time_ms": 3200,
  "warnings": []
}
```

## Pseudocode

```python
async def validate_all_documents(extraction_folder):
    """Validate all extraction files."""

    # 1. Find all extraction files
    extraction_files = glob(extraction_folder, "*_analysis.json")

    # 2. Sequential validation (not parallel due to pip conflicts)
    results = []
    for extraction_file in extraction_files:
        result = await validate_document(extraction_file)
        results.append(result)

    # 3. Aggregate summary
    save_summary(results)

    return results


async def validate_document(extraction_file):
    """Validate signatures in a single document."""

    # 1. Load extraction data
    data = load_json(extraction_file)
    library = data["library"]
    version = data["version"]
    signatures = data["signatures"]

    # 2. Create Claude agent with bash access
    hooks = create_validation_hooks() + create_logging_hooks()

    # 3. Ask Claude to validate
    prompt = f"""
    Validate API signatures for {library} version {version}.

    Signatures: {json.dumps(signatures)}

    TASK:
    1. Install library based on language:
       - Python: pip install {library}=={version}
       - JavaScript/TypeScript: npm install {library}@{version}
    2. For each signature:
       a. Import library and locate function/method
       b. Use language-specific introspection:
          - Python: inspect.signature()
          - JS/TS: runtime introspection or TypeScript compiler API
       c. Compare documented vs actual params, types, defaults
       d. Determine status: valid/invalid/not_found
       e. Classify issue severity: critical/warning/info

    STATUS RULES:
    - "valid": All required params documented correctly (missing optional params OK)
    - "invalid": Missing required params or wrong param names/types
    - "not_found": API doesn't exist

    SEVERITY RULES:
    - "critical": API not found, missing required params
    - "warning": Type mismatches in optional params
    - "info": Optional params not shown in docs (acceptable)

    Output JSON ONLY.
    """

    response = await claude.query(prompt)

    # 4. Parse and validate
    validation_data = parse_json(response)
    validate_against_schema(validation_data)  # Via hook

    # 5. Calculate summary
    summary = calculate_summary(validation_data["validations"])

    # 6. Save result
    output = create_validation_output(
        validation_data,
        summary,
        source_file=extraction_file.name
    )

    save_json(output_folder / f"{doc_name}_validation.json", output)

    return output


# What Claude does internally
def claude_validation_logic(library, version, language, signatures):
    """Claude's introspection process."""

    # 1. Install library (language-specific)
    if language == "python":
        run_bash(f"pip install {library}=={version}")
    elif language in ["javascript", "typescript"]:
        run_bash(f"npm install {library}@{version}")

    # 2. Get environment info (language-specific)
    if language == "python":
        version_installed = run_bash(f"pip show {library} | grep Version")
        runtime_version = run_bash("python --version")
    elif language in ["javascript", "typescript"]:
        version_installed = run_bash(f"npm list {library} --depth=0")
        runtime_version = run_bash("node --version")

    validations = []

    # 3. For each signature
    for sig in signatures:
        function_name = sig["function"]
        method_chain = sig["method_chain"]

        try:
            # 4. Import and locate function
            if method_chain:
                # Handle chained methods (e.g., db.create_table)
                # Get parent object type first
                parent_obj = get_parent_object(library, method_chain)
                actual_func = get_method(parent_obj, function_name)
            else:
                # Direct function
                actual_func = import_function(library, function_name)

            # 5. Introspect actual signature (language-specific)
            if language == "python":
                import inspect
                actual_sig = inspect.signature(actual_func)
                actual_spec = inspect.getfullargspec(actual_func)
                actual_params = list(actual_sig.parameters.keys())
                actual_types = extract_type_hints(actual_func)
                actual_defaults = extract_defaults(actual_sig)
            elif language in ["javascript", "typescript"]:
                # Runtime introspection or TypeScript compiler API
                actual_params = extract_params_from_function(actual_func)
                actual_types = parse_typescript_types(library, function_name)
                actual_defaults = extract_js_defaults(actual_func)

            # 6. Compare documented vs actual
            documented_params = sig["params"]
            required_params = get_required_params(actual_sig)

            issues = []

            # Check for missing required params
            for param in required_params:
                if param not in documented_params:
                    issues.append({
                        "type": "missing_required_param",
                        "severity": "critical",
                        "message": f"Required parameter '{param}' missing from docs",
                        "suggested_fix": f"Add '{param}' to documented signature"
                    })

            # Check for wrong param names
            for param in documented_params:
                if param not in actual_params:
                    issues.append({
                        "type": "wrong_param_name",
                        "severity": "critical",
                        "message": f"Parameter '{param}' doesn't exist in actual API",
                        "suggested_fix": "Check spelling or if param was renamed"
                    })

            # Check for missing optional params (info level)
            optional_params = [p for p in actual_params if p not in required_params]
            for param in optional_params:
                if param not in documented_params:
                    issues.append({
                        "type": "missing_param_in_docs",
                        "severity": "info",
                        "message": f"Optional parameter '{param}' not shown in docs",
                        "suggested_fix": "This is acceptable for simplified examples"
                    })

            # 7. Determine status
            if any(i["severity"] == "critical" for i in issues):
                status = "invalid"
            else:
                status = "valid"

            validations.append({
                "signature_id": f"{library}.{function_name}",
                "function": function_name,
                "status": status,
                "documented": {...},
                "actual": {
                    "params": actual_params,
                    "param_types": actual_types,
                    "defaults": actual_defaults,
                    "required_params": required_params,
                    "optional_params": optional_params,
                    "return_type": get_return_type(actual_func),
                    "is_async": inspect.iscoroutinefunction(actual_func),
                    "is_method": inspect.ismethod(actual_func),
                    "verified_by": "inspect.signature"
                },
                "issues": issues,
                "confidence": 0.95
            })

        except (ImportError, AttributeError):
            # API doesn't exist
            validations.append({
                "signature_id": f"{library}.{function_name}",
                "function": function_name,
                "status": "not_found",
                "issues": [{
                    "type": "api_not_found",
                    "severity": "critical",
                    "message": f"Function '{function_name}' not found in {library}",
                    "suggested_fix": "Remove or check if API was renamed"
                }]
            })

    return {
        "environment": {...},
        "validations": validations
    }
```

## Key Features

### 1. **Status Determination Logic**

```python
# Valid: Required params correct, optional params may be omitted
if all_required_params_present and no_critical_issues:
    status = "valid"

# Invalid: Critical errors
elif missing_required_params or wrong_param_names:
    status = "invalid"

# Not Found: API doesn't exist
elif import_error or attribute_error:
    status = "not_found"
```

### 2. **Severity Classification**

- **Critical**: API not found, missing required params, wrong param names
- **Warning**: Type mismatches in optional params, outdated defaults
- **Info**: Optional params not shown (acceptable for tutorials)

### 3. **Method Chain Handling**

For chained methods like `db.create_table()`:

```python
# 1. Get parent object type
db = lancedb.connect(...)  # Returns Database object

# 2. Introspect method on that type
Database_class = type(db)
create_table_method = getattr(Database_class, "create_table")

# 3. Validate method signature
sig = inspect.signature(create_table_method)
```

### 4. **Environment Verification**

Captures installation details (language-specific):
```json
{
  "library_installed": "lancedb",
  "version_installed": "0.25.2",
  "version_requested": "0.25.2",
  "version_match": true,
  "runtime_version": "Python 3.11.5 OR Node.js v18.17.0"
}
```

### 5. **Smart Scoring**

```python
accuracy_score = valid / total_signatures

# Example:
# 4 valid, 0 invalid, 1 not_found → 4/5 = 0.800 (80%)
```

## Logging & Debugging

### Per-Document Logs
```
validation_log_dir/api_signature_logs/{doc_name}/
├── agent.log       # Human-readable log
├── tools.jsonl     # Bash + Read + Write calls
└── messages.jsonl  # Full Claude conversation
```

### Log Contents
- `pip install` output
- `inspect.signature()` results
- Import errors and stack traces
- Validation hook failures

## Performance

- **Sequential processing**: Avoids pip install conflicts
- **Typical throughput**:
  - ~7 documents in ~25 seconds
  - ~3-4 seconds per document
- **Bottlenecks**: pip install time

## Common Issues & Solutions

### Issue: Version mismatch (requested 0.25.2, installed 0.26.0)
**Cause**: Library not available at specified version
**Solution**: Check PyPI for available versions, update docs

### Issue: Status "invalid" for correct signatures
**Cause**: Missing optional params classified as critical
**Solution**: Check severity - should be "info" for optional params

### Issue: Method chain validation fails
**Cause**: Can't determine parent object type
**Solution**: Add explicit type hints or check agent logs

### Issue: All validations marked "not_found"
**Cause**: Library import failed during installation
**Solution**: Check `environment.installation_output` for pip errors

## Implementation Notes

### Why Sequential?
```python
# Parallel validation would cause:
# - Multiple pip installs of same library
# - Version conflicts
# - File locking issues

# Sequential ensures:
# - Clean environment per validation
# - Deterministic results
```

### Validation Hook

```python
@PreToolUse hook (on Write)
def validate_api_validation_json(json_data):
    """Validate before saving."""
    try:
        APISignatureValidationOutput(**json_data)
        return True
    except ValidationError as e:
        send_error_to_claude(e)
        return False
```

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `APISignatureValidationOutput`, `SignatureValidation`
- **Hooks**: `stackbench/hooks/validation.py` - `validate_validation_output_json()`
- **CLI**: Results automatically displayed in `stackbench run` summary

## See Also

- [Extraction Agent](./extraction-agent.md) - Provides input signatures
- [Code Example Validation Agent](./code-example-validation-agent.md) - Validates code execution
- [Clarity Agent](./clarity-agent.md) - Correlates API issues with clarity problems
