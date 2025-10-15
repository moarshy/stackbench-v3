#!/usr/bin/env python3
"""
JSON Schema Validator Hook for Documentation Extraction

This hook validates JSON output files from the extraction agent to ensure
they conform to the expected Pydantic model schemas.

Hook Event: PreToolUse (blocks before write if validation fails)
Trigger: Write tool on *_analysis.json or extraction_summary.json files
"""

import json
import sys
import os
from typing import Any, List


# ============================================================================
# VALIDATION SCHEMAS (Extracted from Pydantic models)
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
    },
    "nested_schemas": {
        "signatures": {
            "required_fields": ["library", "function", "params", "param_types", "defaults", "imports", "line", "context"],
            "optional_fields": ["method_chain", "raw_code"],
            "field_types": {
                "library": str,
                "function": str,
                "method_chain": (str, type(None)),
                "params": list,
                "param_types": dict,
                "defaults": dict,
                "imports": str,
                "line": int,
                "context": str,
                "raw_code": (str, type(None))
            }
        },
        "examples": {
            "required_fields": ["library", "language", "code", "has_main", "is_executable", "line", "context", "dependencies"],
            "optional_fields": ["imports"],
            "field_types": {
                "library": str,
                "language": str,
                "code": str,
                "imports": (str, type(None)),
                "has_main": bool,
                "is_executable": bool,
                "line": int,
                "context": str,
                "dependencies": list
            }
        }
    }
}

EXTRACTION_SUMMARY_SCHEMA = {
    "required_fields": [
        "total_documents", "processed", "total_signatures",
        "total_examples", "timestamp", "documents"
    ],
    "optional_fields": [],
    "field_types": {
        "total_documents": int,
        "processed": int,
        "total_signatures": int,
        "total_examples": int,
        "timestamp": str,
        "documents": list
    },
    "nested_schemas": {
        "documents": DOCUMENT_ANALYSIS_SCHEMA
    }
}


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def validate_field_type(field_name: str, value: Any, expected_types: tuple) -> List[str]:
    """Validate that a field has the correct type."""
    errors = []
    if not isinstance(value, expected_types):
        actual_type = type(value).__name__
        expected_type_names = " or ".join(t.__name__ for t in expected_types if t is not type(None))
        errors.append(f"  ❌ Field '{field_name}': Expected type {expected_type_names}, got {actual_type}")
    return errors


def validate_nested_list(field_name: str, items: list, schema: dict, path: str = "") -> List[str]:
    """Validate a list of nested objects against a schema."""
    errors = []

    for idx, item in enumerate(items):
        item_path = f"{path}.{field_name}[{idx}]" if path else f"{field_name}[{idx}]"

        if not isinstance(item, dict):
            errors.append(f"  ❌ {item_path}: Expected dict, got {type(item).__name__}")
            continue

        # Check required fields
        for req_field in schema.get("required_fields", []):
            if req_field not in item:
                errors.append(f"  ❌ {item_path}: Missing required field '{req_field}'")

        # Check field types
        for field, value in item.items():
            if field in schema.get("field_types", {}):
                expected_type = schema["field_types"][field]
                if not isinstance(expected_type, tuple):
                    expected_type = (expected_type,)

                field_errors = validate_field_type(f"{item_path}.{field}", value, expected_type)
                errors.extend(field_errors)

    return errors


def validate_json_structure(data: dict, schema: dict, path: str = "") -> List[str]:
    """
    Validate JSON data against a schema definition.

    Args:
        data: The JSON data to validate
        schema: Schema definition with required_fields, optional_fields, field_types
        path: Current path in the data structure (for error messages)

    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []

    # Check required fields
    for field in schema.get("required_fields", []):
        if field not in data:
            field_path = f"{path}.{field}" if path else field
            errors.append(f"  ❌ Missing required field: '{field_path}'")

    # Check field types
    for field, value in data.items():
        field_path = f"{path}.{field}" if path else field

        if field in schema.get("field_types", {}):
            expected_type = schema["field_types"][field]

            # Handle union types (e.g., str | None)
            if not isinstance(expected_type, tuple):
                expected_type = (expected_type,)

            # Type check
            field_errors = validate_field_type(field_path, value, expected_type)
            errors.extend(field_errors)

            # Nested validation for lists
            if isinstance(value, list) and field in schema.get("nested_schemas", {}):
                nested_schema = schema["nested_schemas"][field]
                nested_errors = validate_nested_list(field, value, nested_schema, path)
                errors.extend(nested_errors)

    return errors


def validate_extraction_output(file_path: str) -> tuple[bool, List[str]]:
    """
    Validate an extraction output JSON file.

    Args:
        file_path: Path to the JSON file to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check file exists
    if not os.path.exists(file_path):
        return False, [f"❌ File not found: {file_path}"]

    # Read and parse JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"❌ Invalid JSON syntax: {e}"]
    except Exception as e:
        return False, [f"❌ Error reading file: {e}"]

    # Determine schema based on filename
    filename = os.path.basename(file_path)

    if filename == "extraction_summary.json":
        schema = EXTRACTION_SUMMARY_SCHEMA
        schema_name = "ExtractionSummary"
    elif filename.endswith("_analysis.json"):
        schema = DOCUMENT_ANALYSIS_SCHEMA
        schema_name = "DocumentAnalysis"
    else:
        # Unknown file type, skip validation
        return True, []

    # Validate structure
    validation_errors = validate_json_structure(data, schema)

    if validation_errors:
        errors.append(f"❌ Schema validation failed for {schema_name}:")
        errors.extend(validation_errors)
        return False, errors

    return True, []


# ============================================================================
# HOOK ENTRY POINT
# ============================================================================

def main():
    """
    Main hook entry point.

    Receives JSON input from Claude Code via stdin with format:
    {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/path/to/file.json",
            "content": "..."
        },
        "tool_output": {...}
    }
    """
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract file path
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Only validate Write operations on extraction JSON files
        if tool_name != "Write":
            sys.exit(0)  # Not a Write operation, skip

        filename = os.path.basename(file_path)
        if not (filename.endswith("_analysis.json") or filename == "extraction_summary.json"):
            sys.exit(0)  # Not an extraction file, skip

        # Check if file is in the correct output directory
        expected_output_dir = os.getenv("EXTRACTION_OUTPUT_DIR")
        if expected_output_dir:
            # Resolve absolute paths for comparison
            abs_file_path = os.path.abspath(file_path)
            abs_output_dir = os.path.abspath(expected_output_dir)
            file_dir = os.path.dirname(abs_file_path)

            # Check if file is being created in the wrong location
            if not file_dir.startswith(abs_output_dir):
                print(f"\n{'='*70}", file=sys.stderr)
                print(f"🚫 FILE LOCATION BLOCKED: {filename}", file=sys.stderr)
                print(f"{'='*70}", file=sys.stderr)
                print(f"  ❌ Files must be created in: {abs_output_dir}", file=sys.stderr)
                print(f"  ❌ Attempted location: {file_dir}", file=sys.stderr)
                print(f"  ℹ️  Please create extraction files in the extraction_output/ directory", file=sys.stderr)
                print(f"{'='*70}\n", file=sys.stderr)
                # Exit code 2 = BLOCK the operation
                sys.exit(2)

        # PreToolUse: Validate content from tool_input (before file is written)
        content = tool_input.get("content", "")
        if not content:
            # No content to validate, allow
            sys.exit(0)

        # Parse content as JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"\n{'='*70}", file=sys.stderr)
            print(f"🚫 INVALID JSON BLOCKED: {filename}", file=sys.stderr)
            print(f"{'='*70}", file=sys.stderr)
            print(f"  ❌ JSON syntax error: {e}", file=sys.stderr)
            print(f"{'='*70}\n", file=sys.stderr)
            sys.exit(2)

        # Determine schema based on filename
        if filename == "extraction_summary.json":
            schema = EXTRACTION_SUMMARY_SCHEMA
            schema_name = "ExtractionSummary"
        elif filename.endswith("_analysis.json"):
            schema = DOCUMENT_ANALYSIS_SCHEMA
            schema_name = "DocumentAnalysis"
        else:
            # Unknown file type, skip validation
            sys.exit(0)

        # Validate structure
        validation_errors = validate_json_structure(data, schema)

        is_valid = len(validation_errors) == 0
        errors = []
        if validation_errors:
            errors.append(f"❌ Schema validation failed for {schema_name}:")
            errors.extend(validation_errors)

        if is_valid:
            print(f"✅ JSON validation passed: {filename}", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"\n{'='*70}", file=sys.stderr)
            print(f"⚠️  JSON VALIDATION FAILED: {filename}", file=sys.stderr)
            print(f"{'='*70}", file=sys.stderr)
            for error in errors:
                print(error, file=sys.stderr)
            print(f"{'='*70}\n", file=sys.stderr)

            # Exit with error code to signal validation failure
            # Exit code 0 = continue, 1 = error logged but continue, 2 = block and stop
            sys.exit(2)  # Block invalid files

    except Exception as e:
        print(f"❌ Hook validation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
