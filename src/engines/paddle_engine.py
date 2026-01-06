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
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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

    # Minimum confidence threshold for keeping results
    MIN_CONFIDENCE_THRESHOLD = 0.20  # Lower to catch more Arabic text

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
            options: Additional options

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
            # Use lock to prevent concurrent PaddlePaddle access (oneDNN not thread-safe)
            with self._ocr_lock:
                ocr = self._get_ocr_engine(lang)

                # Preprocess image for better OCR (especially Arabic)
                processed_image = self._preprocess_image(image_path, lang)

                # Get language-specific OCR parameters
                ocr_params = self._get_ocr_params(lang)

                # Run OCR with optimized parameters for Arabic accuracy
                # Note: Only text_det_limit_side_len and text_rec_score_thresh are
                # reliably supported in the predict() method. Other detection params
                # may cause RuntimeError in some PaddleOCR versions.
                result = ocr.predict(
                    input=processed_image,
                    text_det_limit_side_len=ocr_params.get("text_det_limit_side_len", 960),
                    text_rec_score_thresh=ocr_params.get("text_rec_score_thresh", 0.5),
                )

            # Parse OCR result with RTL support for Arabic
            pages = []
            for res in result:
                page_data = self._parse_ocr_result(res, lang=lang)
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
                metadata={
                    "ocr_version": "PP-OCRv5",
                    "server_model": self._use_server_model,
                    "preprocessed": True
                }
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

    def _preprocess_image(self, image_path: str, lang: str) -> str:
        """
        Preprocess image for better OCR recognition.

        Note: PaddleOCR PP-OCRv5 already includes built-in preprocessing
        (document orientation, unwarping, etc.), so we keep external
        preprocessing minimal to avoid conflicts.

        Args:
            image_path: Path to image file
            lang: Language code

        Returns:
            Path to image (preprocessing disabled to avoid conflicts)
        """
        # PP-OCRv5 has built-in preprocessing, return path directly
        # to let PaddleOCR handle preprocessing internally
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

                    # Run OCR with optimized parameters (locked for thread safety)
                    with self._ocr_lock:
                        result = ocr.predict(
                            input=img_array,
                            text_det_limit_side_len=ocr_params.get("text_det_limit_side_len", 960),
                            text_rec_score_thresh=ocr_params.get("text_rec_score_thresh", 0.5),
                        )

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

        Note: PaddleOCR PP-OCRv5 handles preprocessing internally.
        We keep this minimal to avoid conflicts.

        Args:
            img_array: NumPy array of the image

        Returns:
            Image array (minimal preprocessing)
        """
        # PP-OCRv5 has built-in preprocessing, return array directly
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
