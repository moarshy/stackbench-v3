#!/usr/bin/env python3
"""
Markdown API Matcher - Fast deterministic fuzzy matching for API discovery in docs.

This script scans all markdown files in a documentation folder and finds API references
using pattern matching. Outputs a JSON mapping of APIs to their documentation locations.

Usage:
    python markdown_api_matcher.py <docs_folder> <api_list_file> <output_file> [language]

Inputs:
    - docs_folder: Path to documentation root
    - api_list_file: JSON file with list of APIs to search for (api_surface.json format)
    - output_file: Where to write matches JSON
    - language: Optional language hint (python, javascript, typescript)

Output:
    {
      "api_name": {
        "documented": true,
        "reference_count": 5,
        "files": ["quickstart.md", "api.md"],
        "references": [
          {
            "file": "quickstart.md",
            "line": 42,
            "context": "import mylib",
            "match_type": "import",
            "matched_variant": "mylib",
            "in_code_block": true
          }
        ]
      }
    }
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any


def normalize_api_name(name: str) -> str:
    """Normalize API name for matching (handle snake_case <-> camelCase)."""
    return name.lower().replace('_', '').replace('.', '')


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.capitalize() for x in components[1:])


def generate_variants(api: str) -> Set[str]:
    """
    Generate naming variants for an API.

    Examples:
        "mylib.create_table" -> ["mylib.create_table", "mylib.createTable", "create_table", "createTable"]
        "Table.add_data" -> ["Table.add_data", "Table.addData", "add_data", "addData"]
    """
    variants = {api}

    # Snake case to camel case conversion
    parts = api.split('.')
    for i, part in enumerate(parts):
        if '_' in part:
            camel = snake_to_camel(part)
            parts_copy = parts.copy()
            parts_copy[i] = camel
            variants.add('.'.join(parts_copy))

    # Add without module prefix (last component only)
    if '.' in api:
        last_component = api.split('.')[-1]
        variants.add(last_component)
        if '_' in last_component:
            variants.add(snake_to_camel(last_component))

    return variants


def detect_match_type(line: str, api_variant: str, language: str) -> str:
    """Determine the type of API match in the line."""
    line_lower = line.lower()
    api_lower = api_variant.lower()

    # Import patterns
    if language == "python":
        if re.search(rf'\bimport\s+\w*{re.escape(api_lower)}\w*', line, re.IGNORECASE):
            return "import"
        if re.search(rf'\bfrom\s+\w*{re.escape(api_lower)}\w*\s+import', line, re.IGNORECASE):
            return "import"
    elif language in ["javascript", "typescript"]:
        if re.search(rf"require\s*\(\s*['\"].*{re.escape(api_lower)}.*['\"]\s*\)", line, re.IGNORECASE):
            return "import"
        if re.search(rf"import\s+.*\bfrom\s+['\"].*{re.escape(api_lower)}.*['\"]", line, re.IGNORECASE):
            return "import"

    # Function call patterns
    if re.search(rf'\b{re.escape(api_lower)}\s*\(', line, re.IGNORECASE):
        return "function_call"

    # Method call patterns
    if re.search(rf'\.\s*{re.escape(api_lower)}\s*\(', line, re.IGNORECASE):
        return "method_call"

    # Type annotation (TS/Python)
    if ':' in line and re.search(rf':\s*\w*{re.escape(api_lower)}\w*', line, re.IGNORECASE):
        return "type_annotation"

    # Class instantiation
    if re.search(rf'\bnew\s+{re.escape(api_lower)}\s*\(', line, re.IGNORECASE):
        return "class_instantiation"

    # Generic mention
    if api_lower in line_lower:
        return "mention"

    return "mention"


def is_in_code_block(line: str, in_code_block_state: bool) -> tuple[bool, bool]:
    """
    Check if line is in a code block.

    Returns: (is_in_code, new_state)
    """
    # Check for code fence markers
    if line.strip().startswith('```'):
        return True, not in_code_block_state

    # Check for indented code (4 spaces or tab)
    if line.startswith('    ') or line.startswith('\t'):
        return True, in_code_block_state

    # Check for inline code
    if '`' in line:
        return True, in_code_block_state

    return in_code_block_state, in_code_block_state


def scan_markdown_file(
    file_path: Path,
    apis_to_find: List[str],
    api_variants_map: Dict[str, Set[str]],
    language: str,
    docs_folder: Path
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scan a single markdown file for API references.

    Returns:
        Dict mapping API name to list of references found
    """
    matches = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"ERROR: Failed to read {file_path}: {e}", file=sys.stderr)
        return matches

    in_code_block = False

    # Track which APIs we've found to avoid duplicates on same line
    for line_num, line in enumerate(lines, 1):
        # Update code block state
        is_code, in_code_block = is_in_code_block(line, in_code_block)

        for api in apis_to_find:
            variants = api_variants_map[api]

            for variant in variants:
                # Case-insensitive search
                if variant.lower() in line.lower():
                    match_type = detect_match_type(line, variant, language)

                    # Extract context (trim whitespace)
                    context = line.strip()
                    if len(context) > 100:
                        context = context[:97] + "..."

                    # Get relative path
                    try:
                        relative_path = str(file_path.relative_to(docs_folder))
                    except ValueError:
                        relative_path = str(file_path)

                    reference = {
                        "file": relative_path,
                        "line": line_num,
                        "context": context,
                        "match_type": match_type,
                        "matched_variant": variant,
                        "in_code_block": is_code
                    }

                    if api not in matches:
                        matches[api] = []

                    # Avoid duplicate references on same line
                    if not any(ref['line'] == line_num and ref['file'] == reference['file'] for ref in matches[api]):
                        matches[api].append(reference)

                    break  # Found a match, no need to check other variants for this API on this line

    return matches


def scan_all_markdown_files(docs_folder: Path, apis_to_find: List[str], language: str) -> Dict[str, Any]:
    """
    Recursively scan all markdown files in docs folder.

    Returns:
        Dict with API match results
    """
    # Generate variants for all APIs
    api_variants_map = {api: generate_variants(api) for api in apis_to_find}

    all_matches = {}
    markdown_files = list(docs_folder.rglob("*.md"))

    print(f"Scanning {len(markdown_files)} markdown files in {docs_folder}...", file=sys.stderr)

    for md_file in markdown_files:
        file_matches = scan_markdown_file(md_file, apis_to_find, api_variants_map, language, docs_folder)

        # Merge matches
        for api, references in file_matches.items():
            if api not in all_matches:
                all_matches[api] = []
            all_matches[api].extend(references)

    # Build final result
    result = {}
    for api in apis_to_find:
        if api in all_matches and all_matches[api]:
            result[api] = {
                "documented": True,
                "reference_count": len(all_matches[api]),
                "references": all_matches[api],
                "files": list(set(ref['file'] for ref in all_matches[api]))
            }
        else:
            result[api] = {
                "documented": False,
                "reference_count": 0,
                "references": [],
                "files": []
            }

    return result


def main():
    """Main matching logic."""
    if len(sys.argv) < 4:
        print("Usage: python markdown_api_matcher.py <docs_folder> <api_list_file> <output_file> [language]", file=sys.stderr)
        sys.exit(1)

    docs_folder = Path(sys.argv[1])
    api_list_file = Path(sys.argv[2])
    output_file = Path(sys.argv[3])
    language = sys.argv[4] if len(sys.argv) > 4 else "python"

    if not docs_folder.exists():
        print(f"ERROR: Docs folder not found: {docs_folder}", file=sys.stderr)
        sys.exit(1)

    if not api_list_file.exists():
        print(f"ERROR: API list file not found: {api_list_file}", file=sys.stderr)
        sys.exit(1)

    # Read API list
    with open(api_list_file, 'r', encoding='utf-8') as f:
        api_data = json.load(f)
        # Support both formats: {"apis": [...]} or direct list
        if isinstance(api_data, dict) and 'apis' in api_data:
            apis_to_find = [item['api'] for item in api_data['apis']]
        elif isinstance(api_data, list):
            apis_to_find = api_data
        else:
            print("ERROR: Invalid API list format", file=sys.stderr)
            sys.exit(1)

    print(f"Searching for {len(apis_to_find)} APIs in {docs_folder}...", file=sys.stderr)

    # Scan all markdown files
    results = scan_all_markdown_files(docs_folder, apis_to_find, language)

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    documented_count = sum(1 for r in results.values() if r['documented'])
    total_references = sum(r['reference_count'] for r in results.values())

    print(f"\nMatching complete:", file=sys.stderr)
    print(f"  Total APIs: {len(apis_to_find)}", file=sys.stderr)
    print(f"  Documented: {documented_count}", file=sys.stderr)
    print(f"  Undocumented: {len(apis_to_find) - documented_count}", file=sys.stderr)
    print(f"  Total references found: {total_references}", file=sys.stderr)
    print(f"\nOutput written to: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
