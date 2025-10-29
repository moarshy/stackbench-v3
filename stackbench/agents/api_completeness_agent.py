"""
API Completeness & Deprecation Agent - Orchestrates 3-stage completeness analysis.

This orchestrator runs 3 sequential sub-agents:
1. IntrospectionAgent: Discovers APIs via library introspection → api_surface.json
2. MatchingAgent: Matches APIs to documentation → documented_apis.json + undocumented_apis.json
3. AnalysisAgent: Calculates metrics and builds final report → completeness_analysis.json

Each sub-agent is focused, testable, and produces intermediate JSON for debugging.
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from stackbench.agents.sub_agents import IntrospectionAgent, MatchingAgent, AnalysisAgent


class APICompletenessAgent:
    """Orchestrator for 3-stage API completeness analysis."""

    def __init__(
        self,
        docs_folder: Path,
        output_folder: Path,
        library_name: str,
        library_version: str,
        language: str = "python",
        extraction_folder: Optional[Path] = None,
        validation_log_dir: Optional[Path] = None
    ):
        """
        Initialize the completeness agent orchestrator.

        Args:
            docs_folder: Path to documentation root folder (scans ALL .md files)
            output_folder: Path to save completeness analysis
            library_name: Name of library to analyze
            library_version: Version to install and analyze
            language: Programming language (python, javascript, typescript)
            extraction_folder: Optional path to extraction results (for enrichment)
            validation_log_dir: Optional directory for validation hook tracking logs
        """
        self.docs_folder = Path(docs_folder)
        self.extraction_folder = Path(extraction_folder) if extraction_folder else None
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.library_name = library_name
        self.library_version = library_version
        self.language = language
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        print(f"🔍 API Completeness Agent - 3-Stage Pipeline")
        print(f"   Library: {library_name} v{library_version} ({language})")
        print(f"   Documentation folder: {docs_folder}")
        if self.extraction_folder:
            print(f"   Extraction folder: {extraction_folder} (for enrichment)")
        print(f"   Output folder: {output_folder}")

        if self.validation_log_dir:
            print(f"   Logging enabled: {self.validation_log_dir}")

    async def analyze_completeness(self):
        """
        Run 3-stage API completeness analysis.

        Stage 1: Introspection → api_surface.json
        Stage 2: Matching → documented_apis.json + undocumented_apis.json
        Stage 3: Analysis → completeness_analysis.json

        Returns:
            Dict with results from all 3 stages
        """
        start_time = datetime.now()

        print(f"\n{'='*80}")
        print(f"Starting 3-Stage API Completeness Analysis")
        print(f"{'='*80}\n")

        # Stage 1: Introspection
        print(f"{'='*80}")
        print(f"STAGE 1: API INTROSPECTION")
        print(f"{'='*80}")

        stage1_agent = IntrospectionAgent(
            output_folder=self.output_folder,
            library_name=self.library_name,
            library_version=self.library_version,
            language=self.language,
            validation_log_dir=self.validation_log_dir
        )

        stage1_result = await stage1_agent.run()
        api_surface_file = self.output_folder / "api_surface.json"

        print(f"\n{'='*80}")
        print(f"STAGE 2: API-TO-DOCUMENTATION MATCHING")
        print(f"{'='*80}")

        # Stage 2: Matching
        stage2_agent = MatchingAgent(
            api_surface_file=api_surface_file,
            docs_folder=self.docs_folder,
            output_folder=self.output_folder,
            language=self.language,
            extraction_folder=self.extraction_folder,
            validation_log_dir=self.validation_log_dir
        )

        stage2_result = await stage2_agent.run()
        documented_file = self.output_folder / "documented_apis.json"
        undocumented_file = self.output_folder / "undocumented_apis.json"

        print(f"\n{'='*80}")
        print(f"STAGE 3: METRICS & FINAL ANALYSIS")
        print(f"{'='*80}")

        # Stage 3: Analysis
        stage3_agent = AnalysisAgent(
            api_surface_file=api_surface_file,
            documented_file=documented_file,
            undocumented_file=undocumented_file,
            output_folder=self.output_folder,
            library_name=self.library_name,
            library_version=self.library_version,
            validation_log_dir=self.validation_log_dir
        )

        stage3_result = await stage3_agent.run()

        # Final summary
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        print(f"\n{'='*80}")
        print(f"3-STAGE PIPELINE COMPLETE")
        print(f"{'='*80}")
        print(f"Total Time: {processing_time}ms")
        print(f"\nOutputs:")
        print(f"  1. API Surface:       {api_surface_file}")
        print(f"  2. Documented APIs:   {documented_file}")
        print(f"  3. Undocumented APIs: {undocumented_file}")
        print(f"  4. Final Analysis:    {self.output_folder / 'completeness_analysis.json'}")
        print(f"\nSummary:")
        print(f"  Total APIs:       {stage1_result['total_apis']}")
        print(f"  Documented:       {stage2_result['documented_count']}")
        print(f"  Undocumented:     {stage2_result['undocumented_count']}")
        print(f"  Coverage:         {stage3_result['coverage_percentage']:.1f}%")
        print(f"{'='*80}\n")

        return {
            'stage1': stage1_result,
            'stage2': stage2_result,
            'stage3': stage3_result,
            'total_processing_time_ms': processing_time
        }


# This module is designed to be used as a library.
# For CLI usage, see stackbench.cli module.
