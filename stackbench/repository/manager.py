"""Repository management for cloning and organizing API signature analysis runs."""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

import git


class RunContext:
    """Context for managing API signature analysis runs."""

    def __init__(
        self,
        run_id: str,
        repo_url: str,
        base_data_dir: Path,
        analysis_type: str = "api_signature"
    ):
        self.run_id = run_id
        self.repo_url = repo_url
        self.analysis_type = analysis_type
        self.base_data_dir = base_data_dir

        # Directory structure
        self.run_dir = base_data_dir / run_id
        self.repo_dir = self.run_dir / "repository"
        self.results_dir = self.run_dir / "results"
        self.cache_dir = self.run_dir / "cache"

        # Metadata
        self.created_at = datetime.now().isoformat()
        self.completed_at: Optional[str] = None
        self.status = "initializing"

    @classmethod
    def create(
        cls,
        repo_url: str,
        base_data_dir: Path,
        analysis_type: str = "api_signature"
    ) -> "RunContext":
        """Create a new run context with unique run ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        run_id = f"{analysis_type}_{repo_name}_{timestamp}"

        return cls(run_id, repo_url, base_data_dir, analysis_type)

    def create_directories(self) -> None:
        """Create necessary directories for the run."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.repo_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

        # Save context metadata
        self.save_metadata()

    def save_metadata(self) -> None:
        """Save run context metadata to JSON file."""
        metadata = {
            "run_id": self.run_id,
            "repo_url": self.repo_url,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status,
        }

        metadata_file = self.run_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def mark_clone_completed(self) -> None:
        """Mark repository cloning as completed."""
        self.status = "cloned"
        self.save_metadata()

    def mark_analysis_completed(self) -> None:
        """Mark analysis as completed."""
        self.status = "completed"
        self.completed_at = datetime.now().isoformat()
        self.save_metadata()

    @classmethod
    def load(cls, run_id: str, base_data_dir: Path) -> "RunContext":
        """Load existing run context by ID."""
        run_dir = base_data_dir / run_id
        metadata_file = run_dir / "metadata.json"

        if not metadata_file.exists():
            raise FileNotFoundError(f"Run context not found: {run_id}")

        with open(metadata_file) as f:
            metadata = json.load(f)

        context = cls(
            run_id=metadata["run_id"],
            repo_url=metadata["repo_url"],
            base_data_dir=base_data_dir,
            analysis_type=metadata.get("analysis_type", "api_signature")
        )
        context.created_at = metadata["created_at"]
        context.completed_at = metadata.get("completed_at")
        context.status = metadata["status"]

        return context


class RepositoryManager:
    """Manages repository cloning and run organization for API signature analysis."""

    def __init__(self, base_data_dir: Optional[Path] = None):
        """Initialize repository manager with data directory."""
        self.base_data_dir = base_data_dir or Path.cwd() / "data"
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

    def clone_repository(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> RunContext:
        """Clone repository and set up run directory structure.

        Args:
            repo_url: Git repository URL to clone
            branch: Git branch to clone (default: main)

        Returns:
            RunContext with cloned repository and directory structure
        """
        # Create run context with configuration
        context = RunContext.create(
            repo_url=repo_url,
            base_data_dir=self.base_data_dir
        )
        context.create_directories()

        try:
            # Clone repository with specific branch
            git.Repo.clone_from(repo_url, context.repo_dir, branch=branch)

            # Clean up non-essential files to save space and focus on relevant content
            self.cleanup_for_signature_analysis(context.repo_dir)

            # Mark clone as completed and save
            context.mark_clone_completed()

            return context

        except Exception as e:
            # Cleanup on failure
            if context.run_dir.exists():
                shutil.rmtree(context.run_dir)
            raise RuntimeError(f"Failed to clone repository {repo_url}: {e}")

    def cleanup_for_signature_analysis(self, repo_dir: Path) -> None:
        """Remove files not needed for signature analysis.

        Keeps: .py, .md, .mdx, .toml, .json, .yaml, .yml files
        Preserves: .git directory and its contents
        Removes: All other files and empty directories

        Args:
            repo_dir: Path to the cloned repository directory
        """
        # Extensions to keep for signature analysis
        allowed_extensions = {'.py', '.md', '.mdx', '.toml', '.json', '.yaml', '.yml', '.txt', '.rst'}
        preserved_dirs = {'.git'}

        # Walk the directory tree from bottom up to handle directory removal
        for root, dirs, files in os.walk(repo_dir, topdown=False):
            root_path = Path(root)

            # Skip .git directory and its contents
            if any(preserved_dir in root_path.parts for preserved_dir in preserved_dirs):
                continue

            # Remove files that don't match allowed extensions
            for file in files:
                file_path = root_path / file
                if file_path.suffix.lower() not in allowed_extensions:
                    try:
                        file_path.unlink()
                    except OSError:
                        # Skip files that can't be removed (permissions, etc.)
                        pass

            # Remove empty directories (but not the root repo directory)
            if root_path != repo_dir:
                try:
                    # Only remove if directory is empty
                    if not any(root_path.iterdir()):
                        root_path.rmdir()
                except OSError:
                    # Directory not empty or can't be removed
                    pass

    def find_python_files(self, context: RunContext) -> List[Path]:
        """Find all Python files in the cloned repository.

        Args:
            context: Run context with repository path

        Returns:
            List of Python file paths
        """
        python_files = []

        for root, _, files in os.walk(context.repo_dir):
            # Skip common non-source directories
            root_path = Path(root)
            relative_root = root_path.relative_to(context.repo_dir)

            # Skip test directories and virtual environments
            skip_dirs = {
                '__pycache__', '.pytest_cache', 'node_modules',
                '.venv', 'venv', '.env', 'env', 'build', 'dist',
                '.git', '.tox', '.mypy_cache'
            }

            if any(skip_dir in relative_root.parts for skip_dir in skip_dirs):
                continue

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    # Skip test files by convention
                    if not (file.startswith('test_') or file.endswith('_test.py') or 'test' in file_path.parts):
                        python_files.append(file_path)

        return python_files

    def find_markdown_files(self, context: RunContext, include_folders: Optional[List[str]] = None) -> List[Path]:
        """Find markdown files that likely contain API documentation.

        Args:
            context: Run context with repository path
            include_folders: Specific folders to include (e.g., ['docs', 'docs/examples'])

        Returns:
            List of markdown file paths
        """
        md_files = []

        for root, _, files in os.walk(context.repo_dir):
            # Prioritize documentation directories
            root_path = Path(root)
            relative_root = root_path.relative_to(context.repo_dir)

            # Skip .git directory
            if '.git' in relative_root.parts:
                continue

            # If include_folders is specified, only process those folders
            if include_folders:
                # Check if current path is within any of the included folders
                path_str = str(relative_root)
                if path_str == ".":
                    # Root directory - check if any include_folders are at root level
                    should_include = any(folder.count('/') == 0 for folder in include_folders)
                else:
                    # Check if current path starts with any of the included folders
                    should_include = any(
                        path_str.startswith(folder) or path_str == folder
                        for folder in include_folders
                    )

                if not should_include:
                    continue

            for file in files:
                if file.endswith(('.md', '.mdx')):
                    file_path = Path(root) / file

                    # Filter out non-API documentation
                    if not self._should_exclude_document(file_path):
                        md_files.append(file_path)

        return md_files

    def _should_exclude_document(self, file_path: Path) -> bool:
        """Check if a document should be excluded from analysis."""
        filename = file_path.name.lower()

        # Exclude common non-API documentation files
        exclude_patterns = [
            'changelog', 'history', 'news', 'authors', 'contributors',
            'license', 'copying', 'install', 'todo', 'issue', 'bug',
            'pull_request', 'pr_template', 'code_of_conduct'
        ]

        return any(pattern in filename for pattern in exclude_patterns)

    def load_run_context(self, run_id: str) -> RunContext:
        """Load existing run context by ID."""
        return RunContext.load(run_id, self.base_data_dir)

    def cleanup_run(self, run_id: str) -> None:
        """Remove a run directory and all its contents."""
        run_dir = self.base_data_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)

    def list_runs(self) -> List[str]:
        """List all available run IDs."""
        runs = []
        for item in self.base_data_dir.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                runs.append(item.name)
        return runs