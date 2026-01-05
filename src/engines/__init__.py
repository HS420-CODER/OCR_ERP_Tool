"""
OCR and Vision Engine implementations.

Available engines:
- PaddleEngine: PaddleOCR-based OCR (primary)
- TesseractEngine: Tesseract OCR (fallback) - Phase 2
- OllamaEngine: Ollama Vision models (context-aware analysis) - Phase 3
"""

from .base_engine import (
    BaseEngine,
    EngineCapabilities,
    EngineError,
    EngineNotAvailableError,
    EngineProcessingError,
    LanguageNotSupportedError
)
from .paddle_engine import PaddleEngine

__all__ = [
    "BaseEngine",
    "EngineCapabilities",
    "EngineError",
    "EngineNotAvailableError",
    "EngineProcessingError",
    "LanguageNotSupportedError",
    "PaddleEngine",
]
