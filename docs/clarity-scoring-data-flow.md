# Clarity Scoring MCP Server - Data Flow

**Related:** `clarity-scoring-mcp-design.md`

This document clarifies **where the scoring metrics come from** in the Stackbench pipeline.

---

## Overview

The MCP scoring server receives metrics from **four pipeline stages**:
1. **Extraction Agent** - Extracts API signatures and code examples from markdown
2. **API Validation Agent** - Validates documented APIs against actual library
3. **Code Validation Agent** - Executes code examples to verify they work
4. **Clarity Agent** - Evaluates documentation quality and user experience

### Full Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│           1. EXTRACTION AGENT (runs first)                  │
│  Reads: Markdown documentation                              │
│  Output: data/<run_id>/results/extraction/<doc>_analysis.json │
│  Extracts:                                                  │
│    • API signatures (function names, params, types)         │
│    • Code examples (executable snippets)                    │
│    • Metadata (library, version, language)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────────────┐    ┌──────────────────────────┐
│  2. API VALIDATION       │    │  3. CODE VALIDATION      │
│     AGENT                │    │     AGENT                │
│                          │    │                          │
│  Validates signatures    │    │  Executes code examples  │
│  against actual library  │    │  in isolated env         │
│                          │    │                          │
│  Output:                 │    │  Output:                 │
│  api_validation/         │    │  code_validation/        │
│  <doc>_analysis_         │    │  <doc>_validation.json   │
│  validation.json         │    │                          │
│                          │    │  Results:                │
│  Results:                │    │  • successful: 8         │
│  • valid: 12             │    │  • failed: 2             │
│  • invalid: 2            │    │  • skipped: 0            │
│  • not_found: 1          │    │  • Error details         │
│  • accuracy: 0.8         │    │                          │
└──────────────────────────┘    └──────────────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           4. CLARITY AGENT (runs last)                      │
│  Phase 1: Load validation results + markdown               │
│  Phase 2: Detect issues (qualitative analysis)             │
│    • clarity_issues (logical gaps, unclear instructions)    │
│    • structural_issues (missing sections, poor flow)        │
│    • technical_accessibility (broken links, alt text)       │
│  Phase 3: Call MCP server (quantitative scoring)           │
│    Passes:                                                  │
│    - Issue counts (from Phase 2)                            │
│    - Code metrics (from code validation)                    │
│    - API metrics (from API validation)                      │
│    - Accessibility metrics (from Phase 2)                   │
│                                                             │
│  Output: clarity_validation/<doc>_clarity.json             │
│    • Issues detected (agent)                                │
│    • Scores calculated (MCP server)                         │
│    • Improvement roadmap (MCP server)                       │
│    • Score explanation (MCP server)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           CLARITY SCORING MCP SERVER                        │
│  Input: Validation results + issue counts                  │
│  Processing:                                                │
│    • Apply scoring formula                                  │
│    • Calculate dimension scores                             │
│    • Generate improvement roadmap                           │
│    • Explain calculation                                    │
│  Output: Deterministic scores + actionable guidance        │
└─────────────────────────────────────────────────────────────┘
```

### Key Insight

The clarity agent acts as the **orchestrator** in the final stage:
- **Loads** results from API and code validation agents
- **Detects** clarity issues using LLM reasoning (qualitative)
- **Delegates** score calculation to MCP server (quantitative)
- **Combines** all results into comprehensive output

This separation ensures:
- ✅ **Qualitative analysis** (issue detection) uses LLM strengths
- ✅ **Quantitative calculation** (scoring) uses deterministic formulas
- ✅ **Validation data** (actual execution) informs quality scores

---

## Data Sources

### Source 1: Code Validation Results

**File Location:** `data/<run_id>/results/code_validation/<doc>_validation.json`

**Example:** `pydantic_validation.json`

```json
{
  "page": "pydantic.md",
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",
  "validation_timestamp": "2025-10-23T12:44:55.266032",
  "results": [
    {
      "example_index": 0,
      "line": 8,
      "context": "Complete example of using LanceDB with Pydantic...",
      "code": "import lancedb\nfrom lancedb.pydantic import Vector...",
      "status": "success",       // ← Used for scoring! (success/failed/skipped)
      "error_message": null,
      "execution_output": "",
      ...
    }
  ],
  "total_examples": 1,          // ← Used for scoring
  "successful": 1,              // ← Used for scoring
  "failed": 0,                  // ← Used for scoring
  "skipped": 0
}
```

**Metrics Extracted:**
- `total_code_blocks` = `total_examples` (1)
- `executable_examples` = `successful` (1) ← **Validated successfully!**
- `failed_examples` = `failed` (0)
- `skipped_examples` = `skipped` (0)

---

### Source 2: API Signature Validation Results

**File Location:** `data/<run_id>/results/api_validation/<doc>_analysis_validation.json`

**Example:** `pydantic_analysis_validation.json`

```json
{
  "validation_id": "700d9036-2897-446b-9a03-d75f65e54df2",
  "validated_at": "2025-10-23T12:44:46.263185",
  "source_file": "pydantic_analysis.json",
  "document_page": "pydantic.md",
  "library": "lancedb",
  "version": "0.25.2",
  "language": "python",
  "summary": {
    "total_signatures": 8,      // ← Used for scoring
    "valid": 8,                 // ← Used for scoring
    "invalid": 0,               // ← Used for scoring
    "not_found": 0,             // ← Used for scoring
    "error": 0,
    "accuracy_score": 1.0,
    "critical_issues": 0,       // ← Used for scoring
    "warnings": 0
  },
  "validations": [
    {
      "signature_id": "lancedb.pydantic.Vector",
      "function": "Vector",
      "status": "valid",        // ← valid/invalid/not_found/error
      "issues": [
        {
          "type": "missing_param_in_docs",
          "severity": "info",
          "message": "Documented signature missing optional parameter 'dim_name'",
          ...
        }
      ],
      ...
    }
  ],
  ...
}
```

**Metrics Extracted:**
- `total_api_signatures` = `summary.total_signatures` (8)
- `valid_api_signatures` = `summary.valid` (8)
- `invalid_api_signatures` = `summary.invalid` (0)
- `missing_api_signatures` = `summary.not_found` (0)
- `api_accuracy_score` = `summary.accuracy_score` (1.0)

---

### Source 3: Clarity Agent Issue Detection

**File Location:** `data/<run_id>/results/clarity_validation/<doc>_clarity.json`

**Example:** `pydantic_clarity.json`

```json
{
  "clarity_issues": [
    {
      "type": "syntax_error",
      "severity": "critical",    // ← Used for scoring
      "line": 14,
      "section": "Introduction/First Example",
      "message": "Inconsistent indentation...",
      "suggested_fix": "Remove the extra indentation...",
      ...
    },
    {
      "type": "missing_explanation",
      "severity": "critical",    // ← Used for scoring
      "line": 8,
      ...
    },
    {
      "type": "incomplete_explanation",
      "severity": "warning",     // ← Used for scoring
      "line": 29,
      ...
    }
  ],
  "structural_issues": [
    {
      "type": "missing_prerequisites",
      "severity": "warning",     // ← Used for scoring
      "location": "Document beginning...",
      ...
    }
  ],
  "technical_accessibility": {
    "broken_links": [],          // ← Used for scoring (length)
    "missing_alt_text": [],      // ← Used for scoring (length)
    "code_blocks_without_language": [],
    "total_links_checked": 5,
    "total_images_checked": 0,
    "total_code_blocks_checked": 1,  // ← Alternative source for total_code_blocks
    "all_validated": true
  }
}
```

**Metrics Extracted:**
- `critical_issues` = count where `severity == "critical"` in `clarity_issues` + `structural_issues`
- `warning_issues` = count where `severity == "warning"` in `clarity_issues` + `structural_issues`
- `info_issues` = count where `severity == "info"` in `clarity_issues` + `structural_issues`
- `broken_links` = `len(technical_accessibility.broken_links)`
- `missing_alt_text` = `len(technical_accessibility.missing_alt_text)`

---

## Updated Clarity Agent Workflow

### Current Implementation

```python
async def analyze_document(self, extraction_file: Path) -> Optional[ClarityValidationOutput]:
    """Analyze clarity and structure of a single document."""

    # 1. Load extraction data
    with open(extraction_file, 'r') as f:
        extraction_data = json.load(f)

    # 2. Read markdown content
    markdown_path = self.repository_folder / extraction_data["page"]
    with open(markdown_path, 'r') as f:
        content = f.read()

    # 3. Agent analyzes and detects issues
    async with ClaudeSDKClient(options=options) as client:
        prompt = create_clarity_validation_prompt(...)
        response_text = await self.get_claude_response(client, prompt, logger, messages_log_file)
        clarity_data = self.extract_json_from_response(response_text)

    # 4. Construct output
    analysis = ClarityValidationOutput(
        clarity_issues=[...],
        structural_issues=[...],
        technical_accessibility=TechnicalAccessibility(...),
        ...
    )

    return analysis
```

### Proposed Implementation (With MCP Scoring)

```python
async def analyze_document(self, extraction_file: Path) -> Optional[ClarityValidationOutput]:
    """Analyze clarity using MCP server for deterministic scoring."""

    # ===== PHASE 1: Load Existing Data =====

    # Load extraction results
    with open(extraction_file, 'r') as f:
        extraction_data = json.load(f)

    # Extract content metrics from extraction data
    total_code_blocks = extraction_data.get("total_examples", 0)
    executable_examples = sum(
        1 for ex in extraction_data.get("examples", [])
        if ex.get("is_executable", False)
    )

    # Read markdown
    markdown_path = self.repository_folder / extraction_data["page"]
    with open(markdown_path, 'r') as f:
        content = f.read()

    # ===== PHASE 2: Issue Detection (Agent) =====

    async with ClaudeSDKClient(options=options) as client:
        # Agent finds issues (qualitative analysis)
        issue_detection_prompt = create_clarity_validation_prompt(...)
        response_text = await self.get_claude_response(client, prompt, logger, messages_log_file)
        issues_data = self.extract_json_from_response(response_text)

        # Count issues by severity
        clarity_issues = issues_data.get('clarity_issues', [])
        structural_issues = issues_data.get('structural_issues', [])
        tech_access = issues_data.get('technical_accessibility', {})

        critical_count = sum(
            1 for i in clarity_issues + structural_issues
            if i.get('severity') == 'critical'
        )
        warning_count = sum(
            1 for i in clarity_issues + structural_issues
            if i.get('severity') == 'warning'
        )
        info_count = sum(
            1 for i in clarity_issues + structural_issues
            if i.get('severity') == 'info'
        )

        broken_links_count = len(tech_access.get('broken_links', []))
        missing_alt_text_count = len(tech_access.get('missing_alt_text', []))

        # ===== PHASE 3: Score Calculation (MCP Server) =====

        # Agent calls MCP server with metrics
        scoring_prompt = f"""
I've analyzed the documentation and found:
- Critical issues: {critical_count}
- Warning issues: {warning_count}
- Info issues: {info_count}
- Total code blocks: {total_code_blocks}
- Executable examples: {executable_examples}
- Broken links: {broken_links_count}
- Missing alt text: {missing_alt_text_count}

Use the clarity-scoring MCP server:

1. Call `calculate_clarity_score` with these metrics
2. Call `calculate_dimension_score` for each dimension
3. Call `get_improvement_roadmap` (current score, target 8.0)
4. Call `explain_score`

Return the complete scoring data as JSON.
"""

        scoring_response = await self.get_claude_response(client, scoring_prompt, logger, messages_log_file)
        scoring_data = self.extract_json_from_response(scoring_response)

        # ===== PHASE 4: Combine Results =====

        analysis = ClarityValidationOutput(
            # Issues from agent (Phase 2)
            clarity_issues=[ClarityIssue(**i) for i in clarity_issues],
            structural_issues=[StructuralIssue(**i) for i in structural_issues],
            technical_accessibility=TechnicalAccessibility(**tech_access),

            # Scores from MCP server (Phase 3)
            clarity_score=ClarityScore(**scoring_data['clarity_score']),
            improvement_roadmap=ImprovementRoadmap(**scoring_data['improvement_roadmap']),
            score_explanation=ScoreExplanation(**scoring_data['score_explanation']),

            ...
        )

        return analysis
```

---

## MCP Server Input Example

When the clarity agent calls `calculate_clarity_score`, it sends:

```json
{
  "tool": "calculate_clarity_score",
  "arguments": {
    // Clarity agent's issue detection
    "critical_issues": 2,
    "warning_issues": 3,
    "info_issues": 1,

    // Code validation results (actually executed!)
    "total_code_blocks": 1,          // From code_validation.total_examples
    "successful_examples": 1,         // From code_validation.successful ✅
    "failed_examples": 0,            // From code_validation.failed

    // API validation results (actually validated!)
    "total_api_signatures": 8,       // From api_validation.summary.total_signatures
    "valid_api_signatures": 8,       // From api_validation.summary.valid ✅
    "invalid_api_signatures": 0,     // From api_validation.summary.invalid
    "missing_api_signatures": 0,     // From api_validation.summary.not_found
    "api_accuracy_score": 1.0,       // From api_validation.summary.accuracy_score

    // Technical accessibility (clarity agent)
    "broken_links": 0,               // From clarity agent's tech_access analysis
    "missing_alt_text": 0            // From clarity agent's tech_access analysis
  }
}
```

---

## MCP Server Output Example

The MCP server responds with:

```json
{
  "overall_score": 6.5,
  "grade": "B",
  "rubric_tier": "6.0-7.9",
  "rubric_description": "Good - Clear Improvements Needed",
  "calculation_breakdown": {
    "starting_score": 10.0,
    "total_penalty": 3.5,
    "penalties": [
      {
        "type": "critical_issues",
        "count": 2,
        "penalty": 4.0,
        "explanation": "2 critical issues × 2.0 points each"
      },
      {
        "type": "warning_issues",
        "count": 3,
        "penalty": 1.5,
        "explanation": "3 warnings × 0.5 points each"
      },
      {
        "type": "info_issues",
        "count": 1,
        "penalty": 0.1,
        "explanation": "1 info issue × 0.1 points each"
      }
    ]
  },
  "quality_rating": "good",
  "meets_criteria": true
}
```

---

## Data Availability

### ✅ Already Available

These metrics are **already computed** by existing agents:

1. **total_code_blocks** - Extraction agent counts all code examples
2. **executable_examples** - Extraction agent marks `is_executable` flag
3. **broken_links** - Clarity agent already checks links (in `technical_accessibility`)
4. **missing_alt_text** - Clarity agent already checks images (in `technical_accessibility`)
5. **issue counts** - Clarity agent already categorizes by severity

### 🆕 New Requirement (Minor)

The only new requirement is **counting executable examples**:

```python
# Add this helper to clarity_agent.py
def get_content_metrics(extraction_data: Dict[str, Any]) -> Dict[str, int]:
    """Extract content quality metrics from extraction data."""
    examples = extraction_data.get("examples", [])

    return {
        "total_code_blocks": len(examples),
        "executable_examples": sum(1 for ex in examples if ex.get("is_executable", False)),
        "total_sections": extraction_data.get("total_sections", 0)  # Could add this to extraction agent
    }
```

This is trivial to implement since all data is already in `extraction_data`.

---

## Alternative: Let Agent Count

Instead of pre-computing, we could let the **agent count** from the markdown:

```python
scoring_prompt = f"""
Based on your analysis of the markdown:
- How many code blocks did you find?
- How many are complete executable examples (vs snippets)?

Then call the MCP scoring server with these metrics along with the {critical_count} critical issues, {warning_count} warnings, etc.
"""
```

**Pros:**
- No changes to extraction agent
- Agent has already read the markdown

**Cons:**
- Less reliable (agent might miscount)
- Inconsistent with extraction agent's count
- Wastes agent context analyzing what extraction already did

**Recommendation:** Use extraction data (more deterministic).

---

## Summary

| Metric | Source | Location | Availability |
|--------|--------|----------|--------------|
| `total_code_blocks` | Code Validation | `total_examples` field | ✅ Already available |
| `successful_examples` | Code Validation | `successful` field | ✅ Already available |
| `failed_examples` | Code Validation | `failed` field | ✅ Already available |
| `total_api_signatures` | API Validation | `summary.total_signatures` | ✅ Already available |
| `valid_api_signatures` | API Validation | `summary.valid` | ✅ Already available |
| `invalid_api_signatures` | API Validation | `summary.invalid` | ✅ Already available |
| `missing_api_signatures` | API Validation | `summary.not_found` | ✅ Already available |
| `api_accuracy_score` | API Validation | `summary.accuracy_score` | ✅ Already available |
| `critical_issues` | Clarity Agent | Count `severity="critical"` | ✅ Already available |
| `warning_issues` | Clarity Agent | Count `severity="warning"` | ✅ Already available |
| `info_issues` | Clarity Agent | Count `severity="info"` | ✅ Already available |
| `broken_links` | Clarity Agent | `len(technical_accessibility.broken_links)` | ✅ Already available |
| `missing_alt_text` | Clarity Agent | `len(technical_accessibility.missing_alt_text)` | ✅ Already available |

**Key Insight:** We should use **validation results** (actual execution) not extraction metadata (heuristics).

**No major changes needed!** All required metrics are already in the pipeline. We just need to **load validation results and pass them** to the MCP server.

---

## Code Changes Required

### 1. Helper Function (clarity_agent.py)

```python
def get_content_metrics_from_validation(
    doc_stem: str,
    validation_folder: Path
) -> Dict[str, Any]:
    """
    Extract content quality metrics from code and API validation results.

    Args:
        doc_stem: Document stem (e.g., 'pydantic' from 'pydantic_analysis.json')
        validation_folder: Path to validation results parent folder

    Returns:
        Dictionary with content metrics for MCP scoring
    """
    metrics = {
        # Code validation metrics
        "total_code_blocks": 0,
        "successful_examples": 0,
        "failed_examples": 0,
        "skipped_examples": 0,

        # API validation metrics
        "total_api_signatures": 0,
        "valid_api_signatures": 0,
        "invalid_api_signatures": 0,
        "missing_api_signatures": 0,
        "api_accuracy_score": 0.0
    }

    # Load code validation results
    code_validation_file = validation_folder / "code_validation" / f"{doc_stem}_validation.json"
    if code_validation_file.exists():
        try:
            with open(code_validation_file, 'r') as f:
                code_data = json.load(f)

            metrics["total_code_blocks"] = code_data.get("total_examples", 0)
            metrics["successful_examples"] = code_data.get("successful", 0)
            metrics["failed_examples"] = code_data.get("failed", 0)
            metrics["skipped_examples"] = code_data.get("skipped", 0)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load code validation: {e}[/yellow]")

    # Load API validation results
    api_validation_file = validation_folder / "api_validation" / f"{doc_stem}_analysis_validation.json"
    if api_validation_file.exists():
        try:
            with open(api_validation_file, 'r') as f:
                api_data = json.load(f)

            summary = api_data.get("summary", {})
            metrics["total_api_signatures"] = summary.get("total_signatures", 0)
            metrics["valid_api_signatures"] = summary.get("valid", 0)
            metrics["invalid_api_signatures"] = summary.get("invalid", 0)
            metrics["missing_api_signatures"] = summary.get("not_found", 0)
            metrics["api_accuracy_score"] = summary.get("accuracy_score", 0.0)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load API validation: {e}[/yellow]")

    return metrics
```

### 2. Updated analyze_document() Method

```python
async def analyze_document(self, extraction_file: Path) -> Optional[ClarityValidationOutput]:
    """Analyze clarity using MCP server for deterministic scoring."""

    # Get document stem for validation lookup
    doc_stem = extraction_file.stem.replace('_analysis', '')

    # Get content metrics from validation results
    validation_folder = self.output_folder.parent  # Go up from clarity_validation/ to results/
    content_metrics = get_content_metrics_from_validation(doc_stem, validation_folder)

    # ... rest of existing code ...

    # After agent detects issues, call MCP server
    scoring_prompt = f"""
Use the clarity-scoring MCP server to calculate scores:

Call `calculate_clarity_score` with:
- critical_issues: {critical_count}
- warning_issues: {warning_count}
- info_issues: {info_count}
- total_code_blocks: {content_metrics['total_code_blocks']}
- successful_examples: {content_metrics['successful_examples']}
- failed_examples: {content_metrics['failed_examples']}
- total_api_signatures: {content_metrics['total_api_signatures']}
- valid_api_signatures: {content_metrics['valid_api_signatures']}
- invalid_api_signatures: {content_metrics['invalid_api_signatures']}
- missing_api_signatures: {content_metrics['missing_api_signatures']}
- api_accuracy_score: {content_metrics['api_accuracy_score']}
- broken_links: {len(tech_access.get('broken_links', []))}
- missing_alt_text: {len(tech_access.get('missing_alt_text', []))}
"""

    # ... rest of scoring logic ...
```

**Key Changes:**
1. Load from **validation results** (code_validation + api_validation) not extraction
2. Use **successful/failed counts** from actual execution
3. Include **API validation metrics** (accuracy, invalid signatures, missing APIs)
4. More comprehensive quality assessment
