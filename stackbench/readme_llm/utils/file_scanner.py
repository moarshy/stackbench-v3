"""
File scanner for documentation directories.

Recursively scans a documentation directory to find all documentation files
(Markdown, reStructuredText, MDX). Used by the README.LLM generation system
to discover all documentation that needs to be processed.
"""

from pathlib import Path
from typing import List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class FileScanner:
    """
    Recursively scan documentation directories for supported file types.

    Supports:
    - Markdown (.md)
    - MDX (.mdx)
    - reStructuredText (.rst)

    Excludes common non-documentation directories:
    - node_modules, .git, __pycache__, .venv, venv, build, dist, etc.
    """

    # Supported documentation file extensions
    SUPPORTED_EXTENSIONS = {'.md', '.mdx', '.rst'}

    # Directories to exclude from scanning
    DEFAULT_EXCLUDE_DIRS = {
        'node_modules',
        '.git',
        '.github',
        '__pycache__',
        '.pytest_cache',
        '.venv',
        'venv',
        'env',
        'build',
        'dist',
        '.next',
        '.nuxt',
        '.cache',
        'coverage',
        '.tox',
        'site',  # MkDocs build output
        '_build',  # Sphinx build output
        '.docusaurus',  # Docusaurus cache
    }

    def __init__(
        self,
        base_path: Path,
        extensions: Optional[Set[str]] = None,
        exclude_dirs: Optional[Set[str]] = None
    ):
        """
        Initialize the file scanner.

        Args:
            base_path: Base directory to scan
            extensions: File extensions to include (default: .md, .mdx, .rst)
            exclude_dirs: Directory names to exclude (default: common build/cache dirs)
        """
        self.base_path = Path(base_path).resolve()
        self.extensions = extensions or self.SUPPORTED_EXTENSIONS
        self.exclude_dirs = exclude_dirs or self.DEFAULT_EXCLUDE_DIRS

        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {self.base_path}")

        if not self.base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {self.base_path}")

    def scan(self) -> List[Path]:
        """
        Scan the base directory recursively for documentation files.

        Returns:
            List of Path objects for all documentation files found,
            sorted by path for consistent ordering.
        """
        doc_files = []

        logger.info(f"Scanning documentation directory: {self.base_path}")
        logger.debug(f"Looking for extensions: {', '.join(self.extensions)}")
        logger.debug(f"Excluding directories: {', '.join(self.exclude_dirs)}")

        for file_path in self._walk_directory(self.base_path):
            if file_path.suffix in self.extensions:
                doc_files.append(file_path)
                logger.debug(f"Found documentation file: {file_path.relative_to(self.base_path)}")

        # Sort for consistent ordering
        doc_files.sort()

        logger.info(f"Found {len(doc_files)} documentation files")
        self._log_statistics(doc_files)

        return doc_files

    def _walk_directory(self, directory: Path):
        """
        Recursively walk directory, yielding files while respecting exclusions.

        Args:
            directory: Directory to walk

        Yields:
            Path objects for files found
        """
        try:
            for item in directory.iterdir():
                # Skip hidden files and directories (starting with .)
                if item.name.startswith('.') and item.name not in {'.github'}:
                    continue

                if item.is_dir():
                    # Skip excluded directories
                    if item.name in self.exclude_dirs:
                        logger.debug(f"Skipping excluded directory: {item.name}")
                        continue

                    # Recursively scan subdirectory
                    yield from self._walk_directory(item)

                elif item.is_file():
                    yield item

        except PermissionError:
            logger.warning(f"Permission denied accessing: {directory}")
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")

    def _log_statistics(self, files: List[Path]):
        """
        Log statistics about found files.

        Args:
            files: List of documentation files
        """
        if not files:
            logger.warning("No documentation files found!")
            return

        # Count by extension
        by_extension = {}
        for file in files:
            ext = file.suffix
            by_extension[ext] = by_extension.get(ext, 0) + 1

        logger.info("Files by extension:")
        for ext, count in sorted(by_extension.items()):
            logger.info(f"  {ext}: {count} files")

    def scan_filtered(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Path]:
        """
        Scan with additional path filtering.

        Args:
            include_patterns: List of glob patterns to include (e.g., ["**/python/**"])
            exclude_patterns: List of glob patterns to exclude (e.g., ["**/drafts/**"])

        Returns:
            Filtered list of documentation files
        """
        all_files = self.scan()

        if not include_patterns and not exclude_patterns:
            return all_files

        filtered_files = []

        for file in all_files:
            relative_path = file.relative_to(self.base_path)
            relative_str = str(relative_path)

            # Apply include patterns
            if include_patterns:
                included = any(
                    relative_path.match(pattern)
                    for pattern in include_patterns
                )
                if not included:
                    continue

            # Apply exclude patterns
            if exclude_patterns:
                excluded = any(
                    relative_path.match(pattern)
                    for pattern in exclude_patterns
                )
                if excluded:
                    continue

            filtered_files.append(file)

        logger.info(f"Filtered to {len(filtered_files)} files (from {len(all_files)})")
        return filtered_files

    def get_file_metadata(self, file_path: Path) -> dict:
        """
        Get metadata for a documentation file.

        Args:
            file_path: Path to documentation file

        Returns:
            Dictionary with metadata (size, modified time, etc.)
        """
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")

        stat = file_path.stat()

        return {
            "path": str(file_path),
            "relative_path": str(file_path.relative_to(self.base_path)),
            "filename": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": stat.st_size,
            "modified_timestamp": stat.st_mtime,
            "is_empty": stat.st_size == 0,
        }


def scan_documentation(
    docs_path: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> List[Path]:
    """
    Convenience function to scan documentation directory.

    Args:
        docs_path: Base documentation directory
        include_patterns: Optional glob patterns to include
        exclude_patterns: Optional glob patterns to exclude

    Returns:
        List of documentation file paths

    Example:
        >>> docs = scan_documentation(Path("docs/src"))
        >>> python_docs = scan_documentation(
        ...     Path("docs"),
        ...     include_patterns=["**/python/**"]
        ... )
    """
    scanner = FileScanner(docs_path)

    if include_patterns or exclude_patterns:
        return scanner.scan_filtered(include_patterns, exclude_patterns)

    return scanner.scan()
