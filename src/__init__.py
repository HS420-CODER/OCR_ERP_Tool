"""
Hybrid Read Tool - Claude Code CLI-like functionality offline.

A modular OCR and document reading tool that provides:
- Text file reading with line numbers (cat -n format)
- Image OCR via PaddleOCR, Tesseract, or Ollama Vision
- PDF processing with page-by-page extraction
- Jupyter notebook (.ipynb) cell extraction
- Structured Arabic/English bilingual output

No API keys required - fully offline operation.
"""

__version__ = "1.0.0"
__author__ = "OCR_2 Project"

from .models import ReadOptions, ReadResult, TextBlock, PageResult
from .config import ReadToolConfig
from .read_tool import HybridReadTool

__all__ = [
    "ReadOptions",
    "ReadResult",
    "TextBlock",
    "PageResult",
    "ReadToolConfig",
    "HybridReadTool",
]
