#!/usr/bin/env python3
"""
Demo script for M0: PDF Annotation Proof-of-Concept

This script demonstrates the core PDF annotation capability of AEMS,
showing how to add color-coded annotations to PDFs:
- Green: Correct work
- Amber: Review needed / uncertain
- Red: Incorrect work

Usage:
    python examples/demo_m0_annotations.py <input.pdf>

Or use the CLI:
    aems demo annotate input.pdf
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aems.models.annotations import (
    PDFAnnotation,
    AnnotationBatch,
    AnnotationType,
    AnnotationColor,
    BBox,
)
from aems.pdf.annotator import PDFAnnotator, apply_annotations


def demo_basic_annotations(pdf_path: Path) -> Path:
    """
    Demonstrate basic color-coded annotations on a PDF.

    Args:
        pdf_path: Path to input PDF

    Returns:
        Path to annotated output PDF
    """
    print(f"Creating demo annotations for: {pdf_path}")

    # Open the PDF to get page dimensions
    import fitz
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")

        page = doc[0]
        width, height = page.rect.width, page.rect.height
        print(f"  Page dimensions: {width:.1f} × {height:.1f} pt")

    # Create a batch of annotations
    batch = AnnotationBatch(pdf_path=str(pdf_path))

    # Example 1: Green highlight for correct work
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=100, x1=width - 50, y1=180),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
        comment="Correct application of the fundamental theorem",
        check_id="Q1a-01",
    )

    # Example 2: Red squiggly underline for incorrect work
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=250, x1=400, y1=270),
        kind=AnnotationType.SQUIGGLY,
        color=AnnotationColor.RED,
        comment="Sign error: should be +2σ, not -2σ",
        check_id="Q1b-03",
    )

    # Example 3: Red strikeout for incorrect expression
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=300, x1=300, y1=320),
        kind=AnnotationType.STRIKEOUT,
        color=AnnotationColor.RED,
        comment="Wrong formula: use F=ma, not F=mv",
        check_id="Q2-02",
    )

    # Example 4: Amber sticky note for uncertain/review needed
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=width - 80, y0=height - 200, x1=width - 40, y1=height - 160),
        kind=AnnotationType.TEXT,
        color=AnnotationColor.AMBER,
        comment="Novel solution method - requires human review. "
                "Student used matrix approach instead of standard geometric method.",
        check_id="Q3-05",
    )

    # Example 5: Green underline for correct final answer
    if height > 500:
        batch.add_annotation(
            page_index=0,
            bbox=BBox(x0=50, y0=450, x1=250, y1=470),
            kind=AnnotationType.UNDERLINE,
            color=AnnotationColor.GREEN,
            comment="Correct final answer: σ₁ = 45.2 MPa",
            check_id="Q3-final",
        )

    # Apply annotations
    output_path = pdf_path.parent / f"{pdf_path.stem}_annotated_demo.pdf"

    with PDFAnnotator(pdf_path) as annotator:
        count = annotator.add_annotations(batch.annotations)
        annotator.save(output_path)

    print(f"\n✓ Applied {count} annotations")
    print(f"✓ Output saved to: {output_path}")

    # Print summary
    counts = batch.count_by_color()
    print(f"\nAnnotation summary:")
    print(f"  Green (correct): {counts[AnnotationColor.GREEN]}")
    print(f"  Amber (review):  {counts[AnnotationColor.AMBER]}")
    print(f"  Red (incorrect): {counts[AnnotationColor.RED]}")

    return output_path


def demo_realistic_grading_scenario(pdf_path: Path) -> Path:
    """
    Demonstrate a realistic exam grading scenario with multiple checks.

    Simulates grading a student's work on a mechanics problem with:
    - Correct free body diagram
    - Correct force equations
    - Sign error in calculation
    - Correct final numerical answer (despite intermediate error)
    """
    print(f"\nRealistic grading scenario for: {pdf_path}")

    import fitz
    with fitz.open(pdf_path) as doc:
        page = doc[0]
        width, height = page.rect.width, page.rect.height

    batch = AnnotationBatch(pdf_path=str(pdf_path))

    # Define regions for different parts of the solution
    # (In a real system, these would come from layout detection)
    regions = {
        "diagram": (100, 150),      # y-coordinates
        "equations": (200, 280),
        "calculation": (330, 410),
        "answer": (450, 490),
    }

    # Micro-check Q2a-01: Free body diagram (correct)
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=regions["diagram"][0], x1=width - 50, y1=regions["diagram"][1]),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
        comment="Correct: All forces identified and labeled. +2 pts",
        check_id="Q2a-01",
    )

    # Micro-check Q2a-02: Force equations (correct)
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=regions["equations"][0], x1=width - 50, y1=regions["equations"][1]),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
        comment="Correct: ΣFx=0 and ΣFy=0 properly applied. +3 pts",
        check_id="Q2a-02",
    )

    # Micro-check Q2a-03: Calculation (sign error - partial credit)
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=150, y0=regions["calculation"][0] + 20, x1=350, y1=regions["calculation"][0] + 40),
        kind=AnnotationType.SQUIGGLY,
        color=AnnotationColor.RED,
        comment="Sign error: tension should be positive in this convention. -1 pt",
        check_id="Q2a-03-error",
    )

    # But the rest of the calculation is fine
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=regions["calculation"][0] + 50, x1=width - 50, y1=regions["calculation"][1]),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
        comment="Algebra and substitution correct. +2 pts",
        check_id="Q2a-03-algebra",
    )

    # Micro-check Q2a-04: Final answer (correct, with units)
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=50, y0=regions["answer"][0], x1=400, y1=regions["answer"][1]),
        kind=AnnotationType.UNDERLINE,
        color=AnnotationColor.GREEN,
        comment="Correct final answer with units: T = 245 N. +2 pts",
        check_id="Q2a-04",
    )

    # Apply annotations
    output_path = pdf_path.parent / f"{pdf_path.stem}_annotated_realistic.pdf"

    with PDFAnnotator(pdf_path) as annotator:
        count = annotator.add_annotations(batch.annotations)
        annotator.save(output_path)

    print(f"✓ Applied {count} annotations")
    print(f"✓ Output saved to: {output_path}")

    # Calculate score
    total_points = 8  # 2+3+2+2 (partial credit on check 03)
    max_points = 9
    print(f"\nScore: {total_points}/{max_points} points ({total_points/max_points*100:.1f}%)")

    return output_path


def main():
    """Main entry point for demo script."""
    if len(sys.argv) < 2:
        print("Usage: python demo_m0_annotations.py <input.pdf>")
        print("\nThis demo will create two annotated versions:")
        print("  1. Basic demo with all annotation types")
        print("  2. Realistic grading scenario for a mechanics problem")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print("=" * 70)
    print("AEMS M0 Demo: PDF Annotation Proof-of-Concept")
    print("=" * 70)

    try:
        # Demo 1: Basic annotations
        print("\n--- Demo 1: Basic Annotation Types ---")
        output1 = demo_basic_annotations(pdf_path)

        # Demo 2: Realistic scenario
        print("\n--- Demo 2: Realistic Grading Scenario ---")
        output2 = demo_realistic_grading_scenario(pdf_path)

        print("\n" + "=" * 70)
        print("Demo completed successfully!")
        print("=" * 70)
        print(f"\nGenerated files:")
        print(f"  1. {output1}")
        print(f"  2. {output2}")
        print("\nOpen these PDFs to see the color-coded annotations.")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
