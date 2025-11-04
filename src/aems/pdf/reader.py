"""
PDF reading and text extraction using PyMuPDF and pdfplumber.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from aems.models.annotations import BBox

logger = logging.getLogger(__name__)


class PDFReader:
    """
    PDF reader for text and layout extraction.

    Supports both PyMuPDF (fitz) and pdfplumber backends.
    """

    def __init__(self, pdf_path: Path | str, backend: str = "pymupdf"):
        """
        Initialize PDF reader.

        Args:
            pdf_path: Path to PDF file
            backend: Backend to use ('pymupdf' or 'pdfplumber')
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        self.backend = backend
        self.doc: Optional[fitz.Document] = None
        self.plumber_pdf: Optional[Any] = None

        self._open()

    def _open(self) -> None:
        """Open the PDF with selected backend."""
        if self.backend == "pymupdf":
            self.doc = fitz.open(self.pdf_path)
            logger.info(f"Opened PDF with PyMuPDF: {self.pdf_path} ({self.doc.page_count} pages)")
        elif self.backend == "pdfplumber":
            if pdfplumber is None:
                raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")
            self.plumber_pdf = pdfplumber.open(self.pdf_path)
            logger.info(f"Opened PDF with pdfplumber: {self.pdf_path} ({len(self.plumber_pdf.pages)} pages)")
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def close(self) -> None:
        """Close the PDF."""
        if self.doc:
            self.doc.close()
            self.doc = None
        if self.plumber_pdf:
            self.plumber_pdf.close()
            self.plumber_pdf = None

    def __enter__(self) -> "PDFReader":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @property
    def page_count(self) -> int:
        """Get number of pages in PDF."""
        if self.doc:
            return self.doc.page_count
        elif self.plumber_pdf:
            return len(self.plumber_pdf.pages)
        return 0

    def get_page_text(self, page_index: int) -> str:
        """
        Extract text from a page.

        Args:
            page_index: Page number (0-indexed)

        Returns:
            Extracted text
        """
        if self.backend == "pymupdf" and self.doc:
            if page_index >= self.doc.page_count:
                raise IndexError(f"Page {page_index} out of range")
            page = self.doc[page_index]
            return page.get_text()

        elif self.backend == "pdfplumber" and self.plumber_pdf:
            if page_index >= len(self.plumber_pdf.pages):
                raise IndexError(f"Page {page_index} out of range")
            page = self.plumber_pdf.pages[page_index]
            return page.extract_text() or ""

        return ""

    def get_text_with_bbox(self, page_index: int) -> List[Dict[str, Any]]:
        """
        Extract text with bounding boxes.

        Args:
            page_index: Page number (0-indexed)

        Returns:
            List of dicts with 'text', 'bbox', 'font', 'size'
        """
        if self.backend == "pymupdf" and self.doc:
            if page_index >= self.doc.page_count:
                raise IndexError(f"Page {page_index} out of range")

            page = self.doc[page_index]
            words = page.get_text("words")  # Returns list of (x0, y0, x1, y1, word, block, line, word_num)

            result = []
            for word in words:
                result.append({
                    "text": word[4],
                    "bbox": BBox(x0=word[0], y0=word[1], x1=word[2], y1=word[3]),
                    "block": word[5],
                    "line": word[6],
                })
            return result

        elif self.backend == "pdfplumber" and self.plumber_pdf:
            if page_index >= len(self.plumber_pdf.pages):
                raise IndexError(f"Page {page_index} out of range")

            page = self.plumber_pdf.pages[page_index]
            words = page.extract_words()

            result = []
            for word in words:
                result.append({
                    "text": word["text"],
                    "bbox": BBox(
                        x0=word["x0"],
                        y0=word["top"],
                        x1=word["x1"],
                        y1=word["bottom"],
                    ),
                    "font": word.get("fontname"),
                    "size": word.get("height"),
                })
            return result

        return []

    def get_page_image(self, page_index: int, dpi: int = 300) -> bytes:
        """
        Render a page as an image.

        Args:
            page_index: Page number (0-indexed)
            dpi: Resolution in dots per inch

        Returns:
            Image bytes (PNG format)
        """
        if self.backend != "pymupdf" or not self.doc:
            raise NotImplementedError("Page rendering only supported with PyMuPDF backend")

        if page_index >= self.doc.page_count:
            raise IndexError(f"Page {page_index} out of range")

        page = self.doc[page_index]
        zoom = dpi / 72  # 72 DPI is default
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        return pix.tobytes("png")

    def extract_images(self, page_index: int) -> List[Dict[str, Any]]:
        """
        Extract images from a page.

        Args:
            page_index: Page number (0-indexed)

        Returns:
            List of dicts with 'bbox', 'width', 'height', 'ext', 'image_data'
        """
        if self.backend != "pymupdf" or not self.doc:
            raise NotImplementedError("Image extraction only supported with PyMuPDF backend")

        if page_index >= self.doc.page_count:
            raise IndexError(f"Page {page_index} out of range")

        page = self.doc[page_index]
        images = []

        for img_index, img in enumerate(page.get_images()):
            xref = img[0]
            base_image = self.doc.extract_image(xref)

            images.append({
                "index": img_index,
                "xref": xref,
                "bbox": BBox.from_rect(page.get_image_bbox(img)),
                "width": base_image["width"],
                "height": base_image["height"],
                "ext": base_image["ext"],
                "image_data": base_image["image"],
            })

        return images

    def get_page_dimensions(self, page_index: int) -> Tuple[float, float]:
        """
        Get page dimensions (width, height).

        Args:
            page_index: Page number (0-indexed)

        Returns:
            Tuple of (width, height) in points
        """
        if self.backend == "pymupdf" and self.doc:
            if page_index >= self.doc.page_count:
                raise IndexError(f"Page {page_index} out of range")
            page = self.doc[page_index]
            rect = page.rect
            return (rect.width, rect.height)

        elif self.backend == "pdfplumber" and self.plumber_pdf:
            if page_index >= len(self.plumber_pdf.pages):
                raise IndexError(f"Page {page_index} out of range")
            page = self.plumber_pdf.pages[page_index]
            return (page.width, page.height)

        return (0, 0)


def extract_text(pdf_path: Path | str, page_index: Optional[int] = None) -> str:
    """
    Extract text from PDF (convenience function).

    Args:
        pdf_path: Path to PDF
        page_index: Specific page to extract (None = all pages)

    Returns:
        Extracted text
    """
    with PDFReader(pdf_path) as reader:
        if page_index is not None:
            return reader.get_page_text(page_index)
        else:
            # Extract all pages
            texts = []
            for i in range(reader.page_count):
                texts.append(reader.get_page_text(i))
            return "\n\n".join(texts)


def extract_layout(pdf_path: Path | str, page_index: int = 0) -> Dict[str, Any]:
    """
    Extract layout information from a page (convenience function).

    Args:
        pdf_path: Path to PDF
        page_index: Page number (0-indexed)

    Returns:
        Dictionary with 'text', 'words', 'dimensions'
    """
    with PDFReader(pdf_path) as reader:
        return {
            "text": reader.get_page_text(page_index),
            "words": reader.get_text_with_bbox(page_index),
            "dimensions": reader.get_page_dimensions(page_index),
            "images": reader.extract_images(page_index) if reader.backend == "pymupdf" else [],
        }
