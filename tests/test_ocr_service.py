"""
ERP Arabic OCR Microservice - OCR Service Unit Tests
=====================================================
Tests for the MultiEngineArabicOCR service.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services import OCREngine, OCRResult, TextBlock, BoundingBox
from config.settings import EngineMode


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_arabic_image():
    """Create a sample image with Arabic-like content."""
    # Create a simple test image
    img = Image.new('RGB', (800, 200), color='white')
    return np.array(img)


@pytest.fixture
def sample_image_file(tmp_path):
    """Create a temporary image file."""
    img = Image.new('RGB', (800, 200), color='white')
    img_path = tmp_path / "test_image.png"
    img.save(img_path)
    return str(img_path)


@pytest.fixture
def mock_paddle_result():
    """Mock PaddleOCR result."""
    return [
        [
            [[10, 10], [100, 10], [100, 40], [10, 40]],
            ("الرقم الضريبي", 0.95)
        ],
        [
            [[10, 50], [150, 50], [150, 80], [10, 80]],
            ("310123456789012", 0.92)
        ]
    ]


@pytest.fixture
def mock_easyocr_result():
    """Mock EasyOCR result."""
    return [
        ([[10, 10], [100, 10], [100, 40], [10, 40]], "الرقم الضريبي", 0.93),
        ([[10, 50], [150, 50], [150, 80], [10, 80]], "310123456789012", 0.90)
    ]


# ==============================================================================
# OCR Engine Initialization Tests
# ==============================================================================

class TestOCREngineInitialization:
    """Tests for OCR engine initialization."""

    def test_paddle_ocr_import(self):
        """Test PaddleOCR can be imported."""
        try:
            from paddleocr import PaddleOCR
            assert PaddleOCR is not None
        except ImportError:
            pytest.skip("PaddleOCR not installed")

    def test_easyocr_import(self):
        """Test EasyOCR can be imported."""
        try:
            import easyocr
            assert easyocr is not None
        except ImportError:
            pytest.skip("EasyOCR not installed")

    def test_tesseract_import(self):
        """Test pytesseract can be imported."""
        try:
            import pytesseract
            assert pytesseract is not None
        except ImportError:
            pytest.skip("pytesseract not installed")

    def test_multi_engine_ocr_init(self):
        """Test MultiEngineArabicOCR initialization."""
        from src.services.ocr_microservice import MultiEngineArabicOCR

        # Initialize with paddle only mode
        ocr = MultiEngineArabicOCR(
            engine_mode=EngineMode.PADDLE_ONLY,
            use_gpu=False
        )

        assert ocr is not None
        assert ocr.engine_mode == EngineMode.PADDLE_ONLY

    def test_ocr_result_dataclass(self):
        """Test OCRResult dataclass."""
        result = OCRResult(
            text="Test text",
            confidence=0.95,
            engine=OCREngine.PADDLE,
            blocks=[],
            raw_text="Test text",
            processing_time_ms=100.0
        )

        assert result.text == "Test text"
        assert result.confidence == 0.95
        assert result.engine == OCREngine.PADDLE
        assert result.processing_time_ms == 100.0

    def test_text_block_dataclass(self):
        """Test TextBlock dataclass."""
        bbox = BoundingBox(x1=10, y1=10, x2=100, y2=40)
        block = TextBlock(
            text="مرحبا",
            confidence=0.92,
            bbox=bbox,
            language="ar"
        )

        assert block.text == "مرحبا"
        assert block.confidence == 0.92
        assert block.bbox.width == 90
        assert block.language == "ar"

    def test_bounding_box_properties(self):
        """Test BoundingBox properties."""
        bbox = BoundingBox(x1=10, y1=20, x2=110, y2=70)

        assert bbox.width == 100
        assert bbox.height == 50
        assert bbox.area == 5000
        assert bbox.center == (60, 45)


# ==============================================================================
# OCR Processing Tests
# ==============================================================================

class TestOCRProcessing:
    """Tests for OCR processing functionality."""

    def test_paddle_ocr_processing(self, sample_image_file, mock_paddle_result):
        """Test PaddleOCR processing."""
        from src.services.ocr_microservice import MultiEngineArabicOCR

        ocr = MultiEngineArabicOCR(engine_mode=EngineMode.PADDLE_ONLY, use_gpu=False)

        # Skip if PaddleOCR not properly initialized
        if ocr._paddle_ocr is None:
            pytest.skip("PaddleOCR not initialized")

        # Load test image
        img = np.array(Image.open(sample_image_file))
        result = ocr._run_paddle(img)

        assert result is not None
        assert result.engine == OCREngine.PADDLE

    def test_easyocr_processing(self, sample_image_file, mock_easyocr_result):
        """Test EasyOCR processing."""
        pytest.skip("EasyOCR not installed in test environment")

    def test_process_image_with_numpy_array(self, sample_arabic_image):
        """Test processing numpy array input."""
        from src.services.ocr_microservice import MultiEngineArabicOCR

        ocr = MultiEngineArabicOCR(engine_mode=EngineMode.PADDLE_ONLY, use_gpu=False)
        result = ocr.process_image(sample_arabic_image)

        assert result is not None
        assert isinstance(result, OCRResult)

    def test_engine_status(self):
        """Test engine status reporting."""
        from src.services.ocr_microservice import MultiEngineArabicOCR

        ocr = MultiEngineArabicOCR(engine_mode=EngineMode.PADDLE_ONLY, use_gpu=False)
        status = ocr.get_engine_status()

        assert 'paddle' in status
        assert 'easyocr' in status
        assert 'tesseract' in status


# ==============================================================================
# Confidence Score Tests
# ==============================================================================

class TestConfidenceScores:
    """Tests for confidence score calculations."""

    def test_confidence_range(self):
        """Test confidence scores are in valid range."""
        result = OCRResult(
            text="Test",
            confidence=0.85,
            engine=OCREngine.PADDLE,
            blocks=[]
        )

        assert 0.0 <= result.confidence <= 1.0

    def test_block_confidence_aggregation(self):
        """Test confidence aggregation from blocks."""
        blocks = [
            TextBlock(text="Hello", confidence=0.9, bbox=None),
            TextBlock(text="World", confidence=0.8, bbox=None),
            TextBlock(text="Test", confidence=0.7, bbox=None)
        ]

        # Calculate average confidence
        avg_confidence = sum(b.confidence for b in blocks) / len(blocks)
        assert abs(avg_confidence - 0.8) < 0.01

    def test_empty_result_confidence(self):
        """Test confidence for empty result."""
        result = OCRResult(
            text="",
            confidence=0.0,
            engine=OCREngine.PADDLE,
            blocks=[]
        )

        assert result.confidence == 0.0
        assert result.word_count == 0


# ==============================================================================
# Arabic Text Processing Tests
# ==============================================================================

class TestArabicProcessing:
    """Tests for Arabic-specific processing."""

    def test_arabic_text_extraction(self):
        """Test Arabic text is properly extracted."""
        arabic_text = "الرقم الضريبي: 310123456789012"
        result = OCRResult(
            text=arabic_text,
            confidence=0.95,
            engine=OCREngine.PADDLE,
            blocks=[]
        )

        assert "الرقم الضريبي" in result.text
        assert result.word_count > 0

    def test_bilingual_text_extraction(self):
        """Test Arabic+English mixed text."""
        text = "Invoice رقم الفاتورة Number: 12345"
        result = OCRResult(
            text=text,
            confidence=0.92,
            engine=OCREngine.PADDLE,
            blocks=[]
        )

        assert "Invoice" in result.text
        assert "رقم الفاتورة" in result.text
        assert "12345" in result.text

    def test_rtl_text_handling(self):
        """Test right-to-left text handling."""
        # Arabic text is RTL
        arabic_text = "مرحبا بالعالم"
        block = TextBlock(
            text=arabic_text,
            confidence=0.95,
            bbox=BoundingBox(100, 10, 10, 40),  # RTL bbox
            language="ar"
        )

        assert block.text == arabic_text
        assert block.language == "ar"


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_image_path(self):
        """Test handling of invalid image path."""
        from src.services.ocr_microservice import MultiEngineArabicOCR

        ocr = MultiEngineArabicOCR(engine_mode=EngineMode.PADDLE_ONLY, use_gpu=False)

        with pytest.raises(Exception):
            ocr.process_image("/nonexistent/path.png")

    def test_corrupted_image_handling(self, tmp_path):
        """Test handling of corrupted image."""
        # Create corrupted file
        corrupted_path = tmp_path / "corrupted.png"
        corrupted_path.write_bytes(b"not an image")

        from src.services.ocr_microservice import MultiEngineArabicOCR

        ocr = MultiEngineArabicOCR(engine_mode=EngineMode.PADDLE_ONLY, use_gpu=False)

        # Should handle gracefully - either raise or return empty result
        try:
            result = ocr.process_image(str(corrupted_path))
            # If no exception, check it's a valid OCRResult
            assert isinstance(result, OCRResult)
        except Exception:
            # Exception is acceptable for corrupted images
            pass

    def test_empty_image_handling(self, tmp_path):
        """Test handling of empty/blank image."""
        # Create blank white image
        blank_img = Image.new('RGB', (100, 100), color='white')
        blank_path = tmp_path / "blank.png"
        blank_img.save(blank_path)

        from src.services.ocr_microservice import MultiEngineArabicOCR

        ocr = MultiEngineArabicOCR(engine_mode=EngineMode.PADDLE_ONLY, use_gpu=False)
        result = ocr.process_image(str(blank_path))

        # Blank image should return empty or low confidence result
        assert isinstance(result, OCRResult)


# ==============================================================================
# Serialization Tests
# ==============================================================================

class TestSerialization:
    """Tests for result serialization."""

    def test_ocr_result_to_dict(self):
        """Test OCRResult to_dict method."""
        result = OCRResult(
            text="Test text",
            confidence=0.95,
            engine=OCREngine.PADDLE,
            blocks=[
                TextBlock(text="Test", confidence=0.95, bbox=None)
            ],
            raw_text="Test text",
            processing_time_ms=150.0
        )

        result_dict = result.to_dict()

        assert result_dict['text'] == "Test text"
        assert result_dict['confidence'] == 0.95
        assert result_dict['engine'] == "paddle"
        assert result_dict['processing_time_ms'] == 150.0
        assert len(result_dict['blocks']) == 1

    def test_bounding_box_from_points(self):
        """Test BoundingBox.from_points method."""
        points = [[10, 10], [100, 10], [100, 40], [10, 40]]
        bbox = BoundingBox.from_points(points)

        assert bbox.x1 == 10
        assert bbox.y1 == 10
        assert bbox.x2 == 100
        assert bbox.y2 == 40

    def test_text_block_to_dict(self):
        """Test TextBlock to_dict method."""
        bbox = BoundingBox(10, 10, 100, 40)
        block = TextBlock(
            text="مرحبا",
            confidence=0.92,
            bbox=bbox,
            language="ar"
        )

        block_dict = block.to_dict()

        assert block_dict['text'] == "مرحبا"
        assert block_dict['confidence'] == 0.92
        assert block_dict['language'] == "ar"
        assert block_dict['bbox']['width'] == 90


# ==============================================================================
# Performance Tests
# ==============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_result_creation_speed(self):
        """Test OCRResult creation is fast."""
        import time

        start = time.time()
        for _ in range(1000):
            OCRResult(
                text="Test text " * 100,
                confidence=0.95,
                engine=OCREngine.PADDLE,
                blocks=[]
            )
        elapsed = time.time() - start

        # Should create 1000 results in under 1 second
        assert elapsed < 1.0

    def test_large_text_handling(self):
        """Test handling of large text output."""
        large_text = "مرحبا " * 10000  # ~60KB of Arabic text

        result = OCRResult(
            text=large_text,
            confidence=0.90,
            engine=OCREngine.PADDLE,
            blocks=[]
        )

        assert len(result.text) > 50000
        assert result.word_count == 10000


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
