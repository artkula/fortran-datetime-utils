"""
Tesseract OCR Engine wrapper.

Provides a clean interface to Tesseract OCR with support for:
- 100+ languages
- Confidence scoring
- Multiple output formats (text, hOCR, TSV)
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess
import shutil

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


class TesseractEngine:
    """
    Tesseract OCR engine wrapper.

    Handles text extraction from images with confidence scoring and
    multi-language support.
    """

    def __init__(self, lang: str = "eng", tesseract_cmd: Optional[str] = None):
        """
        Initialize Tesseract engine.

        Args:
            lang: Language code(s), e.g., 'eng', 'eng+swe', 'rus'
            tesseract_cmd: Path to tesseract binary (None = auto-detect)
        """
        if not PYTESSERACT_AVAILABLE:
            raise ImportError(
                "pytesseract not installed. Install with: pip install pytesseract"
            )

        self.lang = lang

        # Set tesseract command if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # Verify tesseract is available
        if not self._check_tesseract():
            raise RuntimeError(
                "Tesseract not found. Please install tesseract-ocr:\n"
                "  Ubuntu/Debian: sudo apt-get install tesseract-ocr\n"
                "  MacOS: brew install tesseract\n"
                "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )

        logger.info(f"Initialized Tesseract engine with language: {lang}")

    def _check_tesseract(self) -> bool:
        """Check if tesseract is available."""
        try:
            version = pytesseract.get_tesseract_version()
            logger.debug(f"Tesseract version: {version}")
            return True
        except Exception as e:
            logger.error(f"Tesseract check failed: {e}")
            return False

    def extract_text(
        self,
        image_path: Path,
        language: Optional[str] = None,
        config: Optional[str] = None,
    ) -> "OCRResult":
        """
        Extract text from an image file.

        Args:
            image_path: Path to image file
            language: Language override (None = use default)
            config: Tesseract config string

        Returns:
            OCRResult with text and confidence
        """
        from aems.ocr.router import OCRResult, OCREngine

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        lang = language or self.lang

        try:
            # Load image
            image = Image.open(image_path)

            # Extract text
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=config or "",
            )

            # Get detailed data for confidence calculation
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )

            # Calculate average confidence
            confidences = [
                float(conf) for conf in data["conf"] if conf != -1
            ]
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence / 100.0,  # Normalize to 0-1
                engine=OCREngine.TESSERACT,
                language=lang,
                metadata={
                    "num_words": len([c for c in data["conf"] if c != -1]),
                    "image_size": image.size,
                },
            )

        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            raise

    def extract_with_boxes(
        self,
        image_path: Path,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract text with bounding box information.

        Args:
            image_path: Path to image file
            language: Language override

        Returns:
            Dictionary with text and word-level bounding boxes
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        lang = language or self.lang

        try:
            image = Image.open(image_path)

            # Get detailed data with boxes
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )

            # Parse into structured format
            words = []
            for i in range(len(data["text"])):
                if data["text"][i].strip():
                    words.append({
                        "text": data["text"][i],
                        "confidence": float(data["conf"][i]) / 100.0,
                        "bbox": {
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        },
                        "block": data["block_num"][i],
                        "paragraph": data["par_num"][i],
                        "line": data["line_num"][i],
                        "word": data["word_num"][i],
                    })

            full_text = " ".join([w["text"] for w in words])

            return {
                "text": full_text,
                "words": words,
                "language": lang,
            }

        except Exception as e:
            logger.error(f"Tesseract box extraction failed: {e}")
            raise

    def get_available_languages(self) -> List[str]:
        """
        Get list of available Tesseract languages.

        Returns:
            List of language codes
        """
        try:
            langs = pytesseract.get_languages()
            return sorted(langs)
        except Exception as e:
            logger.error(f"Failed to get languages: {e}")
            return []

    def extract_hocr(
        self,
        image_path: Path,
        language: Optional[str] = None,
    ) -> str:
        """
        Extract text as hOCR (HTML-based OCR format).

        Args:
            image_path: Path to image file
            language: Language override

        Returns:
            hOCR formatted string
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        lang = language or self.lang

        try:
            image = Image.open(image_path)
            hocr = pytesseract.image_to_pdf_or_hocr(
                image,
                lang=lang,
                extension="hocr",
            )
            return hocr.decode("utf-8")

        except Exception as e:
            logger.error(f"hOCR extraction failed: {e}")
            raise


def check_tesseract_installation() -> Dict[str, Any]:
    """
    Check Tesseract installation and available languages.

    Returns:
        Dictionary with installation status and available languages
    """
    result = {
        "installed": False,
        "version": None,
        "languages": [],
        "path": None,
    }

    # Check if tesseract binary exists
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        result["path"] = tesseract_path
        result["installed"] = True

        try:
            # Get version
            version_output = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
            )
            first_line = version_output.stdout.split("\n")[0]
            result["version"] = first_line

            # Get languages
            if PYTESSERACT_AVAILABLE:
                engine = TesseractEngine()
                result["languages"] = engine.get_available_languages()

        except Exception as e:
            logger.error(f"Failed to query tesseract: {e}")

    return result
