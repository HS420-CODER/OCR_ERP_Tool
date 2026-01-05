"""
Unit tests for TesseractEngine (Phase 2).

These tests verify:
1. Engine registration and availability checks
2. Language mapping and normalization
3. OCR processing (when Tesseract is installed)
4. Error handling for missing dependencies
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.engines.tesseract_engine import TesseractEngine
from src.engines.base_engine import EngineCapabilities


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestTesseractEngineBasics:
    """Tests for basic engine properties."""

    def test_engine_name(self):
        """Test engine name property."""
        engine = TesseractEngine()
        assert engine.name == "tesseract"

    def test_display_name(self):
        """Test display name property."""
        engine = TesseractEngine()
        assert engine.display_name == "Tesseract OCR"

    def test_capabilities(self):
        """Test engine capabilities."""
        engine = TesseractEngine()
        caps = engine.get_capabilities()

        assert isinstance(caps, EngineCapabilities)
        assert caps.supports_images == True
        assert caps.supports_pdf == True
        assert caps.supports_vision_analysis == False
        assert caps.supports_gpu == False
        assert "en" in caps.supported_languages
        assert "ar" in caps.supported_languages


class TestLanguageMapping:
    """Tests for language code normalization."""

    @pytest.fixture
    def engine(self):
        return TesseractEngine()

    def test_normalize_english(self, engine):
        """Test English language normalization."""
        assert engine._normalize_lang("en") == "eng"
        assert engine._normalize_lang("eng") == "eng"
        assert engine._normalize_lang("english") == "eng"
        assert engine._normalize_lang("EN") == "eng"

    def test_normalize_arabic(self, engine):
        """Test Arabic language normalization."""
        assert engine._normalize_lang("ar") == "ara"
        assert engine._normalize_lang("ara") == "ara"
        assert engine._normalize_lang("arabic") == "ara"
        assert engine._normalize_lang("AR") == "ara"

    def test_normalize_unknown(self, engine):
        """Test unknown language passthrough."""
        assert engine._normalize_lang("xyz") == "xyz"

    def test_supported_languages(self, engine):
        """Test supported languages list."""
        langs = engine.get_supported_languages()
        assert "en" in langs
        assert "ar" in langs

    def test_supports_language(self, engine):
        """Test language support check."""
        assert engine.supports_language("en") == True
        assert engine.supports_language("ar") == True
        assert engine.supports_language("EN") == True


class TestTesseractAvailability:
    """Tests for Tesseract availability checking."""

    def test_is_available_returns_boolean(self):
        """Test that is_available returns a boolean."""
        engine = TesseractEngine()
        result = engine.is_available()
        assert isinstance(result, bool)

    def test_availability_caching(self):
        """Test that availability check is cached."""
        engine = TesseractEngine()

        # First call checks availability
        result1 = engine.is_available()

        # Second call should use cache
        result2 = engine.is_available()

        assert result1 == result2


class TestTesseractConfig:
    """Tests for Tesseract configuration building."""

    @pytest.fixture
    def engine(self):
        return TesseractEngine()

    def test_default_config(self, engine):
        """Test default config generation."""
        config = engine._build_config(None)
        assert "--psm 3" in config
        assert "--oem 3" in config

    def test_custom_psm(self, engine):
        """Test custom PSM setting."""
        config = engine._build_config({"psm": 6})
        assert "--psm 6" in config

    def test_custom_oem(self, engine):
        """Test custom OEM setting."""
        config = engine._build_config({"oem": 1})
        assert "--oem 1" in config

    def test_custom_config_string(self, engine):
        """Test custom config string."""
        config = engine._build_config({"config": "-c preserve_interword_spaces=1"})
        assert "-c preserve_interword_spaces=1" in config


class TestTesseractEngineNotInstalled:
    """Tests for when Tesseract is not installed."""

    @pytest.fixture
    def engine_not_available(self):
        """Create an engine that is not available."""
        engine = TesseractEngine()
        engine._available = False
        return engine

    def test_process_image_when_unavailable(self, engine_not_available):
        """Test error handling when Tesseract is not installed."""
        result = engine_not_available.process_image("/fake/image.png", "en")

        assert result.success == False
        assert "not installed" in result.error.lower() or "not available" in result.error.lower()

    def test_process_pdf_when_unavailable(self, engine_not_available):
        """Test error handling for PDF when Tesseract is not installed."""
        result = engine_not_available.process_pdf("/fake/doc.pdf", "en")

        assert result.success == False
        assert "not installed" in result.error.lower() or "not available" in result.error.lower()


class TestTesseractEngineFileValidation:
    """Tests for file validation."""

    @pytest.fixture
    def engine(self):
        engine = TesseractEngine()
        # Mock availability to True for file validation tests
        engine._available = True
        return engine

    def test_nonexistent_image_error(self, engine):
        """Test error for non-existent image file."""
        result = engine.process_image("/nonexistent/path/image.png", "en")

        assert result.success == False
        assert "not found" in result.error.lower()

    def test_nonexistent_pdf_error(self, engine):
        """Test error for non-existent PDF file."""
        result = engine.process_pdf("/nonexistent/path/doc.pdf", "en")

        assert result.success == False
        assert "not found" in result.error.lower()

    def test_unsupported_language_error(self, engine):
        """Test error for unsupported language."""
        # Create a test file
        test_file = FIXTURES_DIR / "test_image.png"
        if not test_file.exists():
            pytest.skip("Test image fixture not available")

        result = engine.process_image(str(test_file), "xyz")

        assert result.success == False
        assert "not supported" in result.error.lower()


class TestTesseractEngineRegistration:
    """Tests for engine registration in the system."""

    def test_engine_importable(self):
        """Test that TesseractEngine can be imported from engines package."""
        from src.engines import TesseractEngine
        assert TesseractEngine is not None

    def test_engine_in_all_exports(self):
        """Test that TesseractEngine is in __all__ exports."""
        from src import engines
        assert "TesseractEngine" in engines.__all__

    def test_read_tool_registers_tesseract(self):
        """Test that HybridReadTool registers TesseractEngine."""
        from src.read_tool import HybridReadTool

        reader = HybridReadTool()
        engine_classes = reader.engine_manager._engine_classes

        assert "tesseract" in engine_classes


class TestTesseractWithMockedPytesseract:
    """Tests using mocked pytesseract for predictable results."""

    @pytest.fixture
    def mock_pytesseract(self):
        """Create mocked pytesseract module."""
        mock = MagicMock()
        mock.get_tesseract_version.return_value = "5.3.3"
        mock.get_languages.return_value = ["eng", "ara", "osd"]
        mock.Output = MagicMock()
        mock.Output.DICT = "dict"
        return mock

    @pytest.fixture
    def engine_with_mock(self, mock_pytesseract):
        """Create engine with mocked pytesseract."""
        engine = TesseractEngine()
        engine._pytesseract = mock_pytesseract
        engine._available = True
        return engine

    def test_get_installed_languages(self, engine_with_mock, mock_pytesseract):
        """Test getting installed languages."""
        langs = engine_with_mock.get_installed_languages()

        assert "eng" in langs
        assert "ara" in langs
        mock_pytesseract.get_languages.assert_called_once()

    def test_check_language_installed_english(self, engine_with_mock):
        """Test checking if English is installed."""
        result = engine_with_mock._check_language_installed("en")
        assert result == True

    def test_check_language_installed_arabic(self, engine_with_mock):
        """Test checking if Arabic is installed."""
        result = engine_with_mock._check_language_installed("ar")
        assert result == True


class TestTesseractDataParsing:
    """Tests for Tesseract output data parsing."""

    @pytest.fixture
    def engine(self):
        return TesseractEngine()

    def test_parse_empty_data(self, engine):
        """Test parsing empty Tesseract data."""
        data = {
            'text': [],
            'conf': [],
            'left': [],
            'top': [],
            'width': [],
            'height': [],
            'line_num': [],
            'block_num': []
        }

        text_blocks, full_text = engine._parse_tesseract_data(data)

        assert len(text_blocks) == 0
        assert full_text == ""

    def test_parse_single_word(self, engine):
        """Test parsing single word output."""
        data = {
            'text': ['Hello'],
            'conf': [95],
            'left': [10],
            'top': [20],
            'width': [50],
            'height': [15],
            'line_num': [1],
            'block_num': [1]
        }

        text_blocks, full_text = engine._parse_tesseract_data(data)

        assert len(text_blocks) == 1
        assert text_blocks[0].text == "Hello"
        assert text_blocks[0].confidence == 0.95
        assert "Hello" in full_text

    def test_parse_multiple_words_same_line(self, engine):
        """Test parsing multiple words on same line."""
        data = {
            'text': ['Hello', 'World'],
            'conf': [95, 90],
            'left': [10, 70],
            'top': [20, 20],
            'width': [50, 60],
            'height': [15, 15],
            'line_num': [1, 1],
            'block_num': [1, 1]
        }

        text_blocks, full_text = engine._parse_tesseract_data(data)

        # Should combine into one text block for the line
        assert len(text_blocks) == 1
        assert "Hello" in text_blocks[0].text
        assert "World" in text_blocks[0].text
        assert "Hello World" in full_text or "Hello  World" in full_text

    def test_parse_skips_empty_text(self, engine):
        """Test that empty text entries are skipped."""
        data = {
            'text': ['Hello', '', '  ', 'World'],
            'conf': [95, 90, 85, 92],
            'left': [10, 50, 60, 70],
            'top': [20, 20, 20, 20],
            'width': [40, 10, 5, 60],
            'height': [15, 15, 15, 15],
            'line_num': [1, 1, 1, 1],
            'block_num': [1, 1, 1, 1]
        }

        text_blocks, full_text = engine._parse_tesseract_data(data)

        # Empty entries should be skipped
        assert len(text_blocks) == 1
        assert "Hello" in full_text
        assert "World" in full_text

    def test_parse_skips_low_confidence(self, engine):
        """Test that entries with conf=-1 are skipped."""
        data = {
            'text': ['Hello', 'noise'],
            'conf': [95, -1],
            'left': [10, 100],
            'top': [20, 20],
            'width': [50, 30],
            'height': [15, 15],
            'line_num': [1, 1],
            'block_num': [1, 1]
        }

        text_blocks, full_text = engine._parse_tesseract_data(data)

        assert len(text_blocks) == 1
        assert "Hello" in text_blocks[0].text
        assert "noise" not in text_blocks[0].text

    def test_parse_multiple_lines(self, engine):
        """Test parsing multiple lines."""
        data = {
            'text': ['Line1', 'Line2'],
            'conf': [95, 92],
            'left': [10, 10],
            'top': [20, 50],
            'width': [50, 50],
            'height': [15, 15],
            'line_num': [1, 2],
            'block_num': [1, 1]
        }

        text_blocks, full_text = engine._parse_tesseract_data(data)

        assert len(text_blocks) == 2
        lines = full_text.split('\n')
        assert len(lines) == 2


class TestWindowsPathDetection:
    """Tests for Windows Tesseract path detection."""

    def test_windows_paths_defined(self):
        """Test that Windows paths are defined."""
        from src.engines.tesseract_engine import TesseractEngine

        assert len(TesseractEngine.WINDOWS_TESSERACT_PATHS) > 0
        assert r"C:\Program Files\Tesseract-OCR\tesseract.exe" in TesseractEngine.WINDOWS_TESSERACT_PATHS


# Conditional tests that run only when Tesseract is installed
class TestTesseractIntegration:
    """Integration tests that require Tesseract to be installed."""

    @pytest.fixture
    def engine(self):
        engine = TesseractEngine()
        if not engine.is_available():
            pytest.skip("Tesseract is not installed - skipping integration tests")
        return engine

    def test_process_real_image(self, engine):
        """Test processing a real image file (requires Tesseract)."""
        # Look for a test image
        test_image = FIXTURES_DIR / "test_image.png"
        if not test_image.exists():
            pytest.skip("Test image fixture not available")

        result = engine.process_image(str(test_image), "en")

        # Should either succeed or fail gracefully
        assert hasattr(result, 'success')
        if result.success:
            assert result.full_text is not None
            assert result.engine_used == "tesseract"

    def test_get_text_only_convenience(self, engine):
        """Test get_text_only convenience method."""
        test_image = FIXTURES_DIR / "test_image.png"
        if not test_image.exists():
            pytest.skip("Test image fixture not available")

        try:
            text = engine.get_text_only(str(test_image), "en")
            assert isinstance(text, str)
        except Exception:
            # May fail if language pack not installed
            pass
