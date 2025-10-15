#!/usr/bin/env python3
"""
Output Directory Validator Hook

This hook validates the entire extraction output directory structure to ensure:
- All *_analysis.json files are valid
- extraction_summary.json exists and is valid
- Summary references all analysis files
- No orphaned or corrupted files

Hook Event: Stop (runs when agent finishes)
Environment Variable: EXTRACTION_OUTPUT_DIR
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Set


# ============================================================================
# VALIDATION SCHEMAS (Same as validate_extraction_json.py)
# ============================================================================

DOCUMENT_ANALYSIS_SCHEMA = {
    "required_fields": [
        "page", "library", "language", "signatures", "examples",
        "processed_at", "total_signatures", "total_examples", "warnings"
    ],
    "optional_fields": ["version", "processing_time_ms"],
    "field_types": {
        "page": str,
        "library": str,
        "version": (str, type(None)),
        "language": str,
        "signatures": list,
        "examples": list,
        "processed_at": str,
        "total_signatures": int,
        "total_examples": int,
        "warnings": list,
        "processing_time_ms": (int, type(None))
    }
}

EXTRACTION_SUMMARY_SCHEMA = {
    "required_fields": [
        "total_documents", "processed", "total_signatures",
        "total_examples", "timestamp", "documents"
    ],
    "field_types": {
        "total_documents": int,
        "processed": int,
        "total_signatures": int,
        "total_examples": int,
        "timestamp": str,
        "documents": list
    }
}


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

def validate_json_file(file_path: Path) -> tuple[bool, List[str]]:
    """Validate a single JSON file exists and is valid JSON."""
    errors = []

    if not file_path.exists():
        return False, [f"❌ File not found: {file_path}"]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, []
    except json.JSONDecodeError as e:
        return False, [f"❌ Invalid JSON in {file_path.name}: {e}"]
    except Exception as e:
        return False, [f"❌ Error reading {file_path.name}: {e}"]


def validate_directory_structure(output_dir: Path) -> Dict[str, any]:
    """
    Validate the entire output directory structure.

    Returns:
        Dict with validation results and statistics
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {
            "analysis_files": 0,
            "valid_analysis_files": 0,
            "summary_exists": False,
            "summary_valid": False,
            "orphaned_files": []
        }
    }

    # Check output directory exists
    if not output_dir.exists():
        results["valid"] = False
        results["errors"].append(f"❌ Output directory not found: {output_dir}")
        return results

    if not output_dir.is_dir():
        results["valid"] = False
        results["errors"].append(f"❌ Not a directory: {output_dir}")
        return results

    # Find all analysis files
    analysis_files = list(output_dir.glob("*_analysis.json"))
    results["stats"]["analysis_files"] = len(analysis_files)

    # Validate each analysis file
    valid_analysis_files = set()
    for analysis_file in analysis_files:
        is_valid, errors = validate_json_file(analysis_file)

        if is_valid:
            results["stats"]["valid_analysis_files"] += 1
            valid_analysis_files.add(analysis_file.name)
        else:
            results["valid"] = False
            results["errors"].extend(errors)

    # Check for extraction_summary.json
    summary_file = output_dir / "extraction_summary.json"

    if summary_file.exists():
        results["stats"]["summary_exists"] = True

        # Validate summary file
        is_valid, errors = validate_json_file(summary_file)

        if is_valid:
            results["stats"]["summary_valid"] = True

            # Load summary and check references
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)

                # Check summary metadata
                total_docs = summary_data.get("total_documents", 0)
                processed = summary_data.get("processed", 0)
                documents = summary_data.get("documents", [])

                # Check counts match
                if len(documents) != processed:
                    results["warnings"].append(
                        f"⚠️  Summary 'processed' count ({processed}) doesn't match "
                        f"documents array length ({len(documents)})"
                    )

                if processed != len(analysis_files):
                    results["warnings"].append(
                        f"⚠️  Summary processed count ({processed}) doesn't match "
                        f"analysis files found ({len(analysis_files)})"
                    )

                # Check all documents reference valid pages
                referenced_pages = set()
                for idx, doc in enumerate(documents):
                    page = doc.get("page", "")
                    if page:
                        referenced_pages.add(page)
                    else:
                        results["warnings"].append(
                            f"⚠️  Document [{idx}] in summary has no 'page' field"
                        )

                # Check for orphaned analysis files (files not in summary)
                analysis_pages = {f.stem.replace("_analysis", "") + ".md"
                                for f in analysis_files}
                orphaned = analysis_pages - referenced_pages

                if orphaned:
                    results["stats"]["orphaned_files"] = list(orphaned)
                    results["warnings"].append(
                        f"⚠️  Found {len(orphaned)} analysis files not referenced in summary: "
                        f"{', '.join(list(orphaned)[:3])}"
                    )

            except Exception as e:
                results["errors"].append(f"❌ Error validating summary content: {e}")
                results["valid"] = False
        else:
            results["valid"] = False
            results["errors"].extend(errors)
    else:
        results["warnings"].append("⚠️  extraction_summary.json not found")

    # Check for unexpected files
    all_json_files = list(output_dir.glob("*.json"))
    expected_files = set([f.name for f in analysis_files] + ["extraction_summary.json"])
    unexpected_files = [f.name for f in all_json_files if f.name not in expected_files]

    if unexpected_files:
        results["warnings"].append(
            f"⚠️  Found {len(unexpected_files)} unexpected JSON files: "
            f"{', '.join(unexpected_files[:3])}"
        )

    return results


def print_validation_report(results: Dict[str, any], output_dir: Path):
    """Print a formatted validation report."""
    print("\n" + "="*80)
    print("📊 EXTRACTION OUTPUT DIRECTORY VALIDATION REPORT")
    print("="*80)
    print(f"Directory: {output_dir}")
    print()

    # Statistics
    stats = results["stats"]
    print("📈 Statistics:")
    print(f"   Analysis files found: {stats['analysis_files']}")
    print(f"   Valid analysis files: {stats['valid_analysis_files']}")
    print(f"   Summary file exists: {'✅ Yes' if stats['summary_exists'] else '❌ No'}")
    print(f"   Summary file valid: {'✅ Yes' if stats['summary_valid'] else '❌ No'}")

    if stats['orphaned_files']:
        print(f"   Orphaned files: {len(stats['orphaned_files'])}")

    print()

    # Errors
    if results["errors"]:
        print("❌ ERRORS:")
        for error in results["errors"]:
            print(f"   {error}")
        print()

    # Warnings
    if results["warnings"]:
        print("⚠️  WARNINGS:")
        for warning in results["warnings"]:
            print(f"   {warning}")
        print()

    # Overall status
    if results["valid"] and not results["errors"]:
        print("✅ OVERALL STATUS: VALID")
        if results["warnings"]:
            print("   (with warnings)")
    else:
        print("❌ OVERALL STATUS: INVALID")

    print("="*80 + "\n")


# ============================================================================
# HOOK ENTRY POINT
# ============================================================================

def main():
    """
    Main hook entry point.

    Reads EXTRACTION_OUTPUT_DIR environment variable to find the output directory.
    Validates the entire directory structure after extraction completes.
    """
    try:
        # Get output directory from environment variable
        output_dir_str = os.getenv("EXTRACTION_OUTPUT_DIR")

        if not output_dir_str:
            # Silent exit - no output directory configured
            sys.exit(0)

        output_dir = Path(output_dir_str)

        # Validate directory structure
        results = validate_directory_structure(output_dir)

        # Only print report if there are errors or warnings
        if results["errors"] or results["warnings"]:
            print_validation_report(results, output_dir)

        # Exit based on validation results
        if results["valid"]:
            sys.exit(0)  # Success
        else:
            # Exit code 2 = BLOCK - critical validation failure
            sys.exit(2)  # Validation failed - block

    except Exception as e:
        print(f"❌ Directory validation hook error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
