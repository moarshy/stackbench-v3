"""
Helper functions for clarity validation agent.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def get_content_metrics_from_validation(
    doc_stem: str,
    results_folder: Path
) -> Dict[str, Any]:
    """
    Extract content quality metrics from API and code validation results.

    Args:
        doc_stem: Document stem (e.g., 'pydantic' from 'pydantic_analysis.json')
        results_folder: Path to results folder containing api_validation and code_validation subdirs

    Returns:
        Dictionary with metrics:
        - total_code_blocks: int
        - successful_examples: int
        - failed_examples: int
        - total_api_signatures: int
        - valid_api_signatures: int
        - invalid_api_signatures: int
        - missing_api_signatures: int
        - api_accuracy_score: float
    """
    metrics = {
        "total_code_blocks": 0,
        "successful_examples": 0,
        "failed_examples": 0,
        "total_api_signatures": 0,
        "valid_api_signatures": 0,
        "invalid_api_signatures": 0,
        "missing_api_signatures": 0,
        "api_accuracy_score": 0.0
    }

    # Load code validation results
    code_validation_file = results_folder / "code_validation" / f"{doc_stem}_validation.json"
    if code_validation_file.exists():
        try:
            with open(code_validation_file, 'r', encoding='utf-8') as f:
                code_data = json.load(f)

            metrics["total_code_blocks"] = code_data.get("total_examples", 0)
            metrics["successful_examples"] = code_data.get("successful", 0)
            metrics["failed_examples"] = code_data.get("failed", 0)
        except Exception as e:
            print(f"Warning: Could not load code validation for {doc_stem}: {e}")

    # Load API validation results
    api_validation_file = results_folder / "api_validation" / f"{doc_stem}_validation.json"
    if api_validation_file.exists():
        try:
            with open(api_validation_file, 'r', encoding='utf-8') as f:
                api_data = json.load(f)

            summary = api_data.get("summary", {})
            metrics["total_api_signatures"] = summary.get("total_signatures", 0)
            metrics["valid_api_signatures"] = summary.get("valid", 0)
            metrics["invalid_api_signatures"] = summary.get("invalid", 0)
            metrics["missing_api_signatures"] = summary.get("not_found", 0)
            metrics["api_accuracy_score"] = summary.get("accuracy_score", 0.0)
        except Exception as e:
            print(f"Warning: Could not load API validation for {doc_stem}: {e}")

    return metrics
