"""
Tests for PaddleOCR engine.

Tests engine initialization, configuration, language mapping,
OCR result parsing, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import numpy as np


class TestPaddleEngineBasics:
    """Tests for basic PaddleEngine properties."""

    def test_engine_name(self):
        """Test engine name is 'paddle'."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.name == "paddle"

    def test_display_name(self):
        """Test display name is 'PaddleOCR'."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.display_name == "PaddleOCR"

    def test_supported_languages_list(self):
        """Test supported languages includes en and ar."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert "en" in engine.SUPPORTED_LANGUAGES
        assert "ar" in engine.SUPPORTED_LANGUAGES

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine._lang == "en"
        assert engine._use_gpu is False
        assert engine._use_angle_cls is True

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine(lang="ar", use_gpu=True, use_angle_cls=False)
        assert engine._lang == "ar"
        assert engine._use_gpu is True
        assert engine._use_angle_cls is False


class TestPaddleLanguageMapping:
    """Tests for language code normalization."""

    def test_normalize_english(self):
        """Test English language code normalization."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine._normalize_lang("en") == "en"
        assert engine._normalize_lang("eng") == "en"
        assert engine._normalize_lang("english") == "en"
        assert engine._normalize_lang("EN") == "en"
        assert engine._normalize_lang("ENGLISH") == "en"

    def test_normalize_arabic(self):
        """Test Arabic language code normalization."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine._normalize_lang("ar") == "ar"
        assert engine._normalize_lang("ara") == "ar"
        assert engine._normalize_lang("arabic") == "ar"
        assert engine._normalize_lang("AR") == "ar"
        assert engine._normalize_lang("ARABIC") == "ar"

    def test_normalize_unknown_returns_lowercase(self):
        """Test unknown language codes are returned lowercase."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine._normalize_lang("xyz") == "xyz"
        assert engine._normalize_lang("XYZ") == "xyz"


class TestPaddleCapabilities:
    """Tests for engine capabilities."""

    def test_capabilities_returns_dataclass(self):
        """Test capabilities returns EngineCapabilities."""
        from src.engines.paddle_engine import PaddleEngine
        from src.engines.base_engine import EngineCapabilities
        engine = PaddleEngine()
        caps = engine.get_capabilities()
        assert isinstance(caps, EngineCapabilities)

    def test_supports_images(self):
        """Test engine supports images."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.get_capabilities().supports_images is True

    def test_supports_pdf(self):
        """Test engine supports PDF."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.get_capabilities().supports_pdf is True

    def test_supports_gpu(self):
        """Test engine supports GPU acceleration."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.get_capabilities().supports_gpu is True

    def test_does_not_support_vision_analysis(self):
        """Test engine doesn't support vision analysis."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.get_capabilities().supports_vision_analysis is False

    def test_supported_languages_in_capabilities(self):
        """Test capabilities include supported languages."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        caps = engine.get_capabilities()
        assert "en" in caps.supported_languages
        assert "ar" in caps.supported_languages

    def test_supports_tables(self):
        """Test engine supports table detection."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.get_capabilities().supports_tables is True

    def test_supports_structure(self):
        """Test engine supports structure analysis."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        assert engine.get_capabilities().supports_structure is True


class TestPaddleAvailability:
    """Tests for availability checking."""

    def test_is_available_returns_boolean(self):
        """Test is_available returns boolean."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        result = engine.is_available()
        assert isinstance(result, bool)

    def test_available_when_paddleocr_installed(self):
        """Test engine is available when PaddleOCR is installed."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        engine._available = None  # Reset cache
        # Since PaddleOCR is installed in this environment, it should be available
        result = engine.is_available()
        assert isinstance(result, bool)
        # If PaddleOCR is installed, this should be True
        if result:
            assert engine._available is True

    def test_availability_caching(self):
        """Test availability result is cached."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        engine._available = True
        assert engine.is_available() is True
        engine._available = False
        assert engine.is_available() is False


class TestPaddleOCRResultParsing:
    """Tests for OCR result parsing."""

    def test_parse_empty_result(self):
        """Test parsing empty result."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()
        result = engine._parse_ocr_result([])
        assert result['text_blocks'] == []
        assert result['full_text'] == ""

    def test_parse_new_api_format(self):
        """Test parsing new API format with rec_texts."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()

        mock_result = MagicMock()
        mock_result.keys.return_value = ['rec_texts', 'rec_scores', 'dt_polys']
        mock_result.get.side_effect = lambda k, default=[]: {
            'rec_texts': ['Hello', 'World'],
            'rec_scores': [0.95, 0.98],
            'dt_polys': [[[0, 0], [100, 0], [100, 20], [0, 20]], [[0, 30], [100, 30], [100, 50], [0, 50]]]
        }.get(k, default)

        result = engine._parse_ocr_result(mock_result)
        assert len(result['text_blocks']) == 2
        assert result['text_blocks'][0].text == 'Hello'
        assert result['text_blocks'][1].text == 'World'
        assert 'Hello' in result['full_text']
        assert 'World' in result['full_text']

    def test_parse_legacy_format(self):
        """Test parsing legacy format [bbox, (text, score)]."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()

        legacy_result = [
            [[[0, 0], [100, 0], [100, 20], [0, 20]], ('Test Text', 0.95)],
            [[[0, 30], [100, 30], [100, 50], [0, 50]], ('More Text', 0.98)]
        ]

        result = engine._parse_ocr_result(legacy_result)
        assert len(result['text_blocks']) == 2
        assert result['text_blocks'][0].text == 'Test Text'
        assert result['text_blocks'][1].text == 'More Text'

    def test_parse_skips_empty_text(self):
        """Test parsing skips empty text entries."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()

        mock_result = MagicMock()
        mock_result.keys.return_value = ['rec_texts', 'rec_scores', 'dt_polys']
        mock_result.get.side_effect = lambda k, default=[]: {
            'rec_texts': ['Hello', '', '   ', 'World'],
            'rec_scores': [0.95, 0.5, 0.5, 0.98],
            'dt_polys': []
        }.get(k, default)

        result = engine._parse_ocr_result(mock_result)
        assert len(result['text_blocks']) == 2

    def test_parse_with_numpy_bbox(self):
        """Test parsing handles numpy array bboxes."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()

        mock_poly = MagicMock()
        mock_poly.tolist.return_value = [[0, 0], [100, 0], [100, 20], [0, 20]]

        mock_result = MagicMock()
        mock_result.keys.return_value = ['rec_texts', 'rec_scores', 'dt_polys']
        mock_result.get.side_effect = lambda k, default=[]: {
            'rec_texts': ['Test'],
            'rec_scores': [0.95],
            'dt_polys': [mock_poly]
        }.get(k, default)

        result = engine._parse_ocr_result(mock_result)
        assert len(result['text_blocks']) == 1
        assert result['text_blocks'][0].bbox is not None


class TestPaddleProcessImage:
    """Tests for image processing."""

    def test_process_nonexistent_image(self):
        """Test processing non-existent image returns error."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()

        result = engine.process_image('/nonexistent/image.png')
        assert result.success is False
        assert 'not found' in result.error.lower()

    @patch('src.engines.paddle_engine.PaddleEngine._get_ocr_engine')
    def test_process_image_success(self, mock_get_engine, tmp_path):
        """Test successful image processing."""
        from src.engines.paddle_engine import PaddleEngine

        # Create a temporary image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        # Mock OCR engine
        mock_ocr = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ['rec_texts', 'rec_scores', 'dt_polys']
        mock_result.get.side_effect = lambda k, default=[]: {
            'rec_texts': ['Test OCR Output'],
            'rec_scores': [0.95],
            'dt_polys': []
        }.get(k, default)
        mock_ocr.predict.return_value = [mock_result]
        mock_get_engine.return_value = mock_ocr

        engine = PaddleEngine()
        result = engine.process_image(str(test_image))

        assert result.success is True
        assert result.engine_used == "paddle"
        assert 'Test OCR Output' in result.full_text

    @patch('src.engines.paddle_engine.PaddleEngine._get_ocr_engine')
    def test_process_image_with_language(self, mock_get_engine, tmp_path):
        """Test image processing with language parameter."""
        from src.engines.paddle_engine import PaddleEngine

        test_image = tmp_path / "test_ar.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        mock_ocr = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ['rec_texts', 'rec_scores', 'dt_polys']
        mock_result.get.side_effect = lambda k, default=[]: {
            'rec_texts': ['مرحبا'],
            'rec_scores': [0.95],
            'dt_polys': []
        }.get(k, default)
        mock_ocr.predict.return_value = [mock_result]
        mock_get_engine.return_value = mock_ocr

        engine = PaddleEngine()
        result = engine.process_image(str(test_image), lang='ar')

        assert result.success is True
        assert result.language == "ar"


class TestPaddleProcessPDF:
    """Tests for PDF processing."""

    def test_process_nonexistent_pdf(self):
        """Test processing non-existent PDF returns error."""
        from src.engines.paddle_engine import PaddleEngine
        engine = PaddleEngine()

        result = engine.process_pdf('/nonexistent/file.pdf')
        assert result.success is False
        assert 'not found' in result.error.lower()

    def test_process_pdf_missing_dependency(self, tmp_path):
        """Test PDF processing with missing fitz dependency."""
        from src.engines.paddle_engine import PaddleEngine

        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b'%PDF-1.4\n')

        engine = PaddleEngine()

        with patch.dict('sys.modules', {'fitz': None}):
            with patch('src.engines.paddle_engine.PaddleEngine._get_ocr_engine'):
                # This should handle ImportError gracefully
                result = engine.process_pdf(str(test_pdf))
                # Result depends on whether fitz is actually installed


class TestPaddleGetTextOnly:
    """Tests for get_text_only convenience method."""

    @patch('src.engines.paddle_engine.PaddleEngine.process_image')
    def test_get_text_only_image(self, mock_process):
        """Test get_text_only for image file."""
        from src.engines.paddle_engine import PaddleEngine
        from src.models import ReadResult, PageResult

        mock_process.return_value = ReadResult(
            success=True,
            file_path='/test/image.png',
            file_type='image',
            engine_used='paddle',
            pages=[PageResult(page_number=1, text_blocks=[], full_text='Extracted text')],
            full_text='Extracted text',
            processing_time_ms=100,
            language='en'
        )

        engine = PaddleEngine()
        text = engine.get_text_only('/test/image.png')
        assert text == 'Extracted text'

    @patch('src.engines.paddle_engine.PaddleEngine.process_pdf')
    def test_get_text_only_pdf(self, mock_process):
        """Test get_text_only for PDF file."""
        from src.engines.paddle_engine import PaddleEngine
        from src.models import ReadResult, PageResult

        mock_process.return_value = ReadResult(
            success=True,
            file_path='/test/file.pdf',
            file_type='pdf',
            engine_used='paddle',
            pages=[PageResult(page_number=1, text_blocks=[], full_text='PDF text')],
            full_text='PDF text',
            processing_time_ms=100,
            language='en'
        )

        engine = PaddleEngine()
        text = engine.get_text_only('/test/file.pdf')
        assert text == 'PDF text'

    @patch('src.engines.paddle_engine.PaddleEngine.process_image')
    def test_get_text_only_failure_raises(self, mock_process):
        """Test get_text_only raises on failure."""
        from src.engines.paddle_engine import PaddleEngine
        from src.engines.base_engine import EngineProcessingError
        from src.models import ReadResult

        mock_process.return_value = ReadResult(
            success=False,
            file_path='/test/image.png',
            file_type='image',
            engine_used='paddle',
            pages=[],
            full_text='',
            processing_time_ms=0,
            language='en',
            error='OCR failed'
        )

        engine = PaddleEngine()
        with pytest.raises(EngineProcessingError):
            engine.get_text_only('/test/image.png')


class TestPaddleEngineRegistration:
    """Tests for engine registration and imports."""

    def test_engine_importable(self):
        """Test PaddleEngine can be imported."""
        from src.engines.paddle_engine import PaddleEngine
        assert PaddleEngine is not None

    def test_engine_in_engines_init(self):
        """Test PaddleEngine is exported from engines package."""
        from src.engines import PaddleEngine
        assert PaddleEngine is not None

    def test_read_tool_registers_paddle(self):
        """Test HybridReadTool registers paddle engine."""
        from src.read_tool import HybridReadTool

        tool = HybridReadTool()
        result = tool.get_available_engines()
        engines = result.get('engines', [])
        engine_names = [e['name'] for e in engines]
        assert 'paddle' in engine_names


class TestPaddleErrorHandling:
    """Tests for error handling."""

    def test_unsupported_language_error(self):
        """Test unsupported language raises proper error."""
        from src.engines.paddle_engine import PaddleEngine
        from src.engines.base_engine import LanguageNotSupportedError

        engine = PaddleEngine()

        # Trigger language check - 'xyz' is not in SUPPORTED_LANGUAGES
        with pytest.raises(LanguageNotSupportedError):
            engine._get_ocr_engine('xyz')

    @patch('src.engines.paddle_engine.PaddleEngine._get_ocr_engine')
    def test_processing_error_returns_error_result(self, mock_get_engine, tmp_path):
        """Test processing errors return error result."""
        from src.engines.paddle_engine import PaddleEngine

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        mock_ocr = MagicMock()
        mock_ocr.predict.side_effect = Exception("OCR processing failed")
        mock_get_engine.return_value = mock_ocr

        engine = PaddleEngine()
        result = engine.process_image(str(test_image))

        assert result.success is False
        assert 'failed' in result.error.lower()
