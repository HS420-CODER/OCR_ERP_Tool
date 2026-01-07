"""
OCR and Vision Engine implementations.

Available engines:
- PaddleEngine: PaddleOCR-based OCR (primary)
- TesseractEngine: Tesseract OCR (fallback)
- OllamaEngine: Ollama Vision models (context-aware analysis) - Phase 3
- BilingualOCRPipeline: 6-stage bilingual pipeline (Phase 6)
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

# Phase 6: Bilingual OCR Pipeline
from .bilingual_ocr_pipeline import (
    OCRMode,
    DegradationLevel,
    LanguageRegion,
    CorrectionRecord,
    StageResult,
    BilingualOCRResult,
    PipelineConfig,
    BilingualOCRPipeline,
    create_pipeline,
    get_bilingual_pipeline,
)

__all__ = [
    # Base Engine
    "BaseEngine",
    "EngineCapabilities",
    "EngineError",
    "EngineNotAvailableError",
    "EngineProcessingError",
    "LanguageNotSupportedError",
    # OCR Engines
    "PaddleEngine",
    "TesseractEngine",
    "OllamaEngine",
    # Phase 6: Bilingual Pipeline
    "OCRMode",
    "DegradationLevel",
    "LanguageRegion",
    "CorrectionRecord",
    "StageResult",
    "BilingualOCRResult",
    "PipelineConfig",
    "BilingualOCRPipeline",
    "create_pipeline",
    "get_bilingual_pipeline",
]
