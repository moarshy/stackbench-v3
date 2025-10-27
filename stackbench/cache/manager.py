"""Cache manager for storing and retrieving validation run metadata.

This module provides a JSON-based caching system to avoid re-running
validations on the same documentation commit + library version combination.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class CacheManager:
    """Manages run caching using a JSON-based index."""

    def __init__(self, data_dir: Path):
        """Initialize cache manager.

        Args:
            data_dir: Base data directory containing runs
        """
        self.data_dir = Path(data_dir)
        self.cache_file = self.data_dir / "runs.json"

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize cache file if it doesn't exist
        if not self.cache_file.exists():
            self._write_cache({"runs": []})

    def _read_cache(self) -> Dict[str, Any]:
        """Read cache file."""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # If cache is corrupted or missing, reinitialize
            return {"runs": []}

    def _write_cache(self, cache_data: Dict[str, Any]) -> None:
        """Write cache file."""
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

    def _generate_cache_key(
        self,
        repo_url: str,
        doc_commit_hash: str,
        docs_path: Optional[str],
        library_name: str,
        library_version: str
    ) -> str:
        """Generate unique cache key.

        Format: repo_url:commit_hash:docs_path:library_name:library_version

        Args:
            repo_url: Git repository URL
            doc_commit_hash: Documentation commit hash
            docs_path: Base documentation path
            library_name: Library name
            library_version: Library version

        Returns:
            Cache key string
        """
        docs_path_part = docs_path or "root"
        return f"{repo_url}:{doc_commit_hash}:{docs_path_part}:{library_name}:{library_version}"

    def get_cached_run(
        self,
        repo_url: str,
        doc_commit_hash: str,
        docs_path: Optional[str],
        library_name: str,
        library_version: str
    ) -> Optional[str]:
        """Check if a run exists in cache.

        Args:
            repo_url: Git repository URL
            doc_commit_hash: Documentation commit hash
            docs_path: Base documentation path
            library_name: Library name
            library_version: Library version

        Returns:
            run_id if cache hit, None if cache miss
        """
        cache_key = self._generate_cache_key(
            repo_url, doc_commit_hash, docs_path, library_name, library_version
        )

        cache_data = self._read_cache()

        # Search for matching run
        for run in cache_data.get("runs", []):
            run_cache_key = self._generate_cache_key(
                run["repo_url"],
                run["doc_commit_hash"],
                run.get("docs_path"),
                run["library_name"],
                run["library_version"]
            )

            if run_cache_key == cache_key and run["status"] == "completed":
                return run["run_id"]

        return None

    def add_run(
        self,
        run_id: str,
        repo_url: str,
        branch: str,
        doc_commit_hash: str,
        docs_path: Optional[str],
        include_folders: List[str],
        library_name: str,
        library_version: str,
        timestamp: Optional[str] = None,
        status: str = "initializing"
    ) -> None:
        """Add a run to the cache.

        Args:
            run_id: Unique run identifier
            repo_url: Git repository URL
            branch: Git branch
            doc_commit_hash: Documentation commit hash
            docs_path: Base documentation path
            include_folders: List of folders analyzed
            library_name: Library name
            library_version: Library version
            timestamp: ISO timestamp (defaults to now)
            status: Run status (default: initializing)
        """
        cache_data = self._read_cache()

        # Check if run already exists
        existing_run = next(
            (r for r in cache_data["runs"] if r["run_id"] == run_id),
            None
        )

        run_entry = {
            "run_id": run_id,
            "repo_url": repo_url,
            "branch": branch,
            "doc_commit_hash": doc_commit_hash,
            "docs_path": docs_path,
            "include_folders": include_folders,
            "library_name": library_name,
            "library_version": library_version,
            "timestamp": timestamp or datetime.now().isoformat(),
            "status": status,
            "run_dir": str(self.data_dir / run_id)
        }

        if existing_run:
            # Update existing run
            cache_data["runs"].remove(existing_run)

        cache_data["runs"].append(run_entry)

        # Sort by timestamp (newest first)
        cache_data["runs"].sort(key=lambda r: r["timestamp"], reverse=True)

        self._write_cache(cache_data)

    def update_run_status(self, run_id: str, status: str) -> None:
        """Update the status of a run.

        Args:
            run_id: Run identifier
            status: New status value
        """
        cache_data = self._read_cache()

        for run in cache_data["runs"]:
            if run["run_id"] == run_id:
                run["status"] = status
                break

        self._write_cache(cache_data)

    def list_runs(
        self,
        repo_url: Optional[str] = None,
        library_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all cached runs, optionally filtered.

        Args:
            repo_url: Filter by repository URL
            library_name: Filter by library name

        Returns:
            List of run metadata dictionaries
        """
        cache_data = self._read_cache()
        runs = cache_data.get("runs", [])

        # Apply filters
        if repo_url:
            runs = [r for r in runs if r["repo_url"] == repo_url]

        if library_name:
            runs = [r for r in runs if r["library_name"] == library_name]

        return runs

    def get_run_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific run.

        Args:
            run_id: Run identifier

        Returns:
            Run metadata dictionary or None if not found
        """
        cache_data = self._read_cache()

        for run in cache_data["runs"]:
            if run["run_id"] == run_id:
                return run

        return None

    def invalidate_cache(self, run_id: str) -> bool:
        """Remove a run from the cache.

        Args:
            run_id: Run identifier to remove

        Returns:
            True if run was found and removed, False otherwise
        """
        cache_data = self._read_cache()

        # Find and remove run
        run_to_remove = next(
            (r for r in cache_data["runs"] if r["run_id"] == run_id),
            None
        )

        if run_to_remove:
            cache_data["runs"].remove(run_to_remove)
            self._write_cache(cache_data)
            return True

        return False
