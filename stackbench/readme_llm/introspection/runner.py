"""
Introspection runner for multi-language library API discovery.

Wraps existing introspection templates to provide a unified interface
for discovering library APIs across Python, TypeScript, JavaScript, Go, and Rust.

Creates isolated environments, installs libraries, runs templates, and
parses standardized JSON output.
"""

import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from stackbench.readme_llm.schemas import IntrospectionResult

logger = logging.getLogger(__name__)


class IntrospectionRunner:
    """
    Run language-specific introspection templates to discover library APIs.

    Handles:
    - Python: Creates venv, pip installs, runs python_introspect.py
    - TypeScript/JavaScript: Creates npm project, installs, runs typescript_introspect.ts
    - Go: Uses go mod, runs go_introspect.go (Phase 2)
    - Rust: Uses cargo, runs rust_introspect.rs (Phase 2)
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize introspection runner.

        Args:
            templates_dir: Directory containing introspection templates
                         (default: stackbench/introspection_templates/)
        """
        if templates_dir is None:
            # Default to templates directory in stackbench
            templates_dir = Path(__file__).parent.parent.parent / "introspection_templates"

        self.templates_dir = Path(templates_dir).resolve()

        if not self.templates_dir.exists():
            raise ValueError(f"Templates directory not found: {self.templates_dir}")

        logger.debug(f"Using introspection templates from: {self.templates_dir}")

    def introspect_library(
        self,
        library_name: str,
        version: str,
        language: str,
        modules: Optional[List[str]] = None
    ) -> IntrospectionResult:
        """
        Introspect a library to discover its API surface.

        Args:
            library_name: Name of library to introspect
            version: Version to install and introspect
            language: Programming language (python, typescript, javascript, go, rust)
            modules: Optional list of specific modules to introspect

        Returns:
            IntrospectionResult with API surface data

        Raises:
            ValueError: If language is not supported
            RuntimeError: If introspection fails
        """
        logger.info(f"Starting introspection: {library_name} {version} ({language})")

        # Dispatch to language-specific handler
        if language == 'python':
            return self._introspect_python(library_name, version, modules)
        elif language in ('typescript', 'javascript'):
            return self._introspect_typescript(library_name, version, modules)
        elif language == 'go':
            return self._introspect_go(library_name, version, modules)
        elif language == 'rust':
            return self._introspect_rust(library_name, version, modules)
        else:
            raise ValueError(f"Unsupported language: {language}")

    def _introspect_python(
        self,
        library_name: str,
        version: str,
        modules: Optional[List[str]] = None
    ) -> IntrospectionResult:
        """
        Introspect Python library using python_introspect.py template.

        Creates venv, installs library, runs introspection.

        Args:
            library_name: Python package name
            version: Version to install
            modules: Optional modules to introspect (default: [library_name])

        Returns:
            IntrospectionResult
        """
        template_path = self.templates_dir / "python_introspect.py"
        if not template_path.exists():
            raise FileNotFoundError(f"Python template not found: {template_path}")

        # Create temporary directory for isolated environment
        with tempfile.TemporaryDirectory(prefix="readme_llm_python_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            logger.debug(f"Created temporary environment: {tmpdir}")

            # Create virtual environment
            venv_path = tmpdir_path / "venv"
            logger.debug("Creating Python virtual environment...")
            subprocess.run(
                ["python3", "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True
            )

            # Determine pip and python paths in venv
            if subprocess.run(["uname"], capture_output=True).stdout.decode().strip() == "Darwin" or \
               subprocess.run(["uname"], capture_output=True).stdout.decode().startswith("Linux"):
                pip_path = venv_path / "bin" / "pip"
                python_path = venv_path / "bin" / "python"
            else:  # Windows
                pip_path = venv_path / "Scripts" / "pip.exe"
                python_path = venv_path / "Scripts" / "python.exe"

            # Install library
            package_spec = f"{library_name}=={version}"
            logger.info(f"Installing {package_spec}...")
            result = subprocess.run(
                [str(pip_path), "install", package_spec],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to install {package_spec}: {result.stderr}")

            # Run introspection template
            modules_args = modules or [library_name]
            cmd = [str(python_path), str(template_path), library_name, version] + modules_args

            logger.debug(f"Running introspection: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Introspection failed: {result.stderr}")

            # Parse JSON output
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse introspection output: {result.stdout[:500]}")
                raise RuntimeError(f"Invalid JSON output from introspection: {e}")

            # Convert to IntrospectionResult
            return IntrospectionResult(
                language="python",
                library_name=library_name,
                library_version=version,
                apis=output_data.get("apis", []),
                timestamp=datetime.now().isoformat(),
                introspection_method="inspect.signature",
                total_functions=output_data.get("by_type", {}).get("function", 0),
                total_classes=output_data.get("by_type", {}).get("class", 0),
                total_methods=output_data.get("by_type", {}).get("method", 0)
            )

    def _introspect_typescript(
        self,
        library_name: str,
        version: str,
        modules: Optional[List[str]] = None
    ) -> IntrospectionResult:
        """
        Introspect TypeScript/JavaScript library.

        Creates npm project, installs library, runs typescript_introspect.ts.

        Args:
            library_name: NPM package name
            version: Version to install
            modules: Optional modules to introspect

        Returns:
            IntrospectionResult
        """
        template_path = self.templates_dir / "typescript_introspect.ts"
        if not template_path.exists():
            raise FileNotFoundError(f"TypeScript template not found: {template_path}")

        # Create temporary npm project
        with tempfile.TemporaryDirectory(prefix="readme_llm_ts_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            logger.debug(f"Created temporary npm project: {tmpdir}")

            # Initialize npm project
            package_json = {
                "name": "introspection-temp",
                "version": "1.0.0",
                "private": True
            }
            (tmpdir_path / "package.json").write_text(json.dumps(package_json, indent=2))

            # Install library
            package_spec = f"{library_name}@{version}"
            logger.info(f"Installing {package_spec}...")
            result = subprocess.run(
                ["npm", "install", package_spec],
                cwd=tmpdir_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to install {package_spec}: {result.stderr}")

            # Install ts-node for running TypeScript
            subprocess.run(
                ["npm", "install", "ts-node", "typescript", "@types/node"],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Copy template to temp directory
            template_copy = tmpdir_path / "introspect.ts"
            shutil.copy(template_path, template_copy)

            # Run introspection
            modules_args = modules or []
            cmd = ["npx", "ts-node", "introspect.ts", library_name, version] + modules_args

            logger.debug(f"Running introspection: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                raise RuntimeError(f"Introspection failed: {result.stderr}")

            # Parse JSON output
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse output: {result.stdout[:500]}")
                raise RuntimeError(f"Invalid JSON output: {e}")

            return IntrospectionResult(
                language=output_data.get("language", "typescript"),
                library_name=library_name,
                library_version=version,
                apis=output_data.get("apis", []),
                timestamp=datetime.now().isoformat(),
                introspection_method="typescript-compiler-api",
                total_functions=output_data.get("by_type", {}).get("function", 0),
                total_classes=output_data.get("by_type", {}).get("class", 0),
                total_methods=output_data.get("by_type", {}).get("method", 0)
            )

    def _introspect_go(
        self,
        library_name: str,
        version: str,
        modules: Optional[List[str]] = None
    ) -> IntrospectionResult:
        """
        Introspect Go library using go_introspect.go template.

        Creates go mod project, installs module, runs introspection.

        Args:
            library_name: Go module name (e.g., github.com/user/lib)
            version: Version (e.g., v1.0.0)
            modules: Optional packages to introspect

        Returns:
            IntrospectionResult
        """
        template_path = self.templates_dir / "go_introspect.go"
        if not template_path.exists():
            raise FileNotFoundError(f"Go template not found: {template_path}")

        # Create temporary Go module
        with tempfile.TemporaryDirectory(prefix="readme_llm_go_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            logger.debug(f"Created temporary Go module: {tmpdir}")

            # Initialize Go module
            logger.debug("Initializing Go module...")
            subprocess.run(
                ["go", "mod", "init", "introspection-temp"],
                cwd=tmpdir_path,
                check=True,
                capture_output=True
            )

            # Install library
            module_spec = f"{library_name}@{version}"
            logger.info(f"Installing {module_spec}...")
            result = subprocess.run(
                ["go", "get", module_spec],
                cwd=tmpdir_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to install {module_spec}: {result.stderr}")

            # Copy template to temp directory
            template_copy = tmpdir_path / "introspect.go"
            shutil.copy(template_path, template_copy)

            # Run introspection
            modules_args = modules or ["."]
            cmd = ["go", "run", "introspect.go", library_name, version] + modules_args

            logger.debug(f"Running introspection: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                raise RuntimeError(f"Introspection failed: {result.stderr}")

            # Parse JSON output
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse output: {result.stdout[:500]}")
                raise RuntimeError(f"Invalid JSON output: {e}")

            return IntrospectionResult(
                language="go",
                library_name=library_name,
                library_version=version,
                apis=output_data.get("apis", []),
                timestamp=datetime.now().isoformat(),
                introspection_method="go/parser",
                total_functions=output_data.get("by_type", {}).get("function", 0),
                total_classes=output_data.get("by_type", {}).get("class", 0),
                total_methods=output_data.get("by_type", {}).get("method", 0)
            )

    def _introspect_rust(
        self,
        library_name: str,
        version: str,
        modules: Optional[List[str]] = None
    ) -> IntrospectionResult:
        """
        Introspect Rust crate using rust_introspect.rs template.

        Creates Cargo project, installs crate, runs introspection.

        Args:
            library_name: Crate name
            version: Version
            modules: Optional source files to introspect

        Returns:
            IntrospectionResult
        """
        template_path = self.templates_dir / "rust_introspect.rs"
        if not template_path.exists():
            raise FileNotFoundError(f"Rust template not found: {template_path}")

        # Create temporary Cargo project
        with tempfile.TemporaryDirectory(prefix="readme_llm_rust_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            logger.debug(f"Created temporary Rust project: {tmpdir}")

            # Initialize Cargo project
            logger.debug("Initializing Cargo project...")
            subprocess.run(
                ["cargo", "init", "--name", "introspection-temp"],
                cwd=tmpdir_path,
                check=True,
                capture_output=True
            )

            # Add library dependency to Cargo.toml
            cargo_toml = tmpdir_path / "Cargo.toml"
            cargo_content = cargo_toml.read_text()
            cargo_content += f'\n[dependencies]\n{library_name} = "{version}"\n'
            cargo_toml.write_text(cargo_content)

            # Install dependencies
            logger.info(f"Installing {library_name} {version}...")
            result = subprocess.run(
                ["cargo", "fetch"],
                cwd=tmpdir_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to install {library_name}: {result.stderr}")

            # Copy template
            template_copy = tmpdir_path / "introspect.rs"
            shutil.copy(template_path, template_copy)

            # Run introspection using cargo +nightly -Zscript if available,
            # otherwise compile and run
            modules_args = modules or []

            # Try nightly script first
            cmd = ["cargo", "+nightly", "-Zscript", str(template_copy), library_name, version] + modules_args

            logger.debug(f"Running introspection: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            # If nightly script fails, try standard compile
            if result.returncode != 0:
                logger.debug("Nightly script failed, trying standard compile...")
                # Compile
                compile_result = subprocess.run(
                    ["rustc", str(template_copy), "-o", str(tmpdir_path / "introspect")],
                    cwd=tmpdir_path,
                    capture_output=True,
                    text=True
                )

                if compile_result.returncode != 0:
                    raise RuntimeError(f"Failed to compile Rust introspection: {compile_result.stderr}")

                # Run
                cmd = [str(tmpdir_path / "introspect"), library_name, version] + modules_args
                result = subprocess.run(
                    cmd,
                    cwd=tmpdir_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

            if result.returncode != 0:
                raise RuntimeError(f"Introspection failed: {result.stderr}")

            # Parse JSON output
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse output: {result.stdout[:500]}")
                raise RuntimeError(f"Invalid JSON output: {e}")

            return IntrospectionResult(
                language="rust",
                library_name=library_name,
                library_version=version,
                apis=output_data.get("apis", []),
                timestamp=datetime.now().isoformat(),
                introspection_method="syn",
                total_functions=output_data.get("by_type", {}).get("function", 0),
                total_classes=output_data.get("by_type", {}).get("class", 0),
                total_methods=output_data.get("by_type", {}).get("method", 0)
            )


def introspect_library(
    library_name: str,
    version: str,
    language: str,
    modules: Optional[List[str]] = None
) -> IntrospectionResult:
    """
    Convenience function to introspect a library.

    Args:
        library_name: Library name
        version: Version to introspect
        language: Programming language
        modules: Optional specific modules

    Returns:
        IntrospectionResult with API surface

    Example:
        >>> result = introspect_library("lancedb", "0.25.2", "python")
        >>> print(f"Found {result.total_functions} functions")
        >>> print(f"APIs: {len(result.apis)}")
    """
    runner = IntrospectionRunner()
    return runner.introspect_library(library_name, version, language, modules)
