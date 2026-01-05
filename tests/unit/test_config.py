"""
Unit tests for configuration.
"""

import pytest
import os
from src.config import (
    ReadToolConfig,
    LANGUAGE_MAPPING,
    get_paddle_lang,
    get_tesseract_lang
)


class TestReadToolConfig:
    """Tests for ReadToolConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ReadToolConfig()

        assert config.default_engine == "paddle"
        assert config.fallback_enabled == True
        assert config.fallback_order == ["paddle", "tesseract"]
        assert config.paddle_lang == "en"
        assert config.paddle_use_gpu == False
        assert config.ollama_host == "http://localhost:11434"
        assert config.max_file_size_mb == 50

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ReadToolConfig(
            default_engine="tesseract",
            fallback_enabled=False,
            paddle_use_gpu=True,
            max_file_size_mb=100
        )

        assert config.default_engine == "tesseract"
        assert config.fallback_enabled == False
        assert config.paddle_use_gpu == True
        assert config.max_file_size_mb == 100

    def test_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("READ_TOOL_DEFAULT_ENGINE", "tesseract")
        monkeypatch.setenv("PADDLE_OCR_USE_GPU", "true")
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "75")
        monkeypatch.setenv("READ_TOOL_DEBUG", "true")

        config = ReadToolConfig.from_env()

        assert config.default_engine == "tesseract"
        assert config.paddle_use_gpu == True
        assert config.max_file_size_mb == 75
        assert config.debug == True

    def test_from_env_with_invalid_int(self, monkeypatch):
        """Test that invalid int values fall back to defaults."""
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "not_a_number")

        config = ReadToolConfig.from_env()

        assert config.max_file_size_mb == 50  # Default value

    def test_get_temp_dir(self, tmp_path):
        """Test temp directory creation."""
        config = ReadToolConfig(temp_dir=str(tmp_path / "test_temp"))
        temp_dir = config.get_temp_dir()

        assert temp_dir.exists()
        assert temp_dir.is_dir()


class TestLanguageMapping:
    """Tests for language code mapping."""

    def test_language_mapping_exists(self):
        """Test that language mapping is defined."""
        assert "english" in LANGUAGE_MAPPING
        assert "arabic" in LANGUAGE_MAPPING

    def test_get_paddle_lang_english(self):
        """Test English language code conversion for PaddleOCR."""
        assert get_paddle_lang("en") == "en"
        assert get_paddle_lang("eng") == "en"
        assert get_paddle_lang("english") == "en"
        assert get_paddle_lang("EN") == "en"  # Case insensitive

    def test_get_paddle_lang_arabic(self):
        """Test Arabic language code conversion for PaddleOCR."""
        assert get_paddle_lang("ar") == "ar"
        assert get_paddle_lang("ara") == "ar"
        assert get_paddle_lang("arabic") == "ar"

    def test_get_tesseract_lang_english(self):
        """Test English language code conversion for Tesseract."""
        assert get_tesseract_lang("en") == "eng"
        assert get_tesseract_lang("eng") == "eng"
        assert get_tesseract_lang("english") == "eng"

    def test_get_tesseract_lang_arabic(self):
        """Test Arabic language code conversion for Tesseract."""
        assert get_tesseract_lang("ar") == "ara"
        assert get_tesseract_lang("ara") == "ara"
        assert get_tesseract_lang("arabic") == "ara"

    def test_get_paddle_lang_unknown(self):
        """Test unknown language code returns as-is."""
        assert get_paddle_lang("xyz") == "xyz"
