"""
ERP Arabic OCR Microservice - Multi-Engine OCR Service
=======================================================
Implements multi-engine OCR processing with PaddleOCR, EasyOCR, and Tesseract.
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image

# Set environment variables before importing paddle
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from . import (
    OCREngine,
    OCRResult,
    TextBlock,
    BoundingBox,
    FusionResult,
    CorrectionResult,
    ProcessingResult,
    DocumentType
)
from ..utils.arabic_utils import advanced_arabic_ocr_correction
from config.settings import get_settings, EngineMode

logger = logging.getLogger(__name__)


class MultiEngineArabicOCR:
    """
    Multi-engine Arabic OCR service.

    Supports:
    - PaddleOCR (PP-OCRv5) - Primary engine for Arabic
    - EasyOCR - Secondary engine for fusion
    - Tesseract - Fallback engine

    Features:
    - Concurrent multi-engine processing
    - Confidence-weighted result fusion
    - Arabic text correction pipeline
    - Configurable engine modes
    """

    # Thread lock for thread-safe OCR operations
    _ocr_lock = threading.Lock()

    def __init__(
        self,
        engine_mode: Optional[EngineMode] = None,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False
    ):
        """
        Initialize multi-engine OCR service.

        Args:
            engine_mode: OCR engine mode (paddle_only, easyocr_only, multi_engine, fusion)
            languages: List of languages to detect (default: ['ar', 'en'])
            use_gpu: Enable GPU acceleration
        """
        settings = get_settings()

        self.engine_mode = engine_mode or settings.ocr.engine_mode
        self.languages = languages or settings.ocr.languages
        self.use_gpu = use_gpu or settings.ocr.paddle_use_gpu

        # Engine instances (lazy initialization)
        self._paddle_ocr = None
        self._easyocr_reader = None
        self._tesseract_available = False

        # Initialize engines based on mode
        self._init_engines()

        logger.info(
            f"MultiEngineArabicOCR initialized: mode={self.engine_mode.value}, "
            f"languages={self.languages}, gpu={self.use_gpu}"
        )

    def _init_engines(self) -> None:
        """Initialize OCR engines based on configuration."""
        mode = self.engine_mode

        if mode in [EngineMode.PADDLE_ONLY, EngineMode.MULTI_ENGINE, EngineMode.FUSION]:
            self._init_paddle_ocr()

        if mode in [EngineMode.EASYOCR_ONLY, EngineMode.MULTI_ENGINE, EngineMode.FUSION]:
            self._init_easyocr()

        if mode in [EngineMode.MULTI_ENGINE, EngineMode.FUSION]:
            self._init_tesseract()

    def _init_paddle_ocr(self) -> None:
        """Initialize PaddleOCR engine for Arabic."""
        try:
            from paddleocr import PaddleOCR

            settings = get_settings()

            # Determine language for PaddleOCR
            lang = "ar" if "ar" in self.languages else "en"

            self._paddle_ocr = PaddleOCR(
                lang=lang,
                use_angle_cls=settings.ocr.paddle_use_angle_cls,
                use_gpu=self.use_gpu,
                show_log=False,
                # Arabic-optimized parameters
                det_limit_side_len=1280,
                rec_score_thresh=0.25,
            )

            logger.info(f"PaddleOCR initialized successfully (lang={lang})")

        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            self._paddle_ocr = None

    def _init_easyocr(self) -> None:
        """Initialize EasyOCR engine for Arabic+English."""
        try:
            import easyocr

            settings = get_settings()

            # EasyOCR language codes
            easyocr_langs = []
            if "ar" in self.languages:
                easyocr_langs.append("ar")
            if "en" in self.languages:
                easyocr_langs.append("en")

            if not easyocr_langs:
                easyocr_langs = ["ar", "en"]

            self._easyocr_reader = easyocr.Reader(
                easyocr_langs,
                gpu=self.use_gpu,
                verbose=False
            )

            logger.info(f"EasyOCR initialized successfully (langs={easyocr_langs})")

        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self._easyocr_reader = None

    def _init_tesseract(self) -> None:
        """Initialize Tesseract as fallback engine."""
        try:
            import pytesseract

            # Test if Tesseract is available
            pytesseract.get_tesseract_version()
            self._tesseract_available = True

            logger.info("Tesseract initialized successfully")

        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            self._tesseract_available = False

    def process_image(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        apply_correction: bool = True,
        extract_blocks: bool = True
    ) -> OCRResult:
        """
        Process image with configured OCR engine(s).

        Args:
            image: Image path, numpy array, or PIL Image
            apply_correction: Apply Arabic text correction
            extract_blocks: Extract individual text blocks

        Returns:
            OCRResult with extracted text and confidence
        """
        start_time = time.time()

        # Load image if path provided
        if isinstance(image, (str, Path)):
            image_array = self._load_image(image)
        elif isinstance(image, Image.Image):
            image_array = np.array(image)
        else:
            image_array = image

        # Process based on engine mode
        mode = self.engine_mode

        if mode == EngineMode.PADDLE_ONLY:
            result = self._run_paddle(image_array, extract_blocks)
        elif mode == EngineMode.EASYOCR_ONLY:
            result = self._run_easyocr(image_array, extract_blocks)
        elif mode == EngineMode.MULTI_ENGINE:
            result = self._run_multi_engine(image_array, extract_blocks)
        elif mode == EngineMode.FUSION:
            result = self._run_fusion(image_array, extract_blocks)
        else:
            result = self._run_paddle(image_array, extract_blocks)

        # Apply Arabic text correction
        if apply_correction and result.text:
            corrected_text = advanced_arabic_ocr_correction(result.text)
            result = OCRResult(
                text=corrected_text,
                confidence=result.confidence,
                engine=result.engine,
                blocks=result.blocks,
                raw_text=result.text,
                processing_time_ms=result.processing_time_ms,
                language_detected=result.language_detected,
                metadata=result.metadata
            )

        # Update processing time
        processing_time_ms = (time.time() - start_time) * 1000
        result.processing_time_ms = processing_time_ms

        return result

    def _load_image(self, image_path: Union[str, Path]) -> np.ndarray:
        """Load image from path."""
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return np.array(image)

    def _run_paddle(
        self,
        image: np.ndarray,
        extract_blocks: bool = True
    ) -> OCRResult:
        """
        Run PaddleOCR on image.

        Args:
            image: Image as numpy array
            extract_blocks: Extract individual text blocks

        Returns:
            OCRResult from PaddleOCR
        """
        if self._paddle_ocr is None:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.PADDLE,
                metadata={"error": "PaddleOCR not initialized"}
            )

        start_time = time.time()

        try:
            with self._ocr_lock:
                result = self._paddle_ocr.ocr(image, cls=True)

            if not result or not result[0]:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    engine=OCREngine.PADDLE,
                    processing_time_ms=(time.time() - start_time) * 1000
                )

            # Extract text and confidence
            texts = []
            confidences = []
            blocks = []

            for line in result[0]:
                if line and len(line) >= 2:
                    box_points = line[0]
                    text_data = line[1]

                    text = text_data[0] if isinstance(text_data, tuple) else str(text_data)
                    confidence = float(text_data[1]) if isinstance(text_data, tuple) and len(text_data) > 1 else 0.5

                    texts.append(text)
                    confidences.append(confidence)

                    if extract_blocks:
                        bbox = BoundingBox.from_points(box_points)
                        blocks.append(TextBlock(
                            text=text,
                            confidence=confidence,
                            bbox=bbox,
                            language=self._detect_language(text)
                        ))

            # Combine text (RTL order for Arabic)
            combined_text = self._combine_text_rtl(texts, blocks)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                engine=OCREngine.PADDLE,
                blocks=blocks,
                processing_time_ms=(time.time() - start_time) * 1000,
                language_detected="ar" if self._is_arabic(combined_text) else "en",
                metadata={"line_count": len(texts)}
            )

        except Exception as e:
            logger.error(f"PaddleOCR processing error: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.PADDLE,
                metadata={"error": str(e)},
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _run_easyocr(
        self,
        image: np.ndarray,
        extract_blocks: bool = True
    ) -> OCRResult:
        """
        Run EasyOCR on image.

        Args:
            image: Image as numpy array
            extract_blocks: Extract individual text blocks

        Returns:
            OCRResult from EasyOCR
        """
        if self._easyocr_reader is None:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.EASYOCR,
                metadata={"error": "EasyOCR not initialized"}
            )

        start_time = time.time()

        try:
            result = self._easyocr_reader.readtext(image)

            if not result:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    engine=OCREngine.EASYOCR,
                    processing_time_ms=(time.time() - start_time) * 1000
                )

            texts = []
            confidences = []
            blocks = []

            for detection in result:
                box_points = detection[0]
                text = detection[1]
                confidence = float(detection[2])

                texts.append(text)
                confidences.append(confidence)

                if extract_blocks:
                    bbox = BoundingBox.from_points(box_points)
                    blocks.append(TextBlock(
                        text=text,
                        confidence=confidence,
                        bbox=bbox,
                        language=self._detect_language(text)
                    ))

            combined_text = self._combine_text_rtl(texts, blocks)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                engine=OCREngine.EASYOCR,
                blocks=blocks,
                processing_time_ms=(time.time() - start_time) * 1000,
                language_detected="ar" if self._is_arabic(combined_text) else "en",
                metadata={"detection_count": len(result)}
            )

        except Exception as e:
            logger.error(f"EasyOCR processing error: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.EASYOCR,
                metadata={"error": str(e)},
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _run_tesseract(
        self,
        image: np.ndarray,
        extract_blocks: bool = True
    ) -> OCRResult:
        """
        Run Tesseract OCR on image (fallback).

        Args:
            image: Image as numpy array
            extract_blocks: Extract individual text blocks

        Returns:
            OCRResult from Tesseract
        """
        if not self._tesseract_available:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.TESSERACT,
                metadata={"error": "Tesseract not available"}
            )

        start_time = time.time()

        try:
            import pytesseract

            # Configure Tesseract for Arabic
            lang = "ara+eng" if "ar" in self.languages else "eng"
            config = "--oem 3 --psm 6"

            # Get text with confidence data
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )

            texts = []
            confidences = []
            blocks = []

            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])

                if text and conf > 0:
                    texts.append(text)
                    confidences.append(conf / 100.0)

                    if extract_blocks:
                        bbox = BoundingBox(
                            x1=float(data['left'][i]),
                            y1=float(data['top'][i]),
                            x2=float(data['left'][i] + data['width'][i]),
                            y2=float(data['top'][i] + data['height'][i])
                        )
                        blocks.append(TextBlock(
                            text=text,
                            confidence=conf / 100.0,
                            bbox=bbox,
                            language=self._detect_language(text)
                        ))

            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                engine=OCREngine.TESSERACT,
                blocks=blocks,
                processing_time_ms=(time.time() - start_time) * 1000,
                language_detected="ar" if self._is_arabic(combined_text) else "en",
                metadata={"word_count": len(texts)}
            )

        except Exception as e:
            logger.error(f"Tesseract processing error: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.TESSERACT,
                metadata={"error": str(e)},
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _run_multi_engine(
        self,
        image: np.ndarray,
        extract_blocks: bool = True
    ) -> OCRResult:
        """
        Run multiple engines and return the best result.

        Args:
            image: Image as numpy array
            extract_blocks: Extract individual text blocks

        Returns:
            OCRResult with highest confidence
        """
        results = []

        # Run engines in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            if self._paddle_ocr:
                futures[executor.submit(self._run_paddle, image, extract_blocks)] = "paddle"
            if self._easyocr_reader:
                futures[executor.submit(self._run_easyocr, image, extract_blocks)] = "easyocr"
            if self._tesseract_available:
                futures[executor.submit(self._run_tesseract, image, extract_blocks)] = "tesseract"

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.text:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Engine {futures[future]} failed: {e}")

        if not results:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.PADDLE,
                metadata={"error": "All engines failed"}
            )

        # Return best result by confidence
        best_result = max(results, key=lambda r: r.confidence)
        return best_result

    def _run_fusion(
        self,
        image: np.ndarray,
        extract_blocks: bool = True
    ) -> OCRResult:
        """
        Run engines and fuse results for best accuracy.

        Uses confidence-weighted fusion algorithm.

        Args:
            image: Image as numpy array
            extract_blocks: Extract individual text blocks

        Returns:
            OCRResult with fused text
        """
        # Import fusion engine here to avoid circular import
        from .fusion_engine import FusionEngine

        results = []

        # Run engines
        if self._paddle_ocr:
            results.append(self._run_paddle(image, extract_blocks))
        if self._easyocr_reader:
            results.append(self._run_easyocr(image, extract_blocks))

        # Filter out empty results
        results = [r for r in results if r.text.strip()]

        if not results:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=OCREngine.FUSED,
                metadata={"error": "All engines returned empty"}
            )

        if len(results) == 1:
            return results[0]

        # Fuse results
        fusion_engine = FusionEngine()
        fusion_result = fusion_engine.fuse_results(results)

        return OCRResult(
            text=fusion_result.fused_text,
            confidence=fusion_result.confidence,
            engine=OCREngine.FUSED,
            blocks=results[0].blocks if results else [],
            processing_time_ms=sum(r.processing_time_ms for r in results),
            language_detected="ar" if self._is_arabic(fusion_result.fused_text) else "en",
            metadata={
                "engines_used": fusion_result.engines_used,
                "fusion_strategy": fusion_result.strategy.value,
                "improvement_score": fusion_result.improvement_score
            }
        )

    def _combine_text_rtl(
        self,
        texts: List[str],
        blocks: List[TextBlock]
    ) -> str:
        """
        Combine text blocks respecting RTL order for Arabic.

        Args:
            texts: List of text strings
            blocks: List of text blocks with positions

        Returns:
            Combined text in correct reading order
        """
        if not texts:
            return ""

        if not blocks or len(blocks) != len(texts):
            return "\n".join(texts)

        # Sort blocks by vertical position, then horizontal (RTL)
        indexed_blocks = list(zip(blocks, texts))

        # Group by approximate vertical position (lines)
        line_height_threshold = 20  # pixels
        lines = []
        current_line = []
        current_y = None

        # Sort by y position first
        indexed_blocks.sort(key=lambda x: x[0].bbox.y1 if x[0].bbox else 0)

        for block, text in indexed_blocks:
            if block.bbox is None:
                current_line.append(text)
                continue

            y = block.bbox.y1

            if current_y is None:
                current_y = y
                current_line = [(block, text)]
            elif abs(y - current_y) < line_height_threshold:
                current_line.append((block, text))
            else:
                # New line
                if current_line:
                    lines.append(current_line)
                current_line = [(block, text)]
                current_y = y

        if current_line:
            lines.append(current_line)

        # Sort each line RTL (by x position, descending for Arabic)
        result_lines = []
        for line in lines:
            if isinstance(line[0], tuple):
                # Sort by x position (RTL for Arabic)
                line.sort(key=lambda x: x[0].bbox.x1 if x[0].bbox else 0, reverse=True)
                result_lines.append(" ".join(t for _, t in line))
            else:
                result_lines.append(" ".join(line))

        return "\n".join(result_lines)

    def _detect_language(self, text: str) -> str:
        """Detect if text is Arabic or English."""
        if not text:
            return "en"
        return "ar" if self._is_arabic(text) else "en"

    def _is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        return arabic_chars > len(text) * 0.3

    def get_engine_status(self) -> Dict[str, Any]:
        """Get status of all engines."""
        return {
            "paddle": {
                "available": self._paddle_ocr is not None,
                "gpu": self.use_gpu
            },
            "easyocr": {
                "available": self._easyocr_reader is not None,
                "gpu": self.use_gpu
            },
            "tesseract": {
                "available": self._tesseract_available
            },
            "engine_mode": self.engine_mode.value,
            "languages": self.languages
        }
