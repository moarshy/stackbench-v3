"""
API Example Matcher - Links code examples to library APIs.

Analyzes code examples to determine which APIs they demonstrate.
Builds bi-directional mappings (API → Examples, Example → APIs) and
infers complexity levels for ranking and organization.
"""

import re
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import logging

from stackbench.readme_llm.schemas import CodeExample, IntrospectionResult

logger = logging.getLogger(__name__)


class APIExampleMatcher:
    """
    Match code examples to library APIs using import and usage analysis.

    Handles multiple programming languages with language-specific patterns
    for import detection, function calls, and method chaining.
    """

    def __init__(self, introspection_result: IntrospectionResult):
        """
        Initialize API matcher with introspection data.

        Args:
            introspection_result: Introspected library API surface
        """
        self.introspection = introspection_result
        self.language = introspection_result.language

        # Build API lookup structures
        self.api_names = {api["api"] for api in introspection_result.apis}
        self.api_by_name = {api["api"]: api for api in introspection_result.apis}

        # Extract just the function/class names for simpler matching
        self.simple_api_names = set()
        for api_full_name in self.api_names:
            # Get last component (e.g., "connect" from "lancedb.connect")
            parts = api_full_name.split('.')
            if len(parts) > 0:
                self.simple_api_names.add(parts[-1])

        logger.debug(f"Initialized matcher with {len(self.api_names)} APIs")

    def match_examples(self, examples: List[CodeExample]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Match code examples to APIs.

        Args:
            examples: List of CodeExample objects

        Returns:
            Tuple of (api_to_examples, example_to_apis):
            - api_to_examples: Maps API names to example IDs
            - example_to_apis: Maps example IDs to API names
        """
        api_to_examples = defaultdict(list)
        example_to_apis = defaultdict(list)

        for example in examples:
            matched_apis = self._match_example_to_apis(example)

            for api_name in matched_apis:
                api_to_examples[api_name].append(example.example_id)
                example_to_apis[example.example_id].append(api_name)

        logger.info(
            f"Matched {len(examples)} examples to {len(api_to_examples)} APIs"
        )

        return dict(api_to_examples), dict(example_to_apis)

    def _match_example_to_apis(self, example: CodeExample) -> Set[str]:
        """
        Match a single example to APIs.

        Args:
            example: CodeExample object

        Returns:
            Set of matched API names
        """
        matched_apis = set()

        # Language-specific matching
        if self.language == 'python':
            matched_apis = self._match_python(example.code)
        elif self.language in ('typescript', 'javascript'):
            matched_apis = self._match_typescript_javascript(example.code)
        elif self.language == 'go':
            matched_apis = self._match_go(example.code)
        elif self.language == 'rust':
            matched_apis = self._match_rust(example.code)

        # Filter to only known APIs
        matched_apis = {api for api in matched_apis if api in self.api_names}

        logger.debug(f"Example {example.example_id}: matched {len(matched_apis)} APIs")

        return matched_apis

    def _match_python(self, code: str) -> Set[str]:
        """
        Match Python code to APIs.

        Detects:
        - import statements (import X, from X import Y)
        - Function calls (module.function(), Class.method())
        - Method chaining (obj.method1().method2())
        """
        matched = set()

        # 1. Extract imports
        import_pattern = r'^\s*(?:from\s+(\S+)\s+)?import\s+([^\n]+)'
        for match in re.finditer(import_pattern, code, re.MULTILINE):
            from_module = match.group(1)
            import_items = match.group(2)

            if from_module:
                # from lancedb import connect, Table
                for item in re.split(r'[,\s]+', import_items):
                    item = item.strip()
                    if item and not item.startswith('('):
                        # Check both module.item and just item
                        matched.add(f"{from_module}.{item}")
                        matched.add(item)
            else:
                # import lancedb
                for item in re.split(r'[,\s]+', import_items):
                    item = item.strip()
                    if item and not item.startswith('('):
                        matched.add(item)

        # 2. Extract function/method calls
        call_pattern = r'([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\('
        for match in re.finditer(call_pattern, code):
            call_chain = match.group(1)

            # Add full chain and components
            matched.add(call_chain)

            # Also add individual components
            parts = call_chain.split('.')
            for i in range(len(parts)):
                matched.add('.'.join(parts[:i+1]))

        return matched

    def _match_typescript_javascript(self, code: str) -> Set[str]:
        """
        Match TypeScript/JavaScript code to APIs.

        Detects:
        - ES6 imports (import X from 'lib', import { A, B } from 'lib')
        - CommonJS requires (const X = require('lib'))
        - Function calls and method chaining
        """
        matched = set()

        # 1. ES6 imports
        # import { connect, Table } from 'lancedb'
        es6_pattern = r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(es6_pattern, code):
            items = match.group(1)
            module = match.group(2)

            for item in re.split(r'[,\s]+', items):
                item = item.strip()
                if item and item != 'type':
                    matched.add(f"{module}.{item}")
                    matched.add(item)

        # import lancedb from 'lancedb'
        es6_default_pattern = r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(es6_default_pattern, code):
            name = match.group(1)
            module = match.group(2)
            matched.add(module)
            matched.add(name)

        # 2. CommonJS requires
        require_pattern = r'(?:const|let|var)\s+(?:\{([^}]+)\}|(\w+))\s*=\s*require\([\'"]([^\'"]+)[\'"]\)'
        for match in re.finditer(require_pattern, code):
            destructured = match.group(1)
            simple = match.group(2)
            module = match.group(3)

            if destructured:
                for item in re.split(r'[,\s]+', destructured):
                    item = item.strip()
                    if item:
                        matched.add(f"{module}.{item}")
                        matched.add(item)
            elif simple:
                matched.add(module)
                matched.add(simple)

        # 3. Function/method calls
        call_pattern = r'([a-zA-Z_$][a-zA-Z0-9_$\.]*)\s*\('
        for match in re.finditer(call_pattern, code):
            call_chain = match.group(1)
            matched.add(call_chain)

            parts = call_chain.split('.')
            for i in range(len(parts)):
                matched.add('.'.join(parts[:i+1]))

        return matched

    def _match_go(self, code: str) -> Set[str]:
        """
        Match Go code to APIs.

        Detects:
        - import statements
        - Package.Function calls
        - Method calls
        """
        matched = set()

        # 1. Extract imports
        import_pattern = r'import\s+(?:"([^"]+)"|(\w+)\s+"([^"]+)")'
        for match in re.finditer(import_pattern, code):
            pkg = match.group(1) or match.group(3)
            alias = match.group(2)

            if pkg:
                matched.add(pkg)
            if alias:
                matched.add(alias)

        # 2. Function calls (Package.Function or variable.Method)
        call_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\('
        for match in re.finditer(call_pattern, code):
            call_chain = match.group(1)
            matched.add(call_chain)

            parts = call_chain.split('.')
            for i in range(len(parts)):
                matched.add('.'.join(parts[:i+1]))

        return matched

    def _match_rust(self, code: str) -> Set[str]:
        """
        Match Rust code to APIs.

        Detects:
        - use statements
        - Module::function calls
        - Method calls
        """
        matched = set()

        # 1. Extract use statements
        use_pattern = r'use\s+([a-zA-Z_][a-zA-Z0-9_:]*(?:::\{[^}]+\})?)'
        for match in re.finditer(use_pattern, code):
            use_path = match.group(1)

            # Handle use crate::{A, B, C}
            if '::' in use_path and '{' in use_path:
                base = use_path.split('::')[0]
                items_match = re.search(r'\{([^}]+)\}', use_path)
                if items_match:
                    items = items_match.group(1)
                    for item in re.split(r'[,\s]+', items):
                        item = item.strip()
                        if item:
                            matched.add(f"{base}::{item}")
                            matched.add(item)
            else:
                matched.add(use_path)

        # 2. Function calls (module::function or variable.method)
        call_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:::[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\('
        for match in re.finditer(call_pattern, code):
            call_chain = match.group(1)
            matched.add(call_chain)

            # Also add individual components
            parts = call_chain.split('::')
            for i in range(len(parts)):
                matched.add('::'.join(parts[:i+1]))

        # 3. Method calls (obj.method())
        method_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)\s*\('
        for match in re.finditer(method_pattern, code):
            call_chain = match.group(1)
            matched.add(call_chain)

        return matched

    def infer_complexity(self, example_id: str, apis_used: List[str]) -> str:
        """
        Infer complexity level of an example based on APIs used.

        Args:
            example_id: Example identifier
            apis_used: List of APIs used in example

        Returns:
            Complexity level: "beginner", "intermediate", or "advanced"
        """
        if not apis_used:
            return "beginner"

        # Heuristics for complexity
        api_count = len(apis_used)

        # Check for advanced patterns
        has_async = any(
            self.api_by_name.get(api, {}).get("is_async", False)
            for api in apis_used
        )

        # Count distinct types (functions vs methods vs classes)
        types = set()
        for api in apis_used:
            api_data = self.api_by_name.get(api)
            if api_data:
                types.add(api_data.get("type"))

        # Complexity inference
        if api_count <= 2 and not has_async:
            return "beginner"
        elif api_count <= 5 and len(types) <= 2:
            return "intermediate"
        else:
            return "advanced"


def match_examples_to_apis(
    examples: List[CodeExample],
    introspection_result: IntrospectionResult
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, str]]:
    """
    Convenience function to match examples to APIs.

    Args:
        examples: List of CodeExample objects
        introspection_result: Library introspection data

    Returns:
        Tuple of (api_to_examples, example_to_apis, example_complexity):
        - api_to_examples: Maps API names to example IDs
        - example_to_apis: Maps example IDs to API names
        - example_complexity: Maps example IDs to complexity levels

    Example:
        >>> from stackbench.readme_llm import introspect_library
        >>> result = introspect_library("lancedb", "0.25.2", "python")
        >>> api_map, ex_map, complexity = match_examples_to_apis(examples, result)
        >>> print(f"API lancedb.connect used in: {api_map['lancedb.connect']}")
    """
    matcher = APIExampleMatcher(introspection_result)
    api_to_examples, example_to_apis = matcher.match_examples(examples)

    # Infer complexity for each example
    example_complexity = {}
    for example_id, apis in example_to_apis.items():
        complexity = matcher.infer_complexity(example_id, apis)
        example_complexity[example_id] = complexity

    return api_to_examples, example_to_apis, example_complexity
