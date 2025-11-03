"""
Feedback Analyzer for DocuMentor MCP Server.

Analyzes user feedback collected via report_issue tool to identify documentation
quality issues, patterns, and priorities for library maintainers.

Features:
- Load and aggregate feedback from JSONL files
- Identify common issue patterns
- Prioritize issues by severity and frequency
- Generate actionable reports
- Support filtering and querying
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import Counter, defaultdict
from datetime import datetime
import logging

from stackbench.readme_llm.schemas import FeedbackIssue

logger = logging.getLogger(__name__)


class FeedbackAnalyzer:
    """
    Analyze user feedback to identify documentation quality issues.

    Example:
        >>> analyzer = FeedbackAnalyzer(feedback_path)
        >>> report = analyzer.generate_report()
        >>> print(f"Total issues: {report['summary']['total_issues']}")
        >>> print(f"Critical: {report['summary']['by_severity']['critical']}")
    """

    def __init__(self, feedback_file: Path):
        """
        Initialize feedback analyzer.

        Args:
            feedback_file: Path to feedback.jsonl file
        """
        self.feedback_file = Path(feedback_file)
        self.issues: List[FeedbackIssue] = []

        if self.feedback_file.exists():
            self._load_feedback()
        else:
            logger.warning(f"Feedback file not found: {self.feedback_file}")

    def _load_feedback(self):
        """Load feedback issues from JSONL file."""
        logger.info(f"Loading feedback from: {self.feedback_file}")

        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        issue_data = json.loads(line)
                        issue = FeedbackIssue(**issue_data)
                        self.issues.append(issue)
                    except Exception as e:
                        logger.error(f"Failed to parse feedback line: {e}")

            logger.info(f"Loaded {len(self.issues)} feedback issues")

        except Exception as e:
            logger.error(f"Failed to load feedback: {e}")
            raise

    def get_summary(self) -> Dict:
        """
        Get high-level summary of feedback.

        Returns:
            Summary statistics dictionary
        """
        if not self.issues:
            return {
                "total_issues": 0,
                "by_type": {},
                "by_severity": {},
                "by_status": {},
                "date_range": None,
            }

        # Count by type
        by_type = Counter(issue.issue_type for issue in self.issues)

        # Count by severity
        by_severity = Counter(issue.severity for issue in self.issues)

        # Count by status
        by_status = Counter(issue.status for issue in self.issues)

        # Date range
        timestamps = [datetime.fromisoformat(issue.timestamp) for issue in self.issues]
        date_range = {
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat(),
        }

        return {
            "total_issues": len(self.issues),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "by_status": dict(by_status),
            "date_range": date_range,
        }

    def get_api_issues(self) -> Dict[str, List[FeedbackIssue]]:
        """
        Group issues by API ID.

        Returns:
            Dictionary mapping API IDs to list of issues
        """
        api_issues = defaultdict(list)

        for issue in self.issues:
            if issue.api_id:
                api_issues[issue.api_id].append(issue)

        return dict(api_issues)

    def get_example_issues(self) -> Dict[str, List[FeedbackIssue]]:
        """
        Group issues by example ID.

        Returns:
            Dictionary mapping example IDs to list of issues
        """
        example_issues = defaultdict(list)

        for issue in self.issues:
            if issue.example_id:
                example_issues[issue.example_id].append(issue)

        return dict(example_issues)

    def identify_patterns(self) -> List[Dict]:
        """
        Identify common patterns in feedback.

        Returns:
            List of pattern dictionaries with:
            - pattern_type: Type of pattern identified
            - description: Human-readable description
            - count: Number of issues matching pattern
            - examples: Sample issue IDs
        """
        patterns = []

        # Pattern 1: Frequently reported APIs
        api_issues = self.get_api_issues()
        frequent_apis = [(api_id, issues) for api_id, issues in api_issues.items() if len(issues) >= 2]
        if frequent_apis:
            frequent_apis.sort(key=lambda x: len(x[1]), reverse=True)
            for api_id, issues in frequent_apis[:5]:  # Top 5
                patterns.append({
                    "pattern_type": "frequent_api_issues",
                    "description": f"API '{api_id}' has multiple reported issues",
                    "count": len(issues),
                    "api_id": api_id,
                    "issue_types": list(set(issue.issue_type for issue in issues)),
                    "example_issues": [issue.issue_id for issue in issues[:3]],
                })

        # Pattern 2: Frequently reported examples
        example_issues = self.get_example_issues()
        frequent_examples = [(ex_id, issues) for ex_id, issues in example_issues.items() if len(issues) >= 2]
        if frequent_examples:
            frequent_examples.sort(key=lambda x: len(x[1]), reverse=True)
            for example_id, issues in frequent_examples[:5]:  # Top 5
                patterns.append({
                    "pattern_type": "frequent_example_issues",
                    "description": f"Example '{example_id}' has multiple reported issues",
                    "count": len(issues),
                    "example_id": example_id,
                    "issue_types": list(set(issue.issue_type for issue in issues)),
                    "example_issues": [issue.issue_id for issue in issues[:3]],
                })

        # Pattern 3: Specific issue type clusters
        by_type = defaultdict(list)
        for issue in self.issues:
            by_type[issue.issue_type].append(issue)

        for issue_type, issues in by_type.items():
            if len(issues) >= 3:  # At least 3 issues of same type
                patterns.append({
                    "pattern_type": "issue_type_cluster",
                    "description": f"Multiple '{issue_type}' issues reported",
                    "count": len(issues),
                    "issue_type": issue_type,
                    "affected_apis": list(set(issue.api_id for issue in issues if issue.api_id)),
                    "affected_examples": list(set(issue.example_id for issue in issues if issue.example_id)),
                    "example_issues": [issue.issue_id for issue in issues[:3]],
                })

        # Pattern 4: Critical severity clusters
        critical_issues = [issue for issue in self.issues if issue.severity == "critical"]
        if len(critical_issues) >= 2:
            patterns.append({
                "pattern_type": "critical_severity_cluster",
                "description": f"Multiple critical issues need immediate attention",
                "count": len(critical_issues),
                "severity": "critical",
                "issue_types": list(set(issue.issue_type for issue in critical_issues)),
                "affected_apis": list(set(issue.api_id for issue in critical_issues if issue.api_id)),
                "affected_examples": list(set(issue.example_id for issue in critical_issues if issue.example_id)),
                "example_issues": [issue.issue_id for issue in critical_issues[:5]],
            })

        return patterns

    def prioritize_issues(self, top_k: int = 20) -> List[Dict]:
        """
        Prioritize issues for maintainers to address.

        Scoring factors:
        - Severity (critical=10, high=7, medium=5, low=2)
        - Issue type importance (broken_example=3, incorrect_signature=3, unclear_docs=2, missing_info=2, other=1)
        - Frequency (if same API/example has multiple issues)

        Args:
            top_k: Number of top priority issues to return

        Returns:
            List of prioritized issues with scores
        """
        severity_scores = {
            "critical": 10,
            "high": 7,
            "medium": 5,
            "low": 2,
        }

        type_scores = {
            "broken_example": 3,
            "incorrect_signature": 3,
            "unclear_docs": 2,
            "missing_info": 2,
            "other": 1,
        }

        # Count frequency per API/example
        api_frequency = Counter(issue.api_id for issue in self.issues if issue.api_id)
        example_frequency = Counter(issue.example_id for issue in self.issues if issue.example_id)

        # Score each issue
        scored_issues = []
        for issue in self.issues:
            # Base scores
            severity_score = severity_scores.get(issue.severity, 1)
            type_score = type_scores.get(issue.issue_type, 1)

            # Frequency boost
            frequency_boost = 0
            if issue.api_id:
                frequency_boost += min(api_frequency[issue.api_id] - 1, 3)  # Max +3
            if issue.example_id:
                frequency_boost += min(example_frequency[issue.example_id] - 1, 3)  # Max +3

            # Total score
            total_score = severity_score + type_score + frequency_boost

            scored_issues.append({
                "issue": issue.model_dump(),
                "priority_score": total_score,
                "score_breakdown": {
                    "severity": severity_score,
                    "type": type_score,
                    "frequency_boost": frequency_boost,
                }
            })

        # Sort by priority score
        scored_issues.sort(key=lambda x: x["priority_score"], reverse=True)

        return scored_issues[:top_k]

    def filter_issues(
        self,
        issue_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        api_id: Optional[str] = None,
        example_id: Optional[str] = None,
    ) -> List[FeedbackIssue]:
        """
        Filter issues by criteria.

        Args:
            issue_type: Filter by issue type
            severity: Filter by severity
            status: Filter by status
            api_id: Filter by API ID
            example_id: Filter by example ID

        Returns:
            Filtered list of issues
        """
        filtered = self.issues

        if issue_type:
            filtered = [issue for issue in filtered if issue.issue_type == issue_type]

        if severity:
            filtered = [issue for issue in filtered if issue.severity == severity]

        if status:
            filtered = [issue for issue in filtered if issue.status == status]

        if api_id:
            filtered = [issue for issue in filtered if issue.api_id == api_id]

        if example_id:
            filtered = [issue for issue in filtered if issue.example_id == example_id]

        return filtered

    def generate_report(self) -> Dict:
        """
        Generate comprehensive feedback report.

        Returns:
            Complete report dictionary with:
            - summary: Overall statistics
            - patterns: Identified patterns
            - priorities: Top priority issues
            - by_api: Issues grouped by API
            - by_example: Issues grouped by example
        """
        logger.info("Generating feedback report...")

        report = {
            "generated_at": datetime.now().isoformat(),
            "feedback_file": str(self.feedback_file),
            "summary": self.get_summary(),
            "patterns": self.identify_patterns(),
            "priorities": self.prioritize_issues(top_k=20),
            "by_api": {
                api_id: [issue.model_dump() for issue in issues]
                for api_id, issues in self.get_api_issues().items()
            },
            "by_example": {
                example_id: [issue.model_dump() for issue in issues]
                for example_id, issues in self.get_example_issues().items()
            },
            "recommendations": self._generate_recommendations(),
        }

        logger.info(f"Report generated: {report['summary']['total_issues']} issues analyzed")

        return report

    def _generate_recommendations(self) -> List[str]:
        """
        Generate actionable recommendations based on feedback.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        summary = self.get_summary()

        # Severity recommendations
        critical_count = summary["by_severity"].get("critical", 0)
        if critical_count > 0:
            recommendations.append(
                f"⚠️  URGENT: {critical_count} critical issue(s) need immediate attention"
            )

        high_count = summary["by_severity"].get("high", 0)
        if high_count >= 3:
            recommendations.append(
                f"⚠️  {high_count} high-severity issues should be addressed soon"
            )

        # Type recommendations
        broken_examples = summary["by_type"].get("broken_example", 0)
        if broken_examples >= 2:
            recommendations.append(
                f"🔧 {broken_examples} broken examples detected - run code validation to identify issues"
            )

        incorrect_sigs = summary["by_type"].get("incorrect_signature", 0)
        if incorrect_sigs >= 2:
            recommendations.append(
                f"📝 {incorrect_sigs} incorrect signatures reported - run API signature validation"
            )

        unclear_docs = summary["by_type"].get("unclear_docs", 0)
        if unclear_docs >= 3:
            recommendations.append(
                f"📖 {unclear_docs} clarity issues reported - consider improving documentation structure"
            )

        # Pattern-based recommendations
        patterns = self.identify_patterns()
        frequent_api_patterns = [p for p in patterns if p["pattern_type"] == "frequent_api_issues"]
        if frequent_api_patterns:
            top_api = frequent_api_patterns[0]
            recommendations.append(
                f"🎯 API '{top_api['api_id']}' has {top_api['count']} issues - prioritize fixes here"
            )

        # General recommendations
        if summary["total_issues"] == 0:
            recommendations.append("✅ No issues reported - documentation quality looks good!")
        elif summary["total_issues"] >= 10:
            recommendations.append(
                "📊 Consider running full Stackbench validation pipeline to systematically address issues"
            )

        return recommendations

    def export_report(self, output_path: Path):
        """
        Export feedback report to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        report = self.generate_report()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

        logger.info(f"Report exported to: {output_path}")
