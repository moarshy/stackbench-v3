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
    include_folders: Optional[str] = typer.Option(
        None,
        "--include-folders",
        "-i",
        help="Comma-separated list of folders to include (e.g., 'docs/src/python,docs/examples')",
    ),
    library: str = typer.Option(..., "--library", "-l", help="Primary library name (e.g., lancedb, fastapi)"),
    version: str = typer.Option(..., "--version", "-v", help="Library version (e.g., 0.25.2)"),
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
        help="Number of parallel workers for extraction (default: 5)",
    ),
):
    """
    Run complete documentation validation pipeline.

    This command will:
    1. Clone the repository
    2. Extract API signatures and code examples from documentation
    3. Validate API signatures against the actual library
    4. Validate code examples by executing them
    5. Validate documentation clarity and structure

    Example:
        stackbench run \\
            --repo https://github.com/lancedb/lancedb \\
            --branch main \\
            --include-folders docs/src/python \\
            --library lancedb \\
            --version 0.25.2 \\
            --output ./my-results
    """

    # Parse include_folders
    include_folders_list = None
    if include_folders:
        include_folders_list = [f.strip() for f in include_folders.split(",")]

    # Set output directory
    output_dir = Path(output) if output else Path("./data")

    # Display header
    console.print(Panel.fit(
        "[bold cyan]Stackbench Documentation Quality Validation[/bold cyan]\n\n"
        f"Repository: [yellow]{repo}[/yellow]\n"
        f"Branch: [yellow]{branch}[/yellow]\n"
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
            include_folders=include_folders_list,
            library=library,
            version=version,
            output_dir=output_dir,
            num_workers=num_workers,
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
    include_folders: Optional[List[str]],
    library: str,
    version: str,
    output_dir: Path,
    num_workers: int,
):
    """Run the validation pipeline with progress tracking."""

    # Create pipeline
    pipeline = DocumentationValidationPipeline(
        repo_url=repo,
        branch=branch,
        include_folders=include_folders,
        library_name=library,
        library_version=version,
        base_output_dir=output_dir,
        num_workers=num_workers,
    )

    # Run pipeline with progress tracking
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:

        # Track each stage
        task = progress.add_task("[cyan]Initializing pipeline...", total=5)

        # Clone repository
        progress.update(task, description="[cyan]Cloning repository...")
        await pipeline.clone_repository()
        progress.advance(task)

        # Extract documentation
        progress.update(task, description="[cyan]Extracting API signatures and code examples...")
        extraction_summary = await pipeline.run_extraction()
        progress.advance(task)

        # Validate API signatures
        progress.update(task, description="[cyan]Validating API signatures...")
        api_validation_summary = await pipeline.run_api_validation()
        progress.advance(task)

        # Validate code examples
        progress.update(task, description="[cyan]Validating code examples...")
        code_validation_summary = await pipeline.run_code_validation()
        progress.advance(task)

        # Validate clarity & structure
        progress.update(task, description="[cyan]Validating documentation clarity...")
        clarity_validation_summary = await pipeline.run_clarity_validation()
        progress.advance(task)

        # Mark pipeline as completed
        if pipeline.run_context:
            pipeline.run_context.mark_analysis_completed()

    # Display results
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✨ Pipeline Complete![/bold green]",
        border_style="green"
    ))

    # Display extraction results
    console.print("\n[bold]📊 Extraction Results[/bold]")
    extraction_table = Table(show_header=True, header_style="bold cyan")
    extraction_table.add_column("Metric")
    extraction_table.add_column("Count", justify="right")
    extraction_table.add_row("Documents Processed", str(extraction_summary.processed))
    extraction_table.add_row("API Signatures Found", str(extraction_summary.total_signatures))
    extraction_table.add_row("Code Examples Found", str(extraction_summary.total_examples))
    console.print(extraction_table)

    # Display API validation results
    console.print("\n[bold]🔍 API Signature Validation[/bold]")
    api_table = Table(show_header=True, header_style="bold cyan")
    api_table.add_column("Status")
    api_table.add_column("Count", justify="right")
    api_table.add_column("Percentage", justify="right")

    total_sigs = api_validation_summary['total_signatures']
    if total_sigs > 0:
        valid_pct = (api_validation_summary['total_valid'] / total_sigs * 100)
        invalid_pct = (api_validation_summary['total_invalid'] / total_sigs * 100)
        not_found_pct = (api_validation_summary['total_not_found'] / total_sigs * 100)

        api_table.add_row("[green]Valid", str(api_validation_summary['total_valid']), f"{valid_pct:.1f}%")
        api_table.add_row("[yellow]Invalid", str(api_validation_summary['total_invalid']), f"{invalid_pct:.1f}%")
        api_table.add_row("[red]Not Found", str(api_validation_summary['total_not_found']), f"{not_found_pct:.1f}%")
    else:
        api_table.add_row("[dim]No signatures to validate", "0", "0%")

    console.print(api_table)

    # Display code validation results
    console.print("\n[bold]📝 Code Example Validation[/bold]")
    code_table = Table(show_header=True, header_style="bold cyan")
    code_table.add_column("Status")
    code_table.add_column("Count", justify="right")
    code_table.add_column("Percentage", justify="right")

    total_examples = code_validation_summary['total_examples']
    if total_examples > 0:
        success_pct = (code_validation_summary['successful'] / total_examples * 100)
        failed_pct = (code_validation_summary['failed'] / total_examples * 100)

        code_table.add_row("[green]Successful", str(code_validation_summary['successful']), f"{success_pct:.1f}%")
        code_table.add_row("[red]Failed", str(code_validation_summary['failed']), f"{failed_pct:.1f}%")
    else:
        code_table.add_row("[dim]No examples to validate", "0", "0%")

    console.print(code_table)

    # Display clarity validation results
    console.print("\n[bold]📊 Documentation Clarity[/bold]")
    clarity_table = Table(show_header=True, header_style="bold cyan")
    clarity_table.add_column("Metric")
    clarity_table.add_column("Score/Count", justify="right")

    avg_score = clarity_validation_summary['average_clarity_score']
    score_color = "green" if avg_score >= 8 else "yellow" if avg_score >= 6 else "red"
    clarity_table.add_row("Average Clarity Score", f"[{score_color}]{avg_score:.1f}/10[/{score_color}]")
    clarity_table.add_row("Critical Issues", f"[red]{clarity_validation_summary['critical_issues']}[/red]")
    clarity_table.add_row("Warnings", f"[yellow]{clarity_validation_summary['warnings']}[/yellow]")
    clarity_table.add_row("Total Issues", str(clarity_validation_summary['total_issues_found']))

    console.print(clarity_table)

    # Display output location
    console.print(f"\n[bold]📁 Results saved to:[/bold] [cyan]{pipeline.run_context.run_dir}[/cyan]")
    console.print(f"   • Extraction: [cyan]{pipeline.run_context.results_dir / 'extraction'}[/cyan]")
    console.print(f"   • API Validation: [cyan]{pipeline.run_context.results_dir / 'api_validation'}[/cyan]")
    console.print(f"   • Code Validation: [cyan]{pipeline.run_context.results_dir / 'code_validation'}[/cyan]")
    console.print(f"   • Clarity Validation: [cyan]{pipeline.run_context.results_dir / 'clarity_validation'}[/cyan]")


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
    doc_path: str = typer.Option(..., "--doc-path", "-d", help="Path to documentation file or folder"),
    library: str = typer.Option(..., "--library", "-l", help="Primary library name"),
    version: str = typer.Option(..., "--version", "-v", help="Library version"),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./data/wt_<UUID>)",
    ),
):
    """
    Generate a walkthrough from documentation.

    This command analyzes tutorial/quickstart documentation and creates
    a structured walkthrough JSON file with step-by-step instructions.

    Example:
        stackbench walkthrough generate \\
            --doc-path docs/quickstart.md \\
            --library lancedb \\
            --version 0.25.2 \\
            --output ./data/wt_abc123
    """
    from stackbench.walkthroughs.walkthrough_generate_agent import WalkthroughGenerateAgent

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
        "[bold cyan]Walkthrough Generation[/bold cyan]\n\n"
        f"Documentation: [yellow]{doc_path}[/yellow]\n"
        f"Library: [yellow]{library}[/yellow] v[yellow]{version}[/yellow]\n"
        f"Output: [yellow]{output_dir}[/yellow]\n"
        f"Walkthrough ID: [yellow]{walkthrough_id}[/yellow]",
        border_style="cyan"
    ))

    try:
        # Create agent
        agent = WalkthroughGenerateAgent(
            output_folder=output_dir,
            library_name=library,
            library_version=version,
        )

        # Check if doc_path is file or folder
        doc_path_obj = Path(doc_path)
        if doc_path_obj.is_file():
            # Single file
            asyncio.run(agent.generate_walkthrough(doc_path_obj, walkthrough_id))
        elif doc_path_obj.is_dir():
            # Multiple files
            md_files = list(doc_path_obj.glob("**/*.md"))
            console.print(f"\n📚 Found {len(md_files)} markdown files")
            asyncio.run(agent.generate_from_multiple_docs(md_files, walkthrough_id))
        else:
            console.print(f"[red]❌ Path not found: {doc_path}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold green]✨ Generation complete![/bold green]")
        console.print(f"   Output: [cyan]{output_dir}[/cyan]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
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


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
