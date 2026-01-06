"""
ERP Arabic OCR Microservice - Core Services Package
====================================================
Base dataclasses for OCR results, fusion, and correction.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime


class OCREngine(Enum):
    """Supported OCR engines."""
    PADDLE = "paddle"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    FUSED = "fused"


class FusionStrategy(Enum):
    """Result fusion strategies."""
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MAJORITY_VOTING = "majority_voting"
    DICTIONARY_VALIDATED = "dictionary_validated"
    BEST_CONFIDENCE = "best_confidence"


class DocumentType(Enum):
    """Supported document types."""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    ID_CARD = "id_card"
    GENERAL = "general"


@dataclass
class BoundingBox:
    """Bounding box for text region."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> Dict[str, float]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height
        }

    @classmethod
    def from_points(cls, points: List[List[float]]) -> "BoundingBox":
        """Create from list of corner points [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]."""
        if len(points) >= 4:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            return cls(
                x1=min(x_coords),
                y1=min(y_coords),
                x2=max(x_coords),
                y2=max(y_coords)
            )
        return cls(0, 0, 0, 0)


@dataclass
class TextBlock:
    """Single text block from OCR."""
    text: str
    confidence: float
    bbox: Optional[BoundingBox] = None
    language: str = "ar"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "language": self.language
        }


@dataclass
class OCRResult:
    """
    Result from a single OCR engine.

    Attributes:
        text: Full extracted text
        confidence: Overall confidence score (0.0-1.0)
        engine: OCR engine used
        blocks: Individual text blocks with positions
        raw_text: Unprocessed text before corrections
        processing_time_ms: Time taken for OCR
        language_detected: Detected primary language
        metadata: Additional engine-specific data
    """
    text: str
    confidence: float
    engine: OCREngine
    blocks: List[TextBlock] = field(default_factory=list)
    raw_text: str = ""
    processing_time_ms: float = 0.0
    language_detected: str = "ar"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.raw_text:
            self.raw_text = self.text

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "engine": self.engine.value,
            "blocks": [b.to_dict() for b in self.blocks],
            "raw_text": self.raw_text,
            "processing_time_ms": self.processing_time_ms,
            "language_detected": self.language_detected,
            "word_count": self.word_count,
            "block_count": self.block_count,
            "metadata": self.metadata
        }


@dataclass
class FusionResult:
    """
    Result from fusing multiple OCR engine outputs.

    Attributes:
        fused_text: Final fused text output
        confidence: Overall confidence after fusion
        strategy: Fusion strategy used
        individual_results: Results from each engine
        improvement_score: How much fusion improved over best single engine
        word_sources: Which engine contributed each word
    """
    fused_text: str
    confidence: float
    strategy: FusionStrategy
    individual_results: List[OCRResult] = field(default_factory=list)
    improvement_score: float = 0.0
    word_sources: Dict[str, str] = field(default_factory=dict)
    processing_time_ms: float = 0.0

    @property
    def engines_used(self) -> List[str]:
        return [r.engine.value for r in self.individual_results]

    @property
    def best_single_confidence(self) -> float:
        if not self.individual_results:
            return 0.0
        return max(r.confidence for r in self.individual_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fused_text": self.fused_text,
            "confidence": self.confidence,
            "strategy": self.strategy.value,
            "engines_used": self.engines_used,
            "individual_results": [r.to_dict() for r in self.individual_results],
            "improvement_score": self.improvement_score,
            "best_single_confidence": self.best_single_confidence,
            "processing_time_ms": self.processing_time_ms
        }


@dataclass
class CorrectionResult:
    """
    Result from text correction (Arabic rules or LLM).

    Attributes:
        original: Original text before correction
        corrected: Text after correction
        corrections_made: List of corrections applied
        confidence: Confidence in corrections
        correction_type: Type of correction (rules, llm, hybrid)
    """
    original: str
    corrected: str
    corrections_made: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 1.0
    correction_type: str = "rules"
    processing_time_ms: float = 0.0

    @property
    def correction_count(self) -> int:
        return len(self.corrections_made)

    @property
    def was_modified(self) -> bool:
        return self.original != self.corrected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "corrected": self.corrected,
            "corrections_made": self.corrections_made,
            "correction_count": self.correction_count,
            "was_modified": self.was_modified,
            "confidence": self.confidence,
            "correction_type": self.correction_type,
            "processing_time_ms": self.processing_time_ms
        }


@dataclass
class InvoiceField:
    """Single extracted invoice field."""
    field_name: str
    field_name_ar: str
    value: str
    confidence: float
    bbox: Optional[BoundingBox] = None
    validated: bool = False
    validation_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "field_name_ar": self.field_name_ar,
            "value": self.value,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "validated": self.validated,
            "validation_message": self.validation_message
        }


@dataclass
class LineItem:
    """Invoice line item."""
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total": self.total,
            "confidence": self.confidence
        }


@dataclass
class InvoiceData:
    """Complete extracted invoice data."""
    tax_number: Optional[InvoiceField] = None
    invoice_number: Optional[InvoiceField] = None
    date: Optional[InvoiceField] = None
    vendor_name: Optional[InvoiceField] = None
    customer_name: Optional[InvoiceField] = None
    subtotal: Optional[InvoiceField] = None
    tax_amount: Optional[InvoiceField] = None
    total: Optional[InvoiceField] = None
    line_items: List[LineItem] = field(default_factory=list)
    additional_fields: Dict[str, InvoiceField] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for field_name in ['tax_number', 'invoice_number', 'date', 'vendor_name',
                           'customer_name', 'subtotal', 'tax_amount', 'total']:
            field_val = getattr(self, field_name)
            if field_val:
                result[field_name] = field_val.to_dict()

        result['line_items'] = [item.to_dict() for item in self.line_items]
        result['additional_fields'] = {
            k: v.to_dict() for k, v in self.additional_fields.items()
        }
        return result


@dataclass
class ProcessingResult:
    """
    Complete OCR processing result.

    Combines OCR, fusion, correction, and field extraction results.
    """
    # Core OCR output
    text: str
    confidence: float

    # Processing details
    ocr_result: Optional[OCRResult] = None
    fusion_result: Optional[FusionResult] = None
    correction_result: Optional[CorrectionResult] = None

    # Structured data extraction
    invoice_data: Optional[InvoiceData] = None
    document_type: DocumentType = DocumentType.GENERAL

    # Metadata
    request_id: str = ""
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Input file info
    filename: str = ""
    file_size_bytes: int = 0
    image_dimensions: Tuple[int, int] = (0, 0)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and self.confidence > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "text": self.text,
            "confidence": self.confidence,
            "document_type": self.document_type.value,
            "ocr_result": self.ocr_result.to_dict() if self.ocr_result else None,
            "fusion_result": self.fusion_result.to_dict() if self.fusion_result else None,
            "correction_result": self.correction_result.to_dict() if self.correction_result else None,
            "invoice_data": self.invoice_data.to_dict() if self.invoice_data else None,
            "metadata": {
                "request_id": self.request_id,
                "processing_time_ms": self.processing_time_ms,
                "timestamp": self.timestamp,
                "filename": self.filename,
                "file_size_bytes": self.file_size_bytes,
                "image_dimensions": self.image_dimensions
            },
            "warnings": self.warnings,
            "errors": self.errors
        }


# Lazy imports for service modules
def get_resource_manager():
    """Get global resource manager instance."""
    from .resource_manager import get_resource_manager as _get_rm
    return _get_rm()


def get_cache_manager():
    """Get global cache manager instance."""
    from .cache_manager import get_cache_manager as _get_cm
    return _get_cm()


# Export all classes
__all__ = [
    # Enums
    "OCREngine",
    "FusionStrategy",
    "DocumentType",
    # Base classes
    "BoundingBox",
    "TextBlock",
    # Results
    "OCRResult",
    "FusionResult",
    "CorrectionResult",
    # Invoice
    "InvoiceField",
    "LineItem",
    "InvoiceData",
    # Complete result
    "ProcessingResult",
    # Service accessors
    "get_resource_manager",
    "get_cache_manager",
]
