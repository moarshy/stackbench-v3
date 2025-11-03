"""
Stackbench CLI - Documentation Quality Validation Tool

A command-line tool for validating documentation quality by:
1. Extracting API signatures and code examples from documentation
2. Validating API signatures against actual library implementations
3. Validating code examples by executing them
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from stackbench.pipeline.runner import DocumentationValidationPipeline

app = typer.Typer(
    name="stackbench",
    help="Documentation Quality Validation Tool",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    repo: str = typer.Option(..., "--repo", "-r", help="Git repository URL"),
    branch: str = typer.Option("main", "--branch", "-b", help="Git branch to clone"),
    commit: Optional[str] = typer.Option(
        None,
        "--commit",
        "-c",
        help="Git commit hash (optional - if not provided, resolves from branch HEAD)",
    ),
    docs_path: str = typer.Option(..., "--docs-path", "-d", help="Base documentation directory (e.g., 'docs/src')"),
    include_folders: Optional[str] = typer.Option(
        None,
        "--include-folders",
        "-i",
        help="Comma-separated list of folders relative to docs-path (e.g., 'python,javascript')",
    ),
    library: str = typer.Option(..., "--library", "-l", help="Primary library name (e.g., lancedb, fastapi)"),
    version: str = typer.Option(..., "--version", "-v", help="Library version to test against (e.g., 0.25.2)"),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./data)",
    ),
    num_workers: int = typer.Option(
        5,
        "--num-workers",
        "-w",
        help="Number of parallel workers (default: 5)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Bypass cache and force re-analysis",
    ),
):
    """
    Run complete documentation validation pipeline.

    This command will:
    1. Clone the repository (resolves commit hash if not provided)
    2. Extract API signatures and code examples from documentation
    3. Validate API signatures against the actual library
    4. Validate code examples by executing them
    5. Validate documentation clarity and structure

    Each worker processes one document end-to-end (extract → API → code → clarity).
    Documents are sorted longest-first to minimize idle worker time.

    Example (latest commit):
        stackbench run \\
            --repo https://github.com/lancedb/lancedb \\
            --branch main \\
            --docs-path docs/src \\
            --include-folders python \\
            --library lancedb \\
            --version 0.25.2

    Example (specific commit):
        stackbench run \\
            --repo https://github.com/lancedb/lancedb \\
            --commit fe25922 \\
            --docs-path docs/src \\
            --include-folders python,javascript \\
            --library lancedb \\
            --version 0.25.2
    """

    # Parse include_folders
    include_folders_list = None
    if include_folders:
        include_folders_list = [f.strip() for f in include_folders.split(",")]

    # Set output directory (resolve to absolute path)
    output_dir = Path(output).resolve() if output else Path("./data").resolve()

    # Display header
    commit_display = f"Commit: [yellow]{commit}[/yellow]\n" if commit else ""
    console.print(Panel.fit(
        "[bold cyan]Stackbench Documentation Quality Validation[/bold cyan]\n\n"
        f"Repository: [yellow]{repo}[/yellow]\n"
        f"Branch: [yellow]{branch}[/yellow]\n"
        f"{commit_display}"
        f"Docs Path: [yellow]{docs_path}[/yellow]\n"
        f"Include Folders: [yellow]{include_folders or 'all'}[/yellow]\n"
        f"Library: [yellow]{library}[/yellow] v[yellow]{version}[/yellow]\n"
        f"Output: [yellow]{output_dir}[/yellow]\n"
        f"Workers: [yellow]{num_workers}[/yellow]",
        border_style="cyan"
    ))

    # Run pipeline
    try:
        asyncio.run(_run_pipeline(
            repo=repo,
            branch=branch,
            commit=commit,
            docs_path=docs_path,
            include_folders=include_folders_list,
            library=library,
            version=version,
            output_dir=output_dir,
            num_workers=num_workers,
            force=force,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Pipeline interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


async def _run_pipeline(
    repo: str,
    branch: str,
    commit: Optional[str],
    docs_path: str,
    include_folders: Optional[List[str]],
    library: str,
    version: str,
    output_dir: Path,
    num_workers: int,
    force: bool,
):
    """Run the validation pipeline with worker pool."""

    # Create pipeline
    pipeline = DocumentationValidationPipeline(
        repo_url=repo,
        branch=branch,
        commit=commit,
        docs_path=docs_path,
        include_folders=include_folders,
        library_name=library,
        library_version=version,
        base_output_dir=output_dir,
        num_workers=num_workers,
    )

    # Run worker pool pipeline
    result = await pipeline.run(force=force)

    # Display summary
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✨ Pipeline Complete![/bold green]",
        border_style="green"
    ))

    console.print(f"\n[bold]📊 Results[/bold]")
    console.print(f"   Duration: [cyan]{result['duration_seconds']:.1f}s ({result['duration_seconds']/60:.1f}m)[/cyan]")
    console.print(f"   Workers: [cyan]{result['num_workers']}[/cyan]")
    console.print(f"   Documents: [green]{result['successful']}[/green] successful, [red]{result['failed']}[/red] failed")

    console.print(f"\n[bold]📁 Results saved to:[/bold] [cyan]{pipeline.run_context.run_dir}[/cyan]")
    console.print(f"   • Extraction: [cyan]{pipeline.run_context.results_dir / 'extraction'}[/cyan]")
    console.print(f"   • API Validation: [cyan]{pipeline.run_context.results_dir / 'api_validation'}[/cyan]")
    console.print(f"   • Code Validation: [cyan]{pipeline.run_context.results_dir / 'code_validation'}[/cyan]")
    console.print(f"   • Clarity Validation: [cyan]{pipeline.run_context.results_dir / 'clarity_validation'}[/cyan]")


@app.command()
def rerun_clarity(
    run_id: str = typer.Argument(..., help="Run ID from data folder (e.g., 5bd8e375-313e-4328-827b-33889356828c)"),
    num_workers: int = typer.Option(5, "--workers", "-w", help="Number of parallel workers"),
):
    """
    Rerun only the clarity validation for an existing run.

    This is useful after updating the clarity agent or MCP scoring server.
    Requires that extraction, API validation, and code validation have already completed.
    """
    import json
    from stackbench.agents.clarity_agent import DocumentationClarityAgent

    console.print("\n[bold cyan]📊 Rerunning Clarity Validation[/bold cyan]\n")

    # Locate run directory
    data_dir = Path("data")
    run_dir = data_dir / run_id

    if not run_dir.exists():
        console.print(f"[red]❌ Run directory not found: {run_dir}[/red]")
        raise typer.Exit(1)

    # Check required directories exist
    extraction_dir = run_dir / "results" / "extraction"
    results_dir = run_dir / "results"
    repository_dir = run_dir / "repository"
    output_dir = run_dir / "results" / "clarity_validation"
    validation_log_dir = run_dir / "validation_logs"

    if not extraction_dir.exists():
        console.print(f"[red]❌ Extraction results not found: {extraction_dir}[/red]")
        console.print("Run the full pipeline first with: stackbench run ...")
        raise typer.Exit(1)

    if not repository_dir.exists():
        console.print(f"[red]❌ Repository not found: {repository_dir}[/red]")
        raise typer.Exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Run ID:[/bold] {run_id}")
    console.print(f"[bold]Extraction:[/bold] {extraction_dir}")
    console.print(f"[bold]Repository:[/bold] {repository_dir}")
    console.print(f"[bold]Output:[/bold] {output_dir}")
    console.print(f"[bold]Workers:[/bold] {num_workers}\n")

    # Run clarity validation
    try:
        agent = DocumentationClarityAgent(
            extraction_folder=extraction_dir,
            output_folder=output_dir,
            repository_folder=repository_dir,
            num_workers=num_workers,
            validation_log_dir=validation_log_dir
        )

        console.print("[bold]Running clarity validation with MCP scoring...[/bold]\n")

        summary = asyncio.run(agent.analyze_all_documents())

        console.print("\n[bold green]✓ Clarity validation complete![/bold green]")
        console.print(f"\n[bold]📊 Results:[/bold]")
        console.print(f"  • Documents analyzed: {summary['total_documents']}")
        console.print(f"  • Average score: {summary['average_clarity_score']:.1f}/10")
        console.print(f"  • Critical issues: {summary['critical_issues']}")
        console.print(f"  • Warnings: {summary['warnings']}")
        console.print(f"  • Duration: {summary['validation_duration_seconds']:.1f}s\n")
        console.print(f"[bold]📁 Results saved to:[/bold] [cyan]{output_dir}[/cyan]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def version():
    """Show the version of stackbench."""
    console.print("[bold cyan]Stackbench[/bold cyan] v0.1.0")
    console.print("Documentation Quality Validation Tool")


# ============================================================================
# WALKTHROUGH COMMANDS
# ============================================================================

walkthrough_app = typer.Typer(
    name="walkthrough",
    help="Generate and audit interactive documentation walkthroughs",
)
app.add_typer(walkthrough_app, name="walkthrough")


@walkthrough_app.command("generate")
def walkthrough_generate(
    doc_path: str = typer.Option(..., "--doc-path", "-d", help="Path to documentation file (relative to repo root)"),
    library: str = typer.Option(..., "--library", "-l", help="Primary library name"),
    version: str = typer.Option(..., "--version", "-v", help="Library version"),
    from_run: Optional[str] = typer.Option(
        None,
        "--from-run",
        help="Reuse existing run UUID (from core pipeline)",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Git repository URL (for fresh clone)",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Git branch to clone (default: main)",
    ),
):
    """
    Generate a walkthrough from documentation.

    This command analyzes tutorial/quickstart documentation and creates
    a structured walkthrough JSON file with step-by-step instructions.

    Two modes:
    1. From existing run: --from-run <uuid> (reuses cloned repo)
    2. Fresh clone: --repo <url> --branch <branch> (clones new repo)

    Example (from existing run):
        stackbench walkthrough generate \\
            --from-run 22c09315-1385-4ad6-a2ff-1e631a482107 \\
            --doc-path docs/quickstart.md \\
            --library lancedb \\
            --version 0.25.2

    Example (fresh clone):
        stackbench walkthrough generate \\
            --repo https://github.com/lancedb/lancedb \\
            --branch main \\
            --doc-path docs/quickstart.md \\
            --library lancedb \\
            --version 0.25.2
    """
    from stackbench.walkthroughs.walkthrough_generate_agent import WalkthroughGenerateAgent
    from stackbench.repository import RepositoryManager

    # Validate: Must have either --from-run OR --repo
    if not from_run and not repo:
        console.print("[red]❌ Error: Must specify either --from-run or --repo[/red]")
        raise typer.Exit(1)

    if from_run and repo:
        console.print("[red]❌ Error: Cannot specify both --from-run and --repo[/red]")
        raise typer.Exit(1)

    # Generate walkthrough ID
    walkthrough_id = f"wt_{uuid.uuid4().hex[:8]}"

    base_data_dir = Path("./data")

    try:
        # Scenario 1: From existing run
        if from_run:
            parent_run_dir = base_data_dir / from_run
            if not parent_run_dir.exists():
                console.print(f"[red]❌ Run not found: {from_run}[/red]")
                raise typer.Exit(1)

            repo_dir = parent_run_dir / "repository"
            if not repo_dir.exists():
                console.print(f"[red]❌ Repository not found in run: {from_run}[/red]")
                raise typer.Exit(1)

            # Create walkthroughs directory
            walkthroughs_dir = parent_run_dir / "walkthroughs"
            walkthroughs_dir.mkdir(exist_ok=True)

            # Create specific walkthrough directory
            walkthrough_dir = walkthroughs_dir / walkthrough_id
            walkthrough_dir.mkdir(exist_ok=True)

            # Display header
            console.print(Panel.fit(
                "[bold cyan]Walkthrough Generation (From Existing Run)[/bold cyan]\n\n"
                f"Parent Run: [yellow]{from_run}[/yellow]\n"
                f"Repository: [yellow]{repo_dir}[/yellow]\n"
                f"Documentation: [yellow]{doc_path}[/yellow]\n"
                f"Library: [yellow]{library}[/yellow] v[yellow]{version}[/yellow]\n"
                f"Walkthrough ID: [yellow]{walkthrough_id}[/yellow]\n"
                f"Output: [yellow]{walkthrough_dir}[/yellow]",
                border_style="cyan"
            ))

            # Resolve doc path relative to repo
            doc_path_full = repo_dir / doc_path
            if not doc_path_full.exists():
                console.print(f"[red]❌ Documentation not found: {doc_path_full}[/red]")
                raise typer.Exit(1)

            # Create agent
            agent = WalkthroughGenerateAgent(
                output_folder=walkthrough_dir,
                library_name=library,
                library_version=version,
            )

            # Generate walkthrough
            asyncio.run(agent.generate_walkthrough(doc_path_full, walkthrough_id))

            console.print(f"\n[bold green]✨ Generation complete![/bold green]")
            console.print(f"   Output: [cyan]{walkthrough_dir}[/cyan]")

        # Scenario 2: Fresh clone
        else:
            # Create new run directory
            run_id = str(uuid.uuid4())
            run_dir = base_data_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            # Clone repository
            console.print(f"\n🔄 Cloning repository: {repo}")

            repo_manager = RepositoryManager(base_data_dir=base_data_dir)
            run_context = repo_manager.clone_repository(
                repo_url=repo,
                branch=branch,
                run_id=run_id,
                library_name=library,
                library_version=version
            )

            repo_dir = run_context.repo_dir

            # Create walkthroughs directory
            walkthroughs_dir = run_dir / "walkthroughs"
            walkthroughs_dir.mkdir(exist_ok=True)

            # Create specific walkthrough directory
            walkthrough_dir = walkthroughs_dir / walkthrough_id
            walkthrough_dir.mkdir(exist_ok=True)

            # Display header
            console.print(Panel.fit(
                "[bold cyan]Walkthrough Generation (Fresh Clone)[/bold cyan]\n\n"
                f"Repository: [yellow]{repo}[/yellow]\n"
                f"Branch: [yellow]{branch}[/yellow]\n"
                f"Run ID: [yellow]{run_id}[/yellow]\n"
                f"Documentation: [yellow]{doc_path}[/yellow]\n"
                f"Library: [yellow]{library}[/yellow] v[yellow]{version}[/yellow]\n"
                f"Walkthrough ID: [yellow]{walkthrough_id}[/yellow]\n"
                f"Output: [yellow]{walkthrough_dir}[/yellow]",
                border_style="cyan"
            ))

            # Resolve doc path relative to repo
            doc_path_full = repo_dir / doc_path
            if not doc_path_full.exists():
                console.print(f"[red]❌ Documentation not found: {doc_path_full}[/red]")
                raise typer.Exit(1)

            # Create agent
            agent = WalkthroughGenerateAgent(
                output_folder=walkthrough_dir,
                library_name=library,
                library_version=version,
            )

            # Generate walkthrough
            asyncio.run(agent.generate_walkthrough(doc_path_full, walkthrough_id))

            console.print(f"\n[bold green]✨ Generation complete![/bold green]")
            console.print(f"   Run ID: [cyan]{run_id}[/cyan]")
            console.print(f"   Output: [cyan]{walkthrough_dir}[/cyan]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@walkthrough_app.command("audit")
def walkthrough_audit(
    walkthrough_path: str = typer.Option(..., "--walkthrough", "-w", help="Path to walkthrough JSON file"),
    library: str = typer.Option(..., "--library", "-l", help="Library name"),
    version: str = typer.Option(..., "--version", "-v", help="Library version"),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: same as walkthrough)",
    ),
    working_dir: Optional[str] = typer.Option(
        None,
        "--working-dir",
        help="Working directory for execution (default: temp dir)",
    ),
):
    """
    Audit a walkthrough by executing it step-by-step.

    This command uses a Claude Code agent to follow the walkthrough
    and identify gaps, unclear instructions, and documentation issues.

    Example:
        stackbench walkthrough audit \\
            --walkthrough ./data/wt_abc123/walkthrough.json \\
            --library lancedb \\
            --version 0.25.2
    """
    from stackbench.walkthroughs.walkthrough_audit_agent import WalkthroughAuditAgent

    walkthrough_path_obj = Path(walkthrough_path)
    if not walkthrough_path_obj.exists():
        console.print(f"[red]❌ Walkthrough file not found: {walkthrough_path}[/red]")
        raise typer.Exit(1)

    # Set output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = walkthrough_path_obj.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # Set working directory
    working_dir_obj = Path(working_dir) if working_dir else None

    # Display header
    console.print(Panel.fit(
        "[bold cyan]Walkthrough Audit[/bold cyan]\n\n"
        f"Walkthrough: [yellow]{walkthrough_path}[/yellow]\n"
        f"Library: [yellow]{library}[/yellow] v[yellow]{version}[/yellow]\n"
        f"Output: [yellow]{output_dir}[/yellow]",
        border_style="cyan"
    ))

    try:
        # Create agent
        agent = WalkthroughAuditAgent(
            output_folder=output_dir,
            library_name=library,
            library_version=version,
        )

        # Run audit
        result = asyncio.run(agent.audit_walkthrough(
            walkthrough_path=walkthrough_path_obj,
            working_directory=working_dir_obj
        ))

        # Display results
        console.print("\n")
        console.print(Panel.fit(
            "[bold green]✨ Audit Complete![/bold green]",
            border_style="green"
        ))

        # Display audit summary
        console.print("\n[bold]📊 Audit Summary[/bold]")
        audit_table = Table(show_header=True, header_style="bold cyan")
        audit_table.add_column("Metric")
        audit_table.add_column("Value", justify="right")

        audit_table.add_row("Steps Completed", f"{result.completed_steps}/{result.total_steps}")
        audit_table.add_row("Success", "[green]Yes[/green]" if result.success else "[red]No[/red]")
        audit_table.add_row("Duration", f"{result.duration_seconds:.1f}s")
        audit_table.add_row("Total Gaps", str(len(result.gaps)))

        console.print(audit_table)

        # Display gaps by severity
        if len(result.gaps) > 0:
            console.print("\n[bold]🚨 Gaps by Severity[/bold]")
            gaps_table = Table(show_header=True, header_style="bold cyan")
            gaps_table.add_column("Severity")
            gaps_table.add_column("Count", justify="right")

            gaps_table.add_row("[red]Critical", str(result.critical_gaps))
            gaps_table.add_row("[yellow]Warning", str(result.warning_gaps))
            gaps_table.add_row("[cyan]Info", str(result.info_gaps))

            console.print(gaps_table)

            # Display gaps by type
            console.print("\n[bold]📋 Gaps by Type[/bold]")
            type_table = Table(show_header=True, header_style="bold cyan")
            type_table.add_column("Type")
            type_table.add_column("Count", justify="right")

            type_table.add_row("Clarity", str(result.clarity_gaps))
            type_table.add_row("Prerequisite", str(result.prerequisite_gaps))
            type_table.add_row("Logical Flow", str(result.logical_flow_gaps))
            type_table.add_row("Execution Error", str(result.execution_gaps))
            type_table.add_row("Completeness", str(result.completeness_gaps))
            type_table.add_row("Cross-Reference", str(result.cross_reference_gaps))

            console.print(type_table)

        console.print(f"\n[bold]📁 Results saved to:[/bold] [cyan]{output_dir}[/cyan]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@walkthrough_app.command("run")
def walkthrough_run(
    doc_path: str = typer.Option(..., "--doc-path", "-d", help="Path to documentation file or folder"),
    library: str = typer.Option(..., "--library", "-l", help="Primary library name"),
    version: str = typer.Option(..., "--version", "-v", help="Library version"),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./data/wt_<UUID>)",
    ),
    working_dir: Optional[str] = typer.Option(
        None,
        "--working-dir",
        help="Working directory for audit execution (default: temp dir)",
    ),
):
    """
    Generate and audit a walkthrough (full pipeline).

    This command combines generation and audit into a single workflow.

    Example:
        stackbench walkthrough run \\
            --doc-path docs/quickstart.md \\
            --library lancedb \\
            --version 0.25.2
    """
    from stackbench.walkthroughs.walkthrough_generate_agent import WalkthroughGenerateAgent
    from stackbench.walkthroughs.walkthrough_audit_agent import WalkthroughAuditAgent

    # Generate walkthrough ID
    walkthrough_id = f"wt_{uuid.uuid4().hex[:8]}"

    # Set output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path("./data") / walkthrough_id

    output_dir.mkdir(parents=True, exist_ok=True)

    # Display header
    console.print(Panel.fit(
        "[bold cyan]Walkthrough Full Pipeline[/bold cyan]\n\n"
        f"Documentation: [yellow]{doc_path}[/yellow]\n"
        f"Library: [yellow]{library}[/yellow] v[yellow]{version}[/yellow]\n"
        f"Output: [yellow]{output_dir}[/yellow]\n"
        f"Walkthrough ID: [yellow]{walkthrough_id}[/yellow]",
        border_style="cyan"
    ))

    try:
        # Phase 1: Generate
        console.print("\n[bold cyan]📝 Phase 1: Generating Walkthrough[/bold cyan]")
        generate_agent = WalkthroughGenerateAgent(
            output_folder=output_dir,
            library_name=library,
            library_version=version,
        )

        doc_path_obj = Path(doc_path)
        if not doc_path_obj.exists():
            console.print(f"[red]❌ Path not found: {doc_path}[/red]")
            raise typer.Exit(1)

        if doc_path_obj.is_file():
            walkthrough_export = asyncio.run(generate_agent.generate_walkthrough(doc_path_obj, walkthrough_id))
            walkthrough_file = output_dir / f"{walkthrough_id}.json"
        else:
            console.print(f"[red]❌ Full pipeline only supports single file. Use 'generate' for folders.[/red]")
            raise typer.Exit(1)

        console.print(f"[green]✅ Walkthrough generated[/green]")

        # Phase 2: Audit
        console.print("\n[bold cyan]🔍 Phase 2: Auditing Walkthrough[/bold cyan]")
        audit_agent = WalkthroughAuditAgent(
            output_folder=output_dir,
            library_name=library,
            library_version=version,
        )

        working_dir_obj = Path(working_dir) if working_dir else None
        result = asyncio.run(audit_agent.audit_walkthrough(
            walkthrough_path=walkthrough_file,
            working_directory=working_dir_obj
        ))

        # Display final results
        console.print("\n")
        console.print(Panel.fit(
            "[bold green]✨ Pipeline Complete![/bold green]",
            border_style="green"
        ))

        console.print(f"\n[bold]📊 Final Summary[/bold]")
        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric")
        summary_table.add_column("Value", justify="right")

        summary_table.add_row("Walkthrough Title", walkthrough_export.walkthrough.title)
        summary_table.add_row("Total Steps", str(len(walkthrough_export.steps)))
        summary_table.add_row("Completed Steps", f"{result.completed_steps}/{result.total_steps}")
        summary_table.add_row("Total Gaps Found", str(len(result.gaps)))
        summary_table.add_row("Critical Gaps", f"[red]{result.critical_gaps}[/red]")
        summary_table.add_row("Warnings", f"[yellow]{result.warning_gaps}[/yellow]")

        console.print(summary_table)
        console.print(f"\n[bold]📁 Results saved to:[/bold] [cyan]{output_dir}[/cyan]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# README.LLM COMMANDS
# ============================================================================

readme_llm_app = typer.Typer(
    name="readme-llm",
    help="Generate LLM-optimized documentation (README.LLM system)",
)
app.add_typer(readme_llm_app, name="readme-llm")


@readme_llm_app.command("generate")
def readme_llm_generate(
    docs_path: str = typer.Option(..., "--docs-path", "-d", help="Path to documentation directory"),
    library: str = typer.Option(..., "--library", "-l", help="Library name (e.g., lancedb)"),
    version: str = typer.Option(..., "--version", "-v", help="Library version (e.g., 0.25.2)"),
    languages: Optional[str] = typer.Option(
        None,
        "--languages",
        help="Comma-separated languages (e.g., python,typescript). Auto-detected if omitted.",
    ),
    output_format: str = typer.Option(
        "both",
        "--output-format",
        "-f",
        help="Output format: monolithic (README.LLM), knowledge_base (JSON), or both (default: both)",
    ),
    max_contexts: int = typer.Option(
        50,
        "--max-contexts",
        help="Maximum API contexts in README.LLM (default: 50)",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./data/<run-id>/readme_llm)",
    ),
):
    """
    Generate README.LLM from documentation (standalone mode).

    This command processes documentation to create LLM-optimized outputs:
    - README.LLM: Monolithic XML file with interleaved API + examples
    - knowledge_base/: Structured JSON for DocuMentor MCP server

    The system will:
    1. Scan documentation for code examples
    2. Auto-detect programming languages (or use --languages)
    3. Introspect the library to discover APIs
    4. Match code examples to APIs
    5. Generate README.LLM and/or knowledge base

    Example (auto-detect languages):
        stackbench readme-llm generate \\
            --docs-path docs/src \\
            --library lancedb \\
            --version 0.25.2

    Example (specify languages):
        stackbench readme-llm generate \\
            --docs-path docs/src \\
            --library lancedb \\
            --version 0.25.2 \\
            --languages python,typescript \\
            --output-format both
    """
    try:
        console.print("\n[bold cyan]📚 README.LLM Generation[/bold cyan]")
        console.print(f"Library: [yellow]{library} {version}[/yellow]")
        console.print(f"Documentation: [cyan]{docs_path}[/cyan]")

        # Parse languages
        language_list = None
        if languages:
            language_list = [lang.strip() for lang in languages.split(",")]
            console.print(f"Languages: [green]{', '.join(language_list)}[/green]")
        else:
            console.print(f"Languages: [yellow]Auto-detect[/yellow]")

        # Validate output format
        if output_format not in ("monolithic", "knowledge_base", "both"):
            console.print(f"[red]Error: Invalid output format '{output_format}'[/red]")
            console.print("Valid options: monolithic, knowledge_base, both")
            raise typer.Exit(1)

        # Import generator
        from stackbench.readme_llm import ReadMeLLMGenerator

        # Create generator
        generator = ReadMeLLMGenerator(
            docs_path=Path(docs_path),
            library_name=library,
            library_version=version,
            output_dir=Path(output) if output else None,
            languages=language_list,
            generation_mode="standalone"
        )

        console.print("\n[bold]Starting generation pipeline...[/bold]\n")

        # Run generation
        with console.status("[bold green]Processing...") as status:
            result = generator.generate(
                output_format=output_format,
                max_contexts=max_contexts
            )

        # Display results
        console.print("\n[bold green]✅ Generation Complete![/bold green]\n")

        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric")
        summary_table.add_column("Value", justify="right")

        summary_table.add_row("Library", f"{result.library_name} {result.library_version}")
        summary_table.add_row("Languages", ", ".join(result.languages))
        summary_table.add_row("Total APIs", str(result.total_apis))
        summary_table.add_row("Total Examples", str(result.total_examples))
        summary_table.add_row("Generation Mode", result.generation_mode)

        for lang, count in result.apis_by_language.items():
            summary_table.add_row(f"  {lang.capitalize()} APIs", str(count))

        console.print(summary_table)

        if result.readme_llm_path:
            console.print(f"\n📄 README.LLM: [cyan]{result.readme_llm_path}[/cyan]")

        if result.knowledge_base_path:
            console.print(f"📁 Knowledge Base: [cyan]{result.knowledge_base_path}[/cyan]")

        console.print(f"\n[dim]Run ID: {result.run_id}[/dim]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@readme_llm_app.command("mcp")
def readme_llm_mcp_serve(
    knowledge_base: str = typer.Option(
        ...,
        "--knowledge-base-path",
        "-k",
        help="Path to knowledge_base/ directory",
    ),
    search_mode: str = typer.Option(
        "hybrid",
        "--search-mode",
        "-m",
        help="Search mode: keyword (fast, exact) or hybrid (keyword + semantic)",
    ),
    vector_model: Optional[str] = typer.Option(
        None,
        "--vector-model",
        help="Sentence-transformer model (default: all-MiniLM-L6-v2)",
    ),
):
    """
    Start DocuMentor MCP server (stdio mode).

    The MCP server provides LLM-friendly tools to interact with the README.LLM
    knowledge base:

    Tools:
    - get_library_overview: Retrieve library metadata
    - find_api: Search for APIs
    - get_examples: Search for code examples
    - report_issue: Collect user feedback

    Search Modes:
    - keyword: Fast TF-IDF-based search with exact matching
    - hybrid: Combines keyword + semantic (sentence-transformers) search

    Example (hybrid mode):
        stackbench readme-llm mcp \\
            --knowledge-base-path data/run_abc123/readme_llm/knowledge_base \\
            --search-mode hybrid

    Example (keyword-only mode):
        stackbench readme-llm mcp \\
            --knowledge-base-path data/run_abc123/readme_llm/knowledge_base \\
            --search-mode keyword

    The server runs in stdio mode for MCP communication.
    """
    try:
        console.print("\n[bold cyan]🔌 Starting DocuMentor MCP Server[/bold cyan]")
        console.print(f"Knowledge Base: [cyan]{knowledge_base}[/cyan]")
        console.print(f"Search Mode: [yellow]{search_mode}[/yellow]")

        # Validate search mode
        if search_mode not in ["keyword", "hybrid"]:
            console.print(f"[red]Error: Invalid search mode '{search_mode}'[/red]")
            console.print("Valid modes: keyword, hybrid")
            raise typer.Exit(1)

        # Validate knowledge base path
        kb_path = Path(knowledge_base)
        if not kb_path.exists():
            console.print(f"[red]Error: Knowledge base not found: {kb_path}[/red]")
            raise typer.Exit(1)

        # Import server
        from stackbench.readme_llm.mcp_servers.documentor_server import DocuMentorServer
        import asyncio

        if vector_model:
            console.print(f"Vector Model: [cyan]{vector_model}[/cyan]")

        console.print("\n[dim]Server starting in stdio mode...[/dim]")
        console.print("[dim]Use Ctrl+C to stop the server[/dim]\n")

        # Create and run server
        server = DocuMentorServer(
            kb_path,
            search_mode=search_mode,
            vector_model=vector_model
        )
        asyncio.run(server.run())

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@readme_llm_app.command("analyze-feedback")
def readme_llm_analyze_feedback(
    feedback_file: str = typer.Option(
        ...,
        "--feedback-file",
        "-f",
        help="Path to feedback.jsonl file",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to save report JSON (optional)",
    ),
    show_details: bool = typer.Option(
        False,
        "--show-details",
        help="Show detailed issue list in terminal",
    ),
):
    """
    Analyze user feedback collected via DocuMentor MCP server.

    This command processes feedback issues to:
    - Identify patterns (frequently reported APIs/examples)
    - Prioritize issues by severity and frequency
    - Generate actionable recommendations
    - Export comprehensive report

    Example:
        stackbench readme-llm analyze-feedback \\
            --feedback-file data/run_abc123/readme_llm/feedback.jsonl \\
            --output feedback_report.json \\
            --show-details

    The feedback file is generated when users call the report_issue tool
    through the MCP server.
    """
    try:
        console.print("\n[bold cyan]📊 Analyzing Feedback[/bold cyan]")
        console.print(f"Feedback File: [cyan]{feedback_file}[/cyan]")

        # Validate feedback file
        fb_path = Path(feedback_file)
        if not fb_path.exists():
            console.print(f"[red]Error: Feedback file not found: {fb_path}[/red]")
            raise typer.Exit(1)

        # Import analyzer
        from stackbench.readme_llm.mcp_servers.feedback_analyzer import FeedbackAnalyzer

        console.print("\n[dim]Loading and analyzing feedback...[/dim]\n")

        # Create analyzer
        analyzer = FeedbackAnalyzer(fb_path)
        report = analyzer.generate_report()

        # Display summary
        console.print("[bold]📈 Summary[/bold]\n")

        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric")
        summary_table.add_column("Value", justify="right")

        summary = report["summary"]
        summary_table.add_row("Total Issues", str(summary["total_issues"]))

        if summary["total_issues"] > 0:
            summary_table.add_row("", "")  # Spacer

            # By severity
            for severity, count in summary["by_severity"].items():
                color = {
                    "critical": "red",
                    "high": "yellow",
                    "medium": "blue",
                    "low": "dim"
                }.get(severity, "white")
                summary_table.add_row(f"  {severity.capitalize()}", f"[{color}]{count}[/{color}]")

            summary_table.add_row("", "")  # Spacer

            # By type
            for issue_type, count in summary["by_type"].items():
                summary_table.add_row(f"  {issue_type.replace('_', ' ').title()}", str(count))

        console.print(summary_table)

        # Display recommendations
        if report["recommendations"]:
            console.print("\n[bold]💡 Recommendations[/bold]\n")
            for rec in report["recommendations"]:
                console.print(f"  {rec}")

        # Display patterns
        if report["patterns"]:
            console.print("\n[bold]🔍 Patterns Identified[/bold]\n")
            for i, pattern in enumerate(report["patterns"][:5], 1):  # Top 5
                console.print(f"  {i}. {pattern['description']} ([yellow]{pattern['count']} issues[/yellow])")

        # Display top priorities
        if report["priorities"]:
            console.print("\n[bold]⚡ Top Priority Issues[/bold]\n")

            priorities_table = Table(show_header=True, header_style="bold cyan")
            priorities_table.add_column("Issue ID", width=20)
            priorities_table.add_column("Type", width=20)
            priorities_table.add_column("Severity", width=10)
            priorities_table.add_column("Score", justify="right", width=8)
            priorities_table.add_column("Description", width=60)

            for priority in report["priorities"][:10]:  # Top 10
                issue = priority["issue"]
                score = priority["priority_score"]

                severity_color = {
                    "critical": "red",
                    "high": "yellow",
                    "medium": "blue",
                    "low": "dim"
                }.get(issue["severity"], "white")

                priorities_table.add_row(
                    issue["issue_id"],
                    issue["issue_type"].replace("_", " ").title(),
                    f"[{severity_color}]{issue['severity']}[/{severity_color}]",
                    str(score),
                    issue["description"][:60] + ("..." if len(issue["description"]) > 60 else "")
                )

            console.print(priorities_table)

        # Show detailed issues if requested
        if show_details and report["summary"]["total_issues"] > 0:
            console.print("\n[bold]📋 All Issues[/bold]\n")
            for issue in analyzer.issues[:20]:  # Limit to 20 in terminal
                console.print(f"  [{issue.severity}] {issue.issue_type}: {issue.description[:80]}")
                if issue.api_id:
                    console.print(f"    API: [cyan]{issue.api_id}[/cyan]")
                if issue.example_id:
                    console.print(f"    Example: [cyan]{issue.example_id}[/cyan]")
                console.print()

        # Export report if output specified
        if output:
            output_path = Path(output)
            analyzer.export_report(output_path)
            console.print(f"\n[bold green]✅ Report exported to:[/bold green] [cyan]{output_path}[/cyan]")
        else:
            console.print("\n[dim]Tip: Use --output to save the full report as JSON[/dim]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
