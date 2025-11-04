"""
Tests for PDF annotation functionality (M0).
"""

import pytest
from pathlib import Path
from aems.models.annotations import (
    AnnotationColor,
    AnnotationType,
    BBox,
    PDFAnnotation,
    AnnotationBatch,
)


def test_bbox_creation():
    """Test BBox model creation and conversions."""
    bbox = BBox(x0=10.0, y0=20.0, x1=100.0, y1=200.0)

    assert bbox.x0 == 10.0
    assert bbox.y0 == 20.0
    assert bbox.x1 == 100.0
    assert bbox.y1 == 200.0

    # Test conversions
    assert bbox.to_rect() == (10.0, 20.0, 100.0, 200.0)
    assert bbox.to_list() == [10.0, 20.0, 100.0, 200.0]


def test_bbox_from_rect():
    """Test BBox creation from rect tuple."""
    rect = (10.0, 20.0, 100.0, 200.0)
    bbox = BBox.from_rect(rect)

    assert bbox.x0 == 10.0
    assert bbox.y0 == 20.0
    assert bbox.x1 == 100.0
    assert bbox.y1 == 200.0


def test_bbox_from_list():
    """Test BBox creation from list."""
    rect = [10.0, 20.0, 100.0, 200.0]
    bbox = BBox.from_list(rect)

    assert bbox.x0 == 10.0
    assert bbox.y1 == 200.0


def test_pdf_annotation_creation():
    """Test PDFAnnotation model creation."""
    bbox = BBox(x0=50, y0=100, x1=500, y1=150)
    annotation = PDFAnnotation(
        page_index=0,
        bbox=bbox,
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
        comment="Correct work",
        check_id="Q1-01",
    )

    assert annotation.page_index == 0
    assert annotation.kind == AnnotationType.HIGHLIGHT
    assert annotation.color == AnnotationColor.GREEN
    assert annotation.comment == "Correct work"
    assert annotation.check_id == "Q1-01"


def test_annotation_rgb_colors():
    """Test RGB color conversion."""
    annotation = PDFAnnotation(
        page_index=0,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
    )

    # Green
    assert annotation.get_rgb_color() == (0.0, 1.0, 0.0)

    # Amber
    annotation.color = AnnotationColor.AMBER
    assert annotation.get_rgb_color() == (1.0, 0.65, 0.0)

    # Red
    annotation.color = AnnotationColor.RED
    assert annotation.get_rgb_color() == (1.0, 0.0, 0.0)


def test_annotation_comment_formatting():
    """Test comment formatting with check IDs."""
    # With both check_id and comment
    annotation = PDFAnnotation(
        page_index=0,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.TEXT,
        color=AnnotationColor.GREEN,
        comment="Good work",
        check_id="Q2-03",
    )
    assert annotation.format_comment() == "[Q2-03] Good work"

    # With only comment
    annotation.check_id = None
    assert annotation.format_comment() == "Good work"

    # With only check_id
    annotation.comment = None
    annotation.check_id = "Q2-03"
    assert annotation.format_comment() == "[Q2-03]"

    # With neither
    annotation.check_id = None
    assert annotation.format_comment() == ""


def test_annotation_batch():
    """Test AnnotationBatch functionality."""
    batch = AnnotationBatch(pdf_path="test.pdf")

    assert len(batch.annotations) == 0

    # Add annotations
    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
    )

    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=0, y0=100, x1=100, y1=200),
        kind=AnnotationType.SQUIGGLY,
        color=AnnotationColor.RED,
    )

    batch.add_annotation(
        page_index=1,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.TEXT,
        color=AnnotationColor.AMBER,
    )

    assert len(batch.annotations) == 3


def test_annotation_batch_filtering():
    """Test filtering annotations by color and page."""
    batch = AnnotationBatch(pdf_path="test.pdf")

    # Add various annotations
    for i, color in enumerate([
        AnnotationColor.GREEN,
        AnnotationColor.GREEN,
        AnnotationColor.RED,
        AnnotationColor.AMBER,
    ]):
        batch.add_annotation(
            page_index=i % 2,  # Pages 0 and 1
            bbox=BBox(x0=0, y0=0, x1=100, y1=100),
            kind=AnnotationType.HIGHLIGHT,
            color=color,
        )

    # Test color filtering
    green_annots = batch.get_by_color(AnnotationColor.GREEN)
    assert len(green_annots) == 2

    red_annots = batch.get_by_color(AnnotationColor.RED)
    assert len(red_annots) == 1

    amber_annots = batch.get_by_color(AnnotationColor.AMBER)
    assert len(amber_annots) == 1

    # Test page filtering
    page0_annots = batch.get_by_page(0)
    assert len(page0_annots) == 2

    page1_annots = batch.get_by_page(1)
    assert len(page1_annots) == 2


def test_annotation_batch_counting():
    """Test counting annotations by color."""
    batch = AnnotationBatch(pdf_path="test.pdf")

    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
    )

    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.HIGHLIGHT,
        color=AnnotationColor.GREEN,
    )

    batch.add_annotation(
        page_index=0,
        bbox=BBox(x0=0, y0=0, x1=100, y1=100),
        kind=AnnotationType.SQUIGGLY,
        color=AnnotationColor.RED,
    )

    counts = batch.count_by_color()

    assert counts[AnnotationColor.GREEN] == 2
    assert counts[AnnotationColor.AMBER] == 0
    assert counts[AnnotationColor.RED] == 1
