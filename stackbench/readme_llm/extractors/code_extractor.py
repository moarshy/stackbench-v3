"""
Code example extraction from documentation.

Extracts code examples from multiple documentation formats:
- Standard markdown code blocks
- MkDocs Material snippet includes (--8<--)
- reStructuredText literalinclude directives
- Indented code blocks

Provides full metadata including language, location, section hierarchy,
and snippet source information.
"""

import re
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
import logging

from stackbench.readme_llm.schemas import CodeExample

logger = logging.getLogger(__name__)


@dataclass
class ExtractedBlock:
    """Intermediate representation of an extracted code block."""
    code: str
    language: str
    line_number: int
    is_snippet: bool
    snippet_source: Optional[str] = None  # Path to snippet file if applicable


class CodeExampleExtractor:
    """
    Extract code examples from documentation with full metadata.

    Handles:
    - Standard markdown: ```python ... ```
    - MkDocs snippets: --8<-- "snippets/example.py"
    - reStructuredText: .. literalinclude:: example.py
    - Markdown section hierarchy tracking
    """

    # Regex patterns for different code block formats
    CODE_BLOCK_PATTERN = re.compile(
        r'^```(\w+)?.*?\n(.*?)^```',
        re.MULTILINE | re.DOTALL
    )

    MKDOCS_SNIPPET_PATTERN = re.compile(
        r'--8<--\s+"([^"]+)"'
    )

    RST_LITERALINCLUDE_PATTERN = re.compile(
        r'\.\.\s+literalinclude::\s+([^\s]+)\s*\n(?:\s+:language:\s+(\w+))?',
        re.MULTILINE
    )

    # Markdown heading pattern (# Title, ## Subtitle, etc.)
    HEADING_PATTERN = re.compile(
        r'^(#{1,6})\s+(.+?)$',
        re.MULTILINE
    )

    def __init__(self, docs_base_path: Path):
        """
        Initialize code extractor.

        Args:
            docs_base_path: Base path of documentation directory
                          (used for resolving snippet includes)
        """
        self.docs_base_path = docs_base_path

    def extract_from_file(self, file_path: Path) -> List[CodeExample]:
        """
        Extract all code examples from a documentation file.

        Args:
            file_path: Path to documentation file

        Returns:
            List of CodeExample objects with full metadata
        """
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")

        logger.debug(f"Extracting code from: {file_path.name}")

        content = file_path.read_text(encoding='utf-8', errors='ignore')

        # Build section hierarchy from headings
        section_hierarchy = self._build_section_hierarchy(content)

        # Extract code blocks
        code_blocks = []

        # 1. Standard markdown code blocks
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or 'text'
            code = match.group(2)
            line_number = content[:match.start()].count('\n') + 1

            code_blocks.append(ExtractedBlock(
                code=code.strip(),
                language=language.lower(),
                line_number=line_number,
                is_snippet=False
            ))

        # 2. MkDocs snippet includes (will be resolved later by SnippetResolver)
        for match in self.MKDOCS_SNIPPET_PATTERN.finditer(content):
            snippet_path = match.group(1)
            line_number = content[:match.start()].count('\n') + 1

            # Placeholder - actual resolution happens in SnippetResolver
            code_blocks.append(ExtractedBlock(
                code=f"# MkDocs snippet: {snippet_path}",
                language='unknown',  # Will be determined from snippet file
                line_number=line_number,
                is_snippet=True,
                snippet_source=snippet_path
            ))

        # 3. reStructuredText literalinclude
        for match in self.RST_LITERALINCLUDE_PATTERN.finditer(content):
            include_path = match.group(1)
            language = match.group(2) or 'text'
            line_number = content[:match.start()].count('\n') + 1

            code_blocks.append(ExtractedBlock(
                code=f"# RST literalinclude: {include_path}",
                language=language.lower(),
                line_number=line_number,
                is_snippet=True,
                snippet_source=include_path
            ))

        # Convert to CodeExample objects
        examples = []
        for idx, block in enumerate(code_blocks):
            # Find current section
            current_section = self._find_section_at_line(
                section_hierarchy,
                block.line_number
            )

            # Generate example ID
            example_id = self._generate_example_id(file_path, idx)

            # Detect if code is complete (has imports, main, etc.)
            is_complete = self._is_complete_program(block.code, block.language)

            # Extract API mentions (basic heuristic)
            apis_mentioned = self._extract_api_mentions(block.code, block.language)

            example = CodeExample(
                example_id=example_id,
                code=block.code,
                language=block.language,
                source_file=str(file_path.relative_to(self.docs_base_path)),
                line_number=block.line_number,
                is_complete=is_complete,
                is_snippet=block.is_snippet,
                apis_mentioned=apis_mentioned,
                section_hierarchy=current_section.get('hierarchy', []),
                markdown_anchor=current_section.get('anchor')
            )

            examples.append(example)

        logger.debug(f"Extracted {len(examples)} code examples from {file_path.name}")
        return examples

    def _build_section_hierarchy(self, content: str) -> List[Dict]:
        """
        Build section hierarchy from markdown headings.

        Args:
            content: File content

        Returns:
            List of section dicts with line numbers and hierarchy paths
        """
        sections = []
        hierarchy_stack = []

        for match in self.HEADING_PATTERN.finditer(content):
            level = len(match.group(1))  # Number of # symbols
            title = match.group(2).strip()
            line_number = content[:match.start()].count('\n') + 1

            # Generate markdown anchor (lowercase, hyphens, no special chars)
            anchor = '#' + re.sub(r'[^a-z0-9-]', '', title.lower().replace(' ', '-'))

            # Adjust hierarchy stack to current level
            hierarchy_stack = hierarchy_stack[:level-1]
            hierarchy_stack.append(title)

            sections.append({
                'line': line_number,
                'level': level,
                'title': title,
                'hierarchy': list(hierarchy_stack),
                'anchor': anchor
            })

        return sections

    def _find_section_at_line(self, sections: List[Dict], line_number: int) -> Dict:
        """
        Find the section containing a given line number.

        Args:
            sections: List of section dictionaries
            line_number: Line number to find

        Returns:
            Section dictionary, or empty dict if no section found
        """
        current_section = {'hierarchy': [], 'anchor': None}

        for section in sections:
            if section['line'] <= line_number:
                current_section = section
            else:
                break

        return current_section

    def _generate_example_id(self, file_path: Path, index: int) -> str:
        """
        Generate unique ID for code example.

        Args:
            file_path: Documentation file path
            index: Index of example within file

        Returns:
            Unique example ID
        """
        # Use file name (without extension) + index
        base_name = file_path.stem
        # Clean up name for ID
        clean_name = re.sub(r'[^a-z0-9_]', '_', base_name.lower())
        return f"{clean_name}_ex{index + 1}"

    def _is_complete_program(self, code: str, language: str) -> bool:
        """
        Heuristic to determine if code is a complete program.

        Checks for:
        - Python: imports, function definitions, main blocks
        - TypeScript/JavaScript: imports, function/class definitions
        - Go: package, func, main
        - Rust: fn, main

        Args:
            code: Code string
            language: Programming language

        Returns:
            True if appears to be complete program
        """
        if language == 'python':
            has_import = bool(re.search(r'^\s*(import|from)\s+', code, re.MULTILINE))
            has_function = bool(re.search(r'^\s*def\s+\w+', code, re.MULTILINE))
            has_class = bool(re.search(r'^\s*class\s+\w+', code, re.MULTILINE))
            has_main = '__main__' in code
            return has_import or has_function or has_class or has_main

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
            has_use = bool(re.search(r'^\s*use\s+', code, re.MULTILINE))
            return has_fn or has_use

        # Default: if code is > 3 lines, consider it complete
        return len(code.strip().split('\n')) > 3

    def _extract_api_mentions(self, code: str, language: str) -> List[str]:
        """
        Extract API mentions from code (basic heuristic).

        This is a simple implementation that looks for common patterns.
        The APIExampleMatcher will do more sophisticated analysis later.

        Args:
            code: Code string
            language: Programming language

        Returns:
            List of API identifiers mentioned (may include false positives)
        """
        apis = []

        if language == 'python':
            # Look for imports: import lancedb, from lancedb import X
            import_matches = re.findall(r'(?:from\s+(\w+)|import\s+(\w+))', code)
            for match in import_matches:
                api = match[0] or match[1]
                if api:
                    apis.append(api)

            # Look for function calls: module.function()
            call_matches = re.findall(r'(\w+\.\w+)\s*\(', code)
            apis.extend(call_matches)

        elif language in ('typescript', 'javascript'):
            # Look for imports: import X from 'module'
            import_matches = re.findall(r'from\s+[\'"](\w+)[\'"]', code)
            apis.extend(import_matches)

            # Look for function calls
            call_matches = re.findall(r'(\w+\.\w+)\s*\(', code)
            apis.extend(call_matches)

        # Remove duplicates and return
        return list(set(apis))


def extract_code_examples(file_paths: List[Path], docs_base_path: Path) -> Dict[str, List[CodeExample]]:
    """
    Convenience function to extract code examples from multiple files.

    Args:
        file_paths: List of documentation files
        docs_base_path: Base documentation directory

    Returns:
        Dictionary mapping file paths to lists of CodeExample objects

    Example:
        >>> from pathlib import Path
        >>> docs = [Path("docs/quickstart.md"), Path("docs/api.md")]
        >>> examples = extract_code_examples(docs, Path("docs"))
        >>> print(f"Found {sum(len(v) for v in examples.values())} examples")
    """
    extractor = CodeExampleExtractor(docs_base_path)
    results = {}

    for file_path in file_paths:
        try:
            examples = extractor.extract_from_file(file_path)
            if examples:
                results[str(file_path)] = examples
        except Exception as e:
            logger.error(f"Error extracting from {file_path}: {e}")

    total_examples = sum(len(v) for v in results.values())
    logger.info(f"Extracted {total_examples} code examples from {len(file_paths)} files")

    return results
