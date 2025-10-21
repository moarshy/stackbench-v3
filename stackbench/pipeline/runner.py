"""
Pipeline runner that orchestrates the complete documentation validation workflow.

This module coordinates:
1. Repository cloning
2. Documentation extraction
3. API signature validation
4. Code example validation
"""

import uuid
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from stackbench.repository import RepositoryManager, RunContext
from stackbench.agents import (
    DocumentationExtractionAgent,
    APISignatureValidationAgent,
    CodeExampleValidationAgent,
    DocumentationClarityAgent,
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
        num_workers: int = 5,
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
            num_workers: Number of parallel workers for extraction (default: 5)
        """
        self.repo_url = repo_url
        self.branch = branch
        self.library_name = library_name
        self.library_version = library_version
        self.base_output_dir = Path(base_output_dir)
        self.include_folders = include_folders
        self.num_workers = num_workers

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
        print(f"   Run ID: {self.run_id}")

        self.run_context = self.repo_manager.clone_repository(
            repo_url=self.repo_url,
            branch=self.branch,
            run_id=self.run_id,
            library_name=self.library_name,
            library_version=self.library_version
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
        (self.run_context.results_dir / "clarity_validation").mkdir(exist_ok=True)

        # Create validation tracking log directory
        (self.run_context.run_dir / "validation_logs").mkdir(exist_ok=True)

        return self.run_context


    async def _estimate_and_sort_documents(self, md_files: List[Path]) -> List[Path]:
        """
        Estimate document processing time and sort longest-first.

        Uses file size as a proxy for processing time (larger docs take longer).

        Args:
            md_files: List of markdown file paths

        Returns:
            List of paths sorted by size (largest first)
        """
        doc_sizes = []
        for doc in md_files:
            size = doc.stat().st_size
            doc_sizes.append((doc, size))

        # Sort by size descending (largest first)
        doc_sizes.sort(key=lambda x: x[1], reverse=True)

        sorted_docs = [doc for doc, size in doc_sizes]

        print(f"\n📊 Document processing order (by size):")
        for i, (doc, size) in enumerate(doc_sizes[:10], 1):  # Show first 10
            kb = size / 1024
            print(f"   {i}. {doc.name:40s} ({kb:7.1f} KB)")
        if len(doc_sizes) > 10:
            print(f"   ... and {len(doc_sizes) - 10} more")

        return sorted_docs

    async def _process_document_end_to_end(self, doc_file: Path) -> Dict[str, Any]:
        """
        Run complete validation pipeline for a single document.

        Executes all four stages (extraction, API validation, code validation, clarity)
        for one document. If extraction fails, downstream stages are skipped.

        Args:
            doc_file: Path to markdown file to process

        Returns:
            Dict with results from all stages
        """
        doc_name = doc_file.stem
        start_time = datetime.now()

        # 1. EXTRACTION
        print(f"   📝 Extracting: {doc_file.name}")
        extraction_agent = DocumentationExtractionAgent(
            docs_folder=self.docs_folder,
            output_folder=self.run_context.results_dir / "extraction",
            repo_root=self.run_context.repo_dir,
            default_version=self.library_version,
            num_workers=1,
            validation_log_dir=self.run_context.run_dir / "validation_logs"
        )

        extraction_result = await extraction_agent.process_document(
            doc_file,
            library_name=self.library_name
        )

        # If extraction fails, skip downstream validation
        if not extraction_result:
            return {
                "document": doc_name,
                "status": "failed",
                "stage_failed": "extraction",
                "extraction": None,
                "api_validation": {"status": "skipped", "reason": "extraction failed"},
                "code_validation": {"status": "skipped", "reason": "extraction failed"},
                "clarity_validation": {"status": "skipped", "reason": "extraction failed"}
            }

        # 2. API VALIDATION
        print(f"   🔍 API validation: {doc_file.name}")
        extraction_file = self.run_context.results_dir / "extraction" / f"{doc_name}_analysis.json"

        api_agent = APISignatureValidationAgent(
            extraction_folder=self.run_context.results_dir / "extraction",
            output_folder=self.run_context.results_dir / "api_validation",
            num_workers=1,
            validation_log_dir=self.run_context.run_dir / "validation_logs"
        )

        api_result = await api_agent.validate_document(extraction_file)

        # 3. CODE VALIDATION
        print(f"   🧪 Code validation: {doc_file.name}")
        code_agent = CodeExampleValidationAgent(
            extraction_output_folder=self.run_context.results_dir / "extraction",
            validation_output_folder=self.run_context.results_dir / "code_validation",
            num_workers=1,
            validation_log_dir=self.run_context.run_dir / "validation_logs"
        )

        code_result = await code_agent.validate_document(extraction_file)

        # 4. CLARITY VALIDATION (requires extraction + API + Code)
        print(f"   📊 Clarity validation: {doc_file.name}")
        clarity_agent = DocumentationClarityAgent(
            extraction_folder=self.run_context.results_dir / "extraction",
            output_folder=self.run_context.results_dir / "clarity_validation",
            repository_folder=self.run_context.repo_dir,
            num_workers=1,
            validation_log_dir=self.run_context.run_dir / "validation_logs"
        )

        clarity_result = await clarity_agent.analyze_document(extraction_file)

        duration = (datetime.now() - start_time).total_seconds()
        print(f"   ✅ Completed {doc_file.name} in {duration:.1f}s")

        return {
            "document": doc_name,
            "status": "success",
            "duration_seconds": duration,
            "extraction": extraction_result,
            "api_validation": api_result,
            "code_validation": code_result,
            "clarity_validation": clarity_result
        }

    async def _worker(self, worker_id: int, document_queue: asyncio.Queue) -> List[Dict[str, Any]]:
        """
        Worker that processes documents from queue until empty.

        Each worker takes documents from the shared queue and runs the full
        pipeline (extract → API → code → clarity) for each document.

        Args:
            worker_id: Unique worker identifier (0 to num_workers-1)
            document_queue: Shared queue of documents to process

        Returns:
            List of results for all documents processed by this worker
        """
        worker_results = []

        while True:
            try:
                # Get next document (non-blocking with timeout)
                doc_file = await asyncio.wait_for(
                    document_queue.get(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                # Queue is empty
                break

            try:
                print(f"\n🔄 Worker {worker_id}: Processing {doc_file.name}")

                # Run full pipeline for this document
                result = await self._process_document_end_to_end(doc_file)

                worker_results.append(result)

            except Exception as e:
                print(f"❌ Worker {worker_id}: Failed {doc_file.name}: {e}")
                import traceback
                traceback.print_exc()

                worker_results.append({
                    "document": doc_file.stem,
                    "status": "failed",
                    "error": str(e)
                })

            finally:
                document_queue.task_done()

        print(f"🏁 Worker {worker_id}: No more documents, shutting down")
        return worker_results

    async def run(self) -> Dict[str, Any]:
        """
        Run the complete pipeline using worker pool pattern.

        Each worker processes documents end-to-end (extract → API → code → clarity).
        Documents are sorted longest-first to minimize idle time at end.

        Returns:
            Dict with all summaries
        """
        overall_start = datetime.now()

        # 1. Clone repository
        await self.clone_repository()

        # 2. Find all markdown files
        md_files = self.repo_manager.find_markdown_files(
            self.run_context,
            include_folders=self.include_folders
        )

        if not md_files:
            print("❌ No markdown files found")
            return {
                "run_id": self.run_id,
                "status": "failed",
                "reason": "no markdown files found"
            }

        # 3. Sort documents by size (longest first)
        sorted_docs = await self._estimate_and_sort_documents(md_files)

        # 4. Create shared document queue
        document_queue = asyncio.Queue()
        for doc in sorted_docs:
            await document_queue.put(doc)

        print(f"\n🚀 Launching {self.num_workers} workers to process {len(sorted_docs)} documents\n")

        # 5. Launch worker pool
        workers = [
            self._worker(worker_id, document_queue)
            for worker_id in range(self.num_workers)
        ]

        # 6. Wait for all workers to complete
        worker_results = await asyncio.gather(*workers)

        # 7. Flatten results from all workers
        all_results = [r for worker in worker_results for r in worker]

        overall_duration = (datetime.now() - overall_start).total_seconds()

        print(f"\n✨ Pipeline complete in {overall_duration:.1f}s ({overall_duration/60:.1f}m)")
        print(f"   Documents processed: {len([r for r in all_results if r['status'] == 'success'])}/{len(all_results)}")
        print(f"   Failed: {len([r for r in all_results if r['status'] == 'failed'])}")

        # Mark as complete
        if self.run_context:
            self.run_context.mark_analysis_completed()

        return {
            "run_id": self.run_id,
            "duration_seconds": overall_duration,
            "num_workers": self.num_workers,
            "total_documents": len(all_results),
            "successful": len([r for r in all_results if r['status'] == 'success']),
            "failed": len([r for r in all_results if r['status'] == 'failed']),
            "results": all_results
        }
