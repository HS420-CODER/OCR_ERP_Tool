"""
Bilingual OCR Pipeline - Phase 6 Production Implementation.

A 6-stage pipeline for processing Arabic, English, and mixed-language documents.

Stages:
1. Initial OCR - Primary engine processing
2. Language Detection - Per-region language classification
3. Engine Selection - Language-optimal engine routing
4. Reprocessing - Confidence-based secondary OCR
5. Post-Processing - Beam correction and validation
6. Confidence Calculation - Bilingual scoring

Based on ARABIC_OCR_IMPLEMENTATION_PLAN.md v4.0

Usage:
    pipeline = BilingualOCRPipeline(mode=OCRMode.BILINGUAL)
    result = pipeline.process_image("invoice.png")
    print(result.full_text)
    print(result.overall_confidence)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class OCRMode(Enum):
    """OCR processing mode for document handling."""
    ARABIC_ONLY = "arabic_only"      # Optimized for pure Arabic documents
    ENGLISH_ONLY = "english_only"    # Optimized for pure English documents
    BILINGUAL = "bilingual"          # Mixed Arabic-English (default)
    AUTO_DETECT = "auto_detect"      # Automatic language detection and routing


class DegradationLevel(Enum):
    """Level of feature degradation when components are unavailable."""
    NONE = 0           # All components available
    MINOR = 1          # Some optional components missing
    MODERATE = 2       # Fallback engines being used
    SIGNIFICANT = 3    # Core features degraded
    CRITICAL = 4       # Basic OCR only


class PipelineStage(Enum):
    """Pipeline processing stages."""
    INITIAL_OCR = "stage1_initial_ocr"
    LANGUAGE_DETECTION = "stage2_language_detection"
    ENGINE_SELECTION = "stage3_engine_selection"
    REPROCESSING = "stage4_reprocessing"
    POST_PROCESSING = "stage5_post_processing"
    CONFIDENCE_CALC = "stage6_confidence_calculation"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LanguageRegion:
    """
    A region of text with detected language.

    Attributes:
        text: Extracted text content
        language: Detected language code ('ar', 'en', 'mixed')
        bbox: Optional bounding box coordinates
        confidence: OCR confidence for this region
        word_count: Number of words in region
        start_index: Position in full text
        end_index: End position in full text
    """
    text: str
    language: str
    confidence: float
    word_count: int = 0
    bbox: Optional[Dict[str, float]] = None
    start_index: int = 0
    end_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "confidence": self.confidence,
            "word_count": self.word_count,
            "bbox": self.bbox,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }


@dataclass
class CorrectionRecord:
    """Record of a text correction made during post-processing."""
    position: int
    original: str
    corrected: str
    correction_type: str  # 'beam', 'spell', 'ligature', 'number'
    confidence: float
    source_module: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position,
            "original": self.original,
            "corrected": self.corrected,
            "type": self.correction_type,
            "confidence": self.confidence,
            "source": self.source_module,
        }


@dataclass
class StageResult:
    """Result from a single pipeline stage."""
    stage: PipelineStage
    success: bool
    data: Any
    processing_time_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "success": self.success,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
        }


@dataclass
class BilingualOCRResult:
    """
    Complete result from the bilingual OCR pipeline.

    Attributes:
        success: Whether processing completed successfully
        full_text: Complete extracted text
        regions: Language-annotated text regions
        overall_confidence: Combined confidence score
        arabic_confidence: Confidence for Arabic portions
        english_confidence: Confidence for English portions
        primary_language: Dominant language detected
        is_bilingual: Whether document contains both languages
        corrections_made: Total corrections applied
        processing_time_ms: Total processing time
        stages_executed: List of stages that ran
        engines_used: OCR engines used
        degradation_level: Feature availability level
    """
    success: bool
    full_text: str
    regions: List[LanguageRegion] = field(default_factory=list)
    overall_confidence: float = 0.0
    arabic_confidence: float = 0.0
    english_confidence: float = 0.0
    primary_language: str = "unknown"
    is_bilingual: bool = False
    corrections_made: int = 0
    corrections: List[CorrectionRecord] = field(default_factory=list)
    processing_time_ms: float = 0.0
    stages_executed: List[str] = field(default_factory=list)
    engines_used: List[str] = field(default_factory=list)
    degradation_level: DegradationLevel = DegradationLevel.NONE
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """Total word count across all regions."""
        return sum(r.word_count for r in self.regions)

    @property
    def arabic_word_count(self) -> int:
        """Word count for Arabic regions."""
        return sum(r.word_count for r in self.regions if r.language == "ar")

    @property
    def english_word_count(self) -> int:
        """Word count for English regions."""
        return sum(r.word_count for r in self.regions if r.language == "en")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "full_text": self.full_text,
            "regions": [r.to_dict() for r in self.regions],
            "confidence": {
                "overall": self.overall_confidence,
                "arabic": self.arabic_confidence,
                "english": self.english_confidence,
            },
            "language": {
                "primary": self.primary_language,
                "is_bilingual": self.is_bilingual,
            },
            "corrections": {
                "count": self.corrections_made,
                "details": [c.to_dict() for c in self.corrections],
            },
            "processing": {
                "time_ms": self.processing_time_ms,
                "stages": self.stages_executed,
                "engines": self.engines_used,
                "degradation": self.degradation_level.name,
            },
            "word_counts": {
                "total": self.word_count,
                "arabic": self.arabic_word_count,
                "english": self.english_word_count,
            },
            "warnings": self.warnings,
            "errors": self.errors,
            "metadata": self.metadata,
        }


# =============================================================================
# Pipeline Configuration
# =============================================================================

@dataclass
class PipelineConfig:
    """Configuration for BilingualOCRPipeline."""

    # Processing mode
    mode: OCRMode = OCRMode.BILINGUAL

    # Stage toggles
    enable_reprocessing: bool = True
    enable_post_processing: bool = True
    enable_confidence_calc: bool = True

    # Confidence thresholds
    reprocess_threshold: float = 0.70
    high_confidence_threshold: float = 0.85
    vlm_trigger_threshold: float = 0.40

    # Engine preferences
    primary_arabic_engine: str = "paddle"
    primary_english_engine: str = "paddle"
    enable_vlm_fallback: bool = False

    # Post-processing options
    enable_beam_correction: bool = True
    beam_width: int = 5
    max_corrections_per_word: int = 3
    enable_english_validation: bool = True

    # Performance
    cache_engines: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "enable_reprocessing": self.enable_reprocessing,
            "enable_post_processing": self.enable_post_processing,
            "thresholds": {
                "reprocess": self.reprocess_threshold,
                "high_confidence": self.high_confidence_threshold,
                "vlm_trigger": self.vlm_trigger_threshold,
            },
            "beam_width": self.beam_width,
            "max_corrections": self.max_corrections_per_word,
        }


# =============================================================================
# Bilingual OCR Pipeline
# =============================================================================

class BilingualOCRPipeline:
    """
    6-Stage Bilingual OCR Pipeline for Arabic-English documents.

    Integrates all Phase 1-5 components for comprehensive bilingual OCR:
    - Phase 1-2: Arabic beam correction, N-gram, confusion matrix
    - Phase 3: Multi-engine fusion with IoU alignment
    - Phase 4: Word-level language detection
    - Phase 5: English validation, bilingual confidence scoring

    Stages:
        1. Initial OCR - Primary engine based on mode
        2. Language Detection - Per-region classification
        3. Engine Selection - Language-optimal routing
        4. Reprocessing - Secondary OCR for low confidence
        5. Post-Processing - Corrections and validation
        6. Confidence Calculation - Bilingual scoring

    Usage:
        pipeline = BilingualOCRPipeline(mode=OCRMode.BILINGUAL)
        result = pipeline.process_image("document.png")

        # Check results
        print(f"Text: {result.full_text}")
        print(f"Confidence: {result.overall_confidence}")
        print(f"Languages: {result.primary_language}")
    """

    # Default thresholds
    DEFAULT_REPROCESS_THRESHOLD = 0.70
    DEFAULT_HIGH_CONFIDENCE = 0.85
    DEFAULT_VLM_TRIGGER = 0.40

    def __init__(
        self,
        mode: OCRMode = OCRMode.BILINGUAL,
        config: Optional[PipelineConfig] = None,
        enable_reprocessing: bool = True,
        enable_post_processing: bool = True,
        cache_engines: bool = True
    ):
        """
        Initialize the bilingual OCR pipeline.

        Args:
            mode: Processing mode (ARABIC_ONLY, ENGLISH_ONLY, BILINGUAL, AUTO_DETECT)
            config: Optional PipelineConfig for fine-tuning
            enable_reprocessing: Enable Stage 4 reprocessing
            enable_post_processing: Enable Stage 5 corrections
            cache_engines: Cache engine instances for performance
        """
        self.mode = mode
        self.config = config or PipelineConfig(
            mode=mode,
            enable_reprocessing=enable_reprocessing,
            enable_post_processing=enable_post_processing,
            cache_engines=cache_engines
        )

        # Engine cache
        self._engine_cache: Dict[str, Any] = {}
        self._cache_engines = cache_engines

        # Lazy-loaded components
        self._paddle_engine = None
        self._tesseract_engine = None
        self._language_detector = None
        self._beam_corrector = None
        self._english_validator = None
        self._bilingual_scorer = None

        # Track degradation
        self._degradation_level = DegradationLevel.NONE
        self._unavailable_components: List[str] = []

        logger.info(f"BilingualOCRPipeline initialized with mode={mode.value}")

    # =========================================================================
    # Lazy Loading Properties
    # =========================================================================

    @property
    def paddle_engine(self):
        """Lazy load PaddleEngine."""
        if self._paddle_engine is None:
            try:
                from .paddle_engine import PaddleEngine
                self._paddle_engine = PaddleEngine()
                logger.debug("PaddleEngine loaded successfully")
            except Exception as e:
                logger.warning(f"PaddleEngine not available: {e}")
                self._unavailable_components.append("PaddleEngine")
        return self._paddle_engine

    @property
    def tesseract_engine(self):
        """Lazy load TesseractEngine."""
        if self._tesseract_engine is None:
            try:
                from .tesseract_engine import TesseractEngine
                self._tesseract_engine = TesseractEngine()
                logger.debug("TesseractEngine loaded successfully")
            except Exception as e:
                logger.warning(f"TesseractEngine not available: {e}")
                self._unavailable_components.append("TesseractEngine")
        return self._tesseract_engine

    @property
    def language_detector(self):
        """Lazy load WordLevelDetector."""
        if self._language_detector is None:
            try:
                from ..utils.word_level_detector import get_language_detector
                self._language_detector = get_language_detector()
                logger.debug("WordLevelDetector loaded successfully")
            except Exception as e:
                logger.warning(f"WordLevelDetector not available: {e}")
                self._unavailable_components.append("WordLevelDetector")
        return self._language_detector

    @property
    def beam_corrector(self):
        """Lazy load ArabicBeamCorrector."""
        if self._beam_corrector is None:
            try:
                from ..ml.arabic_beam_corrector import create_beam_corrector
                # Map beam_width to preset
                preset = "balanced"
                if self.config.beam_width <= 3:
                    preset = "fast"
                elif self.config.beam_width >= 7:
                    preset = "accurate" if self.config.beam_width < 10 else "maximum"
                self._beam_corrector = create_beam_corrector(preset=preset)
                logger.debug("ArabicBeamCorrector loaded successfully")
            except Exception as e:
                logger.warning(f"ArabicBeamCorrector not available: {e}")
                self._unavailable_components.append("ArabicBeamCorrector")
        return self._beam_corrector

    @property
    def english_validator(self):
        """Lazy load EnglishOCRValidator."""
        if self._english_validator is None:
            try:
                from ..validators.english_validator import get_english_validator
                self._english_validator = get_english_validator()
                logger.debug("EnglishOCRValidator loaded successfully")
            except Exception as e:
                logger.warning(f"EnglishOCRValidator not available: {e}")
                self._unavailable_components.append("EnglishOCRValidator")
        return self._english_validator

    @property
    def bilingual_scorer(self):
        """Lazy load BilingualConfidenceScorer."""
        if self._bilingual_scorer is None:
            try:
                from ..validators.confidence_scorer import get_bilingual_scorer
                self._bilingual_scorer = get_bilingual_scorer()
                logger.debug("BilingualConfidenceScorer loaded successfully")
            except Exception as e:
                logger.warning(f"BilingualConfidenceScorer not available: {e}")
                self._unavailable_components.append("BilingualConfidenceScorer")
        return self._bilingual_scorer

    # =========================================================================
    # Public API
    # =========================================================================

    def process_image(
        self,
        image_path: str,
        language_hint: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> BilingualOCRResult:
        """
        Process an image through the 6-stage pipeline.

        Args:
            image_path: Path to image file
            language_hint: Optional language hint ('ar', 'en', 'mixed')
            options: Additional processing options
                - skip_stages: List[str] - stages to skip
                - force_reprocess: bool - always reprocess
                - debug: bool - include debug info in result

        Returns:
            BilingualOCRResult with full extraction results
        """
        start_time = time.time()
        options = options or {}

        # Validate input
        if not Path(image_path).exists():
            return BilingualOCRResult(
                success=False,
                full_text="",
                errors=[f"File not found: {image_path}"]
            )

        # Initialize result
        result = BilingualOCRResult(
            success=True,
            full_text="",
            metadata={"file": image_path, "mode": self.mode.value}
        )

        try:
            # Execute pipeline stages
            self._execute_pipeline(image_path, "image", language_hint, options, result)

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            result.success = False
            result.errors.append(f"Pipeline error: {str(e)}")

        # Finalize
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.degradation_level = self._calculate_degradation()

        return result

    def process_pdf(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None,
        language_hint: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> BilingualOCRResult:
        """
        Process a PDF through the 6-stage pipeline.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process (None for all)
            language_hint: Optional language hint
            options: Additional processing options

        Returns:
            BilingualOCRResult with full extraction results
        """
        start_time = time.time()
        options = options or {}
        options["max_pages"] = max_pages

        # Validate input
        if not Path(pdf_path).exists():
            return BilingualOCRResult(
                success=False,
                full_text="",
                errors=[f"File not found: {pdf_path}"]
            )

        # Initialize result
        result = BilingualOCRResult(
            success=True,
            full_text="",
            metadata={"file": pdf_path, "mode": self.mode.value, "max_pages": max_pages}
        )

        try:
            # Execute pipeline stages
            self._execute_pipeline(pdf_path, "pdf", language_hint, options, result)

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            result.success = False
            result.errors.append(f"Pipeline error: {str(e)}")

        # Finalize
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.degradation_level = self._calculate_degradation()

        return result

    # =========================================================================
    # Pipeline Execution
    # =========================================================================

    def _execute_pipeline(
        self,
        file_path: str,
        file_type: str,
        language_hint: Optional[str],
        options: Dict[str, Any],
        result: BilingualOCRResult
    ) -> None:
        """Execute all pipeline stages."""
        skip_stages = options.get("skip_stages", [])

        # Stage 1: Initial OCR
        if PipelineStage.INITIAL_OCR.value not in skip_stages:
            stage1_result = self._stage1_initial_ocr(file_path, file_type, language_hint)
            result.stage_results[PipelineStage.INITIAL_OCR.value] = stage1_result
            result.stages_executed.append(PipelineStage.INITIAL_OCR.value)

            if not stage1_result.success:
                result.warnings.append(f"Stage 1 failed: {stage1_result.error}")
                return

            blocks = stage1_result.data.get("blocks", [])
            result.full_text = stage1_result.data.get("text", "")
            result.engines_used.append(stage1_result.data.get("engine", "unknown"))

        # Stage 2: Language Detection
        if PipelineStage.LANGUAGE_DETECTION.value not in skip_stages:
            stage2_result = self._stage2_language_detection(blocks)
            result.stage_results[PipelineStage.LANGUAGE_DETECTION.value] = stage2_result
            result.stages_executed.append(PipelineStage.LANGUAGE_DETECTION.value)

            if stage2_result.success:
                result.regions = stage2_result.data.get("regions", [])
                result.primary_language = stage2_result.data.get("primary_language", "unknown")
                result.is_bilingual = stage2_result.data.get("is_bilingual", False)

        # Stage 3: Engine Selection
        if PipelineStage.ENGINE_SELECTION.value not in skip_stages:
            stage3_result = self._stage3_engine_selection(result.regions)
            result.stage_results[PipelineStage.ENGINE_SELECTION.value] = stage3_result
            result.stages_executed.append(PipelineStage.ENGINE_SELECTION.value)

        # Stage 4: Reprocessing (if enabled and needed)
        avg_confidence = sum(r.confidence for r in result.regions) / len(result.regions) if result.regions else 0
        if (
            self.config.enable_reprocessing and
            PipelineStage.REPROCESSING.value not in skip_stages and
            avg_confidence < self.config.high_confidence_threshold
        ):
            stage4_result = self._stage4_reprocessing(
                file_path, file_type, result.regions,
                stage3_result.data if stage3_result else {}
            )
            result.stage_results[PipelineStage.REPROCESSING.value] = stage4_result
            result.stages_executed.append(PipelineStage.REPROCESSING.value)

            if stage4_result.success and stage4_result.data.get("improved"):
                # Update regions with reprocessed data
                result.regions = stage4_result.data.get("regions", result.regions)
                result.full_text = stage4_result.data.get("text", result.full_text)
                if stage4_result.data.get("engine"):
                    result.engines_used.append(stage4_result.data["engine"])

        # Stage 5: Post-Processing
        if (
            self.config.enable_post_processing and
            PipelineStage.POST_PROCESSING.value not in skip_stages
        ):
            stage5_result = self._stage5_post_processing(result.regions)
            result.stage_results[PipelineStage.POST_PROCESSING.value] = stage5_result
            result.stages_executed.append(PipelineStage.POST_PROCESSING.value)

            if stage5_result.success:
                result.corrections = stage5_result.data.get("corrections", [])
                result.corrections_made = len(result.corrections)
                result.full_text = stage5_result.data.get("text", result.full_text)
                result.regions = stage5_result.data.get("regions", result.regions)

        # Stage 6: Confidence Calculation
        if (
            self.config.enable_confidence_calc and
            PipelineStage.CONFIDENCE_CALC.value not in skip_stages
        ):
            stage6_result = self._stage6_confidence_calculation(result)
            result.stage_results[PipelineStage.CONFIDENCE_CALC.value] = stage6_result
            result.stages_executed.append(PipelineStage.CONFIDENCE_CALC.value)

            if stage6_result.success:
                result.overall_confidence = stage6_result.data.get("overall", 0.0)
                result.arabic_confidence = stage6_result.data.get("arabic", 0.0)
                result.english_confidence = stage6_result.data.get("english", 0.0)

    # =========================================================================
    # Stage 1: Initial OCR
    # =========================================================================

    def _stage1_initial_ocr(
        self,
        file_path: str,
        file_type: str,
        language_hint: Optional[str]
    ) -> StageResult:
        """
        Stage 1: Initial OCR processing.

        Selects primary engine based on mode and executes OCR.
        """
        start_time = time.time()

        try:
            # Determine language for OCR
            lang = self._get_ocr_language(language_hint)

            # Get primary engine
            engine = self.paddle_engine
            if engine is None:
                engine = self.tesseract_engine
                if engine is None:
                    return StageResult(
                        stage=PipelineStage.INITIAL_OCR,
                        success=False,
                        data={},
                        processing_time_ms=(time.time() - start_time) * 1000,
                        error="No OCR engine available"
                    )

            # Execute OCR
            if file_type == "pdf":
                ocr_result = engine.process_pdf(file_path, lang=lang)
            else:
                ocr_result = engine.process_image(file_path, lang=lang)

            # Extract blocks and text
            blocks = []
            full_text = ""

            if hasattr(ocr_result, 'pages'):
                for page in ocr_result.pages:
                    if hasattr(page, 'text_blocks'):
                        for block in page.text_blocks:
                            blocks.append({
                                "text": block.text if hasattr(block, 'text') else str(block),
                                "confidence": block.confidence if hasattr(block, 'confidence') else 0.85,
                                "bbox": block.bbox if hasattr(block, 'bbox') else None,
                            })
                    if hasattr(page, 'full_text'):
                        full_text += page.full_text + "\n"

            if not full_text and hasattr(ocr_result, 'full_text'):
                full_text = ocr_result.full_text

            return StageResult(
                stage=PipelineStage.INITIAL_OCR,
                success=True,
                data={
                    "blocks": blocks,
                    "text": full_text.strip(),
                    "engine": engine.__class__.__name__,
                    "language": lang,
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.exception(f"Stage 1 error: {e}")
            return StageResult(
                stage=PipelineStage.INITIAL_OCR,
                success=False,
                data={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    def _get_ocr_language(self, language_hint: Optional[str]) -> str:
        """Determine OCR language based on mode and hint."""
        if language_hint:
            return language_hint

        if self.mode == OCRMode.ARABIC_ONLY:
            return "ar"
        elif self.mode == OCRMode.ENGLISH_ONLY:
            return "en"
        else:
            return "ar"  # Default to Arabic for bilingual

    # =========================================================================
    # Stage 2: Language Detection
    # =========================================================================

    def _stage2_language_detection(
        self,
        blocks: List[Dict[str, Any]]
    ) -> StageResult:
        """
        Stage 2: Detect language for each text region.

        Uses WordLevelDetector to classify each block.
        """
        start_time = time.time()

        try:
            regions: List[LanguageRegion] = []
            current_pos = 0

            for block in blocks:
                text = block.get("text", "")
                confidence = block.get("confidence", 0.85)
                bbox = block.get("bbox")

                if not text.strip():
                    continue

                # Detect language
                if self.language_detector:
                    detection = self.language_detector.detect_line(text)
                    language = detection.primary_language.value
                    word_count = detection.word_count
                else:
                    # Fallback: Simple Unicode-based detection
                    language, word_count = self._fallback_language_detection(text)

                region = LanguageRegion(
                    text=text,
                    language=language,
                    confidence=confidence,
                    word_count=word_count,
                    bbox=bbox,
                    start_index=current_pos,
                    end_index=current_pos + len(text),
                )
                regions.append(region)
                current_pos += len(text) + 1  # +1 for separator

            # Determine primary language and bilingual status
            arabic_count = sum(r.word_count for r in regions if r.language == "ar")
            english_count = sum(r.word_count for r in regions if r.language == "en")
            total_count = arabic_count + english_count

            if total_count == 0:
                primary_language = "unknown"
                is_bilingual = False
            elif arabic_count > english_count * 2:
                primary_language = "ar"
                is_bilingual = english_count > 0
            elif english_count > arabic_count * 2:
                primary_language = "en"
                is_bilingual = arabic_count > 0
            else:
                primary_language = "mixed"
                is_bilingual = True

            return StageResult(
                stage=PipelineStage.LANGUAGE_DETECTION,
                success=True,
                data={
                    "regions": regions,
                    "primary_language": primary_language,
                    "is_bilingual": is_bilingual,
                    "arabic_words": arabic_count,
                    "english_words": english_count,
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.exception(f"Stage 2 error: {e}")
            return StageResult(
                stage=PipelineStage.LANGUAGE_DETECTION,
                success=False,
                data={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    def _fallback_language_detection(self, text: str) -> Tuple[str, int]:
        """Fallback language detection using Unicode ranges."""
        words = text.split()
        arabic_count = 0
        english_count = 0

        for word in words:
            ar_chars = sum(1 for c in word if '\u0600' <= c <= '\u06FF')
            en_chars = sum(1 for c in word if c.isascii() and c.isalpha())

            if ar_chars > en_chars:
                arabic_count += 1
            elif en_chars > ar_chars:
                english_count += 1

        total = arabic_count + english_count
        if total == 0:
            return "unknown", len(words)
        elif arabic_count > english_count:
            return "ar", len(words)
        else:
            return "en", len(words)

    # =========================================================================
    # Stage 3: Engine Selection
    # =========================================================================

    def _stage3_engine_selection(
        self,
        regions: List[LanguageRegion]
    ) -> StageResult:
        """
        Stage 3: Select optimal OCR engine for each region.

        Routes to specialized engines based on detected language.
        """
        start_time = time.time()

        try:
            engine_assignments: Dict[int, Dict[str, str]] = {}

            for i, region in enumerate(regions):
                primary_engine = "paddle"
                secondary_engine = None

                if region.language == "ar":
                    primary_engine = "paddle"
                    secondary_engine = "tesseract"
                elif region.language == "en":
                    primary_engine = "paddle"
                    secondary_engine = "tesseract"
                else:  # mixed
                    primary_engine = "paddle"
                    secondary_engine = "tesseract"

                engine_assignments[i] = {
                    "primary": primary_engine,
                    "secondary": secondary_engine,
                    "language": region.language,
                }

            return StageResult(
                stage=PipelineStage.ENGINE_SELECTION,
                success=True,
                data={
                    "assignments": engine_assignments,
                    "region_count": len(regions),
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.exception(f"Stage 3 error: {e}")
            return StageResult(
                stage=PipelineStage.ENGINE_SELECTION,
                success=False,
                data={},
                processing_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    # =========================================================================
    # Stage 4: Reprocessing
    # =========================================================================

    def _stage4_reprocessing(
        self,
        file_path: str,
        file_type: str,
        regions: List[LanguageRegion],
        engine_assignments: Dict[str, Any]
    ) -> StageResult:
        """
        Stage 4: Reprocess low-confidence regions with secondary engines.

        Uses IoU alignment and character-level voting for fusion.
        """
        start_time = time.time()

        try:
            improved = False
            updated_regions = list(regions)

            # Find regions needing reprocessing
            for i, region in enumerate(regions):
                if region.confidence < self.config.reprocess_threshold:
                    # Try secondary engine
                    secondary_result = self._run_secondary_engine(
                        file_path, file_type, region
                    )

                    if secondary_result and secondary_result.get("confidence", 0) > region.confidence:
                        # Update region with better result
                        updated_regions[i] = LanguageRegion(
                            text=secondary_result.get("text", region.text),
                            language=region.language,
                            confidence=secondary_result.get("confidence", region.confidence),
                            word_count=len(secondary_result.get("text", "").split()),
                            bbox=region.bbox,
                            start_index=region.start_index,
                            end_index=region.end_index,
                        )
                        improved = True

            # Rebuild full text
            full_text = " ".join(r.text for r in updated_regions)

            return StageResult(
                stage=PipelineStage.REPROCESSING,
                success=True,
                data={
                    "improved": improved,
                    "regions": updated_regions,
                    "text": full_text,
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.exception(f"Stage 4 error: {e}")
            return StageResult(
                stage=PipelineStage.REPROCESSING,
                success=False,
                data={"improved": False},
                processing_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    def _run_secondary_engine(
        self,
        file_path: str,
        file_type: str,
        region: LanguageRegion
    ) -> Optional[Dict[str, Any]]:
        """Run secondary engine on a specific region."""
        try:
            engine = self.tesseract_engine
            if engine is None:
                return None

            lang = "ara" if region.language == "ar" else "eng"

            if file_type == "pdf":
                result = engine.process_pdf(file_path, lang=lang)
            else:
                result = engine.process_image(file_path, lang=lang)

            if hasattr(result, 'full_text'):
                return {
                    "text": result.full_text,
                    "confidence": 0.75,  # Default for Tesseract
                }

            return None

        except Exception as e:
            logger.warning(f"Secondary engine error: {e}")
            return None

    # =========================================================================
    # Stage 5: Post-Processing
    # =========================================================================

    def _stage5_post_processing(
        self,
        regions: List[LanguageRegion]
    ) -> StageResult:
        """
        Stage 5: Apply language-specific corrections.

        Arabic: Beam correction, spell check
        English: Ligature detection, validation
        """
        start_time = time.time()

        try:
            corrections: List[CorrectionRecord] = []
            updated_regions: List[LanguageRegion] = []

            for region in regions:
                corrected_text = region.text
                region_corrections = []

                if region.language == "ar" and self.beam_corrector:
                    # Apply Arabic beam correction
                    corrected_text, ar_corrections = self._apply_arabic_corrections(
                        region.text
                    )
                    region_corrections.extend(ar_corrections)

                elif region.language == "en" and self.english_validator:
                    # Apply English validation
                    corrected_text, en_corrections = self._apply_english_corrections(
                        region.text
                    )
                    region_corrections.extend(en_corrections)

                elif region.language == "mixed":
                    # Process mixed content by segments
                    corrected_text, mixed_corrections = self._apply_mixed_corrections(
                        region.text
                    )
                    region_corrections.extend(mixed_corrections)

                # Create updated region
                updated_region = LanguageRegion(
                    text=corrected_text,
                    language=region.language,
                    confidence=region.confidence,
                    word_count=len(corrected_text.split()),
                    bbox=region.bbox,
                    start_index=region.start_index,
                    end_index=region.end_index,
                )
                updated_regions.append(updated_region)
                corrections.extend(region_corrections)

            # Rebuild full text
            full_text = " ".join(r.text for r in updated_regions)

            return StageResult(
                stage=PipelineStage.POST_PROCESSING,
                success=True,
                data={
                    "text": full_text,
                    "regions": updated_regions,
                    "corrections": corrections,
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.exception(f"Stage 5 error: {e}")
            return StageResult(
                stage=PipelineStage.POST_PROCESSING,
                success=False,
                data={"corrections": []},
                processing_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    def _apply_arabic_corrections(
        self,
        text: str
    ) -> Tuple[str, List[CorrectionRecord]]:
        """Apply Arabic beam correction."""
        corrections = []
        words = text.split()
        corrected_words = []

        for i, word in enumerate(words):
            if len(word) < 2:
                corrected_words.append(word)
                continue

            try:
                result = self.beam_corrector.correct(word)
                if result.was_corrected:
                    corrected_words.append(result.corrected)
                    corrections.append(CorrectionRecord(
                        position=i,
                        original=word,
                        corrected=result.corrected,
                        correction_type="beam",
                        confidence=result.confidence,
                        source_module="ArabicBeamCorrector",
                    ))
                else:
                    corrected_words.append(word)
            except Exception:
                corrected_words.append(word)

        return " ".join(corrected_words), corrections

    def _apply_english_corrections(
        self,
        text: str
    ) -> Tuple[str, List[CorrectionRecord]]:
        """Apply English validation and correction."""
        corrections = []

        try:
            result = self.english_validator.validate(text)
            if result.was_corrected:
                for pos, old, new in result.corrections:
                    corrections.append(CorrectionRecord(
                        position=pos,
                        original=old,
                        corrected=new,
                        correction_type="ligature",
                        confidence=result.confidence,
                        source_module="EnglishOCRValidator",
                    ))
                return result.corrected, corrections
        except Exception:
            pass

        return text, corrections

    def _apply_mixed_corrections(
        self,
        text: str
    ) -> Tuple[str, List[CorrectionRecord]]:
        """Apply corrections to mixed-language text."""
        corrections = []

        if self.language_detector:
            segments = self.language_detector.get_language_segments(text)
            corrected_parts = []

            for segment_text, lang in segments:
                if lang.value == "ar" and self.beam_corrector:
                    corrected, _ = self._apply_arabic_corrections(segment_text)
                    corrected_parts.append(corrected)
                elif lang.value == "en" and self.english_validator:
                    corrected, _ = self._apply_english_corrections(segment_text)
                    corrected_parts.append(corrected)
                else:
                    corrected_parts.append(segment_text)

            return " ".join(corrected_parts), corrections

        return text, corrections

    # =========================================================================
    # Stage 6: Confidence Calculation
    # =========================================================================

    def _stage6_confidence_calculation(
        self,
        result: BilingualOCRResult
    ) -> StageResult:
        """
        Stage 6: Calculate comprehensive confidence scores.

        Uses BilingualConfidenceScorer for language-aware scoring.
        """
        start_time = time.time()

        try:
            overall_confidence = 0.0
            arabic_confidence = 0.0
            english_confidence = 0.0

            if self.bilingual_scorer:
                # Score full text
                score_result = self.bilingual_scorer.score(
                    result.full_text,
                    engine_confidence=0.85
                )
                overall_confidence = score_result.score

                # Score by language
                arabic_texts = [r.text for r in result.regions if r.language == "ar"]
                english_texts = [r.text for r in result.regions if r.language == "en"]

                if arabic_texts:
                    ar_score = self.bilingual_scorer.score(
                        " ".join(arabic_texts),
                        language_hint="ar"
                    )
                    arabic_confidence = ar_score.score

                if english_texts:
                    en_score = self.bilingual_scorer.score(
                        " ".join(english_texts),
                        language_hint="en"
                    )
                    english_confidence = en_score.score

            else:
                # Fallback: Use average region confidence
                if result.regions:
                    overall_confidence = sum(r.confidence for r in result.regions) / len(result.regions)
                    arabic_confidence = sum(r.confidence for r in result.regions if r.language == "ar") / max(1, len([r for r in result.regions if r.language == "ar"]))
                    english_confidence = sum(r.confidence for r in result.regions if r.language == "en") / max(1, len([r for r in result.regions if r.language == "en"]))

            return StageResult(
                stage=PipelineStage.CONFIDENCE_CALC,
                success=True,
                data={
                    "overall": overall_confidence,
                    "arabic": arabic_confidence,
                    "english": english_confidence,
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.exception(f"Stage 6 error: {e}")
            return StageResult(
                stage=PipelineStage.CONFIDENCE_CALC,
                success=False,
                data={"overall": 0.0, "arabic": 0.0, "english": 0.0},
                processing_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _calculate_degradation(self) -> DegradationLevel:
        """Calculate current degradation level based on available components."""
        if not self._unavailable_components:
            return DegradationLevel.NONE

        critical = ["PaddleEngine"]
        important = ["WordLevelDetector", "ArabicBeamCorrector", "EnglishOCRValidator"]
        optional = ["BilingualConfidenceScorer", "TesseractEngine"]

        critical_missing = any(c in self._unavailable_components for c in critical)
        important_missing = sum(1 for c in important if c in self._unavailable_components)
        optional_missing = sum(1 for c in optional if c in self._unavailable_components)

        if critical_missing:
            return DegradationLevel.CRITICAL
        elif important_missing >= 2:
            return DegradationLevel.SIGNIFICANT
        elif important_missing >= 1:
            return DegradationLevel.MODERATE
        elif optional_missing > 0:
            return DegradationLevel.MINOR
        else:
            return DegradationLevel.NONE

    def get_available_engines(self) -> Dict[str, bool]:
        """Get availability status of all engines."""
        return {
            "PaddleEngine": self.paddle_engine is not None,
            "TesseractEngine": self.tesseract_engine is not None,
        }

    def get_available_components(self) -> Dict[str, bool]:
        """Get availability status of all components."""
        return {
            "PaddleEngine": self.paddle_engine is not None,
            "TesseractEngine": self.tesseract_engine is not None,
            "WordLevelDetector": self.language_detector is not None,
            "ArabicBeamCorrector": self.beam_corrector is not None,
            "EnglishOCRValidator": self.english_validator is not None,
            "BilingualConfidenceScorer": self.bilingual_scorer is not None,
        }

    def set_mode(self, mode: OCRMode) -> None:
        """Change processing mode."""
        self.mode = mode
        self.config.mode = mode
        logger.info(f"Pipeline mode changed to {mode.value}")


# =============================================================================
# Factory Functions
# =============================================================================

def create_pipeline(
    mode: str = "bilingual",
    **kwargs
) -> BilingualOCRPipeline:
    """
    Factory function to create a BilingualOCRPipeline.

    Args:
        mode: Processing mode ('arabic', 'english', 'bilingual', 'auto')
        **kwargs: Additional pipeline configuration

    Returns:
        Configured BilingualOCRPipeline instance
    """
    # Handle both string and OCRMode inputs
    if isinstance(mode, OCRMode):
        ocr_mode = mode
    else:
        mode_map = {
            "arabic": OCRMode.ARABIC_ONLY,
            "ar": OCRMode.ARABIC_ONLY,
            "english": OCRMode.ENGLISH_ONLY,
            "en": OCRMode.ENGLISH_ONLY,
            "bilingual": OCRMode.BILINGUAL,
            "mixed": OCRMode.BILINGUAL,
            "auto": OCRMode.AUTO_DETECT,
        }
        ocr_mode = mode_map.get(str(mode).lower(), OCRMode.BILINGUAL)

    return BilingualOCRPipeline(mode=ocr_mode, **kwargs)


# Singleton instance
_pipeline_instance: Optional[BilingualOCRPipeline] = None


def get_bilingual_pipeline(
    mode: OCRMode = OCRMode.BILINGUAL
) -> BilingualOCRPipeline:
    """
    Get singleton instance of BilingualOCRPipeline.

    Args:
        mode: Processing mode

    Returns:
        BilingualOCRPipeline instance
    """
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = BilingualOCRPipeline(mode=mode)
    return _pipeline_instance
