"""
README.LLM Generator - Main orchestration logic.

This module contains the core generation logic that can be called
programmatically or from a Claude Code agent. It ties together all
the extraction, introspection, matching, and formatting components.
"""

import uuid
from pathlib import Path
from typing import List, Dict, Optional, Literal
from datetime import datetime
import logging

from stackbench.readme_llm.utils import scan_documentation
from stackbench.readme_llm.extractors import (
    detect_languages,
    extract_code_examples,
    resolve_snippets
)
from stackbench.readme_llm.introspection import introspect_library
from stackbench.readme_llm.matchers import match_examples_to_apis
from stackbench.readme_llm.formatters import generate_readme_llm, build_knowledge_base
from stackbench.readme_llm.schemas import (
    LibraryOverview,
    APIEntry,
    ExampleEntry,
    Parameter,
    ReadMeLLMOutput
)

logger = logging.getLogger(__name__)


class ReadMeLLMGenerator:
    """
    Main generator for README.LLM system.

    Orchestrates the entire generation pipeline:
    1. Scan documentation
    2. Detect/validate languages
    3. Introspect library
    4. Extract and match examples
    5. Generate outputs
    """

    def __init__(
        self,
        docs_path: Path,
        library_name: str,
        library_version: str,
        output_dir: Optional[Path] = None,
        languages: Optional[List[str]] = None,
        generation_mode: Literal["standalone", "integration"] = "standalone"
    ):
        """
        Initialize README.LLM generator.

        Args:
            docs_path: Path to documentation directory
            library_name: Name of library
            library_version: Library version
            output_dir: Output directory (default: data/<run_id>/readme_llm/)
            languages: Languages to process (default: auto-detect)
            generation_mode: "standalone" or "integration"
        """
        self.docs_path = Path(docs_path)
        self.library_name = library_name
        self.library_version = library_version
        self.generation_mode = generation_mode
        self.specified_languages = languages

        # Generate run ID if output_dir not provided
        if output_dir is None:
            run_id = str(uuid.uuid4())[:8]
            output_dir = Path(f"data/{run_id}/readme_llm")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized README.LLM generator")
        logger.info(f"  Library: {library_name} {library_version}")
        logger.info(f"  Docs: {docs_path}")
        logger.info(f"  Output: {output_dir}")

    def generate(
        self,
        output_format: Literal["monolithic", "knowledge_base", "both"] = "both",
        max_contexts: int = 50
    ) -> ReadMeLLMOutput:
        """
        Run complete generation pipeline.

        Args:
            output_format: Which output(s) to generate
            max_contexts: Maximum API contexts in README.LLM

        Returns:
            ReadMeLLMOutput with metadata and paths
        """
        logger.info("=" * 80)
        logger.info("Starting README.LLM Generation")
        logger.info("=" * 80)

        # Step 1: Scan documentation
        logger.info("\n[1/7] Scanning documentation directory...")
        doc_files = scan_documentation(self.docs_path)
        logger.info(f"Found {len(doc_files)} documentation files")

        # Step 2: Detect languages
        logger.info("\n[2/7] Detecting programming languages...")
        if self.specified_languages:
            languages = self.specified_languages
            logger.info(f"Using specified languages: {', '.join(languages)}")
        else:
            languages = detect_languages(doc_files, introspectable_only=True)
            logger.info(f"Auto-detected languages: {', '.join(languages)}")

        if not languages:
            raise ValueError("No supported languages detected or specified")

        # Prepare data structures
        api_entries_by_language: Dict[str, List[APIEntry]] = {}
        example_entries_by_language: Dict[str, List[ExampleEntry]] = {}
        introspection_results = {}

        # Process each language
        for language in languages:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing Language: {language.upper()}")
            logger.info(f"{'=' * 80}")

            # Step 3: Introspect library
            logger.info(f"\n[3/7] Introspecting {self.library_name} ({language})...")
            introspection = introspect_library(
                library_name=self.library_name,
                version=self.library_version,
                language=language
            )
            introspection_results[language] = introspection
            logger.info(
                f"Discovered {len(introspection.apis)} APIs "
                f"({introspection.total_functions} functions, "
                f"{introspection.total_classes} classes, "
                f"{introspection.total_methods} methods)"
            )

            # Step 4: Extract code examples
            logger.info(f"\n[4/7] Extracting code examples ({language})...")
            all_examples_dict = extract_code_examples(doc_files, self.docs_path)

            # Flatten and filter by language
            all_examples = []
            for examples in all_examples_dict.values():
                all_examples.extend([ex for ex in examples if ex.language == language])

            logger.info(f"Extracted {len(all_examples)} {language} code examples")

            # Step 5: Resolve snippets
            logger.info(f"\n[5/7] Resolving snippet includes ({language})...")
            all_examples = resolve_snippets(all_examples, self.docs_path)
            snippet_count = sum(1 for ex in all_examples if ex.is_snippet)
            logger.info(f"Resolved {snippet_count} snippet includes")

            # Step 6: Match examples to APIs
            logger.info(f"\n[6/7] Matching examples to APIs ({language})...")
            api_to_examples, example_to_apis, complexity = match_examples_to_apis(
                all_examples, introspection
            )

            logger.info(
                f"Matched {len(example_to_apis)} examples to "
                f"{len(api_to_examples)} APIs"
            )

            # Build APIEntry objects
            api_entries = self._build_api_entries(
                introspection,
                api_to_examples,
                language
            )
            api_entries_by_language[language] = api_entries

            # Build ExampleEntry objects
            example_entries = self._build_example_entries(
                all_examples,
                example_to_apis,
                complexity,
                language
            )
            example_entries_by_language[language] = example_entries

        # Step 7: Generate outputs
        logger.info(f"\n[7/7] Generating outputs...")

        # Create library overview
        library_overview = self._create_library_overview(languages)

        # Generate README.LLM (monolithic XML)
        readme_llm_path = None
        if output_format in ("monolithic", "both"):
            readme_llm_path = self.output_dir / "README.LLM"
            for language in languages:
                # Generate per-language README.LLM
                lang_path = self.output_dir / f"README.LLM.{language}"
                generate_readme_llm(
                    library_overview=library_overview,
                    api_entries=api_entries_by_language[language],
                    example_entries={
                        ex.example_id: ex
                        for ex in example_entries_by_language[language]
                    },
                    output_path=lang_path,
                    language=language,
                    max_contexts=max_contexts
                )

            # Use first language for main README.LLM
            first_language = languages[0]
            generate_readme_llm(
                library_overview=library_overview,
                api_entries=api_entries_by_language[first_language],
                example_entries={
                    ex.example_id: ex
                    for ex in example_entries_by_language[first_language]
                },
                output_path=readme_llm_path,
                language=first_language,
                max_contexts=max_contexts
            )

            logger.info(f"Generated README.LLM: {readme_llm_path}")

        # Generate knowledge base (structured JSON)
        knowledge_base_path = None
        if output_format in ("knowledge_base", "both"):
            knowledge_base_path = self.output_dir / "knowledge_base"
            build_knowledge_base(
                output_dir=knowledge_base_path,
                library_overview=library_overview,
                api_entries_by_language=api_entries_by_language,
                example_entries_by_language=example_entries_by_language,
                generation_mode=self.generation_mode
            )

            logger.info(f"Generated knowledge base: {knowledge_base_path}")

        # Create output metadata
        output = ReadMeLLMOutput(
            run_id=self.output_dir.parent.name if "data/" in str(self.output_dir) else "standalone",
            library_name=self.library_name,
            library_version=self.library_version,
            languages=languages,
            generation_mode=self.generation_mode,
            timestamp=datetime.now().isoformat(),
            readme_llm_path=str(readme_llm_path) if readme_llm_path else "",
            knowledge_base_path=str(knowledge_base_path) if knowledge_base_path else "",
            total_apis=sum(len(apis) for apis in api_entries_by_language.values()),
            total_examples=sum(len(exs) for exs in example_entries_by_language.values()),
            apis_by_language={
                lang: len(apis)
                for lang, apis in api_entries_by_language.items()
            },
            examples_by_language={
                lang: len(exs)
                for lang, exs in example_entries_by_language.items()
            }
        )

        # Save output metadata
        metadata_path = self.output_dir / "generation_metadata.json"
        metadata_path.write_text(output.model_dump_json(indent=2), encoding='utf-8')

        logger.info("\n" + "=" * 80)
        logger.info("README.LLM Generation Complete!")
        logger.info("=" * 80)
        logger.info(f"Total APIs: {output.total_apis}")
        logger.info(f"Total Examples: {output.total_examples}")
        logger.info(f"Languages: {', '.join(languages)}")
        logger.info(f"Output directory: {self.output_dir}")

        return output

    def _build_api_entries(
        self,
        introspection,
        api_to_examples: Dict[str, List[str]],
        language: str
    ) -> List[APIEntry]:
        """Build APIEntry objects from introspection results."""
        api_entries = []

        for api_data in introspection.apis:
            api_id = api_data["api"]

            # Calculate importance score (heuristic)
            importance = self._calculate_importance(api_data, api_to_examples.get(api_id, []))

            # Extract parameters
            parameters = []
            # This would require parsing signatures - simplified for now
            # In a full implementation, would parse from introspection data

            # Create APIEntry
            entry = APIEntry(
                api_id=api_id,
                language=language,
                signature=api_data.get("signature", ""),
                description=f"API: {api_id}",  # Could extract from docstrings
                parameters=parameters,
                returns=None,  # Could extract from introspection
                examples=api_to_examples.get(api_id, []),
                importance_score=importance,
                tags=[api_data.get("type", "function")],
                related_apis=[],
                search_keywords=[api_id.split('.')[-1]],  # Last component as keyword
                source="introspection"
            )

            api_entries.append(entry)

        return api_entries

    def _build_example_entries(
        self,
        examples: List,
        example_to_apis: Dict[str, List[str]],
        complexity: Dict[str, str],
        language: str
    ) -> List[ExampleEntry]:
        """Build ExampleEntry objects from code examples."""
        example_entries = []

        for example in examples:
            entry = ExampleEntry(
                example_id=example.example_id,
                title=f"Example: {example.example_id}",
                code=example.code,
                language=language,
                apis_used=example_to_apis.get(example.example_id, []),
                use_case="general",  # Could infer from context
                complexity=complexity.get(example.example_id, "beginner"),
                tags=[],
                prerequisites=[],
                expected_output=None,
                validated=False,  # True only in integration mode
                execution_context={
                    "library_version": self.library_version,
                    "generation_method": self.generation_mode,
                    "timestamp": datetime.now().isoformat()
                },
                source_file=example.source_file,
                line_number=example.line_number
            )

            example_entries.append(entry)

        return example_entries

    def _calculate_importance(self, api_data: Dict, examples: List[str]) -> float:
        """Calculate importance score for an API (0.0 to 1.0)."""
        score = 0.5  # Base score

        # Boost for public/exported APIs
        if api_data.get("in_all", False):
            score += 0.2

        # Boost for having documentation
        if api_data.get("has_docstring", False):
            score += 0.1

        # Boost based on number of examples
        example_count = len(examples)
        if example_count > 0:
            score += min(0.2, example_count * 0.05)

        # Penalty for deprecated
        if api_data.get("is_deprecated", False):
            score -= 0.3

        # Boost for common patterns in name
        api_name = api_data["api"].lower()
        if any(word in api_name for word in ["connect", "create", "init", "open", "new"]):
            score += 0.1

        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, score))

    def _create_library_overview(self, languages: List[str]) -> LibraryOverview:
        """Create library overview from generation parameters."""
        return LibraryOverview(
            name=self.library_name,
            version=self.library_version,
            languages=languages,
            domain=None,  # Could infer or accept as parameter
            description=f"Documentation for {self.library_name} library",
            architecture=None,
            key_concepts=[],
            quickstart_summary=f"Install {self.library_name} and follow the examples"
        )
