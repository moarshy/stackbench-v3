"""
Utilities for working with Pydantic schemas.

Provides functions to auto-generate prompt examples and validation schemas
from Pydantic models, eliminating the need for manual schema duplication.
"""

import json
from typing import Type, Any, Dict, List, Optional, get_origin, get_args, Union
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo


def pydantic_to_json_example(
    model: Type[BaseModel],
    indent: int = 2,
    use_real_values: bool = True
) -> str:
    """
    Generate a JSON example from a Pydantic model.

    Uses field descriptions, defaults, and type hints to create realistic examples.

    Args:
        model: Pydantic model class
        indent: JSON indentation level
        use_real_values: If True, use realistic example values; if False, use generic placeholders

    Returns:
        JSON string representation of the model
    """
    example = _model_to_example_dict(model, use_real_values=use_real_values)
    return json.dumps(example, indent=indent)


def _model_to_example_dict(model: Type[BaseModel], use_real_values: bool = True) -> Dict[str, Any]:
    """Convert a Pydantic model to an example dictionary."""
    example = {}

    for field_name, field_info in model.model_fields.items():
        field_type = field_info.annotation
        default = field_info.default

        # Use default if available and not a factory
        if default is not None and not callable(default):
            example[field_name] = default
        else:
            example[field_name] = _generate_example_value(
                field_type,
                field_name,
                use_real_values=use_real_values
            )

    return example


def _generate_example_value(field_type: Any, field_name: str, use_real_values: bool = True) -> Any:
    """Generate an example value for a given type."""
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Handle Optional types
    if origin is Union:
        # Get non-None type
        non_none_types = [t for t in args if t != type(None)]
        if non_none_types:
            field_type = non_none_types[0]
            origin = get_origin(field_type)
            args = get_args(field_type)
        else:
            return None

    # Handle List types
    if origin is list or field_type == list:
        if use_real_values and 'signature' in field_name.lower():
            return [{"function": "example_function", "params": ["param1"]}]
        elif use_real_values and 'example' in field_name.lower():
            return [{"code": "print('hello')", "language": "python"}]
        elif use_real_values and 'hierarchy' in field_name.lower():
            return ["Section 1", "Subsection 1.1"]
        return []

    # Handle Dict types
    if origin is dict or field_type == dict:
        if use_real_values and 'types' in field_name.lower():
            return {"param1": "str", "param2": "int"}
        elif use_real_values and 'defaults' in field_name.lower():
            return {"param1": "null", "param2": "0"}
        return {}

    # Handle basic types
    if field_type == str:
        if use_real_values:
            if 'library' in field_name.lower():
                return "fastapi"
            elif 'function' in field_name.lower():
                return "FastAPI"
            elif 'version' in field_name.lower():
                return "0.104.1"
            elif 'language' in field_name.lower():
                return "python"
            elif 'context' in field_name.lower():
                return "Getting Started"
            elif 'anchor' in field_name.lower():
                return "#getting-started"
        return "example_string"
    elif field_type == int:
        if use_real_values:
            if 'line' in field_name.lower():
                return 45
            elif 'index' in field_name.lower():
                return 0
        return 0
    elif field_type == float:
        if use_real_values and 'score' in field_name.lower():
            return 0.95
        return 0.0
    elif field_type == bool:
        return False

    # Handle nested Pydantic models
    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        return _model_to_example_dict(field_type, use_real_values=use_real_values)

    return None


def pydantic_to_hook_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Convert Pydantic model to hook validation schema format.

    Returns dict with required_fields, optional_fields, field_types compatible
    with the existing hook validation system.

    Args:
        model: Pydantic model class

    Returns:
        Dictionary with 'required_fields', 'optional_fields', 'field_types'
    """
    required_fields = []
    optional_fields = []
    field_types = {}

    for field_name, field_info in model.model_fields.items():
        field_type = field_info.annotation
        is_required = field_info.is_required()

        # Categorize as required or optional
        if is_required:
            required_fields.append(field_name)
        else:
            optional_fields.append(field_name)

        # Convert Pydantic type to Python type for isinstance() validation
        python_type = _convert_pydantic_type_to_python(field_type)
        field_types[field_name] = python_type

    return {
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "field_types": field_types
    }


def _convert_pydantic_type_to_python(pydantic_type: Any) -> Any:
    """
    Convert Pydantic type annotation to Python type for isinstance() checking.

    Handles Optional, List, Dict, Union, and basic types.
    """
    origin = get_origin(pydantic_type)

    # Handle None type
    if pydantic_type == type(None):
        return type(None)

    # Simple types
    if origin is None:
        return pydantic_type

    # List type
    if origin is list:
        return list

    # Dict type
    if origin is dict:
        return dict

    # Union/Optional types
    if origin is Union:
        args = get_args(pydantic_type)
        # Separate None from other types
        non_none_types = tuple(
            _convert_pydantic_type_to_python(t) for t in args if t != type(None)
        )

        # If it's Optional[X], return (X, None)
        if type(None) in args:
            if len(non_none_types) == 1:
                return (non_none_types[0], type(None))
            else:
                return non_none_types + (type(None),)
        else:
            # Regular Union
            return non_none_types if len(non_none_types) > 1 else non_none_types[0]

    return pydantic_type


def validate_with_pydantic(
    data: Dict[str, Any],
    model: Type[BaseModel]
) -> tuple[bool, Optional[List[str]]]:
    """
    Validate data using Pydantic model directly.

    This is the recommended approach for validation as it leverages Pydantic's
    built-in validation instead of custom hook schemas.

    Args:
        data: Dictionary to validate
        model: Pydantic model class to validate against

    Returns:
        Tuple of (passed, errors) where passed is bool and errors is list of error messages
    """
    try:
        model(**data)
        return True, None
    except ValidationError as e:
        errors = []
        for error in e.errors():
            # Format: field_path: error_message
            loc = '.'.join(str(l) for l in error['loc'])
            msg = error['msg']
            errors.append(f"{loc}: {msg}")
        return False, errors
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


def get_nested_schema_for_list_field(
    model: Type[BaseModel],
    field_name: str
) -> Optional[Type[BaseModel]]:
    """
    Get the nested Pydantic model for a list field.

    For example, if DocumentAnalysis has a field `signatures: List[APISignature]`,
    this returns the APISignature model.

    Args:
        model: Parent Pydantic model
        field_name: Name of the list field

    Returns:
        Nested model class if it's a List[Model], None otherwise
    """
    if field_name not in model.model_fields:
        return None

    field_info = model.model_fields[field_name]
    field_type = field_info.annotation

    # Check if it's a List
    origin = get_origin(field_type)
    if origin is not list:
        return None

    # Get the type argument (what's inside the List)
    args = get_args(field_type)
    if not args:
        return None

    item_type = args[0]

    # Check if it's a Pydantic model
    if isinstance(item_type, type) and issubclass(item_type, BaseModel):
        return item_type

    return None
