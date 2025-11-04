"""
PDF handling and annotation modules.
"""

from aems.pdf.annotator import PDFAnnotator, apply_annotations
from aems.pdf.reader import PDFReader, extract_text, extract_layout
from aems.pdf.converter import PDFConverter, convert_pdf_page, convert_pdf
from aems.pdf.layout import (
    LayoutDetector,
    LayoutBlock,
    Question,
    BlockType,
    detect_layout,
    detect_questions,
    analyze_document,
)

__all__ = [
    "PDFAnnotator",
    "apply_annotations",
    "PDFReader",
    "extract_text",
    "extract_layout",
    "PDFConverter",
    "convert_pdf_page",
    "convert_pdf",
    "LayoutDetector",
    "LayoutBlock",
    "Question",
    "BlockType",
    "detect_layout",
    "detect_questions",
    "analyze_document",
]
