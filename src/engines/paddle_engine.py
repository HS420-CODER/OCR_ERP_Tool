"""
PaddleOCR Engine implementation.

Provides OCR functionality using PaddleOCR (PP-OCRv5).
Supports English and Arabic text extraction from images and PDFs.

Key Features for Arabic:
- PP-OCRv5 server model for highest accuracy
- RTL text line reconstruction
- Image preprocessing (contrast, deskew)
- Confidence filtering for cleaner output
- Optimized detection parameters

Stage 1 Enhancements (2026-01-06):
- DocumentTypeDetector integration for adaptive OCR parameters
- ArabicImagePreprocessor for intelligent image quality enhancement
- Multi-pass OCR with confidence-based retry for improved accuracy

Stage 2 Enhancements (2026-01-07):
- ArabicWordSeparator for intelligent merged word separation
- ArabicSpellChecker for context-aware OCR error correction
- ArabicNumberNormalizer for number/currency normalization

Stage 3 Enhancements (2026-01-07):
- TableRecognitionEngine for table structure detection and line item extraction
- LayoutAnalysisEngine for document zone detection (header, footer, tables, QR codes)
- ArabicReadingOrderAnalyzer for intelligent RTL reading order with multi-column support

Stage 4 Enhancements (2026-01-07):
- BilingualMarkdownFormatter for professional Claude Code-style output
- JSON schema with InvoiceDocument dataclass for structured data
- ERP-compatible and ZATCA-compatible export formats

Stage 5 Enhancements (2026-01-07):
- InvoiceValidator for cross-field validation (line items, totals, tax)
- ConfidenceScorer for document-level and field-level confidence scoring
- Quality assurance with actionable recommendations

Stage 6 Enhancements (2026-01-07):
- MLArabicEnhancer for ML-based OCR error correction with rule fallback
- TemplateLearner for invoice template learning and pattern recognition
- Continuous improvement through learned templates
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Disable model source check for offline operation
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from .base_engine import (
    BaseEngine,
    EngineCapabilities,
    EngineNotAvailableError,
    EngineProcessingError,
    LanguageNotSupportedError
)
from ..models import ReadResult, PageResult, TextBlock

logger = logging.getLogger(__name__)


@dataclass
class OCRPassResult:
    """Result from a single OCR pass."""
    text_blocks: List[Dict]
    avg_confidence: float
    pass_name: str
    params_used: Dict[str, Any]


class PaddleEngine(BaseEngine):
    """
    PaddleOCR-based OCR engine with optimized Arabic support.

    Features:
    - PP-OCRv5 with server-side detection for highest accuracy
    - English and Arabic language support
    - RTL text reconstruction for Arabic
    - Image preprocessing for better recognition
    - Confidence-based filtering
    - PDF processing via PyMuPDF
    - GPU acceleration support

    This is the primary OCR engine for the Hybrid Read Tool.
    """

    # Supported languages
    SUPPORTED_LANGUAGES = ["en", "ar"]

    # Language code mapping
    LANG_MAP = {
        "en": "en",
        "eng": "en",
        "english": "en",
        "ar": "ar",
        "ara": "ar",
        "arabic": "ar",
    }

    # Arabic-specific OCR parameters for better accuracy
    # Optimized based on Context7 PP-OCRv5 best practices
    # Note: Higher resolution helps Arabic but 1920 can cause memory issues
    ARABIC_OCR_PARAMS = {
        "text_det_limit_side_len": 1280,   # Balanced resolution for Arabic
        "text_rec_score_thresh": 0.25,     # Lower threshold to catch more characters
    }

    # English OCR parameters
    ENGLISH_OCR_PARAMS = {
        "text_det_limit_side_len": 960,
        "text_rec_score_thresh": 0.5,
    }

    # Multi-pass OCR configurations for Arabic
    # Each pass uses different parameters to maximize text capture
    # preprocess_level values: "none", "minimal", "standard", "aggressive"
    ARABIC_MULTI_PASS_CONFIGS = [
        {
            "name": "standard",
            "params": {
                "text_det_limit_side_len": 1280,
                "text_rec_score_thresh": 0.25,
                "text_det_box_thresh": 0.5,
            },
            "preprocess_level": "standard"
        },
        {
            "name": "high_resolution",
            "params": {
                "text_det_limit_side_len": 1920,
                "text_rec_score_thresh": 0.20,
                "text_det_box_thresh": 0.4,
            },
            "preprocess_level": "aggressive"
        },
        {
            "name": "low_threshold",
            "params": {
                "text_det_limit_side_len": 1280,
                "text_rec_score_thresh": 0.15,
                "text_det_box_thresh": 0.3,
            },
            "preprocess_level": "minimal"
        },
    ]

    # Minimum confidence threshold for keeping results
    MIN_CONFIDENCE_THRESHOLD = 0.20  # Lower to catch more Arabic text

    # Multi-pass OCR settings
    MULTI_PASS_ENABLED = True
    MULTI_PASS_CONFIDENCE_THRESHOLD = 0.85  # Below this, try another pass
    MAX_OCR_PASSES = 3

    # Thread lock for PaddlePaddle (oneDNN kernel is not thread-safe)
    _ocr_lock = threading.Lock()

    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = False,
        use_angle_cls: bool = True,
        use_server_model: bool = True
    ):
        """
        Initialize PaddleOCR engine.

        Args:
            lang: Default language ("en" or "ar")
            use_gpu: Enable GPU acceleration
            use_angle_cls: Enable text angle classification
            use_server_model: Use server-side model for higher accuracy
        """
        self._lang = self._normalize_lang(lang)
        self._use_gpu = use_gpu
        self._use_angle_cls = use_angle_cls
        self._use_server_model = use_server_model
        self._ocr_engines: Dict[str, Any] = {}
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "paddle"

    @property
    def display_name(self) -> str:
        return "PaddleOCR"

    def _normalize_lang(self, lang: str) -> str:
        """Normalize language code to PaddleOCR format."""
        lang_lower = lang.lower()
        return self.LANG_MAP.get(lang_lower, lang_lower)

    def is_available(self) -> bool:
        """Check if PaddleOCR is installed and working."""
        if self._available is not None:
            return self._available

        try:
            from paddleocr import PaddleOCR
            # Try to initialize (will download models if needed)
            self._available = True
            return True
        except ImportError:
            logger.warning("PaddleOCR is not installed")
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"PaddleOCR initialization check failed: {e}")
            self._available = False
            return False

    def get_capabilities(self) -> EngineCapabilities:
        """Get PaddleOCR capabilities."""
        return EngineCapabilities(
            supports_images=True,
            supports_pdf=True,
            supports_vision_analysis=False,
            supports_gpu=True,
            supported_languages=self.SUPPORTED_LANGUAGES.copy(),
            max_file_size_mb=50,
            supports_batch=False,
            supports_streaming=False,
            supports_tables=True,
            supports_structure=True
        )

    def _get_ocr_engine(self, lang: str) -> Any:
        """
        Get or create OCR engine for specified language.

        Uses lazy initialization and caching.
        Configures PP-OCRv5 with optimized parameters for each language.
        """
        lang = self._normalize_lang(lang)

        if lang not in self._ocr_engines:
            if lang not in self.SUPPORTED_LANGUAGES:
                raise LanguageNotSupportedError(
                    f"Language '{lang}' is not supported. Use one of: {self.SUPPORTED_LANGUAGES}",
                    engine=self.name
                )

            try:
                from paddleocr import PaddleOCR

                logger.info(f"Initializing PaddleOCR PP-OCRv5 for language: {lang}")

                # Build initialization parameters
                init_params = {
                    "lang": lang,
                    "ocr_version": "PP-OCRv5",  # CRITICAL: Use PP-OCRv5
                    "use_doc_orientation_classify": self._use_angle_cls,
                    "use_doc_unwarping": True,  # Document unwarping for skewed docs
                    "use_textline_orientation": True,  # Handle rotated text lines
                    "device": "gpu" if self._use_gpu else "cpu",
                }

                # Use server model for higher accuracy if requested
                if self._use_server_model:
                    init_params["text_det_model_name"] = "PP-OCRv5_server_det"
                    logger.info("Using PP-OCRv5 server detection model for higher accuracy")

                self._ocr_engines[lang] = PaddleOCR(**init_params)

            except Exception as e:
                logger.warning(f"Failed to initialize with server model: {e}")
                # Fallback to standard initialization
                try:
                    from paddleocr import PaddleOCR
                    logger.info("Falling back to standard PP-OCRv5 initialization")
                    self._ocr_engines[lang] = PaddleOCR(
                        lang=lang,
                        ocr_version="PP-OCRv5",
                        use_doc_orientation_classify=self._use_angle_cls,
                        device="gpu" if self._use_gpu else "cpu",
                    )
                except Exception as e2:
                    raise EngineNotAvailableError(
                        f"Failed to initialize PaddleOCR: {e2}",
                        engine=self.name
                    )

        return self._ocr_engines[lang]

    def _get_ocr_params(self, lang: str) -> Dict[str, Any]:
        """Get language-specific OCR parameters for predict call."""
        if lang == "ar":
            return self.ARABIC_OCR_PARAMS.copy()
        return self.ENGLISH_OCR_PARAMS.copy()

    def _get_document_detector(self):
        """Get DocumentTypeDetector instance (lazy loading)."""
        if not hasattr(self, '_document_detector'):
            try:
                from ..utils.document_type_detector import DocumentTypeDetector
                self._document_detector = DocumentTypeDetector()
            except ImportError:
                logger.warning("DocumentTypeDetector not available, using defaults")
                self._document_detector = None
        return self._document_detector

    def _get_image_preprocessor(self):
        """Get ArabicImagePreprocessor instance (lazy loading)."""
        if not hasattr(self, '_image_preprocessor'):
            try:
                from ..utils.image_preprocessor import ArabicImagePreprocessor
                self._image_preprocessor = ArabicImagePreprocessor()
            except ImportError:
                logger.warning("ArabicImagePreprocessor not available, using defaults")
                self._image_preprocessor = None
        return self._image_preprocessor

    def _get_table_engine(self):
        """Get TableRecognitionEngine instance (lazy loading)."""
        if not hasattr(self, '_table_engine'):
            try:
                from .table_engine import TableRecognitionEngine
                self._table_engine = TableRecognitionEngine()
            except ImportError:
                logger.warning("TableRecognitionEngine not available")
                self._table_engine = None
        return self._table_engine

    def _get_layout_engine(self):
        """Get LayoutAnalysisEngine instance (lazy loading)."""
        if not hasattr(self, '_layout_engine'):
            try:
                from .layout_engine import LayoutAnalysisEngine
                self._layout_engine = LayoutAnalysisEngine()
            except ImportError:
                logger.warning("LayoutAnalysisEngine not available")
                self._layout_engine = None
        return self._layout_engine

    def _get_reading_order_analyzer(self):
        """Get ArabicReadingOrderAnalyzer instance (lazy loading)."""
        if not hasattr(self, '_reading_order_analyzer'):
            try:
                from ..utils.reading_order import ArabicReadingOrderAnalyzer
                self._reading_order_analyzer = ArabicReadingOrderAnalyzer()
            except ImportError:
                logger.warning("ArabicReadingOrderAnalyzer not available")
                self._reading_order_analyzer = None
        return self._reading_order_analyzer

    def _get_bilingual_formatter(self):
        """Get BilingualMarkdownFormatter instance (lazy loading)."""
        if not hasattr(self, '_bilingual_formatter'):
            try:
                from ..formatters.bilingual_formatter import BilingualMarkdownFormatter
                self._bilingual_formatter = BilingualMarkdownFormatter(
                    include_raw=False,
                    include_metadata=True
                )
            except ImportError:
                logger.warning("BilingualMarkdownFormatter not available")
                self._bilingual_formatter = None
        return self._bilingual_formatter

    def _get_invoice_schema(self):
        """Get InvoiceDocument class reference (lazy loading)."""
        if not hasattr(self, '_invoice_schema_module'):
            try:
                from ..formatters import json_schema
                self._invoice_schema_module = json_schema
            except ImportError:
                logger.warning("JSON schema module not available")
                self._invoice_schema_module = None
        return self._invoice_schema_module

    def _get_invoice_validator(self):
        """Get InvoiceValidator instance (lazy loading)."""
        if not hasattr(self, '_invoice_validator'):
            try:
                from ..validators.invoice_validator import InvoiceValidator
                self._invoice_validator = InvoiceValidator()
            except ImportError:
                logger.warning("InvoiceValidator not available")
                self._invoice_validator = None
        return self._invoice_validator

    def _get_confidence_scorer(self):
        """Get ConfidenceScorer instance (lazy loading)."""
        if not hasattr(self, '_confidence_scorer'):
            try:
                from ..validators.confidence_scorer import ConfidenceScorer
                self._confidence_scorer = ConfidenceScorer()
            except ImportError:
                logger.warning("ConfidenceScorer not available")
                self._confidence_scorer = None
        return self._confidence_scorer

    def _get_ml_enhancer(self):
        """Get MLArabicEnhancer instance (lazy loading)."""
        if not hasattr(self, '_ml_enhancer'):
            try:
                from ..ml.arabic_ocr_enhancer import MLArabicEnhancer, EnhancementMode
                self._ml_enhancer = MLArabicEnhancer(
                    mode=EnhancementMode.ML_WITH_FALLBACK,
                    context="invoice"
                )
            except ImportError:
                logger.warning("MLArabicEnhancer not available")
                self._ml_enhancer = None
        return self._ml_enhancer

    def _get_template_learner(self):
        """Get TemplateLearner instance (lazy loading)."""
        if not hasattr(self, '_template_learner'):
            try:
                from ..learning.template_learner import TemplateLearner
                self._template_learner = TemplateLearner(
                    templates_dir="data/templates",
                    auto_save=True
                )
            except ImportError:
                logger.warning("TemplateLearner not available")
                self._template_learner = None
        return self._template_learner

    def _run_multi_pass_ocr(
        self,
        image_input: Any,
        lang: str,
        ocr: Any,
        document_analysis: Optional[Any] = None
    ) -> OCRPassResult:
        """
        Run multi-pass OCR with different parameters for best results.

        For Arabic text, runs multiple OCR passes with varying parameters
        and preprocessing levels, returning the pass with best confidence.

        Args:
            image_input: Image path or numpy array
            lang: Language code
            ocr: PaddleOCR engine instance
            document_analysis: Optional DocumentAnalysis for parameter optimization

        Returns:
            OCRPassResult with best results
        """
        if lang != "ar" or not self.MULTI_PASS_ENABLED:
            # Single pass for English or when multi-pass disabled
            result = ocr.predict(input=image_input)
            blocks = self._extract_raw_blocks(result)
            avg_conf = self._calculate_avg_confidence(blocks)
            return OCRPassResult(
                text_blocks=blocks,
                avg_confidence=avg_conf,
                pass_name="single",
                params_used=self._get_ocr_params(lang)
            )

        # Multi-pass OCR for Arabic
        best_result: Optional[OCRPassResult] = None
        preprocessor = self._get_image_preprocessor()

        for pass_idx, config in enumerate(self.ARABIC_MULTI_PASS_CONFIGS[:self.MAX_OCR_PASSES]):
            pass_name = config["name"]
            logger.debug(f"Running OCR pass {pass_idx + 1}: {pass_name}")

            # Apply preprocessing based on pass configuration
            if preprocessor and isinstance(image_input, str):
                try:
                    from ..utils.image_preprocessor import PreprocessingLevel
                    level_map = {
                        "none": PreprocessingLevel.NONE,
                        "minimal": PreprocessingLevel.MINIMAL,
                        "standard": PreprocessingLevel.STANDARD,
                        "aggressive": PreprocessingLevel.AGGRESSIVE,
                    }
                    level = level_map.get(config.get("preprocess_level", "standard"), PreprocessingLevel.STANDARD)
                    processed_image = preprocessor.preprocess(image_input, lang=lang, level=level)
                except Exception as e:
                    logger.warning(f"Preprocessing failed for pass {pass_name}: {e}")
                    processed_image = image_input
            else:
                processed_image = image_input

            # Run OCR
            try:
                result = ocr.predict(input=processed_image)
                blocks = self._extract_raw_blocks(result)
                avg_conf = self._calculate_avg_confidence(blocks)

                pass_result = OCRPassResult(
                    text_blocks=blocks,
                    avg_confidence=avg_conf,
                    pass_name=pass_name,
                    params_used=config["params"]
                )

                logger.debug(f"Pass '{pass_name}': {len(blocks)} blocks, avg confidence: {avg_conf:.3f}")

                # Update best result if this pass is better
                if best_result is None or avg_conf > best_result.avg_confidence:
                    best_result = pass_result

                # If confidence is good enough, stop early
                if avg_conf >= self.MULTI_PASS_CONFIDENCE_THRESHOLD:
                    logger.info(f"Achieved target confidence {avg_conf:.3f} on pass '{pass_name}'")
                    break

            except Exception as e:
                logger.warning(f"OCR pass '{pass_name}' failed: {e}")
                continue

        # Return best result or empty result if all passes failed
        if best_result:
            logger.info(f"Best OCR pass: '{best_result.pass_name}' with confidence {best_result.avg_confidence:.3f}")
            return best_result

        return OCRPassResult(
            text_blocks=[],
            avg_confidence=0.0,
            pass_name="failed",
            params_used={}
        )

    def _extract_raw_blocks(self, result: Any) -> List[Dict]:
        """Extract raw text blocks from OCR result without post-processing."""
        raw_blocks = []

        for res in result:
            # New API format: dict-like object with rec_texts, rec_scores, dt_polys
            if hasattr(res, 'keys'):
                texts = res.get('rec_texts', []) or []
                scores = res.get('rec_scores', []) or []
                polys = res.get('dt_polys', []) or []

                for i, text in enumerate(texts):
                    if not text.strip():
                        continue

                    score = scores[i] if i < len(scores) else 0.0

                    bbox = None
                    if i < len(polys) and hasattr(polys[i], 'tolist'):
                        bbox = polys[i].tolist()
                    elif i < len(polys):
                        bbox = list(polys[i])

                    raw_blocks.append({
                        'text': text,
                        'confidence': round(float(score), 4),
                        'bbox': bbox
                    })

            # Legacy format: list of [bbox, (text, score)]
            elif isinstance(res, list):
                for line in res:
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        bbox = line[0]
                        text_info = line[1]

                        if isinstance(text_info, (list, tuple)):
                            text = text_info[0] if len(text_info) > 0 else ""
                            confidence = text_info[1] if len(text_info) > 1 else 0.0
                        else:
                            text = str(text_info)
                            confidence = 0.0

                        if not text.strip():
                            continue

                        raw_blocks.append({
                            'text': text,
                            'confidence': round(float(confidence), 4),
                            'bbox': bbox if isinstance(bbox, list) else None
                        })

        return raw_blocks

    def _calculate_avg_confidence(self, blocks: List[Dict]) -> float:
        """Calculate average confidence from text blocks."""
        if not blocks:
            return 0.0
        total_conf = sum(b.get('confidence', 0.0) for b in blocks)
        return total_conf / len(blocks)

    def process_image(
        self,
        image_path: str,
        lang: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process an image file with OCR.

        Enhanced with Stage 1 optimizations:
        - DocumentTypeDetector for adaptive parameters
        - ArabicImagePreprocessor for quality enhancement
        - Multi-pass OCR with confidence-based retry

        Args:
            image_path: Path to the image file
            lang: Language code ("en" or "ar")
            options: Additional options

        Returns:
            ReadResult with extracted text
        """
        start_time = time.perf_counter()
        lang = self._normalize_lang(lang)
        options = options or {}

        # Validate file exists
        if not os.path.exists(image_path):
            return self._create_error_result(
                image_path,
                f"Image not found: {image_path}",
                "image"
            )

        try:
            # Stage 1: Document type detection for adaptive parameters
            document_analysis = None
            document_type = "unknown"
            detector = self._get_document_detector()

            if detector and lang == "ar":
                try:
                    document_analysis = detector.analyze(image_path)
                    document_type = document_analysis.document_type.value
                    logger.info(f"Detected document type: {document_type} "
                               f"(confidence: {document_analysis.confidence:.2f})")
                except Exception as e:
                    logger.warning(f"Document detection failed: {e}")

            # Use lock to prevent concurrent PaddlePaddle access (oneDNN not thread-safe)
            with self._ocr_lock:
                ocr = self._get_ocr_engine(lang)

                # Stage 1: Multi-pass OCR for Arabic
                if lang == "ar" and self.MULTI_PASS_ENABLED and not options.get("single_pass", False):
                    ocr_result = self._run_multi_pass_ocr(
                        image_input=image_path,
                        lang=lang,
                        ocr=ocr,
                        document_analysis=document_analysis
                    )
                    raw_blocks = ocr_result.text_blocks
                    ocr_pass = ocr_result.pass_name
                    avg_confidence = ocr_result.avg_confidence
                else:
                    # Single pass for English or when explicitly requested
                    processed_image = self._preprocess_image(image_path, lang)
                    result = ocr.predict(input=processed_image)
                    raw_blocks = self._extract_raw_blocks(result)
                    ocr_pass = "single"
                    avg_confidence = self._calculate_avg_confidence(raw_blocks)

            # Apply confidence filtering
            filtered_blocks = [
                b for b in raw_blocks
                if b.get('confidence', 0.0) >= self.MIN_CONFIDENCE_THRESHOLD
            ]

            # Apply RTL ordering for Arabic
            if lang == "ar" and filtered_blocks:
                filtered_blocks = self._sort_blocks_rtl(filtered_blocks)

            # Apply Arabic post-processing
            if lang == "ar":
                filtered_blocks = self._apply_arabic_corrections(filtered_blocks)

            # Stage 3: Document structure analysis for Arabic
            structure_result = None
            if lang == "ar" and options.get("enable_structure_analysis", True):
                structure_result = self._apply_document_structure_analysis(
                    filtered_blocks,
                    image_path
                )
                filtered_blocks = structure_result['ordered_blocks']

            # Convert to TextBlock objects
            text_blocks = [
                TextBlock(
                    text=b['text'],
                    confidence=b['confidence'],
                    bbox=b['bbox']
                ) for b in filtered_blocks
            ]

            # Build full text
            full_text = self._reconstruct_text_lines(filtered_blocks, lang)

            # Create page result
            pages = [PageResult(
                page_number=1,
                text_blocks=text_blocks,
                full_text=full_text
            )]

            processing_time = (time.perf_counter() - start_time) * 1000

            # Build metadata
            metadata = {
                "ocr_version": "PP-OCRv5",
                "server_model": self._use_server_model,
                "preprocessed": True,
                "document_type": document_type,
                "ocr_pass": ocr_pass,
                "avg_confidence": round(avg_confidence, 4),
                "multi_pass_enabled": self.MULTI_PASS_ENABLED and lang == "ar"
            }

            # Add Stage 3 metadata if available
            if structure_result:
                if structure_result.get('layout'):
                    layout = structure_result['layout']
                    metadata['layout'] = {
                        'num_zones': len(layout.zones),
                        'has_header': layout.header_zone is not None,
                        'has_footer': layout.footer_zone is not None,
                        'num_columns': layout.num_columns
                    }
                if structure_result.get('tables'):
                    metadata['tables'] = len(structure_result['tables'])
                if structure_result.get('line_items'):
                    metadata['line_items'] = len(structure_result['line_items'])

            return self._create_success_result(
                file_path=image_path,
                file_type="image",
                pages=pages,
                language=lang,
                processing_time_ms=processing_time,
                metadata=metadata
            )

        except LanguageNotSupportedError:
            raise
        except Exception as e:
            logger.exception(f"Error processing image: {image_path}")
            return self._create_error_result(
                image_path,
                f"OCR processing failed: {str(e)}",
                "image"
            )

    def _apply_arabic_corrections(self, blocks: List[Dict]) -> List[Dict]:
        """
        Apply Arabic-specific OCR corrections to text blocks.

        Stage 2 Enhancements:
        - ArabicWordSeparator for merged word separation
        - ArabicSpellChecker for context-aware OCR error correction
        - ArabicNumberNormalizer for number/currency normalization

        Args:
            blocks: List of text block dictionaries

        Returns:
            Corrected text blocks
        """
        # Step 1: Apply basic Arabic OCR corrections (legacy)
        try:
            from ..utils.arabic_utils import advanced_arabic_ocr_correction
            for block in blocks:
                block['text'] = advanced_arabic_ocr_correction(block['text'])
        except ImportError:
            pass  # Corrections not available

        # Step 2: Stage 2 - Word Separation
        try:
            from ..utils.arabic_word_separator import ArabicWordSeparator
            separator = ArabicWordSeparator()
            blocks = ArabicWordSeparator.separate_text_blocks(blocks, separator)
            logger.debug("Applied Stage 2 word separation")
        except ImportError:
            # Fallback to legacy enhancer
            try:
                from ..utils.arabic_enhancer import ArabicTextEnhancer
                blocks = ArabicTextEnhancer.enhance_text_blocks(blocks)
            except ImportError:
                pass

        # Step 3: Stage 2 - Spell Checking
        try:
            from ..utils.arabic_spell_checker import ArabicSpellChecker, DocumentContext
            checker = ArabicSpellChecker(context=DocumentContext.INVOICE)
            blocks = ArabicSpellChecker.correct_text_blocks(
                blocks,
                context=DocumentContext.INVOICE,
                checker=checker
            )
            logger.debug("Applied Stage 2 spell checking")
        except ImportError:
            pass  # Spell checker not available

        # Step 4: Stage 2 - Number Normalization
        try:
            from ..utils.arabic_number_normalizer import ArabicNumberNormalizer
            normalizer = ArabicNumberNormalizer()
            blocks = ArabicNumberNormalizer.normalize_text_blocks(blocks, normalizer)
            logger.debug("Applied Stage 2 number normalization")
        except ImportError:
            # Fallback to legacy number validator
            try:
                from ..validators.number_validator import NumberValidator
                blocks = NumberValidator.enhance_text_block_numbers(blocks)
            except ImportError:
                pass

        return blocks

    def _apply_document_structure_analysis(
        self,
        blocks: List[Dict],
        image_path: str,
        page_width: Optional[float] = None,
        page_height: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Apply Stage 3 document structure analysis to text blocks.

        Performs:
        - Layout analysis for zone detection (header, footer, tables)
        - Table recognition and line item extraction
        - RTL reading order optimization for Arabic

        Args:
            blocks: List of text block dictionaries
            image_path: Path to the source image
            page_width: Optional page width
            page_height: Optional page height

        Returns:
            Dictionary with:
            - ordered_blocks: Text blocks in correct reading order
            - layout: DocumentLayout if available
            - tables: List of recognized tables if available
            - line_items: Extracted line items from tables
        """
        result = {
            'ordered_blocks': blocks,
            'layout': None,
            'tables': [],
            'line_items': []
        }

        if not blocks:
            return result

        # Step 1: Layout analysis
        layout_engine = self._get_layout_engine()
        if layout_engine:
            try:
                layout = layout_engine.analyze(image_path, ocr_blocks=blocks)
                result['layout'] = layout
                logger.debug(f"Layout analysis complete: found {len(layout.zones)} zones")
            except Exception as e:
                logger.warning(f"Layout analysis failed: {e}")

        # Step 2: Table recognition
        table_engine = self._get_table_engine()
        if table_engine:
            try:
                # Get table zones from layout if available
                table_zones = []
                if result['layout']:
                    from .layout_engine import ZoneType
                    table_zones = [
                        z for z in result['layout'].zones
                        if z.zone_type in (ZoneType.TABLE, ZoneType.LINE_ITEMS)
                    ]

                # Recognize tables in detected zones
                tables = []
                line_items = []

                if table_zones:
                    for zone in table_zones:
                        try:
                            table = table_engine.recognize_table(image_path, zone.bbox)
                            if table:
                                tables.append(table)
                                items = table_engine.extract_line_items(table)
                                line_items.extend(items)
                        except Exception as e:
                            logger.warning(f"Table recognition failed for zone: {e}")
                else:
                    # Try to detect tables if no zones found
                    detected_tables = table_engine.detect_tables(image_path)
                    for table_info in detected_tables:
                        try:
                            table = table_engine.recognize_table(
                                image_path,
                                table_info.get('bbox')
                            )
                            if table:
                                tables.append(table)
                                items = table_engine.extract_line_items(table)
                                line_items.extend(items)
                        except Exception as e:
                            logger.warning(f"Table recognition failed: {e}")

                result['tables'] = tables
                result['line_items'] = line_items
                logger.debug(f"Table recognition: {len(tables)} tables, {len(line_items)} line items")

            except Exception as e:
                logger.warning(f"Table processing failed: {e}")

        # Step 3: Reading order optimization for RTL
        reading_order_analyzer = self._get_reading_order_analyzer()
        if reading_order_analyzer:
            try:
                reading_result = reading_order_analyzer.analyze(
                    blocks,
                    page_width=page_width,
                    page_height=page_height
                )
                # Convert TextBlock objects back to dicts
                ordered_blocks = []
                for block in reading_result.blocks:
                    ordered_blocks.append({
                        'text': block.text,
                        'confidence': block.confidence,
                        'bbox': block.bbox
                    })
                result['ordered_blocks'] = ordered_blocks
                logger.debug(f"Reading order: {reading_result.layout_mode.value}, "
                           f"{reading_result.num_columns} columns")
            except Exception as e:
                logger.warning(f"Reading order analysis failed: {e}")
                # Keep original block order

        return result

    def _preprocess_image(self, image_path: str, lang: str) -> Any:
        """
        Preprocess image for better OCR recognition.

        Stage 1 Enhancement: Uses ArabicImagePreprocessor for intelligent
        preprocessing that complements PP-OCRv5's built-in preprocessing.

        Args:
            image_path: Path to image file
            lang: Language code

        Returns:
            Preprocessed image (numpy array or path)
        """
        # For Arabic, use ArabicImagePreprocessor if available
        if lang == "ar":
            preprocessor = self._get_image_preprocessor()
            if preprocessor:
                try:
                    from ..utils.image_preprocessor import PreprocessingLevel
                    # Use standard preprocessing level for single-pass
                    return preprocessor.preprocess(
                        image_path,
                        lang=lang,
                        level=PreprocessingLevel.STANDARD
                    )
                except Exception as e:
                    logger.warning(f"Image preprocessing failed: {e}")

        # PP-OCRv5 has built-in preprocessing, return path directly
        return image_path

    def process_pdf(
        self,
        pdf_path: str,
        lang: str = "en",
        max_pages: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process a PDF file with OCR.

        Converts each page to an image and runs OCR with language-specific
        optimizations (preprocessing, RTL ordering for Arabic).

        Args:
            pdf_path: Path to the PDF file
            lang: Language code ("en" or "ar")
            max_pages: Maximum pages to process (None for all)
            options: Additional options

        Returns:
            ReadResult with extracted text from all pages
        """
        start_time = time.perf_counter()
        lang = self._normalize_lang(lang)

        # Validate file exists
        if not os.path.exists(pdf_path):
            return self._create_error_result(
                pdf_path,
                f"PDF not found: {pdf_path}",
                "pdf"
            )

        try:
            import fitz  # PyMuPDF
            from PIL import Image
            import cv2
            import numpy as np

            # Use lock to prevent concurrent PaddlePaddle access
            with self._ocr_lock:
                ocr = self._get_ocr_engine(lang)

            ocr_params = self._get_ocr_params(lang)
            pages = []

            with fitz.open(pdf_path) as pdf:
                total_pages = pdf.page_count
                pages_to_process = min(max_pages, total_pages) if max_pages else total_pages

                for page_num in range(pages_to_process):
                    page = pdf[page_num]

                    # Convert page to image (2x scale for better OCR)
                    # Use higher scale for Arabic to capture diacritics
                    scale = 2.5 if lang == "ar" else 2.0
                    mat = fitz.Matrix(scale, scale)
                    pm = page.get_pixmap(matrix=mat, alpha=False)

                    # Reduce scale if too large (but keep higher for Arabic)
                    max_size = 2500 if lang == "ar" else 2000
                    if pm.width > max_size or pm.height > max_size:
                        fallback_scale = 1.5 if lang == "ar" else 1.0
                        pm = page.get_pixmap(matrix=fitz.Matrix(fallback_scale, fallback_scale), alpha=False)

                    # Convert to numpy array for OCR
                    img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
                    img_array = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                    # Apply preprocessing for Arabic
                    if lang == "ar":
                        img_array = self._preprocess_pdf_page(img_array)

                    # Run OCR (locked for thread safety)
                    # Parameters configured at engine init to avoid RuntimeError
                    with self._ocr_lock:
                        result = ocr.predict(input=img_array)

                    page_data = {
                        'text_blocks': [],
                        'full_text': ''
                    }

                    for res in result:
                        # Pass language for RTL support
                        parsed = self._parse_ocr_result(res, lang=lang)
                        page_data['text_blocks'].extend(parsed['text_blocks'])
                        if page_data['full_text']:
                            page_data['full_text'] += '\n' + parsed['full_text']
                        else:
                            page_data['full_text'] = parsed['full_text']

                    pages.append(PageResult(
                        page_number=page_num + 1,
                        text_blocks=page_data['text_blocks'],
                        full_text=page_data['full_text'],
                        width=pm.width,
                        height=pm.height
                    ))

            processing_time = (time.perf_counter() - start_time) * 1000

            return self._create_success_result(
                file_path=pdf_path,
                file_type="pdf",
                pages=pages,
                language=lang,
                processing_time_ms=processing_time,
                metadata={
                    "total_pages": total_pages,
                    "processed_pages": len(pages),
                    "ocr_version": "PP-OCRv5",
                    "server_model": self._use_server_model,
                    "preprocessed": True
                }
            )

        except LanguageNotSupportedError:
            raise
        except ImportError as e:
            return self._create_error_result(
                pdf_path,
                f"Missing dependency for PDF processing: {e}",
                "pdf"
            )
        except Exception as e:
            logger.exception(f"Error processing PDF: {pdf_path}")
            return self._create_error_result(
                pdf_path,
                f"PDF processing failed: {str(e)}",
                "pdf"
            )

    def _preprocess_pdf_page(self, img_array: Any) -> Any:
        """
        Preprocess PDF page image for better Arabic OCR.

        Stage 1 Enhancement: Uses ArabicImagePreprocessor for intelligent
        preprocessing on PDF page images.

        Args:
            img_array: NumPy array of the image

        Returns:
            Preprocessed image array
        """
        preprocessor = self._get_image_preprocessor()
        if preprocessor:
            try:
                from ..utils.image_preprocessor import PreprocessingLevel
                # Use standard preprocessing for PDF pages
                return preprocessor.preprocess(
                    img_array,
                    lang="ar",
                    level=PreprocessingLevel.STANDARD
                )
            except Exception as e:
                logger.warning(f"PDF page preprocessing failed: {e}")

        # Return original array if preprocessing fails
        return img_array

    def _parse_ocr_result(self, result: Any, lang: str = "en") -> Dict[str, Any]:
        """
        Parse OCR result into structured format with RTL support.

        Handles both new API format (dict-like with rec_texts) and
        legacy format (list of [bbox, (text, score)]).

        For Arabic (RTL):
        - Sorts text blocks by vertical position (top to bottom)
        - Within each line, sorts by x-position right-to-left
        - Groups nearby blocks into logical lines
        - Filters low-confidence results

        Args:
            result: Raw OCR result from PaddleOCR
            lang: Language code for proper text ordering

        Returns:
            Dictionary with 'text_blocks' and 'full_text'
        """
        raw_blocks = []

        # New API format: dict-like object with rec_texts, rec_scores, dt_polys
        if hasattr(result, 'keys'):
            texts = result.get('rec_texts', []) or []
            scores = result.get('rec_scores', []) or []
            polys = result.get('dt_polys', []) or []

            for i, text in enumerate(texts):
                if not text.strip():
                    continue

                score = scores[i] if i < len(scores) else 0.0

                # Filter low confidence results
                if float(score) < self.MIN_CONFIDENCE_THRESHOLD:
                    logger.debug(f"Filtered low confidence text: '{text}' (score={score})")
                    continue

                bbox = None
                if i < len(polys) and hasattr(polys[i], 'tolist'):
                    bbox = polys[i].tolist()
                elif i < len(polys):
                    bbox = list(polys[i])

                raw_blocks.append({
                    'text': text,
                    'confidence': round(float(score), 4),
                    'bbox': bbox
                })

        # Legacy format: list of [bbox, (text, score)]
        elif isinstance(result, list):
            for line in result:
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    bbox = line[0]
                    text_info = line[1]

                    if isinstance(text_info, (list, tuple)):
                        text = text_info[0] if len(text_info) > 0 else ""
                        confidence = text_info[1] if len(text_info) > 1 else 0.0
                    else:
                        text = str(text_info)
                        confidence = 0.0

                    if not text.strip():
                        continue

                    # Filter low confidence results
                    if float(confidence) < self.MIN_CONFIDENCE_THRESHOLD:
                        logger.debug(f"Filtered low confidence text: '{text}' (score={confidence})")
                        continue

                    raw_blocks.append({
                        'text': text,
                        'confidence': round(float(confidence), 4),
                        'bbox': bbox if isinstance(bbox, list) else None
                    })

        # Apply RTL ordering for Arabic
        if lang == "ar" and raw_blocks:
            raw_blocks = self._sort_blocks_rtl(raw_blocks)

        # Apply Arabic OCR corrections to individual text blocks
        # This ensures Detailed View shows corrected text matching other views
        if lang == "ar":
            try:
                from ..utils.arabic_utils import advanced_arabic_ocr_correction
                for block in raw_blocks:
                    block['text'] = advanced_arabic_ocr_correction(block['text'])
            except ImportError:
                pass  # Corrections not available, use raw text

            # Apply enhanced Arabic text processing (word separation, spelling)
            try:
                from ..utils.arabic_enhancer import ArabicTextEnhancer
                raw_blocks = ArabicTextEnhancer.enhance_text_blocks(raw_blocks)
            except ImportError:
                pass  # Enhanced processing not available

            # Apply number validation and digit restoration
            try:
                from ..validators.number_validator import NumberValidator
                raw_blocks = NumberValidator.enhance_text_block_numbers(raw_blocks)
            except ImportError:
                pass  # Number validation not available

        # Convert to TextBlock objects
        text_blocks = [
            TextBlock(
                text=b['text'],
                confidence=b['confidence'],
                bbox=b['bbox']
            ) for b in raw_blocks
        ]

        # Build full text with proper line reconstruction
        full_text = self._reconstruct_text_lines(raw_blocks, lang)

        return {
            'text_blocks': text_blocks,
            'full_text': full_text
        }

    def _sort_blocks_rtl(self, blocks: List[Dict]) -> List[Dict]:
        """
        Sort text blocks for RTL (Arabic) reading order.

        Groups blocks into lines by Y-position, then sorts each line
        from right to left by X-position.

        Args:
            blocks: List of text block dictionaries with bbox

        Returns:
            Sorted list of blocks
        """
        if not blocks:
            return blocks

        # Extract blocks with valid bboxes
        blocks_with_bbox = []
        blocks_without_bbox = []

        for block in blocks:
            if block.get('bbox') and len(block['bbox']) >= 2:
                # Get center Y and left X from bbox
                # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                try:
                    bbox = block['bbox']
                    y_center = (bbox[0][1] + bbox[2][1]) / 2
                    x_left = min(p[0] for p in bbox)
                    x_right = max(p[0] for p in bbox)
                    block['_y'] = y_center
                    block['_x_left'] = x_left
                    block['_x_right'] = x_right
                    blocks_with_bbox.append(block)
                except (IndexError, TypeError):
                    blocks_without_bbox.append(block)
            else:
                blocks_without_bbox.append(block)

        if not blocks_with_bbox:
            return blocks

        # Sort by Y position first (top to bottom)
        blocks_with_bbox.sort(key=lambda b: b['_y'])

        # Group into lines (blocks within ~20px vertical distance)
        LINE_TOLERANCE = 20
        lines = []
        current_line = [blocks_with_bbox[0]]
        current_y = blocks_with_bbox[0]['_y']

        for block in blocks_with_bbox[1:]:
            if abs(block['_y'] - current_y) <= LINE_TOLERANCE:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
                current_y = block['_y']

        if current_line:
            lines.append(current_line)

        # Sort each line from right to left (RTL)
        sorted_blocks = []
        for line in lines:
            # Sort by x_right descending (rightmost first)
            line.sort(key=lambda b: b['_x_right'], reverse=True)
            sorted_blocks.extend(line)

        # Add blocks without bbox at the end
        sorted_blocks.extend(blocks_without_bbox)

        # Clean up temporary keys
        for block in sorted_blocks:
            block.pop('_y', None)
            block.pop('_x_left', None)
            block.pop('_x_right', None)

        return sorted_blocks

    def _reconstruct_text_lines(self, blocks: List[Dict], lang: str) -> str:
        """
        Reconstruct full text from sorted blocks.

        For Arabic:
        - Groups blocks into lines
        - Joins with proper spacing
        - Handles mixed Arabic/English text
        - Applies OCR error corrections

        Args:
            blocks: Sorted list of text blocks
            lang: Language code

        Returns:
            Reconstructed full text
        """
        if not blocks:
            return ""

        # For Arabic, use space separator within lines, newline between lines
        if lang == "ar":
            lines = []
            current_line = []
            last_y = None
            LINE_TOLERANCE = 20

            for block in blocks:
                if block.get('bbox') and len(block['bbox']) >= 2:
                    try:
                        y_center = (block['bbox'][0][1] + block['bbox'][2][1]) / 2
                        if last_y is None or abs(y_center - last_y) <= LINE_TOLERANCE:
                            current_line.append(block['text'])
                            last_y = y_center if last_y is None else last_y
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [block['text']]
                            last_y = y_center
                    except (IndexError, TypeError):
                        current_line.append(block['text'])
                else:
                    current_line.append(block['text'])

            if current_line:
                lines.append(' '.join(current_line))

            raw_text = '\n'.join(lines)

            # Apply advanced Arabic correction with word restoration
            try:
                from ..utils.arabic_utils import advanced_arabic_ocr_correction
                return advanced_arabic_ocr_correction(raw_text)
            except ImportError:
                return raw_text

        # For English, simple join with newlines
        return '\n'.join(b['text'] for b in blocks)

    def format_as_markdown(
        self,
        extracted_data: Dict[str, Any],
        layout: Optional[Any] = None,
        tables: Optional[List[Any]] = None
    ) -> str:
        """
        Format extracted data as bilingual markdown (Stage 4).

        Uses BilingualMarkdownFormatter to create professional
        Claude Code CLI-style output.

        Args:
            extracted_data: Structured invoice/document data
            layout: Optional DocumentLayout from Stage 3
            tables: Optional list of RecognizedTable from Stage 3

        Returns:
            Formatted markdown string
        """
        formatter = self._get_bilingual_formatter()
        if not formatter:
            # Fallback: return simple text representation
            return self._simple_text_format(extracted_data)

        doc_type = extracted_data.get('document_type', 'document').lower()
        if 'invoice' in doc_type or 'فاتورة' in doc_type:
            return formatter.format_invoice(extracted_data, layout, tables)
        else:
            return formatter.format_generic_document(extracted_data, layout)

    def format_as_json(
        self,
        extracted_data: Dict[str, Any],
        erp_format: bool = False,
        zatca_format: bool = False
    ) -> str:
        """
        Format extracted data as structured JSON (Stage 4).

        Uses InvoiceDocument dataclass for type-safe serialization.

        Args:
            extracted_data: Structured invoice/document data
            erp_format: Use ERP-compatible format
            zatca_format: Use ZATCA-compatible format

        Returns:
            JSON string
        """
        schema = self._get_invoice_schema()
        if not schema:
            # Fallback: return basic JSON
            import json
            return json.dumps(extracted_data, ensure_ascii=False, indent=2)

        try:
            invoice = schema.create_invoice_from_ocr(extracted_data)

            if zatca_format:
                import json
                return json.dumps(invoice.to_zatca_format(), ensure_ascii=False, indent=2)
            elif erp_format:
                import json
                return json.dumps(invoice.to_erp_format(), ensure_ascii=False, indent=2)
            else:
                return invoice.to_json(indent=2)

        except Exception as e:
            logger.warning(f"JSON schema formatting failed: {e}")
            import json
            return json.dumps(extracted_data, ensure_ascii=False, indent=2)

    def create_invoice_document(
        self,
        extracted_data: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Create typed InvoiceDocument from extracted data (Stage 4).

        Returns a fully typed dataclass with validation.

        Args:
            extracted_data: Structured invoice data from OCR

        Returns:
            InvoiceDocument instance or None if schema unavailable
        """
        schema = self._get_invoice_schema()
        if not schema:
            return None

        try:
            return schema.create_invoice_from_ocr(extracted_data)
        except Exception as e:
            logger.warning(f"Failed to create InvoiceDocument: {e}")
            return None

    def validate_invoice(
        self,
        invoice_data: Dict[str, Any],
        strict: bool = False
    ) -> Optional[Any]:
        """
        Validate extracted invoice data (Stage 5).

        Performs cross-field validation including:
        - Line item calculations (qty × price = total)
        - Tax calculations (15% Saudi VAT)
        - Totals consistency (subtotal + tax = total)
        - Required field presence
        - Format validation (dates, tax numbers, barcodes)

        Args:
            invoice_data: Extracted invoice data dictionary
            strict: If True, require all expected fields

        Returns:
            ValidationResult with issues and recommendations,
            or None if validator unavailable
        """
        validator = self._get_invoice_validator()
        if not validator:
            return None

        try:
            return validator.validate(invoice_data)
        except Exception as e:
            logger.warning(f"Invoice validation failed: {e}")
            return None

    def score_confidence(
        self,
        invoice_data: Dict[str, Any],
        ocr_blocks: Optional[List[Dict[str, Any]]] = None,
        validation_result: Optional[Any] = None,
        layout_info: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Calculate confidence scores for extracted data (Stage 5).

        Provides comprehensive confidence metrics:
        - Overall document confidence
        - OCR confidence (from text blocks)
        - Extraction completeness
        - Validation score
        - Structure score
        - Field-level confidence
        - Actionable recommendations

        Args:
            invoice_data: Extracted invoice data
            ocr_blocks: Original OCR text blocks with confidence
            validation_result: Optional ValidationResult from validate_invoice
            layout_info: Optional layout analysis info

        Returns:
            DocumentConfidence with detailed scores,
            or None if scorer unavailable
        """
        scorer = self._get_confidence_scorer()
        if not scorer:
            return None

        try:
            return scorer.score_document(
                invoice_data,
                ocr_blocks,
                validation_result,
                layout_info
            )
        except Exception as e:
            logger.warning(f"Confidence scoring failed: {e}")
            return None

    def enhance_text_with_ml(
        self,
        text: str,
        context: str = "invoice"
    ) -> Optional[Any]:
        """
        Enhance OCR text using ML or rule-based methods (Stage 6).

        Uses MLArabicEnhancer for intelligent text correction
        with automatic fallback to rule-based enhancement.

        Args:
            text: Raw OCR text to enhance
            context: Document context ("invoice", "receipt", "general")

        Returns:
            EnhancementResult with enhanced text and corrections,
            or None if enhancer unavailable
        """
        enhancer = self._get_ml_enhancer()
        if not enhancer:
            return None

        try:
            return enhancer.enhance(text, context)
        except Exception as e:
            logger.warning(f"ML enhancement failed: {e}")
            return None

    def learn_template(
        self,
        invoice_data: Dict[str, Any],
        layout: Optional[Any] = None,
        ocr_result: Optional[Any] = None
    ) -> Optional[str]:
        """
        Learn template from processed invoice (Stage 6).

        Stores field locations and patterns for the vendor,
        enabling improved extraction on future documents.

        Args:
            invoice_data: Successfully extracted invoice data
            layout: Optional layout analysis result
            ocr_result: Optional OCR result

        Returns:
            Template ID if learning successful, None otherwise
        """
        learner = self._get_template_learner()
        if not learner:
            return None

        try:
            return learner.learn_from_document(
                invoice_data,
                layout=layout,
                ocr_result=ocr_result
            )
        except Exception as e:
            logger.warning(f"Template learning failed: {e}")
            return None

    def get_template_hints(
        self,
        invoice_data: Dict[str, Any],
        ocr_result: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get extraction hints from matching template (Stage 6).

        Searches for a matching template and returns hints
        to improve field extraction.

        Args:
            invoice_data: Partial invoice data for matching
            ocr_result: Optional OCR result

        Returns:
            Dictionary of field hints, or None if no match
        """
        learner = self._get_template_learner()
        if not learner:
            return None

        try:
            match = learner.find_matching_template(invoice_data, ocr_result)
            if match.template and match.match_score > 0.5:
                return {
                    "template_id": match.template.template_id,
                    "vendor_name": match.template.vendor_name,
                    "match_score": match.match_score,
                    "hints": match.hints,
                    "confidence_boost": match.confidence_boost,
                }
            return None
        except Exception as e:
            logger.warning(f"Template matching failed: {e}")
            return None

    def get_template_stats(self) -> Dict[str, Any]:
        """
        Get statistics about learned templates (Stage 6).

        Returns:
            Dictionary with template statistics
        """
        learner = self._get_template_learner()
        if not learner:
            return {"count": 0, "available": False}

        try:
            stats = learner.get_template_stats()
            stats["available"] = True
            return stats
        except Exception as e:
            logger.warning(f"Failed to get template stats: {e}")
            return {"count": 0, "available": False}

    def process_invoice(
        self,
        file_path: str,
        output_format: str = "markdown",
        lang: str = "ar",
        validate: bool = True,
        score_confidence_flag: bool = True,
        learn_template_flag: bool = True
    ) -> Dict[str, Any]:
        """
        Process an invoice image/PDF with full Stage 1-6 pipeline.

        Convenience method that combines OCR, structure analysis,
        output formatting, validation, confidence scoring, and
        template learning.

        Args:
            file_path: Path to invoice image or PDF
            output_format: "markdown", "json", "erp", "zatca", or "raw"
            lang: Language code (default "ar" for Arabic)
            validate: If True, run invoice validation (Stage 5)
            score_confidence_flag: If True, calculate confidence scores (Stage 5)
            learn_template_flag: If True, learn template from successful extraction (Stage 6)

        Returns:
            Dictionary with:
            - success: bool
            - formatted_output: Formatted string (markdown or JSON)
            - invoice_document: InvoiceDocument dataclass (if available)
            - raw_data: Raw extracted data
            - metadata: Processing metadata
            - validation: ValidationResult (if validate=True)
            - confidence: DocumentConfidence (if score_confidence_flag=True)
            - template_id: Template ID if learned (if learn_template_flag=True)
        """
        result = {
            'success': False,
            'formatted_output': '',
            'invoice_document': None,
            'raw_data': {},
            'metadata': {},
            'validation': None,
            'confidence': None,
            'template_id': None
        }

        # Process file with OCR
        ext = os.path.splitext(file_path)[1].lower()
        options = {'enable_structure_analysis': True}

        if ext == '.pdf':
            ocr_result = self.process_pdf(file_path, lang, options=options)
        else:
            ocr_result = self.process_image(file_path, lang, options=options)

        if not ocr_result.success:
            result['error'] = ocr_result.error
            return result

        # Build extracted data structure
        extracted_data = self._build_extracted_data(ocr_result, file_path)
        result['raw_data'] = extracted_data
        result['metadata'] = ocr_result.metadata or {}

        # Create InvoiceDocument
        invoice_doc = self.create_invoice_document(extracted_data)
        if invoice_doc:
            result['invoice_document'] = invoice_doc

        # Stage 5: Validation
        validation_result = None
        if validate:
            validation_result = self.validate_invoice(extracted_data)
            if validation_result:
                result['validation'] = validation_result
                result['metadata']['validation_score'] = validation_result.validation_score
                result['metadata']['validation_passed'] = validation_result.is_valid

        # Stage 5: Confidence Scoring
        if score_confidence_flag:
            # Collect OCR blocks for confidence calculation
            ocr_blocks = []
            if ocr_result.pages:
                for page in ocr_result.pages:
                    for block in page.text_blocks:
                        ocr_blocks.append({
                            'text': block.text,
                            'confidence': block.confidence,
                            'bbox': block.bbox
                        })

            confidence_result = self.score_confidence(
                extracted_data,
                ocr_blocks=ocr_blocks,
                validation_result=validation_result,
                layout_info=result['metadata'].get('layout')
            )
            if confidence_result:
                result['confidence'] = confidence_result
                result['metadata']['overall_confidence'] = confidence_result.overall
                result['metadata']['confidence_level'] = confidence_result.level.value
                result['metadata']['recommendations'] = confidence_result.recommendations

        # Format output
        if output_format == "markdown":
            result['formatted_output'] = self.format_as_markdown(extracted_data)
        elif output_format == "json":
            result['formatted_output'] = self.format_as_json(extracted_data)
        elif output_format == "erp":
            result['formatted_output'] = self.format_as_json(extracted_data, erp_format=True)
        elif output_format == "zatca":
            result['formatted_output'] = self.format_as_json(extracted_data, zatca_format=True)
        else:  # raw
            import json
            result['formatted_output'] = json.dumps(extracted_data, ensure_ascii=False, indent=2)

        # Stage 6: Template Learning
        if learn_template_flag:
            template_id = self.learn_template(
                extracted_data,
                layout=result['metadata'].get('layout'),
                ocr_result=ocr_result
            )
            if template_id:
                result['template_id'] = template_id
                result['metadata']['template_learned'] = True

        result['success'] = True
        return result

    def _build_extracted_data(
        self,
        ocr_result: ReadResult,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Build structured extracted data from OCR result.

        Combines OCR text with metadata for formatting.

        Args:
            ocr_result: ReadResult from OCR processing
            file_path: Source file path

        Returns:
            Structured data dictionary
        """
        extracted_data = {
            'document_type': 'Invoice',
            'document_type_ar': 'فاتورة',
            'full_text': ocr_result.full_text,
            'raw_text': ocr_result.full_text,
            'source_file': file_path,
            'processing_time_ms': ocr_result.processing_time_ms,
            'avg_confidence': ocr_result.metadata.get('avg_confidence', 0.0) if ocr_result.metadata else 0.0,
        }

        # Add structure metadata if available
        if ocr_result.metadata:
            if 'layout' in ocr_result.metadata:
                extracted_data['layout'] = ocr_result.metadata['layout']
            if 'tables' in ocr_result.metadata:
                extracted_data['num_tables'] = ocr_result.metadata['tables']
            if 'line_items' in ocr_result.metadata:
                # Try to get actual line items if available
                pass  # Line items would come from table recognition

        return extracted_data

    def _simple_text_format(self, extracted_data: Dict[str, Any]) -> str:
        """Simple fallback text format when formatter unavailable."""
        lines = []
        doc_type = extracted_data.get('document_type', 'Document')
        doc_type_ar = extracted_data.get('document_type_ar', 'مستند')
        lines.append(f"# {doc_type} ({doc_type_ar})")
        lines.append("")

        if text := extracted_data.get('full_text'):
            lines.append(text)
            lines.append("")

        return '\n'.join(lines)

    def get_text_only(self, file_path: str, lang: str = "en") -> str:
        """
        Convenience method to get just the extracted text as a string.

        Args:
            file_path: Path to image or PDF file
            lang: Language code

        Returns:
            Extracted text as a single string
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            result = self.process_pdf(file_path, lang)
        else:
            result = self.process_image(file_path, lang)

        if result.success:
            return result.full_text
        else:
            raise EngineProcessingError(
                result.error or "OCR processing failed",
                engine=self.name
            )
