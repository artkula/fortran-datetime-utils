"""
Tests for OCR functionality.
"""

import pytest
from pathlib import Path
from aems.ocr import OCRRouter, OCREngine, ContentType, OCRResult
from aems.ocr.tesseract_engine import check_tesseract_installation


def test_ocr_engine_enum():
    """Test OCR engine enum."""
    assert OCREngine.TESSERACT.value == "tesseract"
    assert OCREngine.PIX2TEX.value == "pix2tex"


def test_content_type_enum():
    """Test content type enum."""
    assert ContentType.PRINTED.value == "printed"
    assert ContentType.HANDWRITING.value == "handwriting"
    assert ContentType.MATH.value == "math"


def test_ocr_result_creation():
    """Test OCRResult creation."""
    result = OCRResult(
        text="Hello world",
        confidence=0.95,
        engine=OCREngine.TESSERACT,
        language="eng",
        metadata={"source": "test"},
    )

    assert result.text == "Hello world"
    assert result.confidence == 0.95
    assert result.engine == OCREngine.TESSERACT
    assert result.language == "eng"
    assert result.metadata["source"] == "test"


def test_ocr_router_initialization():
    """Test OCR router initialization."""
    router = OCRRouter()
    assert router is not None


def test_content_type_detection():
    """Test content type detection (currently returns default)."""
    router = OCRRouter()
    # For now, this should return PRINTED as default
    # In future, will use ML-based detection
    content_type = router.detect_content_type(Path("test.png"))
    assert content_type == ContentType.PRINTED


def test_get_best_engine():
    """Test best engine selection."""
    router = OCRRouter()

    # For printed text, should prefer Tesseract
    engine = router.get_best_engine(ContentType.PRINTED)
    assert engine == OCREngine.TESSERACT

    # For mixed content, default to Tesseract
    engine = router.get_best_engine(ContentType.MIXED)
    assert engine == OCREngine.TESSERACT


def test_tesseract_check():
    """Test Tesseract installation check."""
    info = check_tesseract_installation()

    assert "installed" in info
    assert "version" in info
    assert "languages" in info
    assert "path" in info

    # If Tesseract is installed, check details
    if info["installed"]:
        assert info["version"] is not None
        assert info["path"] is not None
        # Should have at least 'eng' language
        assert len(info["languages"]) > 0


@pytest.mark.skipif(
    not check_tesseract_installation()["installed"],
    reason="Tesseract not installed"
)
def test_ocr_router_with_tesseract():
    """Test OCR router with real Tesseract (if available)."""
    from aems.ocr import get_ocr_router

    router = get_ocr_router()
    assert router is not None
    assert OCREngine.TESSERACT in router._engines


# Integration tests (skip if Tesseract not available)
@pytest.mark.skipif(
    not check_tesseract_installation()["installed"],
    reason="Tesseract not installed"
)
def test_ocr_simple_image(tmp_path):
    """
    Test OCR on a simple generated image (if Tesseract available).

    Creates a simple image with text and runs OCR.
    """
    from PIL import Image, ImageDraw, ImageFont

    # Create a simple image with text
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)

    # Use default font
    d.text((10, 10), "AEMS Test OCR", fill='black')

    # Save to temp file
    img_path = tmp_path / "test_ocr.png"
    img.save(img_path)

    # Run OCR
    from aems.ocr import ocr_image

    result = ocr_image(img_path, language="eng")

    # Check result
    assert result.text  # Should have some text
    assert result.engine == OCREngine.TESSERACT
    assert result.confidence >= 0  # Confidence should be non-negative
    assert "AEMS" in result.text or "Test" in result.text or "OCR" in result.text
