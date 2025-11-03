"""
README.LLM XML formatter.

Generates the monolithic README.LLM file in XML format following the
validated structure from the paper (Wijaya et al., 2025).

Structure:
<ReadMe.LLM>
  <rules>...</rules>
  <context_description>...</context_description>
  <context_1>
    <context_1_description>...</context_1_description>
    <context_1_function>...</context_1_function>
    <context_1_example>...</context_1_example>
  </context_1>
  ...
</ReadMe.LLM>
"""

from typing import List, Dict, Optional
from pathlib import Path
import logging

from stackbench.readme_llm.schemas import APIEntry, ExampleEntry, LibraryOverview

logger = logging.getLogger(__name__)


class ReadMeLLMFormatter:
    """
    Generate README.LLM in XML format.

    Follows the validated structure from the ReadMe.LLM paper:
    - Rules section (customizable)
    - Context description
    - N context sections (interleaved description + function + example)
    - Sorted by importance scores
    """

    DEFAULT_RULES = [
        "When you are unsure about something, ask the user what information you need.",
        "Reuse {library} functions and code when applicable.",
        "Consider library dependencies when generating code solutions.",
        "Follow best practices and idiomatic patterns for {language}.",
        "Provide clear error handling in code examples."
    ]

    def __init__(
        self,
        library_overview: LibraryOverview,
        custom_rules: Optional[List[str]] = None,
        max_contexts: int = 50
    ):
        """
        Initialize README.LLM formatter.

        Args:
            library_overview: Library metadata
            custom_rules: Optional custom rules (default: DEFAULT_RULES)
            max_contexts: Maximum number of API contexts to include (default: 50)
        """
        self.library_overview = library_overview
        self.rules = custom_rules or self.DEFAULT_RULES
        self.max_contexts = max_contexts

    def format(
        self,
        api_entries: List[APIEntry],
        example_entries: Dict[str, ExampleEntry],
        language: Optional[str] = None
    ) -> str:
        """
        Generate README.LLM XML content.

        Args:
            api_entries: List of API catalog entries (should be sorted by importance)
            example_entries: Dictionary mapping example IDs to ExampleEntry objects
            language: Optional language filter (if None, uses library_overview.languages[0])

        Returns:
            XML string for README.LLM
        """
        if not language:
            language = self.library_overview.languages[0] if self.library_overview.languages else "python"

        # Filter APIs by language
        language_apis = [api for api in api_entries if api.language == language]

        # Sort by importance score (descending)
        language_apis.sort(key=lambda api: api.importance_score, reverse=True)

        # Limit to max_contexts
        language_apis = language_apis[:self.max_contexts]

        logger.info(f"Generating README.LLM for {len(language_apis)} APIs ({language})")

        # Build XML
        xml_lines = ['<ReadMe.LLM>']

        # 1. Rules section
        xml_lines.append('  <rules>')
        for i, rule in enumerate(self.rules, 1):
            # Substitute placeholders
            rule_text = rule.replace('{library}', self.library_overview.name)
            rule_text = rule_text.replace('{language}', language)
            xml_lines.append(f'    Rule number {i}: {self._escape_xml(rule_text)}')
        xml_lines.append('  </rules>')
        xml_lines.append('')

        # 2. Context description
        xml_lines.append('  <context_description>')
        description = (
            f"The context will be for the {self.library_overview.name} library. "
            f"{self.library_overview.description} "
            f"The context is organized into different numbered sections using XML tags, "
            f"each covering a specific API or functionality."
        )
        xml_lines.append(f'    {self._escape_xml(description)}')
        xml_lines.append('  </context_description>')
        xml_lines.append('')

        # 3. Context sections (one per API)
        for i, api in enumerate(language_apis, 1):
            context_xml = self._format_context(i, api, example_entries)
            xml_lines.append(context_xml)
            xml_lines.append('')

        xml_lines.append('</ReadMe.LLM>')

        return '\n'.join(xml_lines)

    def _format_context(
        self,
        context_num: int,
        api: APIEntry,
        example_entries: Dict[str, ExampleEntry]
    ) -> str:
        """
        Format a single context section.

        Args:
            context_num: Context number (1-indexed)
            api: APIEntry object
            example_entries: Dictionary of example entries

        Returns:
            XML string for context section
        """
        lines = [f'  <context_{context_num}>']

        # Description
        lines.append(f'    <context_{context_num}_description>')
        lines.append(f'      {self._escape_xml(api.description)}')

        # Add usage information if available
        if api.tags:
            tags_str = ', '.join(api.tags)
            lines.append(f'      Tags: {self._escape_xml(tags_str)}')

        lines.append(f'    </context_{context_num}_description>')

        # Function signature
        lines.append(f'    <context_{context_num}_function>')
        lines.append(f'      API: {self._escape_xml(api.api_id)}')
        lines.append(f'      Signature: {self._escape_xml(api.signature)}')

        # Add parameter details if available
        if api.parameters:
            lines.append('      Parameters:')
            for param in api.parameters:
                param_desc = f"        - {param.name} ({param.type})"
                if not param.required:
                    param_desc += f", optional, default: {param.default}"
                param_desc += f": {param.description}"
                lines.append(self._escape_xml(param_desc))

        # Add return type if available
        if api.returns:
            lines.append(f"      Returns: {self._escape_xml(api.returns.get('type', 'unknown'))} - {self._escape_xml(api.returns.get('description', ''))}")

        lines.append(f'    </context_{context_num}_function>')

        # Example
        lines.append(f'    <context_{context_num}_example>')

        # Get best example for this API
        example = self._select_best_example(api, example_entries)

        if example:
            lines.append(f'      {self._escape_xml(example.title)}')
            lines.append('')
            # Format code with proper indentation
            code_lines = example.code.split('\n')
            for code_line in code_lines:
                lines.append(f'      {self._escape_xml(code_line)}')

            # Add complexity indicator
            lines.append('')
            lines.append(f'      Complexity: {example.complexity}')

            # Add prerequisites if available
            if example.prerequisites:
                lines.append(f'      Prerequisites: {self._escape_xml(", ".join(example.prerequisites))}')
        else:
            lines.append('      # Example not available for this API')

        lines.append(f'    </context_{context_num}_example>')

        lines.append(f'  </context_{context_num}>')

        return '\n'.join(lines)

    def _select_best_example(
        self,
        api: APIEntry,
        example_entries: Dict[str, ExampleEntry]
    ) -> Optional[ExampleEntry]:
        """
        Select the best example for an API.

        Prefers:
        1. Validated examples over unvalidated
        2. Beginner examples over advanced
        3. Complete examples over snippets

        Args:
            api: APIEntry object
            example_entries: Dictionary of example entries

        Returns:
            Best ExampleEntry or None if no examples
        """
        if not api.examples:
            return None

        # Get all examples for this API
        candidates = [
            example_entries[ex_id]
            for ex_id in api.examples
            if ex_id in example_entries
        ]

        if not candidates:
            return None

        # Sort by preference
        def score_example(ex: ExampleEntry) -> tuple:
            return (
                ex.validated,  # Validated first
                ex.complexity == 'beginner',  # Beginner examples preferred
                ex.is_complete,  # Complete examples preferred
                -len(ex.code)  # Shorter examples preferred (tie-breaker)
            )

        candidates.sort(key=score_example, reverse=True)
        return candidates[0]

    def _escape_xml(self, text: str) -> str:
        """
        Escape XML special characters.

        Args:
            text: Raw text

        Returns:
            XML-escaped text
        """
        if not text:
            return ""

        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }

        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        return result

    def save(self, output_path: Path, content: str):
        """
        Save README.LLM to file.

        Args:
            output_path: Path to save file
            content: XML content
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"Saved README.LLM to {output_path} ({len(content)} chars)")


def generate_readme_llm(
    library_overview: LibraryOverview,
    api_entries: List[APIEntry],
    example_entries: Dict[str, ExampleEntry],
    output_path: Path,
    language: Optional[str] = None,
    max_contexts: int = 50,
    custom_rules: Optional[List[str]] = None
) -> str:
    """
    Convenience function to generate and save README.LLM.

    Args:
        library_overview: Library metadata
        api_entries: List of API catalog entries
        example_entries: Dictionary of example entries
        output_path: Where to save README.LLM
        language: Optional language filter
        max_contexts: Maximum API contexts to include
        custom_rules: Optional custom rules

    Returns:
        Generated XML content

    Example:
        >>> from pathlib import Path
        >>> content = generate_readme_llm(
        ...     overview,
        ...     apis,
        ...     examples,
        ...     Path("data/run_123/readme_llm/README.LLM"),
        ...     language="python",
        ...     max_contexts=50
        ... )
    """
    formatter = ReadMeLLMFormatter(
        library_overview=library_overview,
        custom_rules=custom_rules,
        max_contexts=max_contexts
    )

    content = formatter.format(api_entries, example_entries, language)
    formatter.save(output_path, content)

    return content
