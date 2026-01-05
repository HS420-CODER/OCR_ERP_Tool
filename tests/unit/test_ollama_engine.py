"""
Unit tests for OllamaEngine (Phase 6).

These tests verify:
1. Engine registration and availability checks
2. Ollama API communication (mocked)
3. Image and PDF processing
4. Custom prompt handling
5. Error handling for server unavailability
6. Timeout handling
"""

import pytest
import sys
import os
import base64
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestOllamaEngineBasics:
    """Tests for basic engine properties."""

    def test_engine_name(self):
        """Test engine name property."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.name == "ollama"

    def test_display_name(self):
        """Test display name property."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.display_name == "Ollama Vision"

    def test_supported_languages(self):
        """Test supported languages list."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert "en" in engine.SUPPORTED_LANGUAGES
        assert "ar" in engine.SUPPORTED_LANGUAGES

    def test_supports_language_english(self):
        """Test language support check for English."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.supports_language("en") == True

    def test_supports_language_arabic(self):
        """Test language support check for Arabic."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.supports_language("ar") == True

    def test_does_not_support_unknown_language(self):
        """Test unsupported language returns False."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.supports_language("xyz") == False


class TestOllamaCapabilities:
    """Tests for engine capabilities."""

    def test_capabilities_returns_dataclass(self):
        """Test capabilities returns EngineCapabilities."""
        from src.engines.ollama_engine import OllamaEngine
        from src.engines.base_engine import EngineCapabilities
        engine = OllamaEngine()
        caps = engine.get_capabilities()
        assert isinstance(caps, EngineCapabilities)

    def test_supports_images(self):
        """Test image support capability."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        caps = engine.get_capabilities()
        assert caps.supports_images == True

    def test_supports_pdf(self):
        """Test PDF support capability."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        caps = engine.get_capabilities()
        assert caps.supports_pdf == True

    def test_supports_vision_analysis(self):
        """Test vision analysis capability - KEY DIFFERENCE from other engines."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        caps = engine.get_capabilities()
        assert caps.supports_vision_analysis == True

    def test_supported_languages_in_capabilities(self):
        """Test languages in capabilities."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        caps = engine.get_capabilities()
        assert "en" in caps.supported_languages
        assert "ar" in caps.supported_languages


class TestOllamaConfiguration:
    """Tests for configuration handling."""

    def test_default_configuration(self):
        """Test default configuration values."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine._host == "http://localhost:11434"
        assert engine._model == "llava"
        assert engine._timeout == 120

    def test_custom_configuration_via_parameters(self):
        """Test custom configuration via constructor parameters."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine(
            host="http://custom:11434",
            model="bakllava",
            timeout=60
        )
        assert engine._host == "http://custom:11434"
        assert engine._model == "bakllava"
        assert engine._timeout == 60

    def test_configuration_from_readtoolconfig(self):
        """Test configuration from ReadToolConfig."""
        from src.engines.ollama_engine import OllamaEngine

        # Create mock config
        config = Mock()
        config.ollama_host = "http://test:11434"
        config.ollama_model = "llava-llama3"
        config.ollama_timeout = 180

        engine = OllamaEngine(config=config)

        assert engine._host == "http://test:11434"
        assert engine._model == "llava-llama3"
        assert engine._timeout == 180


class TestOllamaAvailability:
    """Tests for availability checking."""

    def test_is_available_returns_boolean(self):
        """Test that is_available returns boolean."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        result = engine.is_available()
        assert isinstance(result, bool)

    @patch('httpx.get')
    def test_server_available_with_models(self, mock_get):
        """Test availability when server responds with models."""
        from src.engines.ollama_engine import OllamaEngine

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llava:latest'},
                {'name': 'bakllava:latest'}
            ]
        }
        mock_get.return_value = mock_response

        engine = OllamaEngine()
        engine._available = None  # Reset cache

        assert engine.is_available() == True
        assert 'llava' in engine._available_models

    @patch('httpx.get')
    def test_server_unavailable_connection_error(self, mock_get):
        """Test availability when server is down."""
        from src.engines.ollama_engine import OllamaEngine
        import httpx

        mock_get.side_effect = httpx.ConnectError("Connection refused")

        engine = OllamaEngine()
        engine._available = None  # Reset cache

        assert engine.is_available() == False

    @patch('httpx.get')
    def test_server_returns_error_status(self, mock_get):
        """Test availability when server returns error status."""
        from src.engines.ollama_engine import OllamaEngine

        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        engine = OllamaEngine()
        engine._available = None

        assert engine.is_available() == False

    def test_availability_caching(self):
        """Test that availability result is cached."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        engine._available = True  # Set cached value

        # Should return cached value without making request
        assert engine.is_available() == True


class TestOllamaImageEncoding:
    """Tests for image encoding."""

    def test_encode_image_returns_string(self):
        """Test that _encode_image returns a string."""
        from src.engines.ollama_engine import OllamaEngine

        # Create a minimal test file
        test_file = FIXTURES_DIR / "test_encode.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"test content")

        try:
            engine = OllamaEngine()
            encoded = engine._encode_image(str(test_file))

            assert isinstance(encoded, str)
            # Verify it's valid base64
            decoded = base64.b64decode(encoded)
            assert decoded == b"test content"
        finally:
            test_file.unlink(missing_ok=True)

    def test_encode_image_with_fixture(self):
        """Test encoding with actual test image if available."""
        from src.engines.ollama_engine import OllamaEngine

        test_image = FIXTURES_DIR / "test_image.png"
        if not test_image.exists():
            pytest.skip("Test image fixture not available")

        engine = OllamaEngine()
        encoded = engine._encode_image(str(test_image))

        assert isinstance(encoded, str)
        assert len(encoded) > 0


class TestOllamaPrompts:
    """Tests for prompt handling."""

    def test_default_english_prompt_exists(self):
        """Test that English OCR prompt exists."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.DEFAULT_OCR_PROMPT
        assert "Extract" in engine.DEFAULT_OCR_PROMPT

    def test_default_arabic_prompt_exists(self):
        """Test that Arabic OCR prompt exists and includes both languages."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.DEFAULT_ARABIC_OCR_PROMPT
        assert "Arabic" in engine.DEFAULT_ARABIC_OCR_PROMPT

    def test_invoice_analysis_prompt_exists(self):
        """Test that invoice analysis prompt exists."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        assert engine.INVOICE_ANALYSIS_PROMPT
        assert "invoice" in engine.INVOICE_ANALYSIS_PROMPT.lower()


class TestOllamaProcessImage:
    """Tests for image processing."""

    def test_process_nonexistent_image(self):
        """Test error handling for missing file."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        engine._available = True

        result = engine.process_image("/nonexistent/image.png", "en")

        assert result.success == False
        assert "not found" in result.error.lower()

    def test_process_image_server_unavailable(self):
        """Test error when server is unavailable."""
        from src.engines.ollama_engine import OllamaEngine

        # Create a temporary test file so we pass the file check
        test_file = FIXTURES_DIR / "test_unavailable.png"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"fake png data")

        try:
            engine = OllamaEngine()
            engine._available = False

            result = engine.process_image(str(test_file), "en")

            assert result.success == False
            assert "not available" in result.error.lower()
        finally:
            test_file.unlink(missing_ok=True)

    @patch.object(__import__('src.engines.ollama_engine', fromlist=['OllamaEngine']).OllamaEngine, '_generate_with_image')
    @patch.object(__import__('src.engines.ollama_engine', fromlist=['OllamaEngine']).OllamaEngine, '_encode_image')
    def test_process_image_success(self, mock_encode, mock_generate):
        """Test successful image processing with mocked API."""
        from src.engines.ollama_engine import OllamaEngine

        mock_encode.return_value = "base64data"
        mock_generate.return_value = "Extracted text from the image"

        # Create a temporary test file
        test_file = FIXTURES_DIR / "test_process.png"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"fake png data")

        try:
            engine = OllamaEngine()
            engine._available = True

            result = engine.process_image(str(test_file), "en")

            assert result.success == True
            assert "Extracted text" in result.full_text
            assert result.engine_used == "ollama"
        finally:
            test_file.unlink(missing_ok=True)


class TestOllamaProcessWithPrompt:
    """Tests for custom prompt processing."""

    @patch.object(__import__('src.engines.ollama_engine', fromlist=['OllamaEngine']).OllamaEngine, 'process_image')
    def test_process_with_prompt_calls_process_image(self, mock_process):
        """Test that process_with_prompt calls process_image for images."""
        from src.engines.ollama_engine import OllamaEngine
        from src.models import ReadResult

        mock_process.return_value = ReadResult(
            success=True,
            file_path="/test.png",
            file_type="image",
            full_text="Custom result",
            engine_used="ollama"
        )

        engine = OllamaEngine()
        result = engine.process_with_prompt("/test.png", "Custom prompt")

        mock_process.assert_called_once()
        # Verify prompt was passed in options
        call_args = mock_process.call_args
        assert call_args[1]['options']['prompt'] == "Custom prompt"

    @patch.object(__import__('src.engines.ollama_engine', fromlist=['OllamaEngine']).OllamaEngine, 'process_pdf')
    def test_process_with_prompt_calls_process_pdf(self, mock_process):
        """Test that process_with_prompt calls process_pdf for PDFs."""
        from src.engines.ollama_engine import OllamaEngine
        from src.models import ReadResult

        mock_process.return_value = ReadResult(
            success=True,
            file_path="/test.pdf",
            file_type="pdf",
            full_text="PDF result",
            engine_used="ollama"
        )

        engine = OllamaEngine()
        result = engine.process_with_prompt("/test.pdf", "Analyze this PDF")

        mock_process.assert_called_once()


class TestOllamaAPIInteraction:
    """Tests for Ollama API request/response handling."""

    @patch('httpx.post')
    def test_generate_api_request_format(self, mock_post):
        """Test that API request has correct format."""
        from src.engines.ollama_engine import OllamaEngine

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Generated text'}
        mock_post.return_value = mock_response

        engine = OllamaEngine()
        result = engine._generate_with_image(
            prompt="Test prompt",
            image_base64="base64imagedata"
        )

        # Verify request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Verify endpoint
        assert "/api/generate" in call_args[0][0]

        # Verify payload structure
        payload = call_args[1]['json']
        assert payload['model'] == 'llava'
        assert payload['prompt'] == 'Test prompt'
        assert payload['images'] == ['base64imagedata']
        assert payload['stream'] == False

    @patch('httpx.post')
    def test_generate_returns_response_text(self, mock_post):
        """Test that generate returns the response text."""
        from src.engines.ollama_engine import OllamaEngine

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Hello World'}
        mock_post.return_value = mock_response

        engine = OllamaEngine()
        result = engine._generate_with_image("prompt", "image")

        assert result == "Hello World"

    @patch('httpx.post')
    def test_timeout_handling(self, mock_post):
        """Test timeout error handling."""
        from src.engines.ollama_engine import OllamaEngine
        from src.engines.base_engine import EngineProcessingError
        import httpx

        mock_post.side_effect = httpx.TimeoutException("Timeout")

        engine = OllamaEngine()

        with pytest.raises(EngineProcessingError) as exc_info:
            engine._generate_with_image("prompt", "image")

        assert "timed out" in str(exc_info.value).lower()

    @patch('httpx.post')
    def test_connection_error_handling(self, mock_post):
        """Test connection error handling."""
        from src.engines.ollama_engine import OllamaEngine
        from src.engines.base_engine import EngineNotAvailableError
        import httpx

        mock_post.side_effect = httpx.ConnectError("Connection refused")

        engine = OllamaEngine()

        with pytest.raises(EngineNotAvailableError) as exc_info:
            engine._generate_with_image("prompt", "image")

        assert "Cannot connect" in str(exc_info.value)

    @patch('httpx.post')
    def test_api_error_status_handling(self, mock_post):
        """Test API error status handling."""
        from src.engines.ollama_engine import OllamaEngine
        from src.engines.base_engine import EngineProcessingError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        engine = OllamaEngine()

        with pytest.raises(EngineProcessingError) as exc_info:
            engine._generate_with_image("prompt", "image")

        assert "500" in str(exc_info.value)


class TestOllamaEngineRegistration:
    """Tests for engine registration in the system."""

    def test_engine_importable(self):
        """Test that OllamaEngine can be imported."""
        from src.engines.ollama_engine import OllamaEngine
        assert OllamaEngine is not None

    def test_engine_in_engines_init(self):
        """Test that OllamaEngine is exported from engines package."""
        from src.engines import OllamaEngine
        assert OllamaEngine is not None

    def test_read_tool_registers_ollama(self):
        """Test that HybridReadTool registers OllamaEngine."""
        from src.read_tool import HybridReadTool

        reader = HybridReadTool()
        engine_classes = reader.engine_manager._engine_classes

        assert "ollama" in engine_classes


class TestOllamaAvailableModels:
    """Tests for model listing."""

    def test_get_available_models_initially_empty(self):
        """Test that available models is empty before check."""
        from src.engines.ollama_engine import OllamaEngine
        engine = OllamaEngine()
        engine._available_models = []
        engine._available = None

        # Without calling is_available, models should trigger check
        # but with mocked/unavailable server, will be empty
        models = engine.get_available_models()
        assert isinstance(models, list)

    @patch('httpx.get')
    def test_get_available_models_after_check(self, mock_get):
        """Test that models are populated after availability check."""
        from src.engines.ollama_engine import OllamaEngine

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llava:latest'},
                {'name': 'bakllava:7b'}
            ]
        }
        mock_get.return_value = mock_response

        engine = OllamaEngine()
        engine._available = None
        engine._available_models = []

        engine.is_available()
        models = engine.get_available_models()

        assert 'llava' in models
        assert 'bakllava' in models
