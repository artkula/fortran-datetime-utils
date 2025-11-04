"""
PDF annotation module using PyMuPDF for color-coded marking.

Supports green (correct), amber (review), and red (incorrect) annotations
with highlights, squiggly underlines, strikeouts, and text notes.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError(
        "PyMuPDF is required for PDF annotation. "
        "Install with: pip install pymupdf"
    )

from aems.models.annotations import (
    PDFAnnotation,
    AnnotationBatch,
    AnnotationType,
    AnnotationColor,
    BBox,
)

logger = logging.getLogger(__name__)


class PDFAnnotator:
    """
    PDF annotator using PyMuPDF to add color-coded annotations.

    This class handles opening PDFs, adding various types of annotations
    (highlights, squiggly underlines, strikeouts, text notes), and saving
    the annotated PDFs.
    """

    def __init__(self, pdf_path: Path | str):
        """
        Initialize the annotator with a PDF file.

        Args:
            pdf_path: Path to the PDF file to annotate
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        self.doc: Optional[fitz.Document] = None
        self._open()

    def _open(self) -> None:
        """Open the PDF document."""
        try:
            self.doc = fitz.open(self.pdf_path)
            logger.info(f"Opened PDF: {self.pdf_path} ({self.doc.page_count} pages)")
        except Exception as e:
            logger.error(f"Failed to open PDF {self.pdf_path}: {e}")
            raise

    def close(self) -> None:
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __enter__(self) -> "PDFAnnotator":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def add_annotation(self, annotation: PDFAnnotation) -> bool:
        """
        Add a single annotation to the PDF.

        Args:
            annotation: PDFAnnotation object with all details

        Returns:
            True if annotation was added successfully, False otherwise
        """
        if not self.doc:
            logger.error("PDF document not opened")
            return False

        if annotation.page_index >= self.doc.page_count:
            logger.error(
                f"Page {annotation.page_index} out of range "
                f"(PDF has {self.doc.page_count} pages)"
            )
            return False

        try:
            page = self.doc[annotation.page_index]
            rect = fitz.Rect(annotation.bbox.to_rect())
            rgb = annotation.get_rgb_color()

            # Add annotation based on type
            if annotation.kind == AnnotationType.HIGHLIGHT:
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=rgb)

            elif annotation.kind == AnnotationType.SQUIGGLY:
                annot = page.add_squiggly_annot(rect)
                annot.set_colors(stroke=rgb)

            elif annotation.kind == AnnotationType.STRIKEOUT:
                annot = page.add_strikeout_annot(rect)
                annot.set_colors(stroke=rgb)

            elif annotation.kind == AnnotationType.UNDERLINE:
                annot = page.add_underline_annot(rect)
                annot.set_colors(stroke=rgb)

            elif annotation.kind == AnnotationType.TEXT:
                # Text annotation (sticky note)
                annot = page.add_text_annot(
                    rect.top_left,  # Position of note icon
                    annotation.format_comment(),
                )
                annot.set_colors(stroke=rgb)

            else:
                logger.error(f"Unknown annotation type: {annotation.kind}")
                return False

            # Add comment to all annotation types (except text which has it built-in)
            if annotation.kind != AnnotationType.TEXT:
                formatted_comment = annotation.format_comment()
                if formatted_comment:
                    annot.set_info(content=formatted_comment)

            # Update annotation appearance
            annot.update()

            logger.debug(
                f"Added {annotation.kind.value} annotation "
                f"(color={annotation.color.value}) on page {annotation.page_index}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add annotation: {e}")
            return False

    def add_annotations(self, annotations: List[PDFAnnotation]) -> int:
        """
        Add multiple annotations to the PDF.

        Args:
            annotations: List of PDFAnnotation objects

        Returns:
            Number of annotations successfully added
        """
        count = 0
        for annot in annotations:
            if self.add_annotation(annot):
                count += 1
        return count

    def save(self, output_path: Optional[Path | str] = None) -> Path:
        """
        Save the annotated PDF.

        Args:
            output_path: Path to save the annotated PDF. If None, overwrites original.

        Returns:
            Path to the saved PDF
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened")

        if output_path is None:
            output_path = self.pdf_path
        else:
            output_path = Path(output_path)

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.doc.save(
                output_path,
                garbage=4,  # Aggressive garbage collection
                deflate=True,  # Compress
                clean=True,  # Clean up
            )
            logger.info(f"Saved annotated PDF: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save PDF to {output_path}: {e}")
            raise

    def get_annotations_on_page(self, page_index: int) -> List[dict]:
        """
        Get existing annotations on a page.

        Args:
            page_index: Page number (0-indexed)

        Returns:
            List of annotation dictionaries with type, rect, color, content
        """
        if not self.doc or page_index >= self.doc.page_count:
            return []

        page = self.doc[page_index]
        annotations = []

        for annot in page.annots():
            annotations.append({
                "type": annot.type[1],  # Annotation type name
                "rect": tuple(annot.rect),
                "color": annot.colors,
                "content": annot.info.get("content", ""),
            })

        return annotations


def apply_annotations(
    pdf_path: Path | str,
    annotations: List[PDFAnnotation],
    output_path: Optional[Path | str] = None,
) -> Tuple[Path, int]:
    """
    Apply annotations to a PDF file (convenience function).

    Args:
        pdf_path: Path to the input PDF
        annotations: List of annotations to apply
        output_path: Path for output (if None, creates *_annotated.pdf)

    Returns:
        Tuple of (output_path, number_of_annotations_added)
    """
    pdf_path = Path(pdf_path)

    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}_annotated.pdf"

    with PDFAnnotator(pdf_path) as annotator:
        count = annotator.add_annotations(annotations)
        saved_path = annotator.save(output_path)

    return saved_path, count


def apply_annotation_batch(batch: AnnotationBatch) -> Tuple[Path, int]:
    """
    Apply an AnnotationBatch to a PDF.

    Args:
        batch: AnnotationBatch with pdf_path and annotations

    Returns:
        Tuple of (output_path, number_of_annotations_added)
    """
    pdf_path = Path(batch.pdf_path)
    output_path = pdf_path.parent / f"{pdf_path.stem}_annotated.pdf"

    return apply_annotations(pdf_path, batch.annotations, output_path)


def create_demo_annotations(pdf_path: Path | str, output_path: Optional[Path | str] = None) -> Path:
    """
    Create a demo PDF with sample annotations (for testing M0).

    Args:
        pdf_path: Path to input PDF
        output_path: Path for output (optional)

    Returns:
        Path to annotated PDF
    """
    logger.info("Creating demo annotations...")

    # Open PDF to get page dimensions
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")

        page = doc[0]
        width, height = page.rect.width, page.rect.height

    # Create sample annotations on first page
    annotations = [
        # Green highlight for "correct" area (top third)
        PDFAnnotation(
            page_index=0,
            bbox=BBox(x0=50, y0=50, x1=width - 50, y1=150),
            kind=AnnotationType.HIGHLIGHT,
            color=AnnotationColor.GREEN,
            comment="Correct derivation of initial equation",
            check_id="Q1a-01",
        ),
        # Red squiggly for "incorrect" area (middle third)
        PDFAnnotation(
            page_index=0,
            bbox=BBox(x0=50, y0=height / 2 - 50, x1=width - 50, y1=height / 2),
            kind=AnnotationType.SQUIGGLY,
            color=AnnotationColor.RED,
            comment="Sign error: should be +σ not -σ",
            check_id="Q1b-03",
        ),
        # Amber text note for "review needed"
        PDFAnnotation(
            page_index=0,
            bbox=BBox(x0=width - 100, y0=height - 150, x1=width - 50, y1=height - 100),
            kind=AnnotationType.TEXT,
            color=AnnotationColor.AMBER,
            comment="Uncertain: Novel solution method requires human review",
            check_id="Q2-05",
        ),
    ]

    return apply_annotations(pdf_path, annotations, output_path)[0]
