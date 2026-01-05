"""
Abstract base class for OCR/Vision engines.

All engine implementations (PaddleOCR, Tesseract, Ollama) must inherit
from BaseEngine and implement the abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from ..models import ReadResult, PageResult, TextBlock


@dataclass
class EngineCapabilities:
    """
    Describes what an engine can do.

    Attributes:
        supports_images: Can process image files
        supports_pdf: Can process PDF files
        supports_vision_analysis: Can perform context-aware vision analysis
        supports_gpu: Can use GPU acceleration
        supported_languages: List of supported language codes
        max_file_size_mb: Maximum file size the engine can handle
        supports_batch: Can process multiple files at once
        supports_streaming: Can stream results
        supports_tables: Can detect and extract tables
        supports_structure: Can analyze document structure
    """
    supports_images: bool = True
    supports_pdf: bool = True
    supports_vision_analysis: bool = False
    supports_gpu: bool = False
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    max_file_size_mb: int = 50
    supports_batch: bool = False
    supports_streaming: bool = False
    supports_tables: bool = False
    supports_structure: bool = False


class BaseEngine(ABC):
    """
    Abstract base class for OCR/Vision engines.

    All engine implementations must:
    1. Implement the abstract methods
    2. Set the `name` and `display_name` properties
    3. Return proper ReadResult objects
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Engine identifier name (lowercase, no spaces).

        Examples: "paddle", "tesseract", "ollama"
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable engine name.

        Examples: "PaddleOCR", "Tesseract OCR", "Ollama Vision"
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the engine is installed and ready to use.

        Returns:
            True if engine is available, False otherwise
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> EngineCapabilities:
        """
        Get the engine's capabilities.

        Returns:
            EngineCapabilities describing what this engine can do
        """
        pass

    @abstractmethod
    def process_image(
        self,
        image_path: str,
        lang: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process a single image file with OCR.

        Args:
            image_path: Path to the image file
            lang: Language code for OCR ("en" or "ar")
            options: Additional engine-specific options

        Returns:
            ReadResult with extracted text and metadata
        """
        pass

    @abstractmethod
    def process_pdf(
        self,
        pdf_path: str,
        lang: str = "en",
        max_pages: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process a PDF file with OCR.

        Args:
            pdf_path: Path to the PDF file
            lang: Language code for OCR ("en" or "ar")
            max_pages: Maximum number of pages to process (None for all)
            options: Additional engine-specific options

        Returns:
            ReadResult with extracted text from all pages
        """
        pass

    def process_with_prompt(
        self,
        file_path: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Process file with custom prompt (for vision models).

        Default implementation raises NotImplementedError.
        Override in engines that support vision analysis (e.g., Ollama).

        Args:
            file_path: Path to the file
            prompt: Custom analysis prompt
            options: Additional options

        Returns:
            ReadResult with analysis

        Raises:
            NotImplementedError: If engine doesn't support prompted analysis
        """
        raise NotImplementedError(
            f"{self.display_name} does not support prompted vision analysis"
        )

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.

        Returns:
            List of language codes (e.g., ["en", "ar"])
        """
        return self.get_capabilities().supported_languages

    def supports_language(self, lang: str) -> bool:
        """
        Check if a language is supported.

        Args:
            lang: Language code to check

        Returns:
            True if language is supported
        """
        return lang.lower() in [l.lower() for l in self.get_supported_languages()]

    def _create_error_result(
        self,
        file_path: str,
        error: str,
        file_type: str = "unknown"
    ) -> ReadResult:
        """
        Helper to create an error result.

        Args:
            file_path: Path to the file
            error: Error message
            file_type: Type of file

        Returns:
            ReadResult with error
        """
        return ReadResult(
            success=False,
            file_path=file_path,
            file_type=file_type,
            engine_used=self.name,
            error=error
        )

    def _create_success_result(
        self,
        file_path: str,
        file_type: str,
        pages: List[PageResult],
        language: str,
        processing_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReadResult:
        """
        Helper to create a success result.

        Args:
            file_path: Path to the file
            file_type: Type of file
            pages: List of page results
            language: Language used
            processing_time_ms: Processing time
            metadata: Additional metadata

        Returns:
            ReadResult with extracted text
        """
        # Combine full text from all pages
        full_text_parts = []
        for page in pages:
            if page.full_text:
                full_text_parts.append(page.full_text)

        full_text = "\n\n--- Page Break ---\n\n".join(full_text_parts)

        return ReadResult(
            success=True,
            file_path=file_path,
            file_type=file_type,
            engine_used=self.name,
            pages=pages,
            full_text=full_text,
            processing_time_ms=processing_time_ms,
            language=language,
            metadata=metadata or {}
        )

    @staticmethod
    def _measure_time(func):
        """
        Decorator to measure execution time.

        Usage:
            @BaseEngine._measure_time
            def process_image(self, ...):
                ...
        """
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # If result is a ReadResult, update processing time
            if isinstance(result, ReadResult):
                result.processing_time_ms = elapsed_ms

            return result
        return wrapper


class EngineError(Exception):
    """Base exception for engine errors."""

    def __init__(self, message: str, engine: str = "", code: str = ""):
        self.message = message
        self.engine = engine
        self.code = code
        super().__init__(message)


class EngineNotAvailableError(EngineError):
    """Engine is not installed or not ready."""
    pass


class EngineProcessingError(EngineError):
    """Error during engine processing."""
    pass


class LanguageNotSupportedError(EngineError):
    """Language not supported by the engine."""
    pass
