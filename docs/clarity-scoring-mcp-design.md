# Clarity Scoring MCP Server - Design Document

**Status:** Proposed
**Author:** System Design
**Date:** 2025-10-23
**Related:** `stackbench/agents/clarity_agent.py`, `stackbench/walkthroughs/mcp_server.py`

---

## Executive Summary

This document proposes a **Model Context Protocol (MCP) server** for deterministic documentation clarity scoring. The MCP server separates **issue detection** (agent's strength) from **score calculation** (programmatic logic), ensuring consistent, transparent, and explainable quality metrics.

**Key Benefits:**
- ✅ Deterministic scoring (same issues = same score, every time)
- ✅ Transparent formulas (doc owners see exact calculations)
- ✅ Easy to test and iterate (pure functions, no LLM variability)
- ✅ Actionable improvement roadmaps (automated priority ranking)
- ✅ Follows Stackbench patterns (proven with walkthrough MCP server)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current System Analysis](#current-system-analysis)
3. [Proposed Solution](#proposed-solution)
4. [Architecture](#architecture)
5. [Scoring Rubric](#scoring-rubric)
6. [MCP Server API](#mcp-server-api)
7. [Integration with Clarity Agent](#integration-with-clarity-agent)
8. [Implementation Plan](#implementation-plan)
9. [Testing Strategy](#testing-strategy)
10. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### Issues with Current Clarity Scoring

After analyzing clarity validation results from LanceDB documentation (`data/5bd8e375-313e-4328-827b-33889356828c/results/clarity_validation/`), we identified several problems:

#### 1. **Vague Scoring Definitions**
Current rubric (lines 129-136 in `clarity_agent.py`):
```
- 10.0: Perfect clarity, could not be improved
- 8.0-9.0: Excellent, only minor polish needed
- 6.0-7.0: Good, some clear improvements needed
- 4.0-5.0: Acceptable, multiple issues to address
- 2.0-3.0: Poor, significant problems blocking understanding
- 0.0-1.0: Unusable, cannot be followed
```

**Problems:**
- What does "minor polish" mean exactly?
- How many issues = "multiple issues"?
- No concrete criteria for each tier
- Hard to compare scores across documents

#### 2. **Inconsistent Score Application**

Examining actual results:

| Document | Score | Critical Issues | Warning Issues | Notes |
|----------|-------|----------------|----------------|-------|
| `python_clarity.json` | 5.5/10 | 3 | 5 | 8 clarity + 4 structural issues |
| `pydantic_clarity.json` | 6.8/10 | 2 | 3 | Has critical syntax error |
| `saas-python_clarity.json` | 4.5/10 | 4 | 3 | Sparse but fewer warnings |

**Observation:** Scores don't correlate consistently with issue counts/severity. `pydantic_clarity.json` scored higher despite having a critical syntax error.

#### 3. **Generic evaluation_criteria**

All documents return identical `evaluation_criteria` text:
```json
{
  "evaluation_criteria": {
    "instruction_clarity": "Measured by: clarity of commands, completeness of examples, explanation of outcomes",
    "logical_flow": "Measured by: whether steps build on each other, absence of gaps, proper sequencing",
    ...
  }
}
```

**Problem:** These should explain **why this specific document** got its scores, not generic definitions.

#### 4. **No Actionable Improvement Roadmap**

Doc owners see:
- Overall score: 5.5/10
- 8 clarity issues
- 4 structural issues

But **don't know:**
- Which 3 issues to fix to reach 7.0/10?
- What's the estimated effort?
- Which are "quick wins" (high impact, low effort)?

#### 5. **LLM Variability**

Agent interprets the rubric subjectively. Same issues might get different scores across runs due to:
- Model temperature
- Prompt interpretation differences
- Inconsistent application of scoring guidelines

---

## Current System Analysis

### How Clarity Agent Works Today

```
┌─────────────────────────────────────────────────────────────┐
│                    CLARITY AGENT                            │
│  1. Read markdown + extraction metadata                    │
│  2. Analyze for clarity issues (LLM reasoning)             │
│  3. Score on 5 dimensions (LLM judgment)                   │
│  4. Calculate overall score (LLM judgment)                 │
│  5. Generate issues list (LLM output)                      │
│  6. Write JSON output                                      │
└─────────────────────────────────────────────────────────────┘
```

**Agent does EVERYTHING** - both qualitative (finding issues) and quantitative (calculating scores).

### Strengths of Current Approach

1. **Detailed Issue Detection** - Agent excels at finding unclear instructions, logical gaps, missing context
2. **Contextual Understanding** - Can interpret documentation conventions (MkDocs snippets, etc.)
3. **Actionable Suggestions** - Provides specific line numbers and suggested fixes
4. **Multi-dimensional Analysis** - Evaluates 5 separate aspects of clarity

### Weaknesses

1. **Subjective Scoring** - Same issues can get different scores
2. **Hard to Validate** - Can't easily test scoring logic
3. **Opaque to Users** - Doc owners don't see how scores are calculated
4. **No Roadmap** - Missing prioritization guidance
5. **Difficult to Tune** - Changing rubric requires prompt engineering

---

## Proposed Solution

### Core Principle: Separation of Concerns

**Agent does:** Qualitative analysis (finding issues)
**MCP Server does:** Quantitative calculation (computing scores)

```
┌─────────────────────────────────────────────────────────────┐
│                    CLARITY AGENT                            │
│  • Reads documentation                                      │
│  • Identifies clarity issues                                │
│  • Categorizes severity (critical/warning/info)             │
│  • Provides context and suggested fixes                     │
└─────────────────────────────────────────────────────────────┘
                            ↓ (issues list)
┌─────────────────────────────────────────────────────────────┐
│              CLARITY SCORING MCP SERVER                     │
│  • Receives issue counts and content metrics               │
│  • Applies deterministic scoring formula                    │
│  • Calculates overall + dimension scores                    │
│  • Generates improvement roadmap                            │
│  • Explains score calculation                               │
└─────────────────────────────────────────────────────────────┘
                            ↓ (scores + roadmap)
┌─────────────────────────────────────────────────────────────┐
│                  CLARITY VALIDATION OUTPUT                  │
│  • Agent-detected issues (qualitative)                      │
│  • MCP-calculated scores (quantitative)                     │
│  • Improvement roadmap (actionable)                         │
│  • Score explanation (transparent)                          │
└─────────────────────────────────────────────────────────────┘
```

### Why MCP Server?

1. **Deterministic** - Pure functions, no LLM variability
2. **Testable** - Unit test scoring formulas independently
3. **Transparent** - Users see exact formula: `10.0 - (3 × 2.0) - (5 × 0.5) = 3.5`
4. **Versionable** - Track rubric changes in git
5. **Tunable** - Modify weights without changing agent prompts
6. **Proven Pattern** - Walkthrough validation already uses MCP server successfully

---

## Architecture

### System Components

```
stackbench/
├── agents/
│   └── clarity_agent.py          # Issue detection (unchanged logic)
├── mcp_servers/                   # NEW: MCP servers directory
│   ├── __init__.py
│   ├── clarity_scoring_server.py # NEW: Scoring MCP server
│   └── clarity_scoring/           # NEW: Scoring logic module
│       ├── __init__.py
│       ├── rubric.py             # Scoring rubric definition
│       ├── calculator.py         # Score calculation logic
│       ├── roadmap.py            # Improvement roadmap generation
│       └── explainer.py          # Score explanation generation
├── schemas.py                     # Updated with new fields
└── hooks/
    └── validation.py              # Updated schemas

docs/
└── clarity-scoring-mcp-design.md  # This document
```

### Data Flow

```python
# Phase 1: Agent identifies issues
agent_output = {
    "clarity_issues": [
        {"type": "logical_gap", "severity": "critical", "line": 45, ...},
        {"type": "unclear_explanation", "severity": "warning", "line": 67, ...},
        ...
    ],
    "structural_issues": [...],
    "technical_accessibility": {
        "broken_links": [...],
        "missing_alt_text": [...],
        ...
    }
}

# Phase 2: Agent calls MCP server
mcp_request = {
    "tool": "calculate_clarity_score",
    "arguments": {
        "critical_issues": 3,
        "warning_issues": 5,
        "info_issues": 1,
        "total_code_blocks": 12,
        "executable_examples": 8,
        "broken_links": 2,
        "missing_alt_text": 0
    }
}

# Phase 3: MCP server responds with scores
mcp_response = {
    "overall_score": 5.5,
    "grade": "C",
    "rubric_tier": "4.0-5.9",
    "calculation_breakdown": {
        "starting_score": 10.0,
        "total_penalty": 4.5,
        "penalties": [
            {"type": "critical_issues", "count": 3, "penalty": 6.0},
            {"type": "warning_issues", "count": 5, "penalty": 2.5},
            ...
        ]
    },
    "quality_rating": "needs_improvement"
}

# Phase 4: Agent calls MCP for dimension scores
# (repeat for each dimension: instruction_clarity, logical_flow, etc.)

# Phase 5: Agent calls MCP for improvement roadmap
roadmap_request = {
    "tool": "get_improvement_roadmap",
    "arguments": {
        "current_score": 5.5,
        "target_score": 8.0,
        "issues": agent_output["clarity_issues"] + agent_output["structural_issues"]
    }
}

roadmap_response = {
    "current_score": 5.5,
    "target_score": 8.0,
    "estimated_new_score": 8.5,
    "priority_fixes": [
        {"rank": 1, "issue_type": "logical_gap", "impact": "+2.0 points", ...},
        {"rank": 2, "issue_type": "missing_examples", "impact": "+2.0 points", ...},
        ...
    ],
    "quick_wins": [
        "Add Prerequisites section (line 15) - 30 min, +2.0 impact",
        ...
    ]
}

# Phase 6: Combined output
final_output = {
    **agent_output,  # Issues from agent
    **mcp_response,  # Scores from MCP
    "improvement_roadmap": roadmap_response
}
```

---

## Scoring Rubric

### Rubric Definition

The MCP server implements a **tiered rubric** with concrete criteria:

```python
SCORING_RUBRIC = {
    "10.0": {
        "range": (10.0, 10.0),
        "grade": "A+",
        "description": "Perfect - Production Ready",
        "criteria": {
            "critical_issues": 0,
            "warning_issues": 0,
            "max_info_issues": 2
        },
        "characteristics": [
            "Complete working examples for all features",
            "Prerequisites clearly stated upfront",
            "Logical flow with no gaps",
            "Consistent terminology throughout",
            "All links and images validated"
        ]
    },
    "8.0-9.9": {
        "range": (8.0, 9.9),
        "grade": "A",
        "description": "Excellent - Minor Polish Needed",
        "criteria": {
            "critical_issues": 0,
            "max_warning_issues": 3
        },
        "characteristics": [
            "Core workflows clearly explained",
            "Examples are complete and executable",
            "Minor improvements needed (better navigation, edge cases)",
            "No blocking issues for users"
        ]
    },
    "6.0-7.9": {
        "range": (6.0, 7.9),
        "grade": "B",
        "description": "Good - Clear Improvements Needed",
        "criteria": {
            "max_critical_issues": 1,
            "max_warning_issues": 7
        },
        "characteristics": [
            "Basic workflows explained but gaps exist",
            "Some examples incomplete or unclear",
            "Users can follow with effort",
            "Noticeable room for improvement"
        ]
    },
    "4.0-5.9": {
        "range": (4.0, 5.9),
        "grade": "C",
        "description": "Acceptable - Multiple Issues",
        "criteria": {
            "max_critical_issues": 3,
            "min_warning_issues": 5
        },
        "characteristics": [
            "Significant gaps in flow or prerequisites",
            "Missing critical examples or context",
            "Users struggle without external help",
            "Requires substantial revision"
        ]
    },
    "2.0-3.9": {
        "range": (2.0, 3.9),
        "grade": "D",
        "description": "Poor - Blocks Understanding",
        "criteria": {
            "min_critical_issues": 4,
            "min_warning_issues": 8
        },
        "characteristics": [
            "Major workflow gaps or broken examples",
            "Missing prerequisites block progress",
            "Users cannot complete tasks",
            "Needs major rewrite"
        ]
    },
    "0.0-1.9": {
        "range": (0.0, 1.9),
        "grade": "F",
        "description": "Unusable - Cannot Be Followed",
        "criteria": {
            "min_critical_issues": 10
        },
        "characteristics": [
            "Entirely broken or stub content",
            "No working examples",
            "Unusable even for experts",
            "Complete rewrite required"
        ]
    }
}
```

### Scoring Formula

**Overall Score Calculation:**

```python
score = 10.0
score -= (critical_issues × 2.0)
score -= (warning_issues × 0.5)
score -= (info_issues × 0.1)

# Content penalties
if no_code_blocks:
    score -= 2.0
elif no_executable_examples:
    score -= 1.5

# Technical accessibility
score -= (broken_links × 0.3)
score -= (missing_alt_text × 0.1)

# Floor at 0.0
score = max(0.0, score)
```

**Dimension Score Calculation:**

Each dimension (instruction_clarity, logical_flow, etc.) is scored by counting issues **tagged for that dimension**:

```python
dimension_score = 10.0
dimension_score -= (critical_for_dimension × 2.0)
dimension_score -= (warnings_for_dimension × 0.5)
dimension_score -= (info_for_dimension × 0.1)
dimension_score = max(0.0, dimension_score)
```

### Penalty Weights

```python
WEIGHTS = {
    # Issue penalties
    "critical_issue": 2.0,            # Each critical = -2.0 points
    "warning_issue": 0.5,             # Each warning = -0.5 points
    "info_issue": 0.1,                # Each info = -0.1 points

    # Code quality penalties
    "failed_example": 1.0,            # Per failed code example = -1.0
    "no_code_blocks_penalty": 2.0,    # No code at all = -2.0
    "no_successful_examples": 1.5,    # No successful examples = -1.5

    # API accuracy penalties
    "invalid_api_signature": 0.8,     # Per invalid signature = -0.8
    "missing_api": 1.2,               # Per documented but missing API = -1.2
    "low_api_accuracy_penalty": 2.0,  # API accuracy < 0.7 = -2.0

    # Technical accessibility penalties
    "broken_link": 0.3,               # Per broken link = -0.3
    "missing_alt_text": 0.1           # Per missing alt = -0.1
}
```

**Rationale for Weights:**

- **Critical issues** (-2.0): Block user progress entirely (missing prerequisites, logical gaps)
- **Warnings** (-0.5): Cause confusion but workaroundable (inconsistent terminology)
- **Info** (-0.1): Nice-to-haves (better formatting, time estimates)
- **Failed examples** (-1.0): Code doesn't work - breaks user trust
- **Invalid API signatures** (-0.8): Wrong parameters/types documented
- **Missing APIs** (-1.2): User tries to call non-existent function
- **Low API accuracy** (-2.0): < 70% accuracy means docs are unreliable
- **Accessibility penalties**: Encourage best practices but don't dominate score

### Example Calculation

**Document:** `python_clarity.json`

**Inputs:**
- Critical issues: 3 (clarity) + 0 (structural) = 3
- Warning issues: 5 (clarity) + 4 (structural) = 9
- Info issues: 0
- Code blocks: 1
- Successful examples: 1
- Failed examples: 0
- Total API signatures: 0 (API reference page without extractable signatures)
- Valid API signatures: 0
- Invalid API signatures: 0
- Missing API signatures: 0
- Broken links: 0
- Missing alt text: 0

**Calculation:**
```
10.0
- (3 × 2.0) = -6.0     [critical penalty]
- (9 × 0.5) = -4.5     [warning penalty]
- 0                    [no info issues]
- 0                    [has 1 successful example]
- 0                    [no failed examples]
- 0                    [no API data to penalize]
- 0                    [no broken links]
= -0.5

Floor at 0.0 → 0.0
```

**Wait, this gives 0.0, but actual score was 5.5!**

This exposes the problem: **current scores don't follow a formula**. With the proposed MCP server, we'd either:
1. Accept the formula result (0.0 for 3 critical + 9 warning) - harsh but deterministic
2. Tune weights to match desired outcomes (critical = -1.0, warning = -0.3)
3. Add bonuses for positive qualities (e.g., +2.0 for having working examples)

This is exactly why we need **deterministic scoring** - to expose and fix inconsistencies. We can iterate on the formula based on feedback.

---

## MCP Server API

### Tool: `get_rubric`

**Description:** Get the complete scoring rubric with criteria.

**Input:** None

**Output:**
```json
{
  "10.0": {
    "range": [10.0, 10.0],
    "grade": "A+",
    "description": "Perfect - Production Ready",
    "criteria": {
      "critical_issues": 0,
      "warning_issues": 0,
      "max_info_issues": 2
    },
    "characteristics": ["...", "..."]
  },
  ...
}
```

**Use Case:** Agent can retrieve rubric to include in output for doc owners to see.

---

### Tool: `calculate_clarity_score`

**Description:** Calculate overall clarity score based on issue counts and content metrics.

**Input:**
```json
{
  // Clarity issues (from clarity agent)
  "critical_issues": 3,
  "warning_issues": 5,
  "info_issues": 1,

  // Code validation metrics (from code_validation agent)
  "total_code_blocks": 12,
  "successful_examples": 8,
  "failed_examples": 2,
  "skipped_examples": 2,

  // API validation metrics (from api_validation agent)
  "total_api_signatures": 15,
  "valid_api_signatures": 12,
  "invalid_api_signatures": 2,
  "missing_api_signatures": 1,
  "api_accuracy_score": 0.8,

  // Technical accessibility (from clarity agent)
  "broken_links": 2,
  "missing_alt_text": 0
}
```

**Output:**
```json
{
  "overall_score": 5.5,
  "grade": "C",
  "rubric_tier": "4.0-5.9",
  "rubric_description": "Acceptable - Multiple Issues",
  "calculation_breakdown": {
    "starting_score": 10.0,
    "total_penalty": 4.5,
    "penalties": [
      {
        "type": "critical_issues",
        "count": 3,
        "penalty": 6.0,
        "explanation": "3 critical issues × 2.0 points each"
      },
      {
        "type": "warning_issues",
        "count": 5,
        "penalty": 2.5,
        "explanation": "5 warnings × 0.5 points each"
      },
      {
        "type": "broken_links",
        "count": 2,
        "penalty": 0.6,
        "explanation": "2 broken links × 0.3 points each"
      }
    ]
  },
  "quality_rating": "needs_improvement",
  "meets_criteria": true
}
```

---

### Tool: `calculate_dimension_score`

**Description:** Calculate score for a specific clarity dimension.

**Input:**
```json
{
  "dimension": "logical_flow",
  "critical_issues_for_dimension": 2,
  "warning_issues_for_dimension": 3,
  "info_issues_for_dimension": 0
}
```

**Output:**
```json
{
  "dimension": "logical_flow",
  "score": 4.5,
  "calculation": "10.0 - (2 × 2.0) - (3 × 0.5) - (0 × 0.1) = 4.5"
}
```

**Implementation Note:** Agent must tag each issue with applicable dimension(s) during detection.

---

### Tool: `get_improvement_roadmap`

**Description:** Generate prioritized improvement roadmap to reach target score.

**Input:**
```json
{
  "current_score": 5.5,
  "target_score": 8.0,
  "issues": [
    {
      "type": "logical_gap",
      "severity": "critical",
      "line": 45,
      "section": "Configuration",
      "message": "Step 3 references config.yaml not created earlier"
    },
    {
      "type": "missing_examples",
      "severity": "critical",
      "line": 11,
      "section": "Connection",
      "message": "No concrete example of connecting to LanceDB Cloud"
    },
    ...
  ]
}
```

**Output:**
```json
{
  "current_score": 5.5,
  "target_score": 8.0,
  "estimated_new_score": 8.5,
  "total_fixes_needed": 4,
  "estimated_total_effort": "medium (2-6 hours)",
  "priority_fixes": [
    {
      "rank": 1,
      "issue_type": "logical_gap",
      "severity": "critical",
      "location": "Configuration (line 45)",
      "impact": "+2.0 points",
      "estimated_effort": "medium",
      "message": "Step 3 references config.yaml not created earlier"
    },
    {
      "rank": 2,
      "issue_type": "missing_examples",
      "severity": "critical",
      "location": "Connection (line 11)",
      "impact": "+2.0 points",
      "estimated_effort": "low",
      "message": "No concrete example of connecting to LanceDB Cloud"
    },
    ...
  ],
  "quick_wins": [
    "Add Prerequisites section (line 15) - 30 min, +2.0 impact",
    "Fix missing alt text on 3 images - 15 min, +0.3 impact"
  ]
}
```

**Prioritization Logic:**
1. Sort by severity (critical > warning > info)
2. Within severity, sort by estimated effort (low > medium > high)
3. Stop when `current_score + sum(impacts) >= target_score`

---

### Tool: `explain_score`

**Description:** Get detailed explanation of how a score was calculated.

**Input:**
```json
{
  "score": 5.5,
  "critical_issues": 3,
  "warning_issues": 5,
  "info_issues": 1,
  "penalties_applied": [
    {"type": "no_executable_examples", "penalty": 1.5}
  ]
}
```

**Output:**
```json
{
  "final_score": 5.5,
  "grade": "C",
  "tier_description": "Acceptable - Multiple Issues",
  "formula": "10.0 - (critical × 2.0) - (warnings × 0.5) - (info × 0.1) - content_penalties",
  "breakdown": {
    "starting_score": 10.0,
    "critical_penalty": 6.0,
    "warning_penalty": 2.5,
    "info_penalty": 0.1,
    "content_penalties": [
      {
        "type": "no_executable_examples",
        "penalty": 1.5,
        "explanation": "No complete executable examples found"
      }
    ]
  },
  "human_explanation": "Acceptable documentation with notable gaps: 3 critical issues block user progress. Requires substantial improvements.",
  "rubric_match": true,
  "characteristics_of_tier": [
    "Significant gaps in flow or prerequisites",
    "Missing critical examples or context",
    "Users struggle without external help",
    "Requires substantial revision"
  ]
}
```

---

## Integration with Clarity Agent

### Updated Agent Workflow

```python
# stackbench/agents/clarity_agent.py

async def analyze_document(self, extraction_file: Path) -> Optional[ClarityValidationOutput]:
    """
    Analyze clarity and structure of a single document.

    NEW: Uses MCP server for deterministic scoring.
    """

    # ... existing setup code ...

    # Create options with MCP server configured
    options = ClaudeAgentOptions(
        system_prompt=CLARITY_SYSTEM_PROMPT,
        allowed_tools=["Read"],
        permission_mode="acceptEdits",
        hooks=hooks,
        cwd=str(Path.cwd()),
        mcpServers=[{
            "name": "clarity-scoring",
            "command": "python",
            "args": ["-m", "stackbench.mcp_servers.clarity_scoring_server"],
            "transport": "stdio"
        }]
    )

    async with ClaudeSDKClient(options=options) as client:
        # ===== PHASE 1: Issue Detection (Agent) =====

        issue_detection_prompt = create_clarity_validation_prompt(
            document_page=document_page,
            markdown_file_path=str(markdown_path.absolute()),
            repository_root=str(self.repository_folder.absolute()),
            library=library,
            version=version,
            language=language,
            content=processed_content,
            api_validation=api_validation,
            code_validation=code_validation
        )

        # Agent identifies all issues
        response_text = await self.get_claude_response(
            client, issue_detection_prompt, logger, messages_log_file
        )
        issues_data = self.extract_json_from_response(response_text)

        # ===== PHASE 2: Score Calculation (MCP Server) =====

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

        scoring_prompt = f"""
I've analyzed the documentation and identified:
- Critical issues: {critical_count}
- Warning issues: {warning_count}
- Info issues: {info_count}
- Total code blocks: {tech_access.get('total_code_blocks_checked', 0)}
- Broken links: {len(tech_access.get('broken_links', []))}
- Missing alt text: {len(tech_access.get('missing_alt_text', []))}

Use the clarity-scoring MCP server to:

1. Call `calculate_clarity_score` with these metrics
2. Call `calculate_dimension_score` for each dimension:
   - instruction_clarity (issues: {count_by_dimension(clarity_issues, 'instruction_clarity')})
   - logical_flow (issues: {count_by_dimension(clarity_issues, 'logical_flow')})
   - completeness (issues: {count_by_dimension(clarity_issues, 'completeness')})
   - consistency (issues: {count_by_dimension(clarity_issues, 'consistency')})
   - prerequisite_coverage (issues: {count_by_dimension(clarity_issues, 'prerequisite_coverage')})
3. Call `get_improvement_roadmap` with current score and target 8.0
4. Call `explain_score` for transparency

Return the complete scoring data as JSON.
"""

        scoring_response = await self.get_claude_response(
            client, scoring_prompt, logger, messages_log_file
        )
        scoring_data = self.extract_json_from_response(scoring_response)

        # ===== PHASE 3: Combine Results =====

        analysis = ClarityValidationOutput(
            validation_id=str(uuid4()),
            validated_at=datetime.utcnow().isoformat() + 'Z',
            source_file=extraction_file.name,
            document_page=document_page,
            library=library,
            version=version,
            language=language,

            # Issues from agent (Phase 1)
            clarity_issues=[ClarityIssue(**i) for i in clarity_issues],
            structural_issues=[StructuralIssue(**i) for i in structural_issues],
            technical_accessibility=TechnicalAccessibility(**tech_access),

            # Scores from MCP server (Phase 2)
            clarity_score=ClarityScore(**scoring_data['clarity_score']),

            # Roadmap from MCP server (Phase 2)
            improvement_roadmap=ImprovementRoadmap(**scoring_data['improvement_roadmap']),

            # Explanation from MCP server (Phase 2)
            score_explanation=ScoreExplanation(**scoring_data['score_explanation']),

            summary=clarity_data.get('summary', {}),
            processing_time_ms=processing_time,
            warnings=all_warnings
        )

        # Save and return
        output_file = self.output_folder / f"{doc_stem}_clarity.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(analysis.model_dump_json(indent=2))

        return analysis
```

### Updated Prompt

The clarity agent prompt needs to:
1. **Remove scoring instructions** - MCP server handles this
2. **Add dimension tagging** - Each issue must tag applicable dimension(s)
3. **Focus on issue detection** - Agent's core strength

```python
CLARITY_SYSTEM_PROMPT = """You are an expert documentation quality analyst specializing in evaluating instructional clarity and structure.

Your role is to identify clarity issues in documentation from the perspective of a new user. You do NOT assign scores - a separate scoring system handles that deterministically.

**Your Tasks:**
1. Read through documentation as a new user trying to follow it
2. Identify clarity issues with specific locations
3. Tag each issue with applicable dimension(s)
4. Provide actionable suggested fixes

**Issue Dimensions:**
Tag each issue with one or more of:
- `instruction_clarity`: Unclear commands, incomplete examples, missing outcome explanations
- `logical_flow`: Steps don't build properly, gaps in reasoning, forward references
- `completeness`: Missing prerequisites, missing details, missing edge cases
- `consistency`: Inconsistent terminology, code style, or explanations
- `prerequisite_coverage`: Prerequisites not stated upfront, missing version requirements

**Severity Levels:**
- `critical`: Issue blocks user progress entirely
- `warning`: Issue causes confusion but is workaroundable
- `info`: Nice-to-have improvement

**Output Format:**
Return issues as JSON with this structure:
```json
{
  "clarity_issues": [
    {
      "type": "logical_gap",
      "severity": "critical",
      "dimensions": ["logical_flow", "completeness"],
      "line": 45,
      "section": "Configuration",
      "message": "...",
      "suggested_fix": "...",
      "affected_code": "...",
      "context_quote": "..."
    }
  ],
  "structural_issues": [...],
  "technical_accessibility": {...}
}
```

DO NOT include score fields - the scoring system will calculate those based on your issues.
"""
```

---

## Implementation Plan

### Phase 1: MCP Server Foundation (Week 1)

**Tasks:**
1. Create `stackbench/mcp_servers/` directory structure
2. Implement `clarity_scoring_server.py` with 5 tools:
   - `get_rubric`
   - `calculate_clarity_score`
   - `calculate_dimension_score`
   - `get_improvement_roadmap`
   - `explain_score`
3. Create `clarity_scoring/` submodules:
   - `rubric.py` - Rubric definition
   - `calculator.py` - Score calculation logic
   - `roadmap.py` - Roadmap generation
   - `explainer.py` - Explanation generation
4. Add unit tests for all calculation functions

**Deliverables:**
- MCP server runnable via: `python -m stackbench.mcp_servers.clarity_scoring_server`
- Test suite with 100% coverage of scoring logic
- Documentation for each tool

**Success Criteria:**
- All 5 MCP tools respond correctly to sample inputs
- Formula produces expected scores for test cases
- Tests pass

---

### Phase 2: Schema Updates (Week 1-2)

**Tasks:**
1. Update `stackbench/schemas.py`:
   - Add `ImprovementRoadmap` model
   - Add `ScoreExplanation` model
   - Add `DashboardMetrics` model
   - Update `ClarityScore` to include rubric reference
   - Update `ClarityValidationOutput` to include new fields
2. Update validation hooks in `stackbench/hooks/validation.py`
3. Update CLI output formatting in `stackbench/cli.py`

**Schema Additions:**

```python
class PriorityFix(BaseModel):
    """A prioritized fix in the improvement roadmap."""
    rank: int
    issue_type: str
    severity: str
    location: str
    impact: str  # e.g., "+2.0 points"
    estimated_effort: str  # "low" | "medium" | "high"
    message: str


class ImprovementRoadmap(BaseModel):
    """Prioritized roadmap to improve documentation score."""
    current_score: float
    target_score: float
    estimated_new_score: float
    total_fixes_needed: int
    estimated_total_effort: str
    priority_fixes: List[PriorityFix]
    quick_wins: List[str]


class ScoreExplanation(BaseModel):
    """Detailed explanation of score calculation."""
    final_score: float
    grade: str
    tier_description: str
    formula: str
    breakdown: Dict[str, Any]
    human_explanation: str
    rubric_match: bool
    characteristics_of_tier: List[str]


class DashboardMetrics(BaseModel):
    """Metrics optimized for dashboard visualization."""
    score_grade: str  # "A+", "A", "B", "C", "D", "F"
    completeness_percent: float  # 0-100
    blocker_count: int
    health_status: str  # "healthy" | "needs_attention" | "critical"


class ClarityScore(BaseModel):
    """Clarity scoring metrics (updated)."""
    overall_score: float
    grade: str  # NEW: Letter grade
    rubric_tier: str  # NEW: e.g., "6.0-7.9"
    instruction_clarity: float
    logical_flow: float
    completeness: float
    consistency: float
    prerequisite_coverage: float
    evaluation_criteria: Dict[str, Any]  # Updated: specific not generic
    scoring_rationale: Optional[str] = None


class ClarityValidationOutput(BaseModel):
    """Complete clarity validation output (updated)."""
    # ... existing fields ...
    clarity_score: ClarityScore
    improvement_roadmap: ImprovementRoadmap  # NEW
    score_explanation: ScoreExplanation  # NEW
    dashboard_metrics: DashboardMetrics  # NEW
    # ... rest ...
```

**Deliverables:**
- Updated schemas with backward compatibility
- Validation tests pass
- CLI displays new fields

---

### Phase 3: Agent Integration (Week 2)

**Tasks:**
1. Update `clarity_agent.py`:
   - Configure MCP server in `ClaudeAgentOptions`
   - Update system prompt (remove scoring instructions)
   - Add dimension tagging to issues
   - Implement 2-phase workflow (issues → scoring)
2. Update `create_clarity_validation_prompt()` function
3. Add helper function `count_by_dimension()`
4. Test integration end-to-end

**Key Changes:**

```python
# Helper function
def count_by_dimension(issues: List[Dict], dimension: str) -> Dict[str, int]:
    """Count issues by severity for a specific dimension."""
    result = {"critical": 0, "warning": 0, "info": 0}
    for issue in issues:
        if dimension in issue.get('dimensions', []):
            severity = issue.get('severity', 'info')
            result[severity] += 1
    return result
```

**Deliverables:**
- Clarity agent uses MCP server for scoring
- Sample runs produce new output format
- Agent logs show MCP tool calls

---

### Phase 4: Frontend Display (Week 3)

**Tasks:**
1. Update frontend to display new fields:
   - Letter grade badge (A+, A, B, etc.)
   - Score explanation tooltip
   - Improvement roadmap UI
   - Quick wins callout box
   - Rubric reference panel
2. Add visual elements:
   - Score gauge/meter
   - Priority fixes checklist
   - Effort estimates
3. Update API endpoints in backend

**UI Mockup:**

```
┌───────────────────────────────────────────────────────────┐
│ Document: pydantic.md                          Grade: B   │
├───────────────────────────────────────────────────────────┤
│ Overall Clarity Score: 6.8 / 10                          │
│ [████████████████░░░░░░░░] 68%                           │
│                                                           │
│ Tier: Good - Clear Improvements Needed                   │
│ ℹ️  Score calculated: 10.0 - (2 critical × 2.0) -       │
│    (3 warnings × 0.5) = 6.5, +0.3 for good structure    │
├───────────────────────────────────────────────────────────┤
│ 🎯 Improvement Roadmap                                    │
│                                                           │
│ To reach 8.0/10, fix these 3 issues:                     │
│                                                           │
│ ⚠️  #1 Critical: Syntax error (line 14)    +2.0 | 30min │
│     Fix indentation in code example                      │
│                                                           │
│ ⚠️  #2 Critical: Missing explanation       +2.0 | 1hr   │
│     Add intro paragraph explaining workflow              │
│                                                           │
│ ⚡ #3 Warning: Missing prerequisites        +0.5 | 30min │
│     Add Prerequisites section at top                     │
│                                                           │
│ Estimated effort: 2 hours → New score: 8.5/10           │
├───────────────────────────────────────────────────────────┤
│ ⚡ Quick Wins (high impact, low effort)                   │
│                                                           │
│ • Fix syntax error at line 14 (30 min, +2.0 impact)     │
│ • Add missing import statements (15 min, +0.5 impact)   │
└───────────────────────────────────────────────────────────┘
```

**Deliverables:**
- Updated UI components
- Responsive design for roadmap display
- Tooltips for score explanations

---

### Phase 5: Testing & Validation (Week 3-4)

**Tasks:**
1. Run on real documentation sets:
   - LanceDB Python docs (existing test case)
   - New documentation sets
2. Compare old vs new scoring
3. Validate consistency across multiple runs
4. Gather feedback from doc owners
5. Tune weights if needed

**Test Cases:**

| Test Case | Critical | Warning | Info | Expected Score | Expected Grade |
|-----------|----------|---------|------|----------------|----------------|
| Perfect doc | 0 | 0 | 0 | 10.0 | A+ |
| Minor issues | 0 | 3 | 2 | 8.3 | A |
| Some gaps | 1 | 5 | 1 | 5.4 | C |
| Major problems | 4 | 8 | 0 | 0.0 | F |

**Deliverables:**
- Test report with consistency metrics
- Comparison document (old vs new scores)
- Updated rubric/weights if needed

---

### Phase 6: Documentation & Launch (Week 4)

**Tasks:**
1. Write user-facing documentation:
   - How scores are calculated
   - How to interpret roadmaps
   - How to improve scores
2. Update CLAUDE.md project instructions
3. Create video walkthrough
4. Announce changes

**Deliverables:**
- User guide: "Understanding Your Clarity Score"
- Developer guide: "How the MCP Scoring Server Works"
- Blog post or demo video

---

## Testing Strategy

### Unit Tests

**MCP Server (`tests/mcp_servers/test_clarity_scoring.py`):**

```python
import pytest
from stackbench.mcp_servers.clarity_scoring import calculator, roadmap, explainer

def test_calculate_overall_score_perfect():
    """Test perfect score with no issues."""
    result = calculator.calculate_overall_score({
        "critical_issues": 0,
        "warning_issues": 0,
        "info_issues": 0,
        "total_code_blocks": 10,
        "executable_examples": 10
    })
    assert result["overall_score"] == 10.0
    assert result["grade"] == "A+"
    assert result["rubric_tier"] == "10.0"


def test_calculate_overall_score_with_issues():
    """Test score with multiple issues."""
    result = calculator.calculate_overall_score({
        "critical_issues": 2,
        "warning_issues": 3,
        "info_issues": 1,
        "total_code_blocks": 8,
        "executable_examples": 5
    })
    # 10.0 - (2*2.0) - (3*0.5) - (1*0.1) = 10.0 - 4.0 - 1.5 - 0.1 = 4.4
    assert result["overall_score"] == 4.4
    assert result["grade"] == "C"
    assert result["rubric_tier"] == "4.0-5.9"


def test_calculate_dimension_score():
    """Test dimension-specific scoring."""
    result = calculator.calculate_dimension({
        "dimension": "logical_flow",
        "critical_issues_for_dimension": 1,
        "warning_issues_for_dimension": 2,
        "info_issues_for_dimension": 0
    })
    # 10.0 - (1*2.0) - (2*0.5) = 10.0 - 2.0 - 1.0 = 7.0
    assert result["score"] == 7.0


def test_improvement_roadmap_generation():
    """Test roadmap prioritization."""
    issues = [
        {"type": "syntax_error", "severity": "critical", "line": 14, "section": "Intro"},
        {"type": "unclear", "severity": "warning", "line": 23, "section": "Setup"},
        {"type": "missing_prereq", "severity": "critical", "line": 1, "section": "Top"}
    ]

    result = roadmap.generate_improvement_roadmap({
        "current_score": 5.0,
        "target_score": 8.0,
        "issues": issues
    })

    # Should prioritize critical issues first
    assert result["priority_fixes"][0]["severity"] == "critical"
    assert result["priority_fixes"][1]["severity"] == "critical"

    # Should estimate new score
    assert result["estimated_new_score"] >= 8.0


def test_score_explanation():
    """Test human-readable explanation generation."""
    result = explainer.explain_score_calculation({
        "score": 6.5,
        "critical_issues": 1,
        "warning_issues": 4,
        "info_issues": 0,
        "penalties_applied": []
    })

    assert "critical" in result["human_explanation"].lower()
    assert result["formula"] is not None
    assert "breakdown" in result
```

### Integration Tests

**End-to-End (`tests/integration/test_clarity_with_mcp.py`):**

```python
import pytest
from pathlib import Path
from stackbench.agents.clarity_agent import DocumentationClarityAgent

@pytest.mark.asyncio
async def test_clarity_agent_with_mcp_scoring(tmp_path):
    """Test clarity agent uses MCP server for scoring."""

    # Setup test data
    extraction_folder = tmp_path / "extraction"
    output_folder = tmp_path / "clarity"
    repo_folder = tmp_path / "repo"

    # Create sample extraction and markdown
    # ...

    agent = DocumentationClarityAgent(
        extraction_folder=extraction_folder,
        output_folder=output_folder,
        repository_folder=repo_folder,
        num_workers=1
    )

    result = await agent.analyze_document(extraction_file)

    # Verify MCP scoring fields present
    assert result.clarity_score.grade in ["A+", "A", "B", "C", "D", "F"]
    assert result.clarity_score.rubric_tier is not None
    assert result.improvement_roadmap is not None
    assert result.score_explanation is not None

    # Verify score is deterministic
    result2 = await agent.analyze_document(extraction_file)
    assert result.clarity_score.overall_score == result2.clarity_score.overall_score


@pytest.mark.asyncio
async def test_scoring_consistency():
    """Test that same issues always produce same score."""

    metrics = {
        "critical_issues": 3,
        "warning_issues": 5,
        "info_issues": 1,
        "total_code_blocks": 10,
        "executable_examples": 8
    }

    # Run multiple times
    scores = []
    for _ in range(5):
        result = calculator.calculate_overall_score(metrics)
        scores.append(result["overall_score"])

    # All scores should be identical
    assert len(set(scores)) == 1
```

### Validation Tests

**Rubric Consistency (`tests/validation/test_rubric.py`):**

```python
def test_rubric_tiers_non_overlapping():
    """Ensure rubric tiers don't overlap."""
    from stackbench.mcp_servers.clarity_scoring.rubric import SCORING_RUBRIC

    ranges = [tier["range"] for tier in SCORING_RUBRIC.values()]

    for i, (min1, max1) in enumerate(ranges):
        for j, (min2, max2) in enumerate(ranges):
            if i != j:
                # No overlap
                assert not (min1 <= max2 and min2 <= max1)


def test_formula_produces_valid_scores():
    """Test formula never produces out-of-range scores."""
    import itertools

    # Test exhaustive combinations
    for critical in range(0, 10):
        for warnings in range(0, 15):
            for info in range(0, 5):
                result = calculator.calculate_overall_score({
                    "critical_issues": critical,
                    "warning_issues": warnings,
                    "info_issues": info,
                    "total_code_blocks": 10,
                    "executable_examples": 5
                })

                # Score must be in [0.0, 10.0]
                assert 0.0 <= result["overall_score"] <= 10.0


def test_tier_criteria_match_formula():
    """Test that rubric criteria align with formula results."""
    # Tier "8.0-9.9" says: max 3 warnings, 0 critical
    result = calculator.calculate_overall_score({
        "critical_issues": 0,
        "warning_issues": 3,
        "info_issues": 0,
        "total_code_blocks": 10,
        "executable_examples": 10
    })

    # 10.0 - (3*0.5) = 8.5 → should be in "8.0-9.9" tier
    assert result["rubric_tier"] == "8.0-9.9"
    assert result["meets_criteria"] is True
```

---

## Future Enhancements

### Phase 7: Advanced Features (Optional)

**1. Custom Rubrics**

Allow users to define custom scoring rubrics:

```bash
stackbench validate clarity \
  --rubric custom_rubric.yaml \
  --weights critical=3.0,warning=1.0
```

**2. Historical Tracking**

Track score changes over time:

```python
{
  "score_history": [
    {"date": "2025-10-01", "score": 5.5, "commit": "abc123"},
    {"date": "2025-10-15", "score": 7.2, "commit": "def456"},
    {"date": "2025-10-23", "score": 8.1, "commit": "ghi789"}
  ],
  "trend": "improving",
  "improvement_velocity": "+0.13 per week"
}
```

**3. Comparative Benchmarking**

Compare documentation quality across projects:

```
Your score: 6.8/10 (B)

Benchmark comparison:
- Top 10% of projects: 8.5+ (A)
- Median: 6.2 (B)
- Your rank: 58th percentile
```

**4. AI-Generated Fix PRs**

Generate pull requests with suggested fixes:

```bash
stackbench fix-clarity \
  --doc docs/quickstart.md \
  --target-score 8.0 \
  --create-pr
```

**5. Quality Gates for CI/CD**

Enforce minimum scores in CI:

```yaml
# .github/workflows/docs-quality.yml
- name: Validate Documentation Clarity
  run: |
    stackbench validate clarity \
      --min-score 7.0 \
      --fail-on-critical
```

---

## Appendix A: Example Output

### Before (Current System)

```json
{
  "clarity_score": {
    "overall_score": 6.8,
    "instruction_clarity": 6.5,
    "logical_flow": 6.0,
    "completeness": 6.5,
    "consistency": 8.0,
    "prerequisite_coverage": 6.5,
    "evaluation_criteria": {
      "instruction_clarity": "Measured by: clarity of commands, completeness of examples...",
      "logical_flow": "Measured by: whether steps build on each other...",
      ...
    },
    "scoring_rationale": "Documentation provides a working example but suffers from..."
  },
  "clarity_issues": [...],
  "summary": {
    "total_clarity_issues": 6,
    "critical_clarity_issues": 2,
    "warning_clarity_issues": 3,
    "overall_quality_rating": "good"
  }
}
```

### After (With MCP Server)

```json
{
  "clarity_score": {
    "overall_score": 6.5,
    "grade": "B",
    "rubric_tier": "6.0-7.9",
    "rubric_description": "Good - Clear Improvements Needed",
    "instruction_clarity": 6.5,
    "logical_flow": 5.0,
    "completeness": 6.0,
    "consistency": 8.0,
    "prerequisite_coverage": 6.5,
    "evaluation_criteria": {
      "instruction_clarity": {
        "score": 6.5,
        "measured_by": [
          "Found 8 code examples, 6 are complete and runnable",
          "2 examples missing imports",
          "Commands clear but outcomes not explained"
        ],
        "key_issues": ["Line 14: Syntax error in main example"]
      },
      "logical_flow": {
        "score": 5.0,
        "measured_by": [
          "2 critical gaps: Steps reference undefined resources",
          "Prerequisites scattered (lines 87, 102)"
        ],
        "key_issues": ["Line 67: References config.yaml never created"]
      }
    },
    "scoring_rationale": "Score calculated: 10.0 - (2 critical × 2.0) - (3 warnings × 0.5) - (1 info × 0.1) = 5.4, adjusted to 6.5 for good consistency"
  },

  "score_explanation": {
    "final_score": 6.5,
    "grade": "B",
    "tier_description": "Good - Clear Improvements Needed",
    "formula": "10.0 - (critical × 2.0) - (warnings × 0.5) - (info × 0.1) - content_penalties",
    "breakdown": {
      "starting_score": 10.0,
      "critical_penalty": 4.0,
      "warning_penalty": 1.5,
      "info_penalty": 0.1,
      "content_penalties": []
    },
    "human_explanation": "Good documentation but has 2 critical and 3 warning issues that should be addressed for better user experience.",
    "rubric_match": true,
    "characteristics_of_tier": [
      "Basic workflows explained but gaps exist",
      "Some examples incomplete or unclear",
      "Users can follow with effort",
      "Noticeable room for improvement"
    ]
  },

  "improvement_roadmap": {
    "current_score": 6.5,
    "target_score": 8.0,
    "estimated_new_score": 8.5,
    "total_fixes_needed": 3,
    "estimated_total_effort": "low (< 2 hours)",
    "priority_fixes": [
      {
        "rank": 1,
        "issue_type": "syntax_error",
        "severity": "critical",
        "location": "Introduction/First Example (line 14)",
        "impact": "+2.0 points",
        "estimated_effort": "low",
        "message": "Inconsistent indentation in main code example causes IndentationError"
      },
      {
        "rank": 2,
        "issue_type": "missing_explanation",
        "severity": "critical",
        "location": "Introduction/First Example (line 8)",
        "impact": "+2.0 points",
        "estimated_effort": "medium",
        "message": "Introductory code example has no explanation of what it demonstrates"
      },
      {
        "rank": 3,
        "issue_type": "missing_prerequisites",
        "severity": "warning",
        "location": "Document beginning (before line 1)",
        "impact": "+0.5 points",
        "estimated_effort": "low",
        "message": "No prerequisites section - missing Python version and install requirements"
      }
    ],
    "quick_wins": [
      "Fix syntax error at line 14 (30 min effort, +2.0 impact)",
      "Add Prerequisites section at top (30 min effort, +0.5 impact)"
    ]
  },

  "dashboard_metrics": {
    "score_grade": "B",
    "completeness_percent": 75.0,
    "blocker_count": 2,
    "health_status": "needs_attention"
  },

  "clarity_issues": [...],
  "structural_issues": [...],
  "summary": {
    "total_clarity_issues": 6,
    "critical_clarity_issues": 2,
    "warning_clarity_issues": 3,
    "info_clarity_issues": 1,
    "overall_quality_rating": "good"
  }
}
```

---

## Appendix B: Rationale Deep Dive

### Why Not Just Use Agent Prompting?

**Option 1: Better Prompts**
```
"Use this exact formula: 10.0 - (critical × 2.0) - (warnings × 0.5)..."
```

**Problems:**
- LLM might still interpret differently
- Can't guarantee exact math
- Can't unit test
- Hard to version control

**Option 2: Post-Processing**
```python
# After agent runs, recalculate scores
agent_output = agent.analyze()
agent_output["score"] = recalculate_score(agent_output["issues"])
```

**Problems:**
- Duplicates scoring logic
- Agent still outputs wrong scores (confusing for users reading logs)
- Doesn't provide roadmap or explanation

**Option 3: MCP Server (Proposed)**
- Agent uses MCP tools **during** execution
- Scoring is deterministic and testable
- Roadmap and explanation included
- Single source of truth for rubric

### Why Weights Matter

Current weights:
```python
WEIGHTS = {
    "critical_issue": 2.0,
    "warning_issue": 0.5,
    "info_issue": 0.1,
}
```

**Thought process:**

1. **Critical = -2.0 points**
   - 5 critical issues = -10.0 (score drops to 0)
   - Makes sense: 5 blocking issues = unusable docs

2. **Warning = -0.5 points**
   - 10 warnings = -5.0 (score drops to 5.0)
   - Makes sense: lots of confusion but still usable

3. **Info = -0.1 points**
   - 20 info issues = -2.0 (minor impact)
   - Makes sense: polish matters but doesn't dominate

**Alternative weighting schemes:**

| Scheme | Critical | Warning | Info | Philosophy |
|--------|----------|---------|------|------------|
| Strict | 3.0 | 1.0 | 0.2 | Harshly penalize all issues |
| Lenient | 1.5 | 0.3 | 0.05 | Only major issues matter |
| Balanced (proposed) | 2.0 | 0.5 | 0.1 | Middle ground |

We can tune these based on real-world feedback.

### Why Improvement Roadmap Matters

**User Story:**

> "I got a 5.5/10 score. I want 8.0. I have limited time. What should I fix first?"

**Without Roadmap:**
- Reads all 12 issues
- Guesses which are most important
- Wastes time on low-impact fixes
- Frustrated

**With Roadmap:**
- Sees: "Fix these 3 issues to reach 8.0"
- Knows exact effort: "2 hours total"
- Has quick wins: "30 min for +2.0 impact"
- Prioritizes effectively

This transforms Stackbench from **diagnostic tool** → **actionable improvement platform**.

---

## Conclusion

The proposed MCP server for clarity scoring addresses all identified problems:

1. ✅ **Concrete rubric** with measurable criteria
2. ✅ **Deterministic scoring** via pure functions
3. ✅ **Transparent calculations** with detailed breakdowns
4. ✅ **Actionable roadmaps** prioritized by impact
5. ✅ **Consistent results** across runs
6. ✅ **Testable logic** with full unit test coverage
7. ✅ **Follows Stackbench patterns** (proven MCP approach)

**Next Steps:**
1. Review this design document
2. Approve approach and timeline
3. Begin Phase 1 implementation (MCP server foundation)
4. Iterate based on feedback

**Questions or Feedback:**
Please file issues or discuss in the team channel.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Related Issues:** TBD
**Contributors:** [Your Name]
