"""
Ollama Vision Engine implementation.

Provides vision-based document analysis using Ollama with multimodal models.
Supports context-aware OCR and document understanding for English and Arabic.
Works completely offline with local Ollama server.

Requires:
    - Ollama server running locally (default: http://localhost:11434)
    - Multimodal model (e.g., llava, bakllava, llava-llama3)
"""

import os
import time
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base_engine import (
    BaseEngine,
    EngineCapabilities,
    EngineNotAvailableError,
    EngineProcessingError
)
from ..models import ReadResult, PageResult, TextBlock

logger = logging.getLogger(__name__)


class OllamaEngine(BaseEngine):
    """
    Ollama Vision-based engine for intelligent document analysis.

    Features:
    - Context-aware vision analysis (not just OCR)
    - Custom prompt support for targeted extraction
    - English and Arabic document understanding
    - Completely offline operation
    - Support for images and PDFs

    Requires:
    - Ollama server running locally
    - Multimodal model (e.g., llava, bakllava, llava-llama3)

    Usage:
        engine = OllamaEngine()
        if engine.is_available():
            result = engine.process_image("invoice.png", lang="ar")

        # Custom prompt analysis
        result = engine.process_with_prompt(
            "document.png",
            "Extract all invoice amounts and totals"
        )
    """

    # Supported languages
    SUPPORTED_LANGUAGES = ["en", "ar"]

    # Default prompts for different use cases
    DEFAULT_OCR_PROMPT = """Extract all visible text from this image.
Preserve the original layout and structure as much as possible.
Include all text in its original language(s).
Output the text exactly as it appears."""

    DEFAULT_ARABIC_OCR_PROMPT = """Extract all visible text from this image.
This document contains Arabic text - preserve Arabic characters exactly.
Include both Arabic and English text if present.
Preserve the original layout and structure.
Output the text exactly as it appears, maintaining right-to-left order for Arabic."""

    INVOICE_ANALYSIS_PROMPT = """Analyze this invoice/document image and extract:
1. All text content (preserve Arabic and English)
2. Key fields: date, invoice number, amounts, names, addresses
3. Line items with quantities and prices
4. Total amounts and taxes
Format as structured text with clear sections."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        config: Optional[Any] = None
    ):
        """
        Initialize Ollama Vision engine.

        Args:
            host: Ollama server URL (default: http://localhost:11434)
            model: Vision model name (default: llava)
            timeout: Request timeout in seconds (default: 120)
            config: Optional ReadToolConfig to override defaults
        """
        # Set from config if provided, else use parameters, else defaults
        if config:
            self._host = getattr(config, 'ollama_host', None) or "http://localhost:11434"
            self._model = getattr(config, 'ollama_model', None) or "llava"
            self._timeout = getattr(config, 'ollama_timeout', None) or 120
        else:
            self._host = host or "http://localhost:11434"
            self._model = model or "llava"
            self._timeout = timeout or 120

        self._available: Optional[bool] = None
        self._available_models: List[str] = []

    @property
    def name(self) -> str:
        """Engine identifier name."""
        return "ollama"

    @property
    def display_name(self) -> str:
        """Human-readable engine name."""
        return "Ollama Vision"

    def is_available(self) -> bool:
        """
        Check if Ollama server is running and accessible.

        Checks:
        1. Server health at /api/tags
        2. Logs available models

        Returns:
            True if Ollama server is available
        """
        if self._available is not None:
            return self._available

        try:
            import httpx

            # Check server health by listing models
            response = httpx.get(
                f"{self._host}/api/tags",
                timeout=10.0
            )

            if response.status_code != 200:
                logger.warning(f"Ollama server returned status {response.status_code}")
                self._available = False
                return False

            # Parse available models
            data = response.json()
            self._available_models = [
                model['name'].split(':')[0]  # Remove tag suffix
                for model in data.get('models', [])
            ]

            # Log available models
            if self._available_models:
                logger.info(f"Ollama available models: {self._available_models}")
            else:
                logger.warning("Ollama server running but no models installed")

            # Check if configured model is available
            model_base = self._model.split(':')[0]
            if model_base not in self._available_models and self._available_models:
                logger.warning(
                    f"Model '{self._model}' not found. "
                    f"Available: {self._available_models}. "
                    f"Model may be pulled on first use."
                )

            self._available = True
            return True

        except ImportError:
            logger.warning("httpx not installed. Run: pip install httpx")
            self._available = False
            return False
        except Exception as e:
            if "ConnectError" in str(type(e).__name__) or "Connection" in str(e):
                logger.warning(f"Cannot connect to Ollama at {self._host}")
            else:
                logger.warning(f"Ollama availability check failed: {e}")
            self._available = False
            return False

    def get_capabilities(self) -> EngineCapabilities:
        """Get Ollama Vision capabilities."""
        return EngineCapabilities(
            supports_images=True,
            supports_pdf=True,
            supports_vision_analysis=True,  # KEY: This enables vision use case
            supports_gpu=True,  # Ollama can use GPU
            supported_languages=self.SUPPORTED_LANGUAGES.copy(),
            max_file_size_mb=20,  # Vision models have context limits
            supports_batch=False,
            supports_streaming=True,  # Ollama supports streaming
            supports_tables=True,
            supports_structure=True
        )

    def supports_language(self, lang: str) -> bool:
        """Check if language is supported."""
        return lang in self.SUPPORTED_LANGUAGES

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return self.SUPPORTED_LANGUAGES.copy()

    def process_image(
        self,
        image_path: str,
        lang: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process image using Ollama vision model.

        Args:
            image_path: Path to image file
            lang: Language code ("en" or "ar")
            options: Additional options:
                - prompt: Custom prompt (overrides default)
                - model: Override model for this request
                - temperature: Model temperature (0.0-1.0)

        Returns:
            ReadResult with extracted text
        """
        start_time = time.perf_counter()
        options = options or {}

        # Validate file exists
        if not os.path.exists(image_path):
            return self._create_error_result(
                image_path,
                f"Image not found: {image_path}",
                "image"
            )

        # Check availability
        if not self.is_available():
            return self._create_error_result(
                image_path,
                f"Ollama server not available at {self._host}. "
                f"Please start Ollama: 'ollama serve'",
                "image"
            )

        # Select appropriate prompt
        prompt = options.get('prompt')
        if not prompt:
            prompt = self.DEFAULT_ARABIC_OCR_PROMPT if lang == "ar" else self.DEFAULT_OCR_PROMPT

        try:
            # Encode image to base64
            image_base64 = self._encode_image(image_path)

            # Call Ollama API
            response_text = self._generate_with_image(
                prompt=prompt,
                image_base64=image_base64,
                model=options.get('model', self._model),
                temperature=options.get('temperature', 0.1)
            )

            # Parse response into structured result
            text_blocks = [TextBlock(
                text=response_text,
                confidence=1.0,  # Vision models don't provide confidence
                bbox=None,
                page=1
            )]

            pages = [PageResult(
                page_number=1,
                text_blocks=text_blocks,
                full_text=response_text
            )]

            processing_time = (time.perf_counter() - start_time) * 1000

            return self._create_success_result(
                file_path=image_path,
                file_type="image",
                pages=pages,
                language=lang,
                processing_time_ms=processing_time,
                metadata={
                    "model": self._model,
                    "prompt_used": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "vision_analysis": True,
                    "host": self._host
                }
            )

        except EngineProcessingError:
            raise
        except EngineNotAvailableError:
            raise
        except Exception as e:
            logger.exception(f"Error processing image with Ollama: {image_path}")
            return self._create_error_result(
                image_path,
                f"Vision processing failed: {str(e)}",
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
        Process PDF by converting pages to images and analyzing each.

        Args:
            pdf_path: Path to PDF file
            lang: Language code
            max_pages: Maximum pages to process (None for all)
            options: Additional processing options

        Returns:
            ReadResult with text from all pages
        """
        start_time = time.perf_counter()
        options = options or {}

        if not os.path.exists(pdf_path):
            return self._create_error_result(
                pdf_path,
                f"PDF not found: {pdf_path}",
                "pdf"
            )

        if not self.is_available():
            return self._create_error_result(
                pdf_path,
                f"Ollama server not available at {self._host}",
                "pdf"
            )

        try:
            import fitz  # PyMuPDF

            prompt = options.get('prompt')
            if not prompt:
                prompt = self.DEFAULT_ARABIC_OCR_PROMPT if lang == "ar" else self.DEFAULT_OCR_PROMPT

            pages = []

            with fitz.open(pdf_path) as pdf:
                total_pages = pdf.page_count
                pages_to_process = min(max_pages, total_pages) if max_pages else total_pages

                for page_num in range(pages_to_process):
                    page = pdf[page_num]

                    # Convert to image at 2x scale for better OCR
                    mat = fitz.Matrix(2, 2)
                    pm = page.get_pixmap(matrix=mat, alpha=False)

                    # Get image bytes and encode to base64
                    img_bytes = pm.tobytes("png")
                    image_base64 = base64.b64encode(img_bytes).decode('utf-8')

                    # Process with Ollama
                    page_prompt = f"Page {page_num + 1} of {total_pages}:\n{prompt}"
                    response_text = self._generate_with_image(
                        prompt=page_prompt,
                        image_base64=image_base64,
                        model=options.get('model', self._model)
                    )

                    text_blocks = [TextBlock(
                        text=response_text,
                        confidence=1.0,
                        page=page_num + 1
                    )]

                    pages.append(PageResult(
                        page_number=page_num + 1,
                        text_blocks=text_blocks,
                        full_text=response_text,
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
                    "model": self._model,
                    "vision_analysis": True
                }
            )

        except ImportError:
            return self._create_error_result(
                pdf_path,
                "PyMuPDF (fitz) required for PDF processing. "
                "Install with: pip install PyMuPDF",
                "pdf"
            )
        except Exception as e:
            logger.exception(f"Error processing PDF with Ollama: {pdf_path}")
            return self._create_error_result(
                pdf_path,
                f"PDF vision processing failed: {str(e)}",
                "pdf"
            )

    def process_with_prompt(
        self,
        file_path: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process file with custom analysis prompt.

        This is the key differentiator for Ollama - allowing context-aware
        analysis beyond simple OCR.

        Args:
            file_path: Path to image or PDF
            prompt: Custom analysis prompt
            options: Additional options

        Returns:
            ReadResult with analysis

        Example:
            result = engine.process_with_prompt(
                "invoice.png",
                "Extract all line items with quantities and prices. "
                "Calculate the total. Identify any discounts applied."
            )
        """
        options = options or {}
        options['prompt'] = prompt

        # Determine file type and process
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            return self.process_pdf(file_path, "en", options=options)
        else:
            return self.process_image(file_path, "en", options=options)

    def _encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64 string.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded string
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _generate_with_image(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
        temperature: float = 0.1
    ) -> str:
        """
        Call Ollama generate API with image.

        Uses POST /api/generate endpoint with multimodal input.

        Args:
            prompt: Text prompt for analysis
            image_base64: Base64 encoded image
            model: Model to use (overrides default)
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text response

        Raises:
            EngineProcessingError: On API errors
            EngineNotAvailableError: On connection errors
        """
        import httpx

        model = model or self._model

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            response = httpx.post(
                f"{self._host}/api/generate",
                json=payload,
                timeout=self._timeout
            )

            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "Unknown error"
                raise EngineProcessingError(
                    f"Ollama API error ({response.status_code}): {error_text}",
                    engine=self.name
                )

            data = response.json()
            return data.get('response', '')

        except httpx.TimeoutException:
            raise EngineProcessingError(
                f"Ollama request timed out after {self._timeout}s. "
                f"The model may be loading or processing a large image. "
                f"Try increasing timeout or using a smaller image.",
                engine=self.name
            )
        except httpx.ConnectError:
            raise EngineNotAvailableError(
                f"Cannot connect to Ollama at {self._host}. "
                f"Please ensure Ollama is running: 'ollama serve'",
                engine=self.name
            )

    def get_available_models(self) -> List[str]:
        """
        Get list of available vision models.

        Returns:
            List of model names installed on Ollama server
        """
        if not self._available_models:
            self.is_available()  # Populates _available_models
        return self._available_models.copy()

    def _create_success_result(
        self,
        file_path: str,
        file_type: str,
        pages: List[PageResult],
        language: str,
        processing_time_ms: float,
        metadata: Dict[str, Any]
    ) -> ReadResult:
        """Create a successful ReadResult."""
        # Combine all page text
        full_text = "\n\n".join(p.full_text for p in pages if p.full_text)

        return ReadResult(
            success=True,
            file_path=file_path,
            file_type=file_type,
            full_text=full_text,
            pages=pages,
            engine_used=self.name,
            processing_time_ms=processing_time_ms,
            metadata={
                **metadata,
                "language": language
            }
        )

    def _create_error_result(
        self,
        file_path: str,
        error: str,
        file_type: str
    ) -> ReadResult:
        """Create an error ReadResult."""
        return ReadResult(
            success=False,
            file_path=file_path,
            file_type=file_type,
            error=error,
            engine_used=self.name
        )
