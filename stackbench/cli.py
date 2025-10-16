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


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
