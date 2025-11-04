"""
PDF to image conversion utilities.

Converts PDF pages to images for OCR processing.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile
from io import BytesIO

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from PIL import Image

logger = logging.getLogger(__name__)


class PDFConverter:
    """
    Converts PDF pages to images for OCR processing.

    Uses PyMuPDF for fast, high-quality rendering.
    """

    def __init__(self, dpi: int = 300):
        """
        Initialize PDF converter.

        Args:
            dpi: Resolution in dots per inch (default: 300)
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError(
                "PyMuPDF not installed. Install with: pip install pymupdf"
            )

        self.dpi = dpi
        self.zoom = dpi / 72  # 72 DPI is PDF default

    def pdf_page_to_image(
        self,
        pdf_path: Path,
        page_index: int,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Convert a single PDF page to an image.

        Args:
            pdf_path: Path to PDF file
            page_index: Page number (0-indexed)
            output_path: Output image path (None = create temp file)

        Returns:
            Path to the generated image
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            if page_index >= doc.page_count:
                raise IndexError(
                    f"Page {page_index} out of range (PDF has {doc.page_count} pages)"
                )

            page = doc[page_index]

            # Render page to pixmap
            mat = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=mat)

            # Determine output path
            if output_path is None:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    output_path = Path(tmp.name)

            # Save as PNG
            pix.save(str(output_path))

            doc.close()

            logger.info(
                f"Converted page {page_index} of {pdf_path.name} "
                f"to {output_path} ({pix.width}x{pix.height})"
            )

            return output_path

        except Exception as e:
            logger.error(f"Failed to convert PDF page: {e}")
            raise

    def pdf_to_images(
        self,
        pdf_path: Path,
        output_dir: Optional[Path] = None,
        page_range: Optional[Tuple[int, int]] = None,
    ) -> List[Path]:
        """
        Convert all pages of a PDF to images.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output images (None = temp directory)
            page_range: Optional (start, end) page range (inclusive)

        Returns:
            List of paths to generated images
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            # Determine page range
            if page_range:
                start, end = page_range
                start = max(0, start)
                end = min(doc.page_count - 1, end)
            else:
                start, end = 0, doc.page_count - 1

            # Determine output directory
            if output_dir is None:
                output_dir = Path(tempfile.mkdtemp(prefix="aems_pdf_"))
            else:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

            image_paths = []

            for page_num in range(start, end + 1):
                output_path = output_dir / f"{pdf_path.stem}_page_{page_num:04d}.png"
                page_path = self.pdf_page_to_image(pdf_path, page_num, output_path)
                image_paths.append(page_path)

            doc.close()

            logger.info(
                f"Converted {len(image_paths)} pages from {pdf_path.name} "
                f"to {output_dir}"
            )

            return image_paths

        except Exception as e:
            logger.error(f"Failed to convert PDF: {e}")
            raise

    def pdf_region_to_image(
        self,
        pdf_path: Path,
        page_index: int,
        bbox: Tuple[float, float, float, float],
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Convert a specific region of a PDF page to an image.

        Args:
            pdf_path: Path to PDF file
            page_index: Page number (0-indexed)
            bbox: Bounding box (x0, y0, x1, y1) in PDF coordinates
            output_path: Output image path (None = create temp file)

        Returns:
            Path to the generated image
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            if page_index >= doc.page_count:
                raise IndexError(
                    f"Page {page_index} out of range (PDF has {doc.page_count} pages)"
                )

            page = doc[page_index]

            # Create clip rectangle
            clip = fitz.Rect(bbox)

            # Render clipped region
            mat = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=mat, clip=clip)

            # Determine output path
            if output_path is None:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    output_path = Path(tmp.name)

            # Save as PNG
            pix.save(str(output_path))

            doc.close()

            logger.debug(
                f"Converted region {bbox} from page {page_index} "
                f"to {output_path} ({pix.width}x{pix.height})"
            )

            return output_path

        except Exception as e:
            logger.error(f"Failed to convert PDF region: {e}")
            raise


def pdf_page_to_pil_image(
    pdf_path: Path,
    page_index: int,
    dpi: int = 300,
) -> Image.Image:
    """
    Convert a PDF page to a PIL Image (in memory).

    Args:
        pdf_path: Path to PDF file
        page_index: Page number (0-indexed)
        dpi: Resolution in dots per inch

    Returns:
        PIL Image object
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF not installed")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)

        if page_index >= doc.page_count:
            raise IndexError(
                f"Page {page_index} out of range (PDF has {doc.page_count} pages)"
            )

        page = doc[page_index]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(BytesIO(img_data))

        doc.close()

        return img

    except Exception as e:
        logger.error(f"Failed to convert PDF page to PIL image: {e}")
        raise


# Convenience functions
def convert_pdf_page(
    pdf_path: Path,
    page_index: int,
    output_path: Optional[Path] = None,
    dpi: int = 300,
) -> Path:
    """
    Convenience function to convert a single PDF page to image.

    Args:
        pdf_path: Path to PDF file
        page_index: Page number (0-indexed)
        output_path: Output image path (None = temp file)
        dpi: Resolution in dots per inch

    Returns:
        Path to generated image
    """
    converter = PDFConverter(dpi=dpi)
    return converter.pdf_page_to_image(pdf_path, page_index, output_path)


def convert_pdf(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    dpi: int = 300,
) -> List[Path]:
    """
    Convenience function to convert all PDF pages to images.

    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory (None = temp directory)
        dpi: Resolution in dots per inch

    Returns:
        List of paths to generated images
    """
    converter = PDFConverter(dpi=dpi)
    return converter.pdf_to_images(pdf_path, output_dir)
