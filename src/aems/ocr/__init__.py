"""
OCR (Optical Character Recognition) modules.

Supports multiple engines:
- Tesseract: Printed text (100+ languages)
- docTR/TrOCR: Handwriting (future)
- pix2tex: Mathematical expressions (future)
"""

from aems.ocr.router import (
    OCRRouter,
    OCRResult,
    OCREngine,
    ContentType,
    get_ocr_router,
    ocr_image,
)
from aems.ocr.tesseract_engine import TesseractEngine, check_tesseract_installation

__all__ = [
    "OCRRouter",
    "OCRResult",
    "OCREngine",
    "ContentType",
    "get_ocr_router",
    "ocr_image",
    "TesseractEngine",
    "check_tesseract_installation",
]
