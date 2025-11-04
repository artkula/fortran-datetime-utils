"""
OCR Router - Intelligent routing to the best OCR engine for each content type.

Supports multiple OCR engines:
- Tesseract: Printed text (100+ languages)
- docTR/TrOCR: Handwriting (future)
- pix2tex: Mathematical expressions (future)
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path

from PIL import Image

from aems.ocr.tesseract_engine import TesseractEngine
from aems.config import get_config

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Types of content that can be OCR'd."""
    PRINTED = "printed"
    HANDWRITING = "handwriting"
    MATH = "math"
    MIXED = "mixed"


class OCREngine(str, Enum):
    """Available OCR engines."""
    TESSERACT = "tesseract"
    DOCTRL = "doctr"
    TROCR = "trocr"
    PIX2TEX = "pix2tex"
    MATHPIX = "mathpix"


class OCRResult:
    """Result from OCR processing."""

    def __init__(
        self,
        text: str,
        confidence: float,
        engine: OCREngine,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.engine = engine
        self.language = language
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return (
            f"OCRResult(engine={self.engine.value}, "
            f"confidence={self.confidence:.2f}, "
            f"text_len={len(self.text)})"
        )


class OCRRouter:
    """
    Routes OCR requests to the appropriate engine based on content type.

    Provides a unified interface for different OCR engines and automatically
    selects the best engine for each content type.
    """

    def __init__(self):
        """Initialize the OCR router with available engines."""
        self.config = get_config()
        self._engines: Dict[OCREngine, Any] = {}
        self._initialize_engines()

    def _initialize_engines(self) -> None:
        """Initialize available OCR engines."""
        # Initialize Tesseract (always available)
        try:
            self._engines[OCREngine.TESSERACT] = TesseractEngine(
                lang=self.config.tesseract_lang
            )
            logger.info("Initialized Tesseract engine")
        except Exception as e:
            logger.warning(f"Failed to initialize Tesseract: {e}")

        # TODO: Initialize other engines when implemented
        # - docTR/TrOCR for handwriting
        # - pix2tex for math

    def detect_content_type(self, image_path: Path) -> ContentType:
        """
        Detect the content type of an image region.

        Args:
            image_path: Path to image file

        Returns:
            ContentType enum

        Note:
            Currently returns MIXED as default. Future versions will use
            ML-based classification to detect printed vs handwriting vs math.
        """
        # TODO: Implement ML-based content type detection
        # For now, default to printed text
        return ContentType.PRINTED

    def get_best_engine(self, content_type: ContentType) -> OCREngine:
        """
        Get the best OCR engine for a content type.

        Args:
            content_type: Type of content to OCR

        Returns:
            Best available OCR engine for this content type
        """
        # Engine preferences by content type
        preferences = {
            ContentType.PRINTED: [OCREngine.TESSERACT],
            ContentType.HANDWRITING: [OCREngine.TROCR, OCREngine.DOCTRL, OCREngine.TESSERACT],
            ContentType.MATH: [OCREngine.PIX2TEX, OCREngine.MATHPIX, OCREngine.TESSERACT],
            ContentType.MIXED: [OCREngine.TESSERACT],
        }

        # Return first available engine from preference list
        for engine in preferences.get(content_type, [OCREngine.TESSERACT]):
            if engine in self._engines:
                return engine

        # Fallback to Tesseract
        if OCREngine.TESSERACT in self._engines:
            return OCREngine.TESSERACT

        raise RuntimeError("No OCR engines available")

    def ocr_image(
        self,
        image_path: Path,
        engine: Optional[OCREngine] = None,
        language: Optional[str] = None,
        content_type: Optional[ContentType] = None,
    ) -> OCRResult:
        """
        Perform OCR on an image file.

        Args:
            image_path: Path to image file
            engine: Specific engine to use (None = auto-select)
            language: Language hint (ISO-639 code)
            content_type: Type of content (None = auto-detect)

        Returns:
            OCRResult with text and confidence
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Detect content type if not provided
        if content_type is None:
            content_type = self.detect_content_type(image_path)
            logger.debug(f"Detected content type: {content_type.value}")

        # Select engine if not specified
        if engine is None:
            engine = self.get_best_engine(content_type)
            logger.debug(f"Selected engine: {engine.value}")

        # Check engine is available
        if engine not in self._engines:
            raise ValueError(f"Engine not available: {engine.value}")

        # Use language from config if not specified
        if language is None:
            language = self.config.tesseract_lang

        # Perform OCR with selected engine
        ocr_engine = self._engines[engine]

        try:
            result = ocr_engine.extract_text(image_path, language=language)
            logger.info(
                f"OCR complete: {len(result.text)} chars, "
                f"confidence={result.confidence:.2f}"
            )
            return result
        except Exception as e:
            logger.error(f"OCR failed with {engine.value}: {e}")
            raise

    def ocr_region(
        self,
        image: Image.Image,
        bbox: tuple,
        engine: Optional[OCREngine] = None,
        language: Optional[str] = None,
    ) -> OCRResult:
        """
        Perform OCR on a specific region of an image.

        Args:
            image: PIL Image object
            bbox: Bounding box (x0, y0, x1, y1)
            engine: Specific engine to use
            language: Language hint

        Returns:
            OCRResult with text and confidence
        """
        # Crop to region
        region = image.crop(bbox)

        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            region.save(tmp.name)
            tmp_path = Path(tmp.name)

        try:
            result = self.ocr_image(tmp_path, engine=engine, language=language)
            return result
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    def batch_ocr(
        self,
        image_paths: List[Path],
        engine: Optional[OCREngine] = None,
        language: Optional[str] = None,
    ) -> List[OCRResult]:
        """
        Perform OCR on multiple images.

        Args:
            image_paths: List of image paths
            engine: Specific engine to use for all images
            language: Language hint

        Returns:
            List of OCRResult objects
        """
        results = []
        for path in image_paths:
            try:
                result = self.ocr_image(path, engine=engine, language=language)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to OCR {path}: {e}")
                # Add empty result to maintain list alignment
                results.append(
                    OCRResult(
                        text="",
                        confidence=0.0,
                        engine=engine or OCREngine.TESSERACT,
                        metadata={"error": str(e)},
                    )
                )

        return results


# Global router instance
_router: Optional[OCRRouter] = None


def get_ocr_router() -> OCRRouter:
    """
    Get the global OCR router instance.

    Returns:
        OCRRouter instance
    """
    global _router
    if _router is None:
        _router = OCRRouter()
    return _router


def ocr_image(image_path: Path, **kwargs) -> OCRResult:
    """
    Convenience function for OCR on an image file.

    Args:
        image_path: Path to image file
        **kwargs: Additional arguments passed to OCRRouter.ocr_image()

    Returns:
        OCRResult
    """
    router = get_ocr_router()
    return router.ocr_image(image_path, **kwargs)
