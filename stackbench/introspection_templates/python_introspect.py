#!/usr/bin/env python3
"""
Python Library Introspection Script - Language-agnostic output format.

This script introspects a Python library and outputs a standardized JSON format
that works across all languages (Python, JavaScript, TypeScript, etc.).

Usage:
    python python_introspect.py <library_name> <version> [modules...]

Output (stdout):
    {
      "library": "lancedb",
      "version": "0.25.2",
      "language": "python",
      "total_apis": 118,
      "apis": [...],
      "by_type": {...}
    }
"""

import sys
import json
import importlib
import inspect
from typing import Any, Dict, List


def is_deprecated(obj: Any) -> bool:
    """Check if an API is deprecated."""
    if hasattr(obj, '__deprecated__'):
        return True

    docstring = getattr(obj, '__doc__', '')
    if docstring and any(word in docstring.lower() for word in ['deprecated', 'deprecation']):
        return True

    return False


def introspect_module(module_name: str, parent_path: str = "", depth: int = 0, max_depth: int = 3) -> List[Dict[str, Any]]:
    """
    Recursively introspect a module to find all public APIs.

    Returns list of API dictionaries in standardized format.
    """
    apis = []

    if depth > max_depth:
        return apis

    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        print(f"ERROR: Failed to import {module_name}: {e}", file=sys.stderr)
        return apis

    # Get __all__ if defined
    all_names = getattr(module, '__all__', None)

    # Iterate through module members
    for name, obj in inspect.getmembers(module):
        # Skip private members unless in __all__
        if name.startswith('_') and (not all_names or name not in all_names):
            continue

        # Skip imported modules from other packages
        if inspect.ismodule(obj):
            obj_module = getattr(obj, '__module__', '')
            if not obj_module.startswith(module_name.split('.')[0]):
                continue
            # Recursively introspect submodules
            sub_apis = introspect_module(f"{module_name}.{name}", f"{parent_path}.{name}" if parent_path else name, depth + 1, max_depth)
            apis.extend(sub_apis)
            continue

        full_name = f"{parent_path}.{name}" if parent_path else name
        in_all = all_names is not None and name in all_names

        # Extract signature if available
        signature_str = ""
        try:
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                sig = inspect.signature(obj)
                signature_str = str(sig)
        except Exception:
            pass

        # Handle functions
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            apis.append({
                "api": full_name,
                "module": module_name,
                "type": "function",
                "is_async": inspect.iscoroutinefunction(obj),
                "has_docstring": bool(obj.__doc__),
                "in_all": in_all,
                "is_deprecated": is_deprecated(obj),
                "signature": signature_str
            })

        # Handle classes
        elif inspect.isclass(obj):
            # Add class itself
            apis.append({
                "api": full_name,
                "module": module_name,
                "type": "class",
                "is_async": False,
                "has_docstring": bool(obj.__doc__),
                "in_all": in_all,
                "is_deprecated": is_deprecated(obj),
                "signature": f"class {name}"
            })

            # Add class methods
            for method_name, method_obj in inspect.getmembers(obj, inspect.isfunction):
                if not method_name.startswith('_') or method_name in ['__init__', '__call__']:
                    method_full_name = f"{full_name}.{method_name}"
                    method_sig = ""
                    try:
                        method_sig = str(inspect.signature(method_obj))
                    except Exception:
                        pass

                    apis.append({
                        "api": method_full_name,
                        "module": module_name,
                        "type": "method",
                        "is_async": inspect.iscoroutinefunction(method_obj),
                        "has_docstring": bool(method_obj.__doc__),
                        "in_all": False,
                        "is_deprecated": is_deprecated(method_obj),
                        "signature": method_sig
                    })

    return apis


def main():
    """Main introspection logic."""
    if len(sys.argv) < 3:
        print("Usage: python python_introspect.py <library_name> <version> [modules...]", file=sys.stderr)
        sys.exit(1)

    library_name = sys.argv[1]
    version = sys.argv[2]
    modules = sys.argv[3:] if len(sys.argv) > 3 else [library_name]

    # Introspect all specified modules
    all_apis = []
    for module_name in modules:
        apis = introspect_module(module_name)
        all_apis.extend(apis)

    # Group by type
    by_type = {}
    for api in all_apis:
        api_type = api['type']
        by_type[api_type] = by_type.get(api_type, 0) + 1

    # Build standardized output
    output = {
        "library": library_name,
        "version": version,
        "language": "python",
        "total_apis": len(all_apis),
        "apis": all_apis,
        "by_type": by_type,
        "deprecated_count": sum(1 for a in all_apis if a.get('is_deprecated', False))
    }

    # Output JSON to stdout
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
