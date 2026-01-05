"""
PaddleOCR Engine implementation.

Provides OCR functionality using PaddleOCR (PP-OCRv5).
Supports English and Arabic text extraction from images and PDFs.
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

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


class PaddleEngine(BaseEngine):
    """
    PaddleOCR-based OCR engine.

    Features:
    - High accuracy text extraction
    - English and Arabic language support
    - PDF processing via PyMuPDF
    - GPU acceleration support
    - Text angle classification

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

    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = False,
        use_angle_cls: bool = True
    ):
        """
        Initialize PaddleOCR engine.

        Args:
            lang: Default language ("en" or "ar")
            use_gpu: Enable GPU acceleration
            use_angle_cls: Enable text angle classification
        """
        self._lang = self._normalize_lang(lang)
        self._use_gpu = use_gpu
        self._use_angle_cls = use_angle_cls
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

                logger.info(f"Initializing PaddleOCR for language: {lang}")
                self._ocr_engines[lang] = PaddleOCR(
                    use_textline_orientation=self._use_angle_cls,
                    lang=lang,
                    device='gpu' if self._use_gpu else 'cpu'
                )
            except Exception as e:
                raise EngineNotAvailableError(
                    f"Failed to initialize PaddleOCR: {e}",
                    engine=self.name
                )

        return self._ocr_engines[lang]

    def process_image(
        self,
        image_path: str,
        lang: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process an image file with OCR.

        Args:
            image_path: Path to the image file
            lang: Language code ("en" or "ar")
            options: Additional options (unused currently)

        Returns:
            ReadResult with extracted text
        """
        start_time = time.perf_counter()
        lang = self._normalize_lang(lang)

        # Validate file exists
        if not os.path.exists(image_path):
            return self._create_error_result(
                image_path,
                f"Image not found: {image_path}",
                "image"
            )

        try:
            ocr = self._get_ocr_engine(lang)
            result = ocr.predict(image_path)

            # Parse OCR result
            pages = []
            for res in result:
                page_data = self._parse_ocr_result(res)
                pages.append(PageResult(
                    page_number=1,
                    text_blocks=page_data['text_blocks'],
                    full_text=page_data['full_text']
                ))

            if not pages:
                pages.append(PageResult(
                    page_number=1,
                    text_blocks=[],
                    full_text=""
                ))

            processing_time = (time.perf_counter() - start_time) * 1000

            return self._create_success_result(
                file_path=image_path,
                file_type="image",
                pages=pages,
                language=lang,
                processing_time_ms=processing_time,
                metadata={"ocr_version": "PP-OCRv5"}
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

    def process_pdf(
        self,
        pdf_path: str,
        lang: str = "en",
        max_pages: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process a PDF file with OCR.

        Converts each page to an image and runs OCR.

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

            ocr = self._get_ocr_engine(lang)
            pages = []

            with fitz.open(pdf_path) as pdf:
                total_pages = pdf.page_count
                pages_to_process = min(max_pages, total_pages) if max_pages else total_pages

                for page_num in range(pages_to_process):
                    page = pdf[page_num]

                    # Convert page to image (2x scale for better OCR)
                    mat = fitz.Matrix(2, 2)
                    pm = page.get_pixmap(matrix=mat, alpha=False)

                    # Reduce scale if too large
                    if pm.width > 2000 or pm.height > 2000:
                        pm = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)

                    # Convert to numpy array for OCR
                    img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
                    img_array = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                    # Run OCR on the image
                    result = ocr.predict(img_array)

                    page_data = {
                        'text_blocks': [],
                        'full_text': ''
                    }

                    for res in result:
                        parsed = self._parse_ocr_result(res)
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
                    "ocr_version": "PP-OCRv5"
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

    def _parse_ocr_result(self, result: Any) -> Dict[str, Any]:
        """
        Parse OCR result into structured format.

        Handles both new API format (dict-like with rec_texts) and
        legacy format (list of [bbox, (text, score)]).

        Args:
            result: Raw OCR result from PaddleOCR

        Returns:
            Dictionary with 'text_blocks' and 'full_text'
        """
        text_blocks = []
        full_text_lines = []

        # New API format: dict-like object with rec_texts, rec_scores, dt_polys
        if hasattr(result, 'keys'):
            texts = result.get('rec_texts', []) or []
            scores = result.get('rec_scores', []) or []
            polys = result.get('dt_polys', []) or []

            for i, text in enumerate(texts):
                if not text.strip():
                    continue

                score = scores[i] if i < len(scores) else 0.0
                bbox = None
                if i < len(polys) and hasattr(polys[i], 'tolist'):
                    bbox = polys[i].tolist()
                elif i < len(polys):
                    bbox = list(polys[i])

                text_blocks.append(TextBlock(
                    text=text,
                    confidence=round(float(score), 4),
                    bbox=bbox
                ))
                full_text_lines.append(text)

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

                    text_blocks.append(TextBlock(
                        text=text,
                        confidence=round(float(confidence), 4),
                        bbox=bbox if isinstance(bbox, list) else None
                    ))
                    full_text_lines.append(text)

        return {
            'text_blocks': text_blocks,
            'full_text': '\n'.join(full_text_lines)
        }

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
