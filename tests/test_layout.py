"""
Tests for PDF layout detection.
"""

import pytest
from pathlib import Path
from aems.pdf.layout import (
    LayoutDetector,
    LayoutBlock,
    Question,
    BlockType,
    detect_layout,
    detect_questions,
    analyze_document,
)
from aems.models.annotations import BBox


def test_block_type_enum():
    """Test BlockType enum."""
    assert BlockType.TEXT.value == "text"
    assert BlockType.QUESTION.value == "question"
    assert BlockType.HEADER.value == "header"


def test_layout_block_creation():
    """Test LayoutBlock creation."""
    bbox = BBox(x0=10, y0=20, x1=100, y1=200)
    block = LayoutBlock(
        block_id=1,
        page_num=0,
        bbox=bbox,
        block_type=BlockType.TEXT,
        text="Hello world",
        confidence=0.95,
    )

    assert block.block_id == 1
    assert block.page_num == 0
    assert block.block_type == BlockType.TEXT
    assert block.text == "Hello world"
    assert block.confidence == 0.95


def test_layout_block_to_dict():
    """Test LayoutBlock to_dict conversion."""
    bbox = BBox(x0=10, y0=20, x1=100, y1=200)
    block = LayoutBlock(
        block_id=1,
        page_num=0,
        bbox=bbox,
        block_type=BlockType.QUESTION,
        text="Question 1",
    )

    data = block.to_dict()

    assert data["block_id"] == 1
    assert data["page_num"] == 0
    assert data["block_type"] == "question"
    assert data["text"] == "Question 1"
    assert data["bbox"] == [10, 20, 100, 200]


def test_question_creation():
    """Test Question creation."""
    bbox = BBox(x0=50, y0=100, x1=500, y1=300)
    block = LayoutBlock(
        block_id=0,
        page_num=0,
        bbox=bbox,
        block_type=BlockType.QUESTION,
        text="Question 1: Solve for x",
    )

    question = Question(
        question_id="Q1",
        page_num=0,
        bbox=bbox,
        text="Question 1: Solve for x",
        blocks=[block],
    )

    assert question.question_id == "Q1"
    assert question.page_num == 0
    assert len(question.blocks) == 1
    assert len(question.sub_questions) == 0


def test_question_to_dict():
    """Test Question to_dict conversion."""
    bbox = BBox(x0=50, y0=100, x1=500, y1=300)
    block = LayoutBlock(
        block_id=0,
        page_num=0,
        bbox=bbox,
        block_type=BlockType.QUESTION,
        text="Question 1",
    )

    question = Question(
        question_id="Q1",
        page_num=0,
        bbox=bbox,
        text="Question 1",
        blocks=[block],
    )

    data = question.to_dict()

    assert data["question_id"] == "Q1"
    assert data["page_num"] == 0
    assert len(data["blocks"]) == 1
    assert len(data["sub_questions"]) == 0


def test_layout_detector_initialization():
    """Test LayoutDetector initialization."""
    detector = LayoutDetector()
    assert detector is not None


def test_is_question_header():
    """Test question header detection."""
    detector = LayoutDetector()

    # Should detect as questions
    assert detector._is_question_header("1. What is the answer?")
    assert detector._is_question_header("Question 1")
    assert detector._is_question_header("Q1")
    assert detector._is_question_header("Q2a")
    assert detector._is_question_header("Problem 1")
    assert detector._is_question_header("1) What is it?")
    assert detector._is_question_header("(1)")
    assert detector._is_question_header("1.1")
    assert detector._is_question_header("2a)")

    # Should not detect as questions
    assert not detector._is_question_header("This is just regular text")
    assert not detector._is_question_header("The answer is 42")


def test_extract_question_id():
    """Test question ID extraction."""
    detector = LayoutDetector()

    assert detector._extract_question_id("Question 1") == "Q1"
    assert detector._extract_question_id("Question 2a") == "Q2a"
    assert detector._extract_question_id("Q1") == "Q1"
    assert detector._extract_question_id("Q3b") == "Q3b"
    assert detector._extract_question_id("Problem 5") == "Q5"
    assert detector._extract_question_id("1.") == "Q1"
    assert detector._extract_question_id("2a)") == "Q2a"
    assert detector._extract_question_id("1.1") == "Q1.1"


def test_merge_bboxes():
    """Test bounding box merging."""
    detector = LayoutDetector()

    bbox1 = BBox(x0=10, y0=20, x1=100, y1=200)
    bbox2 = BBox(x0=50, y0=150, x1=150, y1=300)

    merged = detector._merge_bboxes(bbox1, bbox2)

    assert merged.x0 == 10  # min of 10, 50
    assert merged.y0 == 20  # min of 20, 150
    assert merged.x1 == 150  # max of 100, 150
    assert merged.y1 == 300  # max of 200, 300


# Integration tests with real PDFs (skip if file doesn't exist)
@pytest.mark.parametrize("test_pdf", [
    "examples/sample_exam_submission.pdf",
    pytest.param("nonexistent.pdf", marks=pytest.mark.skip(reason="File doesn't exist")),
])
def test_detect_layout_integration(test_pdf):
    """
    Test layout detection on a real PDF (if available).
    """
    pdf_path = Path(test_pdf)
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")

    blocks = detect_layout(pdf_path, page_num=0)

    assert isinstance(blocks, list)
    assert len(blocks) > 0

    for block in blocks:
        assert isinstance(block, LayoutBlock)
        assert block.page_num == 0
        assert isinstance(block.bbox, BBox)
        assert isinstance(block.block_type, BlockType)


def test_detect_questions_integration():
    """
    Test question detection on a real PDF (if available).
    """
    pdf_path = Path("examples/sample_exam_submission.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")

    questions = detect_questions(pdf_path, page_num=0)

    assert isinstance(questions, list)
    # May or may not find questions depending on PDF content
    for question in questions:
        assert isinstance(question, Question)
        assert question.page_num == 0
        assert isinstance(question.bbox, BBox)
        assert len(question.blocks) > 0


def test_analyze_document_integration():
    """
    Test document structure analysis on a real PDF (if available).
    """
    pdf_path = Path("examples/sample_exam_submission.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")

    structure = analyze_document(pdf_path)

    assert isinstance(structure, dict)
    assert "pages" in structure
    assert "total_questions" in structure
    assert "questions_by_page" in structure
    assert structure["pages"] > 0


def test_classify_block_type():
    """Test block type classification."""
    import fitz
    detector = LayoutDetector()

    # Create a mock page rect
    page_rect = fitz.Rect(0, 0, 595, 842)  # A4 size

    # Test header detection (top 10%)
    bbox_header = BBox(x0=50, y0=30, x1=500, y1=60)
    assert detector._classify_block_type("Page Header", bbox_header, page_rect) == BlockType.HEADER

    # Test footer detection (bottom 10%)
    bbox_footer = BBox(x0=50, y0=800, x1=500, y1=830)
    assert detector._classify_block_type("Page 1 of 10", bbox_footer, page_rect) == BlockType.FOOTER

    # Test question detection
    bbox_mid = BBox(x0=50, y0=200, x1=500, y1=250)
    assert detector._classify_block_type("1. What is the answer?", bbox_mid, page_rect) == BlockType.QUESTION
    assert detector._classify_block_type("Question 2", bbox_mid, page_rect) == BlockType.QUESTION

    # Test figure detection
    assert detector._classify_block_type("Figure 1: Example", bbox_mid, page_rect) == BlockType.FIGURE
    assert detector._classify_block_type("Fig. 2: Diagram", bbox_mid, page_rect) == BlockType.FIGURE

    # Test table detection
    assert detector._classify_block_type("Table 1: Results", bbox_mid, page_rect) == BlockType.TABLE

    # Test regular text
    assert detector._classify_block_type("This is regular text content.", bbox_mid, page_rect) == BlockType.TEXT
