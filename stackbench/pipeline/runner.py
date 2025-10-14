"""
Pipeline runner that orchestrates the complete documentation validation workflow.

This module coordinates:
1. Repository cloning
2. Documentation extraction
3. API signature validation
4. Code example validation
"""

import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from stackbench.repository import RepositoryManager, RunContext
from stackbench.agents import (
    DocumentationExtractionAgent,
    APISignatureValidationAgent,
    CodeExampleValidationAgent,
    ExtractionSummary,
)


class DocumentationValidationPipeline:
    """Orchestrates the complete documentation validation pipeline."""

    def __init__(
        self,
        repo_url: str,
        branch: str,
        library_name: str,
        library_version: str,
        base_output_dir: Path,
        include_folders: Optional[List[str]] = None,
    ):
        """
        Initialize the validation pipeline.

        Args:
            repo_url: Git repository URL
            branch: Git branch to clone
            library_name: Primary library being documented
            library_version: Library version to validate against
            base_output_dir: Base directory for all outputs
            include_folders: Specific documentation folders to analyze
        """
        self.repo_url = repo_url
        self.branch = branch
        self.library_name = library_name
        self.library_version = library_version
        self.base_output_dir = Path(base_output_dir)
        self.include_folders = include_folders

        # Generate unique run ID
        self.run_id = str(uuid.uuid4())

        # Initialize repository manager
        self.repo_manager = RepositoryManager(base_data_dir=self.base_output_dir)

        # Will be set during execution
        self.run_context: Optional[RunContext] = None
        self.docs_folder: Optional[Path] = None

    async def clone_repository(self) -> RunContext:
        """
        Clone the repository and set up the run directory structure.

        Returns:
            RunContext with cloned repository
        """
        print(f"\n🔄 Cloning repository: {self.repo_url}")
        print(f"   Branch: {self.branch}")

        self.run_context = self.repo_manager.clone_repository(
            repo_url=self.repo_url,
            branch=self.branch
        )

        print(f"✅ Repository cloned to: {self.run_context.repo_dir}")

        # Find documentation files
        md_files = self.repo_manager.find_markdown_files(
            self.run_context,
            include_folders=self.include_folders
        )

        print(f"📄 Found {len(md_files)} documentation files")

        # Set docs folder based on include_folders
        if self.include_folders and len(self.include_folders) == 1:
            # Single folder specified - use it directly
            self.docs_folder = self.run_context.repo_dir / self.include_folders[0]
        else:
            # Multiple folders or none - use repo root
            self.docs_folder = self.run_context.repo_dir

        # Create output directories
        (self.run_context.results_dir / "extraction").mkdir(exist_ok=True)
        (self.run_context.results_dir / "api_validation").mkdir(exist_ok=True)
        (self.run_context.results_dir / "code_validation").mkdir(exist_ok=True)

        return self.run_context

    async def run_extraction(self) -> ExtractionSummary:
        """
        Run the documentation extraction agent.

        Returns:
            ExtractionSummary with all extracted signatures and examples
        """
        if not self.run_context:
            raise RuntimeError("Repository not cloned. Call clone_repository() first.")

        print(f"\n📝 Extracting API signatures and code examples...")
        print(f"   Library: {self.library_name} v{self.library_version}")
        print(f"   Docs folder: {self.docs_folder}")

        extraction_output = self.run_context.results_dir / "extraction"

        agent = DocumentationExtractionAgent(
            docs_folder=self.docs_folder,
            output_folder=extraction_output,
            repo_root=self.run_context.repo_dir,
            default_version=self.library_version
        )

        summary = await agent.process_all_documents(library_name=self.library_name)

        print(f"✅ Extraction complete:")
        print(f"   Documents: {summary.processed}/{summary.total_documents}")
        print(f"   Signatures: {summary.total_signatures}")
        print(f"   Examples: {summary.total_examples}")

        return summary

    async def run_api_validation(self) -> Dict[str, Any]:
        """
        Run the API signature validation agent.

        Returns:
            Dict with validation summary statistics
        """
        if not self.run_context:
            raise RuntimeError("Repository not cloned. Call clone_repository() first.")

        print(f"\n🔍 Validating API signatures against {self.library_name} v{self.library_version}...")

        extraction_output = self.run_context.results_dir / "extraction"
        validation_output = self.run_context.results_dir / "api_validation"

        agent = APISignatureValidationAgent(
            extraction_folder=extraction_output,
            output_folder=validation_output
        )

        await agent.validate_all_documents()

        # Load and return summary
        summary_file = validation_output / "validation_summary.json"
        if summary_file.exists():
            import json
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            print(f"✅ API validation complete:")
            print(f"   Valid: {summary['total_valid']}")
            print(f"   Invalid: {summary['total_invalid']}")
            print(f"   Not Found: {summary['total_not_found']}")
            return summary
        else:
            print(f"⚠️  No validation summary found")
            return {
                "total_signatures": 0,
                "total_valid": 0,
                "total_invalid": 0,
                "total_not_found": 0
            }

    async def run_code_validation(self) -> Dict[str, Any]:
        """
        Run the code example validation agent.

        Returns:
            Dict with validation summary statistics
        """
        if not self.run_context:
            raise RuntimeError("Repository not cloned. Call clone_repository() first.")

        print(f"\n📝 Validating code examples...")

        extraction_output = self.run_context.results_dir / "extraction"
        validation_output = self.run_context.results_dir / "code_validation"

        agent = CodeExampleValidationAgent(
            extraction_output_folder=extraction_output,
            validation_output_folder=validation_output
        )

        summary = await agent.validate_all_documents()

        print(f"✅ Code validation complete:")
        print(f"   Successful: {summary['successful']}")
        print(f"   Failed: {summary['failed']}")

        return summary

    async def run(self) -> Dict[str, Any]:
        """
        Run the complete pipeline.

        Returns:
            Dict with all summaries
        """
        # 1. Clone repository
        await self.clone_repository()

        # 2. Extract documentation
        extraction_summary = await self.run_extraction()

        # 3. Validate API signatures
        api_validation_summary = await self.run_api_validation()

        # 4. Validate code examples
        code_validation_summary = await self.run_code_validation()

        # Mark as complete
        if self.run_context:
            self.run_context.mark_analysis_completed()

        return {
            "run_id": self.run_id,
            "extraction": extraction_summary.model_dump() if hasattr(extraction_summary, 'model_dump') else extraction_summary,
            "api_validation": api_validation_summary,
            "code_validation": code_validation_summary,
        }
