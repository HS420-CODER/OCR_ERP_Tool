"""
API module for OCR batch processing and external interfaces.

Modules:
- batch_processor: Parallel OCR processing for multiple images

Part of Phase 7: Performance & Quality implementation.
"""

from .batch_processor import (
    BatchResult,
    BatchOCRProcessor,
    get_batch_processor,
    process_batch,
    process_batch_async,
)

__all__ = [
    # Batch Processing
    "BatchResult",
    "BatchOCRProcessor",
    "get_batch_processor",
    "process_batch",
    "process_batch_async",
]
