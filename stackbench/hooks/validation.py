"""
Validation hooks for StackBench agents.

Converted from shell script hooks to programmatic Python hooks for better
integration, debugging, and type safety.
"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime


# ============================================================================
# VALIDATION SCHEMAS
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

API_SIGNATURE_VALIDATION_SCHEMA = {
    "required_fields": [
        "validation_id", "validated_at", "source_file", "document_page", "library", "version",
        "language", "summary", "validations", "environment", "processing_time_ms", "warnings"
    ],
    "optional_fields": [],
    "field_types": {
        "validation_id": str,
        "validated_at": str,
        "source_file": str,
        "document_page": str,
        "library": str,
        "version": str,
        "language": str,
        "summary": dict,
        "validations": list,
        "environment": dict,
        "processing_time_ms": int,
        "warnings": list
    },
    "nested_schemas": {
        "summary": {
            "required_fields": ["total_signatures", "valid", "invalid", "not_found", "error", "accuracy_score", "critical_issues", "warnings"],
            "field_types": {
                "total_signatures": int,
                "valid": int,
                "invalid": int,
                "not_found": int,
                "error": int,
                "accuracy_score": float,
                "critical_issues": int,
                "warnings": int
            }
        },
        "environment": {
            "required_fields": ["library_installed", "version_installed", "version_requested", "version_match", "python_version"],
            "optional_fields": ["installation_output"],
            "field_types": {
                "library_installed": str,
                "version_installed": str,
                "version_requested": str,
                "version_match": bool,
                "python_version": str,
                "installation_output": (str, type(None))
            }
        },
        "validations": {
            "required_fields": ["signature_id", "function", "library", "status", "documented", "issues", "confidence"],
            "optional_fields": ["method_chain", "actual"],
            "field_types": {
                "signature_id": str,
                "function": str,
                "method_chain": (str, type(None)),
                "library": str,
                "status": str,
                "documented": dict,
                "actual": (dict, type(None)),
                "issues": list,
                "confidence": float
            }
        }
    }
}

CODE_EXAMPLE_VALIDATION_SCHEMA = {
    "required_fields": [
        "page", "library", "version", "language", "validation_timestamp",
        "results", "total_examples", "successful", "failed", "skipped"
    ],
    "optional_fields": [],
    "field_types": {
        "page": str,
        "library": str,
        "version": str,
        "language": str,
        "validation_timestamp": str,
        "results": list,
        "total_examples": int,
        "successful": int,
        "failed": int,
        "skipped": int
    },
    "nested_schemas": {
        "results": {
            "required_fields": ["example_index", "line", "context", "code", "status", "depends_on_previous"],
            "optional_fields": ["error_message", "suggestions", "execution_output"],
            "field_types": {
                "example_index": int,
                "line": int,
                "context": str,
                "code": str,
                "status": str,
                "error_message": (str, type(None)),
                "suggestions": (str, type(None)),
                "execution_output": (str, type(None)),
                "depends_on_previous": bool
            }
        }
    }
}


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_field_type(field_name: str, value: Any, expected_types: tuple) -> List[str]:
    """Validate that a field has the correct type."""
    errors = []
    if not isinstance(value, expected_types):
        actual_type = type(value).__name__
        expected_type_names = " or ".join(t.__name__ for t in expected_types if t is not type(None))
        errors.append(f"Field '{field_name}': Expected type {expected_type_names}, got {actual_type}")
    return errors


def validate_nested_list(field_name: str, items: list, schema: dict, path: str = "") -> List[str]:
    """Validate a list of nested objects against a schema."""
    errors = []

    for idx, item in enumerate(items):
        item_path = f"{path}.{field_name}[{idx}]" if path else f"{field_name}[{idx}]"

        if not isinstance(item, dict):
            errors.append(f"{item_path}: Expected dict, got {type(item).__name__}")
            continue

        # Check required fields
        for req_field in schema.get("required_fields", []):
            if req_field not in item:
                errors.append(f"{item_path}: Missing required field '{req_field}'")

        # Check field types
        for field, value in item.items():
            if field in schema.get("field_types", {}):
                expected_type = schema["field_types"][field]
                if not isinstance(expected_type, tuple):
                    expected_type = (expected_type,)

                field_errors = validate_field_type(f"{item_path}.{field}", value, expected_type)
                errors.extend(field_errors)

    return errors


def validate_nested_dict(field_name: str, data: dict, schema: dict, path: str = "") -> List[str]:
    """Validate a nested dictionary against a schema."""
    errors = []
    item_path = f"{path}.{field_name}" if path else field_name

    if not isinstance(data, dict):
        errors.append(f"{item_path}: Expected dict, got {type(data).__name__}")
        return errors

    # Check required fields
    for req_field in schema.get("required_fields", []):
        if req_field not in data:
            errors.append(f"{item_path}: Missing required field '{req_field}'")

    # Check field types
    for field, value in data.items():
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
            errors.append(f"Missing required field: '{field_path}'")

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

            # Nested validation for dicts
            if isinstance(value, dict) and field in schema.get("nested_schemas", {}):
                nested_schema = schema["nested_schemas"][field]
                nested_errors = validate_nested_dict(field, value, nested_schema, path)
                errors.extend(nested_errors)

            # Nested validation for lists
            elif isinstance(value, list) and field in schema.get("nested_schemas", {}):
                nested_schema = schema["nested_schemas"][field]
                nested_errors = validate_nested_list(field, value, nested_schema, path)
                errors.extend(nested_errors)

    return errors


# ============================================================================
# TRACKING UTILITIES
# ============================================================================

def log_validation_call(
    log_dir: Path,
    hook_type: str,
    filename: str,
    passed: bool,
    errors: Optional[List[str]] = None,
    reason: Optional[str] = None
):
    """
    Log validation hook call to a text file for tracking.

    Args:
        log_dir: Directory to store validation logs
        hook_type: Type of hook (extraction_validation or validation_output)
        filename: Name of file being validated
        passed: Whether validation passed
        errors: List of validation errors (if any)
        reason: Reason for failure (if any)
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{hook_type}_calls.txt"

        timestamp = datetime.now().isoformat()
        status = "✅ PASSED" if passed else "❌ FAILED"

        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Hook Type: {hook_type}\n")
            f.write(f"File: {filename}\n")
            f.write(f"Status: {status}\n")

            if not passed:
                f.write(f"\nReason: {reason}\n")
                if errors:
                    f.write(f"\nValidation Errors:\n")
                    for error in errors:
                        f.write(f"  - {error}\n")

            f.write(f"{'='*80}\n")

    except Exception as e:
        # Don't let logging errors break the hook
        print(f"⚠️  Failed to log validation call: {e}")


# ============================================================================
# DIRECT VALIDATION HELPERS
# ============================================================================

def validate_extraction_json(
    data: dict,
    filename: str,
    log_dir: Optional[Path] = None
) -> tuple[bool, Optional[List[str]]]:
    """
    Validate extraction JSON data directly (not via hook).

    Args:
        data: The JSON data to validate
        filename: Name of the file being validated
        log_dir: Optional directory to log validation calls

    Returns:
        Tuple of (passed, errors) where passed is bool and errors is list of error messages
    """
    # Validate structure
    errors = validate_json_structure(data, DOCUMENT_ANALYSIS_SCHEMA)

    passed = len(errors) == 0

    # Log validation call
    if log_dir:
        log_validation_call(
            log_dir,
            "extraction_validation",
            filename,
            passed,
            errors=errors if errors else None,
            reason="Schema validation failed" if errors else None
        )

    return passed, errors if errors else None


def validate_validation_output_json(
    data: dict,
    filename: str,
    log_dir: Optional[Path] = None,
    validation_type: str = "validation_output"
) -> tuple[bool, Optional[List[str]]]:
    """
    Validate API/code validation JSON data directly (not via hook).

    Args:
        data: The JSON data to validate
        filename: Name of the file being validated
        log_dir: Optional directory to log validation calls
        validation_type: Type of validation (api_signature_validation or code_example_validation)

    Returns:
        Tuple of (passed, errors) where passed is bool and errors is list of error messages
    """
    # Select appropriate schema based on validation type
    if validation_type == "api_signature_validation":
        schema = API_SIGNATURE_VALIDATION_SCHEMA
    elif validation_type == "code_example_validation":
        schema = CODE_EXAMPLE_VALIDATION_SCHEMA
    else:
        # Default to API schema for backward compatibility
        schema = API_SIGNATURE_VALIDATION_SCHEMA

    # Validate structure
    errors = validate_json_structure(data, schema)

    passed = len(errors) == 0

    # Log validation call
    if log_dir:
        log_validation_call(
            log_dir,
            validation_type,
            filename,
            passed,
            errors=errors if errors else None,
            reason="Schema validation failed" if errors else None
        )

    return passed, errors if errors else None


# ============================================================================
# HOOK FACTORIES
# ============================================================================

def create_extraction_validation_hook(output_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
    """
    Create a PreToolUse hook that validates extraction JSON output.

    Args:
        output_dir: Optional expected output directory for location validation
        log_dir: Optional directory to log validation calls

    Returns:
        Async hook function
    """
    async def extraction_validation_hook(
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],  # noqa: ARG001 - Required by hook signature
        context: Any  # noqa: ARG001 - Required by hook signature
    ) -> Dict[str, Any]:
        """Validate extraction JSON before writing."""
        try:
            tool_name = input_data.get('tool_name', '')
            tool_input = input_data.get('tool_input', {})
            file_path = tool_input.get('file_path', '')

            # Only validate Write operations on extraction JSON files
            if tool_name != 'Write':
                return {}

            filename = Path(file_path).name
            if not (filename.endswith('_analysis.json') or filename == 'extraction_summary.json'):
                return {}

            # Validate output directory if specified
            if output_dir:
                abs_file_path = Path(file_path).resolve()
                abs_output_dir = output_dir.resolve()
                file_dir = abs_file_path.parent

                if not str(file_dir).startswith(str(abs_output_dir)):
                    reason = f"Files must be created in {abs_output_dir}, not {file_dir}"

                    # Log validation failure
                    if log_dir:
                        log_validation_call(log_dir, "extraction_validation", filename, False, reason=reason)

                    return {
                        'hookSpecificOutput': {
                            'hookEventName': 'PreToolUse',
                            'permissionDecision': 'deny',
                            'permissionDecisionReason': reason
                        }
                    }

            # Validate JSON content
            content = tool_input.get('content', '')
            if not content:
                return {}

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                reason = f"Invalid JSON: {e}"

                # Log validation failure
                if log_dir:
                    log_validation_call(log_dir, "extraction_validation", filename, False, reason=reason)

                return {
                    'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': reason
                    }
                }

            # Select schema
            schema = DOCUMENT_ANALYSIS_SCHEMA

            # Validate structure
            errors = validate_json_structure(data, schema)

            if errors:
                error_msg = f"Schema validation failed: {'; '.join(errors[:3])}"

                # Log validation failure
                if log_dir:
                    log_validation_call(log_dir, "extraction_validation", filename, False, errors=errors, reason="Schema validation failed")

                return {
                    'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': error_msg
                    }
                }

            # Validation passed - log success
            if log_dir:
                log_validation_call(log_dir, "extraction_validation", filename, True)

            return {}  # Validation passed

        except Exception as e:
            # Log error but don't block
            print(f"⚠️  Validation hook error: {e}")
            if log_dir:
                log_validation_call(log_dir, "extraction_validation", filename or "unknown", False, reason=f"Hook error: {e}")
            return {}

    return extraction_validation_hook


def create_validation_output_hook(output_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
    """
    Create a PreToolUse hook that validates API/code validation JSON output.

    Args:
        output_dir: Optional expected output directory for location validation
        log_dir: Optional directory to log validation calls

    Returns:
        Async hook function
    """
    async def validation_output_hook(
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],  # noqa: ARG001 - Required by hook signature
        context: Any  # noqa: ARG001 - Required by hook signature
    ) -> Dict[str, Any]:
        """Validate validation JSON before writing."""
        try:
            tool_name = input_data.get('tool_name', '')
            tool_input = input_data.get('tool_input', {})
            file_path = tool_input.get('file_path', '')

            # Only validate Write operations on validation JSON files
            if tool_name != 'Write':
                return {}

            filename = Path(file_path).name
            if not filename.endswith('_validation.json'):
                return {}

            # Validate output directory if specified
            if output_dir:
                abs_file_path = Path(file_path).resolve()
                abs_output_dir = output_dir.resolve()
                file_dir = abs_file_path.parent

                if not str(file_dir).startswith(str(abs_output_dir)):
                    reason = f"Files must be created in {abs_output_dir}, not {file_dir}"

                    # Log validation failure
                    if log_dir:
                        log_validation_call(log_dir, "validation_output", filename, False, reason=reason)

                    return {
                        'hookSpecificOutput': {
                            'hookEventName': 'PreToolUse',
                            'permissionDecision': 'deny',
                            'permissionDecisionReason': reason
                        }
                    }

            # Validate JSON content
            content = tool_input.get('content', '')
            if not content:
                return {}

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                reason = f"Invalid JSON: {e}"

                # Log validation failure
                if log_dir:
                    log_validation_call(log_dir, "validation_output", filename, False, reason=reason)

                return {
                    'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': reason
                    }
                }

            # Validate structure
            errors = validate_json_structure(data, VALIDATION_OUTPUT_SCHEMA)

            if errors:
                error_msg = f"Schema validation failed: {'; '.join(errors[:3])}"

                # Log validation failure
                if log_dir:
                    log_validation_call(log_dir, "validation_output", filename, False, errors=errors, reason="Schema validation failed")

                return {
                    'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': error_msg
                    }
                }

            # Validation passed - log success
            if log_dir:
                log_validation_call(log_dir, "validation_output", filename, True)

            return {}  # Validation passed

        except Exception as e:
            # Log error but don't block
            print(f"⚠️  Validation hook error: {e}")
            if log_dir:
                log_validation_call(log_dir, "validation_output", filename or "unknown", False, reason=f"Hook error: {e}")
            return {}

    return validation_output_hook
