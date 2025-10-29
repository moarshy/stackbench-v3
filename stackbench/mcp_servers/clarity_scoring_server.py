#!/usr/bin/env python3
"""
Clarity Scoring MCP Server

Provides deterministic scoring and improvement roadmap generation for documentation clarity validation.
Separates quantitative scoring (this server) from qualitative analysis (clarity agent).

Scoring Algorithm:
- Calculate 5 dimensional scores (each 0-10)
- Overall score = average of dimension scores
- TIER CONSTRAINT: Critical issues or failed examples automatically cap score at 7.9 (max Tier B)

Tools:
1. get_rubric - Returns scoring rubric and criteria
2. calculate_clarity_score - Computes overall and dimensional scores
3. calculate_dimension_score - Scores a single dimension
4. get_improvement_roadmap - Generates prioritized fix list
5. explain_score - Provides human-readable score explanation
"""

import json
from typing import Any, Dict, List, Literal, Optional

from mcp.server.stdio import stdio_server
from pydantic import BaseModel, Field

# Import centralized schemas from stackbench.schemas
from stackbench.schemas import (
    ClarityScore,
    ScoreBreakdown,
    ScoreExplanation,
    ImprovementRoadmap,
    PrioritizedFix,
    TierRequirements,
    ClarityIssue
)


# ============================================================================
# RUBRIC DEFINITION
# ============================================================================

SCORING_RUBRIC = {
    "10.0": {
        "tier": "S",
        "description": "Perfect - Production-ready documentation",
        "criteria": {
            "critical_issues": 0,
            "failed_examples": 0,
            "max_warning_issues": 0,
            "max_info_issues": 2,
        },
    },
    "8.0-9.9": {
        "tier": "A",
        "description": "Excellent - Minor polish needed",
        "criteria": {
            "critical_issues": 0,
            "failed_examples": 0,
            "max_warning_issues": 3,
        },
        "constraint": "Score automatically capped at 7.9 if critical_issues > 0 or failed_examples > 0",
    },
    "6.0-7.9": {
        "tier": "B",
        "description": "Good - Some clear improvements needed",
        "criteria": {
            "max_critical_issues": 1,
            "max_warning_issues": 7,
        },
    },
    "4.0-5.9": {
        "tier": "C",
        "description": "Acceptable - Multiple issues to address",
        "criteria": {
            "max_critical_issues": 3,
            "max_warning_issues": 12,
        },
    },
    "2.0-3.9": {
        "tier": "D",
        "description": "Poor - Significant problems blocking understanding",
        "criteria": {
            "max_critical_issues": 5,
        },
    },
    "0.0-1.9": {
        "tier": "F",
        "description": "Unusable - Cannot be followed",
        "criteria": {
            "critical_issues": "6+",
        },
    },
}

PENALTY_WEIGHTS = {
    "critical_issue": -2.0,
    "warning_issue": -0.5,
    "info_issue": -0.1,
    "failed_example": -1.0,
    "invalid_api": -0.8,
    "missing_api": -1.2,
}


# ============================================================================
# INPUT SCHEMAS (imported from centralized schemas.py at top)
# ============================================================================

# Map issue types to dimensions for scoring
ISSUE_TYPE_TO_DIMENSION = {
    # Instruction clarity issues
    "unclear_instruction": "instruction_clarity",
    "missing_example": "instruction_clarity",
    "incomplete_command": "instruction_clarity",

    # Logical flow issues
    "logical_gap": "logical_flow",
    "undefined_reference": "logical_flow",
    "missing_step": "logical_flow",

    # Completeness issues
    "missing_prerequisite": "prerequisite_coverage",
    "buried_prerequisites": "prerequisite_coverage",
    "missing_explanation": "completeness",
    "incomplete_example": "completeness",

    # Consistency issues
    "terminology_inconsistency": "consistency",
    "style_inconsistency": "consistency",
}


def get_issue_dimension(issue: ClarityIssue) -> str:
    """
    Map an issue type to its dimension for scoring.

    Args:
        issue: ClarityIssue with type field

    Returns:
        Dimension name (defaults to "completeness" if not mapped)
    """
    return ISSUE_TYPE_TO_DIMENSION.get(issue.type, "completeness")


class ContentMetrics(BaseModel):
    """Content quality metrics from validation agents."""

    total_code_blocks: int = 0
    successful_examples: int = 0
    failed_examples: int = 0
    total_api_signatures: int = 0
    valid_api_signatures: int = 0
    invalid_api_signatures: int = 0
    missing_api_signatures: int = 0
    api_accuracy_score: float = 0.0


# ============================================================================
# OUTPUT SCHEMAS
# ============================================================================
# Note: ClarityScore, ScoreBreakdown, ScoreExplanation, ImprovementRoadmap,
# PrioritizedFix, and TierRequirements are now imported from stackbench.schemas
# to avoid duplication and maintain a single source of truth.


class DimensionScore(BaseModel):
    """Score for a single clarity dimension (MCP-internal only)."""

    dimension: str
    score: float = Field(ge=0.0, le=10.0)
    issues_count: Dict[str, int]  # {"critical": 2, "warning": 3, "info": 1}
    primary_issues: List[str]  # Top 3 issues affecting this dimension


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================


def calculate_score(
    issues: List[ClarityIssue], metrics: ContentMetrics
) -> tuple[float, ScoreBreakdown]:
    """
    Calculate penalty-based score and breakdown (for transparency/debugging).

    NOTE: This function is now primarily used to generate the ScoreBreakdown
    for transparency. The actual overall_score is calculated by averaging
    dimension scores in the tool handler.

    Args:
        issues: List of issues detected by clarity agent
        metrics: Content quality metrics from validation agents

    Returns:
        Tuple of (penalty_based_score, breakdown)
    """
    # Count issues by severity
    critical_count = sum(1 for i in issues if i.severity == "critical")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")

    # Calculate penalties
    breakdown = ScoreBreakdown(
        base_score=10.0,  # Start with perfect score
        critical_issues_penalty=critical_count * PENALTY_WEIGHTS["critical_issue"],
        warning_issues_penalty=warning_count * PENALTY_WEIGHTS["warning_issue"],
        info_issues_penalty=info_count * PENALTY_WEIGHTS["info_issue"],
        failed_examples_penalty=metrics.failed_examples
        * PENALTY_WEIGHTS["failed_example"],
        invalid_api_penalty=metrics.invalid_api_signatures
        * PENALTY_WEIGHTS["invalid_api"],
        missing_api_penalty=metrics.missing_api_signatures
        * PENALTY_WEIGHTS["missing_api"],
        final_score=0.0,  # Will be calculated below
    )

    # Calculate final score
    final_score = 10.0
    final_score += breakdown.critical_issues_penalty
    final_score += breakdown.warning_issues_penalty
    final_score += breakdown.info_issues_penalty
    final_score += breakdown.failed_examples_penalty
    final_score += breakdown.invalid_api_penalty
    final_score += breakdown.missing_api_penalty
    final_score = max(0.0, min(10.0, final_score))

    breakdown.final_score = final_score

    return final_score, breakdown


def calculate_dimension_score(
    dimension: str, issues: List[ClarityIssue], metrics: ContentMetrics
) -> DimensionScore:
    """
    Calculate score for a single dimension.

    Args:
        dimension: Dimension name (e.g., "instruction_clarity")
        issues: All issues (will be filtered to this dimension)
        metrics: Content quality metrics

    Returns:
        DimensionScore with score and breakdown
    """
    # Filter issues for this dimension using type-to-dimension mapping
    dimension_issues = [i for i in issues if get_issue_dimension(i) == dimension]

    # Count by severity
    critical_count = sum(1 for i in dimension_issues if i.severity == "critical")
    warning_count = sum(1 for i in dimension_issues if i.severity == "warning")
    info_count = sum(1 for i in dimension_issues if i.severity == "info")

    # Calculate dimension score
    score = 10.0
    score += critical_count * PENALTY_WEIGHTS["critical_issue"]
    score += warning_count * PENALTY_WEIGHTS["warning_issue"]
    score += info_count * PENALTY_WEIGHTS["info_issue"]

    # For completeness dimension, add validation penalties
    if dimension == "completeness":
        score += metrics.failed_examples * PENALTY_WEIGHTS["failed_example"]
        score += metrics.invalid_api_signatures * PENALTY_WEIGHTS["invalid_api"]
        score += metrics.missing_api_signatures * PENALTY_WEIGHTS["missing_api"]

    score = max(0.0, min(10.0, score))

    # Get top 3 issues for this dimension
    primary_issues = [i.message for i in dimension_issues[:3]]

    return DimensionScore(
        dimension=dimension,
        score=score,
        issues_count={
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
        },
        primary_issues=primary_issues,
    )


def get_tier(score: float) -> tuple[str, str]:
    """
    Map score to tier and description.

    Args:
        score: Overall score (0.0-10.0)

    Returns:
        Tuple of (tier, description)
    """
    if score >= 10.0:
        return "S", SCORING_RUBRIC["10.0"]["description"]
    elif score >= 8.0:
        return "A", SCORING_RUBRIC["8.0-9.9"]["description"]
    elif score >= 6.0:
        return "B", SCORING_RUBRIC["6.0-7.9"]["description"]
    elif score >= 4.0:
        return "C", SCORING_RUBRIC["4.0-5.9"]["description"]
    elif score >= 2.0:
        return "D", SCORING_RUBRIC["2.0-3.9"]["description"]
    else:
        return "F", SCORING_RUBRIC["0.0-1.9"]["description"]


def generate_roadmap(
    issues: List[ClarityIssue], metrics: ContentMetrics, current_score: float
) -> ImprovementRoadmap:
    """
    Generate prioritized improvement roadmap.

    Args:
        issues: All detected issues
        metrics: Content quality metrics
        current_score: Current overall score

    Returns:
        ImprovementRoadmap with prioritized fixes
    """
    fixes: List[PrioritizedFix] = []

    # 1. Generate fixes for detected issues
    for issue in issues:
        dimension = get_issue_dimension(issue)

        # Map severity to priority
        if issue.severity == "critical":
            priority = "critical"
            impact = "high"
            projected_change = 2.0
        elif issue.severity == "warning":
            priority = "high" if dimension == "logical_flow" else "medium"
            impact = "medium"
            projected_change = 0.5
        else:
            priority = "low"
            impact = "low"
            projected_change = 0.1

        # Estimate effort based on dimension
        if dimension == "prerequisite_coverage":
            effort = "low"  # Usually just add missing info
        elif dimension == "logical_flow":
            effort = "medium"  # May need restructuring
        elif dimension == "completeness":
            effort = "medium"
        else:
            effort = "low"

        # Build location string from issue fields
        location = f"Line {issue.line}"
        if issue.section:
            location += f", Section '{issue.section}'"
        if issue.step_number:
            location += f", Step {issue.step_number}"

        fixes.append(
            PrioritizedFix(
                priority=priority,
                category=dimension,
                description=issue.message,
                location=location,
                impact=impact,
                effort=effort,
                projected_score_change=projected_change,
            )
        )

    # 2. Add fixes for failed examples
    if metrics.failed_examples > 0:
        fixes.append(
            PrioritizedFix(
                priority="critical",
                category="completeness",
                description=f"Fix {metrics.failed_examples} failed code example(s)",
                location="Code validation results",
                impact="high",
                effort="medium",
                projected_score_change=metrics.failed_examples * 1.0,
            )
        )

    # 3. Add fixes for invalid APIs
    if metrics.invalid_api_signatures > 0:
        fixes.append(
            PrioritizedFix(
                priority="critical",
                category="completeness",
                description=f"Fix {metrics.invalid_api_signatures} invalid API signature(s)",
                location="API validation results",
                impact="high",
                effort="low",
                projected_score_change=metrics.invalid_api_signatures * 0.8,
            )
        )

    # 4. Add fixes for missing APIs
    if metrics.missing_api_signatures > 0:
        fixes.append(
            PrioritizedFix(
                priority="high",
                category="completeness",
                description=f"Document {metrics.missing_api_signatures} missing API(s)",
                location="API validation results",
                impact="high",
                effort="high",
                projected_score_change=metrics.missing_api_signatures * 1.2,
            )
        )

    # Sort by priority then impact
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    impact_order = {"high": 0, "medium": 1, "low": 2}
    fixes.sort(
        key=lambda x: (priority_order[x.priority], impact_order[x.impact]), reverse=False
    )

    # Calculate projected scores
    critical_fixes = [f for f in fixes if f.priority == "critical"]
    projected_after_critical = current_score + sum(
        f.projected_score_change for f in critical_fixes
    )
    projected_after_critical = min(10.0, projected_after_critical)

    projected_after_all = current_score + sum(f.projected_score_change for f in fixes)
    projected_after_all = min(10.0, projected_after_all)

    # Identify quick wins (high impact + low effort)
    quick_wins = [
        f for f in fixes if f.impact == "high" and f.effort == "low"
    ]

    return ImprovementRoadmap(
        current_overall_score=current_score,
        projected_score_after_critical_fixes=projected_after_critical,
        projected_score_after_all_fixes=projected_after_all,
        prioritized_fixes=fixes,
        quick_wins=quick_wins,
    )


def explain_score_details(
    score: float,
    breakdown: ScoreBreakdown,
    issues: List[ClarityIssue],
    metrics: ContentMetrics,
) -> ScoreExplanation:
    """
    Generate human-readable score explanation.

    Args:
        score: Overall score
        breakdown: Score breakdown
        issues: All detected issues
        metrics: Content quality metrics

    Returns:
        ScoreExplanation with detailed analysis
    """
    tier, tier_description = get_tier(score)

    # Get next tier requirements
    current_tier_range = None
    next_tier = None
    next_tier_criteria = None

    if tier == "F":
        current_tier_range = "0.0-1.9"
        next_tier = "D (2.0-3.9)"
        next_tier_criteria = SCORING_RUBRIC["2.0-3.9"]["criteria"]
    elif tier == "D":
        current_tier_range = "2.0-3.9"
        next_tier = "C (4.0-5.9)"
        next_tier_criteria = SCORING_RUBRIC["4.0-5.9"]["criteria"]
    elif tier == "C":
        current_tier_range = "4.0-5.9"
        next_tier = "B (6.0-7.9)"
        next_tier_criteria = SCORING_RUBRIC["6.0-7.9"]["criteria"]
    elif tier == "B":
        current_tier_range = "6.0-7.9"
        next_tier = "A (8.0-9.9)"
        next_tier_criteria = SCORING_RUBRIC["8.0-9.9"]["criteria"]
    elif tier == "A":
        current_tier_range = "8.0-9.9"
        next_tier = "S (10.0)"
        next_tier_criteria = SCORING_RUBRIC["10.0"]["criteria"]
    else:  # S
        current_tier_range = "10.0"
        next_tier = None
        next_tier_criteria = None

    # Count current issues
    critical_count = sum(1 for i in issues if i.severity == "critical")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")

    current_status = {
        "critical_issues": critical_count,
        "warning_issues": warning_count,
        "info_issues": info_count,
        "failed_examples": metrics.failed_examples,
        "invalid_api_signatures": metrics.invalid_api_signatures,
        "missing_api_signatures": metrics.missing_api_signatures,
    }

    tier_requirements = TierRequirements(
        current_tier=f"{tier} ({current_tier_range})",
        next_tier=next_tier,
        requirements_for_next_tier=next_tier_criteria,
        current_status=current_status,
    )

    # Group issues by category (dimension) and severity
    primary_issues = []
    for category in [
        "instruction_clarity",
        "logical_flow",
        "completeness",
        "consistency",
        "prerequisite_coverage",
    ]:
        cat_issues = [i for i in issues if get_issue_dimension(i) == category]
        if cat_issues:
            critical = sum(1 for i in cat_issues if i.severity == "critical")
            warning = sum(1 for i in cat_issues if i.severity == "warning")
            info = sum(1 for i in cat_issues if i.severity == "info")

            primary_issues.append(
                {
                    "category": category,
                    "critical": critical,
                    "warning": warning,
                    "info": info,
                    "example": cat_issues[0].message,  # Use message field from ClarityIssue
                }
            )

    # Generate summary
    summary_parts = [
        f"Document scored {score:.1f}/10 (Tier {tier} - {tier_description})."
    ]

    if critical_count > 0:
        summary_parts.append(
            f"Primary concern: {critical_count} critical issue(s) "
            f"({breakdown.critical_issues_penalty:.1f} points penalty)."
        )

    if metrics.failed_examples > 0:
        summary_parts.append(
            f"{metrics.failed_examples} code example(s) failed validation "
            f"({breakdown.failed_examples_penalty:.1f} points penalty)."
        )

    if next_tier:
        summary_parts.append(f"To reach {next_tier}, address the requirements above.")
    else:
        summary_parts.append("Documentation is at perfect tier!")

    summary = " ".join(summary_parts)

    return ScoreExplanation(
        score=score,
        tier=tier,
        tier_description=tier_description,
        score_breakdown=breakdown,
        tier_requirements=tier_requirements,
        primary_issues=primary_issues,
        summary=summary,
    )




# ============================================================================
# MCP SERVER
# ============================================================================


from mcp.server import Server
from mcp.types import Tool, TextContent


class ClarityScoringMCPServer:
    """MCP Server for clarity scoring."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("clarity-scoring-server")
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_rubric",
                    description="Get the scoring rubric with tiers and criteria",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="calculate_clarity_score",
                    description="Calculate overall clarity score and dimensional scores from issues and validation metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issues": {
                                "type": "array",
                                "description": "List of clarity issues (any format accepted)",
                                "items": {"type": "object"}
                            },
                            "metrics": {
                                "type": "object",
                                "description": "Content quality metrics (any fields accepted)",
                            },
                        },
                        "required": ["issues", "metrics"],
                    },
                ),
                Tool(
                    name="calculate_dimension_score",
                    description="Calculate score for a single clarity dimension",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dimension": {"type": "string"},
                            "issues": {"type": "array", "items": {"type": "object"}},
                            "metrics": {"type": "object"},
                        },
                        "required": ["dimension", "issues", "metrics"],
                    },
                ),
                Tool(
                    name="get_improvement_roadmap",
                    description="Generate prioritized improvement roadmap with effort estimates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issues": {"type": "array", "items": {"type": "object"}},
                            "metrics": {"type": "object"},
                            "current_score": {"type": "number"},
                        },
                        "required": ["issues", "metrics", "current_score"],
                    },
                ),
                Tool(
                    name="explain_score",
                    description="Generate human-readable explanation of the clarity score",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "breakdown": {"type": "object"},
                            "issues": {"type": "array", "items": {"type": "object"}},
                            "metrics": {"type": "object"},
                        },
                        "required": ["score", "breakdown", "issues", "metrics"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_rubric":
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "rubric": SCORING_RUBRIC,
                                    "penalty_weights": PENALTY_WEIGHTS,
                                },
                                indent=2,
                            ),
                        )
                    ]

                elif name == "calculate_clarity_score":
                    issues_data = arguments["issues"]
                    metrics_data = arguments["metrics"]

                    # Parse inputs
                    issues = [ClarityIssue(**issue) for issue in issues_data]
                    metrics = ContentMetrics(**metrics_data)

                    # Calculate dimensional scores FIRST
                    dimensions = [
                        "instruction_clarity",
                        "logical_flow",
                        "completeness",
                        "consistency",
                        "prerequisite_coverage",
                    ]

                    dimension_scores = {}
                    for dim in dimensions:
                        dim_score = calculate_dimension_score(dim, issues, metrics)
                        dimension_scores[dim] = dim_score.score

                    # Calculate overall score as AVERAGE of dimension scores
                    # This ensures overall score is consistent with dimensional performance
                    overall_score = sum(dimension_scores.values()) / len(dimension_scores)
                    overall_score = max(0.0, min(10.0, overall_score))  # Clamp to 0-10 range

                    # TIER CONSTRAINT: Critical issues prevent S/A tiers
                    critical_count = sum(1 for i in issues if i.severity == "critical")
                    failed_examples_count = metrics.failed_examples

                    if critical_count > 0 or failed_examples_count > 0:
                        # Cap at 7.9 (max Tier B) if there are critical issues or failed examples
                        overall_score = min(overall_score, 7.9)

                    tier, _ = get_tier(overall_score)

                    # Still generate breakdown for transparency (shows what penalties were applied)
                    _, breakdown = calculate_score(issues, metrics)
                    # Update breakdown's final_score to reflect the new calculation
                    breakdown.final_score = overall_score

                    result = ClarityScore(
                        overall_score=overall_score,
                        tier=tier,
                        instruction_clarity=dimension_scores["instruction_clarity"],
                        logical_flow=dimension_scores["logical_flow"],
                        completeness=dimension_scores["completeness"],
                        consistency=dimension_scores["consistency"],
                        prerequisite_coverage=dimension_scores["prerequisite_coverage"],
                    )

                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "clarity_score": result.model_dump(),
                                    "breakdown": breakdown.model_dump(),
                                },
                                indent=2,
                            ),
                        )
                    ]

                elif name == "calculate_dimension_score":
                    dimension = arguments["dimension"]
                    issues_data = arguments["issues"]
                    metrics_data = arguments["metrics"]

                    issues = [ClarityIssue(**issue) for issue in issues_data]
                    metrics = ContentMetrics(**metrics_data)

                    result = calculate_dimension_score(dimension, issues, metrics)

                    return [
                        TextContent(
                            type="text", text=json.dumps(result.model_dump(), indent=2)
                        )
                    ]

                elif name == "get_improvement_roadmap":
                    issues_data = arguments["issues"]
                    metrics_data = arguments["metrics"]
                    current_score = arguments["current_score"]

                    issues = [ClarityIssue(**issue) for issue in issues_data]
                    metrics = ContentMetrics(**metrics_data)

                    result = generate_roadmap(issues, metrics, current_score)

                    return [
                        TextContent(
                            type="text", text=json.dumps(result.model_dump(), indent=2)
                        )
                    ]

                elif name == "explain_score":
                    score = arguments["score"]
                    breakdown_data = arguments["breakdown"]
                    issues_data = arguments["issues"]
                    metrics_data = arguments["metrics"]

                    breakdown = ScoreBreakdown(**breakdown_data)
                    issues = [ClarityIssue(**issue) for issue in issues_data]
                    metrics = ContentMetrics(**metrics_data)

                    result = explain_score_details(score, breakdown, issues, metrics)

                    return [
                        TextContent(
                            type="text", text=json.dumps(result.model_dump(), indent=2)
                        )
                    ]

                else:
                    return [
                        TextContent(type="text", text=f"Unknown tool: {name}")
                    ]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point for the MCP server."""
    server = ClarityScoringMCPServer()
    await server.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
