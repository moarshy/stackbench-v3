# API Completeness & Deprecation Agent

## Objective

The API Completeness Agent analyzes **documentation coverage** using a two-tier architecture:
- **Agent (Environment Interaction + Qualitative)**: Library installation, introspection execution via Bash, reading extraction files, matching APIs to docs
- **MCP Server (Deterministic)**: Importance scoring, coverage classification, metrics calculations

It:
- Installs the library in the agent's environment (via Bash)
- Runs language-specific introspection templates (via Bash) to discover all public APIs
- Aggregates documented APIs from all extraction results (agent)
- Calculates tiered coverage and importance scores (via MCP)
- Identifies undocumented APIs ranked by importance (via MCP)
- Detects deprecated APIs still taught in documentation (via introspection + agent)

This agent catches **missing documentation** and **deprecated API usage** - ensuring completeness and currency.

**Key Architecture Decision**: Introspection runs in the agent's environment via Bash (not MCP subprocess) to avoid package isolation issues, while MCP handles only pure computational tasks.

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │
└─────────────────────────┘
            ↓
            ↓ (extraction/*.json - ALL docs)
            ↓
┌─────────────────────────────────────┐
│ API COMPLETENESS AGENT (MCP)        │ ◄── YOU ARE HERE
│  • MCP: Library introspection       │
│  • MCP: Importance scoring           │
│  • Agent: Doc pattern matching       │
│  • MCP: Coverage calculation         │
└─────────────────────────────────────┘
            ↓
            ↓ (completeness_analysis.json)
            ↓
   (Dashboard / Reporting)
```

**Stage**: 2-3 (Runs after extraction, in parallel with or after validation agents)
**Runs**: Single execution (not per-document)
**Dependencies**: ALL extraction results
**Consumers**: Dashboard, coverage reports
**MCP Server**: `stackbench.mcp_servers.api_completeness_server`

## Architecture: Agent + MCP Server

### Agent Responsibilities (Environment Interaction + Qualitative)
- **Library Installation**: `pip install` via Bash in agent's environment
- **Introspection Execution**: Run language-specific templates via Bash
  - Python: `stackbench/introspection_templates/python_introspect.py`
  - JavaScript/TypeScript: (Future: `js_introspect.js`, `ts_introspect.ts`)
- **Read Introspection Results**: Parse standardized JSON output from templates
- **Read Extraction Files**: Load all `*_analysis.json` files
- **Pattern Matching**: Identify which APIs appear in docs
- **Context Understanding**: Detect dedicated sections vs mentions
- **MCP Orchestration**: Call MCP tools for scoring/classification
- **Output Building**: Construct final JSON report

### MCP Server Responsibilities (Deterministic Computation Only)
- **Importance Scoring**: Heuristic-based ranking (0-10)
- **Coverage Classification**: Tier assignment (0-3)
- **Metrics Calculation**: Coverage percentages
- **Prioritization**: Rank undocumented APIs

### Introspection Templates (Language-Specific Scripts)
Language-specific scripts that output standardized JSON format:

**Location**: `stackbench/introspection_templates/`

**Python Template** (`python_introspect.py`):
```bash
python python_introspect.py <library> <version> [modules...] > output.json
```

Output format:
```json
{
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",
  "total_apis": 118,
  "apis": [
    {
      "api": "lancedb.connect",
      "module": "lancedb",
      "type": "function",
      "is_async": false,
      "has_docstring": true,
      "in_all": true,
      "is_deprecated": false,
      "signature": "(uri, *, api_key=None, ...)"
    }
  ],
  "by_type": {"function": 5, "class": 11, "method": 102},
  "deprecated_count": 3
}
```

**Why Bash-based?** Avoids MCP subprocess isolation - templates run in agent's environment where packages are installed.

## Inputs

### Required
- **`extraction_folder`** (Path): Folder with ALL extraction results (`*_analysis.json`)
- **`output_folder`** (Path): Folder to save completeness analysis
- **`library_name`** (str): Library to analyze (e.g., "lancedb")
- **`library_version`** (str): Version to install and introspect (e.g., "0.25.2")

### Optional
- **`language`** (str): Programming language (default: "python")
- **`validation_log_dir`** (Path): Directory for logs

### Environment
- MCP server (`stackbench.mcp_servers.api_completeness_server`)
- Python environment with pip and `inspect` module
- Network access for `pip install`

## Expected Output

### Output Files

```
output_folder/
└── completeness_analysis.json   # Complete coverage analysis
```

### Output Schema (`completeness_analysis.json`)

```json
{
  "analysis_id": "uuid-here",
  "analyzed_at": "2025-01-15T11:30:00Z",
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",

  "api_surface": {
    "total_public_apis": 45,
    "by_module": {
      "lancedb": ["connect", "connect_async", "Config"],
      "lancedb.db": ["Database.create_table", "Database.open_table", "Database.drop_table"],
      "lancedb.table": ["Table.search", "Table.add", "Table.update"]
    },
    "by_type": {
      "function": 15,
      "class": 5,
      "method": 20,
      "property": 5
    },
    "deprecated_count": 3
  },

  "coverage_summary": {
    "total_apis": 45,
    "documented": 32,
    "with_examples": 28,
    "with_dedicated_sections": 15,
    "undocumented": 13,
    "coverage_percentage": 71.1,
    "example_coverage_percentage": 62.2,
    "complete_coverage_percentage": 33.3
  },

  "undocumented_apis": [
    {
      "api": "lancedb.Database.drop_table",
      "module": "lancedb.db",
      "type": "method",
      "importance": "high",
      "importance_score": 8,
      "reason": "In __all__, has docstring, common CRUD operation",
      "has_docstring": true,
      "is_async": false
    }
  ],

  "deprecated_in_docs": [
    {
      "api": "lancedb.old_connect",
      "module": "lancedb",
      "deprecated_since": "0.24.0",
      "alternative": "lancedb.connect",
      "documented_in": ["quickstart.md", "tutorial.md"],
      "severity": "critical",
      "deprecation_message": "old_connect is deprecated since 0.24.0, use connect instead",
      "suggestion": "Replace old_connect with connect in quickstart.md and tutorial.md"
    }
  ],

  "api_details": [
    {
      "api": "lancedb.connect",
      "module": "lancedb",
      "type": "function",
      "is_deprecated": false,
      "coverage_tier": 3,
      "documentation_references": [
        {
          "document": "pandas_and_pyarrow.md",
          "section_hierarchy": ["Pandas and PyArrow", "Create dataset"],
          "markdown_anchor": "#create-dataset",
          "line_number": 50,
          "context_type": "signature",
          "code_block_index": 0,
          "raw_context": "Create dataset - connecting to LanceDB database"
        },
        {
          "document": "duckdb.md",
          "section_hierarchy": ["DuckDB Integration", "Setup"],
          "markdown_anchor": "#setup",
          "line_number": 15,
          "context_type": "example",
          "code_block_index": 1,
          "raw_context": "Example: Basic connection"
        }
      ],
      "documented_in": ["pandas_and_pyarrow.md", "duckdb.md"],
      "has_examples": true,
      "has_dedicated_section": true,
      "importance": "high",
      "importance_score": 9
    }
  ],

  "environment": {
    "library_installed": "lancedb",
    "version_installed": "0.25.2",
    "version_requested": "0.25.2",
    "version_match": true,
    "python_version": "3.11.5"
  },

  "processing_time_ms": 5600,
  "warnings": []
}
```

### Rich Documentation References

**New Feature**: Each API in `api_details` now includes a `documentation_references` array with granular location data:

```json
{
  "documentation_references": [
    {
      "document": "pandas_and_pyarrow.md",         // Document filename
      "section_hierarchy": ["Pandas", "Create"],    // Breadcrumb path
      "markdown_anchor": "#create-dataset",         // Section anchor
      "line_number": 50,                            // Exact line
      "context_type": "signature",                  // signature | example | mention
      "code_block_index": 0,                        // Which code block
      "raw_context": "Create dataset - connecting"  // Human-readable context
    }
  ]
}
```

**Benefits:**
- **Granular Traceability**: Know exactly where each API is documented (file, line, section)
- **Context Type Tracking**: Distinguish between signatures, examples, and mentions
- **Actionable Suggestions**: "API X should be added to section Y at line Z"
- **Frontend Navigation**: Click reference → Jump to exact doc location
- **Coverage Heatmap**: Visualize which docs cover which APIs

**Backward Compatibility:**
- `documented_in` remains as derived field (unique list of documents)
- Existing dashboards work unchanged
- New features leverage rich references

## Pseudocode

```python
async def analyze_completeness(extraction_folder, library_name, library_version):
    """Analyze API completeness using MCP server."""

    # 1. Setup MCP server
    mcp_config = {
        "api-completeness": {
            "command": "python",
            "args": ["-m", "stackbench.mcp_servers.api_completeness_server"],
            "transport": "stdio"
        }
    }

    # 2. Create Claude agent with MCP
    options = ClaudeAgentOptions(
        system_prompt=COMPLETENESS_SYSTEM_PROMPT,
        allowed_tools=["Read", "Write"],
        mcp_servers=mcp_config
    )

    # 3. Ask Claude to orchestrate analysis
    prompt = f"""
    Analyze API completeness for {library_name} v{library_version}.

    Extraction files: {extraction_folder}

    WORKFLOW:
    1. Call MCP: introspect_library()
    2. Read extraction files (agent)
    3. Call MCP: calculate_importance_score() for each API
    4. Call MCP: classify_coverage() for each API
    5. Call MCP: calculate_metrics()
    6. Call MCP: prioritize_undocumented()
    7. Build output JSON

    Use MCP tools for ALL calculations.
    """

    async with ClaudeSDKClient(options=options) as client:
        response = await client.query(prompt)

    # 4. Parse and return
    analysis_data = parse_json(response)
    return APICompletenessOutput(**analysis_data)


# What Claude does (orchestration)
def claude_orchestration_logic(extraction_folder, library_name, library_version):
    """Claude orchestrates MCP calls and file reading."""

    # STEP 1: Introspect library (MCP)
    introspection_result = call_mcp_tool("introspect_library", {
        "library_name": library_name,
        "version": library_version,
        "modules": [library_name]
    })

    # Response:
    # {
    #   "apis": [
    #     {"api": "lancedb.connect", "module": "lancedb", "type": "function",
    #      "has_docstring": true, "in_all": true, "is_deprecated": false, ...},
    #     ...
    #   ],
    #   "deprecated_count": 3
    # }

    discovered_apis = introspection_result["apis"]

    # STEP 2: Read extraction files (agent)
    extraction_files = glob(extraction_folder, "*_analysis.json")

    documented_apis = {}  # api -> {pages: [...], in_examples: bool, ...}

    for extraction_file in extraction_files:
        data = load_json(extraction_file)
        page = data["page"]

        # Check signatures (tier 1)
        for sig in data.get("signatures", []):
            api_id = f"{sig['library']}.{sig['function']}"
            if api_id not in documented_apis:
                documented_apis[api_id] = {
                    "pages": [],
                    "in_examples": False,
                    "has_section": False
                }
            documented_apis[api_id]["pages"].append(page)

        # Check code examples (tier 2)
        for example in data.get("examples", []):
            api_calls = extract_api_calls_from_code(example["code"])
            for api_call in api_calls:
                if api_call in documented_apis:
                    documented_apis[api_call]["in_examples"] = True

        # Check for dedicated sections (tier 3)
        for sig in data.get("signatures", []):
            api_id = f"{sig['library']}.{sig['function']}"
            if has_dedicated_context(sig.get("section_hierarchy", [])):
                documented_apis[api_id]["has_section"] = True

    # STEP 3: Calculate importance scores (MCP)
    importance_scores = {}

    for api_obj in discovered_apis:
        score_result = call_mcp_tool("calculate_importance_score", {
            "api": api_obj["api"],
            "module": api_obj["module"],
            "type": api_obj["type"],
            "has_docstring": api_obj["has_docstring"],
            "in_all": api_obj["in_all"]
        })

        # Response: {"importance_score": 8, "importance": "high"}
        importance_scores[api_obj["api"]] = score_result

    # STEP 4: Classify coverage (MCP)
    coverage_tiers = {}

    for api_obj in discovered_apis:
        api_id = api_obj["api"]
        doc_info = documented_apis.get(api_id, {})

        coverage_result = call_mcp_tool("classify_coverage", {
            "api": api_id,
            "documented_in": doc_info.get("pages", []),
            "appears_in_examples": doc_info.get("in_examples", False),
            "has_dedicated_section": doc_info.get("has_section", False)
        })

        # Response: {"coverage_tier": 2}
        coverage_tiers[api_id] = coverage_result["coverage_tier"]

    # STEP 5: Calculate metrics (MCP)
    coverage_data = [
        {"api": api_obj["api"], "tier": coverage_tiers[api_obj["api"]]}
        for api_obj in discovered_apis
    ]

    metrics_result = call_mcp_tool("calculate_metrics", {
        "coverage_data": coverage_data
    })

    # Response:
    # {
    #   "total_apis": 45,
    #   "documented": 32,
    #   "with_examples": 28,
    #   "with_dedicated_sections": 15,
    #   "coverage_percentage": 71.1,
    #   ...
    # }

    # STEP 6: Prioritize undocumented (MCP)
    undocumented_api_names = [
        api_obj["api"] for api_obj in discovered_apis
        if coverage_tiers[api_obj["api"]] == 0
    ]

    prioritization_result = call_mcp_tool("prioritize_undocumented", {
        "undocumented_apis": undocumented_api_names,
        "importance_scores": importance_scores
    })

    # Response:
    # {
    #   "prioritized": [
    #     {"api": "lancedb.Database.drop_table", "importance_score": 8, ...},
    #     ...
    #   ]
    # }

    # STEP 7: Build output JSON
    return {
        "api_surface": {
            "total_public_apis": len(discovered_apis),
            "by_module": group_by_module(discovered_apis),
            "by_type": count_by_type(discovered_apis),
            "deprecated_count": introspection_result["deprecated_count"]
        },
        "coverage_summary": metrics_result,
        "undocumented_apis": prioritization_result["prioritized"],
        "deprecated_in_docs": find_deprecated_in_docs(discovered_apis, documented_apis),
        "api_details": build_api_details(discovered_apis, coverage_tiers, importance_scores)
    }


# MCP Server (deterministic operations)
class APICompletenessMCPServer:
    """MCP server for API completeness analysis."""

    @mcp_tool
    def introspect_library(self, library_name: str, version: str, modules: list[str]):
        """Introspect library to discover all public APIs."""

        # 1. Install library
        run_bash(f"pip install {library_name}=={version}")

        # 2. Import and discover
        import inspect
        import importlib
        import warnings

        discovered_apis = []

        for module_name in modules:
            module = importlib.import_module(module_name)

            # Get __all__ if present
            public_names = getattr(module, '__all__', None)

            # Discover all members
            for name, obj in inspect.getmembers(module):
                # Skip private unless in __all__
                if name.startswith('_') and (not public_names or name not in public_names):
                    continue

                # Determine type
                if inspect.isfunction(obj):
                    api_type = "function"
                elif inspect.isclass(obj):
                    api_type = "class"
                    # Also discover class methods
                    for method_name, method_obj in inspect.getmembers(obj):
                        # ... (discover methods)
                elif inspect.ismethod(obj):
                    api_type = "method"
                else:
                    continue

                # Check deprecation
                is_deprecated = check_deprecation(obj)

                discovered_apis.append({
                    "api": f"{module_name}.{name}",
                    "module": module_name,
                    "type": api_type,
                    "has_docstring": bool(obj.__doc__),
                    "in_all": public_names and name in public_names,
                    "is_deprecated": is_deprecated,
                    "is_async": inspect.iscoroutinefunction(obj)
                })

        return {
            "apis": discovered_apis,
            "deprecated_count": len([a for a in discovered_apis if a["is_deprecated"]])
        }

    @mcp_tool
    def calculate_importance_score(self, api: str, module: str, type: str,
                                     has_docstring: bool, in_all: bool):
        """Calculate importance score for an API."""

        score = 0

        # In __all__
        if in_all:
            score += 3

        # Has docstring
        if has_docstring:
            score += 2

        # Not private
        if not api.split('.')[-1].startswith('_'):
            score += 1

        # Top-level module
        if module == module.split('.')[0]:
            score += 1

        # Common name
        common_names = ['connect', 'create', 'get', 'open', 'close', 'add', 'update', 'delete']
        if any(name in api.lower() for name in common_names):
            score += 1

        # Classify
        if score >= 7:
            importance = "high"
        elif score >= 4:
            importance = "medium"
        else:
            importance = "low"

        return {
            "importance_score": score,
            "importance": importance
        }

    @mcp_tool
    def classify_coverage(self, api: str, documented_in: list[str],
                          appears_in_examples: bool, has_dedicated_section: bool):
        """Classify coverage tier."""

        if has_dedicated_section:
            tier = 3
        elif appears_in_examples:
            tier = 2
        elif documented_in:
            tier = 1
        else:
            tier = 0

        return {"coverage_tier": tier}

    @mcp_tool
    def calculate_metrics(self, coverage_data: list[dict]):
        """Calculate coverage percentages."""

        total = len(coverage_data)
        documented = len([x for x in coverage_data if x["tier"] >= 1])
        with_examples = len([x for x in coverage_data if x["tier"] >= 2])
        with_sections = len([x for x in coverage_data if x["tier"] == 3])
        undocumented = len([x for x in coverage_data if x["tier"] == 0])

        return {
            "total_apis": total,
            "documented": documented,
            "with_examples": with_examples,
            "with_dedicated_sections": with_sections,
            "undocumented": undocumented,
            "coverage_percentage": round(documented / total * 100, 1) if total else 0.0,
            "example_coverage_percentage": round(with_examples / total * 100, 1) if total else 0.0,
            "complete_coverage_percentage": round(with_sections / total * 100, 1) if total else 0.0
        }

    @mcp_tool
    def prioritize_undocumented(self, undocumented_apis: list[str],
                                importance_scores: dict):
        """Rank undocumented APIs by importance."""

        prioritized = []

        for api in undocumented_apis:
            score_info = importance_scores.get(api, {})
            prioritized.append({
                "api": api,
                "importance_score": score_info.get("importance_score", 0),
                "importance": score_info.get("importance", "low")
            })

        # Sort by score (descending)
        prioritized.sort(key=lambda x: x["importance_score"], reverse=True)

        return {"prioritized": prioritized}
```

## Key Features

### 1. **MCP Tools**

Five deterministic tools provided by MCP server:

```python
# 1. Library introspection
introspect_library(library_name, version, modules)
# Returns: {apis: [...], deprecated_count: N}

# 2. Importance scoring
calculate_importance_score(api, module, type, has_docstring, in_all)
# Returns: {importance_score: 8, importance: "high"}

# 3. Coverage classification
classify_coverage(api, documented_in, appears_in_examples, has_dedicated_section)
# Returns: {coverage_tier: 2}

# 4. Metrics calculation
calculate_metrics(coverage_data)
# Returns: {total_apis, documented, coverage_percentage, ...}

# 5. Prioritization
prioritize_undocumented(undocumented_apis, importance_scores)
# Returns: {prioritized: [...]}
```

### 2. **Importance Scoring Algorithm** (MCP)

```python
importance_score = 0

# In __all__ declaration
if in_all: importance_score += 3

# Has docstring
if has_docstring: importance_score += 2

# Not private (no leading _)
if not name.startswith('_'): importance_score += 1

# Top-level module (not nested)
if module == library_name: importance_score += 1

# Common operation name
if name in ['connect', 'create', 'get', 'open', ...]: importance_score += 1

# Classification:
# high: >= 7, medium: 4-6, low: 0-3
```

### 3. **Coverage Tiers** (MCP)

Deterministic classification:

```python
if has_dedicated_section:
    tier = 3  # "Dedicated section"
elif appears_in_examples:
    tier = 2  # "Has examples"
elif documented_in:
    tier = 1  # "Mentioned"
else:
    tier = 0  # "Undocumented"
```

### 4. **Deprecation Detection** (MCP)

Three strategies:

```python
# Strategy 1: @deprecated decorator
if hasattr(obj, '__deprecated__'):
    is_deprecated = True

# Strategy 2: Docstring mentions
if 'deprecated' in obj.__doc__.lower():
    is_deprecated = True

# Strategy 3: DeprecationWarning
with warnings.catch_warnings(record=True) as w:
    inspect.signature(obj)
    if any(issubclass(warn.category, DeprecationWarning) for warn in w):
        is_deprecated = True
```

### 5. **Agent Pattern Matching** (Qualitative)

Agent handles doc understanding:

```python
# Detect API mentions in signatures
for sig in signatures:
    api_id = f"{sig['library']}.{sig['function']}"
    # → Tier 1

# Detect API usage in examples
api_calls = parse_code_for_api_calls(example["code"])
# → Tier 2

# Detect dedicated sections
if section_hierarchy == ["API Reference", "connect"]:
    # → Tier 3
```

## Logging & Debugging

### Logs
```
validation_log_dir/api_completeness_logs/
├── agent.log       # Human-readable log
├── tools.jsonl     # Read/Write + MCP tool calls
└── messages.jsonl  # Full Claude conversation
```

### Log Contents
- MCP tool calls (introspect_library, calculate_importance_score, etc.)
- Read tool calls (extraction files)
- Pattern matching decisions
- Final output building

## Performance

- **Single run**: Not per-document
- **Typical duration**: ~10-20 seconds
- **Bottlenecks**:
  - Library introspection (MCP: pip install + inspect)
  - Reading many extraction files (agent)
  - Multiple MCP tool calls

## Common Issues & Solutions

### Issue: Many false "undocumented" for internal methods
**Cause**: Introspection finding private methods
**Solution**: MCP server filters by `__all__` and `_` prefix

### Issue: Missing deprecation warnings
**Cause**: Library doesn't use standard patterns
**Solution**: Enhance MCP server deprecation detection

### Issue: Coverage tier 0 for documented APIs
**Cause**: API name mismatch in pattern matching
**Solution**: Check agent logs for pattern matching results

### Issue: MCP server fails to introspect
**Cause**: Library installation failed
**Solution**: Check MCP server logs for pip errors

## Implementation Notes

### Why This Architecture?

**First Principles Design Decision:**

```python
# PROBLEM: Original MCP approach (introspection in MCP subprocess)
# ❌ MCP server runs as subprocess
# ❌ Subprocess can't access packages installed in parent environment
# ❌ Even with sys.executable, package isolation persists
# ❌ Complex workarounds (venv in subprocess, etc.) are fragile

# SOLUTION: Bash-based introspection + MCP for computation
# ✅ Agent installs library in its own environment
# ✅ Agent runs introspection templates via Bash (same environment)
# ✅ Templates output standardized JSON (deterministic format)
# ✅ MCP handles only pure computational tasks (scoring, metrics)
# ✅ Clean separation: Environment interaction (Bash) vs Computation (MCP)
```

**Template-Based Introspection:**
```python
# Instead of MCP subprocess calling inspect module...
# Agent runs language-specific templates via Bash:

# Python:
python stackbench/introspection_templates/python_introspect.py lancedb 0.25.2 > result.json

# JavaScript (future):
node stackbench/introspection_templates/js_introspect.js axios 1.6.0 > result.json

# Standardized JSON output:
{
  "library": "lancedb",
  "total_apis": 118,
  "apis": [...],
  "by_type": {...},
  "deprecated_count": 3
}
```

### Agent vs MCP Division

```python
# Agent (Environment Interaction + Qualitative):
# - pip install (Bash)
# - Run introspection templates (Bash)
# - Read JSON output
# - Read markdown/JSON extraction files
# - Pattern matching in text
# - Understanding doc structure
# - Orchestrating workflow
# - Building final output

# MCP (Pure Computation):
# - Importance score calculations
# - Coverage tier classification
# - Metric formulas (percentages)
# - Ranking algorithms (prioritization)

# Introspection Templates (Language-Specific):
# - Python: inspect module, __all__, docstrings
# - JavaScript (future): AST parsing, exports
# - TypeScript (future): type declarations
# - Output: Standardized JSON
```

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `APICompletenessOutput`, `UndocumentedAPI`, `DeprecatedInDocs`
- **MCP Server**: `stackbench/mcp_servers/api_completeness_server.py`
- **CLI**: `stackbench run` automatically runs this agent

## See Also

- [Extraction Agent](./extraction-agent.md) - Provides documented APIs
- [Clarity Agent](./clarity-agent.md) - Also uses MCP for deterministic scoring
- Dashboard: Uses this data for coverage visualization
