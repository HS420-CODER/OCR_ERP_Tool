"""
Tesseract OCR Engine implementation.

Provides OCR functionality using Tesseract (pytesseract).
Supports English and Arabic text extraction from images and PDFs.
Acts as fallback when PaddleOCR is not available.
"""

import os
import time
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base_engine import (
    BaseEngine,
    EngineCapabilities,
    EngineNotAvailableError,
    EngineProcessingError,
    LanguageNotSupportedError
)
from ..models import ReadResult, PageResult, TextBlock

logger = logging.getLogger(__name__)


class TesseractEngine(BaseEngine):
    """
    Tesseract OCR-based engine.

    Features:
    - Text extraction using Tesseract OCR
    - English and Arabic language support
    - PDF processing via PyMuPDF
    - Windows path auto-detection
    - Fallback engine when PaddleOCR is unavailable

    Requires:
    - Tesseract OCR installed on system
    - pytesseract Python package
    - Language data files for desired languages
    """

    # Supported languages
    SUPPORTED_LANGUAGES = ["en", "ar"]

    # Language code mapping (internal -> Tesseract)
    LANG_MAP = {
        "en": "eng",
        "eng": "eng",
        "english": "eng",
        "ar": "ara",
        "ara": "ara",
        "arabic": "ara",
    }

    # Common Tesseract installation paths on Windows
    WINDOWS_TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
    ]

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize Tesseract engine.

        Args:
            tesseract_cmd: Custom path to tesseract executable (auto-detects if None)
        """
        self._tesseract_cmd = tesseract_cmd
        self._available: Optional[bool] = None
        self._pytesseract = None
        self._setup_tesseract_path()

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def display_name(self) -> str:
        return "Tesseract OCR"

    def _setup_tesseract_path(self) -> None:
        """Configure Tesseract executable path for the system."""
        try:
            import pytesseract

            # If custom path provided, use it
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
                self._pytesseract = pytesseract
                return

            # Check if already in PATH
            if shutil.which("tesseract"):
                self._pytesseract = pytesseract
                return

            # On Windows, check common installation locations
            if os.name == 'nt':
                for path in self.WINDOWS_TESSERACT_PATHS:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        self._pytesseract = pytesseract
                        logger.info(f"Found Tesseract at: {path}")
                        return

            # Fallback - let pytesseract try to find it
            self._pytesseract = pytesseract

        except ImportError:
            logger.warning("pytesseract is not installed")
            self._pytesseract = None

    def _normalize_lang(self, lang: str) -> str:
        """Normalize language code to Tesseract format."""
        lang_lower = lang.lower()
        return self.LANG_MAP.get(lang_lower, lang_lower)

    def is_available(self) -> bool:
        """Check if Tesseract is installed and working."""
        if self._available is not None:
            return self._available

        if self._pytesseract is None:
            self._available = False
            return False

        try:
            # Try to get tesseract version
            version = self._pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
            self._available = True
            return True
        except Exception as e:
            logger.warning(f"Tesseract is not available: {e}")
            self._available = False
            return False

    def get_capabilities(self) -> EngineCapabilities:
        """Get Tesseract capabilities."""
        return EngineCapabilities(
            supports_images=True,
            supports_pdf=True,
            supports_vision_analysis=False,
            supports_gpu=False,
            supported_languages=self.SUPPORTED_LANGUAGES.copy(),
            max_file_size_mb=50,
            supports_batch=False,
            supports_streaming=False,
            supports_tables=False,
            supports_structure=False
        )

    def get_installed_languages(self) -> List[str]:
        """
        Get list of installed Tesseract language packs.

        Returns:
            List of installed language codes (e.g., ['eng', 'ara'])
        """
        if not self.is_available():
            return []

        try:
            langs = self._pytesseract.get_languages()
            return langs
        except Exception as e:
            logger.warning(f"Failed to get installed languages: {e}")
            return []

    def _check_language_installed(self, lang: str) -> bool:
        """Check if a language pack is installed."""
        tesseract_lang = self._normalize_lang(lang)
        installed = self.get_installed_languages()
        return tesseract_lang in installed

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
            options: Additional options:
                - config: Custom Tesseract config string
                - psm: Page segmentation mode (0-13)
                - oem: OCR Engine Mode (0-3)

        Returns:
            ReadResult with extracted text
        """
        start_time = time.perf_counter()
        tesseract_lang = self._normalize_lang(lang)

        # Check availability
        if not self.is_available():
            return self._create_error_result(
                image_path,
                "Tesseract OCR is not installed or not available",
                "image"
            )

        # Validate file exists
        if not os.path.exists(image_path):
            return self._create_error_result(
                image_path,
                f"Image not found: {image_path}",
                "image"
            )

        # Check language support
        if lang not in self.SUPPORTED_LANGUAGES:
            return self._create_error_result(
                image_path,
                f"Language '{lang}' is not supported. Use one of: {self.SUPPORTED_LANGUAGES}",
                "image"
            )

        # Check if language pack is installed
        if not self._check_language_installed(lang):
            return self._create_error_result(
                image_path,
                f"Tesseract language pack '{tesseract_lang}' is not installed. "
                f"Install it using: scripts/install_tesseract.py --lang {lang}",
                "image"
            )

        try:
            from PIL import Image

            # Build config string
            config = self._build_config(options)

            # Open and process image
            img = Image.open(image_path)

            # Get text with detailed data
            data = self._pytesseract.image_to_data(
                img,
                lang=tesseract_lang,
                config=config,
                output_type=self._pytesseract.Output.DICT
            )

            # Parse results
            text_blocks, full_text = self._parse_tesseract_data(data)

            pages = [PageResult(
                page_number=1,
                text_blocks=text_blocks,
                full_text=full_text,
                width=img.width,
                height=img.height
            )]

            processing_time = (time.perf_counter() - start_time) * 1000

            return self._create_success_result(
                file_path=image_path,
                file_type="image",
                pages=pages,
                language=lang,
                processing_time_ms=processing_time,
                metadata={
                    "tesseract_lang": tesseract_lang,
                    "config": config,
                    "word_count": len([b for b in text_blocks if b.text.strip()])
                }
            )

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
        tesseract_lang = self._normalize_lang(lang)

        # Check availability
        if not self.is_available():
            return self._create_error_result(
                pdf_path,
                "Tesseract OCR is not installed or not available",
                "pdf"
            )

        # Validate file exists
        if not os.path.exists(pdf_path):
            return self._create_error_result(
                pdf_path,
                f"PDF not found: {pdf_path}",
                "pdf"
            )

        # Check language support
        if lang not in self.SUPPORTED_LANGUAGES:
            return self._create_error_result(
                pdf_path,
                f"Language '{lang}' is not supported. Use one of: {self.SUPPORTED_LANGUAGES}",
                "pdf"
            )

        # Check if language pack is installed
        if not self._check_language_installed(lang):
            return self._create_error_result(
                pdf_path,
                f"Tesseract language pack '{tesseract_lang}' is not installed",
                "pdf"
            )

        try:
            import fitz  # PyMuPDF
            from PIL import Image
            import io

            config = self._build_config(options)
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
                    if pm.width > 3000 or pm.height > 3000:
                        pm = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)

                    # Convert to PIL Image
                    img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)

                    # Run OCR
                    data = self._pytesseract.image_to_data(
                        img,
                        lang=tesseract_lang,
                        config=config,
                        output_type=self._pytesseract.Output.DICT
                    )

                    text_blocks, full_text = self._parse_tesseract_data(data)

                    pages.append(PageResult(
                        page_number=page_num + 1,
                        text_blocks=text_blocks,
                        full_text=full_text,
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
                    "tesseract_lang": tesseract_lang
                }
            )

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

    def _build_config(self, options: Optional[Dict[str, Any]] = None) -> str:
        """
        Build Tesseract config string from options.

        Args:
            options: Dictionary with config options

        Returns:
            Tesseract config string
        """
        options = options or {}
        config_parts = []

        # Page segmentation mode
        psm = options.get('psm', 3)  # Default: Fully automatic page segmentation
        config_parts.append(f'--psm {psm}')

        # OCR Engine Mode
        oem = options.get('oem', 3)  # Default: Default, based on what is available
        config_parts.append(f'--oem {oem}')

        # Custom config
        if 'config' in options:
            config_parts.append(options['config'])

        return ' '.join(config_parts)

    def _parse_tesseract_data(self, data: Dict) -> tuple:
        """
        Parse Tesseract output data into TextBlocks.

        Args:
            data: Dictionary from image_to_data

        Returns:
            Tuple of (text_blocks, full_text)
        """
        text_blocks = []
        lines = {}  # Group words by line number

        n_boxes = len(data['text'])

        for i in range(n_boxes):
            text = data['text'][i]
            conf = data['conf'][i]

            # Skip empty or low confidence
            if not text.strip() or conf == -1:
                continue

            # Get bounding box
            x, y, w, h = (
                data['left'][i],
                data['top'][i],
                data['width'][i],
                data['height'][i]
            )

            # Convert confidence to 0-1 scale
            confidence = float(conf) / 100.0 if conf > 0 else 0.0

            # Group by line
            line_num = data['line_num'][i]
            block_num = data['block_num'][i]
            line_key = (block_num, line_num)

            if line_key not in lines:
                lines[line_key] = {
                    'words': [],
                    'confidence_sum': 0,
                    'count': 0,
                    'bbox': [x, y, x + w, y + h]
                }

            lines[line_key]['words'].append(text)
            lines[line_key]['confidence_sum'] += confidence
            lines[line_key]['count'] += 1

            # Expand bounding box
            lines[line_key]['bbox'][0] = min(lines[line_key]['bbox'][0], x)
            lines[line_key]['bbox'][1] = min(lines[line_key]['bbox'][1], y)
            lines[line_key]['bbox'][2] = max(lines[line_key]['bbox'][2], x + w)
            lines[line_key]['bbox'][3] = max(lines[line_key]['bbox'][3], y + h)

        # Convert lines to TextBlocks
        full_text_lines = []
        for line_key in sorted(lines.keys()):
            line_data = lines[line_key]
            line_text = ' '.join(line_data['words'])
            avg_confidence = line_data['confidence_sum'] / line_data['count']

            bbox = line_data['bbox']
            bbox_polygon = [
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]]
            ]

            text_blocks.append(TextBlock(
                text=line_text,
                confidence=round(avg_confidence, 4),
                bbox=bbox_polygon
            ))
            full_text_lines.append(line_text)

        return text_blocks, '\n'.join(full_text_lines)

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
