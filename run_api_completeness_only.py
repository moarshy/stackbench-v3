#!/usr/bin/env python3
"""
Standalone script to run ONLY the API completeness agent on an existing run.

Usage:
    python run_api_completeness_only.py <run_id>

Example:
    python run_api_completeness_only.py 22f67f53-8a51-4872-a541-28e085482756
"""

import asyncio
import sys
from pathlib import Path

# Add stackbench to path
sys.path.insert(0, str(Path(__file__).parent))

from stackbench.agents.api_completeness_agent import APICompletenessAgent


async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_api_completeness_only.py <run_id>")
        sys.exit(1)

    run_id = sys.argv[1]
    run_dir = Path(f"data/{run_id}")

    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        sys.exit(1)

    # Paths
    extraction_folder = run_dir / "results" / "extraction"
    output_folder = run_dir / "results" / "api_completeness"
    validation_log_dir = run_dir / "validation_logs"

    # Check extraction folder exists
    if not extraction_folder.exists():
        print(f"Error: Extraction folder not found: {extraction_folder}")
        sys.exit(1)

    # Create output folder if needed
    output_folder.mkdir(parents=True, exist_ok=True)
    validation_log_dir.mkdir(parents=True, exist_ok=True)

    # Read metadata for library info
    import json
    metadata_file = run_dir / "metadata.json"
    if not metadata_file.exists():
        print(f"Error: Metadata file not found: {metadata_file}")
        sys.exit(1)

    with open(metadata_file) as f:
        metadata = json.load(f)

    library_name = metadata.get("library_name")
    library_version = metadata.get("library_version")

    if not library_name or not library_version:
        print("Error: library_name or library_version not found in metadata")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"Running API Completeness Agent")
    print(f"{'='*80}")
    print(f"Run ID: {run_id}")
    print(f"Library: {library_name} v{library_version}")
    print(f"Extraction folder: {extraction_folder}")
    print(f"Output folder: {output_folder}")
    print(f"{'='*80}\n")

    # Create and run agent
    completeness_agent = APICompletenessAgent(
        extraction_folder=extraction_folder,
        output_folder=output_folder,
        library_name=library_name,
        library_version=library_version,
        language="python",
        validation_log_dir=validation_log_dir
    )

    print("Starting API completeness analysis...")
    result = await completeness_agent.analyze_completeness()

    print(f"\n{'='*80}")
    print("✅ API Completeness Analysis Complete!")
    print(f"{'='*80}")
    print(f"Output: {output_folder / 'completeness_analysis.json'}")
    print(f"Logs: {validation_log_dir / 'api_completeness_logs'}")
    print(f"{'='*80}\n")

    # Print summary
    if result:
        print("Summary:")
        print(f"  Total APIs: {result.coverage_summary.total_apis}")
        print(f"  Documented: {result.coverage_summary.documented} ({result.coverage_summary.coverage_percentage:.1f}%)")
        print(f"  With Examples: {result.coverage_summary.with_examples}")
        print(f"  Undocumented: {result.coverage_summary.undocumented}")
        if result.deprecated_in_docs:
            print(f"  ⚠️  Deprecated APIs in docs: {len(result.deprecated_in_docs)}")


if __name__ == "__main__":
    asyncio.run(main())
