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
from aems.export.canvas import CanvasExporter
from aems.reviewer import ReviewerApp
from aems.memory import MemoryStore

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

    try:
        from aems.grading import parse_rubric, compile_rubric_file
        from aems.pdf import extract_text

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        console.print("\n[bold]Step 1: Parsing rubric...[/bold]")
        rubric_obj = parse_rubric(rubric)
        console.print(f"[green]✓[/green] Parsed rubric for {rubric_obj.question_id}")
        console.print(f"  Title: {rubric_obj.title}")
        console.print(f"  Total points: {rubric_obj.total_points}")
        console.print(f"  Items: {len(rubric_obj.items)}")

        console.print("\n[bold]Step 2: Extracting solution text...[/bold]")
        solution_text = extract_text(solution)
        console.print(f"[green]✓[/green] Extracted {len(solution_text)} characters from solution")

        console.print("\n[bold]Step 3: Compiling micro-checks...[/bold]")
        checks_output = output / "checks.yaml"
        micro_checks = compile_rubric_file(
            rubric,
            gold_solution_text=solution_text,
            output_path=checks_output,
            output_format="yaml"
        )
        console.print(f"[green]✓[/green] Compiled {len(micro_checks)} micro-checks")
        console.print(f"  Saved to: {checks_output}")

        # Display micro-checks summary
        console.print("\n[bold]Micro-Checks Summary:[/bold]")
        from rich.table import Table
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Points", style="green")
        table.add_column("Required", style="yellow")

        for check in micro_checks:
            table.add_row(
                check.id,
                check.desc[:60] + "..." if len(check.desc) > 60 else check.desc,
                str(check.points),
                "Yes" if not check.optional else "No"
            )

        console.print(table)

        console.print(f"\n[bold green]✓ Ingestion complete![/bold green]")
        console.print(f"\nGenerated files in {output}:")
        console.print(f"  - checks.yaml (compiled micro-checks)")
        console.print("\n[bold]Next step:[/bold]")
        console.print(f"  aems mark --gold {checks_output} --input ./submissions --output ./marked")

    except Exception as e:
        console.print(f"\n[red]Error during ingestion: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


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

    # Validate inputs
    if not gold.exists():
        console.print(f"[red]Error: Checks file not found: {gold}[/red]")
        raise typer.Exit(1)
    if not input_dir.exists():
        console.print(f"[red]Error: Input directory not found: {input_dir}[/red]")
        raise typer.Exit(1)

    try:
        from aems.grading.batch import BatchGrader

        console.print("\n[bold]Step 1: Initializing batch grader...[/bold]")
        grader = BatchGrader(
            checks_path=gold,
            provider_type=provider,
            temperature=temperature,
        )
        console.print(f"[green]✓[/green] Loaded {len(grader.micro_checks)} micro-checks")

        console.print("\n[bold]Step 2: Finding student submissions...[/bold]")
        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            console.print(f"[yellow]No PDF files found in {input_dir}[/yellow]")
            raise typer.Exit(0)

        console.print(f"[green]✓[/green] Found {len(pdf_files)} submissions")

        console.print("\n[bold]Step 3: Grading submissions...[/bold]")
        console.print("[dim](This may take a few minutes depending on number of submissions)[/dim]\n")

        grades = grader.grade_batch(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        console.print(f"\n[bold green]✓ Grading complete![/bold green]")
        console.print(f"\nProcessed: {len(grades)}/{len(pdf_files)} submissions")

        # Display summary
        console.print("\n[bold]Summary:[/bold]")
        from rich.table import Table
        table = Table()
        table.add_column("Student ID", style="cyan")
        table.add_column("Score", style="white")
        table.add_column("Percentage", style="green")
        table.add_column("Review?", style="yellow")

        for grade in grades:
            percentage = (grade.total_points / grade.total_possible * 100) if grade.total_possible > 0 else 0
            needs_review = "Yes" if grade.needs_review else "No"

            table.add_row(
                grade.student_id,
                f"{grade.total_points:.1f}/{grade.total_possible:.1f}",
                f"{percentage:.1f}%",
                needs_review,
            )

        console.print(table)

        # Show statistics
        avg_score = sum(g.total_points for g in grades) / len(grades) if grades else 0
        avg_pct = sum((g.total_points / g.total_possible * 100) for g in grades) / len(grades) if grades else 0
        needs_review_count = sum(1 for g in grades if g.needs_review)

        console.print(f"\n[bold]Statistics:[/bold]")
        console.print(f"  Average score: {avg_score:.1f} points ({avg_pct:.1f}%)")
        console.print(f"  Needs review: {needs_review_count}/{len(grades)} submissions")

        console.print(f"\n[bold]Output:[/bold]")
        console.print(f"  Annotated PDFs: {output_dir}")
        console.print(f"  Results summary: {output_dir}/results.yaml")

        console.print("\n[bold]Next steps:[/bold]")
        if needs_review_count > 0:
            console.print(f"  1. Review {needs_review_count} submissions marked with uncertainty")
        console.print(f"  2. Export grades: aems export --input {output_dir} --format canvas")

    except Exception as e:
        console.print(f"\n[red]Error during grading: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def review(
    marked_dir: Path = typer.Argument(..., help="Directory with marked PDFs"),
    memory_dir: Path = typer.Option("./memory", "--memory", "-m", help="Directory for storing memories"),
    course_id: str = typer.Option("default", "--course", "-c", help="Course identifier"),
    exam_id: str = typer.Option("default", "--exam", "-e", help="Exam identifier"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(5000, "--port", "-p", help="Port to listen on"),
) -> None:
    """
    Launch reviewer UI for human-in-the-loop feedback.

    Opens a web interface where graders can review AI markings, override decisions,
    and provide feedback to improve the system.

    The reviewer UI provides:
    - Side-by-side PDF viewing with grading results
    - Override functionality with rationale capture
    - "Improve checking" feedback submission
    - Memory layer integration for continuous improvement
    """
    console.print("[bold blue]AEMS Reviewer UI[/bold blue]")

    # Validate marked directory
    if not marked_dir.exists():
        console.print(f"[red]Error: Marked directory not found: {marked_dir}[/red]")
        raise typer.Exit(1)

    if not marked_dir.is_dir():
        console.print(f"[red]Error: Path is not a directory: {marked_dir}[/red]")
        raise typer.Exit(1)

    # Create reviewer app
    try:
        app = ReviewerApp(
            marked_dir=marked_dir,
            memory_dir=memory_dir,
            course_id=course_id,
            exam_id=exam_id,
            host=host,
            port=port,
        )

        console.print(f"[green]✓[/green] Loaded {len(app.submissions)} submissions")
        console.print(f"[green]✓[/green] Memory storage: {memory_dir}")

        # Run the server
        app.run(debug=False)

    except Exception as e:
        console.print(f"[red]Error starting reviewer: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    input_dir: Path = typer.Option(..., "--input", "-i", help="Directory with marked PDFs and results"),
    output: Path = typer.Option("grades.csv", "--output", "-o", help="Output CSV file"),
    format: str = typer.Option("canvas", "--format", "-f", help="Export format (canvas, xlsx)"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Section identifier"),
    assignment: str = typer.Option("Exam", "--assignment", "-a", help="Assignment name prefix"),
) -> None:
    """
    Export grades to Canvas-compatible CSV.

    Aggregates grading results and exports them in a format suitable for
    importing into Canvas or other Learning Management Systems.

    Reads *_results.yaml files from the input directory and generates
    a CSV file with student grades organized by question.
    """
    console.print("[bold blue]AEMS Grade Export[/bold blue]")
    console.print(f"Input dir: {input_dir}")
    console.print(f"Output: {output}")
    console.print(f"Format: {format}")

    # Validate input directory
    if not input_dir.exists():
        console.print(f"[red]Error: Input directory not found: {input_dir}[/red]")
        raise typer.Exit(1)

    if not input_dir.is_dir():
        console.print(f"[red]Error: Input path is not a directory: {input_dir}[/red]")
        raise typer.Exit(1)

    # Currently only Canvas format is supported
    if format.lower() != "canvas":
        console.print(f"[yellow]Warning: Only 'canvas' format is currently supported. Ignoring format='{format}'[/yellow]")

    console.print("\n[bold cyan]Step 1:[/bold cyan] Loading grading results...")

    # Create exporter and process
    exporter = CanvasExporter(section=section, assignment_name=assignment)
    grades = exporter.load_grades_from_yaml(input_dir)

    if not grades:
        console.print("[red]Error: No grading results found in input directory[/red]")
        console.print(f"Make sure the directory contains *_results.yaml files from the mark command")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Loaded {len(grades)} student grades")

    console.print("\n[bold cyan]Step 2:[/bold cyan] Exporting to Canvas CSV...")
    exporter.export_with_summary(grades, output)

    console.print(f"\n[bold green]✓ Export complete![/bold green]")
    console.print(f"\n[bold]Next steps:[/bold]")
    console.print(f"  1. Review the CSV file: {output}")
    console.print(f"  2. Import into Canvas: Grades → Import → Upload CSV")
    console.print(f"  3. Review any submissions marked as 'Needs Review'")


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


@demo_app.command("layout")
def demo_layout(
    pdf_file: Path = typer.Argument(..., help="PDF file to analyze"),
    page: int = typer.Option(0, "--page", "-p", help="Page number (0-indexed)"),
    show_blocks: bool = typer.Option(True, "--blocks", help="Show detected blocks"),
    show_questions: bool = typer.Option(True, "--questions", help="Show detected questions"),
) -> None:
    """
    Demonstrate layout detection on a PDF.

    This shows detected blocks, questions, and document structure.
    """
    console.print(f"[bold blue]AEMS Demo: Layout Detection (M1)[/bold blue]\n")

    if not pdf_file.exists():
        console.print(f"[red]Error: PDF not found: {pdf_file}[/red]")
        raise typer.Exit(1)

    try:
        from aems.pdf.layout import LayoutDetector, BlockType

        detector = LayoutDetector()

        # Detect blocks
        if show_blocks:
            console.print(f"[bold]Detecting blocks on page {page}...[/bold]")
            blocks = detector.detect_blocks(pdf_file, page)

            # Create summary table
            from rich.table import Table

            table = Table(title=f"Layout Blocks (Page {page})")
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Position", style="white")
            table.add_column("Text Preview", style="green")

            for block in blocks:
                text_preview = block.text[:50] + "..." if len(block.text) > 50 else block.text
                text_preview = text_preview.replace("\n", " ")

                table.add_row(
                    str(block.block_id),
                    block.block_type.value,
                    f"({block.bbox.x0:.0f}, {block.bbox.y0:.0f})",
                    text_preview,
                )

            console.print(table)
            console.print(f"\n[green]✓[/green] Found {len(blocks)} blocks")

            # Count by type
            type_counts = {}
            for block in blocks:
                type_counts[block.block_type.value] = type_counts.get(block.block_type.value, 0) + 1

            console.print("\n[bold]Block Types:[/bold]")
            for block_type, count in sorted(type_counts.items()):
                console.print(f"  {block_type}: {count}")

        # Detect questions
        if show_questions:
            console.print(f"\n[bold]Detecting questions on page {page}...[/bold]")
            questions = detector.detect_questions(pdf_file, page)

            if questions:
                console.print(f"\n[green]✓[/green] Found {len(questions)} questions\n")

                for q in questions:
                    console.print(f"[bold cyan]{q.question_id}[/bold cyan]")
                    console.print(f"  Position: ({q.bbox.x0:.0f}, {q.bbox.y0:.0f})")
                    console.print(f"  Blocks: {len(q.blocks)}")
                    text_preview = q.text[:100] + "..." if len(q.text) > 100 else q.text
                    console.print(f"  Text: {text_preview}")
                    console.print()
            else:
                console.print(f"[yellow]No questions detected on page {page}[/yellow]")

        # Show document structure summary
        console.print("\n[bold]Analyzing full document structure...[/bold]")
        structure = detector.analyze_document_structure(pdf_file)

        console.print(f"\n[bold]Document Summary:[/bold]")
        console.print(f"  Total pages: {structure['pages']}")
        console.print(f"  Total questions: {structure['total_questions']}")
        console.print(f"  Has headers: {'Yes' if structure['has_headers'] else 'No'}")
        console.print(f"  Has footers: {'Yes' if structure['has_footers'] else 'No'}")

        console.print("\n[bold]Questions per page:[/bold]")
        for page_num, count in structure['questions_by_page'].items():
            console.print(f"  Page {page_num}: {count} question(s)")

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
