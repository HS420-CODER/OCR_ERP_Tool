"""
OCR and Vision Engine implementations.

Available engines:
- PaddleEngine: PaddleOCR-based OCR (primary)
- TesseractEngine: Tesseract OCR (fallback)
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
from .tesseract_engine import TesseractEngine
from .ollama_engine import OllamaEngine

__all__ = [
    "BaseEngine",
    "EngineCapabilities",
    "EngineError",
    "EngineNotAvailableError",
    "EngineProcessingError",
    "LanguageNotSupportedError",
    "PaddleEngine",
    "TesseractEngine",
    "OllamaEngine",
]
