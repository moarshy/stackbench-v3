"""
Snippet resolver for documentation includes.

Resolves snippet includes from MkDocs Material and reStructuredText:
- MkDocs: --8<-- "snippets/example.py"
- reStructuredText: .. literalinclude:: examples/code.py

Reads the actual snippet files and updates CodeExample objects with
the real code content and detected language.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict
import logging

from stackbench.readme_llm.schemas import CodeExample

logger = logging.getLogger(__name__)


class SnippetResolver:
    """
    Resolve snippet includes in code examples.

    MkDocs Material uses --8<-- syntax to include snippets from external files.
    reStructuredText uses literalinclude directives.

    This class reads those external files and replaces placeholders with actual code.
    """

    def __init__(self, docs_base_path: Path):
        """
        Initialize snippet resolver.

        Args:
            docs_base_path: Base path of documentation directory
        """
        self.docs_base_path = Path(docs_base_path).resolve()
        self._cache: Dict[str, str] = {}  # Cache resolved snippets

    def resolve_examples(self, examples: List[CodeExample]) -> List[CodeExample]:
        """
        Resolve snippet includes in a list of code examples.

        Updates examples that reference external snippet files with the actual
        code content and detected language.

        Args:
            examples: List of CodeExample objects

        Returns:
            List of CodeExample objects with resolved snippets
        """
        resolved = []

        for example in examples:
            if example.is_snippet:
                resolved_example = self._resolve_example(example)
                resolved.append(resolved_example)
            else:
                resolved.append(example)

        snippets_resolved = sum(1 for ex in examples if ex.is_snippet)
        if snippets_resolved > 0:
            logger.info(f"Resolved {snippets_resolved} snippet includes")

        return resolved

    def _resolve_example(self, example: CodeExample) -> CodeExample:
        """
        Resolve a single snippet example.

        Args:
            example: CodeExample with snippet reference

        Returns:
            Updated CodeExample with resolved code
        """
        # Extract snippet path from placeholder code
        snippet_path = self._extract_snippet_path(example.code)

        if not snippet_path:
            logger.warning(f"Could not extract snippet path from: {example.code[:100]}")
            return example

        # Resolve the snippet file
        try:
            code, language = self._read_snippet(snippet_path, example.source_file)

            # Create updated example
            return CodeExample(
                example_id=example.example_id,
                code=code,
                language=language or example.language,
                source_file=example.source_file,
                line_number=example.line_number,
                is_complete=self._is_complete_snippet(code, language or example.language),
                is_snippet=True,
                apis_mentioned=self._extract_api_mentions(code, language or example.language),
                section_hierarchy=example.section_hierarchy,
                markdown_anchor=example.markdown_anchor
            )

        except Exception as e:
            logger.error(f"Failed to resolve snippet {snippet_path}: {e}")
            return example

    def _extract_snippet_path(self, code: str) -> Optional[str]:
        """
        Extract snippet file path from placeholder code.

        Args:
            code: Placeholder code string

        Returns:
            Snippet file path, or None if not found
        """
        # MkDocs format: # MkDocs snippet: snippets/example.py
        mkdocs_match = re.search(r'# MkDocs snippet:\s*(.+)', code)
        if mkdocs_match:
            return mkdocs_match.group(1).strip()

        # RST format: # RST literalinclude: examples/code.py
        rst_match = re.search(r'# RST literalinclude:\s*(.+)', code)
        if rst_match:
            return rst_match.group(1).strip()

        return None

    def _read_snippet(self, snippet_path: str, source_file: str) -> tuple[str, Optional[str]]:
        """
        Read snippet file and return code + detected language.

        Args:
            snippet_path: Path to snippet file (relative to docs base or source file)
            source_file: Source documentation file (for relative resolution)

        Returns:
            Tuple of (code_content, detected_language)
        """
        # Check cache first
        if snippet_path in self._cache:
            cached_code = self._cache[snippet_path]
            language = self._detect_language_from_extension(snippet_path)
            return cached_code, language

        # Try multiple resolution strategies
        resolved_path = self._resolve_snippet_path(snippet_path, source_file)

        if not resolved_path or not resolved_path.exists():
            raise FileNotFoundError(f"Snippet file not found: {snippet_path}")

        # Read snippet content
        code = resolved_path.read_text(encoding='utf-8', errors='ignore')

        # Detect language from file extension
        language = self._detect_language_from_extension(snippet_path)

        # Cache the result
        self._cache[snippet_path] = code

        logger.debug(f"Resolved snippet: {snippet_path} ({language}, {len(code)} chars)")

        return code, language

    def _resolve_snippet_path(self, snippet_path: str, source_file: str) -> Optional[Path]:
        """
        Resolve snippet path using multiple strategies.

        Tries:
        1. Relative to docs base path
        2. Relative to source file directory
        3. Absolute path (if provided)

        Args:
            snippet_path: Snippet file path from include directive
            source_file: Source documentation file

        Returns:
            Resolved Path object, or None if not found
        """
        # Strategy 1: Relative to docs base
        candidate1 = self.docs_base_path / snippet_path
        if candidate1.exists():
            return candidate1

        # Strategy 2: Relative to source file directory
        source_dir = (self.docs_base_path / source_file).parent
        candidate2 = source_dir / snippet_path
        if candidate2.exists():
            return candidate2

        # Strategy 3: Try as absolute path
        candidate3 = Path(snippet_path)
        if candidate3.is_absolute() and candidate3.exists():
            return candidate3

        logger.warning(
            f"Could not resolve snippet path: {snippet_path}\n"
            f"  Tried:\n"
            f"    1. {candidate1}\n"
            f"    2. {candidate2}\n"
            f"    3. {candidate3}"
        )

        return None

    def _detect_language_from_extension(self, file_path: str) -> Optional[str]:
        """
        Detect programming language from file extension.

        Args:
            file_path: File path

        Returns:
            Language name, or None if unknown
        """
        ext_to_lang = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.sh': 'bash',
            '.bash': 'bash',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
        }

        suffix = Path(file_path).suffix.lower()
        return ext_to_lang.get(suffix)

    def _is_complete_snippet(self, code: str, language: str) -> bool:
        """
        Determine if snippet code is a complete program.

        Similar to CodeExampleExtractor._is_complete_program but for snippets.

        Args:
            code: Code content
            language: Programming language

        Returns:
            True if appears complete
        """
        if language == 'python':
            has_import = bool(re.search(r'^\s*(import|from)\s+', code, re.MULTILINE))
            has_function = bool(re.search(r'^\s*def\s+\w+', code, re.MULTILINE))
            has_class = bool(re.search(r'^\s*class\s+\w+', code, re.MULTILINE))
            return has_import or has_function or has_class

        elif language in ('typescript', 'javascript'):
            has_import = bool(re.search(r'^\s*(import|require)\s+', code, re.MULTILINE))
            has_function = bool(re.search(r'^\s*(function|const|let|var)\s+\w+', code, re.MULTILINE))
            has_class = bool(re.search(r'^\s*class\s+\w+', code, re.MULTILINE))
            return has_import or has_function or has_class

        elif language == 'go':
            has_package = bool(re.search(r'^\s*package\s+', code, re.MULTILINE))
            has_func = bool(re.search(r'^\s*func\s+', code, re.MULTILINE))
            return has_package and has_func

        elif language == 'rust':
            has_fn = bool(re.search(r'^\s*fn\s+', code, re.MULTILINE))
            return has_fn

        return len(code.strip().split('\n')) > 3

    def _extract_api_mentions(self, code: str, language: str) -> List[str]:
        """
        Extract API mentions from resolved snippet code.

        Args:
            code: Snippet code
            language: Programming language

        Returns:
            List of API identifiers
        """
        apis = []

        if language == 'python':
            import_matches = re.findall(r'(?:from\s+(\w+)|import\s+(\w+))', code)
            for match in import_matches:
                api = match[0] or match[1]
                if api:
                    apis.append(api)

            call_matches = re.findall(r'(\w+\.\w+)\s*\(', code)
            apis.extend(call_matches)

        elif language in ('typescript', 'javascript'):
            import_matches = re.findall(r'from\s+[\'"](\w+)[\'"]', code)
            apis.extend(import_matches)

            call_matches = re.findall(r'(\w+\.\w+)\s*\(', code)
            apis.extend(call_matches)

        return list(set(apis))


def resolve_snippets(examples: List[CodeExample], docs_base_path: Path) -> List[CodeExample]:
    """
    Convenience function to resolve snippets in code examples.

    Args:
        examples: List of CodeExample objects
        docs_base_path: Base documentation directory

    Returns:
        List of CodeExample objects with resolved snippets

    Example:
        >>> from pathlib import Path
        >>> examples = [...]  # CodeExample objects with snippets
        >>> resolved = resolve_snippets(examples, Path("docs"))
        >>> print(f"Resolved {sum(ex.is_snippet for ex in resolved)} snippets")
    """
    resolver = SnippetResolver(docs_base_path)
    return resolver.resolve_examples(examples)
