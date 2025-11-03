"""
Knowledge Base builder for DocuMentor MCP server.

Creates structured JSON knowledge base from library introspection and
documentation extraction. Organized by language with separate API catalog
and examples database.

Directory structure:
knowledge_base/
├── index.json                    # Master index
├── library_overview.json         # High-level info
├── api_catalog/                  # Per-language API definitions
│   ├── python/
│   │   ├── lancedb.connect.json
│   │   └── Table.search.json
│   └── typescript/
├── examples_db/                  # Per-language examples
│   ├── python/
│   │   ├── quickstart_ex1.json
│   │   └── search_ex1.json
│   └── typescript/
└── metadata.json                 # Generation stats
"""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import logging

from stackbench.readme_llm.schemas import (
    KnowledgeBase,
    LibraryOverview,
    APIEntry,
    ExampleEntry
)

logger = logging.getLogger(__name__)


class KnowledgeBaseBuilder:
    """
    Build structured JSON knowledge base for MCP server.

    Creates directory structure with per-language organization,
    individual JSON files for APIs and examples, and master index.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize knowledge base builder.

        Args:
            output_dir: Base directory for knowledge base
        """
        self.output_dir = Path(output_dir)
        self.api_catalog_dir = self.output_dir / "api_catalog"
        self.examples_db_dir = self.output_dir / "examples_db"

    def build(
        self,
        library_overview: LibraryOverview,
        api_entries_by_language: Dict[str, List[APIEntry]],
        example_entries_by_language: Dict[str, List[ExampleEntry]],
        generation_mode: str = "standalone"
    ) -> KnowledgeBase:
        """
        Build complete knowledge base.

        Args:
            library_overview: Library metadata
            api_entries_by_language: APIs grouped by language
            example_entries_by_language: Examples grouped by language
            generation_mode: "standalone" or "integration"

        Returns:
            KnowledgeBase object
        """
        logger.info(f"Building knowledge base at: {self.output_dir}")

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_catalog_dir.mkdir(parents=True, exist_ok=True)
        self.examples_db_dir.mkdir(parents=True, exist_ok=True)

        # Build API catalog
        api_catalog = self._build_api_catalog(api_entries_by_language)

        # Build examples database
        examples_db = self._build_examples_db(example_entries_by_language)

        # Build metadata
        metadata = self._build_metadata(
            library_overview,
            api_entries_by_language,
            example_entries_by_language,
            generation_mode
        )

        # Create knowledge base object
        knowledge_base = KnowledgeBase(
            library_overview=library_overview,
            api_catalog=api_catalog,
            examples_db=examples_db,
            concept_graph=None,  # Future enhancement
            metadata=metadata
        )

        # Save to disk
        self._save_library_overview(library_overview)
        self._save_index(knowledge_base)
        self._save_metadata(metadata)

        logger.info(
            f"Knowledge base complete: "
            f"{sum(len(apis) for apis in api_catalog.values())} APIs, "
            f"{sum(len(examples) for examples in examples_db.values())} examples"
        )

        return knowledge_base

    def _build_api_catalog(
        self,
        api_entries_by_language: Dict[str, List[APIEntry]]
    ) -> Dict[str, Dict[str, APIEntry]]:
        """
        Build API catalog with per-language organization.

        Creates individual JSON files for each API.

        Args:
            api_entries_by_language: APIs grouped by language

        Returns:
            Nested dict: {language: {api_id: APIEntry}}
        """
        api_catalog = {}

        for language, apis in api_entries_by_language.items():
            language_dir = self.api_catalog_dir / language
            language_dir.mkdir(parents=True, exist_ok=True)

            api_catalog[language] = {}

            for api in apis:
                # Save individual API file
                api_file = language_dir / f"{self._safe_filename(api.api_id)}.json"
                api_data = api.model_dump()
                api_file.write_text(json.dumps(api_data, indent=2), encoding='utf-8')

                api_catalog[language][api.api_id] = api

            logger.debug(f"Created {len(apis)} API files for {language}")

        return api_catalog

    def _build_examples_db(
        self,
        example_entries_by_language: Dict[str, List[ExampleEntry]]
    ) -> Dict[str, Dict[str, ExampleEntry]]:
        """
        Build examples database with per-language organization.

        Creates individual JSON files for each example.

        Args:
            example_entries_by_language: Examples grouped by language

        Returns:
            Nested dict: {language: {example_id: ExampleEntry}}
        """
        examples_db = {}

        for language, examples in example_entries_by_language.items():
            language_dir = self.examples_db_dir / language
            language_dir.mkdir(parents=True, exist_ok=True)

            examples_db[language] = {}

            for example in examples:
                # Save individual example file
                example_file = language_dir / f"{example.example_id}.json"
                example_data = example.model_dump()
                example_file.write_text(json.dumps(example_data, indent=2), encoding='utf-8')

                examples_db[language][example.example_id] = example

            logger.debug(f"Created {len(examples)} example files for {language}")

        return examples_db

    def _build_metadata(
        self,
        library_overview: LibraryOverview,
        api_entries_by_language: Dict[str, List[APIEntry]],
        example_entries_by_language: Dict[str, List[ExampleEntry]],
        generation_mode: str
    ) -> Dict:
        """
        Build generation metadata.

        Args:
            library_overview: Library metadata
            api_entries_by_language: APIs by language
            example_entries_by_language: Examples by language
            generation_mode: Generation mode

        Returns:
            Metadata dictionary
        """
        apis_by_language = {
            lang: len(apis)
            for lang, apis in api_entries_by_language.items()
        }

        examples_by_language = {
            lang: len(examples)
            for lang, examples in example_entries_by_language.items()
        }

        # Count validated examples (if in integration mode)
        validated_count = 0
        for examples in example_entries_by_language.values():
            validated_count += sum(1 for ex in examples if ex.validated)

        return {
            "generation_mode": generation_mode,
            "timestamp": datetime.now().isoformat(),
            "library_name": library_overview.name,
            "library_version": library_overview.version,
            "languages": library_overview.languages,
            "total_apis": sum(apis_by_language.values()),
            "total_examples": sum(examples_by_language.values()),
            "apis_by_language": apis_by_language,
            "examples_by_language": examples_by_language,
            "validated_examples": validated_count if generation_mode == "integration" else None,
            "knowledge_base_version": "1.0"
        }

    def _save_library_overview(self, overview: LibraryOverview):
        """Save library overview to JSON."""
        overview_path = self.output_dir / "library_overview.json"
        overview_data = overview.model_dump()
        overview_path.write_text(json.dumps(overview_data, indent=2), encoding='utf-8')
        logger.debug(f"Saved library overview: {overview_path}")

    def _save_index(self, knowledge_base: KnowledgeBase):
        """
        Save master index with references to all APIs and examples.

        Provides quick lookup without loading individual files.
        """
        index = {
            "library": knowledge_base.library_overview.name,
            "version": knowledge_base.library_overview.version,
            "languages": knowledge_base.library_overview.languages,
            "apis": {},
            "examples": {}
        }

        # Index APIs
        for language, apis in knowledge_base.api_catalog.items():
            index["apis"][language] = [
                {
                    "api_id": api_id,
                    "signature": api.signature,
                    "importance_score": api.importance_score,
                    "file": f"api_catalog/{language}/{self._safe_filename(api_id)}.json"
                }
                for api_id, api in apis.items()
            ]

        # Index examples
        for language, examples in knowledge_base.examples_db.items():
            index["examples"][language] = [
                {
                    "example_id": example_id,
                    "title": example.title,
                    "complexity": example.complexity,
                    "apis_used": example.apis_used,
                    "file": f"examples_db/{language}/{example_id}.json"
                }
                for example_id, example in examples.items()
            ]

        index_path = self.output_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2), encoding='utf-8')
        logger.debug(f"Saved index: {index_path}")

    def _save_metadata(self, metadata: Dict):
        """Save metadata to JSON."""
        metadata_path = self.output_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        logger.debug(f"Saved metadata: {metadata_path}")

    def _safe_filename(self, text: str) -> str:
        """
        Convert text to safe filename.

        Args:
            text: Text to convert

        Returns:
            Safe filename string
        """
        # Replace special characters with underscores
        safe = text.replace('.', '_').replace(':', '_').replace('/', '_')
        safe = safe.replace('\\', '_').replace(' ', '_')
        # Limit length
        if len(safe) > 200:
            safe = safe[:200]
        return safe


def build_knowledge_base(
    output_dir: Path,
    library_overview: LibraryOverview,
    api_entries_by_language: Dict[str, List[APIEntry]],
    example_entries_by_language: Dict[str, List[ExampleEntry]],
    generation_mode: str = "standalone"
) -> KnowledgeBase:
    """
    Convenience function to build knowledge base.

    Args:
        output_dir: Output directory for knowledge base
        library_overview: Library metadata
        api_entries_by_language: APIs grouped by language
        example_entries_by_language: Examples grouped by language
        generation_mode: "standalone" or "integration"

    Returns:
        KnowledgeBase object

    Example:
        >>> from pathlib import Path
        >>> kb = build_knowledge_base(
        ...     Path("data/run_123/readme_llm/knowledge_base"),
        ...     overview,
        ...     {"python": python_apis},
        ...     {"python": python_examples},
        ...     generation_mode="standalone"
        ... )
        >>> print(f"Built knowledge base with {len(kb.api_catalog['python'])} Python APIs")
    """
    builder = KnowledgeBaseBuilder(output_dir)
    return builder.build(
        library_overview,
        api_entries_by_language,
        example_entries_by_language,
        generation_mode
    )
