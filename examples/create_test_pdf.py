#!/usr/bin/env python3
"""
Create a simple test PDF for demonstrating AEMS annotations.

This script generates a sample "student submission" PDF that can be used
to test the annotation functionality.
"""

import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install with: pip install pymupdf")
    sys.exit(1)


def create_sample_exam_pdf(output_path: Path) -> None:
    """
    Create a sample exam submission PDF with typical student work.

    Args:
        output_path: Path for the output PDF
    """
    # Create a new PDF
    doc = fitz.open()

    # Add a page (A4 size: 595 x 842 points)
    page = doc.new_page(width=595, height=842)

    # Define font and sizes
    title_font = "helv"
    text_font = "helv"

    # Add header
    page.insert_text(
        (50, 50),
        "Engineering Mechanics - Exam 1",
        fontsize=16,
        fontname=title_font,
    )
    page.insert_text(
        (50, 70),
        "Student: Alex Johnson | ID: 12345",
        fontsize=10,
        fontname=text_font,
    )

    # Add a line
    page.draw_line((50, 80), (545, 80))

    # Question 1
    y = 110
    page.insert_text((50, y), "Question 1: Free Body Diagram (5 points)", fontsize=12)
    y += 25
    page.insert_text(
        (50, y),
        "Draw the free body diagram for a block on an inclined plane.",
        fontsize=10,
    )
    y += 30

    # Simulate student's work area 1
    rect1 = fitz.Rect(50, y, 545, y + 80)
    page.draw_rect(rect1, color=(0.9, 0.9, 0.9), fill=(0.95, 0.95, 0.95))
    page.insert_text((60, y + 20), "[Student's free body diagram would be here]", fontsize=9)
    page.insert_text((60, y + 40), "Forces: N (normal), W (weight), f (friction)", fontsize=9)

    # Question 2
    y += 110
    page.insert_text((50, y), "Question 2: Force Equations (8 points)", fontsize=12)
    y += 25
    page.insert_text(
        (50, y),
        "Write the equilibrium equations for the system.",
        fontsize=10,
    )
    y += 30

    # Simulate student's equations
    rect2 = fitz.Rect(50, y, 545, y + 100)
    page.draw_rect(rect2, color=(0.9, 0.9, 0.9), fill=(0.95, 0.95, 0.95))

    eq_y = y + 20
    page.insert_text((60, eq_y), "ΣFx = 0:  W sin(θ) - f = 0", fontsize=10)
    eq_y += 20
    page.insert_text((60, eq_y), "ΣFy = 0:  N - W cos(θ) = 0", fontsize=10)
    eq_y += 20
    page.insert_text((60, eq_y), "f = μN", fontsize=10)

    # Question 3
    y += 130
    page.insert_text((50, y), "Question 3: Numerical Solution (7 points)", fontsize=12)
    y += 25
    page.insert_text(
        (50, y),
        "Given W=500N, θ=30°, μ=0.3, find the friction force f.",
        fontsize=10,
    )
    y += 30

    # Simulate student's calculation
    rect3 = fitz.Rect(50, y, 545, y + 140)
    page.draw_rect(rect3, color=(0.9, 0.9, 0.9), fill=(0.95, 0.95, 0.95))

    calc_y = y + 20
    page.insert_text((60, calc_y), "N = W cos(30°) = 500 × 0.866 = 433 N", fontsize=10)
    calc_y += 20
    page.insert_text((60, calc_y), "f = μN = 0.3 × 433 = 129.9 N", fontsize=10)
    calc_y += 20
    # Add an intentional error for demo
    page.insert_text((60, calc_y), "Wait, let me recalculate:", fontsize=9, color=(0.5, 0.5, 0.5))
    calc_y += 20
    page.insert_text((60, calc_y), "f = 0.3 × (-433) = -129.9 N  ← sign convention", fontsize=10)
    calc_y += 25
    page.insert_text((60, calc_y), "Final answer: f = 130 N", fontsize=11)

    # Add footer
    page.insert_text(
        (50, 820),
        "End of submission",
        fontsize=9,
        color=(0.5, 0.5, 0.5),
    )

    # Save the PDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    doc.close()

    print(f"Created test PDF: {output_path}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
    else:
        output_path = Path("examples") / "sample_exam_submission.pdf"

    print("Creating sample exam submission PDF...")
    create_sample_exam_pdf(output_path)
    print(f"\nTest PDF created successfully!")
    print(f"You can now use this with the demo:")
    print(f"  python examples/demo_m0_annotations.py {output_path}")
    print(f"Or:")
    print(f"  aems demo annotate {output_path}")


if __name__ == "__main__":
    main()
