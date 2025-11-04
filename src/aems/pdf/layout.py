"""
PDF Layout Detection and Document Structure Analysis.

Detects and analyzes the structure of PDF documents:
- Text blocks and regions
- Headers and titles
- Question numbers and sections
- Figures and tables
- Answer regions
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from aems.models.annotations import BBox

logger = logging.getLogger(__name__)


class BlockType(str, Enum):
    """Types of content blocks in a PDF."""
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    HEADER = "header"
    QUESTION = "question"
    ANSWER = "answer"
    FIGURE = "figure"
    FOOTER = "footer"


@dataclass
class LayoutBlock:
    """
    A single block/region in a PDF layout.

    Represents a coherent unit of content (text paragraph, image, question, etc.)
    """
    block_id: int
    page_num: int
    bbox: BBox
    block_type: BlockType
    text: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "block_id": self.block_id,
            "page_num": self.page_num,
            "bbox": self.bbox.to_list(),
            "block_type": self.block_type.value,
            "text": self.text,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Question:
    """
    A detected question in an exam/document.

    Contains the question text, number, and associated answer regions.
    """
    question_id: str  # e.g., "Q1", "Q2a", "Q3.1"
    page_num: int
    bbox: BBox
    text: str
    blocks: List[LayoutBlock]
    sub_questions: List["Question"] = None

    def __post_init__(self):
        if self.sub_questions is None:
            self.sub_questions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question_id": self.question_id,
            "page_num": self.page_num,
            "bbox": self.bbox.to_list(),
            "text": self.text,
            "blocks": [b.to_dict() for b in self.blocks],
            "sub_questions": [sq.to_dict() for sq in self.sub_questions],
        }


class LayoutDetector:
    """
    Detects layout and structure in PDF documents.

    Uses PyMuPDF's built-in text analysis with optional enhancement
    from LayoutParser or Marker in the future.
    """

    def __init__(self):
        """Initialize layout detector."""
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF required. Install with: pip install pymupdf")

    def detect_blocks(self, pdf_path: Path, page_num: int = 0) -> List[LayoutBlock]:
        """
        Detect all blocks/regions on a PDF page.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            List of LayoutBlock objects
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            if page_num >= doc.page_count:
                raise IndexError(f"Page {page_num} out of range")

            page = doc[page_num]
            blocks = []

            # Get text blocks from PyMuPDF
            text_blocks = page.get_text("dict")["blocks"]

            for idx, block in enumerate(text_blocks):
                block_type = BlockType.TEXT if block["type"] == 0 else BlockType.IMAGE

                bbox = BBox(
                    x0=block["bbox"][0],
                    y0=block["bbox"][1],
                    x1=block["bbox"][2],
                    y1=block["bbox"][3],
                )

                # Extract text from text blocks
                text = ""
                if block_type == BlockType.TEXT:
                    text_parts = []
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text_parts.append(span["text"])
                    text = " ".join(text_parts)

                # Classify block type more precisely
                classified_type = self._classify_block_type(text, bbox, page.rect)

                layout_block = LayoutBlock(
                    block_id=idx,
                    page_num=page_num,
                    bbox=bbox,
                    block_type=classified_type,
                    text=text,
                    metadata={"raw_block": block},
                )

                blocks.append(layout_block)

            doc.close()

            logger.info(f"Detected {len(blocks)} blocks on page {page_num}")
            return blocks

        except Exception as e:
            logger.error(f"Layout detection failed: {e}")
            raise

    def _classify_block_type(
        self,
        text: str,
        bbox: BBox,
        page_rect: fitz.Rect
    ) -> BlockType:
        """
        Classify a text block into a more specific type.

        Args:
            text: Block text content
            bbox: Block bounding box
            page_rect: Full page rectangle

        Returns:
            BlockType classification
        """
        if not text.strip():
            return BlockType.TEXT

        # Check if it's in header region (top 10% of page)
        if bbox.y0 < page_rect.height * 0.1:
            return BlockType.HEADER

        # Check if it's in footer region (bottom 10% of page)
        if bbox.y1 > page_rect.height * 0.9:
            return BlockType.FOOTER

        # Check if it looks like a question
        if self._is_question_header(text):
            return BlockType.QUESTION

        # Check if it looks like a figure caption
        if re.match(r"^(Figure|Fig\.?|Diagram)\s+\d+", text, re.IGNORECASE):
            return BlockType.FIGURE

        # Check if it looks like a table caption
        if re.match(r"^Table\s+\d+", text, re.IGNORECASE):
            return BlockType.TABLE

        return BlockType.TEXT

    def _is_question_header(self, text: str) -> bool:
        """
        Check if text looks like a question header.

        Examples: "1.", "Question 2", "Q3a", "3.1", "Problem 4"

        Args:
            text: Text to check

        Returns:
            True if it looks like a question header
        """
        text = text.strip()

        # Common question patterns
        patterns = [
            r"^\d+\.\s*",  # "1. " or "2. "
            r"^Question\s+\d+",  # "Question 1"
            r"^Q\d+[a-z]?",  # "Q1" or "Q2a"
            r"^Problem\s+\d+",  # "Problem 1"
            r"^\d+\)\s*",  # "1) " or "2) "
            r"^\(\d+\)",  # "(1)" or "(2)"
            r"^\d+\.\d+",  # "1.1" or "2.3"
            r"^\d+[a-z]\)",  # "1a)" or "2b)"
        ]

        for pattern in patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def detect_questions(
        self,
        pdf_path: Path,
        page_num: int = 0
    ) -> List[Question]:
        """
        Detect questions on a PDF page.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            List of Question objects
        """
        blocks = self.detect_blocks(pdf_path, page_num)

        questions = []
        current_question = None
        current_blocks = []

        for block in blocks:
            if block.block_type == BlockType.QUESTION:
                # Save previous question if exists
                if current_question is not None:
                    questions.append(current_question)

                # Start new question
                question_id = self._extract_question_id(block.text)
                current_question = Question(
                    question_id=question_id,
                    page_num=page_num,
                    bbox=block.bbox,
                    text=block.text,
                    blocks=[block],
                )
                current_blocks = [block]

            elif current_question is not None:
                # Add block to current question
                current_blocks.append(block)
                current_question.blocks = current_blocks

                # Expand question bbox to include this block
                current_question.bbox = self._merge_bboxes(
                    current_question.bbox,
                    block.bbox
                )

        # Add last question
        if current_question is not None:
            questions.append(current_question)

        logger.info(f"Detected {len(questions)} questions on page {page_num}")
        return questions

    def _extract_question_id(self, text: str) -> str:
        """
        Extract question ID from header text.

        Args:
            text: Question header text

        Returns:
            Question ID string (e.g., "Q1", "Q2a")
        """
        text = text.strip()

        # Try various patterns
        patterns = [
            (r"Question\s+(\d+[a-z]?)", "Q"),  # "Question 1" -> "Q1"
            (r"Q(\d+[a-z]?)", "Q"),  # "Q1" -> "Q1"
            (r"Problem\s+(\d+[a-z]?)", "Q"),  # "Problem 1" -> "Q1"
            (r"^(\d+[a-z]?)[\.\)]", "Q"),  # "1." or "1a)" -> "Q1" or "Q1a"
            (r"^(\d+\.\d+)", "Q"),  # "1.1" -> "Q1.1"
        ]

        for pattern, prefix in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return f"{prefix}{match.group(1)}"

        # Fallback: use first word/number
        first_token = text.split()[0] if text.split() else "Unknown"
        return f"Q{first_token}"

    def _merge_bboxes(self, bbox1: BBox, bbox2: BBox) -> BBox:
        """
        Merge two bounding boxes into one that contains both.

        Args:
            bbox1: First bounding box
            bbox2: Second bounding box

        Returns:
            Merged bounding box
        """
        return BBox(
            x0=min(bbox1.x0, bbox2.x0),
            y0=min(bbox1.y0, bbox2.y0),
            x1=max(bbox1.x1, bbox2.x1),
            y1=max(bbox1.y1, bbox2.y1),
        )

    def analyze_document_structure(
        self,
        pdf_path: Path
    ) -> Dict[str, Any]:
        """
        Analyze the complete structure of a PDF document.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with document structure information
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            structure = {
                "pages": doc.page_count,
                "questions_by_page": {},
                "total_questions": 0,
                "has_headers": False,
                "has_footers": False,
            }

            all_questions = []

            for page_num in range(doc.page_count):
                questions = self.detect_questions(pdf_path, page_num)
                structure["questions_by_page"][page_num] = len(questions)
                all_questions.extend(questions)

                # Check for headers/footers
                blocks = self.detect_blocks(pdf_path, page_num)
                if any(b.block_type == BlockType.HEADER for b in blocks):
                    structure["has_headers"] = True
                if any(b.block_type == BlockType.FOOTER for b in blocks):
                    structure["has_footers"] = True

            structure["total_questions"] = len(all_questions)
            structure["questions"] = [q.to_dict() for q in all_questions]

            doc.close()

            logger.info(
                f"Document structure: {structure['pages']} pages, "
                f"{structure['total_questions']} questions"
            )

            return structure

        except Exception as e:
            logger.error(f"Document structure analysis failed: {e}")
            raise


# Convenience functions
def detect_layout(pdf_path: Path, page_num: int = 0) -> List[LayoutBlock]:
    """
    Convenience function to detect layout blocks.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)

    Returns:
        List of LayoutBlock objects
    """
    detector = LayoutDetector()
    return detector.detect_blocks(pdf_path, page_num)


def detect_questions(pdf_path: Path, page_num: int = 0) -> List[Question]:
    """
    Convenience function to detect questions.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)

    Returns:
        List of Question objects
    """
    detector = LayoutDetector()
    return detector.detect_questions(pdf_path, page_num)


def analyze_document(pdf_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze document structure.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with structure information
    """
    detector = LayoutDetector()
    return detector.analyze_document_structure(pdf_path)
