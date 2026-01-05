"""
Extended tests for EngineManager.

Additional tests for better coverage of edge cases and error handling.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine_manager import EngineManager
from src.engines.base_engine import (
    BaseEngine,
    EngineCapabilities,
    EngineNotAvailableError,
    LanguageNotSupportedError
)
from src.config import ReadToolConfig
from src.models import ReadResult


class MockEngine(BaseEngine):
    """Mock engine for testing."""

    name = "mock"
    display_name = "Mock Engine"
    _available = True
    _supported_languages = ["en", "ar"]

    @classmethod
    def is_available(cls) -> bool:
        return cls._available

    def supports_language(self, lang: str) -> bool:
        return lang in self._supported_languages

    def get_capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            supports_images=True,
            supports_pdf=True,
            supports_vision_analysis=False,
            supports_gpu=False,
            supported_languages=self._supported_languages,
            max_file_size_mb=50,
            supports_tables=False,
            supports_structure=False
        )

    def process_image(self, image_path, lang="en", options=None):
        return ReadResult(
            success=True,
            file_path=image_path,
            file_type="image",
            full_text="Mock OCR text",
            engine_used="mock"
        )

    def process_pdf(self, pdf_path, lang="en", options=None, **kwargs):
        return ReadResult(
            success=True,
            file_path=pdf_path,
            file_type="pdf",
            full_text="Mock PDF text",
            engine_used="mock"
        )


class MockFailingEngine(MockEngine):
    """Mock engine that always fails."""

    name = "failing"
    display_name = "Failing Engine"

    def process_image(self, image_path, lang="en", options=None):
        return ReadResult(
            success=False,
            file_path=image_path,
            file_type="image",
            error="Mock processing failure"
        )

    def process_pdf(self, pdf_path, lang="en", options=None, **kwargs):
        return ReadResult(
            success=False,
            file_path=pdf_path,
            file_type="pdf",
            error="Mock PDF failure"
        )


class MockExceptionEngine(MockEngine):
    """Mock engine that throws exceptions."""

    name = "exception"
    display_name = "Exception Engine"

    def process_image(self, image_path, lang="en", options=None):
        raise RuntimeError("Mock exception during processing")


class TestEngineManagerRegistration:
    """Tests for engine registration."""

    def test_register_engine_class(self):
        """Test registering an engine class."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)

        assert "mock" in manager._engine_classes
        assert manager._engine_classes["mock"] == MockEngine

    def test_register_multiple_engines(self):
        """Test registering multiple engine classes."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)
        manager.register_engine_class("failing", MockFailingEngine)

        assert len(manager._engine_classes) == 2
        assert "mock" in manager._engine_classes
        assert "failing" in manager._engine_classes


class TestEngineManagerGetEngine:
    """Tests for getting engine instances."""

    @pytest.fixture
    def manager(self):
        """Create manager with mock engine."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)
        return manager

    def test_get_engine_creates_instance(self, manager):
        """Test that get_engine creates instance on first call."""
        engine = manager.get_engine("mock")

        assert engine is not None
        assert isinstance(engine, MockEngine)
        assert "mock" in manager._engines

    def test_get_engine_returns_same_instance(self, manager):
        """Test that get_engine returns cached instance."""
        engine1 = manager.get_engine("mock")
        engine2 = manager.get_engine("mock")

        assert engine1 is engine2

    def test_get_unregistered_engine_raises(self, manager):
        """Test that getting unregistered engine raises error."""
        with pytest.raises(EngineNotAvailableError) as exc_info:
            manager.get_engine("nonexistent")

        assert "not registered" in str(exc_info.value)
        assert exc_info.value.code == "ENGINE_NOT_REGISTERED"


class TestEngineManagerAvailability:
    """Tests for engine availability checking."""

    @pytest.fixture
    def manager(self):
        """Create manager with mock engine."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)
        MockEngine._available = True
        return manager

    def test_is_available_true(self, manager):
        """Test availability for available engine."""
        assert manager.is_available("mock") == True

    def test_is_available_false_for_unregistered(self, manager):
        """Test availability for unregistered engine."""
        assert manager.is_available("nonexistent") == False

    def test_is_available_caches_result(self, manager):
        """Test that availability is cached."""
        manager.is_available("mock")
        assert "mock" in manager._availability_cache

    def test_clear_availability_cache(self, manager):
        """Test clearing availability cache."""
        manager.is_available("mock")
        assert "mock" in manager._availability_cache

        manager.clear_availability_cache()
        assert "mock" not in manager._availability_cache

    def test_get_available_engines(self, manager):
        """Test getting list of available engines."""
        manager.register_engine_class("failing", MockFailingEngine)
        MockFailingEngine._available = True

        available = manager.get_available_engines()
        assert "mock" in available

    def test_is_available_with_unavailable_engine(self, manager):
        """Test availability for unavailable engine."""
        MockEngine._available = False
        result = manager.is_available("mock")
        # Reset for other tests
        MockEngine._available = True
        assert result == False


class TestEngineManagerInfo:
    """Tests for engine information."""

    @pytest.fixture
    def manager(self):
        """Create manager with mock engine."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)
        MockEngine._available = True
        return manager

    def test_get_engine_info(self, manager):
        """Test getting engine information."""
        info = manager.get_engine_info("mock")

        assert info["name"] == "mock"
        assert info["display_name"] == "Mock Engine"
        assert info["available"] == True
        assert "capabilities" in info

    def test_get_engine_info_capabilities(self, manager):
        """Test engine info includes capabilities."""
        info = manager.get_engine_info("mock")
        caps = info["capabilities"]

        assert caps["supports_images"] == True
        assert caps["supports_pdf"] == True
        assert "en" in caps["supported_languages"]

    def test_get_engine_info_unavailable(self, manager):
        """Test engine info for unavailable engine."""
        info = manager.get_engine_info("nonexistent")

        assert info["name"] == "nonexistent"
        assert info["available"] == False
        assert info["capabilities"] == {}

    def test_get_all_engines_info(self, manager):
        """Test getting all engines info."""
        manager.register_engine_class("failing", MockFailingEngine)

        all_info = manager.get_all_engines_info()
        assert len(all_info) == 2


class TestEngineManagerSelection:
    """Tests for engine selection."""

    @pytest.fixture
    def manager(self):
        """Create manager with engines."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)
        manager.register_engine_class("failing", MockFailingEngine)
        MockEngine._available = True
        MockFailingEngine._available = True
        manager.config.fallback_order = ["mock", "failing"]
        return manager

    def test_select_engine_default(self, manager):
        """Test default engine selection."""
        selected = manager.select_engine("image", "ocr", "en")
        assert selected == "mock"

    def test_select_engine_with_preference(self, manager):
        """Test engine selection with user preference."""
        selected = manager.select_engine(
            "image", "ocr", "en",
            user_preference="mock"
        )
        assert selected == "mock"

    def test_select_engine_auto_preference(self, manager):
        """Test engine selection with auto preference."""
        selected = manager.select_engine(
            "image", "ocr", "en",
            user_preference="auto"
        )
        assert selected == "mock"

    def test_select_engine_unavailable_preference_fallback(self, manager):
        """Test fallback when preferred engine unavailable."""
        selected = manager.select_engine(
            "image", "ocr", "en",
            user_preference="nonexistent"
        )
        assert selected == "mock"

    def test_select_engine_no_language_support(self, manager):
        """Test engine selection with unsupported language."""
        MockEngine._supported_languages = ["en"]
        MockFailingEngine._supported_languages = ["ar"]

        selected = manager.select_engine("image", "ocr", "ar")
        assert selected == "failing"

        # Reset
        MockEngine._supported_languages = ["en", "ar"]

    def test_select_engine_vision_requires_ollama(self, manager):
        """Test that vision analysis requires Ollama."""
        with pytest.raises(EngineNotAvailableError) as exc_info:
            manager.select_engine("image", "vision", "en")

        assert "Ollama is required" in str(exc_info.value)

    def test_select_engine_no_suitable_engine(self, manager):
        """Test error when no suitable engine available."""
        MockEngine._supported_languages = ["fr"]
        MockFailingEngine._supported_languages = ["de"]

        with pytest.raises(EngineNotAvailableError) as exc_info:
            manager.select_engine("image", "ocr", "en")

        assert "No OCR engine available" in str(exc_info.value)

        # Reset
        MockEngine._supported_languages = ["en", "ar"]


class TestEngineManagerFallback:
    """Tests for processing with fallback."""

    @pytest.fixture
    def manager(self):
        """Create manager with mock engines."""
        manager = EngineManager()
        manager.register_engine_class("mock", MockEngine)
        manager.register_engine_class("failing", MockFailingEngine)
        manager.register_engine_class("exception", MockExceptionEngine)
        MockEngine._available = True
        MockFailingEngine._available = True
        MockExceptionEngine._available = True
        manager.config.fallback_order = ["failing", "exception", "mock"]
        manager.config.fallback_enabled = True
        return manager

    def test_process_with_fallback_first_success(self, manager):
        """Test processing succeeds on first engine."""
        manager.config.fallback_order = ["mock", "failing"]

        result = manager.process_with_fallback(
            "test.png", "image", "en"
        )

        assert result.success == True
        assert result.full_text == "Mock OCR text"

    def test_process_with_fallback_uses_fallback(self, manager):
        """Test fallback when first engine fails."""
        result = manager.process_with_fallback(
            "test.png", "image", "en"
        )

        assert result.success == True
        assert result.engine_used == "mock"

    def test_process_with_fallback_pdf(self, manager):
        """Test PDF processing with fallback."""
        manager.config.fallback_order = ["mock"]

        result = manager.process_with_fallback(
            "test.pdf", "pdf", "en"
        )

        assert result.success == True
        assert result.full_text == "Mock PDF text"

    def test_process_with_fallback_user_preference(self, manager):
        """Test fallback with user preference."""
        result = manager.process_with_fallback(
            "test.png", "image", "en",
            user_preference="mock"
        )

        assert result.success == True
        assert result.engine_used == "mock"

    def test_process_with_fallback_all_fail(self, manager):
        """Test error when all engines fail."""
        manager.config.fallback_order = ["failing"]
        MockEngine._available = False

        with pytest.raises(EngineNotAvailableError) as exc_info:
            manager.process_with_fallback(
                "test.png", "image", "en"
            )

        assert "All OCR engines failed" in str(exc_info.value)

        # Reset
        MockEngine._available = True

    def test_process_with_fallback_disabled(self, manager):
        """Test that fallback can be disabled."""
        manager.config.fallback_order = ["exception", "mock"]
        manager.config.fallback_enabled = False

        with pytest.raises(RuntimeError):
            manager.process_with_fallback(
                "test.png", "image", "en"
            )

    def test_process_with_fallback_skips_unavailable(self, manager):
        """Test that unavailable engines are skipped."""
        MockEngine._available = False
        manager.config.fallback_order = ["mock", "failing"]

        # Should skip mock and try failing (which fails)
        with pytest.raises(EngineNotAvailableError):
            manager.process_with_fallback(
                "test.png", "image", "en"
            )

        # Reset
        MockEngine._available = True

    def test_process_with_fallback_skips_wrong_language(self, manager):
        """Test that engines not supporting language are skipped."""
        MockFailingEngine._supported_languages = ["en"]
        MockEngine._supported_languages = ["ar"]
        manager.config.fallback_order = ["failing", "mock"]

        result = manager.process_with_fallback(
            "test.png", "image", "ar"
        )

        assert result.success == True
        assert result.engine_used == "mock"

        # Reset
        MockEngine._supported_languages = ["en", "ar"]
        MockFailingEngine._supported_languages = ["en", "ar"]


class TestEngineManagerConfig:
    """Tests for manager configuration."""

    def test_default_config(self):
        """Test manager uses default config."""
        manager = EngineManager()
        assert manager.config is not None
        assert manager.config.fallback_enabled == True

    def test_custom_config(self):
        """Test manager uses custom config."""
        config = ReadToolConfig()
        config.fallback_enabled = False
        config.fallback_order = ["tesseract", "paddle"]

        manager = EngineManager(config)
        assert manager.config.fallback_enabled == False
        assert manager.config.fallback_order == ["tesseract", "paddle"]
