# API Completeness & Deprecation Agent

## Objective

The API Completeness Agent analyzes **documentation coverage** by discovering all public APIs in a library and cross-referencing them with what's actually documented. It:
- Introspects the library to discover all public APIs
- Aggregates documented APIs from all extraction results
- Calculates tiered coverage (mentioned, has example, dedicated section)
- Identifies undocumented APIs ranked by importance
- Detects deprecated APIs still taught in documentation

This agent catches **missing documentation** and **deprecated API usage** - ensuring completeness and currency.

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │
└─────────────────────────┘
            ↓
            ↓ (extraction/*.json - ALL docs)
            ↓
┌─────────────────────────┐
│ API COMPLETENESS AGENT  │ ◄── YOU ARE HERE
│  (Single Run)           │
└─────────────────────────┘
            ↓
            ↓ (completeness_analysis.json)
            ↓
   (Dashboard / Reporting)
```

**Stage**: 2-3 (Runs after extraction, in parallel with or after validation agents)
**Runs**: Single execution (not per-document)
**Dependencies**: ALL extraction results
**Consumers**: Dashboard, coverage reports

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
    },
    {
      "api": "lancedb.Database.list_tables",
      "module": "lancedb.db",
      "type": "method",
      "importance": "high",
      "importance_score": 7,
      "reason": "In __all__, has docstring, discovery operation",
      "has_docstring": true,
      "is_async": false
    },
    {
      "api": "lancedb.Config.from_env",
      "module": "lancedb",
      "type": "method",
      "importance": "medium",
      "importance_score": 5,
      "reason": "Has docstring, configuration helper",
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
      "documented_in": ["quickstart.md", "api-reference.md"],
      "has_examples": true,
      "has_dedicated_section": true,
      "importance": "high",
      "importance_score": 9
    },
    {
      "api": "lancedb.Database.create_table",
      "module": "lancedb.db",
      "type": "method",
      "is_deprecated": false,
      "coverage_tier": 2,
      "documented_in": ["quickstart.md"],
      "has_examples": true,
      "has_dedicated_section": false,
      "importance": "high",
      "importance_score": 8
    },
    {
      "api": "lancedb.Database.drop_table",
      "module": "lancedb.db",
      "type": "method",
      "is_deprecated": false,
      "coverage_tier": 0,
      "documented_in": [],
      "has_examples": false,
      "has_dedicated_section": false,
      "importance": "high",
      "importance_score": 8
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

## Pseudocode

```python
async def analyze_completeness(extraction_folder, library_name, library_version):
    """Analyze API completeness across all documentation."""

    # 1. Ask Claude to do 3-phase analysis
    prompt = f"""
    Analyze API completeness for {library_name} v{library_version}.

    Extraction files: {extraction_folder}

    PHASE 1: DISCOVER LIBRARY API SURFACE
    1. Install {library_name}=={library_version}
    2. Introspect all public APIs (functions, classes, methods)
    3. Detect deprecated APIs (@deprecated, DeprecationWarning)
    4. Calculate importance score (0-10) for each API:
       - In __all__: +3
       - Has docstring: +2
       - Not underscore-prefixed: +1
       - Top-level module: +1
       - Common name (connect, create, get): +1
    5. Group by module and type

    PHASE 2: AGGREGATE DOCUMENTATION COVERAGE
    6. Read all *_analysis.json files from {extraction_folder}
    7. For each extraction:
       - Extract documented API signatures
       - Extract code examples
       - Track which APIs appear where
    8. Classify coverage tiers:
       - Tier 0: Undocumented (not mentioned)
       - Tier 1: Mentioned (in signatures)
       - Tier 2: Has examples (in code examples)
       - Tier 3: Dedicated section (context indicates focus)

    PHASE 3: CROSS-REFERENCE & ANALYZE
    9. Cross-reference library APIs with documented APIs
    10. Identify undocumented APIs (tier 0), ranked by importance
    11. Identify deprecated APIs in docs
    12. Calculate coverage percentages

    Output JSON ONLY.
    """

    response = await claude.query(prompt)

    # 2. Parse and validate
    analysis_data = parse_json(response)
    validate_against_schema(analysis_data)

    # 3. Save result
    output = APICompletenessOutput(**analysis_data)
    save_json(output_folder / "completeness_analysis.json", output)

    return output


# What Claude does internally
def claude_completeness_logic(library_name, library_version, extraction_folder):
    """Claude's 3-phase analysis."""

    # PHASE 1: DISCOVER LIBRARY API SURFACE
    # 1. Install library
    run_bash(f"pip install {library_name}=={library_version}")

    # 2. Introspect all public APIs
    import inspect
    import importlib
    import warnings

    lib = importlib.import_module(library_name)
    discovered_apis = []

    # Find all public modules
    for module_name in find_submodules(lib):
        module = importlib.import_module(module_name)

        # Get __all__ if present
        public_names = getattr(module, '__all__', None)

        # Discover functions and classes
        for name, obj in inspect.getmembers(module):
            # Skip private unless in __all__
            if name.startswith('_') and (not public_names or name not in public_names):
                continue

            # Determine type
            if inspect.isfunction(obj):
                api_type = "function"
            elif inspect.isclass(obj):
                api_type = "class"
                # Also get class methods
                for method_name, method_obj in inspect.getmembers(obj):
                    if not method_name.startswith('_') or (public_names and method_name in public_names):
                        if inspect.ismethod(method_obj) or inspect.isfunction(method_obj):
                            discovered_apis.append({
                                "api": f"{name}.{method_name}",
                                "module": module_name,
                                "type": "method",
                                ...
                            })
            elif inspect.ismethod(obj):
                api_type = "method"
            elif isinstance(obj, property):
                api_type = "property"
            else:
                continue

            # Check for deprecation
            is_deprecated = False
            deprecation_message = None

            # Strategy 1: Check for @deprecated decorator
            if hasattr(obj, '__deprecated__'):
                is_deprecated = True
                deprecation_message = obj.__deprecated__

            # Strategy 2: Check docstring for deprecation
            if obj.__doc__ and 'deprecated' in obj.__doc__.lower():
                is_deprecated = True
                deprecation_message = extract_deprecation_from_docstring(obj.__doc__)

            # Strategy 3: Try calling and catch warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    # Try getting signature (may trigger warning)
                    inspect.signature(obj)
                except:
                    pass

                if w and any(issubclass(warning.category, DeprecationWarning) for warning in w):
                    is_deprecated = True
                    deprecation_message = str(w[0].message)

            # Calculate importance score
            importance_score = 0
            if public_names and name in public_names:
                importance_score += 3
            if obj.__doc__:
                importance_score += 2
            if not name.startswith('_'):
                importance_score += 1
            if module_name == library_name:  # Top-level
                importance_score += 1
            if name in ['connect', 'create', 'get', 'open', 'close', 'add', 'update', 'delete']:
                importance_score += 1

            # Classify importance
            if importance_score > 6:
                importance = "high"
            elif importance_score >= 3:
                importance = "medium"
            else:
                importance = "low"

            discovered_apis.append({
                "api": f"{module_name}.{name}",
                "module": module_name,
                "type": api_type,
                "is_deprecated": is_deprecated,
                "deprecation_message": deprecation_message,
                "has_docstring": bool(obj.__doc__),
                "is_async": inspect.iscoroutinefunction(obj),
                "in_all": public_names and name in public_names,
                "importance": importance,
                "importance_score": importance_score
            })

    # PHASE 2: AGGREGATE DOCUMENTATION COVERAGE
    # 3. Read all extraction files
    extraction_files = glob(extraction_folder, "*_analysis.json")

    documented_apis = {}  # api -> [pages, tier]

    for extraction_file in extraction_files:
        data = load_json(extraction_file)
        page_name = data["page"]

        # Check signatures
        for sig in data.get("signatures", []):
            api_id = f"{sig['library']}.{sig['function']}"
            if sig.get('method_chain'):
                api_id = f"{sig['method_chain']}.{sig['function']}"

            if api_id not in documented_apis:
                documented_apis[api_id] = {
                    "pages": [],
                    "tier": 1  # Mentioned
                }

            documented_apis[api_id]["pages"].append(page_name)

        # Check examples
        for example in data.get("examples", []):
            # Parse code to find API calls
            api_calls = extract_api_calls(example["code"], library_name)

            for api_call in api_calls:
                if api_call in documented_apis:
                    # Upgrade tier to 2 (has example)
                    documented_apis[api_call]["tier"] = max(
                        documented_apis[api_call]["tier"],
                        2
                    )
                else:
                    documented_apis[api_call] = {
                        "pages": [page_name],
                        "tier": 2
                    }

        # Check for dedicated sections
        # If context/section hierarchy indicates focus on specific API
        for sig in data.get("signatures", []):
            api_id = f"{sig['library']}.{sig['function']}"
            if is_dedicated_section(sig.get("section_hierarchy", []), sig["function"]):
                if api_id in documented_apis:
                    documented_apis[api_id]["tier"] = 3

    # PHASE 3: CROSS-REFERENCE & ANALYZE
    # 4. Cross-reference
    api_details = []
    undocumented_apis = []
    deprecated_in_docs = []

    for api_obj in discovered_apis:
        api_id = api_obj["api"]

        # Check if documented
        if api_id in documented_apis:
            doc_info = documented_apis[api_id]

            api_details.append({
                "api": api_id,
                "module": api_obj["module"],
                "type": api_obj["type"],
                "is_deprecated": api_obj["is_deprecated"],
                "coverage_tier": doc_info["tier"],
                "documented_in": doc_info["pages"],
                "has_examples": doc_info["tier"] >= 2,
                "has_dedicated_section": doc_info["tier"] == 3,
                "importance": api_obj["importance"],
                "importance_score": api_obj["importance_score"]
            })

            # Check if deprecated but still documented
            if api_obj["is_deprecated"]:
                deprecated_in_docs.append({
                    "api": api_id,
                    "module": api_obj["module"],
                    "deprecated_since": extract_version(api_obj["deprecation_message"]),
                    "alternative": extract_alternative(api_obj["deprecation_message"]),
                    "documented_in": doc_info["pages"],
                    "severity": "critical",
                    "deprecation_message": api_obj["deprecation_message"],
                    "suggestion": f"Replace {api_id} in {', '.join(doc_info['pages'])}"
                })
        else:
            # Undocumented
            undocumented_apis.append({
                "api": api_id,
                "module": api_obj["module"],
                "type": api_obj["type"],
                "importance": api_obj["importance"],
                "importance_score": api_obj["importance_score"],
                "reason": explain_importance(api_obj),
                "has_docstring": api_obj["has_docstring"],
                "is_async": api_obj["is_async"]
            })

            api_details.append({
                "api": api_id,
                "coverage_tier": 0,
                "documented_in": [],
                "has_examples": False,
                "has_dedicated_section": False,
                ...
            })

    # Sort undocumented by importance
    undocumented_apis.sort(key=lambda x: x["importance_score"], reverse=True)

    # 5. Calculate summary
    total_apis = len(discovered_apis)
    documented = len([api for api in api_details if api["coverage_tier"] >= 1])
    with_examples = len([api for api in api_details if api["coverage_tier"] >= 2])
    with_sections = len([api for api in api_details if api["coverage_tier"] == 3])
    undocumented = len([api for api in api_details if api["coverage_tier"] == 0])

    return {
        "api_surface": {
            "total_public_apis": total_apis,
            "by_module": group_by_module(discovered_apis),
            "by_type": count_by_type(discovered_apis),
            "deprecated_count": len([a for a in discovered_apis if a["is_deprecated"]])
        },
        "coverage_summary": {
            "total_apis": total_apis,
            "documented": documented,
            "with_examples": with_examples,
            "with_dedicated_sections": with_sections,
            "undocumented": undocumented,
            "coverage_percentage": round(documented / total_apis * 100, 1),
            "example_coverage_percentage": round(with_examples / total_apis * 100, 1),
            "complete_coverage_percentage": round(with_sections / total_apis * 100, 1)
        },
        "undocumented_apis": undocumented_apis[:20],  # Top 20
        "deprecated_in_docs": deprecated_in_docs,
        "api_details": api_details
    }
```

## Key Features

### 1. **Importance Scoring Algorithm**

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
# high: > 6, medium: 3-6, low: < 3
```

### 2. **Coverage Tiers**

- **Tier 0**: Undocumented (not mentioned anywhere)
- **Tier 1**: Mentioned (appears in signatures list)
- **Tier 2**: Has examples (used in code examples)
- **Tier 3**: Dedicated section (has own section/heading)

### 3. **Deprecation Detection Strategies**

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

### 4. **Cross-Module Discovery**

Recursively finds all submodules:
```python
# Discovers:
lancedb
lancedb.db
lancedb.table
lancedb.query
lancedb.embeddings
...
```

## Logging & Debugging

### Logs
```
validation_log_dir/api_completeness_logs/
├── agent.log       # Human-readable log
├── tools.jsonl     # Bash, Read tool calls
└── messages.jsonl  # Full Claude conversation
```

## Performance

- **Single run**: Not per-document
- **Typical duration**: ~5-10 seconds
- **Bottlenecks**: Library introspection time

## Common Issues & Solutions

### Issue: Many false "undocumented" for helper methods
**Cause**: Introspection finding internal methods
**Solution**: Filter by `__all__`, increase `_` prefix filtering

### Issue: Missing deprecation warnings
**Cause**: Library doesn't use standard patterns
**Solution**: Add library-specific deprecation detection

### Issue: Coverage tier 0 for documented APIs
**Cause**: API name mismatch (e.g., `connect` vs `lancedb.connect`)
**Solution**: Normalize API identifiers during comparison

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `APICompletenessOutput`, `UndocumentedAPI`, `DeprecatedInDocs`
- **CLI**: `stackbench run` automatically runs this agent

## See Also

- [Extraction Agent](./extraction-agent.md) - Provides documented APIs
- Dashboard: Uses this data for coverage visualization
