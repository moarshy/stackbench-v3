# Documentation Clarity Validation Agent

## Objective

The Clarity Validation Agent evaluates documentation quality from a **user experience perspective** using an LLM-as-judge approach **across Python, JavaScript, and TypeScript**. It:
- Assesses instructional clarity and logical flow
- Identifies gaps, unclear steps, and missing prerequisites
- Checks technical accessibility (broken links, missing alt text, code blocks)
- Verifies language-appropriate syntax patterns (imports/requires, async patterns)
- Generates clarity scores (0-10 scale) across 5 dimensions
- Provides actionable improvement roadmap with impact/effort estimates

This agent catches **UX issues** that static analysis misses - problems a real developer would encounter while following a tutorial in any supported language.

## Position in Pipeline

```
┌─────────────────────────┐
│   EXTRACTION AGENT      │
└─────────────────────────┘
            ↓
            ↓ (extraction/{doc}_analysis.json)
            ↓
┌─────────────────────────┐
│ API VALIDATION AGENT    │
│ CODE VALIDATION AGENT   │
└─────────────────────────┘
            ↓
            ↓ (api_validation/, code_validation/)
            ↓
┌─────────────────────────┐
│ CLARITY VALIDATION AGENT│ ◄── YOU ARE HERE
│  (Parallel Workers)     │
└─────────────────────────┘
```

**Stage**: 3 (Third)
**Runs**: In parallel across documents (default: 5 workers)
**Dependencies**: Extraction output (required), API/Code validation (optional for correlation)
**Consumers**: Frontend dashboard, improvement roadmap

## Inputs

### Required
- **`extraction_folder`** (Path): Folder with extraction results
- **`output_folder`** (Path): Folder to save clarity validation results
- **`repository_folder`** (Path): Cloned repository with original markdown files

### Optional
- **`num_workers`** (int): Number of parallel workers (default: 5)
- **`validation_log_dir`** (Path): Directory for logs

### Environment
- Original markdown files in `repository_folder`
- API/Code validation results (optional, for correlation)
- MCP server for clarity scoring (`stackbench.mcp_servers.clarity_scoring_server`)
- Language context from extraction metadata (python/javascript/typescript)

## Expected Output

### Output Files

For each extraction file `{doc_name}_analysis.json`, produces:
```
output_folder/
├── {doc_name}_clarity.json      # Per-document clarity validation
└── validation_summary.json      # Aggregate statistics
```

### Output Schema (`{doc_name}_clarity.json`)

```json
{
  "validation_id": "uuid-here",
  "validated_at": "2025-01-15T11:00:00Z",
  "source_file": "quickstart_analysis.json",
  "document_page": "quickstart.md",
  "library": "mylib",
  "version": "1.2.3",
  "language": "python",  // or "javascript", "typescript"

  "clarity_score": {
    "overall_score": 7.5,
    "tier": "B",
    "instruction_clarity": 8.0,
    "logical_flow": 7.0,
    "completeness": 7.5,
    "consistency": 8.5,
    "prerequisite_coverage": 6.5
  },

  "clarity_issues": [
    {
      "type": "logical_gap",
      "severity": "critical",
      "line": 45,
      "section": "Creating Tables",
      "step_number": 3,
      "message": "Step 3 references 'config.yaml' but file was never created in prior steps",
      "suggested_fix": "Add Step 2b: Create config.yaml with example content",
      "affected_code": "config = Config.from_file('config.yaml')",
      "context_quote": "Now load your configuration: ..."
    },
    {
      "type": "cross_section_variable_reference",
      "severity": "info",
      "line": 133,
      "section": "From Pydantic Models",
      "step_number": 2,
      "message": "Variable 'data' used here was defined in section 'From Polars DataFrame' above",
      "suggested_fix": "Add comment or redefine data for users who jump to this section",
      "affected_code": "df = pl.DataFrame(data)",
      "context_quote": "..."
    }
  ],

  "structural_issues": [
    {
      "type": "buried_prerequisites",
      "severity": "warning",
      "location": "Prerequisites mentioned at lines 87, 102, 156 instead of upfront",
      "message": "Prerequisites scattered throughout rather than consolidated at top",
      "suggested_fix": "Create 'Prerequisites' section at beginning with all requirements"
    }
  ],

  "technical_accessibility": {
    "broken_links": [
      {
        "url": "https://example.com/old-docs",
        "line": 34,
        "link_text": "See configuration guide",
        "error": "404 Not Found"
      }
    ],
    "missing_alt_text": [
      {
        "image_path": "images/architecture.png",
        "line": 67
      }
    ],
    "code_blocks_without_language": [
      {
        "line": 23,
        "content_preview": "npm install mylib",
        "message": "Code block missing language specifier (should be ```bash or ```shell)"
      }
    ],
    "total_links_checked": 15,
    "total_images_checked": 3,
    "total_code_blocks_checked": 12,
    "all_validated": false
  },

  "improvement_roadmap": {
    "current_overall_score": 7.5,
    "projected_score_after_critical_fixes": 8.2,
    "projected_score_after_all_fixes": 8.9,
    "prioritized_fixes": [
      {
        "priority": "critical",
        "category": "logical_flow",
        "description": "Fix config.yaml reference gap at step 3",
        "location": "Line 45, Section: Creating Tables",
        "impact": "high",
        "effort": "low",
        "projected_score_change": 0.7
      }
    ],
    "quick_wins": [
      {
        "priority": "high",
        "category": "completeness",
        "description": "Add Prerequisites section at top",
        "location": "Beginning of document",
        "impact": "medium",
        "effort": "low",
        "projected_score_change": 0.5
      }
    ]
  },

  "score_explanation": {
    "score": 7.5,
    "tier": "B",
    "tier_description": "Good quality documentation with minor issues",
    "score_breakdown": {
      "base_score": 10.0,
      "critical_issues_penalty": -1.5,
      "warning_issues_penalty": -0.5,
      "info_issues_penalty": -0.2,
      "failed_examples_penalty": -0.3,
      "invalid_api_penalty": 0.0,
      "missing_api_penalty": 0.0,
      "final_score": 7.5
    },
    "tier_requirements": {
      "current_tier": "B",
      "next_tier": "A",
      "requirements_for_next_tier": {
        "critical_issues": "≤ 0 (currently 1)",
        "warning_issues": "≤ 1 (currently 2)",
        "overall_score": "≥ 8.5 (currently 7.5)"
      },
      "current_status": {
        "critical_issues": 1,
        "warning_issues": 2,
        "overall_score": 7.5
      }
    },
    "primary_issues": [
      {
        "category": "logical_flow",
        "critical": 1,
        "warning": 0,
        "info": 0,
        "example": "Step 3 references 'config.yaml' not created earlier"
      },
      {
        "category": "completeness",
        "critical": 0,
        "warning": 2,
        "info": 1,
        "example": "Prerequisites scattered throughout document"
      }
    ],
    "summary": "Document has good overall quality (B tier, 7.5/10). Main issue is a critical logical gap where Step 3 references a file not created. Fix this + consolidate prerequisites to reach A tier (8.5+)."
  },

  "summary": {
    "total_clarity_issues": 2,
    "critical_clarity_issues": 1,
    "warning_clarity_issues": 0,
    "info_clarity_issues": 1,
    "total_structural_issues": 1,
    "critical_structural_issues": 0,
    "total_technical_issues": 3,
    "overall_quality_rating": "good"
  },

  "processing_time_ms": 4500,
  "warnings": []
}
```

## Pseudocode

```python
async def analyze_all_documents(extraction_folder, repository_folder):
    """Analyze clarity for all documents in parallel."""

    # 1. Find extraction files
    extraction_files = glob(extraction_folder, "*_analysis.json")

    # 2. Parallel processing with worker pool
    semaphore = Semaphore(num_workers)
    tasks = [
        analyze_document(extraction_file, repository_folder, semaphore)
        for extraction_file in extraction_files
    ]

    results = await gather(*tasks)

    # 3. Aggregate summary
    save_summary(results)

    return results


async def analyze_document(extraction_file, repository_folder):
    """Analyze clarity for a single document."""

    # 1. Load extraction data
    extraction_data = load_json(extraction_file)
    document_page = extraction_data["page"]

    # 2. Load validation results (optional)
    api_validation = load_optional(f"api_validation/{doc_stem}_validation.json")
    code_validation = load_optional(f"code_validation/{doc_stem}_validation.json")

    # 3. Read original markdown
    markdown_path = find_file(repository_folder, document_page)
    content = read_file(markdown_path)

    # 4. Pre-process snippets (Level 2 - fast path)
    processed_content, warnings = preprocess_markdown_snippets(
        content,
        markdown_path,
        repository_folder
    )

    # 5. Create Claude agent with MCP server configured
    hooks = create_validation_hooks() + create_logging_hooks()

    options = ClaudeAgentOptions(
        system_prompt=CLARITY_SYSTEM_PROMPT,  # Mentions MCP tools
        allowed_tools=["Read"],
        mcp_servers={
            "clarity-scoring": {
                "command": sys.executable,
                "args": ["-m", "stackbench.mcp_servers.clarity_scoring_server"],
            }
        },
        hooks=hooks
    )

    # 6. Ask Claude to analyze AND call MCP tools
    async with ClaudeSDKClient(options=options) as client:
        prompt = f"""
        Analyze this documentation from a user experience perspective.

        Document: {document_page}
        Library: {extraction_data["library"]} v{extraction_data["version"]}
        Language: {extraction_data["language"]}

        CONTEXT:
        - API validation results: {summarize(api_validation)}
        - Code validation results: {summarize(code_validation)}

        INSTRUCTIONS:
        1. Find issues across 5 dimensions (clarity, flow, completeness, consistency, prerequisites)
        2. Check technical accessibility (broken links, missing alt text, code blocks)
        3. Call MCP tools to calculate scores:
           - calculate_clarity_score(issues, metrics)
           - get_improvement_roadmap(issues, metrics, score)
           - explain_score(score, breakdown, issues, metrics)
        4. Return complete JSON with issues AND all MCP results

        Content:
        {processed_content}
        """

        response = await client.query(prompt)

    # 7. Parse complete response (includes both analysis and MCP results)
    clarity_data = parse_json(response)

    # Validate MCP tools were called
    if not clarity_data.get("clarity_score"):
        raise Error("Agent didn't call MCP tools")

    # 8. Construct output from single response
    output = ClarityValidationOutput(
        clarity_score=clarity_data["clarity_score"],
        clarity_issues=clarity_data["clarity_issues"],
        structural_issues=clarity_data["structural_issues"],
        technical_accessibility=clarity_data["technical_accessibility"],
        improvement_roadmap=clarity_data["improvement_roadmap"],
        score_explanation=clarity_data["score_explanation"],
        summary=clarity_data["summary"]
    )

    # 9. Save
    save_json(output_folder / f"{doc_stem}_clarity.json", output)

    return output


# What Claude does (issue finding)
def claude_clarity_analysis(content, library, api_validation, code_validation):
    """Claude identifies issues."""

    clarity_issues = []
    structural_issues = []
    broken_links = []

    # 1. Walk through document as a new user would
    sections = parse_sections(content)

    for section in sections:
        steps = identify_steps(section)

        # 2. Check logical flow
        for i, step in enumerate(steps):
            # Does step reference undefined resources?
            referenced_resources = extract_resources(step.code)

            for resource in referenced_resources:
                if not defined_in_previous_steps(resource, steps[:i]):
                    # Check if defined elsewhere in document
                    if defined_anywhere(resource, content):
                        # Cross-section reference
                        clarity_issues.append({
                            "type": "cross_section_variable_reference",
                            "severity": "info",
                            "line": step.line,
                            "section": section.name,
                            "step_number": i + 1,
                            "message": f"Variable '{resource}' defined in earlier section",
                            "suggested_fix": "Add note or redefine for this section"
                        })
                    else:
                        # Truly undefined
                        clarity_issues.append({
                            "type": "logical_gap",
                            "severity": "critical",
                            "line": step.line,
                            "section": section.name,
                            "step_number": i + 1,
                            "message": f"Step references '{resource}' never created",
                            "suggested_fix": "Add step to create/define this resource"
                        })

    # 3. Check prerequisites
    prerequisites = find_prerequisites(content)
    if prerequisites_scattered(prerequisites):
        structural_issues.append({
            "type": "buried_prerequisites",
            "severity": "warning",
            "message": "Prerequisites scattered instead of upfront"
        })

    # 4. Check links (using Read tool)
    links = extract_links(content)
    for link in links:
        if is_internal(link):
            # Use Read tool to verify
            target_path = resolve_link(link, repository_folder)
            if not file_exists(target_path):
                broken_links.append({
                    "url": link.url,
                    "line": link.line,
                    "error": "File not found"
                })
        elif is_external(link):
            # Check HTTP status
            status = check_url(link.url)
            if status >= 400:
                broken_links.append({
                    "url": link.url,
                    "line": link.line,
                    "error": f"{status} Error"
                })

    # 5. Correlate with validation results
    if code_validation:
        failed_examples = [e for e in code_validation["results"] if e["status"] == "failure"]
        for example in failed_examples:
            # Check if clarity issue contributed to failure
            if has_unclear_instructions(content, example["line"]):
                clarity_issues.append({
                    "type": "unclear_explanation",
                    "severity": "warning",
                    "line": example["line"],
                    "message": "Unclear instructions contributed to execution failure",
                    "context": example["error_message"]
                })

    return {
        "clarity_issues": clarity_issues,
        "structural_issues": structural_issues,
        "technical_accessibility": {
            "broken_links": broken_links,
            ...
        }
    }


# MCP Server (deterministic scoring)
def calculate_clarity_score(issues, metrics):
    """Calculate score from issues and metrics."""

    base_score = 10.0

    # Penalties based on issue severity
    critical_penalty = len([i for i in issues if i["severity"] == "critical"]) * 1.5
    warning_penalty = len([i for i in issues if i["severity"] == "warning"]) * 0.5
    info_penalty = len([i for i in issues if i["severity"] == "info"]) * 0.2

    # Penalties from validation metrics
    failed_examples_penalty = metrics["failed_examples"] * 0.3
    invalid_api_penalty = metrics["invalid_apis"] * 0.4

    final_score = base_score - (
        critical_penalty +
        warning_penalty +
        info_penalty +
        failed_examples_penalty +
        invalid_api_penalty
    )

    final_score = max(0.0, min(10.0, final_score))

    # Calculate dimension scores
    instruction_clarity = calculate_dimension_score(issues, "instruction_clarity", metrics)
    logical_flow = calculate_dimension_score(issues, "logical_flow", metrics)
    completeness = calculate_dimension_score(issues, "completeness", metrics)
    consistency = calculate_dimension_score(issues, "consistency", metrics)
    prerequisite_coverage = calculate_dimension_score(issues, "prerequisite_coverage", metrics)

    # Determine tier
    tier = get_tier(final_score)

    return {
        "clarity_score": {
            "overall_score": round(final_score, 1),
            "tier": tier,
            "instruction_clarity": instruction_clarity,
            "logical_flow": logical_flow,
            "completeness": completeness,
            "consistency": consistency,
            "prerequisite_coverage": prerequisite_coverage
        },
        "breakdown": {
            "base_score": base_score,
            "critical_issues_penalty": critical_penalty,
            "warning_issues_penalty": warning_penalty,
            "info_issues_penalty": info_penalty,
            "failed_examples_penalty": failed_examples_penalty,
            "invalid_api_penalty": invalid_api_penalty,
            "final_score": final_score
        }
    }


def get_tier(score):
    """Map score to tier."""
    if score >= 9.5: return "S"
    elif score >= 8.5: return "A"
    elif score >= 7.0: return "B"
    elif score >= 5.0: return "C"
    elif score >= 3.0: return "D"
    else: return "F"
```

## Key Features

### 1. **Single-Agent Architecture with MCP Tools**

The clarity agent uses a single Claude agent session that calls MCP tools:

**Phase 1 (Claude - Issue Finding)**:
- Reads documentation as a user would
- Identifies gaps, unclear steps, broken links using Read tool
- Outputs: clarity_issues, structural_issues, technical_accessibility

**Phase 2 (Claude calls MCP - Scoring)**:
- Agent calls `calculate_clarity_score(issues, metrics)` → Returns overall score, tier, dimension scores
- Agent calls `get_improvement_roadmap(issues, metrics, score)` → Returns prioritized fixes with impact/effort
- Agent calls `explain_score(score, breakdown, issues, metrics)` → Returns human-readable explanation

**Single Response**:
Agent returns complete JSON with both issue analysis AND all MCP scoring results in one response.

**Why this architecture?**
- **Efficient**: One agent session instead of 4 separate sessions (old pattern)
- **Correct MCP usage**: Agent calls MCP tools naturally, not Python orchestrating separate agents
- **Deterministic scoring**: MCP server ensures reproducible scores
- **Transparent**: Clear separation between qualitative analysis (agent) and quantitative scoring (MCP)

**Tier Constraint**: Critical issues or failed examples automatically cap score at 7.9 (max Tier B), preventing "Excellent" ratings for fundamentally flawed documentation.

### 2. **Snippet Pre-processing (Level 2 - Fast Path)**

Resolves MkDocs Material snippets before sending to Claude:

```python
# Before
--8<-- "python/tests/test_file.py:example"

# After (resolved and dedented)
import lancedb
db = lancedb.connect("./data")
```

Reduces agent tool calls by ~50%.

### 3. **Variable Scope Analysis**

Distinguishes between:
- **Undefined variables** (critical): Never defined anywhere
- **Cross-section references** (info): Defined earlier, but in different section

### 4. **Validation Result Correlation**

Integrates with previous agents:

```python
# If code example failed AND has unclear instructions
if example_failed and unclear_instructions_at_same_line:
    clarity_issues.append({
        "type": "unclear_explanation",
        "message": "Unclear instructions + execution failure (double problem)"
    })
```

### 5. **Language-Aware Evaluation**

Adapts analysis to the target language:

**Python:**
- Verifies `import` statements (not `require`)
- Checks for `async`/`await` patterns
- Validates type hints if present

**JavaScript/TypeScript:**
- Verifies `require()`/`import` statements
- Checks for promises, `.then()` chains, `async`/`await`
- Validates JSDoc annotations (TypeScript)

**Common:**
- Code blocks should specify language (```python, ```javascript, ```typescript, ```js, ```ts)
- Installation commands should match ecosystem (`pip install` vs `npm install`)

### 6. **Improvement Roadmap with Impact/Effort**

Prioritizes fixes by:
- **Impact** (high/medium/low): How much it improves score
- **Effort** (low/medium/high): How hard to fix
- **Quick wins**: High impact + low effort

## Logging & Debugging

### Per-Document Logs
```
validation_log_dir/clarity_logs/{doc_name}/
├── agent.log           # Human-readable log
├── tools.jsonl         # Read tool calls
├── messages.jsonl      # Full Claude conversation
└── mcp/
    ├── mcp_agent.log   # MCP server interactions
    └── mcp_tools.jsonl # MCP tool calls
```

## Performance

- **Parallel workers**: Default 5
- **Typical throughput**:
  - ~7 documents in ~3 minutes
  - ~25-30 seconds per document
- **Bottlenecks**: Claude analysis time, MCP server calls

## Related Documentation

- **Schemas**: `stackbench/schemas.py` - `ClarityValidationOutput`, `ClarityScore`, `ImprovementRoadmap`
- **MCP Server**: `stackbench/mcp_servers/clarity_scoring_server.py`
- **Helpers**: `stackbench/agents/clarity_helpers.py`

## See Also

- [Extraction Agent](./extraction-agent.md) - Provides location metadata
- [API Validation Agent](./api-signature-validation-agent.md) - Results used for correlation
- [Code Validation Agent](./code-example-validation-agent.md) - Results used for correlation
