"""
AEMS Command Line Interface.

Provides commands for:
- ingest: Process gold materials (exam + solution + rubric)
- mark: Batch mark student submissions
- review: Launch reviewer UI
- export: Export grades to Canvas CSV
- demo: Run demo/test commands
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from aems.pdf.annotator import create_demo_annotations
from aems.pdf.reader import PDFReader

# Initialize Typer app and Rich console
app = typer.Typer(
    name="aems",
    help="Automated Exam Marking System - AI-powered exam grading with color-coded PDF annotations",
    add_completion=False,
)
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.callback()
def main_callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """AEMS - Automated Exam Marking System"""
    setup_logging(verbose)


@app.command()
def ingest(
    exam: Path = typer.Option(..., "--exam", "-e", help="Path to exam PDF"),
    solution: Path = typer.Option(..., "--solution", "-s", help="Path to solution PDF"),
    rubric: Path = typer.Option(..., "--rubric", "-r", help="Path to rubric (JSON/YAML)"),
    output: Path = typer.Option("./gold", "--output", "-o", help="Output directory for processed gold materials"),
    hints: Optional[Path] = typer.Option(None, "--hints", help="Optional hints markdown file"),
) -> None:
    """
    Ingest gold materials (exam statement + solution + rubric).

    This command processes the instructor's reference materials and generates
    a stepwise marking plan with micro-checks.
    """
    console.print("[bold blue]AEMS Ingestion[/bold blue]")
    console.print(f"Exam: {exam}")
    console.print(f"Solution: {solution}")
    console.print(f"Rubric: {rubric}")
    console.print(f"Output: {output}")

    # Validate inputs
    if not exam.exists():
        console.print(f"[red]Error: Exam PDF not found: {exam}[/red]")
        raise typer.Exit(1)
    if not solution.exists():
        console.print(f"[red]Error: Solution PDF not found: {solution}[/red]")
        raise typer.Exit(1)
    if not rubric.exists():
        console.print(f"[red]Error: Rubric not found: {rubric}[/red]")
        raise typer.Exit(1)

    # TODO: Implement full ingestion pipeline (M1)
    console.print("\n[yellow]Note: Full ingestion pipeline not yet implemented (M1 milestone)[/yellow]")
    console.print("This will be implemented in the next phase.")


@app.command()
def mark(
    gold: Path = typer.Option(..., "--gold", "-g", help="Path to gold checks.yaml"),
    input_dir: Path = typer.Option(..., "--input", "-i", help="Directory with student PDFs"),
    output_dir: Path = typer.Option("./marked", "--output", "-o", help="Output directory for marked PDFs"),
    provider: str = typer.Option("claude", "--provider", "-p", help="LLM provider (claude, openai, gemini, local)"),
    temperature: float = typer.Option(0.2, "--temperature", "-t", help="Sampling temperature"),
) -> None:
    """
    Batch mark student submissions.

    Processes all PDF submissions in the input directory, grades them against
    the compiled rubric, and produces annotated PDFs with color-coded feedback.
    """
    console.print("[bold blue]AEMS Batch Marking[/bold blue]")
    console.print(f"Gold checks: {gold}")
    console.print(f"Input dir: {input_dir}")
    console.print(f"Output dir: {output_dir}")
    console.print(f"Provider: {provider} (temperature={temperature})")

    # TODO: Implement batch marking (M2/M3)
    console.print("\n[yellow]Note: Batch marking not yet implemented (M2/M3 milestones)[/yellow]")
    console.print("This will be implemented in the next phase.")


@app.command()
def review(
    marked_dir: Path = typer.Argument(..., help="Directory with marked PDFs"),
) -> None:
    """
    Launch reviewer UI for human-in-the-loop feedback.

    Opens a web interface where graders can review AI markings, override decisions,
    and provide feedback to improve the system.
    """
    console.print("[bold blue]AEMS Reviewer UI[/bold blue]")
    console.print(f"Marked dir: {marked_dir}")

    # TODO: Implement reviewer UI (M4)
    console.print("\n[yellow]Note: Reviewer UI not yet implemented (M4 milestone)[/yellow]")
    console.print("This will be implemented in the next phase.")


@app.command()
def export(
    input_dir: Path = typer.Option(..., "--input", "-i", help="Directory with marked PDFs"),
    output: Path = typer.Option("grades.csv", "--output", "-o", help="Output CSV file"),
    format: str = typer.Option("canvas", "--format", "-f", help="Export format (canvas, xlsx)"),
) -> None:
    """
    Export grades to Canvas-compatible CSV.

    Aggregates grading results and exports them in a format suitable for
    importing into Canvas or other Learning Management Systems.
    """
    console.print("[bold blue]AEMS Grade Export[/bold blue]")
    console.print(f"Input dir: {input_dir}")
    console.print(f"Output: {output}")
    console.print(f"Format: {format}")

    # TODO: Implement export (M3)
    console.print("\n[yellow]Note: Export functionality not yet implemented (M3 milestone)[/yellow]")
    console.print("This will be implemented in the next phase.")


# Demo commands
demo_app = typer.Typer(help="Demo and testing commands")
app.add_typer(demo_app, name="demo")


@demo_app.command("annotate")
def demo_annotate(
    input_pdf: Path = typer.Argument(..., help="Input PDF file"),
    output_pdf: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PDF file"),
) -> None:
    """
    Create a demo PDF with color-coded annotations (M0 proof-of-concept).

    This demonstrates the core PDF annotation capability with green (correct),
    amber (review), and red (incorrect) annotations.
    """
    console.print("[bold blue]AEMS Demo: PDF Annotation (M0)[/bold blue]")

    if not input_pdf.exists():
        console.print(f"[red]Error: PDF not found: {input_pdf}[/red]")
        raise typer.Exit(1)

    try:
        output_path = create_demo_annotations(input_pdf, output_pdf)
        console.print(f"\n[green]✓[/green] Created annotated PDF: {output_path}")
        console.print("\nDemo annotations added:")
        console.print("  [green]●[/green] Green highlight - Correct work")
        console.print("  [red]●[/red] Red squiggly - Incorrect work")
        console.print("  [yellow]●[/yellow] Amber text note - Review needed")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@demo_app.command("read")
def demo_read(
    pdf: Path = typer.Argument(..., help="PDF file to read"),
    page: int = typer.Option(0, "--page", "-p", help="Page number (0-indexed)"),
) -> None:
    """
    Read and display PDF metadata and text content.
    """
    console.print(f"[bold blue]Reading PDF: {pdf}[/bold blue]\n")

    if not pdf.exists():
        console.print(f"[red]Error: PDF not found: {pdf}[/red]")
        raise typer.Exit(1)

    try:
        with PDFReader(pdf) as reader:
            # Display metadata
            table = Table(title="PDF Metadata")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("File", str(pdf))
            table.add_row("Pages", str(reader.page_count))

            dims = reader.get_page_dimensions(page)
            table.add_row("Page dimensions", f"{dims[0]:.1f} × {dims[1]:.1f} pt")

            console.print(table)

            # Display text from requested page
            console.print(f"\n[bold]Page {page} text:[/bold]")
            text = reader.get_page_text(page)
            console.print(text[:500] + ("..." if len(text) > 500 else ""))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@demo_app.command("ocr")
def demo_ocr(
    input_file: Path = typer.Argument(..., help="PDF or image file to OCR"),
    page: int = typer.Option(0, "--page", "-p", help="Page number for PDF (0-indexed)"),
    language: str = typer.Option("eng", "--lang", "-l", help="Language code (e.g., eng, swe, eng+swe)"),
) -> None:
    """
    Demonstrate OCR functionality on a PDF or image.

    This tests the OCR engine and shows extracted text with confidence scores.
    """
    console.print(f"[bold blue]AEMS Demo: OCR (M1)[/bold blue]\n")

    if not input_file.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(1)

    try:
        from aems.ocr import check_tesseract_installation, get_ocr_router
        from aems.pdf.converter import convert_pdf_page

        # Check Tesseract installation
        tesseract_info = check_tesseract_installation()
        if not tesseract_info["installed"]:
            console.print("[red]Error: Tesseract not installed[/red]")
            console.print("\nPlease install Tesseract OCR:")
            console.print("  Ubuntu/Debian: sudo apt-get install tesseract-ocr")
            console.print("  MacOS: brew install tesseract")
            console.print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            raise typer.Exit(1)

        console.print(f"[green]✓[/green] Tesseract version: {tesseract_info['version']}")
        console.print(f"[green]✓[/green] Available languages: {len(tesseract_info['languages'])}")

        # Convert PDF to image if needed
        if input_file.suffix.lower() == ".pdf":
            console.print(f"\nConverting PDF page {page} to image...")
            image_path = convert_pdf_page(input_file, page)
            console.print(f"[green]✓[/green] Image created: {image_path}")
        else:
            image_path = input_file

        # Perform OCR
        console.print(f"\nPerforming OCR with language: {language}")
        router = get_ocr_router()
        result = router.ocr_image(image_path, language=language)

        # Display results
        console.print("\n" + "=" * 70)
        console.print("[bold]OCR Results:[/bold]")
        console.print("=" * 70)
        console.print(f"Engine: {result.engine.value}")
        console.print(f"Confidence: {result.confidence:.2%}")
        console.print(f"Text length: {len(result.text)} characters")
        console.print(f"Language: {result.language}")
        console.print("\n[bold]Extracted Text:[/bold]")
        console.print("-" * 70)
        console.print(result.text[:1000] + ("..." if len(result.text) > 1000 else ""))
        console.print("-" * 70)

        # Clean up temp image if created
        if input_file.suffix.lower() == ".pdf" and image_path != input_file:
            image_path.unlink(missing_ok=True)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show AEMS version information."""
    from aems import __version__, __author__

    console.print(f"[bold]AEMS[/bold] version {__version__}")
    console.print(f"By: {__author__}")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
