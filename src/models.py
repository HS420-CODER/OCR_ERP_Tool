"""
Data models for Hybrid Read Tool.

Provides dataclasses for:
- ReadOptions: Input parameters for read operations
- TextBlock: Single text block from OCR
- PageResult: OCR result for a single page
- ReadResult: Complete result from read operation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class EngineType(Enum):
    """Available OCR/Vision engines."""
    AUTO = "auto"
    PADDLE = "paddle"
    TESSERACT = "tesseract"
    OLLAMA = "ollama"


@dataclass
class ReadOptions:
    """
    Options for read operations - mirrors Claude Code CLI Read tool parameters.

    Attributes:
        file_path: Absolute path to file (required)
        offset: Line number to start reading from (0-based, for text files)
        limit: Maximum number of lines to read (for text files)
        max_line_length: Truncate lines longer than this (default 2000)
        lang: Language code for OCR ("en" or "ar")
        engine: OCR engine to use ("auto", "paddle", "tesseract", "ollama")
        include_confidence: Include OCR confidence scores
        include_bounding_boxes: Include text positions
        prompt: Custom prompt for vision analysis (Ollama only)
        vision_model: Ollama vision model name
        output_format: Output format ("text", "json", "markdown")
        structured_output: Enable structured bilingual output for Arabic
    """

    # File reading options
    file_path: str
    offset: int = 0
    limit: int = 2000
    max_line_length: int = 2000

    # OCR-specific options
    lang: str = "en"
    engine: str = "auto"
    include_confidence: bool = True
    include_bounding_boxes: bool = False

    # Vision analysis options (for Ollama)
    prompt: Optional[str] = None
    vision_model: str = "llava"

    # Output format
    output_format: str = "text"
    structured_output: bool = True  # Enable Claude Code-like structured output

    def __post_init__(self):
        """Validate options after initialization."""
        # Validate language
        if self.lang not in ["en", "ar"]:
            raise ValueError(f"Unsupported language: {self.lang}. Use 'en' or 'ar'.")

        # Validate engine
        valid_engines = ["auto", "paddle", "tesseract", "ollama"]
        if self.engine not in valid_engines:
            raise ValueError(f"Invalid engine: {self.engine}. Use one of: {valid_engines}")

        # Validate output format
        valid_formats = ["text", "json", "markdown"]
        if self.output_format not in valid_formats:
            raise ValueError(f"Invalid output format: {self.output_format}. Use one of: {valid_formats}")


@dataclass
class TextBlock:
    """
    Single text block extracted from document.

    Attributes:
        text: The extracted text content
        confidence: OCR confidence score (0.0 to 1.0)
        bbox: Bounding box coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        page: Page number (1-indexed)
    """
    text: str
    confidence: float = 1.0
    bbox: Optional[List[List[int]]] = None
    page: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "page": self.page
        }
        if self.bbox is not None:
            result["bbox"] = self.bbox
        return result


@dataclass
class PageResult:
    """
    OCR result for a single page.

    Attributes:
        page_number: Page number (1-indexed)
        text_blocks: List of text blocks on this page
        full_text: Complete text content of the page
        width: Page width in pixels (if available)
        height: Page height in pixels (if available)
    """
    page_number: int
    text_blocks: List[TextBlock] = field(default_factory=list)
    full_text: str = ""
    width: Optional[int] = None
    height: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "page_number": self.page_number,
            "full_text": self.full_text,
            "text_blocks": [block.to_dict() for block in self.text_blocks]
        }
        if self.width is not None:
            result["width"] = self.width
        if self.height is not None:
            result["height"] = self.height
        return result


@dataclass
class ReadResult:
    """
    Complete result from read operation.

    Attributes:
        success: Whether the operation succeeded
        file_path: Path to the processed file
        file_type: Type of file (image, pdf, text, notebook)
        engine_used: Which OCR engine was used
        pages: List of page results
        full_text: Complete text from all pages
        processing_time_ms: Processing time in milliseconds
        language: Language used for OCR
        metadata: Additional metadata
        error: Error message if operation failed
        structured_output: Structured markdown output (for Arabic invoices)
    """
    success: bool
    file_path: str
    file_type: str
    engine_used: str
    pages: List[PageResult] = field(default_factory=list)
    full_text: str = ""
    processing_time_ms: float = 0.0
    language: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    structured_output: Optional[str] = None  # Claude Code-like markdown output

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "success": self.success,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "engine_used": self.engine_used,
            "pages": [page.to_dict() for page in self.pages],
            "full_text": self.full_text,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "language": self.language,
            "metadata": self.metadata
        }
        if self.error:
            result["error"] = self.error
        if self.structured_output:
            result["structured_output"] = self.structured_output
        return result

    @classmethod
    def error_result(cls, file_path: str, error: str, file_type: str = "unknown") -> "ReadResult":
        """Create an error result."""
        return cls(
            success=False,
            file_path=file_path,
            file_type=file_type,
            engine_used="none",
            error=error
        )
