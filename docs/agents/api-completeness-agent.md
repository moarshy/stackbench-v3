# API Completeness & Deprecation Agent

## Objective

The API Completeness Agent analyzes **documentation coverage** using a **3-stage pipeline architecture**:
- **Stage 1 (Introspection)**: Discovers all public APIs via library introspection
- **Stage 2 (Matching)**: Fast deterministic script matches APIs to ALL documentation
- **Stage 3 (Analysis)**: MCP-based importance scoring and metrics calculation

It:
- Installs the library and runs language-specific introspection templates (Stage 1)
- Scans ALL markdown files using fast fuzzy matching script (Stage 2)
- Aggregates and enriches matches with extraction metadata (Stage 2)
- Calculates importance scores, coverage tiers, and metrics via MCP (Stage 3)
- Identifies undocumented APIs ranked by importance (Stage 3)
- Detects deprecated APIs still taught in documentation (Stage 3)

This agent catches **missing documentation** and **deprecated API usage** - ensuring completeness and currency.

**Key Performance Optimization**: Uses deterministic `markdown_api_matcher.py` script for 5-10x faster matching (~2s for 118 APIs across 7 docs).

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │  (Optional - for metadata enrichment)
└─────────────────────────┘
            ↓
            ↓ (extraction/*.json - optional)
            ↓
┌──────────────────────────────────────────────────────────────┐
│ API COMPLETENESS AGENT - 3-STAGE PIPELINE  ◄── YOU ARE HERE  │
│                                                               │
│  Stage 1: INTROSPECTION                                      │
│    • Bash: pip install library                               │
│    • Bash: Run python_introspect.py                          │
│    • Output: api_surface.json                                │
│                                                               │
│  Stage 2: MATCHING                                           │
│    • Bash: Run markdown_api_matcher.py (fast script)         │
│    • Script scans ALL .md files in docs folder               │
│    • MCP: calculate_importance_score() for each API          │
│    • Agent: Enrich with extraction metadata (optional)       │
│    • Output: documented_apis.json + undocumented_apis.json   │
│                                                               │
│  Stage 3: ANALYSIS                                           │
│    • MCP: Metrics calculations (coverage %, tiers)           │
│    • MCP: Prioritization of undocumented APIs                │
│    • Output: completeness_analysis.json                      │
└──────────────────────────────────────────────────────────────┘
            ↓
            ↓ (completeness_analysis.json)
            ↓
   (Dashboard / Reporting)
```

**Stage**: 2-3 (Runs after extraction if available, in parallel with or after validation agents)
**Runs**: Single execution (not per-document)
**Dependencies**:
  - **Required**: Documentation folder (scans ALL .md files)
  - **Optional**: Extraction results (for metadata enrichment)
**Consumers**: Dashboard, coverage reports
**MCP Server**: `stackbench.mcp_servers.api_completeness_server`
**Deterministic Script**: `stackbench/introspection_templates/markdown_api_matcher.py`

## Architecture: 3-Stage Pipeline

### Stage 1: Introspection Agent
**Responsibilities**:
- **Library Installation**: `pip install` via Bash in agent's environment
- **Introspection Execution**: Run language-specific templates via Bash
  - Python: `stackbench/introspection_templates/python_introspect.py`
  - JavaScript/TypeScript: (Future: `js_introspect.js`, `ts_introspect.ts`)
- **Output**: `api_surface.json` with all discovered APIs

### Stage 2: Matching Agent
**Responsibilities**:
- **Fast Script Execution**: Run `markdown_api_matcher.py` via Bash
  - Script scans ALL .md files in docs folder recursively
  - Fuzzy matching (snake_case ↔ camelCase)
  - Multi-language pattern detection (Python, JS, TS)
  - Outputs `/tmp/api_matches.json` in ~2 seconds
- **MCP Scoring**: Call `calculate_importance_score()` for each API
- **Metadata Enrichment**: Read extraction files (if available) to add section_hierarchy, markdown_anchor, code_block_index
- **Output**: `documented_apis.json` + `undocumented_apis.json`

### Stage 3: Analysis Agent
**Responsibilities**:
- **MCP Metrics**: Call `calculate_metrics()` for coverage percentages
- **MCP Prioritization**: Call `prioritize_undocumented()` to rank by importance
- **Deprecation Detection**: Identify deprecated APIs still in docs
- **Output**: `completeness_analysis.json`

### MCP Server Responsibilities (Deterministic Computation Only)
- **Importance Scoring**: Heuristic-based ranking (0-10)
- **Metrics Calculation**: Coverage percentages
- **Prioritization**: Rank undocumented APIs

### Deterministic Script (`markdown_api_matcher.py`)
**Fast, reliable pattern matching**:
- Scans all .md files recursively (~2s for 118 APIs across 7 docs)
- Generates naming variants (snake_case ↔ camelCase)
- Detects match types: import, function_call, method_call, type_annotation, class_instantiation, mention
- Tracks code block context
- No LLM calls - pure regex-based matching

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
- **`docs_folder`** (Path): Documentation root folder (scans ALL .md files recursively)
- **`output_folder`** (Path): Folder to save all 4 output files
- **`library_name`** (str): Library to analyze (e.g., "lancedb")
- **`library_version`** (str): Version to install and introspect (e.g., "0.25.2")
- **`language`** (str): Programming language ("python", "javascript", "typescript")

### Optional
- **`extraction_folder`** (Path): Folder with extraction results for metadata enrichment (`*_analysis.json`)
- **`validation_log_dir`** (Path): Directory for logs

### Environment
- MCP server (`stackbench.mcp_servers.api_completeness_server`)
- Python environment with pip and `inspect` module
- Deterministic script (`markdown_api_matcher.py`)
- Network access for `pip install`

## Expected Output

### Output Files

```
output_folder/
├── api_surface.json           # Stage 1: All discovered APIs from introspection
├── documented_apis.json       # Stage 2: APIs found in documentation
├── undocumented_apis.json     # Stage 2: APIs missing from documentation
└── completeness_analysis.json # Stage 3: Final metrics and analysis
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

**Enhanced Feature**: Each API in `api_details` now includes a `documentation_references` array with granular location data from both the matching script AND optional extraction metadata:

```json
{
  "documentation_references": [
    {
      "document": "pandas_and_pyarrow.md",             // Document filename
      "line_number": 50,                               // Exact line (from script)
      "context": "db = mylib.connect('./data')",       // Code context (from script)
      "match_type": "function_call",                   // NEW: How API was used
      "matched_variant": "mylib.connect",              // NEW: Actual text matched
      "in_code_block": true,                           // NEW: Inside code fence?

      // Optional enrichment from extraction (if available):
      "section_hierarchy": ["Pandas", "Create"],       // Breadcrumb path
      "markdown_anchor": "#create-dataset",            // Section anchor
      "code_block_index": 0                            // Which code block
    }
  ],
  "reference_count": 23  // NEW: Total references across all docs
}
```

**Match Types** (from script):
- `import` - Import statement (e.g., `import mylib`, `from mylib import X`)
- `function_call` - Direct function call (e.g., `mylib.connect()`)
- `method_call` - Method invocation (e.g., `db.create_table()`)
- `type_annotation` - Type hint (e.g., `: Table`)
- `class_instantiation` - Object creation (e.g., `new Config()`)
- `mention` - Generic mention in text

**Benefits:**
- **Fast Discovery**: Script finds ALL mentions in ~2 seconds
- **Fuzzy Matching**: Handles snake_case ↔ camelCase automatically
- **Context Tracking**: Know exactly how each API is used
- **Granular Traceability**: File, line, match type, code context
- **Optional Enrichment**: Add section hierarchy from extraction metadata
- **Frontend Navigation**: Click reference → Jump to exact doc location
- **Coverage Heatmap**: Visualize which docs cover which APIs

**Backward Compatibility:**
- `documented_in` remains as derived field (unique list of documents)
- Existing dashboards work unchanged
- New fields are additive

## Pseudocode

```python
async def analyze_completeness(docs_folder, library_name, library_version, language, extraction_folder=None):
    """Analyze API completeness using 3-stage pipeline."""

    # Setup MCP server
    mcp_config = {
        "api-completeness": {
            "command": "python",
            "args": ["-m", "stackbench.mcp_servers.api_completeness_server"],
            "transport": "stdio"
        }
    }

    # =========================================================================
    # STAGE 1: INTROSPECTION
    # =========================================================================
    stage1_agent = IntrospectionAgent(
        library_name=library_name,
        library_version=library_version,
        language=language
    )

    await stage1_agent.run()
    # Output: api_surface.json

    # =========================================================================
    # STAGE 2: MATCHING
    # =========================================================================
    stage2_agent = MatchingAgent(
        api_surface_file="api_surface.json",
        docs_folder=docs_folder,           # NEW: Scans ALL .md files
        language=language,
        extraction_folder=extraction_folder  # Optional: for enrichment
    )

    await stage2_agent.run()
    # Output: documented_apis.json + undocumented_apis.json

    # =========================================================================
    # STAGE 3: ANALYSIS
    # =========================================================================
    stage3_agent = AnalysisAgent(
        api_surface_file="api_surface.json",
        documented_file="documented_apis.json",
        undocumented_file="undocumented_apis.json",
        library_name=library_name,
        library_version=library_version
    )

    await stage3_agent.run()
    # Output: completeness_analysis.json


# =========================================================================
# STAGE 2 MATCHING AGENT - What Claude does
# =========================================================================
def stage2_matching_workflow(api_surface_file, docs_folder, language, extraction_folder):
    """Stage 2: Fast script-based matching + MCP scoring + optional enrichment."""

    # STEP 1: Read api_surface.json from Stage 1
    api_surface = load_json(api_surface_file)
    discovered_apis = api_surface["apis"]  # List of all APIs from introspection

    # STEP 2: Run fast deterministic matching script (Bash)
    run_bash(f"""
        python stackbench/introspection_templates/markdown_api_matcher.py \
            {docs_folder} \
            {api_surface_file} \
            /tmp/api_matches.json \
            {language}
    """)
    # Script outputs: /tmp/api_matches.json in ~2 seconds
    # Format:
    # {
    #   "mylib.connect": {
    #     "documented": true,
    #     "reference_count": 23,
    #     "files": ["quickstart.md", "api.md"],
    #     "references": [
    #       {
    #         "file": "quickstart.md",
    #         "line": 42,
    #         "context": "db = mylib.connect('./data')",
    #         "match_type": "function_call",
    #         "matched_variant": "mylib.connect",
    #         "in_code_block": true
    #       }
    #     ]
    #   }
    # }

    # STEP 3: Read script output (agent)
    api_matches = load_json("/tmp/api_matches.json")

    # STEP 4: Calculate importance scores via MCP (for ALL APIs)
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

    # STEP 5: Enrich documented APIs with extraction metadata (OPTIONAL)
    # If extraction_folder exists, add section_hierarchy, markdown_anchor, code_block_index
    if extraction_folder:
        extraction_files = glob(extraction_folder, "*_analysis.json")
        extraction_metadata = {}  # api -> [{section_hierarchy, markdown_anchor, ...}]

        for extraction_file in extraction_files:
            data = load_json(extraction_file)
            for sig in data.get("signatures", []):
                api_id = f"{sig['library']}.{sig['function']}"
                if api_id not in extraction_metadata:
                    extraction_metadata[api_id] = []
                extraction_metadata[api_id].append({
                    "section_hierarchy": sig.get("section_hierarchy"),
                    "markdown_anchor": sig.get("markdown_anchor"),
                    "code_block_index": sig.get("code_block_index")
                })

        # Merge extraction metadata into script matches
        for api_id, match_data in api_matches.items():
            if api_id in extraction_metadata:
                for ref in match_data["references"]:
                    # Match by file and line to find corresponding extraction metadata
                    # (simplified - actual implementation more sophisticated)
                    ref.update(extraction_metadata[api_id][0])

    # STEP 6: Build documented_apis.json and undocumented_apis.json
    documented_apis = []
    undocumented_apis = []

    for api_obj in discovered_apis:
        api_id = api_obj["api"]
        match_data = api_matches.get(api_id, {"documented": false})
        importance = importance_scores[api_id]

        api_detail = {
            "api": api_id,
            "module": api_obj["module"],
            "type": api_obj["type"],
            "is_async": api_obj["is_async"],
            "has_docstring": api_obj["has_docstring"],
            "in_all": api_obj["in_all"],
            "is_deprecated": api_obj["is_deprecated"],
            "signature": api_obj["signature"],
            "importance": importance["importance"],
            "importance_score": importance["importance_score"],
            "reference_count": match_data.get("reference_count", 0),
            "documentation_references": match_data.get("references", []),
            "documented_in": match_data.get("files", [])
        }

        if match_data["documented"]:
            documented_apis.append(api_detail)
        else:
            undocumented_apis.append(api_detail)

    write_json("documented_apis.json", documented_apis)
    write_json("undocumented_apis.json", undocumented_apis)

# =========================================================================
# STAGE 3 ANALYSIS AGENT - What MCP does
# =========================================================================
def stage3_analysis_workflow(api_surface_file, documented_file, undocumented_file):
    """Stage 3: MCP metrics + prioritization."""

    # STEP 1: Calculate metrics (MCP)
    coverage_data = []
    for api in load_json(documented_file):
        tier = 1  # At least mentioned (script found it)
        if api["reference_count"] > 5:
            tier = 2  # Has examples (heuristic: many references)
        coverage_data.append({"api": api["api"], "tier": tier})

    for api in load_json(undocumented_file):
        coverage_data.append({"api": api["api"], "tier": 0})

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

- **Single run**: Not per-document (runs once for entire library)
- **Typical duration**: ~7 seconds total for 118 APIs across 7 docs
  - Stage 1 (Introspection): ~2-3 seconds (pip install + inspect)
  - Stage 2 (Matching): ~2 seconds (fast script + MCP scoring)
  - Stage 3 (Analysis): ~2 seconds (MCP metrics)
- **Performance Improvement**: 5-10x faster than previous LLM-based matching
  - **Before**: 30-60 seconds (agent pattern matching ALL docs)
  - **After**: ~7 seconds (deterministic script + MCP)
- **Bottlenecks**:
  - Library installation (Stage 1: pip install)
  - MCP scoring calls (Stage 2: one per API)
  - Optional extraction metadata reading (Stage 2: if provided)
- **Scalability**:
  - Script handles 1000+ APIs in ~5 seconds
  - MCP calls are fast (<50ms each)
  - Total time dominated by pip install, not matching

## Common Issues & Solutions

### Issue: Many false "undocumented" for internal methods
**Cause**: Introspection finding private methods
**Solution**: Stage 1 filters by `__all__` and `_` prefix during introspection

### Issue: Missing deprecation warnings
**Cause**: Library doesn't use standard patterns
**Solution**: Enhance Stage 1 deprecation detection in introspection template

### Issue: Coverage tier 0 for documented APIs
**Cause**: API name mismatch (e.g., snake_case vs camelCase)
**Solution**: Script handles fuzzy matching automatically via `generate_variants()`. Check Stage 2 logs for matched variants.

### Issue: Script finds API in docs but not in extraction metadata
**Cause**: Extraction folder not provided or incomplete
**Solution**: This is expected! Script scans ALL .md files. Extraction metadata is optional enrichment. The API is still correctly marked as documented.

### Issue: Reference count seems low
**Cause**: Script only counts actual API mentions, not generic text
**Solution**: Check Stage 2 output `/tmp/api_matches.json` to see all detected references and match types

### Issue: Stage 1 introspection fails
**Cause**: Library installation failed (network, version unavailable)
**Solution**: Check Stage 1 logs for pip errors. Ensure version exists on PyPI/npm.

## Implementation Notes

### Why 3-Stage Architecture?

**Design Rationale:**

**Why separate stages instead of monolithic agent?**
1. **Specialization**: Each agent has a focused responsibility
2. **Resumability**: Can re-run Stage 2 without re-introspecting
3. **Debugging**: Easy to identify which stage failed
4. **Intermediate Outputs**: Each stage produces debuggable JSON
5. **Performance**: Script-based matching is 5-10x faster than LLM pattern matching

**Stage 1: Why Bash-based introspection?**
```python
# PROBLEM: MCP subprocess can't access packages installed in parent environment
# ❌ MCP server runs as subprocess with isolation
# ❌ Even with sys.executable, package isolation persists

# SOLUTION: Bash-based introspection templates
# ✅ Agent installs library in its own environment (Bash)
# ✅ Agent runs language-specific template via Bash (same environment)
# ✅ Template outputs standardized JSON
# ✅ Clean separation: Environment interaction (Bash) vs API discovery (template script)
```

**Stage 2: Why deterministic script instead of LLM matching?**
```python
# PROBLEM: LLM-based pattern matching is slow (30-60s for 118 APIs)
# ❌ Agent must read ALL docs and pattern match (slow)
# ❌ Multiple back-and-forth with Claude
# ❌ Costs API tokens

# SOLUTION: Fast deterministic script + MCP scoring
# ✅ Regex-based matching in ~2 seconds
# ✅ Fuzzy matching (snake_case ↔ camelCase) built-in
# ✅ Multi-language pattern detection
# ✅ MCP only for scoring (not matching)
# ✅ 5-10x performance improvement
```

**Stage 3: Why MCP for metrics?**
```python
# MCP is perfect for deterministic computations:
# ✅ Coverage percentage formulas
# ✅ Importance score heuristics
# ✅ Prioritization algorithms
# ✅ No environment interaction needed
```

### Architecture Division

```python
# STAGE 1 AGENT (Introspection)
# - Bash: pip install
# - Bash: Run python_introspect.py template
# - Output: api_surface.json

# STAGE 2 AGENT (Matching)
# - Bash: Run markdown_api_matcher.py script (fast deterministic)
# - Read: /tmp/api_matches.json (script output)
# - Read: extraction/*.json (optional enrichment)
# - MCP: calculate_importance_score() for each API
# - Write: documented_apis.json + undocumented_apis.json

# STAGE 3 AGENT (Analysis)
# - Read: api_surface.json + documented_apis.json + undocumented_apis.json
# - MCP: calculate_metrics() (coverage %)
# - MCP: prioritize_undocumented() (ranking)
# - Write: completeness_analysis.json

# DETERMINISTIC SCRIPT (markdown_api_matcher.py)
# - Pure Python script (no LLM)
# - Scans ALL .md files recursively
# - Generates naming variants (snake_case ↔ camelCase)
# - Detects match types (import, function_call, method_call, etc.)
# - Tracks code block context
# - Outputs /tmp/api_matches.json in ~2 seconds

# MCP SERVER (api_completeness_server.py)
# - Pure computational tasks:
#   * calculate_importance_score() - heuristic scoring
#   * calculate_metrics() - coverage percentages
#   * prioritize_undocumented() - ranking by importance
```

### Introspection Templates

**Template-Based Design:**
```python
# Language-specific scripts output standardized JSON:

# Python template:
python stackbench/introspection_templates/python_introspect.py mylib 0.25.2 > api_surface.json

# Future JavaScript template:
node stackbench/introspection_templates/js_introspect.js mylib 1.6.0 > api_surface.json

# Standardized output format (same across languages):
{
  "library": "mylib",
  "version": "0.25.2",
  "language": "python",
  "total_apis": 118,
  "apis": [
    {
      "api": "mylib.connect",
      "module": "mylib",
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

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `APICompletenessOutput`, `UndocumentedAPI`, `DeprecatedInDocs`
- **MCP Server**: `stackbench/mcp_servers/api_completeness_server.py`
- **CLI**: `stackbench run` automatically runs this agent

## See Also

- [Extraction Agent](./extraction-agent.md) - Provides documented APIs
- [Clarity Agent](./clarity-agent.md) - Also uses MCP for deterministic scoring
- Dashboard: Uses this data for coverage visualization
