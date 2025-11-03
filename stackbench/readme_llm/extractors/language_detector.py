"""
Language detection for documentation code blocks.

Auto-detects programming languages used in documentation by analyzing
code block language tags. Handles multiple tag variations and filters
by occurrence threshold.
"""

import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Auto-detect programming languages from documentation code blocks.

    Scans markdown/rst files for code blocks and identifies which programming
    languages are used based on language tags. Normalizes tag variations and
    filters by minimum occurrence threshold.

    Supported languages:
    - Python (python, py, python3)
    - TypeScript (typescript, ts)
    - JavaScript (javascript, js)
    - Go (go, golang)
    - Rust (rust, rs)
    """

    # Language tag mappings (variations -> canonical name)
    LANGUAGE_MAPPINGS = {
        # Python
        'python': 'python',
        'py': 'python',
        'python3': 'python',
        'py3': 'python',

        # TypeScript
        'typescript': 'typescript',
        'ts': 'typescript',

        # JavaScript
        'javascript': 'javascript',
        'js': 'javascript',

        # Go
        'go': 'go',
        'golang': 'go',

        # Rust
        'rust': 'rust',
        'rs': 'rust',

        # Shell/Bash (for reference, not introspected)
        'bash': 'bash',
        'sh': 'bash',
        'shell': 'bash',

        # SQL (for reference, not introspected)
        'sql': 'sql',

        # YAML/JSON (for reference, not introspected)
        'yaml': 'yaml',
        'yml': 'yaml',
        'json': 'json',
    }

    # Languages we can introspect (excludes config/shell languages)
    INTROSPECTABLE_LANGUAGES = {'python', 'typescript', 'javascript', 'go', 'rust'}

    # Regex pattern to match code blocks with language tags
    # Matches: ```language or ```language:some:thing
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)(?::\S+)?\s*\n',  # Match ```lang or ```lang:something
        re.MULTILINE
    )

    def __init__(self, min_occurrences: int = 5):
        """
        Initialize language detector.

        Args:
            min_occurrences: Minimum number of code blocks required to consider
                           a language as "present" (default: 5)
        """
        self.min_occurrences = min_occurrences

    def detect_from_files(self, file_paths: List[Path]) -> List[str]:
        """
        Detect languages from a list of documentation files.

        Args:
            file_paths: List of documentation file paths to scan

        Returns:
            List of detected language names (canonical form),
            sorted by occurrence count (most common first)
        """
        language_counts = Counter()

        logger.info(f"Scanning {len(file_paths)} files for programming languages...")

        for file_path in file_paths:
            try:
                languages = self._detect_from_file(file_path)
                language_counts.update(languages)

            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")

        # Filter by minimum occurrences
        detected_languages = [
            lang for lang, count in language_counts.items()
            if count >= self.min_occurrences
        ]

        # Sort by occurrence (most common first)
        detected_languages.sort(key=lambda lang: language_counts[lang], reverse=True)

        self._log_detection_results(language_counts, detected_languages)

        return detected_languages

    def detect_introspectable_languages(self, file_paths: List[Path]) -> List[str]:
        """
        Detect only languages that can be introspected.

        Excludes shell scripts, config files, etc.

        Args:
            file_paths: List of documentation file paths

        Returns:
            List of introspectable languages (python, typescript, etc.)
        """
        all_languages = self.detect_from_files(file_paths)

        introspectable = [
            lang for lang in all_languages
            if lang in self.INTROSPECTABLE_LANGUAGES
        ]

        if not introspectable:
            logger.warning(
                f"No introspectable languages detected (found: {', '.join(all_languages) or 'none'})"
            )

        return introspectable

    def _detect_from_file(self, file_path: Path) -> List[str]:
        """
        Detect languages from a single file.

        Args:
            file_path: Path to documentation file

        Returns:
            List of language names found (can include duplicates)
        """
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        # Find all code block language tags
        matches = self.CODE_BLOCK_PATTERN.findall(content)

        # Normalize language tags
        languages = []
        for raw_tag in matches:
            normalized = self._normalize_language_tag(raw_tag.lower())
            if normalized:
                languages.append(normalized)

        return languages

    def _normalize_language_tag(self, tag: str) -> Optional[str]:
        """
        Normalize a language tag to canonical form.

        Args:
            tag: Raw language tag from code block (e.g., "py", "typescript")

        Returns:
            Canonical language name, or None if unknown
        """
        return self.LANGUAGE_MAPPINGS.get(tag)

    def _log_detection_results(
        self,
        all_counts: Counter,
        detected_languages: List[str]
    ):
        """
        Log detection results with statistics.

        Args:
            all_counts: Counter of all languages found
            detected_languages: Languages that met the threshold
        """
        if not all_counts:
            logger.warning("No code blocks with language tags found!")
            return

        logger.info("Code blocks by language:")
        for lang, count in all_counts.most_common():
            marker = "✓" if lang in detected_languages else "✗"
            logger.info(f"  {marker} {lang}: {count} blocks")

        if detected_languages:
            logger.info(
                f"Detected languages (≥{self.min_occurrences} occurrences): "
                f"{', '.join(detected_languages)}"
            )
        else:
            logger.warning(
                f"No languages met the threshold of {self.min_occurrences} occurrences"
            )

    def get_language_statistics(self, file_paths: List[Path]) -> Dict[str, int]:
        """
        Get detailed statistics about language usage.

        Args:
            file_paths: List of documentation files

        Returns:
            Dictionary mapping language names to occurrence counts
        """
        language_counts = Counter()

        for file_path in file_paths:
            try:
                languages = self._detect_from_file(file_path)
                language_counts.update(languages)
            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")

        return dict(language_counts)


def detect_languages(
    file_paths: List[Path],
    min_occurrences: int = 5,
    introspectable_only: bool = True
) -> List[str]:
    """
    Convenience function to detect languages from documentation files.

    Args:
        file_paths: List of documentation file paths
        min_occurrences: Minimum code blocks to consider a language present
        introspectable_only: If True, return only languages that can be introspected
                           (excludes bash, yaml, json, etc.)

    Returns:
        List of detected language names

    Example:
        >>> from pathlib import Path
        >>> docs = [Path("docs/quickstart.md"), Path("docs/api.md")]
        >>> languages = detect_languages(docs)
        >>> print(languages)
        ['python', 'typescript']
    """
    detector = LanguageDetector(min_occurrences=min_occurrences)

    if introspectable_only:
        return detector.detect_introspectable_languages(file_paths)

    return detector.detect_from_files(file_paths)
