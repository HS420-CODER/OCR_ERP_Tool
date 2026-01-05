"""
Configuration management for Hybrid Read Tool.

Provides:
- ReadToolConfig: Main configuration dataclass
- Environment variable loading
- Default settings
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class ReadToolConfig:
    """
    Configuration for the Hybrid Read Tool.

    Can be initialized from environment variables or directly.

    Attributes:
        default_engine: Default OCR engine ("auto", "paddle", "tesseract", "ollama")
        fallback_enabled: Enable automatic fallback on engine failure
        fallback_order: Order of engines to try on fallback

        paddle_lang: Default PaddleOCR language
        paddle_use_gpu: Enable GPU for PaddleOCR
        paddle_use_angle_cls: Enable text angle classification
        paddle_ocr_version: PaddleOCR model version

        tesseract_lang: Default Tesseract language
        tesseract_path: Custom path to Tesseract executable
        tesseract_config: Additional Tesseract configuration

        ollama_host: Ollama server URL
        ollama_model: Default Ollama vision model
        ollama_timeout: Request timeout in seconds

        max_file_size_mb: Maximum file size in MB
        max_image_dimension: Maximum image dimension in pixels
        pdf_dpi: PDF rendering DPI
        temp_dir: Temporary files directory

        include_confidence: Include confidence scores by default
        include_bounding_boxes: Include bounding boxes by default
        output_format: Default output format
        structured_output: Enable structured bilingual output
    """

    # Engine selection
    default_engine: str = "paddle"
    fallback_enabled: bool = True
    fallback_order: List[str] = field(default_factory=lambda: ["paddle", "tesseract"])

    # PaddleOCR settings
    paddle_lang: str = "en"
    paddle_use_gpu: bool = False
    paddle_use_angle_cls: bool = True
    paddle_ocr_version: str = "PP-OCRv5"

    # Tesseract settings
    tesseract_lang: str = "eng"
    tesseract_path: Optional[str] = None
    tesseract_config: str = ""

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llava"
    ollama_timeout: int = 120

    # Processing settings
    max_file_size_mb: int = 50
    max_image_dimension: int = 4096
    pdf_dpi: int = 200
    temp_dir: Optional[str] = None

    # Output settings
    include_confidence: bool = True
    include_bounding_boxes: bool = True
    output_format: str = "json"
    structured_output: bool = True  # Enable Claude Code-like output

    # Debug settings
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ReadToolConfig":
        """
        Create configuration from environment variables.

        Environment variables (all optional):
            READ_TOOL_DEFAULT_ENGINE
            READ_TOOL_FALLBACK_ENABLED
            READ_TOOL_FALLBACK_ORDER (comma-separated)
            PADDLE_OCR_LANG
            PADDLE_OCR_USE_GPU
            PADDLE_OCR_USE_ANGLE_CLS
            PADDLE_OCR_VERSION
            TESSERACT_CMD
            TESSERACT_LANG
            TESSERACT_CONFIG
            OLLAMA_HOST
            OLLAMA_MODEL
            OLLAMA_TIMEOUT
            MAX_FILE_SIZE_MB
            MAX_IMAGE_DIMENSION
            PDF_DPI
            TEMP_DIR
            READ_TOOL_DEBUG
            READ_TOOL_LOG_LEVEL
        """
        def get_bool(key: str, default: bool) -> bool:
            val = os.environ.get(key, "").lower()
            if val in ("true", "1", "yes"):
                return True
            elif val in ("false", "0", "no"):
                return False
            return default

        def get_int(key: str, default: int) -> int:
            val = os.environ.get(key)
            if val:
                try:
                    return int(val)
                except ValueError:
                    pass
            return default

        def get_list(key: str, default: List[str]) -> List[str]:
            val = os.environ.get(key)
            if val:
                return [x.strip() for x in val.split(",") if x.strip()]
            return default

        return cls(
            default_engine=os.environ.get("READ_TOOL_DEFAULT_ENGINE", "paddle"),
            fallback_enabled=get_bool("READ_TOOL_FALLBACK_ENABLED", True),
            fallback_order=get_list("READ_TOOL_FALLBACK_ORDER", ["paddle", "tesseract"]),

            paddle_lang=os.environ.get("PADDLE_OCR_LANG", "en"),
            paddle_use_gpu=get_bool("PADDLE_OCR_USE_GPU", False),
            paddle_use_angle_cls=get_bool("PADDLE_OCR_USE_ANGLE_CLS", True),
            paddle_ocr_version=os.environ.get("PADDLE_OCR_VERSION", "PP-OCRv5"),

            tesseract_lang=os.environ.get("TESSERACT_LANG", "eng"),
            tesseract_path=os.environ.get("TESSERACT_CMD"),
            tesseract_config=os.environ.get("TESSERACT_CONFIG", ""),

            ollama_host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "llava"),
            ollama_timeout=get_int("OLLAMA_TIMEOUT", 120),

            max_file_size_mb=get_int("MAX_FILE_SIZE_MB", 50),
            max_image_dimension=get_int("MAX_IMAGE_DIMENSION", 4096),
            pdf_dpi=get_int("PDF_DPI", 200),
            temp_dir=os.environ.get("TEMP_DIR"),

            debug=get_bool("READ_TOOL_DEBUG", False),
            log_level=os.environ.get("READ_TOOL_LOG_LEVEL", "INFO"),
        )

    def get_temp_dir(self) -> Path:
        """Get temporary directory path, creating if needed."""
        if self.temp_dir:
            path = Path(self.temp_dir)
        else:
            path = Path.cwd() / "temp"
        path.mkdir(parents=True, exist_ok=True)
        return path


# Language mapping for different engines
LANGUAGE_MAPPING = {
    # display_name: (paddle_code, tesseract_code, description)
    "english": ("en", "eng", "English"),
    "arabic": ("ar", "ara", "Arabic (العربية)"),
}

# Shorthand aliases
LANGUAGE_ALIASES = {
    "en": "english",
    "eng": "english",
    "ar": "arabic",
    "ara": "arabic",
}

# Default language
DEFAULT_LANGUAGE = "english"


def get_paddle_lang(lang: str) -> str:
    """Convert language code to PaddleOCR format."""
    lang_lower = lang.lower()
    # Check aliases first
    if lang_lower in LANGUAGE_ALIASES:
        lang_name = LANGUAGE_ALIASES[lang_lower]
        return LANGUAGE_MAPPING[lang_name][0]
    # Check if it's a full language name
    if lang_lower in LANGUAGE_MAPPING:
        return LANGUAGE_MAPPING[lang_lower][0]
    return lang


def get_tesseract_lang(lang: str) -> str:
    """Convert language code to Tesseract format."""
    lang_lower = lang.lower()
    # Check aliases first
    if lang_lower in LANGUAGE_ALIASES:
        lang_name = LANGUAGE_ALIASES[lang_lower]
        return LANGUAGE_MAPPING[lang_name][1]
    # Check if it's a full language name
    if lang_lower in LANGUAGE_MAPPING:
        return LANGUAGE_MAPPING[lang_lower][1]
    # Map common codes
    if lang_lower == "en":
        return "eng"
    if lang_lower == "ar":
        return "ara"
    return lang
